"""Exp 2 SOTA-agent smoke — Phase A (design) + Phase B (run) on one agent.

Ticket 0185. Read-only consumer of ``src/aedist/adapter_*.py``. Built
to support two modes:

- **Interactive** (default): SPACE-gated between phases for a human
  reviewer to inspect the meta-prompt, the Phase A response, and the
  Phase B request before each API call.
- **Agentic** (``--no-confirm``): pipeline runs end-to-end without
  prompting. Every step still writes its artefact to disk so an
  out-of-band reviewer (or this script's caller) can inspect after.

Web search is *available* in both phases — Phase A may or may not
search while designing the prompt; we observe what the model does
rather than suppressing the tool (per author direction 2026-05-21).

Output layout under ``--output-dir`` (default
``experiments/outputs/sota_exp2_smoke/``):

- ``{agent}_meta_prompt.txt`` — exact bytes sent to Phase A
- ``{agent}_phase_a.raw.json`` — raw provider response, Phase A
- ``{agent}_phase_a.json``      — parsed RunRecord, Phase A
- ``{agent}_phase_a_design.json`` — extracted designed prompt + settings
- ``{agent}_phase_b.raw.json`` — raw provider response, Phase B
- ``{agent}_phase_b.json``      — parsed RunRecord, Phase B
"""

import argparse
import json
import logging
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import yaml

from aedist import adapter_mistral
from aedist.extract import count_best_table_rows
from aedist.harness import (
    EVIDENCE_PACK_SECTION_TITLE,
    append_evidence_pack,
    assemble_evidence_pack,
)
from aedist.schema import Method, MethodParams, ResourceUse, ResultSummary, RunRecord
from experiments.sota import dialogue_classifier

_TRIPLE_QUOTE_RE = re.compile(r'"""(.*?)"""', re.DOTALL)
_TOKENS_PER_MTOK = 1_000_000

# --- Policy locked by ticket 0214 (state machine + LLM classifier) ---------
# Supersedes the two-slot ticket 0207 policy. Three reply slots:
# ENCOURAGE (≤3 times), VERIFY (used once after first report), TERMINAL
# (budget trigger or encouragement-exhaustion graceful exit).
PHASE_B_TOTAL_BUDGET_USD = 3.00  # per-session dollar guard
PHASE_B_TOTAL_TOKEN_CAP = 50_000  # per-session token cap (output + thinking)
BUDGET_TRIGGER_FRAC = 0.20  # terminal reply when EITHER axis ≤ this fraction of its cap
MAX_ENCOURAGEMENTS = 3

ENCOURAGE_REPLY = "Proceed as you think is best in autonomous agentic mode."
VERIFY_REPLY = (
    "Thank you for the inventory. Please now verify and polish it in ONE "
    "focused pass, prioritising: (a) per-row provenance — every Source 1 "
    "and Source 2 cell must point to a specific URL from your "
    "bibliography; (b) coverage — any plant present in your bibliography "
    "but absent from the table; (c) temporality — every row has an "
    "as-of date or status-change note; (d) internal consistency — "
    "capacity totals reconcile across the table and the statistical "
    "summary. Return the corrected inventory only — no meta-commentary "
    "on what you changed."
)
TERMINAL_REPLY = (
    "I have no additional directive to give you. Please proceed to "
    "generating the report without further asking. If you cannot, we "
    "would appreciate to know why, but the discussion will stop here "
    "in any case. Thanks for your understanding."
)
TURN_SAFETY_CAP = 20

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = REPO_ROOT / "experiments" / "prompts" / "prompt_complete.txt"
QUALITY_BAR_PATH = REPO_ROOT / "slides" / "manuscript" / "main.tex"
METAPROMPT_PATH = REPO_ROOT / "experiments" / "sota" / "protocol_02_metaprompt.md"
MODELS_YAML = REPO_ROOT / "experiments" / "models.yaml"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "experiments" / "outputs" / "sota_exp2_phase_b0"

# Ticket 0512 renumbered the manuscript sections: a new §2 empirical Related
# Work was inserted, shifting Quality dimensions to §3 and the AI capability
# landscape to §4.
# Ticket 0518: manuscript headings are label-anchored, not number-prefixed.
# Ticket 0524: the manuscript is LaTeX (main.tex); markers are \section calls.
QUALITY_BAR_START = "\\section{Quality dimensions"
QUALITY_BAR_END = "\\section{AI capability"

FAMILY_BY_AGENT = {
    "mistral": "mistral-direct",
    "openai": "openai-direct",
    "anthropic": "anthropic-direct",
    "qwen": "qwen-direct",
}


def extract_quality_bar(manuscript_text: str) -> str:
    """Slice the §2 quality-bar block from the manuscript text."""
    start = manuscript_text.find(QUALITY_BAR_START)
    end = manuscript_text.find(QUALITY_BAR_END)
    if start == -1 or end == -1 or end <= start:
        raise ValueError(
            f"Could not locate §2 quality-bar markers "
            f"({QUALITY_BAR_START!r} ... {QUALITY_BAR_END!r}) in manuscript"
        )
    return manuscript_text[start:end].strip()


_FRAMING_SEPARATOR = "\n---\n"


def strip_meta_framing(text: str) -> str:
    """Drop the meta-framing prefix from a protocol prompt file.

    Convention used in `protocol_02_metaprompt.md` and `protocol_07_naive_prompt.md`:
    the file opens with a single framing line ("This is the prompt sent to ...,
    verbatim. ...") followed by `---` and then the actual prompt content.
    The framing line is FOR THE REVIEWER, not the agent. The script must
    strip it before sending the bytes to the model.

    If no `\\n---\\n` separator is present, the input is returned unchanged.
    """
    if _FRAMING_SEPARATOR in text:
        _, _, content = text.partition(_FRAMING_SEPARATOR)
        return content.lstrip("\n")
    return text


def assemble_meta_prompt(
    metaprompt_path: Path = METAPROMPT_PATH, manifest_path: Path | str | None = None
) -> str:
    """Return the Phase A meta-prompt from disk, with framing stripped.

    The canonical text lives at ``experiments/sota/protocol_02_metaprompt.md``
    (Doc 02 of the protocol set). The harness reads it as-is at run time;
    edits to Doc 02 propagate without code change. The opening framing line
    ("This is the prompt sent to the agents, verbatim.") is removed before
    dispatch (see :func:`strip_meta_framing`).

    When ``manifest_path`` is provided, inject an evidence-pack summary after
    the budget announcement so Phase A can design with explicit knowledge of
    available evidence artifacts without revealing chunk bodies.
    """
    prompt = strip_meta_framing(metaprompt_path.read_text(encoding="utf-8"))
    if manifest_path is None:
        return prompt

    evidence_pack_text = assemble_evidence_pack(Path(manifest_path))
    summary, _, _ = evidence_pack_text.partition("\n\n## Chunk 1\n")
    evidence_section = f"\n\n{EVIDENCE_PACK_SECTION_TITLE}\n\n{summary.strip()}\n"
    planning_marker = "\n## Planning headroom\n"
    if planning_marker in prompt:
        return prompt.replace(planning_marker, evidence_section + planning_marker, 1)
    return prompt + evidence_section


def load_model_meta(agent: str) -> dict:
    """Read the SOTA-route registry entry for ``agent`` from models.yaml."""
    registry = yaml.safe_load(MODELS_YAML.read_text())
    target_family = FAMILY_BY_AGENT[agent]
    if isinstance(registry, dict):
        registry = registry.get("models", [])
    for entry in registry:
        if entry.get("family") == target_family:
            return entry
    raise ValueError(f"No entry with family={target_family!r} found in {MODELS_YAML}")


