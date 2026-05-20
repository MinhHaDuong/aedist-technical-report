"""Anthropic Claude adapter — web_search tool + adaptive thinking.

Part of the SOTA frontier-API experiment (umbrella ticket 0166, ticket 0167).
This adapter is *transport only*; experimental prompt content lives in
Phase A (ticket 0170).

Capabilities composed in one call:
  - Extended (adaptive) thinking — `thinking={"type": "adaptive",
    "display": "summarized"}`. Manual `enabled + budget_tokens` is rejected
    by Claude Opus 4.6 / 4.7 — use the adaptive form.
  - Native `web_search_20250305` server tool — `tools=[{"type":
    "web_search_20250305", "name": "web_search", "max_uses": N}]`.
  - Long-form output via large `max_tokens`.

Model: pinned to ``claude-opus-4-6`` per user decision 2026-05-20. Do not
silently upgrade to 4.7 without re-verifying compose; both models accept
the request shape verified in the live probe of that date, but Anthropic's
point releases can diverge on tool surface.

Sources verified 2026-05-20 against live API + Anthropic docs:
  - Web search tool: https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/web-search-tool
  - Extended thinking: https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking
  - Pricing: https://www.anthropic.com/pricing (token rates) +
             https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/web-search-tool#pricing
             ($10 per 1,000 web_search requests → $0.010 per call).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from aedist.adapter_base import (
    CostCapExceeded,
    enforce_cost_cap,
    estimate_call_cost,
    format_dry_run,
)
from aedist.harness import BudgetTracker, load_models, output_path, save_json
from aedist.schema import (
    Method,
    MethodParams,
    ResourceUse,
    ResultSummary,
    RunRecord,
)

log = logging.getLogger(__name__)

AGENT_FAMILY = "anthropic-direct"
DEFAULT_MODEL = "claude-opus-4-6"
DEFAULT_MAX_TOKENS = 2048
DEFAULT_MAX_USES = 5
DEFAULT_PRICE_PER_WEB_SEARCH_USD = 0.010
TOKENS_PER_MTOK = 1_000_000
API_DOCS_VERIFIED = "2026-05-20"

# Path resolved at call time, never at import — `~` expansion + override-friendly.
DEFAULT_KEY_PATH = "~/.config/keys/anthropic.env"


# ---------------------------------------------------------------------------
# Key loading
# ---------------------------------------------------------------------------


def _load_key(path: str | os.PathLike = DEFAULT_KEY_PATH) -> str:
    """Read ANTHROPIC_API_KEY from a KEY=value env file.

    Lines starting with ``#`` and blank lines are ignored. Raises
    ``SystemExit`` (matching ``harness.make_client``) when the key cannot
    be found, so a missing key fails loudly at CLI exit.
    """
    p = Path(os.path.expanduser(str(path)))
    if not p.exists():
        raise SystemExit(f"Anthropic key file not found: {p}")
    for raw in p.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip() == "ANTHROPIC_API_KEY":
            return v.strip().strip('"').strip("'")
    raise SystemExit(f"ANTHROPIC_API_KEY not found in {p}")


# ---------------------------------------------------------------------------
# Request assembly
# ---------------------------------------------------------------------------


def assemble_request(
    user_message: str,
    model: str = DEFAULT_MODEL,
    *,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    max_uses: int = DEFAULT_MAX_USES,
) -> dict:
    """Return ``messages.create`` kwargs for one Anthropic agent call.

    Wires the three composed capabilities (adaptive thinking, native
    web_search, long-form output) in the exact shape verified on the live
    API on ``API_DOCS_VERIFIED``. The protocol surface for ticket 0170.
    """
    return {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": user_message}],
        "tools": [
            {
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": max_uses,
            }
        ],
        "tool_choice": {"type": "auto"},
        "thinking": {"type": "adaptive", "display": "summarized"},
    }


# Protocol-conformant alias so the 0170 adapter registry can introspect
# uniformly (sibling adapters 0168/0169/0173 implement ``build_request``).
def build_request(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    max_uses: int = DEFAULT_MAX_USES,
    **_: Any,
) -> dict:
    """Protocol alias for :func:`assemble_request`."""
    return assemble_request(prompt, model, max_tokens=max_tokens, max_uses=max_uses)


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Read a field from an object that may be a dict (fixture) or SDK model."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _block_type(block: Any) -> str:
    return _get(block, "type", "")


def _parse_anthropic_response(resp: Any) -> dict:
    """Walk ``resp.content`` and extract the canonical agent-record fields.

    Returns a dict with keys::

        text                — concatenated narrative from ``text`` blocks
        thinking_text       — concatenated summarised reasoning
        reasoning_summary   — same as thinking_text, kept for RunRecord parity
        web_search_calls    — one entry per ``server_tool_use`` block;
                              ``urls_returned`` collected from the matched
                              ``web_search_tool_result`` block (by tool_use_id)
        citations           — one entry per inline citation on text blocks
                              (richer signal than the search result URL list:
                              these are anchored to claims and carry
                              ``cited_text`` as the snippet)
        finish_reason       — ``resp.stop_reason``
        n_searches          — ``usage.server_tool_use.web_search_requests``
                              (authoritative count for billing)
        tokens_in           — ``usage.input_tokens``
        tokens_out          — ``usage.output_tokens``
        cache_read_tokens   — ``usage.cache_read_input_tokens``
        cache_write_tokens  — ``usage.cache_creation_input_tokens``
    """
    content = _get(resp, "content", []) or []

    text_parts: list[str] = []
    thinking_parts: list[str] = []
    citations: list[dict] = []
    server_tool_uses: dict[str, dict] = {}  # tool_use_id -> partial entry
    tool_results: dict[str, list[str]] = {}  # tool_use_id -> URLs

    for block in content:
        bt = _block_type(block)
        if bt == "thinking":
            t = _get(block, "thinking", "") or ""
            if t:
                thinking_parts.append(t)
        elif bt == "text":
            txt = _get(block, "text", "") or ""
            if txt:
                text_parts.append(txt)
            citations.extend(
                {
                    "url": _get(cit, "url"),
                    "snippet": _get(cit, "cited_text"),
                    "supports_claim": None,
                }
                for cit in _get(block, "citations", []) or []
            )
        elif bt == "server_tool_use":
            tu_id = _get(block, "id", "")
            query = _get(_get(block, "input", {}) or {}, "query")
            server_tool_uses[tu_id] = {"query": query, "urls_returned": []}
        elif bt == "web_search_tool_result":
            tu_id = _get(block, "tool_use_id", "")
            urls: list[str] = []
            wsr_content = _get(block, "content", []) or []
            # `content` may be a list of result dicts or an error envelope
            if isinstance(wsr_content, list):
                for item in wsr_content:
                    url = _get(item, "url")
                    if url:
                        urls.append(url)
            tool_results[tu_id] = urls

    # Stitch tool_use → tool_result by id; preserve server_tool_use order.
    web_search_calls: list[dict] = []
    for tu_id, entry in server_tool_uses.items():
        entry["urls_returned"] = tool_results.get(tu_id, [])
        web_search_calls.append(entry)

    usage = _get(resp, "usage", {}) or {}
    stu = _get(usage, "server_tool_use", {}) or {}
    n_searches = _get(stu, "web_search_requests", 0) or 0

    thinking_text = "\n\n".join(thinking_parts)
    return {
        "text": "".join(text_parts),
        "thinking_text": thinking_text,
        "reasoning_summary": thinking_text or None,
        "web_search_calls": web_search_calls,
        "citations": citations,
        "finish_reason": _get(resp, "stop_reason"),
        "n_searches": int(n_searches),
        "tokens_in": int(_get(usage, "input_tokens", 0) or 0),
        "tokens_out": int(_get(usage, "output_tokens", 0) or 0),
        "cache_read_tokens": int(_get(usage, "cache_read_input_tokens", 0) or 0),
        "cache_write_tokens": int(_get(usage, "cache_creation_input_tokens", 0) or 0),
    }


# ---------------------------------------------------------------------------
# Cost
# ---------------------------------------------------------------------------


def _compute_anthropic_cost(usage: dict, model: dict, n_searches: int) -> dict:
    """Compute USD cost from Anthropic ``usage`` and the model price card.

    Returns a dict with keys ``total``, ``input``, ``output``, ``cache_read``,
    ``cache_write``, ``web_search``. All values are USD. Kept adapter-local
    because Anthropic's ``input_tokens`` / ``output_tokens`` shape is
    incompatible with :func:`aedist.harness.compute_cost`, which is hardcoded
    to OpenRouter's ``prompt_tokens`` / ``completion_tokens`` shape.
    """
    price_in = float(model.get("price_per_mtok_in", 0.0))
    price_out = float(model.get("price_per_mtok_out", 0.0))
    price_cache_read = float(
        model.get("price_per_mtok_cache_read", model.get("price_per_mtok_in", 0.0))
    )
    price_cache_write = float(
        model.get("price_per_mtok_cache_write", model.get("price_per_mtok_in", 0.0))
    )
    price_per_search = float(model.get("price_per_web_search", DEFAULT_PRICE_PER_WEB_SEARCH_USD))

    input_tokens = int(usage.get("input_tokens", 0) or 0)
    output_tokens = int(usage.get("output_tokens", 0) or 0)
    cache_read = int(usage.get("cache_read_input_tokens", 0) or 0)
    cache_write = int(usage.get("cache_creation_input_tokens", 0) or 0)

    input_cost = input_tokens * price_in / TOKENS_PER_MTOK
    output_cost = output_tokens * price_out / TOKENS_PER_MTOK
    cache_read_cost = cache_read * price_cache_read / TOKENS_PER_MTOK
    cache_write_cost = cache_write * price_cache_write / TOKENS_PER_MTOK
    search_cost = n_searches * price_per_search

    total = input_cost + output_cost + cache_read_cost + cache_write_cost + search_cost
    return {
        "total": total,
        "input": input_cost,
        "output": output_cost,
        "cache_read": cache_read_cost,
        "cache_write": cache_write_cost,
        "web_search": search_cost,
    }


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def _usage_dict(resp: Any) -> dict:
    """Return a plain dict view of ``resp.usage`` (SDK model or fixture dict)."""
    usage = _get(resp, "usage", {}) or {}
    if isinstance(usage, dict):
        # Normalise nested server_tool_use (also possibly a model on the SDK).
        stu = usage.get("server_tool_use")
        if stu is not None and not isinstance(stu, dict):
            usage = {
                **usage,
                "server_tool_use": {"web_search_requests": _get(stu, "web_search_requests", 0)},
            }
        return usage
    # Pydantic-like SDK object — best-effort .model_dump(), fallback to attrs.
    if hasattr(usage, "model_dump"):
        return usage.model_dump()
    return {
        "input_tokens": _get(usage, "input_tokens", 0),
        "output_tokens": _get(usage, "output_tokens", 0),
        "cache_creation_input_tokens": _get(usage, "cache_creation_input_tokens", 0),
        "cache_read_input_tokens": _get(usage, "cache_read_input_tokens", 0),
        "server_tool_use": {
            "web_search_requests": _get(
                _get(usage, "server_tool_use", {}) or {}, "web_search_requests", 0
            )
        },
    }


def _record_from_parsed(
    parsed: dict,
    *,
    model: str,
    cost_breakdown: dict,
    tokens_in: int,
    tokens_out: int,
    wall_s: float,
    thinking_tokens: int | None,
    agent_mode: str,
    run_number: int,
    parsed_table_path: str | None = None,
    error: str | None = None,
) -> RunRecord:
    """Build a RunRecord from a parsed Anthropic response."""
    total_cost = float(cost_breakdown.get("total", 0.0))
    token_cost = total_cost - float(cost_breakdown.get("web_search", 0.0))
    tool_calls_cost = float(cost_breakdown.get("web_search", 0.0))
    breakdown_for_record = {
        k: v
        for k, v in cost_breakdown.items()
        if k in {"input", "output", "cache_read", "cache_write"} and v
    }
    return RunRecord(
        method=Method.FRONTIER,
        method_params=MethodParams(
            model=model,
            extra={"run_number": run_number},
        ),
        resource_use=ResourceUse(
            wall_s=wall_s,
            cost_usd=token_cost,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_breakdown=breakdown_for_record or None,
            thinking_tokens=thinking_tokens,
        ),
        result_summary=ResultSummary(status="ok" if not error else "error"),
        agent_family=AGENT_FAMILY,
        agent_mode=agent_mode,
        web_search_calls=parsed.get("web_search_calls") or None,
        citations=parsed.get("citations") or None,
        parsed_table_path=parsed_table_path,
        finish_reason=parsed.get("finish_reason"),
        retry_count=0,
        error=error,
        reasoning_summary=parsed.get("reasoning_summary"),
        tool_calls_cost_usd=tool_calls_cost if tool_calls_cost else None,
    )


def dispatch(
    payload: dict,
    model: dict,
    *,
    dry_run: bool,
    output_dir: Path,
    run: int = 1,
    agent_mode: str = "smoke",
    budget: BudgetTracker | None = None,
    cap_usd: float = 0.50,
    key_path: str | os.PathLike = DEFAULT_KEY_PATH,
) -> dict:
    """Execute one Anthropic agent call (or print a dry-run payload).

    Returns a dict with keys ``run_record`` (RunRecord), ``raw_response``
    (provider response or ``None`` on dry-run), and ``output_path`` (Path
    when persisted, ``None`` on dry-run). The 0170-facing entry point.

    ``cap_usd`` is enforced both pre-call (against the conservative upper
    bound from :func:`aedist.adapter_base.estimate_call_cost`) and
    post-call (against actual billed amount).
    """
    model_id = model["model_id"]
    max_tokens = int(payload.get("max_tokens", DEFAULT_MAX_TOKENS))
    max_uses = int(
        next(
            (
                int(t.get("max_uses", DEFAULT_MAX_USES))
                for t in payload.get("tools", [])
                if t.get("type") == "web_search_20250305"
            ),
            DEFAULT_MAX_USES,
        )
    )

    # Pre-call cap.
    estimated = estimate_call_cost(
        max_tokens=max_tokens,
        price_in=float(model.get("price_per_mtok_in", 0.0)) / TOKENS_PER_MTOK,
        price_out=float(model.get("price_per_mtok_out", 0.0)) / TOKENS_PER_MTOK,
        n_searches=max_uses,
        price_per_search=float(
            model.get("price_per_web_search", DEFAULT_PRICE_PER_WEB_SEARCH_USD)
        ),
    )
    enforce_cost_cap(estimated, cap_usd=cap_usd)

    if dry_run:
        print(format_dry_run(payload))
        return {"run_record": None, "raw_response": None, "output_path": None}

    # Live call — import the SDK lazily so dry-run + tests stay import-light.
    import anthropic

    api_key = _load_key(key_path)
    client = anthropic.Anthropic(api_key=api_key)

    t0 = time.monotonic()
    resp = client.messages.create(**payload)
    wall_s = round(time.monotonic() - t0, 3)

    parsed = _parse_anthropic_response(resp)
    usage = _usage_dict(resp)
    breakdown = _compute_anthropic_cost(usage, model, parsed["n_searches"])

    # Post-call cap verification.
    if breakdown["total"] > cap_usd:
        log.warning(
            "Post-call cost ${:.4f} exceeded cap ${:.2f} — call already billed.".format(
                breakdown["total"], cap_usd
            )
        )

    if budget is not None:
        budget.add(breakdown["total"])

    record = _record_from_parsed(
        parsed,
        model=model_id,
        cost_breakdown=breakdown,
        tokens_in=parsed["tokens_in"],
        tokens_out=parsed["tokens_out"],
        wall_s=wall_s,
        thinking_tokens=None,  # Anthropic reports total output incl. thinking.
        agent_mode=agent_mode,
        run_number=run,
    )

    # Persist as one self-contained JSON: record + raw response + parsed view.
    out_path = output_path(output_dir, model_id, run, prefix=AGENT_FAMILY)
    raw_dump = _response_to_dict(resp)
    save_json(
        out_path,
        {
            "run_record": json.loads(record.to_jsonl_line()),
            "parsed": {
                "text": parsed["text"],
                "n_searches": parsed["n_searches"],
                "n_citations": len(parsed["citations"]),
                "n_web_search_calls": len(parsed["web_search_calls"]),
                "reasoning_summary": parsed["reasoning_summary"],
            },
            "raw_response": raw_dump,
            "cost_breakdown": breakdown,
        },
    )

    return {"run_record": record, "raw_response": resp, "output_path": out_path}


def _response_to_dict(resp: Any) -> dict:
    """Best-effort serialisation of the Anthropic SDK response to a dict."""
    if isinstance(resp, dict):
        return resp
    if hasattr(resp, "model_dump"):
        return resp.model_dump()
    # Last resort — string repr, never raise.
    return {"repr": repr(resp)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m aedist.query_anthropic",
        description="Anthropic Claude adapter (web_search + adaptive thinking).",
    )
    p.add_argument(
        "--prompt",
        default="List 3 coal power plants in Vietnam with one citation each, ≤200 words",
        help="User prompt (default: smoke prompt from ticket 0167).",
    )
    p.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Anthropic model id (default: {DEFAULT_MODEL}).",
    )
    p.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help=f"Max output tokens (default: {DEFAULT_MAX_TOKENS}).",
    )
    p.add_argument(
        "--max-uses",
        type=int,
        default=3,
        help="Max web_search calls per request (default: 3).",
    )
    p.add_argument(
        "--cap-usd",
        type=float,
        default=0.50,
        help="Hard per-call cost cap, USD (default: 0.50).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print assembled payload and exit; no API call.",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("experiments/outputs/sota_smoke"),
        help="Directory for the run JSON.",
    )
    p.add_argument(
        "--models-file",
        type=Path,
        default=Path("experiments/models.yaml"),
        help="Model registry YAML.",
    )
    p.add_argument(
        "--agent-mode",
        default="smoke",
        choices=["smoke", "probe", "phase_a_design", "phase_b_run", "phase_c_score"],
        help="RunRecord agent_mode label.",
    )
    p.add_argument(
        "--run",
        type=int,
        default=1,
        help="Run number (used in the output filename).",
    )
    p.add_argument(
        "--key-path",
        default=DEFAULT_KEY_PATH,
        help=f"Path to anthropic.env (default: {DEFAULT_KEY_PATH}).",
    )
    return p


def _find_model(models: list[dict], model_id: str) -> dict:
    """Locate the matching ``anthropic-direct`` entry by ``model_id``."""
    for m in models:
        if m.get("model_id") == model_id and m.get("family") == AGENT_FAMILY:
            return m
    raise SystemExit(
        f"No '{AGENT_FAMILY}' entry with model_id={model_id!r} in registry. "
        f"Check experiments/models.yaml."
    )


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _build_arg_parser().parse_args(argv)

    models = load_models(str(args.models_file))
    model = _find_model(models, args.model)

    payload = assemble_request(
        args.prompt,
        args.model,
        max_tokens=args.max_tokens,
        max_uses=args.max_uses,
    )

    try:
        result = dispatch(
            payload,
            model,
            dry_run=args.dry_run,
            output_dir=args.output_dir,
            run=args.run,
            agent_mode=args.agent_mode,
            cap_usd=args.cap_usd,
            key_path=args.key_path,
        )
    except CostCapExceeded as e:
        print(f"ERROR: {e}", flush=True)
        return 2

    if args.dry_run:
        return 0

    rec = result["run_record"]
    print(
        json.dumps(
            {
                "run_id": rec.run_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "uuid_seed": uuid4().hex[:8],  # diagnostic only
                "cost_usd_total": (rec.resource_use.cost_usd or 0.0)
                + (rec.tool_calls_cost_usd or 0.0),
                "cost_breakdown": rec.resource_use.cost_breakdown,
                "n_web_search_calls": len(rec.web_search_calls or []),
                "n_citations": len(rec.citations or []),
                "output_path": str(result["output_path"]),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
