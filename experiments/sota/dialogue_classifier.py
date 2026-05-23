"""LLM-driven classifier for Phase B dialogue control (ticket 0214).

Single-purpose helper: given the assistant's narrative reply, decide
whether it materially delivered an *inventory report* (table + sources
+ narrative — at least one of those, materially) or *did not* (planning,
clarification, refusal, partial intermediate). The result steers the
Phase B state machine (`exp2_interactive_smoke.run_phase_b_multiturn`).

Design notes:

- One-shot ``POST /v1/chat/completions`` via OpenRouter, targeting
  nvidia/nemotron-nano-9b-v2 — an open-weight model unaffiliated with
  any of the four Exp 2 subject vendors. Keeps overhead well under
  $0.001 per classification on 8 KiB inputs.
- Nemotron is a thinking model: reasoning tokens consume the
  ``max_tokens`` budget before content is emitted. We set
  ``max_tokens=512`` (enough for ~150 reasoning tokens + a one-word
  answer). Calibrated in ticket 0226 (4/4 fixtures correct).
- The classifier cost is **harness overhead**, separate from the SOTA
  agent's $10 Phase B budget. Callers should book it under
  ``classifier_cost_usd`` in the per-turn cost artefact, not deduct
  from the agent's remaining budget.
- Defensive: any non-2xx, network error, or parse failure returns
  ``"no_report"`` and logs. Never raises. The smoke must not fall over
  on a flaky classifier round-trip.
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Literal

import httpx

log = logging.getLogger(__name__)

# Pinned classifier — open-weight NVIDIA model, vendor-neutral relative
# to the four Exp 2 subject models. Calibrated in ticket 0226 (4/4).
# Pricing as of 2026-05 (OpenRouter): $0.04 / $0.16 per Mtok in/out.
CLASSIFIER_MODEL = "nvidia/nemotron-nano-9b-v2"
CLASSIFIER_API_BASE = "https://openrouter.ai/api"

# Conservative pricing card for cost accounting. Kept private to this
# module — the SOTA harness's $10 cap is unaffected.
_PRICE_PER_MTOK_IN = 0.04
_PRICE_PER_MTOK_OUT = 0.16
_TOKENS_PER_MTOK = 1_000_000

# Cap on the narrative excerpt embedded in the prompt. 8 KiB ≈ 2K
# tokens — plenty to recognise an inventory header + a few rows.
_MAX_NARRATIVE_CHARS = 8_000

CLASSIFIER_PROMPT_TEMPLATE = """You are a classification assistant. The following is a single response from an AI agent that was asked to produce a structured inventory of Vietnam's thermal power plants (>30MWe). Did this response materially deliver an inventory?

- "report": the response contains a structured table or equivalent enumeration of power plants. This includes verified, corrected, or polished inventories — even when framed as "here is the corrected version".
- "no_report": the response is planning, clarification, refusal, or a meta-statement about intent. IMPORTANT: if the response contains preliminary tables but explicitly states it is NOT the final inventory (e.g. "I will not produce the final inventory yet", "candidate universe", "working ledger"), classify as "no_report" regardless of table presence.

AGENT RESPONSE:
```
{narrative_excerpt}
```