def wait_for_space(prompt: str, *, no_confirm: bool) -> None:
    """Pause for human review; no-op when ``--no-confirm`` is set."""
    if no_confirm:
        log.info("[auto-continue] %s", prompt)
        return
    sys.stdout.write(f"\n{prompt}\nPRESS ENTER to continue, or 'q' to abort > ")
    sys.stdout.flush()
    line = sys.stdin.readline()
    if line.strip().lower() == "q":
        log.warning("Aborted by user.")
        sys.exit(0)


def extract_narrative_from_mistral_raw(raw: dict) -> str:
    """Concatenate text chunks from message.output items in a Mistral raw response.

    The Mistral Conversations API returns ``content`` in two shapes empirically:
    - a flat ``str`` (observed 2026-05-21, Phase A smoke)
    - a ``list[dict]`` of ``{type, text}`` chunks (the shape adapter_mistral
      assumes; observed in the 2026-05-20 derisk fixture)

    Handle both so the smoke is resilient to either response shape.
    """
    chunks: list[str] = []
    for item in raw.get("outputs", []):
        if item.get("type") != "message.output":
            continue
        content = item.get("content")
        if isinstance(content, str):
            chunks.append(content)
        elif isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get("type") == "text":
                    chunks.append(c.get("text", ""))
                elif isinstance(c, str):
                    chunks.append(c)
    return "".join(chunks).strip()


def _normalize_python_triple_quotes(text: str) -> str:
    """Convert Python-style ``\"\"\"...\"\"\"`` blocks to valid JSON string literals.

    SOTA models occasionally use Python triple-quoted strings inside JSON
    despite that being invalid JSON syntax (observed in Mistral Phase A
    2026-05-21: 16K-char response with a triple-quoted ``designed_prompt``).
    ``json.dumps`` produces a correctly escaped JSON string literal.
    """
    return _TRIPLE_QUOTE_RE.sub(lambda m: json.dumps(m.group(1)), text)


def _escape_json_control_chars_in_strings(text: str) -> str:
    """Escape literal control characters that appear inside JSON strings.

    Some Phase A Mistral replies are almost-JSON but include raw newlines inside
    quoted values (for example inside ``designed_prompt``), which is invalid JSON
    even though the envelope shape is otherwise correct. Escape only control
    characters observed while inside a quoted string, preserving structural
    whitespace outside strings.
    """
    escaped_text: list[str] = []
    in_string = False
    escape_next = False

    for char in text:
        if in_string:
            if escape_next:
                escaped_text.append(char)
                escape_next = False
                continue
            if char == "\\":
                escaped_text.append(char)
                escape_next = True
                continue
            if char == '"':
                escaped_text.append(char)
                in_string = False
                continue
            if ord(char) < 0x20:
                if char == "\n":
                    escaped_text.append("\\n")
                elif char == "\r":
                    escaped_text.append("\\r")
                elif char == "\t":
                    escaped_text.append("\\t")
                else:
                    escaped_text.append(f"\\u{ord(char):04x}")
                continue
        else:
            if char == '"':
                in_string = True
        escaped_text.append(char)

    return "".join(escaped_text)


def extract_phase_a_design(response_text: str) -> dict:
    """Parse the JSON envelope out of Phase A's narrative response.

    Tolerant in three layers (SOTA agents ignore "Output ONLY JSON" routinely):
    1. Strip a leading/trailing ``` fence if present.
    2. ``json.loads`` on the stripped text.
    3. Fallback — slice from first ``{`` to last ``}`` and retry.

    Raises ``ValueError`` with a short preview if both attempts fail.
    """
    text = response_text.strip()
    if text.startswith("```"):
        first_nl = text.find("\n")
        if first_nl != -1:
            text = text[first_nl + 1 :]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()
    text = _escape_json_control_chars_in_strings(_normalize_python_triple_quotes(text))
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        first = text.find("{")
        last = text.rfind("}")
        if first == -1 or last == -1 or last <= first:
            preview = text[:400].replace("\n", "\\n")
            raise ValueError(
                f"Phase A response has no JSON object; first 400 chars: {preview!r}"
            ) from None
        try:
            obj = json.loads(text[first : last + 1])
        except json.JSONDecodeError as exc:
            preview = text[:400].replace("\n", "\\n")
            raise ValueError(
                f"Phase A response is not valid JSON: {exc}; first 400 chars: {preview!r}"
            ) from exc
    for key in ("designed_prompt", "system_prompt", "settings", "rationale"):
        if key not in obj:
            raise ValueError(f"Phase A JSON missing required key {key!r}; got keys {list(obj)}")
    if not isinstance(obj["system_prompt"], str):
        raise ValueError(
            f"Phase A 'system_prompt' must be a string, got {type(obj['system_prompt']).__name__}"
        )
    return obj


def _runrecord_from_raw(
    raw_path: Path,
    meta: dict,
    *,
    agent_mode: str,
    wall_s: float | None = None,
) -> RunRecord:
    """Build a minimal RunRecord from a saved Mistral raw response.

    Used when ``adapter_mistral.parse_response`` raises on an unexpected
    content shape — the raw artefact is the ground truth, this synthesizes
    just enough of a RunRecord for the smoke to continue.
    """
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    usage = raw.get("usage", {}) or {}
    tokens_in = int(usage.get("prompt_tokens", 0) or 0)
    tokens_out = int(usage.get("completion_tokens", 0) or 0)
    p_in = float(meta.get("price_per_mtok_in", 0.0)) / _TOKENS_PER_MTOK
    p_out = float(meta.get("price_per_mtok_out", 0.0)) / _TOKENS_PER_MTOK
    return RunRecord(
        method="frontier",
        method_params=MethodParams(
            model=meta.get("model_id", adapter_mistral.DEFAULT_MODEL),
            max_tokens=tokens_out,
            extra={"recovered_from_raw": True},
        ),
        resource_use=ResourceUse(
            wall_s=wall_s,
            cost_usd=tokens_in * p_in + tokens_out * p_out,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        ),
        result_summary=ResultSummary(status="ok"),
        agent_family=adapter_mistral.AGENT_FAMILY,
        agent_mode=agent_mode,
        finish_reason="stop",
    )


def run_mistral_call(
    prompt: str,
    *,
    cap_usd: float,
    agent_mode: str,
    raw_output_path: Path,
    max_tokens: int,
    continuation: dict | None = None,
    extra_metadata: dict | None = None,
    system_prompt: str | None = None,
) -> RunRecord:
    """Single Mistral Agents call, with the registry-driven model metadata.

    Wraps ``adapter_mistral.run()`` with a recovery path for the case where
    ``parse_response`` raises on an unexpected content shape (str-content
    bug is fixed on main via PR #394 but defense in depth stays). The
    ``continuation`` and ``extra_metadata`` kwargs were added to the four
    SOTA adapters in PR #396 (ticket 0208); we forward them. The
    ``system_prompt`` kwarg (ticket 0213) is forwarded as the agent
    ``description`` at multi-turn-start or single-turn create time;
    follow-up turns must pass ``None`` (the adapter raises otherwise).
    """
    meta = load_model_meta("mistral")
    t0 = time.monotonic()
    try:
        return adapter_mistral.run(
            prompt,
            dry_run=False,
            model_meta=meta,
            max_tokens=max_tokens,
            cap_usd=cap_usd,
            agent_mode=agent_mode,
            output_path=raw_output_path,
            continuation=continuation,
            extra_metadata=extra_metadata,
            system_prompt=system_prompt,
        )
    except AttributeError as exc:
        if not raw_output_path.exists():
            raise
        wall_s = round(time.monotonic() - t0, 3)
        log.warning(
            "adapter_mistral.parse_response failed (%s); rebuilding RunRecord from raw artefact.",
            exc,
        )
        return _runrecord_from_raw(raw_output_path, meta, agent_mode=agent_mode, wall_s=wall_s)


