"""Qwen3-Max adapter via Alibaba DashScope (ticket 0173).

Fourth SOTA-agent slot under umbrella 0166 — adds CN-corpus search
diversity to the Anthropic/OpenAI Western baselines and the Mistral EU
slot.

Capability compose target: thinking mode + server-side web search in a
single API call, with citations and reasoning trace surfaced in the
response.

Reference: Alibaba Cloud Model Studio documentation
  https://www.alibabacloud.com/help/en/model-studio/web-search
  https://www.alibabacloud.com/help/en/model-studio/deep-thinking
API shape verified empirically against ``qwen3-max-2026-01-23`` on the
international endpoint (dashscope-intl.aliyuncs.com) on 2026-05-20 —
see ticket 0173 log entry of the same date.

SDK choice: the official ``dashscope`` Python SDK. The
OpenAI-compatible endpoint at
``https://dashscope-intl.aliyuncs.com/compatible-mode/v1`` exists but
historically lags on tool-call schema fidelity (per ticket
0173 / 0166 raid plans).

Critical: do NOT pass ``tools=[{"type": "web_search"}]``. That triggers
OpenAI-style **client-side** function calling — the server returns a
``tool_call`` requesting that *we* execute the search and reply with a
``tool`` message. For server-side execution with citations in the same
response, set ``enable_search=True`` and pass ``search_options``.
"""

from __future__ import annotations

import logging
import os
import random
import time
from pathlib import Path
from typing import Any

import dashscope

from aedist.adapter_base import (
    enforce_cost_cap,
    estimate_call_cost,
    format_dry_run,
)
from aedist.schema import MethodParams, ResourceUse, ResultSummary, RunRecord

_log = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RATE_LIMIT_WAIT_S = 60.0
_TRANSIENT_BACKOFF_S = 1.0
_RETRYABLE_TRANSIENT = frozenset({502, 503, 504})


def _call_with_retry(**payload: Any) -> Any:
    """Wrap dashscope.Generation.call with retry on 429 and transient errors."""
    for attempt in range(_MAX_RETRIES + 1):
        resp = dashscope.Generation.call(**payload)
        status = getattr(resp, "status_code", 200)
        if status == 200:
            return resp
        if status == 429 and attempt < _MAX_RETRIES:
            wait = _RATE_LIMIT_WAIT_S * (1.0 + random.uniform(-0.1, 0.1))
            _log.warning(
                "Qwen 429 rate limit; retry %d/%d in %.0fs", attempt + 1, _MAX_RETRIES, wait
            )
            time.sleep(wait)
            continue
        if status in _RETRYABLE_TRANSIENT and attempt < _MAX_RETRIES:
            delay = _TRANSIENT_BACKOFF_S * (2**attempt) * (1.0 + random.uniform(-0.1, 0.1))
            _log.warning("Qwen HTTP %d transient; retry %d/%d", status, attempt + 1, _MAX_RETRIES)
            time.sleep(delay)
            continue
        return resp
    return resp  # unreachable


AGENT_FAMILY = "qwen-direct"
DEFAULT_MODEL = "qwen3-max-2026-01-23"
API_DOCS_VERIFIED = "2026-05-20"

# International endpoint (default). Mainland routing is out of scope per
# ticket 0173 — price and latency differ; pin explicitly to avoid silent
# regional drift.
DEFAULT_BASE_URL = "https://dashscope-intl.aliyuncs.com/api/v1"

# Default international price card for qwen3-max-2026-01-23. Source:
# Alibaba Cloud Model Studio pricing page, verified 2026-05-20. Override
# via ``model_meta`` at parse time so models.yaml remains the single
# source of truth for batch runs.
DEFAULT_PRICE_PER_MTOK_IN = 1.2
DEFAULT_PRICE_PER_MTOK_OUT = 6.0
DEFAULT_PRICE_PER_MTOK_REASONING = 6.0
DEFAULT_PRICE_PER_WEB_SEARCH_CALL_USD = 0.010

