"""OpenAI Responses API adapter — web_search + reasoning (ticket 0168).

Part of the SOTA frontier-API experiment (umbrella 0166). Wires
OpenAI's GPT-5.5 as one of the SOTA agents.

Why a sibling, not a graft onto ``harness.query_single_turn``:
  The Responses API returns a heterogeneous ``output[]`` mixing
  ``reasoning | web_search_call | message`` items. Flattening it into the
  chat-completions shape would corrupt the 23 callers of the legacy path.

API surface (verified 2026-05-20, OpenAI Responses API docs:
    https://platform.openai.com/docs/api-reference/responses
):
  * Tool name is ``web_search`` (NOT ``web_search_preview`` — that preview
    alias was removed).
  * ``include=["web_search_call.action.sources"]`` is MANDATORY on the
    request. Without it the response's ``web_search_call.action`` carries
    only the ``query`` and ``output_text.annotations`` stays empty — URLs
    are silently lost.
  * ``reasoning={"effort": "high"}`` is supported; ``summary`` items are
    typically empty even at ``effort=high, summary=detailed``. Use
    ``usage.output_tokens_details.reasoning_tokens`` as the
    reasoning-magnitude signal. ``RunRecord.reasoning_summary`` will
    typically be ``None`` for this adapter — that is correct.
  * Response shape: ``resp.output[]`` is a list whose items are
    distinguished by ``.type``:
      - ``"reasoning"``: ``summary`` (often empty list)
      - ``"web_search_call"``: ``action.query``, ``action.sources[]``
        where each source has ``.url``
      - ``"message"``: ``content[*].output_text`` is narrative; do NOT
        rely on ``content[*].annotations`` for citations.
  * ``usage.input_tokens`` / ``output_tokens``;
    ``output_tokens_details.reasoning_tokens`` for thinking tokens;
    ``input_tokens_details.cached_tokens`` for prompt-cache accounting.
"""

import argparse
import json
import logging
import os
import random  # used by _sleep_with_backoff
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aedist.adapter_base import (
    enforce_cost_cap,
    estimate_call_cost,
    format_dry_run,
)
from aedist.schema import Method, MethodParams, ResourceUse, ResultSummary, RunRecord

log = logging.getLogger(__name__)

AGENT_FAMILY = "openai-direct"
DEFAULT_MODEL = "gpt-5.5"
API_DOCS_VERIFIED = "2026-05-20"

# The magic include= directive without which URLs vanish.
WEB_SEARCH_SOURCES_INCLUDE = "web_search_call.action.sources"

# Cap for the smoke and dry-run paths. Other callers may override via the
# ``max_output_tokens`` argument.
DEFAULT_MAX_OUTPUT_TOKENS = 2000
SMOKE_COST_CAP_USD = 0.50

# Hard cap per call — ticket 0168 Action 4 (umbrella 0166).
# Enforced pre-call from the conservative estimate (max_tokens billed at both
# input + output rates) and verified post-call against the actual cost.
DEFAULT_COST_CAP_USD = 10.0

# ---------------------------------------------------------------------------
# Retry policy for transient / rate-limit failures (ticket 0244).
# Mirrors the Mistral adapter pattern: 3 retries, 1s/2s/4s exponential
# backoff ±10% jitter. Retry on 429, 5xx, connection errors only.
# ---------------------------------------------------------------------------
_MAX_RETRIES = 3
_BACKOFF_BASE_S = 1.0


def _sleep_with_backoff(attempt: int) -> None:
    delay = _BACKOFF_BASE_S * (2**attempt) * (1.0 + random.uniform(-0.1, 0.1))
    time.sleep(delay)


def _call_with_retry(client: Any, payload: dict) -> Any:
    import openai

    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            return client.responses.create(**payload)
        except openai.RateLimitError as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES:
                log.warning("OpenAI 429 rate limit; retry %d/%d", attempt + 1, _MAX_RETRIES)
                _sleep_with_backoff(attempt)
                continue
            raise
        except openai.APIStatusError as exc:
            if exc.status_code >= 500:
                last_exc = exc
                if attempt < _MAX_RETRIES:
                    log.warning(
                        "OpenAI HTTP %d transient; retry %d/%d",
                        exc.status_code,
                        attempt + 1,
                        _MAX_RETRIES,
                    )
                    _sleep_with_backoff(attempt)
                    continue
                raise
            raise
        except openai.APIConnectionError as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES:
                log.warning(
                    "OpenAI connection error (%s); retry %d/%d",
                    type(exc).__name__,
                    attempt + 1,
                    _MAX_RETRIES,
                )
                _sleep_with_backoff(attempt)
                continue
            raise
    assert last_exc is not None
    raise last_exc


# ---------------------------------------------------------------------------
# Request assembly
# ---------------------------------------------------------------------------


