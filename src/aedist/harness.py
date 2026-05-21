"""Shared utilities for the AEDIST query harness.

All query scripts (query, query_direct, query_multiturn, query_rag, query_livesearch) import
from here to avoid duplicating client setup, budget tracking, model loading,
save/skip logic, and cost computation.
"""

import json
import logging
import os
import re
import time
import tomllib
from collections.abc import Iterator
from pathlib import Path

import yaml
from openai import OpenAI

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------


def load_models(path: str) -> list[dict]:
    """Load model registry from YAML file."""
    with open(path) as f:
        models = yaml.safe_load(f) or []
    return models


def select_models(models: list[dict], ids: list[str]) -> list[dict]:
    """Filter models by ID list. Warns on IDs not found in registry."""
    id_set = set(ids)
    result = [m for m in models if m["name"] in id_set]
    missing = id_set - {m["name"] for m in result}
    if missing:
        log.warning("Model IDs not found in registry: %s", sorted(missing))
    return result


def model_metadata(model: dict) -> dict:
    """Extract metadata fields from model registry entry."""
    return {
        k: model.get(k)
        for k in ("size_class", "country", "architecture", "provider", "context_window")
        if model.get(k) is not None
    }


# ---------------------------------------------------------------------------
# Cost computation
# ---------------------------------------------------------------------------

# Pricing is per million tokens; divide by this to get per-token cost.
TOKENS_PER_MTOK = 1_000_000


def compute_cost(usage: dict, model: dict) -> float:
    """Compute USD cost from token usage and model pricing."""
    price_in = model.get("price_per_mtok_in", 0.0)
    price_out = model.get("price_per_mtok_out", 0.0)
    prompt_tokens = usage.get("prompt_tokens", 0) or 0
    completion_tokens = usage.get("completion_tokens", 0) or 0
    return (prompt_tokens * price_in + completion_tokens * price_out) / TOKENS_PER_MTOK


# ---------------------------------------------------------------------------
# Budget tracking
# ---------------------------------------------------------------------------


class BudgetTracker:
    """Track cumulative spend and stop when budget exceeded."""

    def __init__(self, budget_usd: float | None = None):
        self.budget_usd = budget_usd
        self.total_cost = 0.0

    def add(self, cost: float) -> None:
        self.total_cost += cost

    @property
    def exceeded(self) -> bool:
        if self.budget_usd is None:
            return False
        return self.total_cost >= self.budget_usd

    def check_or_warn(self) -> bool:
        """Return True if OK to proceed, False if budget exceeded."""
        if self.exceeded:
            log.warning(
                "Budget exceeded (%.4f >= %.4f USD). Stopping.",
                self.total_cost,
                self.budget_usd,
            )
            return False
        return True


# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------

# Approximate characters per token for English text (actual varies 3-5)
CHARS_PER_TOKEN = 4

# Fraction of model context window to use (safety margin)
CONTEXT_WINDOW_SAFETY_MARGIN = 0.8


def estimate_tokens(text: str) -> int:
    """Rough token estimate based on character count."""
    return len(text) // CHARS_PER_TOKEN


def estimate_messages_tokens(messages: list[dict]) -> int:
    """Estimate total tokens across a message list."""
    return sum(estimate_tokens(m.get("content", "")) for m in messages)


# ---------------------------------------------------------------------------
# OpenAI client
# ---------------------------------------------------------------------------


def load_experiments(path: str) -> dict:
    """Load experiments.toml configuration."""
    with open(path, "rb") as f:
        return tomllib.load(f)


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------

# Modules that are always included regardless of the caller's selection.
# Post-rename (commit 4dc99e5) these are the new implicit "always" set,
# replacing the previous ``base.txt`` single-file role. ``2_goal`` declares
# the task; ``5_table`` declares the structured output schema. Together they
# are the locked Experiment 1 baseline (ticket 0175).
ALWAYS_MODULES = ("2_goal", "5_table")


def assemble_prompt(modules_dir: Path, module_names: list[str]) -> str:
    """Assemble a prompt from the always-pair plus named optional modules.

    *modules_dir* is scanned at call time for ``*.txt`` files. Each filename
    stem is a module identifier (e.g. ``1_persona``, ``A_Statistics``). The
    two modules in :data:`ALWAYS_MODULES` (``2_goal`` and ``5_table``) are
    always included; the *module_names* list adds optional modules. The
    union is sorted lexicographically by filename and joined with
    ``"\\n\\n"``.

    Raises ``ValueError`` if any name in *module_names* does not resolve
    to a file in *modules_dir*.
    """
    available = {p.stem for p in modules_dir.glob("*.txt")}
    requested = set(module_names) | set(ALWAYS_MODULES)
    unknown = requested - available
    if unknown:
        raise ValueError(
            f"Unknown prompt modules: {sorted(unknown)}. Available: {sorted(available)}"
        )
    sections = [(modules_dir / f"{name}.txt").read_text().strip() for name in sorted(requested)]
    return "\n\n".join(sections)