# Hard cap per call — ticket 0173 / 0187 alignment with sibling adapters
# (adapter_openai_responses.DEFAULT_COST_CAP_USD, adapter_mistral.run cap_usd).
# Previously 0.50 (drift): smoke happens to stay under that, but the cap is a
# guardrail separate from the canonical smoke prompt/max_tokens choice.
DEFAULT_COST_CAP_USD = 10.0


def build_request(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 800,
    enable_thinking: bool = True,
    enable_search: bool = True,
    search_options: dict | None = None,
    continuation: dict | None = None,
) -> dict:
    """Assemble the DashScope ``Generation.call`` kwargs.

    The returned dict is consumed in two ways:
    - ``--dry-run`` prints it via :func:`format_dry_run`.
    - Live mode splats it into ``dashscope.Generation.call(**payload)``.

    Multi-turn (ticket 0208): when ``continuation`` is provided with a
    ``messages`` key, those messages are prepended to the new user
    message to form the full conversation history.

    Important: this function intentionally never sets a ``tools`` key.
    Setting it would activate client-side function calling and break
    the server-side search contract. See module docstring.
    """
    if search_options is None:
        search_options = {
            "enable_source": True,
            "enable_citation": True,
            "citation_format": "[<number>]",
        }
    # Build messages: prepend history from continuation if present.
    if continuation is not None and continuation.get("messages"):
        messages = list(continuation["messages"]) + [{"role": "user", "content": prompt}]
    else:
        messages = [{"role": "user", "content": prompt}]
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "enable_thinking": enable_thinking,
        "enable_search": enable_search,
        "search_options": search_options,
        "result_format": "message",
        "max_tokens": max_tokens,
    }
    return payload


def _response_to_dict(resp: Any) -> dict:
    """Normalize a DashScope response (object or dict) to a plain dict.

    The SDK returns a ``GenerationResponse`` object whose nested fields
    are addressable via attribute access. Tests and on-disk fixtures
    use plain dicts. Treat both the same downstream.
    """
    if isinstance(resp, dict):
        return resp
    # DashScope responses expose ``.output``, ``.usage`` etc. as nested
    # ``DictMixin`` instances. The simplest path to a plain dict is the
    # SDK's own serializer.
    if hasattr(resp, "__dict__"):
        # ``GenerationResponse`` carries data under ``.output`` /
        # ``.usage`` / ``.request_id`` / ``.status_code``.
        out: dict[str, Any] = {}
        for key in ("output", "usage", "request_id", "status_code"):
            val = getattr(resp, key, None)
            if val is None:
                continue
            out[key] = val if isinstance(val, (str, int, float, bool)) else _deep_to_dict(val)
        return out
    raise TypeError(f"Cannot normalize response of type {type(resp).__name__}")


def _deep_to_dict(obj: Any) -> Any:
    """Recursively convert DashScope ``DictMixin`` nodes to plain dicts."""
    if isinstance(obj, dict):
        return {k: _deep_to_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_to_dict(v) for v in obj]
    if hasattr(obj, "items") and callable(obj.items):
        return {k: _deep_to_dict(v) for k, v in obj.items()}
    return obj