def build_request(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    reasoning_effort: str = "high",
) -> dict:
    """Assemble the kwargs dict for ``client.responses.create(**payload)``.

    Returns the kwargs exactly as they will be passed to the SDK. The
    ``include`` directive is non-negotiable — see module docstring.
    """
    return {
        "model": model,
        "input": prompt,
        "tools": [{"type": "web_search"}],
        "reasoning": {"effort": reasoning_effort},
        "include": [WEB_SEARCH_SOURCES_INCLUDE],
        "max_output_tokens": max_output_tokens,
    }


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def _get(obj: Any, attr: str, default: Any = None) -> Any:
    """Read ``attr`` from a SimpleNamespace-like object OR a dict.

    The SDK returns attribute-access objects in production; fixtures may
    be loaded as plain dicts. This helper smooths over both without
    forcing the caller to convert.
    """
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def _extract_text(message_item: Any) -> str:
    """Join all ``output_text`` blocks within a message item."""
    content = _get(message_item, "content", []) or []
    parts: list[str] = []
    for block in content:
        if _get(block, "type") == "output_text":
            text = _get(block, "text", "")
            if text:
                parts.append(text)
    return "\n".join(parts)


def _extract_reasoning_summary(reasoning_item: Any) -> str | None:
    """Join all summary chunks within a reasoning item, or None if empty.

    Empirically (2026-05-20 against gpt-5.5) ``summary`` is an empty list
    even at ``effort=high, summary=detailed`` — so this returns ``None``
    in the live path. The implementation is present for forward-compat in
    case OpenAI begins surfacing summaries later.
    """
    summary = _get(reasoning_item, "summary", []) or []
    chunks: list[str] = []
    for chunk in summary:
        text = _get(chunk, "text") or _get(chunk, "content")
        if isinstance(text, str) and text:
            chunks.append(text)
    if not chunks:
        return None
    return "\n".join(chunks)


def _compute_cost(usage: Any, price_card: dict) -> tuple[float, dict]:
    """Compute USD cost from a Responses-API usage object + a price card.

    Price card keys (all $/Mtok):
      - price_per_mtok_in_fresh
      - price_per_mtok_in_cached
      - price_per_mtok_out
      - price_per_mtok_reasoning  (optional — defaults to price_per_mtok_out)

    OpenAI bundles web_search billing into reasoning/output tokens for the
    Responses API on gpt-5.x; there is no separate per-search line, so we
    do NOT add one here. If that changes, add a ``price_per_websearch_call``
    bucket in the same shape used by the Mistral/Qwen adapters.
    """
    input_tokens = _get(usage, "input_tokens", 0) or 0
    output_tokens = _get(usage, "output_tokens", 0) or 0
    cached = _get(_get(usage, "input_tokens_details"), "cached_tokens", 0) or 0
    reasoning_tokens = _get(_get(usage, "output_tokens_details"), "reasoning_tokens", 0) or 0

    fresh_in = max(input_tokens - cached, 0)

    p_fresh = price_card.get("price_per_mtok_in_fresh", 0.0)
    p_cached = price_card.get(
        "price_per_mtok_in_cached", price_card.get("price_per_mtok_in_fresh", 0.0)
    )
    p_out = price_card.get("price_per_mtok_out", 0.0)
    p_reasoning = price_card.get("price_per_mtok_reasoning", p_out)

    cost_input = (fresh_in * p_fresh) / 1_000_000
    cost_cached = (cached * p_cached) / 1_000_000
    cost_output = (output_tokens * p_out) / 1_000_000
    cost_reasoning = (reasoning_tokens * p_reasoning) / 1_000_000

    total = cost_input + cost_cached + cost_output + cost_reasoning

    breakdown = {
        "input": round(cost_input, 8),
        "cached": round(cost_cached, 8),
        "output": round(cost_output, 8),
        "reasoning": round(cost_reasoning, 8),
    }
    return total, breakdown