def run_openai_call(
    prompt: str,
    *,
    cap_usd: float,
    agent_mode: str,
    raw_output_path: Path,
    max_tokens: int,
    continuation: dict | None = None,
    extra_metadata: dict | None = None,
    system_prompt: str | None = None,
) -> RunRecord:
    """Single OpenAI Responses call with continuation chaining for multi-turn.

    Continuation shape: ``{"response_id": str}``. On follow-up turns the SDK
    receives ``previous_response_id``, which restores server-side state.
    The ``system_prompt`` becomes ``instructions=`` on turn 1 only —
    follow-up turns inherit it via the chained response.

    Cost accounting per Doc 02 CONTEXT > Budget: ``tokens_out +
    thinking_tokens`` count against the 50K token cap; ``cost_usd``
    against the $3 dollar guard. OpenAI bundles web_search billing into
    reasoning/output tokens for gpt-5.x (see :mod:`aedist.adapter_openai_responses`),
    so there is no separate ``tool_calls_cost_usd`` bucket for this provider.

    Hard cap enforcement mirrors :func:`adapter_openai_responses.run`'s
    defense-in-depth pattern: pre-call cost estimate against ``cap_usd``,
    then a post-call recheck of the billed cost.
    """
    from openai import OpenAI

    from aedist import adapter_openai_responses
    from aedist.adapter_base import enforce_cost_cap, estimate_call_cost

    meta = load_model_meta("openai")
    is_followup = bool(continuation and continuation.get("response_id"))

    payload = adapter_openai_responses.build_request(
        prompt,
        model=meta.get("model_id"),
        max_output_tokens=max_tokens,
        reasoning_effort="low",  # web_search rejects "minimal"; "low" is the docs floor
    )
    if system_prompt and not is_followup:
        payload["instructions"] = system_prompt
    if is_followup:
        payload["previous_response_id"] = continuation["response_id"]
    if extra_metadata is not None:
        payload["metadata"] = {k: str(v) for k, v in extra_metadata.items()}

    # Pre-call cap check (estimate). Mirrors adapter_openai_responses.run
    # so single-turn callers and multi-turn dispatch enforce the same ceiling.
    p_in = meta.get("price_per_mtok_in_fresh", meta.get("price_per_mtok_in", 0.0)) / 1_000_000
    p_out = meta.get("price_per_mtok_out", 0.0) / 1_000_000
    estimated = estimate_call_cost(max_tokens=max_tokens, price_in=p_in, price_out=p_out)
    enforce_cost_cap(estimated, cap_usd=cap_usd)

    client = OpenAI(api_key=adapter_openai_responses._load_openai_key())
    t0 = time.monotonic()
    resp = client.responses.create(**payload)
    wall = round(time.monotonic() - t0, 3)

    raw_output_path.write_text(resp.model_dump_json(indent=2) + "\n", encoding="utf-8")

    record = adapter_openai_responses.parse_response(resp, meta)
    record.agent_mode = agent_mode
    record.resource_use.wall_s = wall
    # Post-call cap recheck (actual). Catches estimate-vs-billed drift.
    enforce_cost_cap(record.resource_use.cost_usd or 0.0, cap_usd=cap_usd)
    return record