def parse_response(
    resp: Any,
    model_meta: dict | None = None,
    *,
    prompt: str | None = None,
    max_tokens: int | None = None,
    wall_s: float | None = None,
    enable_thinking: bool = True,
    enable_search: bool = True,
) -> RunRecord:
    """Convert a DashScope response into a canonical ``RunRecord``.

    Mapping (verified 2026-05-20):
    - ``output.choices[0].message.content`` → narrative (not stored
      directly on RunRecord; lives in the raw response artifact).
    - ``output.choices[0].message.reasoning_content`` → ``reasoning_summary``.
    - ``output.search_info.search_results[]`` → ``citations``. Each
      entry preserves ``url``, ``title``, ``site_name``, and the
      server-assigned ``index`` for cross-reference to inline ``[N]``
      markers in the narrative.
    - ``usage.plugins.search.count`` → length of ``web_search_calls``.
      DashScope does NOT surface per-query attribution; ``search_results``
      is flat across all searches in the call. We therefore record
      ``count`` placeholder entries with ``query=None`` and
      ``urls_returned=[]`` so the schema list length matches the
      server's reported search count. Citations carry the URL set.
    - ``usage.output_tokens_details.reasoning_tokens`` → ``thinking_tokens``.
    """
    data = _response_to_dict(resp)
    meta = model_meta or {}

    output = data.get("output", {}) or {}
    usage = data.get("usage", {}) or {}

    choices = output.get("choices") or []
    message: dict[str, Any] = choices[0].get("message", {}) if choices else {}
    narrative = message.get("content")
    reasoning = message.get("reasoning_content")
    finish_reason = choices[0].get("finish_reason") if choices else None

    search_info = output.get("search_info") or {}
    raw_results = search_info.get("search_results") or []
    citations = [
        {
            "url": r.get("url"),
            "title": r.get("title"),
            "site_name": r.get("site_name"),
            "index": r.get("index"),
            "snippet": None,
            "supports_claim": None,
        }
        for r in raw_results
    ]

    plugins = usage.get("plugins") or {}
    search_block = plugins.get("search") or {}
    search_count = int(search_block.get("count") or 0)
    web_search_calls = [{"query": None, "urls_returned": []} for _ in range(search_count)] or None

    tokens_in = usage.get("input_tokens")
    tokens_out = usage.get("output_tokens")
    details = usage.get("output_tokens_details") or {}
    reasoning_tokens = details.get("reasoning_tokens")

    # Price card: prefer model_meta, fall back to documented defaults.
    price_in = float(meta.get("price_per_mtok_in", DEFAULT_PRICE_PER_MTOK_IN))
    price_out = float(meta.get("price_per_mtok_out", DEFAULT_PRICE_PER_MTOK_OUT))
    price_reasoning = float(meta.get("price_per_mtok_reasoning", price_out))
    price_per_search = float(
        meta.get("price_per_web_search_call_usd", DEFAULT_PRICE_PER_WEB_SEARCH_CALL_USD)
    )

    token_cost = 0.0
    if tokens_in is not None:
        token_cost += (tokens_in / 1_000_000.0) * price_in
    # Output tokens already include reasoning tokens in DashScope's
    # accounting; bill reasoning at its own rate (often equal to output)
    # and the visible-only output at the output rate.
    visible_out = tokens_out
    if tokens_out is not None and reasoning_tokens is not None:
        visible_out = max(0, tokens_out - reasoning_tokens)
    if visible_out is not None:
        token_cost += (visible_out / 1_000_000.0) * price_out
    if reasoning_tokens is not None:
        token_cost += (reasoning_tokens / 1_000_000.0) * price_reasoning

    tool_calls_cost = search_count * price_per_search

    cost_breakdown: dict[str, float] = {}
    if tokens_in is not None:
        cost_breakdown["input"] = round((tokens_in / 1_000_000.0) * price_in, 6)
    if visible_out is not None:
        cost_breakdown["output"] = round((visible_out / 1_000_000.0) * price_out, 6)
    if reasoning_tokens is not None:
        cost_breakdown["reasoning"] = round((reasoning_tokens / 1_000_000.0) * price_reasoning, 6)

    record = RunRecord(
        method="frontier",
        method_params=MethodParams(
            model=meta.get("model_id", DEFAULT_MODEL),
            max_tokens=max_tokens,
            extra={
                "enable_thinking": enable_thinking,
                "enable_search": enable_search,
                "endpoint": meta.get("base_url", DEFAULT_BASE_URL),
                "prompt_preview": (prompt or "")[:200] if prompt else None,
            },
        ),
        resource_use=ResourceUse(
            wall_s=wall_s,
            cost_usd=round(token_cost, 6),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_breakdown=cost_breakdown or None,
            thinking_tokens=reasoning_tokens,
        ),
        result_summary=ResultSummary(status="ok"),
        agent_family=AGENT_FAMILY,
        agent_mode=meta.get("agent_mode", "smoke"),
        web_search_calls=web_search_calls,
        citations=citations or None,
        finish_reason=finish_reason,
        reasoning_summary=reasoning,
        tool_calls_cost_usd=round(tool_calls_cost, 6) if search_count else None,
    )
    # Stash the narrative on the extras for downstream tabulation. Lives
    # in method_params.extra rather than as a top-level field because
    # RunRecord has no narrative slot today; the raw response file
    # remains the canonical record.
    if narrative is not None and record.method_params.extra is not None:
        record.method_params.extra["narrative_preview"] = narrative[:200]
        # Multi-turn continuation (ticket 0208): include the conversation
        # messages so the harness can replay history on the next turn.
        record.method_params.extra["messages"] = [
            {"role": "user", "content": prompt or ""},
            {"role": "assistant", "content": narrative},
        ]
    return record