def parse_response(resp: Any, price_card: dict) -> RunRecord:
    """Convert a Responses-API ``resp`` into a canonical ``RunRecord``.

    Walks ``resp.output[]`` once, dispatching on ``.type``:

      * ``reasoning``       → reasoning_summary (often None)
      * ``web_search_call`` → web_search_calls + flattened citations
      * ``message``         → narrative output_text
    """
    output_items = _get(resp, "output", []) or []
    model_id = _get(resp, "model", DEFAULT_MODEL)
    finish_reason = _get(resp, "status")

    narrative_parts: list[str] = []
    web_search_calls: list[dict] = []
    citations: list[dict] = []
    reasoning_summary: str | None = None

    for item in output_items:
        item_type = _get(item, "type")
        if item_type == "reasoning":
            if reasoning_summary is None:
                reasoning_summary = _extract_reasoning_summary(item)
        elif item_type == "web_search_call":
            action = _get(item, "action")
            query = _get(action, "query", "")
            sources = _get(action, "sources", []) or []
            urls: list[str] = []
            for src in sources:
                url = _get(src, "url")
                if not url:
                    continue
                urls.append(url)
                citations.append({"url": url, "snippet": None, "supports_claim": None})
            web_search_calls.append({"query": query, "urls_returned": urls})
        elif item_type == "message":
            narrative_parts.append(_extract_text(item))

    narrative = "\n\n".join(p for p in narrative_parts if p)

    usage = _get(resp, "usage")
    cost_usd, cost_breakdown = _compute_cost(usage, price_card)

    input_tokens = _get(usage, "input_tokens", 0) or 0
    output_tokens = _get(usage, "output_tokens", 0) or 0
    reasoning_tokens = _get(_get(usage, "output_tokens_details"), "reasoning_tokens", 0) or 0

    response_id = _get(resp, "id")
    record = RunRecord(
        method=Method.FRONTIER,
        method_params=MethodParams(
            model=model_id,
            extra={"response_id": response_id},
        ),
        agent_family=AGENT_FAMILY,
        resource_use=ResourceUse(
            cost_usd=cost_usd,
            tokens_in=input_tokens,
            tokens_out=output_tokens,
            thinking_tokens=reasoning_tokens,
            cost_breakdown=cost_breakdown,
        ),
        result_summary=ResultSummary(
            status="ok" if narrative else "empty",
        ),
        web_search_calls=web_search_calls,
        citations=citations,
        reasoning_summary=reasoning_summary,
        finish_reason=finish_reason,
    )
    # Attach the narrative as a justification payload so the smoke runner
    # can persist it alongside the structured record without inventing a
    # new schema field.
    record.justification = {"output_text": narrative}
    return record


# ---------------------------------------------------------------------------
# Live-call entry point
# ---------------------------------------------------------------------------


def _load_openai_key() -> str:
    """Load OpenAI key from env or ``~/.config/keys/openai.env``.

    Accepts only the project key ``OPENAI_API_KEY_AEDIST``.
    """
    key = os.environ.get("OPENAI_API_KEY_AEDIST")
    if key:
        return key
    env_file = Path.home() / ".config" / "keys" / "openai.env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                if k.strip() == "OPENAI_API_KEY_AEDIST":
                    return v.strip().strip('"').strip("'")
    raise SystemExit(
        "OpenAI key not set (expected OPENAI_API_KEY_AEDIST) "
        "and not found in ~/.config/keys/openai.env"
    )


# Default price card for gpt-5.5 — pending official verification on
# OpenAI's price page; mirrors the published gpt-5.4 rates as a
# conservative placeholder. Update in experiments/models.yaml once
# the gpt-5.5 page is consulted.
DEFAULT_PRICE_CARD: dict = {
    "price_per_mtok_in_fresh": 2.5,
    "price_per_mtok_in_cached": 0.625,
    "price_per_mtok_out": 15.0,
    "price_per_mtok_reasoning": 15.0,
}


