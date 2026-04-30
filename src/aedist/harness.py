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
        return yaml.safe_load(f)


def select_models(models: list[dict], ids: list[str]) -> list[dict]:
    """Filter models by ID list. Warns on IDs not found in registry."""
    id_set = set(ids)
    result = [m for m in models if m["id"] in id_set]
    missing = id_set - {m["id"] for m in result}
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

# Module ordering: persona is prepended, all others appended in this order.
_MODULE_ORDER = [
    "overview",
    "citation_columns",
    "sourcing_ground",
    "narratives",
    "bibliography",
    "statistics",
]
KNOWN_MODULES = frozenset(["persona"] + _MODULE_ORDER)


def assemble_prompt(modules_dir: Path, module_names: list[str]) -> str:
    """Assemble a prompt from base + named modules.

    *modules_dir* contains ``base.txt`` and one file per module
    (e.g. ``persona.txt``, ``overview.txt``).  The *module_names* list
    selects which modules to include.  ``persona`` is prepended before
    the base; all others are appended in a fixed order.

    Raises ``ValueError`` if *module_names* contains unknown names.
    """
    unknown = set(module_names) - KNOWN_MODULES
    if unknown:
        raise ValueError(
            f"Unknown prompt modules: {sorted(unknown)}. Known: {sorted(KNOWN_MODULES)}"
        )
    base = (modules_dir / "base.txt").read_text().strip()
    parts_before: list[str] = []
    parts_after: list[str] = []
    # Sort requested modules into fixed order for reproducibility.
    ordered = [m for m in ["persona"] + _MODULE_ORDER if m in module_names]
    for name in ordered:
        text = (modules_dir / f"{name}.txt").read_text().strip()
        if name == "persona":
            parts_before.append(text)
        else:
            parts_after.append(text)
    sections = parts_before + [base] + parts_after
    return "\n\n".join(sections)


def make_client(base_url: str | None = None) -> OpenAI:
    """Create an OpenAI-compatible client (legacy interface).

    When *base_url* is provided (e.g. Ollama), use it directly with a
    dummy API key.  Otherwise default to OpenRouter.
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
        return OpenAI(base_url=base_url, api_key=api_key)
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("Set OPENROUTER_API_KEY environment variable")
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )


def make_client_for_router(router: str, routers_config: dict) -> OpenAI:
    """Create an OpenAI-compatible client from router config.

    Resolves base_url and API key from the router definition in
    experiments.toml's [routers] section.
    """
    cfg = routers_config[router]
    base_url = cfg["base_url"]
    env_key = cfg.get("env_key")
    if env_key:
        api_key = os.environ.get(env_key)
        if not api_key:
            raise SystemExit(f"Set {env_key} environment variable")
    else:
        api_key = "ollama"
    return OpenAI(base_url=base_url, api_key=api_key)


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
) -> dict:
    """Query Ollama via native /api/chat with explicit num_ctx."""
    import httpx

    # base_url is like http://localhost:11434/v1 — strip /v1
    api_url = base_url.rstrip("/").removesuffix("/v1") + "/api/chat"
    t0 = time.monotonic()
    resp = httpx.post(
        api_url,
        json={
            "model": model_id,
            "messages": messages,
            "options": {"num_ctx": num_ctx},
            "stream": False,
        },
        timeout=3600.0,
    )
    resp.raise_for_status()
    data = resp.json()
    wall_seconds = round(time.monotonic() - t0, 3)
    return {
        "content": data.get("message", {}).get("content", ""),
        "finish_reason": data.get("done_reason", "stop"),
        "usage": {
            "prompt_tokens": data.get("prompt_eval_count", 0),
            "completion_tokens": data.get("eval_count", 0),
        },
        "wall_seconds": wall_seconds,
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
    """
    if "/" not in model_id:
        return query_ollama_native(ollama_base_url, model_id, messages, num_ctx)
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
    usage = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
    }
    return {
        "content": choice.message.content,
        "finish_reason": choice.finish_reason,
        "usage": usage,
        "wall_seconds": wall_seconds,
    }