def build_messages(user_text: str, system_instruction: str | None) -> list[dict]:
    """Build a chat-completions message list, prepending a system message when given.

    Returns ``[{"role": "system", ...}, {"role": "user", ...}]`` when
    *system_instruction* is a non-empty string, otherwise just the user message.
    """
    messages: list[dict] = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": user_text})
    return messages


def make_client(base_url: str | None = None) -> OpenAI:
    """Create an OpenAI-compatible client (legacy interface).

    When *base_url* is provided (e.g. Ollama), use it directly with a
    dummy API key.  Otherwise default to OpenRouter.

    ``max_retries=1`` (ticket 0183): openai-python defaults to 2, which —
    combined with the worker's 600s per-call timeout — gives a worst-case
    wall time around 30 minutes per wedged call. One retry caps that to
    roughly 20 minutes while still tolerating a single transient network
    blip. The worker-level requeue (failed/ → manual rerun) is the real
    backstop, so we don't need aggressive in-client retries.
    """
    if base_url:
        from urllib.parse import urlparse

        host = urlparse(base_url).hostname or ""
        if host.endswith("openrouter.ai"):
            api_key = os.environ.get("OPENROUTER_API_KEY")
            if not api_key:
                raise SystemExit("Set OPENROUTER_API_KEY environment variable")
        else:
            api_key = "ollama"
        return OpenAI(base_url=base_url, api_key=api_key, max_retries=1)
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("Set OPENROUTER_API_KEY environment variable")
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        max_retries=1,
    )


def make_client_for_route(model: dict) -> OpenAI:
    """Create an OpenAI-compatible client from model registry entry.

    Reads ``route`` and ``base_url`` directly from the model dict
    (v2 registry schema).  For Ollama (no env_key), uses a long timeout
    and a dummy API key.
    """
    base_url = model["base_url"]
    env_key = model.get("env_key")
    if env_key:
        api_key = os.environ.get(env_key)
        if not api_key:
            raise SystemExit(f"Set {env_key} environment variable")
    else:
        api_key = "ollama"
    kwargs: dict = {"base_url": base_url, "api_key": api_key, "max_retries": 1}
    if not env_key:
        import httpx

        kwargs["timeout"] = httpx.Timeout(connect=5.0, read=3600.0, write=600.0, pool=600.0)
    return OpenAI(**kwargs)


# ---------------------------------------------------------------------------
# File naming and skip logic
# ---------------------------------------------------------------------------


def output_filename(model_id: str, run: int, prefix: str = "") -> str:
    """Generate output filename: {prefix}{short_name}-run{n}.json."""
    short = model_id.split("/")[-1].replace(":", "-")
    if prefix:
        return f"{prefix}-{short}-run{run}.json"
    return f"{short}-run{run}.json"


def output_path(output_dir: Path, model_id: str, run: int, prefix: str = "") -> Path:
    """Return the full output path for a model run."""
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / output_filename(model_id, run, prefix)


def should_skip(output_dir: Path, model_id: str, run: int, prefix: str = "") -> bool:
    """Return True if the output file already exists."""
    return output_path(output_dir, model_id, run, prefix).exists()


_MODEL_REPLY_RE = re.compile(r"^.+-run\d+\.json$")


def iter_model_replies(directory: Path) -> Iterator[Path]:
    """Yield model-reply JSON files from *directory*, sorted by name.

    Matches the canonical naming convention from output_filename():
    {slug}-run{N}.json or {prefix}-{slug}-run{N}.json.
    Excludes all derived files (.record.json, _summary.json,
    tavily_cache.json, etc.) by whitelist, not blacklist.
    """
    for f in sorted(directory.glob("*.json")):
        if _MODEL_REPLY_RE.match(f.name):
            yield f


# ---------------------------------------------------------------------------
# Save helpers
# ---------------------------------------------------------------------------