def run(
    prompt: str,
    *,
    dry_run: bool,
    model: str = DEFAULT_MODEL,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    reasoning_effort: str = "high",
    price_card: dict | None = None,
    cap_usd: float = DEFAULT_COST_CAP_USD,
    continuation: dict | None = None,
    extra_metadata: dict | None = None,
) -> RunRecord:
    """Execute one OpenAI Responses call (or dry-run) and return a RunRecord.

    Enforces a hard per-call cost cap (ticket 0168 Action 4):
      * **Pre-call**: ``estimate_call_cost`` against ``max_output_tokens`` and
        the input/output rates from ``price_card``; raises ``CostCapExceeded``
        before the HTTP call when the estimate exceeds ``cap_usd``.
      * **Post-call**: re-checks ``record.resource_use.cost_usd`` against
        ``cap_usd``; raises ``CostCapExceeded`` if the actual billed cost
        breached it (defence in depth against estimate drift).

    Multi-turn chaining (ticket 0208):
      * ``continuation=None`` → new conversation (current behavior).
      * ``continuation={"response_id": "resp_..."}`` → passes
        ``previous_response_id`` to the SDK to chain responses.
      * ``extra_metadata`` → passed as the ``metadata`` dict on the SDK
        call. Values must be strings (OpenAI constraint); the caller is
        responsible for stringifying.
    """
    payload = build_request(
        prompt,
        model=model,
        max_output_tokens=max_output_tokens,
        reasoning_effort=reasoning_effort,
    )
    pc = price_card if price_card is not None else DEFAULT_PRICE_CARD
    # Prices in the card are $/Mtok; estimate_call_cost expects $/token.
    p_in = pc.get("price_per_mtok_in_fresh", pc.get("price_per_mtok_in", 0.0)) / 1_000_000
    p_out = pc.get("price_per_mtok_out", 0.0) / 1_000_000
    estimated = estimate_call_cost(
        max_tokens=max_output_tokens,
        price_in=p_in,
        price_out=p_out,
    )
    enforce_cost_cap(estimated, cap_usd=cap_usd)

    # Wire continuation and metadata into the SDK payload.
    if continuation is not None and continuation.get("response_id"):
        payload["previous_response_id"] = continuation["response_id"]
    if extra_metadata is not None:
        payload["metadata"] = {k: str(v) for k, v in extra_metadata.items()}

    if dry_run:
        print(format_dry_run(payload))
        return RunRecord(
            method=Method.FRONTIER,
            method_params=MethodParams(model=model),
            agent_family=AGENT_FAMILY,
            agent_mode="smoke",
            result_summary=ResultSummary(status="qualitative"),
        )

    from openai import OpenAI

    client = OpenAI(api_key=_load_openai_key(), max_retries=0)
    t0 = time.monotonic()
    resp = _call_with_retry(client, payload)
    wall = round(time.monotonic() - t0, 3)

    record = parse_response(resp, pc)
    record.resource_use.wall_s = wall
    record.agent_mode = "smoke"
    # Defence in depth: actual cost must also respect the cap.
    enforce_cost_cap(record.resource_use.cost_usd or 0.0, cap_usd=cap_usd)
    return record


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _serialise_resp(resp: Any) -> dict:
    """Best-effort JSON dict of the raw SDK response, for the smoke artifact."""
    try:
        return resp.model_dump()  # pydantic v2 path on the SDK side
    except AttributeError:
        pass
    try:
        return json.loads(resp.model_dump_json())
    except AttributeError:
        pass
    try:
        return dict(resp)  # last-ditch — rarely hits
    except Exception:
        return {"_warning": "could not serialise raw response", "_type": type(resp).__name__}


def _smoke(args: argparse.Namespace) -> None:
    prompt = "List 3 coal power plants in Vietnam with one citation each, ≤200 words"
    payload = build_request(
        prompt,
        model=args.model,
        max_output_tokens=args.max_output_tokens,
        reasoning_effort=args.reasoning_effort,
    )

    from openai import OpenAI

    client = OpenAI(api_key=_load_openai_key(), max_retries=0)
    t0 = time.monotonic()
    resp = _call_with_retry(client, payload)
    wall = round(time.monotonic() - t0, 3)

    record = parse_response(resp, DEFAULT_PRICE_CARD)
    record.resource_use.wall_s = wall
    record.agent_mode = "smoke"

    cost = record.resource_use.cost_usd or 0.0
    if cost > SMOKE_COST_CAP_USD:
        log.warning("Smoke cost $%.4f exceeded cap $%.2f", cost, SMOKE_COST_CAP_USD)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%MZ")
    artifact_path = out_dir / f"openai_{timestamp}.json"
    payload_dict = {
        "record": json.loads(record.model_dump_json()),
        "request": payload,
        "raw_response": _serialise_resp(resp),
    }
    with open(artifact_path, "w") as f:
        json.dump(payload_dict, f, indent=2, ensure_ascii=False, default=str)
        f.write("\n")

    n_searches = len(record.web_search_calls or [])
    n_citations = len(record.citations or [])
    print(
        f"Smoke complete: cost=${cost:.4f} wall={wall}s "
        f"searches={n_searches} citations={n_citations}"
    )
    print(f"Saved: {artifact_path}")
    if n_searches < 1:
        log.warning("Smoke produced no web_search_call entries")
    if n_citations < 1:
        log.warning("Smoke produced no citations — check the include= directive was applied")


def _dry_run(args: argparse.Namespace) -> None:
    prompt = args.prompt or (
        "List 3 coal power plants in Vietnam with one citation each, ≤200 words"
    )
    payload = build_request(
        prompt,
        model=args.model,
        max_output_tokens=args.max_output_tokens,
        reasoning_effort=args.reasoning_effort,
    )
    print(format_dry_run(payload))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="OpenAI Responses adapter — web_search + reasoning (ticket 0168)",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-output-tokens", type=int, default=DEFAULT_MAX_OUTPUT_TOKENS)
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the assembled request payload and exit (no network call).",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Execute one real call and save the artifact under --output-dir.",
    )
    parser.add_argument("--prompt", default=None, help="Override prompt for --dry-run.")
    parser.add_argument(
        "--output-dir",
        default="experiments/outputs/sota_smoke",
        help="Where to save the --smoke artifact.",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if args.smoke:
        _smoke(args)
    else:
        _dry_run(args)


if __name__ == "__main__":
    main()