def _slide_followup_cache_breakpoint(messages: list[dict]) -> list[dict]:
    """Breakpoint 3 (ticket 0369): cache the replayed conversation prefix.

    Wraps the LAST assistant message in the replayed history with
    ``cache_control: ephemeral`` so the whole prefix up to and including
    that reply is the cache key for this turn. Any cache_control left on
    *earlier* assistant messages by previous turns is stripped first — the
    breakpoint slides forward each turn (Anthropic matches the longest
    cached prefix, so sliding does not invalidate earlier cache segments,
    and stripping keeps us within the 4-breakpoints-per-request limit:
    system [1] + turn-1 user [2] + this slide [3]).

    No token-minimum guard is needed on this workload: the prefix always
    contains the ~200K-token turn-1 user message (evidence pack), far
    above the 4096-token Opus cache minimum; an under-minimum breakpoint
    would in any case be silently ignored by the API at zero cost.
    """
    out: list[dict] = []
    last_assistant_idx = None
    for i, msg in enumerate(messages):
        if msg.get("role") == "assistant":
            last_assistant_idx = i
        out.append(msg)
    for i, msg in enumerate(out):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        if i == last_assistant_idx:
            if isinstance(content, str):
                out[i] = {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": content,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                }
        elif isinstance(content, list):
            # Strip the wrap a previous turn's slide left behind.
            out[i] = {
                "role": "assistant",
                "content": [
                    {k: v for k, v in block.items() if k != "cache_control"}
                    if isinstance(block, dict)
                    else block
                    for block in content
                ],
            }
    return out


def run_anthropic_call(
    prompt: str,
    *,
    cap_usd: float,
    agent_mode: str,
    raw_output_path: Path,
    max_tokens: int,
    continuation: dict | None = None,
    extra_metadata: dict | None = None,
    system_prompt: str | None = None,
) -> RunRecord:
    """Single Anthropic Messages call with full-history resend for multi-turn.

    Continuation shape: ``{"messages": list[dict]}`` — the complete
    conversation history including each prior assistant reply. Anthropic
    is stateless on the wire; the client resends everything each call.
    The ``system_prompt`` MUST be passed as identical bytes on every
    turn (server does NOT persist it across calls; absence on a
    follow-up turn changes model behaviour).

    Cost accounting: ``cost_usd`` excludes ``web_search`` server-tool
    fees, which go into ``tool_calls_cost_usd``. The dual-axis budget
    cap then deducts the full session bill via :func:`total_cost`.
    ``tokens_out`` includes any thinking output (Anthropic reports it
    bundled in the output count).
    """
    import anthropic

    from aedist import query_anthropic
    from aedist.adapter_base import enforce_cost_cap, estimate_call_cost

    meta = load_model_meta("anthropic")
    model_id = meta.get("model_id")
    is_followup = bool(continuation and continuation.get("messages"))

    payload = query_anthropic.assemble_request(
        prompt,
        model=model_id,
        max_tokens=max_tokens,
        max_uses=3,
    )
    if system_prompt:
        # Breakpoint 1: cache the system prompt (~4700 tokens) so turns 2+
        # and cross-rep Turn-1 calls pay cache-read rate (~$0.50/MTok) not
        # $5/MTok.  Exceeds the 4096-token minimum for Opus 4.6.
        payload["system"] = [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]
    if not is_followup and payload.get("messages"):
        # Breakpoint 2: cache Turn-1 user message (the designed_prompt).
        # Identical across all reps — within-rep turns 2+ cache-hit on
        # system + designed_prompt (~5000 tokens total); cross-rep Turn-1
        # calls also hit fully when reps are spaced within the 5-min TTL.
        turn1 = payload["messages"][-1]
        if isinstance(turn1.get("content"), str):
            payload["messages"][-1] = {
                "role": turn1["role"],
                "content": [
                    {
                        "type": "text",
                        "text": turn1["content"],
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            }
    if is_followup:
        new_user_msg = payload["messages"][-1]
        payload["messages"] = _slide_followup_cache_breakpoint(
            list(continuation["messages"])
        ) + [new_user_msg]
    if extra_metadata is not None:
        # Anthropic metadata only accepts ``user_id``; all other keys are
        # rejected with a 400.  Drop silently — budget info is already in
        # the status-line prefix of the user message.
        user_id = extra_metadata.get("user_id")
        if user_id:
            payload["metadata"] = {"user_id": str(user_id)}

    # Pre-call cap. n_searches uses the provisioned ``max_uses=3`` as the
    # conservative ceiling; the post-call recheck below tightens against
    # actual web_search invocations.
    p_in = float(meta.get("price_per_mtok_in", 0.0)) / _TOKENS_PER_MTOK
    p_out = float(meta.get("price_per_mtok_out", 0.0)) / _TOKENS_PER_MTOK
    p_search = float(meta.get("price_per_web_search", 0.01))
    estimated = estimate_call_cost(
        max_tokens=max_tokens,
        price_in=p_in,
        price_out=p_out,
        n_searches=3,
        price_per_search=p_search,
    )
    enforce_cost_cap(estimated, cap_usd=cap_usd)

    api_key = query_anthropic._load_key()
    client = anthropic.Anthropic(api_key=api_key)
    t0 = time.monotonic()
    resp = query_anthropic._call_with_retry(client, payload)
    wall = round(time.monotonic() - t0, 3)

    raw_output_path.write_text(
        json.dumps(query_anthropic._response_to_dict(resp), indent=2, default=str) + "\n",
        encoding="utf-8",
    )

    parsed = query_anthropic._parse_anthropic_response(resp)
    usage = query_anthropic._usage_dict(resp)
    breakdown = query_anthropic._compute_anthropic_cost(usage, meta, parsed["n_searches"])

    # Build conversation messages for the next turn (full history replay).
    continuation_messages = list(payload.get("messages", []))
    if parsed.get("text"):
        continuation_messages.append({"role": "assistant", "content": parsed["text"]})

    record = query_anthropic._record_from_parsed(
        parsed,
        model=model_id,
        cost_breakdown=breakdown,
        tokens_in=parsed["tokens_in"],
        tokens_out=parsed["tokens_out"],
        wall_s=wall,
        thinking_tokens=None,
        agent_mode=agent_mode,
        run_number=1,
        messages_for_continuation=continuation_messages,
    )
    # _record_from_parsed already populates ``record.tool_calls_cost_usd``
    # from ``cost_breakdown["web_search"]`` (see query_anthropic.py:381) —
    # no need to re-assign here. Surfacing it into total_cost() works
    # through that field.
    # Stash narrative so the classifier's record-first path skips raw-file parse.
    record.justification = {"output_text": parsed.get("text", "") or ""}
    # Post-call cap recheck (actual billed total). Defense in depth.
    enforce_cost_cap(float(breakdown.get("total", 0.0)), cap_usd=cap_usd)
    return record


def run_qwen_call(
    prompt: str,
    *,
    cap_usd: float,
    agent_mode: str,
    raw_output_path: Path,
    max_tokens: int,
    continuation: dict | None = None,
    extra_metadata: dict | None = None,
    system_prompt: str | None = None,
) -> RunRecord:
    """Single Qwen DashScope call with full-history resend for multi-turn.

    Continuation shape: ``{"messages": list[dict]}`` — complete conversation
    history including the leading system message (when present) and each
    assistant reply. DashScope is stateless on the wire; the client
    resends everything every call.

    ``system_prompt`` is injected as the first ``{"role": "system", ...}``
    message on turn 1; turn 2+ inherits it via the replayed history.
    """
    import dashscope

    from aedist import adapter_qwen_dashscope
    from aedist.adapter_base import enforce_cost_cap, estimate_call_cost

    meta = load_model_meta("qwen")
    model_id = meta.get("model_id")
    is_followup = bool(continuation and continuation.get("messages"))

    # Build the messages list: history + new user, or (turn 1) system + user.
    if is_followup:
        messages = list(continuation["messages"]) + [{"role": "user", "content": prompt}]
    else:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

    # Use the adapter's payload assembly, then override the messages list
    # with our explicit history (build_request consults ``continuation``
    # but stores only [user] without preserving an explicit system role).
    payload = adapter_qwen_dashscope.build_request(
        prompt,
        model=model_id,
        max_tokens=max_tokens,
        enable_thinking=True,  # capability default for the optimized arm
        enable_search=True,
    )
    payload["messages"] = messages
    if extra_metadata is not None:
        # DashScope lacks a metadata surface AND allows at most one
        # ``role=system`` entry. If one is already present (e.g. carried
        # by ``system_prompt`` or by the continuation), append the metadata
        # to its content; otherwise prepend a fresh system message.
        meta_text = "; ".join(f"{k}={v}" for k, v in extra_metadata.items())
        meta_line = f"\n[metadata] {meta_text}"
        if payload["messages"] and payload["messages"][0].get("role") == "system":
            payload["messages"][0] = {
                "role": "system",
                "content": payload["messages"][0].get("content", "") + meta_line,
            }
        else:
            payload["messages"] = [
                {"role": "system", "content": f"[metadata] {meta_text}"}
            ] + payload["messages"]

    # Pre-call cap.
    p_in = (
        float(meta.get("price_per_mtok_in", adapter_qwen_dashscope.DEFAULT_PRICE_PER_MTOK_IN))
        / _TOKENS_PER_MTOK
    )
    p_out = (
        float(meta.get("price_per_mtok_out", adapter_qwen_dashscope.DEFAULT_PRICE_PER_MTOK_OUT))
        / _TOKENS_PER_MTOK
    )
    p_search = float(
        meta.get(
            "price_per_web_search_call_usd",
            adapter_qwen_dashscope.DEFAULT_PRICE_PER_WEB_SEARCH_CALL_USD,
        )
    )
    estimated = estimate_call_cost(
        max_tokens=max_tokens,
        price_in=p_in,
        price_out=p_out,
        n_searches=5,
        price_per_search=p_search,
    )
    enforce_cost_cap(estimated, cap_usd=cap_usd)

    dashscope.api_key = adapter_qwen_dashscope._resolve_api_key()
    dashscope.base_http_api_url = adapter_qwen_dashscope.DEFAULT_BASE_URL
    t0 = time.monotonic()
    resp = dashscope.Generation.call(**payload)
    wall = round(time.monotonic() - t0, 3)

    raw_dump = adapter_qwen_dashscope._response_to_dict(resp)
    raw_output_path.write_text(json.dumps(raw_dump, indent=2, default=str) + "\n", encoding="utf-8")

    record = adapter_qwen_dashscope.parse_response(
        resp,
        model_meta=meta,
        prompt=prompt,
        max_tokens=max_tokens,
        wall_s=wall,
        enable_thinking=True,
        enable_search=True,
    )
    record.agent_mode = agent_mode

    # Extract narrative from the raw dump for the continuation + classifier paths.
    output = raw_dump.get("output") or {}
    choices = output.get("choices") or []
    narrative = (choices[0].get("message", {}).get("content")) if choices else None

    # Overwrite parse_response's [user, assistant]-only messages with the
    # complete history we just sent + the assistant reply. The CONTINUATION
    # extractor then consumes this on the next turn.
    extra = record.method_params.extra or {}
    full_history = list(messages)
    if narrative:
        full_history.append({"role": "assistant", "content": narrative})
    extra["messages"] = full_history
    record.method_params.extra = extra

    # Stash narrative so the classifier's record-first path skips raw-file parse.
    record.justification = {"output_text": narrative or ""}

    # Post-call cap recheck (actual billed total).
    enforce_cost_cap(record.resource_use.cost_usd or 0.0, cap_usd=cap_usd)
    return record


def total_cost(record: RunRecord) -> float:
    """Token cost + connector (web_search) cost."""
    return (record.resource_use.cost_usd or 0.0) + (record.tool_calls_cost_usd or 0.0)


# ---------------------------------------------------------------------------
# Multi-turn dialogue state machine (ticket 0214 policy)
# ---------------------------------------------------------------------------


def format_status_line(
    remaining_tokens: int,
    cap_tokens: int,
    remaining_usd: float,
    cap_usd: float,
    elapsed_s: float,
    verify_state: str = "pending",
) -> str:
    """The exact status-prefix string the harness puts on every Phase B user turn.

    Dual-axis budget (Doc 02 CONTEXT > Budget): 50K-token cap binds reasoning
    capacity; $3 dollar guard binds total bill. Both visible. ``verify_state``
    is one of "pending" / "on this turn" / "used".
    """
    return (
        f"Status: remaining {remaining_tokens / 1000:.1f}K of {cap_tokens // 1000}K tokens, "
        f"${remaining_usd:.2f} of ${cap_usd:.2f}. "
        f"Wall-clock elapsed {elapsed_s:.1f}s. "
        f"Verify {verify_state}."
    )


def _turn_artefact_paths(output_dir: Path, agent: str, turn: int) -> dict[str, Path]:
    """Per-turn artefact paths under output_dir.

    Five files per turn (ticket 0214 adds ``classification``):

    - ``.user.txt``         — exact bytes of the user-side message
    - ``.raw.json``         — raw provider response
    - ``.record.json``      — parsed RunRecord
    - ``.cost.json``        — cost / budget bookkeeping
    - ``.classification.json`` — classifier verdict + classifier cost
    """
    base = output_dir / f"{agent}_turn_{turn:02d}"
    return {
        "user": Path(str(base) + ".user.txt"),
        "raw": Path(str(base) + ".raw.json"),
        "record": Path(str(base) + ".record.json"),
        "cost": Path(str(base) + ".cost.json"),
        "classification": Path(str(base) + ".classification.json"),
    }


def _next_reply(
    *,
    verify_used: bool,
    encouragement_count: int,
    remaining_usd: float,
    cap_usd: float,
    remaining_tokens: int,
    cap_tokens: int,
    last_class: str,
) -> tuple[str, str, dict]:
    """Compute the next user-side reply slot and the updated state.

    Returns ``(reply_text, slot_name, state_delta)`` where ``slot_name``
    is one of ``"encourage"``, ``"verify"``, ``"terminal"``, or
    ``"stop"`` (no reply — accept response and exit), and
    ``state_delta`` carries the new values for the tracked variables.

    Transition rules (Doc 02 CONTEXT > Budget + Doc 04 §2.4):

    1. Dual-axis budget trigger: EITHER ``remaining_usd ≤ 20 % of cap_usd``
       OR ``remaining_tokens ≤ 20 % of cap_tokens`` → TERMINAL, regardless
       of class. Overrides everything else.
    2. ``last_class == "report"``:
       - If verify has not been used: VERIFY, set ``verify_used``,
         reset ``encouragement_count`` (so a later no_report cycle
         starts fresh — dead code under caller's "stop after verify
         response" rule, but harmless and matches the spec).
       - Else: STOP (the verify-round response is the polished one).
    3. ``last_class == "no_report"``:
       - The counter records the running tally of no_report
         responses seen so far. If that tally has reached
         ``MAX_ENCOURAGEMENTS`` (3), send TERMINAL — graceful exit
         after three consecutive no_reports. Otherwise send
         ENCOURAGE and bump the counter.
    """
    if (
        remaining_usd <= BUDGET_TRIGGER_FRAC * cap_usd
        or remaining_tokens <= BUDGET_TRIGGER_FRAC * cap_tokens
    ):
        return TERMINAL_REPLY, "terminal", {}

    if last_class == "report":
        if not verify_used:
            return (
                VERIFY_REPLY,
                "verify",
                {"verify_used": True, "encouragement_count": 0},
            )
        # Verify already spent; the next response is the polished one.
        return "", "stop", {}

    # last_class == "no_report"
    # 3-strike rule: count no_report observations; on the 3rd, send
    # TERMINAL on the next user turn. This is the test-anchored
    # interpretation of MAX_ENCOURAGEMENTS — the ticket §State machine
    # pseudocode reads ``count < 3 → encourage``, which would yield 3
    # encouragements + TERMINAL on turn 5; the caller's test scenario
    # ("turns 1–3 classified as no_report → TERMINAL on turn 4")
    # implies the counter increments first, then the bound is checked.
    new_count = encouragement_count + 1
    if new_count >= MAX_ENCOURAGEMENTS:
        return TERMINAL_REPLY, "terminal", {"encouragement_count": new_count}
    return ENCOURAGE_REPLY, "encourage", {"encouragement_count": new_count}


def _extract_narrative_from_raw_path(raw_path: Path) -> str:
    """Read a saved raw Mistral response and return the assistant narrative.

    Wraps the safe extractor so the classifier only sees the user-visible
    text. Returns ``""`` on any read or parse failure (the classifier's
    own defensive path will then return ``"no_report"``).
    """
    try:
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("Could not load raw artefact %s for classification: %s", raw_path, exc)
        return ""
    return extract_narrative_from_mistral_raw(raw)


def _narrative_from_record_or_raw(record: RunRecord, raw_path: Path) -> str:
    """Pull narrative from the RunRecord if present, else parse the raw artefact.

    OpenAI (and future Anthropic / Qwen) adapters populate
    ``record.justification["output_text"]`` with the assistant narrative.
    The Mistral adapter does not, so we fall back to re-reading the raw
    artefact and parsing it via :func:`extract_narrative_from_mistral_raw`.
    The dispatch path is provider-agnostic — only the data source differs.
    """
    just = record.justification or {}
    if isinstance(just, dict) and just.get("output_text"):
        return just["output_text"]
    return _extract_narrative_from_raw_path(raw_path)


# ---------------------------------------------------------------------------
# Per-provider dispatch tables (ticket 0234)
#
# Each adapter exposes one ``run_*_call`` with the unified signature and
# one continuation extractor that translates its ``record.method_params.extra``
# into the opaque ``continuation`` dict consumed on the next turn. The
# dispatcher routes purely by these tables and never introspects the
# continuation shape. Adding a new provider = three additions (call_fn,
# extractor, SYSTEM_PROMPT_PASSTHROUGH policy).
# ---------------------------------------------------------------------------


def _extract_mistral_continuation(record: RunRecord, current: dict | None) -> dict | None:
    """Mistral: persist agent_id across turns, refresh conversation_id."""
    extra = record.method_params.extra or {}
    cur = current or {}
    agent_id = cur.get("agent_id")
    if agent_id is None and extra.get("agent_id"):
        agent_id = str(extra["agent_id"])
    conv_id = extra.get("conversation_id")
    if conv_id and agent_id:
        return {"agent_id": agent_id, "conversation_id": conv_id}
    return current


def _extract_openai_continuation(record: RunRecord, current: dict | None) -> dict | None:
    """OpenAI: chain previous_response_id from the just-returned response."""
    extra = record.method_params.extra or {}
    if extra.get("response_id"):
        return {"response_id": str(extra["response_id"])}
    return current


def _extract_anthropic_continuation(record: RunRecord, current: dict | None) -> dict | None:
    """Anthropic: full conversation messages list (stateless API — client resends history)."""
    extra = record.method_params.extra or {}
    if extra.get("messages"):
        return {"messages": list(extra["messages"])}
    return current


def _extract_qwen_continuation(record: RunRecord, current: dict | None) -> dict | None:
    """Qwen: full conversation messages list (stateless DashScope — client resends history)."""
    extra = record.method_params.extra or {}
    if extra.get("messages"):
        return {"messages": list(extra["messages"])}
    return current


CALL_FNS = {
    "mistral": run_mistral_call,
    "openai": run_openai_call,
    "anthropic": run_anthropic_call,
    "qwen": run_qwen_call,
}

CONTINUATION_EXTRACTORS = {
    "mistral": _extract_mistral_continuation,
    "openai": _extract_openai_continuation,
    "anthropic": _extract_anthropic_continuation,
    "qwen": _extract_qwen_continuation,
}

# Should ``system_prompt`` be passed on follow-up turns (turn > 1)?
#  - mistral / openai: no — adapter raises (Mistral) or server-side state
#    inherits via previous_response_id (OpenAI).
#  - anthropic / qwen: yes — both APIs are stateless on the wire; the
#    client resends the full conversation history (including the system
#    message) every turn.
# Default: False (drop on follow-up).
SYSTEM_PROMPT_PASSTHROUGH = {
    "mistral": False,
    "openai": False,
    "anthropic": True,
    "qwen": True,
}


def run_phase_b_multiturn(
    designed_prompt: str,
    *,
    output_dir: Path,
    cap_usd: float,
    cap_tokens: int,
    initial_spent_usd: float,
    max_tokens: int,
    agent: str = "mistral",
    system_prompt: str | None = None,
) -> dict:
    """Run the Phase B dialogue as a state machine on a single agent.

    Policy: ticket 0214 (supersedes ticket 0207). After each assistant
    reply, the harness classifies the narrative as ``"report"`` or
    ``"no_report"`` via :func:`dialogue_classifier.classify_report` and
    selects the next user-side reply via :func:`_next_reply`:

    - ENCOURAGE (≤ 3 times before forcing TERMINAL)
    - VERIFY    (sent once after the first reply classified as report)
    - TERMINAL  (budget trigger, or encouragement-exhaustion graceful exit)

    Classifier cost is **harness overhead** — accumulated under
    ``total_classifier_cost_usd`` but never deducted from the SOTA
    agent's budget.

    Per ticket 0213, ``system_prompt`` is installed on the agent at
    creation time (turn 1 only). Follow-up turns must not re-send it —
    the agent is already created.

    Returns a dict with ``records``, ``turns``, ``total_spent_usd``,
    ``terminal_sent``, ``agent_id`` (for caller-side cleanup), and
    ``total_classifier_cost_usd``.
    """
    call_fn = CALL_FNS.get(agent)
    if call_fn is None:
        raise NotImplementedError(f"--agent {agent!r} not wired for multi-turn yet")

    remaining = cap_usd - initial_spent_usd
    remaining_tokens = cap_tokens
    elapsed_s = 0.0
    continuation: dict | None = {}  # empty dict = start multi-turn, keep Mistral agent alive
    terminal_sent = False
    records: list[RunRecord] = []
    verify_used = False
    encouragement_count = 0
    total_classifier_cost_usd = 0.0
    turn = 1
    # Client-side conversation log — agent-agnostic. Stateful APIs (Mistral,
    # OpenAI) do not resend history on each call, so this is the only locally
    # persisted copy of the full exchange. Updated and saved after every turn.
    conversation_history: list[dict] = []
    if system_prompt:
        conversation_history.append({"role": "system", "content": system_prompt})
    conversation_path = output_dir / f"{agent}_conversation.json"
    last_slot = "designed_prompt"
    pending_reply = ""  # populated after each turn's classification

    while True:
        if turn == 1:
            user_text = designed_prompt
        else:
            verify_state = (
                "on this turn" if last_slot == "verify" else "used" if verify_used else "pending"
            )
            status = format_status_line(
                remaining_tokens, cap_tokens, remaining, cap_usd, elapsed_s, verify_state
            )
            user_text = f"{status}\n\n{pending_reply}"

        paths = _turn_artefact_paths(output_dir, agent, turn)
        paths["user"].write_text(user_text, encoding="utf-8")
        log.info("Phase B turn %d → %s starting ...", turn, last_slot)

        extra_metadata: dict | None = {
            "remaining_tokens": str(remaining_tokens),
            "cap_tokens": str(cap_tokens),
            "remaining_usd": f"{remaining:.2f}",
            "cap_usd": f"{cap_usd:.2f}",
        }
        is_followup_turn = turn > 1
        # Per-provider quirks on follow-up turns:
        #  - Mistral 422s on body-level ``metadata`` against the append endpoint
        #    (ticket 0218); OpenAI accepts it but we drop for symmetry — the
        #    user-text status prefix already conveys the same info to the model.
        if is_followup_turn:
            extra_metadata = None
        # ``system_prompt`` on follow-up: drop unless the adapter requires
        # identical bytes every call (Anthropic, Qwen — see
        # ``SYSTEM_PROMPT_PASSTHROUGH``).
        turn_system_prompt = (
            system_prompt
            if not is_followup_turn or SYSTEM_PROMPT_PASSTHROUGH.get(agent, False)
            else None
        )

        record = call_fn(
            user_text,
            cap_usd=max(remaining, 0.01),  # adapter wants positive cap
            agent_mode="phase_b_run",
            raw_output_path=paths["raw"],
            max_tokens=max_tokens,
            continuation=continuation,
            extra_metadata=extra_metadata,
            system_prompt=turn_system_prompt,
        )
        records.append(record)

        spent_this_turn = total_cost(record)
        # Token cap (Doc 02 CONTEXT > Budget): visible output + thinking only.
        # Web_search / connector / document-fetch payload is retrieval, not
        # generation, and does not count toward the 50K cap.
        tokens_this_turn = (record.resource_use.tokens_out or 0) + (
            record.resource_use.thinking_tokens or 0
        )
        remaining -= spent_this_turn
        remaining_tokens -= tokens_this_turn
        elapsed_s += record.resource_use.wall_s or 0.0

        paths["record"].write_text(record.model_dump_json(indent=2) + "\n", encoding="utf-8")

        # Classify the assistant's response. Classifier cost is harness
        # overhead, tracked separately from the SOTA agent's spend.
        narrative = _narrative_from_record_or_raw(record, paths["raw"])
        conversation_history.append({"role": "user", "content": user_text})
        conversation_history.append({"role": "assistant", "content": narrative})
        conversation_path.write_text(
            json.dumps({"messages": conversation_history}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        cls_result = dialogue_classifier.classify_report(narrative)
        total_classifier_cost_usd += cls_result.classifier_cost_usd
        paths["classification"].write_text(
            json.dumps(dialogue_classifier.result_to_artefact_dict(cls_result), indent=2) + "\n",
            encoding="utf-8",
        )

        paths["cost"].write_text(
            json.dumps(
                {
                    "turn": turn,
                    "spent_usd": spent_this_turn,
                    "tokens_this_turn": tokens_this_turn,
                    "remaining_usd": remaining,
                    "remaining_tokens": remaining_tokens,
                    "cap_usd": cap_usd,
                    "cap_tokens": cap_tokens,
                    "elapsed_s": elapsed_s,
                    "is_terminal_reply": last_slot == "terminal",
                    "user_slot": last_slot,
                    "classification": cls_result.class_,
                    "classifier_cost_usd": cls_result.classifier_cost_usd,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        # Provider-specific continuation extraction (Mistral: agent_id +
        # conversation_id; OpenAI: previous_response_id; future Anthropic /
        # Qwen: their own shapes). Each extractor returns the opaque dict
        # the dispatcher will pass to ``call_fn`` on the next turn. The
        # dispatcher never introspects the continuation shape — see the
        # return value below for the only consumer-facing field
        # (``agent_id``) that is pulled out by canonical key.
        new_continuation = CONTINUATION_EXTRACTORS[agent](record, continuation)
        if new_continuation is not None:
            continuation = new_continuation

        log.info(
            "Phase B turn %d ← %s done: spent=$%.4f remaining=$%.4f tokens_out=%s "
            "remaining_tokens=%d web_search=%d class=%s%s",
            turn,
            last_slot,
            spent_this_turn,
            remaining,
            record.resource_use.tokens_out,
            remaining_tokens,
            len(record.web_search_calls or []),
            cls_result.class_,
            " [terminal reply was sent]" if terminal_sent and turn > 1 else "",
        )

        # If the terminal reply was sent on the previous iteration, this
        # accepted response is the last one. Stop now.
        if terminal_sent:
            break
        # If the verify reply was sent on the previous iteration, this
        # accepted response IS the polished one. Stop — never cycle
        # back to encouragement after the one-shot verify round.
        if last_slot == "verify":
            break
        if remaining <= 0 or remaining_tokens <= 0:
            log.warning(
                "Budget exhausted (usd=%.4f, tokens=%d) without terminal reply having fired; stopping.",
                remaining,
                remaining_tokens,
            )
            break
        if turn >= TURN_SAFETY_CAP:
            log.warning("Hit safety cap of %d turns; stopping.", TURN_SAFETY_CAP)
            break

        # Decide the next user-side reply based on the just-seen class.
        pending_reply, last_slot, state_delta = _next_reply(
            verify_used=verify_used,
            encouragement_count=encouragement_count,
            remaining_usd=remaining,
            cap_usd=cap_usd,
            remaining_tokens=remaining_tokens,
            cap_tokens=cap_tokens,
            last_class=cls_result.class_,
        )
        verify_used = state_delta.get("verify_used", verify_used)
        encouragement_count = state_delta.get("encouragement_count", encouragement_count)
        if last_slot == "stop":
            # Verify response already accepted; nothing more to send.
            break
        if last_slot == "terminal":
            terminal_sent = True
        turn += 1

    return {
        "records": records,
        "turns": turn,
        "total_spent_usd": cap_usd - remaining - initial_spent_usd,
        "total_tokens_used": cap_tokens - remaining_tokens,
        "terminal_sent": terminal_sent,
        # Mistral exposes ``agent_id`` for caller-side conversation cleanup;
        # other providers omit the key (None for OpenAI / Anthropic / Qwen).
        # The dispatcher pulls it by canonical name rather than tracking it
        # in a local variable — keeps the loop body provider-agnostic.
        "agent_id": (continuation or {}).get("agent_id"),
        "total_classifier_cost_usd": total_classifier_cost_usd,
    }


def _read_turn_field(output_dir: Path, agent: str, turns: int, field: str) -> list[str]:
    values: list[str] = []
    for turn in range(1, turns + 1):
        path = _turn_artefact_paths(output_dir, agent, turn)["cost"]
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        val = data.get(field)
        if isinstance(val, str):
            values.append(val)
    return values


def _count_markdown_table_rows(text: str) -> int:
    return count_best_table_rows(text)


def _estimate_inventory_rows(agent: str, phase_b: dict, output_dir: Path) -> int:
    records = phase_b.get("records", []) or []
    classes = _read_turn_field(output_dir, agent, phase_b.get("turns", 0), "classification")
    for idx, cls in enumerate(classes, start=1):
        if cls != "report":
            continue
        if idx > len(records):
            continue
        raw_path = _turn_artefact_paths(output_dir, agent, idx)["raw"]
        narrative = _narrative_from_record_or_raw(records[idx - 1], raw_path)
        rows = _count_markdown_table_rows(narrative)
        if rows > 0:
            return rows
    return 0


def _write_summary(output_dir: Path, per_agent: list[dict]) -> Path:

    agents_slug = "_".join(item["agent"] for item in per_agent)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%MZ")
    filename = f"summary_{ts}_{agents_slug}.md"

    total_cost = sum(float(item.get("total_cost_usd", 0.0)) for item in per_agent)
    lines = [
        "# Phase B-0 Summary",
        "",
        "| Agent | Status | Cost USD | Wall s | Turns | Class Trace | Inventory Rows |",
        "|---|---:|---:|---:|---:|---|---:|",
    ]
    lines.extend(
        "| {agent} | {status} | {cost:.4f} | {wall:.1f} | {turns} | {trace} | {rows} |".format(
            agent=item["agent"],
            status=item.get("status", "error"),
            cost=float(item.get("total_cost_usd", 0.0)),
            wall=float(item.get("wall_s", 0.0)),
            turns=int(item.get("turns", 0)),
            trace=item.get("class_trace", "n/a"),
            rows=int(item.get("inventory_rows", 0)),
        )
        for item in per_agent
    )
    lines.append("")
    lines.append(f"Total B-0 cost: ${total_cost:.4f}")
    path = output_dir / filename
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _run_one_agent(args: argparse.Namespace, agent: str) -> dict:
    run_tag = f"{agent}_run{args.run_number:02d}"
    agent_output_dir = args.output_dir / run_tag
    agent_output_dir.mkdir(parents=True, exist_ok=True)

    meta_prompt = assemble_meta_prompt(manifest_path=args.evidence_pack_manifest)
    meta_prompt_path = agent_output_dir / f"{agent}_meta_prompt.txt"
    meta_prompt_path.write_text(meta_prompt, encoding="utf-8")
    log.info(
        "Meta-prompt assembled for %s (%d chars) -> %s", agent, len(meta_prompt), meta_prompt_path
    )

    if args.dry_run:
        return {
            "agent": agent,
            "status": "dry-run",
            "total_cost_usd": 0.0,
            "wall_s": 0.0,
            "turns": 0,
            "class_trace": "n/a",
            "inventory_rows": 0,
        }

    reuse_dir = args.reuse_phase_a_from
    if reuse_dir is not None:
        # Reps 2–N: load the rep-1 Phase A design without calling the API.
        src_dir = reuse_dir / f"{agent}_run01"
        design_src = src_dir / f"{agent}_phase_a_design.json"
        if not design_src.exists():
            raise FileNotFoundError(f"--reuse-phase-a-from: design file not found: {design_src}")
        design = json.loads(design_src.read_text(encoding="utf-8"))
        for fname in (
            f"{agent}_phase_a.json",
            f"{agent}_phase_a.raw.json",
            f"{agent}_phase_a_design.json",
        ):
            src = src_dir / fname
            if src.exists():
                (agent_output_dir / fname).write_bytes(src.read_bytes())
        phase_a = RunRecord(
            method=Method.FRONTIER,
            method_params=MethodParams(model="reused-from-run01"),
            resource_use=ResourceUse(cost_usd=0.0, wall_s=0.0),
        )
        log.info("[%s] Phase A reused from %s (no API call)", agent, src_dir)
    else:
        wait_for_space(
            f"Phase A: send meta-prompt to {agent}. Cap ${args.budget_cap_phase_a:.2f}.",
            no_confirm=args.no_confirm,
        )
        phase_a_raw_path = agent_output_dir / f"{agent}_phase_a.raw.json"
        phase_a = CALL_FNS[agent](
            meta_prompt,
            cap_usd=args.budget_cap_phase_a,
            agent_mode="phase_a_design",
            raw_output_path=phase_a_raw_path,
            max_tokens=args.phase_a_max_tokens,
        )
        phase_a_path = agent_output_dir / f"{agent}_phase_a.json"
        phase_a_path.write_text(phase_a.model_dump_json(indent=2) + "\n", encoding="utf-8")

        narrative_a = _narrative_from_record_or_raw(phase_a, phase_a_raw_path)
        design = extract_phase_a_design(narrative_a)
        design_path = agent_output_dir / f"{agent}_phase_a_design.json"
        design_path.write_text(json.dumps(design, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.stop_after_phase_a:
        return {
            "agent": agent,
            "status": "phase-a-only",
            "total_cost_usd": total_cost(phase_a),
            "wall_s": float(phase_a.resource_use.wall_s or 0.0),
            "turns": 0,
            "class_trace": "n/a",
            "inventory_rows": 0,
        }

    wait_for_space(
        f"Phase B: multi-turn loop on {agent}. Dual cap "
        f"{PHASE_B_TOTAL_TOKEN_CAP // 1000}K tokens + ${args.budget_cap_phase_b:.2f}.",
        no_confirm=args.no_confirm,
    )
    designed_prompt_raw = design["designed_prompt"]
    designed_prompt = (
        designed_prompt_raw
        if isinstance(designed_prompt_raw, str)
        else json.dumps(designed_prompt_raw, indent=2, ensure_ascii=False)
    )
    designed_prompt = append_evidence_pack(designed_prompt, args.evidence_pack_manifest)
    requested_max_tokens = max(
        int(design.get("settings", {}).get("max_tokens") or args.phase_b_max_tokens),
        args.min_phase_b_max_tokens,
    )
    designed_system_prompt = design["system_prompt"]

    phase_b = run_phase_b_multiturn(
        designed_prompt,
        output_dir=agent_output_dir,
        cap_usd=args.budget_cap_phase_b,
        cap_tokens=PHASE_B_TOTAL_TOKEN_CAP,
        initial_spent_usd=0.0,
        max_tokens=requested_max_tokens,
        agent=agent,
        system_prompt=designed_system_prompt,
    )

    if agent == "mistral" and phase_b.get("agent_id"):
        try:
            adapter_mistral.cleanup_agent(phase_b["agent_id"])
            log.info("Cleaned up Mistral agent %s", phase_b["agent_id"])
        except Exception as exc:  # noqa: BLE001
            log.warning("Mistral agent cleanup failed: %s", exc)

    class_trace = _read_turn_field(agent_output_dir, agent, phase_b["turns"], "classification")
    inventory_rows = _estimate_inventory_rows(agent, phase_b, agent_output_dir)
    total_cost_usd = total_cost(phase_a) + float(phase_b["total_spent_usd"])
    wall_s = float(phase_a.resource_use.wall_s or 0.0) + sum(
        float(record.resource_use.wall_s or 0.0) for record in (phase_b.get("records") or [])
    )

    status = "pass"
    if not class_trace or "report" not in class_trace:
        status = "fail"
    if total_cost_usd > args.budget_cap_phase_b + args.budget_cap_phase_a:
        status = "fail"

    return {
        "agent": agent,
        "status": status,
        "total_cost_usd": total_cost_usd,
        "wall_s": wall_s,
        "turns": phase_b["turns"],
        "class_trace": ",".join(class_trace) if class_trace else "n/a",
        "inventory_rows": inventory_rows,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--agents",
        nargs="+",
        required=True,
        choices=sorted(FAMILY_BY_AGENT),
        help=(
            "One or more SOTA agents to smoke in Phase B-0. "
            "Example: --agents mistral qwen openai anthropic"
        ),
    )
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    p.add_argument("--no-confirm", action="store_true", help="Skip SPACE gates.")
    p.add_argument("--dry-run", action="store_true", help="Print meta-prompt and exit.")
    p.add_argument("--budget-cap-phase-a", type=float, default=1.0)
    p.add_argument("--budget-cap-phase-b", type=float, default=15.0)
    p.add_argument("--phase-a-max-tokens", type=int, default=8000)
    p.add_argument("--phase-b-max-tokens", type=int, default=12000)
    p.add_argument(
        "--min-phase-b-max-tokens",
        type=int,
        default=32000,
        help="Floor applied to Phase A's designed max_tokens for Phase B turns. "
        "Prevents low Phase A estimates from truncating multi-turn outputs.",
    )
    p.add_argument(
        "--stop-after-phase-a",
        action="store_true",
        help="Exit after Phase A artefacts land; do not call Phase B.",
    )
    p.add_argument(
        "--run-number",
        type=int,
        default=1,
        help="Rep number (1-indexed). Appended to the per-agent output subdir: "
        "<agent>_run{N:02d}. Default 1 keeps the B-0 layout (<agent>_run01).",
    )
    p.add_argument(
        "--reuse-phase-a-from",
        type=Path,
        default=None,
        metavar="DIR",
        help="Load Phase A design from DIR/<agent>_run01/ instead of calling the "
        "Phase A API. Use for reps 2–N to reuse the rep-1 design.",
    )
    p.add_argument(
        "--evidence-pack-manifest",
        type=str,
        default=None,
        metavar="YAML",
        help="Path to an evidence-pack manifest YAML (Arm 4). Injected into the Phase A "
        "meta-prompt and appended to the Phase B prompt. Omit for Arm 2 baseline.",
    )
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    per_agent: list[dict] = []
    for agent in args.agents:
        try:
            per_agent.append(_run_one_agent(args, agent))
        except Exception as exc:  # noqa: BLE001
            log.error("Agent %s failed during Phase B-0 smoke: %s", agent, exc)
            per_agent.append(
                {
                    "agent": agent,
                    "status": "error",
                    "total_cost_usd": 0.0,
                    "wall_s": 0.0,
                    "turns": 0,
                    "class_trace": "n/a",
                    "inventory_rows": 0,
                }
            )

    summary_path = _write_summary(args.output_dir, per_agent)
    (args.output_dir / "summary.json").write_text(
        json.dumps(per_agent, indent=2) + "\n", encoding="utf-8"
    )

    total_cost_usd = sum(float(item.get("total_cost_usd", 0.0)) for item in per_agent)
    log.info("Phase B-0 summary written -> %s", summary_path)
    if not args.dry_run and total_cost_usd > 10.0:
        raise SystemExit(f"Phase B-0 total cost ${total_cost_usd:.4f} exceeds $10.00 cap.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