def save_json(filepath: Path, record: dict) -> None:
    """Write a JSON record to file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    log.info("Saved %s", filepath)


# ---------------------------------------------------------------------------
# Ollama native API (needed because /v1/ ignores num_ctx)
# ---------------------------------------------------------------------------


def query_ollama_native(
    base_url: str,
    model_id: str,
    messages: list[dict],
    num_ctx: int,
    num_predict: int | None = None,
    no_think: bool = False,
    temperature: float | None = None,
    seed: int | None = None,
) -> dict:
    """Query Ollama via native /api/chat with explicit num_ctx (and optional num_predict output cap).

    Plumbs JobSpec-declared API parameters into the Ollama ``options`` payload
    so sweep configs are not silently dropped at the wire (ticket 0139):
    ``temperature``, ``seed``, ``num_predict`` (Ollama's name for max_tokens),
    and ``think=false`` (no_think) all land in ``options``.
    """
    import httpx

    # base_url is like http://localhost:11434/v1 — strip /v1
    api_url = base_url.rstrip("/").removesuffix("/v1") + "/api/chat"
    options: dict = {"num_ctx": num_ctx}
    if num_predict is not None:
        options["num_predict"] = num_predict
    if no_think:
        options["think"] = False
    if temperature is not None:
        options["temperature"] = temperature
    if seed is not None:
        options["seed"] = seed
    t0 = time.monotonic()
    resp = httpx.post(
        api_url,
        json={
            "model": model_id,
            "messages": messages,
            "options": options,
            "stream": False,
        },
        timeout=3600.0,
    )
    resp.raise_for_status()
    data = resp.json()
    wall_seconds = round(time.monotonic() - t0, 3)
    msg = data.get("message", {})
    return {
        "content": msg.get("content", ""),
        "thinking": msg.get("thinking", ""),
        "finish_reason": data.get("done_reason", "stop"),
        "usage": {
            "prompt_tokens": data.get("prompt_eval_count", 0),
            "completion_tokens": data.get("eval_count", 0),
        },
        "wall_seconds": wall_seconds,
    }


# ---------------------------------------------------------------------------
# Claude Code CLI (subprocess, --print mode)
# ---------------------------------------------------------------------------


def query_claude_cli(
    model_id: str,
    messages: list[dict],
    *,
    timeout: float = 600.0,
    max_budget_usd: float | None = None,
) -> dict:
    """Query via Claude Code CLI in non-interactive --print mode.

    Authenticates via the user's existing Claude Code session (no API key
    in the sweep environment). Runs with --bare to skip hooks, plugin
    sync, CLAUDE.md auto-discovery, and other interactive-mode overhead;
    --allowedTools "" to disallow every tool so the model answers from
    parametric knowledge only (matches the no-web Exp 1 discipline).

    Cost is reported by the CLI itself in `total_cost_usd`; pricing is
    governed by the user's Anthropic subscription / API plan, not by the
    registry's price_per_mtok_* fields.

    Messages: a single system message (optional) plus one user message
    are supported; multi-turn is not. The CLI takes the prompt on stdin.

    Limitations:
    - No temperature, seed, or max_tokens control — runs use CLI defaults.
    - Single user turn only (no conversation history).
    - Reasoning tokens are not surfaced separately by the CLI's JSON.
    """
    import subprocess

    system_text = ""
    user_text = ""
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "system":
            system_text = content
        elif role == "user":
            user_text = content
    if not user_text:
        raise ValueError("query_claude_cli: messages must include a user turn")

    cmd = [
        "claude",
        "--print",
        "--bare",
        "--model",
        model_id,
        "--output-format",
        "json",
        "--allowedTools",
        "",
        "--no-session-persistence",
    ]
    if system_text:
        cmd.extend(["--append-system-prompt", system_text])
    if max_budget_usd is not None:
        cmd.extend(["--max-budget-usd", f"{max_budget_usd:.4f}"])

    t0 = time.monotonic()
    proc = subprocess.run(
        cmd,
        input=user_text,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    wall_seconds = round(time.monotonic() - t0, 3)

    if proc.returncode != 0:
        raise RuntimeError(f"claude CLI exited {proc.returncode}: {proc.stderr[:500]}")

    data = json.loads(proc.stdout)
    if data.get("is_error"):
        raise RuntimeError(f"claude CLI error: {data.get('result', 'unknown')}")

    usage = data.get("usage", {})
    return {
        "content": data.get("result", ""),
        "finish_reason": data.get("stop_reason", "stop"),
        "usage": {
            "prompt_tokens": usage.get("input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
        },
        "wall_seconds": wall_seconds,
        "cost_usd": data.get("total_cost_usd", 0.0),
    }


# ---------------------------------------------------------------------------
# Capability-driven API kwargs
# ---------------------------------------------------------------------------


def build_api_kwargs(
    model: dict,
    *,
    max_tokens: int | None = None,
    temperature: float,
    enable_web_search: bool = False,
    seed: int | None = None,
    provider_order: list[str] | None = None,
    no_think: bool = False,
) -> dict:
    """Build API kwargs from model capability flags.

    Reads ``web_search`` flag from the model dict and constructs the
    appropriate kwargs for ``chat.completions.create()``:

    - ``web_search: true`` → add OpenRouter server tool
      ``tools: [{"type": "openrouter:web_search"}]``
      (model decides when to search; ~$0.02 per search call via Exa)

    Set *enable_web_search* to ``False`` to suppress web search tools even
    when the model declares the capability (e.g. RAG mode, where the corpus
    is the context and web search is counterproductive).

    *seed* pins the RNG for reproducibility (OpenRouter: "best effort").
    *provider_order* restricts routing to a specific backend list, e.g.
    ``["DeepSeek"]``, eliminating cross-provider floating-point variance.
    Both are required to approach determinism on MoE models like DeepSeek V3.
    """
    kwargs: dict = {}
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    kwargs["temperature"] = temperature

    if seed is not None:
        kwargs["seed"] = seed

    if enable_web_search and model.get("web_search", False):
        kwargs["tools"] = [
            {
                "type": "openrouter:web_search",
                "parameters": {
                    "max_total_results": 37,  # ~$0.15 cap ($4/1000 results)
                },
            }
        ]

    # OpenRouter provider pinning goes in extra_body, not top-level kwargs.
    extra: dict = {}
    if provider_order:
        extra["provider"] = {"order": provider_order, "allow_fallbacks": False}
    if no_think:
        extra["think"] = False
    # Per-model reasoning_effort (typed "minimal" | "low" | "medium" | "high").
    # Used by OpenAI gpt-oss-* and other reasoning-configurable models; expressed
    # via OpenRouter's unified reasoning field (see ticket 0175). This is a
    # capability of the model, not a sweep-wide knob — set in models.yaml.
    reasoning_effort = model.get("reasoning_effort")
    if reasoning_effort:
        extra["reasoning"] = {"effort": reasoning_effort}
    if extra:
        kwargs["extra_body"] = extra

    return kwargs


# ---------------------------------------------------------------------------
# Single-turn query helper
# ---------------------------------------------------------------------------


def query_model(
    client: OpenAI,
    model_id: str,
    messages: list[dict],
    *,
    num_ctx: int = 32768,
    ollama_base_url: str = "http://localhost:11434/v1",
    **kwargs,
) -> dict:
    """Dispatch to Ollama native or OpenAI-compatible API.

    Models without '/' in their ID are assumed to be Ollama (e.g. 'qwen3.5:2b').
    Ollama native API is used so num_ctx is honoured (the /v1/ shim ignores it).

    For the Ollama branch, translate OpenAI-shape ``api_kwargs`` (as produced
    by :func:`build_api_kwargs`) into Ollama-shape ``options`` parameters so
    JobSpec-declared values reach the wire (ticket 0139):

    | OpenAI-shape kwarg           | Ollama option       |
    |------------------------------|---------------------|
    | ``temperature``              | ``temperature``     |
    | ``seed``                     | ``seed``            |
    | ``max_tokens``               | ``num_predict``     |
    | ``extra_body["think"]=False``| ``think=False``     |

    OpenRouter-only keys (``extra_body["provider"]``, ``extra_body["reasoning"]``,
    ``tools``) are dropped on the Ollama branch — they have no Ollama analogue.
    """
    if "/" not in model_id:
        extra_body = kwargs.get("extra_body") or {}
        no_think = extra_body.get("think") is False
        return query_ollama_native(
            ollama_base_url,
            model_id,
            messages,
            num_ctx,
            num_predict=kwargs.get("max_tokens"),
            no_think=no_think,
            temperature=kwargs.get("temperature"),
            seed=kwargs.get("seed"),
        )
    return query_single_turn(client, model_id, messages, **kwargs)


def query_single_turn(
    client: OpenAI,
    model_id: str,
    messages: list[dict],
    **kwargs,
) -> dict:
    """Send messages to a model, return response dict with timing."""
    t0 = time.monotonic()
    response = client.chat.completions.create(
        model=model_id,
        messages=messages,
        **kwargs,
    )
    wall_seconds = round(time.monotonic() - t0, 3)
    choice = response.choices[0]
    # Preserve the full usage dict (incl. completion_tokens_details.reasoning_tokens
    # exposed by OpenRouter for reasoning-capable models). Falls back to {} if the
    # provider returned no usage block. Ticket 0195.
    usage = response.usage.model_dump() if response.usage is not None else {}
    return {
        "content": choice.message.content,
        "finish_reason": choice.finish_reason,
        "usage": usage,
        "wall_seconds": wall_seconds,
    }