def _resolve_api_key() -> str:
    """Resolve the DashScope API key, preferring the project key file.

    Order: environment ``QWEN_API_KEY_AEDIST``, then
    ``~/.config/keys/alibaba.env`` (KEY=VALUE format).
    """
    env_key = os.environ.get("QWEN_API_KEY_AEDIST")
    if env_key:
        return env_key
    key_file = Path.home() / ".config" / "keys" / "alibaba.env"
    if key_file.exists():
        for line in key_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == "QWEN_API_KEY_AEDIST":
                return v.strip().strip('"').strip("'")
    raise RuntimeError(
        "QWEN_API_KEY_AEDIST not found in environment or ~/.config/keys/alibaba.env"
    )


def run(
    prompt: str,
    *,
    dry_run: bool,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 800,
    enable_thinking: bool = True,
    enable_search: bool = True,
    model_meta: dict | None = None,
    cost_cap_usd: float = DEFAULT_COST_CAP_USD,
    base_url: str = DEFAULT_BASE_URL,
    continuation: dict | None = None,
    extra_metadata: dict | None = None,
) -> RunRecord:
    """Execute one DashScope call (or print the dry-run payload).

    Multi-turn (ticket 0208): ``continuation`` with a ``messages`` key
    prepends conversation history. ``extra_metadata`` is prepended as
    a system-message budget reminder (DashScope lacks a metadata surface).
    """
    payload = build_request(
        prompt,
        model=model,
        max_tokens=max_tokens,
        enable_thinking=enable_thinking,
        enable_search=enable_search,
        continuation=continuation,
    )
    # DashScope lacks a metadata surface. Prepend a system message as a
    # practical fallback so the model sees budget information.
    if extra_metadata is not None:
        meta_text = "; ".join(f"{k}={v}" for k, v in extra_metadata.items())
        payload["messages"].insert(0, {"role": "system", "content": f"[metadata] {meta_text}"})
        _log.info(
            "Qwen: injected extra_metadata as system message (DashScope has no metadata surface)"
        )

    # Pre-call cap: assume worst-case token billing + a small per-call
    # search budget (n_searches is unknown until the response lands).
    estimated = estimate_call_cost(
        max_tokens=max_tokens,
        price_in=DEFAULT_PRICE_PER_MTOK_IN / 1_000_000.0,
        price_out=DEFAULT_PRICE_PER_MTOK_OUT / 1_000_000.0,
        n_searches=5,
        price_per_search=DEFAULT_PRICE_PER_WEB_SEARCH_CALL_USD,
    )
    enforce_cost_cap(estimated, cap_usd=cost_cap_usd)

    if dry_run:
        # Side-effect: print so an operator running `--dry-run` sees the
        # exact payload. Return an empty stub record so callers needn't
        # special-case dry-run.
        print(format_dry_run(payload))  # noqa: T201 — operator-facing
        return RunRecord(
            method="frontier",
            method_params=MethodParams(model=model, max_tokens=max_tokens),
            agent_family=AGENT_FAMILY,
            agent_mode="dry_run",
        )

    dashscope.api_key = _resolve_api_key()
    dashscope.base_http_api_url = base_url

    start = time.perf_counter()
    resp = _call_with_retry(**payload)
    wall_s = time.perf_counter() - start

    return parse_response(
        resp,
        model_meta=model_meta,
        prompt=prompt,
        max_tokens=max_tokens,
        wall_s=wall_s,
        enable_thinking=enable_thinking,
        enable_search=enable_search,
    )