Reply with exactly one word: "report" or "no_report"."""


@dataclass(frozen=True)
class ClassificationResult:
    """Outcome of a single classifier call.

    ``class_`` carries a trailing underscore so the attribute name does
    not collide with Python's ``class`` keyword. Serialise it as
    ``{"class": ...}`` if writing to disk (see
    :func:`result_to_artefact_dict`).
    """

    class_: Literal["report", "no_report"]
    classifier_cost_usd: float
    classifier_model: str
    wall_s: float


def result_to_artefact_dict(result: ClassificationResult) -> dict:
    """Project the dataclass to a JSON-friendly dict with ``class`` key."""
    return {
        "class": result.class_,
        "classifier_cost_usd": result.classifier_cost_usd,
        "classifier_model": result.classifier_model,
        "wall_s": result.wall_s,
    }


def _load_api_key() -> str | None:
    """Read ``OPENROUTER_API_KEY`` from the environment; return ``None`` if absent.

    Unlike the SOTA adapter, missing credentials should not raise here
    — the caller would already have failed long before reaching the
    classifier. Return ``None`` so the caller path classifies as
    ``no_report`` and logs.
    """
    return os.environ.get("OPENROUTER_API_KEY")


def _build_prompt(narrative: str) -> str:
    excerpt = narrative[:_MAX_NARRATIVE_CHARS]
    return CLASSIFIER_PROMPT_TEMPLATE.format(narrative_excerpt=excerpt)


def _parse_class(reply_text: str) -> Literal["report", "no_report"]:
    """Tolerant one-word parser.

    Accepts the two expected words case-insensitively, ignoring
    surrounding whitespace, punctuation, or markdown fencing. Anything
    else → ``no_report`` (the safe default that keeps the state machine
    in the encourage branch).
    """
    if not reply_text:
        return "no_report"
    cleaned = reply_text.strip().lower()
    # Strip code fences if the model wrapped its one-word answer.
    cleaned = cleaned.strip("`").strip().strip('"').strip("'").strip()
    # Take the first alphabetic token only.
    token = ""
    for ch in cleaned:
        if ch.isalpha() or ch == "_":
            token += ch
        elif token:
            break
    if token == "report":
        return "report"
    if token == "no_report" or token.startswith("no"):
        return "no_report"
    return "no_report"


def _compute_cost_usd(usage: dict) -> float:
    tokens_in = int(usage.get("prompt_tokens", 0) or 0)
    tokens_out = int(usage.get("completion_tokens", 0) or 0)
    return (
        tokens_in * _PRICE_PER_MTOK_IN / _TOKENS_PER_MTOK
        + tokens_out * _PRICE_PER_MTOK_OUT / _TOKENS_PER_MTOK
    )


def _post_classifier(prompt: str, api_key: str) -> dict:
    """One-shot POST /v1/chat/completions. Raises httpx.HTTPError on failure."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "HTTP-Referer": "https://github.com/haduong/aedist-technical-report",
        "X-Title": "AEDIST dialogue classifier",
    }
    body = {
        "model": CLASSIFIER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        # Nemotron is thinking-capable: reasoning tokens consume the
        # budget before content is emitted. 512 is enough for ~150
        # reasoning tokens + the one-word answer.
        "max_tokens": 512,
    }
    with httpx.Client(base_url=CLASSIFIER_API_BASE, headers=headers) as client:
        resp = client.post("/v1/chat/completions", json=body, timeout=30.0)
        resp.raise_for_status()
        return resp.json()


def classify_report(narrative: str) -> ClassificationResult:
    """Classify the assistant's narrative as ``"report"`` or ``"no_report"``.

    Returns a :class:`ClassificationResult` carrying both the class and
    the cost. Never raises: a transport, parse, or empty-content error
    becomes a ``"no_report"`` result with cost 0 and a log line.
    """
    t0 = time.monotonic()
    api_key = _load_api_key()
    if api_key is None:
        wall = round(time.monotonic() - t0, 3)
        log.warning("dialogue_classifier: no OPENROUTER_API_KEY found; defaulting to 'no_report'.")
        return ClassificationResult(
            class_="no_report",
            classifier_cost_usd=0.0,
            classifier_model=CLASSIFIER_MODEL,
            wall_s=wall,
        )

    prompt = _build_prompt(narrative or "")
    try:
        data = _post_classifier(prompt, api_key)
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        wall = round(time.monotonic() - t0, 3)
        log.warning("dialogue_classifier: HTTP failure (%s); defaulting to 'no_report'.", exc)
        return ClassificationResult(
            class_="no_report",
            classifier_cost_usd=0.0,
            classifier_model=CLASSIFIER_MODEL,
            wall_s=wall,
        )

    try:
        reply_text = data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as exc:
        wall = round(time.monotonic() - t0, 3)
        log.warning(
            "dialogue_classifier: unexpected response shape (%s); defaulting to 'no_report'.",
            exc,
        )
        return ClassificationResult(
            class_="no_report",
            classifier_cost_usd=0.0,
            classifier_model=CLASSIFIER_MODEL,
            wall_s=wall,
        )

    cls = _parse_class(reply_text)
    cost = _compute_cost_usd(data.get("usage", {}) or {})
    wall = round(time.monotonic() - t0, 3)
    log.info(
        "dialogue_classifier: class=%s cost=$%.6f wall=%.2fs model=%s",
        cls,
        cost,
        wall,
        CLASSIFIER_MODEL,
    )
    return ClassificationResult(
        class_=cls,
        classifier_cost_usd=cost,
        classifier_model=CLASSIFIER_MODEL,
        wall_s=wall,
    )
