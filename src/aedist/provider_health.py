"""Provider health state machine for credit/cap-aware sweep dispatch.

Problem
-------
When a provider hits a daily cap or runs out of credit mid-sweep, the
harness currently treats it like any transient network error: it logs,
moves on, and leaves a lopsided method×model matrix (e.g., 1/3 reps on
DeepSeek but 3/3 on Kimi). Downstream pooling then compares *methods*
across unequal sample sizes — a silent bias on the headline research
claim.

Contract
--------
Failures are classified into three dispositions:

``HARD_STOP``
    Credit exhausted, daily cap, or OpenRouter ``code=402``. The whole
    router is dead for the rest of the sweep; remaining cells get parked
    to ``parked.jsonl`` for a later resume. Retrying in-session is wasted
    budget — credit does not come back in minutes.

``SOFT_RETRY``
    Short-window rate limit, 503, connection reset, timeout, or any
    unknown error (conservative default). The caller backs off and
    retries. After ``soft_retry_limit`` consecutive failures on the same
    (router, model), the state machine *promotes* the soft failure to a
    hard stop for the router.

``PERMANENT_SKIP``
    403 region-locked, 404 model removed, Ollama connection refused.
    The single model is cached as unavailable for the session but the
    router keeps serving other models. One parked record is written so
    the resume path knows it was intentionally skipped, not forgotten.

Integration hook
----------------
The sweep loops in ``query*.py`` already wrap each dispatch in
``except openai.APIError``. The minimal integration is:

1. Before dispatch, call ``health.is_blocked(router, model_id)`` and park
   the cell if blocked.
2. Inside the ``except`` branch, call
   ``health.record_failure(router, model_id, exc)`` and park the cell.

This module does not own the sweep loop, does not call the network, and
has no coupling to any specific ``openai``/``httpx`` class — it
duck-types on ``.status_code`` / ``.body`` so unit tests can feed it
plain ``SimpleNamespace`` stubs.

Out of scope (see ticket 0074)
------------------------------
* Actual resume implementation (``resume_sweep``) — this module only
  writes the ``parked.jsonl`` ledger.
* Retroactively marking short-sampled cells in ``measurements.jsonl``.
* Body-level validation of HTTP-200 responses (that is ticket 0072).
"""

from __future__ import annotations

import enum
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


class Disposition(enum.Enum):
    """How the sweep loop should react to a failure."""

    HARD_STOP = "hard_stop"
    SOFT_RETRY = "soft_retry"
    PERMANENT_SKIP = "permanent_skip"


@dataclass
class Verdict:
    """Outcome of classifying a single failure."""

    disposition: Disposition
    reason: str
    status_code: int | None = None
    upstream_provider: str | None = None

    def __str__(self) -> str:  # pragma: no cover - trivial
        bits = [self.disposition.value, self.reason]
        if self.status_code is not None:
            bits.append(f"http={self.status_code}")
        if self.upstream_provider:
            bits.append(f"upstream={self.upstream_provider}")
        return " | ".join(bits)


# ---------------------------------------------------------------------------
# Keyword tables for body-level classification
# ---------------------------------------------------------------------------

# If the body/message contains any of these substrings (case-insensitive),
# treat as hard stop regardless of the HTTP status code. Daily caps and
# quota exhaustion are surfaced inconsistently across providers.
_HARD_STOP_KEYWORDS = (
    "insufficient credit",
    "insufficient_credits",
    "out of credit",
    "quota_exceeded",
    "quota exceeded",
    "daily quota",
    "daily usage",
    "daily limit",
    "credit balance",
    "billing",
    "payment required",
)

# Short-window rate-limit language. Not a cap — back off and retry.
_SOFT_RETRY_KEYWORDS = (
    "rate_limit_exceeded",
    "rate limit",
    "per minute",
    "per second",
    "slow down",
    "try again",
    "temporarily unavailable",
    "service unavailable",
)


# ---------------------------------------------------------------------------
# classify_exception
# ---------------------------------------------------------------------------


def _extract_body(exc: Any) -> dict:
    """Pull the error body dict off an exception if present.

    Real ``openai.APIStatusError`` has ``.body`` as a dict. Stub exceptions
    in tests also use ``.body``. Returns an empty dict if nothing found.
    """

    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        return body
    return {}


def _extract_error_obj(body: dict) -> dict:
    err = body.get("error")
    if isinstance(err, dict):
        return err
    return {}


def _extract_status(exc: Any) -> int | None:
    sc = getattr(exc, "status_code", None)
    if isinstance(sc, int):
        return sc
    resp = getattr(exc, "response", None)
    if resp is not None:
        sc = getattr(resp, "status_code", None)
        if isinstance(sc, int):
            return sc
    return None


def _extract_message(exc: Any, err_obj: dict) -> str:
    parts: list[str] = []
    msg = err_obj.get("message")
    if isinstance(msg, str):
        parts.append(msg)
    exc_msg = getattr(exc, "message", None)
    if isinstance(exc_msg, str):
        parts.append(exc_msg)
    parts.append(str(exc))
    return " ".join(parts).lower()


def classify_exception(exc: BaseException) -> Verdict:
    """Classify a provider failure into a ``Verdict``.

    The classifier is deliberately conservative:

    * Anything that *looks like* credit/quota exhaustion is a hard stop.
    * 403/404 are permanent skips for the single model.
    * Ollama/local connection-refused is a permanent skip (the daemon is
      down; another sweep may bring it back but this sweep should not
      block waiting).
    * Timeouts and unknown errors default to soft retry rather than hard
      stop so a flaky network does not silently pause a sweep.
    """

    # Connection-refused (Ollama daemon down, local infra broken) →
    # permanent skip for the session. We do not know which model is
    # affected without more context; the caller passes the model id into
    # ProviderHealth.record_failure separately.
    if isinstance(exc, ConnectionRefusedError):
        return Verdict(
            disposition=Disposition.PERMANENT_SKIP,
            reason="connection refused (local provider offline)",
        )

    if isinstance(exc, TimeoutError):
        return Verdict(
            disposition=Disposition.SOFT_RETRY,
            reason="timeout",
        )

    body = _extract_body(exc)
    err_obj = _extract_error_obj(body)
    status = _extract_status(exc)
    message = _extract_message(exc, err_obj)

    metadata = err_obj.get("metadata")
    upstream = None
    if isinstance(metadata, dict):
        upstream = metadata.get("provider_name")

    # OpenRouter upstream code: wraps the real upstream code in
    # ``error.code``. A value of 402 there means "the upstream provider
    # ran out of credit", even if the outer HTTP was 429 or 200.
    inner_code = err_obj.get("code")
    try:
        inner_code_int = int(inner_code) if inner_code is not None else None
    except (TypeError, ValueError):
        inner_code_int = None

    if inner_code_int == 402 or status == 402:
        return Verdict(
            disposition=Disposition.HARD_STOP,
            reason="402 payment required",
            status_code=status,
            upstream_provider=upstream,
        )

    err_type = err_obj.get("type")
    if isinstance(err_type, str) and err_type.lower() == "quota_exceeded":
        return Verdict(
            disposition=Disposition.HARD_STOP,
            reason="quota_exceeded",
            status_code=status,
            upstream_provider=upstream,
        )

    if status == 429:
        # Distinguish daily cap from short-window rate limit. Order matters:
        # check for hard-stop keywords first, because "daily quota reached"
        # also contains "quota".
        for kw in _HARD_STOP_KEYWORDS:
            if kw in message:
                return Verdict(
                    disposition=Disposition.HARD_STOP,
                    reason=f"429 + daily/quota ({kw})",
                    status_code=status,
                    upstream_provider=upstream,
                )
        return Verdict(
            disposition=Disposition.SOFT_RETRY,
            reason="429 short-window rate limit",
            status_code=status,
            upstream_provider=upstream,
        )

    if status == 503:
        return Verdict(
            disposition=Disposition.SOFT_RETRY,
            reason="503 service unavailable",
            status_code=status,
            upstream_provider=upstream,
        )

    if status == 403:
        return Verdict(
            disposition=Disposition.PERMANENT_SKIP,
            reason="403 forbidden (region-locked or disabled)",
            status_code=status,
            upstream_provider=upstream,
        )

    if status == 404:
        return Verdict(
            disposition=Disposition.PERMANENT_SKIP,
            reason="404 model not found",
            status_code=status,
            upstream_provider=upstream,
        )

    # Body-level hard-stop signals independent of status code.
    for kw in _HARD_STOP_KEYWORDS:
        if kw in message:
            return Verdict(
                disposition=Disposition.HARD_STOP,
                reason=f"body match ({kw})",
                status_code=status,
                upstream_provider=upstream,
            )

    for kw in _SOFT_RETRY_KEYWORDS:
        if kw in message:
            return Verdict(
                disposition=Disposition.SOFT_RETRY,
                reason=f"body match ({kw})",
                status_code=status,
                upstream_provider=upstream,
            )

    # Conservative default: retry. A true hard stop will keep failing and
    # be promoted after `soft_retry_limit` attempts.
    return Verdict(
        disposition=Disposition.SOFT_RETRY,
        reason=f"unclassified ({type(exc).__name__})",
        status_code=status,
        upstream_provider=upstream,
    )


# ---------------------------------------------------------------------------
# ProviderHealth session state
# ---------------------------------------------------------------------------


@dataclass
class ProviderHealth:
    """Per-sweep-session health tracker.

    One instance lives inside a sweep runner for the duration of the run.
    It records failures against ``(router, model_id)`` keys and exposes
    ``is_blocked`` so the loop can short-circuit dispatch.

    Blocked set semantics:

    * A HARD_STOP on any model blocks the entire router. Credit is a
      router-wide resource.
    * A PERMANENT_SKIP only blocks the single model.
    * A SOFT_RETRY increments a counter; on the ``soft_retry_limit``-th
      consecutive failure, it is promoted to a router-wide hard stop.
    """

    soft_retry_limit: int = 3
    _hard_stopped_routers: dict[str, str] = field(default_factory=dict)
    _permanent_skipped: dict[tuple[str, str], str] = field(default_factory=dict)
    _soft_counters: dict[tuple[str, str], int] = field(default_factory=dict)

    def record_failure(
        self,
        router: str,
        model_id: str,
        exc: BaseException,
    ) -> Verdict:
        """Fold a failure into the health state. Return the verdict."""

        verdict = classify_exception(exc)
        key = (router, model_id)

        if verdict.disposition is Disposition.HARD_STOP:
            self._hard_stopped_routers[router] = str(verdict)
            log.warning("provider_health: router %s HARD_STOP (%s)", router, verdict.reason)
        elif verdict.disposition is Disposition.PERMANENT_SKIP:
            self._permanent_skipped[key] = str(verdict)
            log.warning(
                "provider_health: model %s/%s PERMANENT_SKIP (%s)",
                router,
                model_id,
                verdict.reason,
            )
        else:  # SOFT_RETRY
            self._soft_counters[key] = self._soft_counters.get(key, 0) + 1
            log.info(
                "provider_health: %s/%s soft retry %d/%d (%s)",
                router,
                model_id,
                self._soft_counters[key],
                self.soft_retry_limit,
                verdict.reason,
            )
            if self._soft_counters[key] >= self.soft_retry_limit:
                promoted = Verdict(
                    disposition=Disposition.HARD_STOP,
                    reason=(
                        f"promoted after {self.soft_retry_limit} soft retries "
                        f"(last: {verdict.reason})"
                    ),
                    status_code=verdict.status_code,
                    upstream_provider=verdict.upstream_provider,
                )
                self._hard_stopped_routers[router] = str(promoted)
                log.warning(
                    "provider_health: router %s promoted to HARD_STOP after %d soft retries",
                    router,
                    self.soft_retry_limit,
                )
                return promoted

        return verdict

    def record_success(self, router: str, model_id: str) -> None:
        """A successful dispatch clears the soft-retry counter for a cell."""
        self._soft_counters.pop((router, model_id), None)

    def is_blocked(self, router: str, model_id: str) -> bool:
        if router in self._hard_stopped_routers:
            return True
        if (router, model_id) in self._permanent_skipped:
            return True
        return False

    def block_reason(self, router: str, model_id: str) -> str | None:
        if router in self._hard_stopped_routers:
            return self._hard_stopped_routers[router]
        return self._permanent_skipped.get((router, model_id))

    def hard_stopped_routers(self) -> list[str]:
        return sorted(self._hard_stopped_routers)


# ---------------------------------------------------------------------------
# parked.jsonl writer
# ---------------------------------------------------------------------------


def park_cell(
    output_dir: Path,
    *,
    sweep_id: str,
    model_id: str,
    run: int,
    prompt_hash: str,
    reason: str,
    extra: dict | None = None,
) -> Path:
    """Append a parked-cell record to ``<output_dir>/parked.jsonl``.

    A parked record carries enough state for a future ``resume_sweep`` to
    re-dispatch the cell: the sweep id, model id, rep index, and a hash
    of the prompt (so a prompt change is detectable and forces a manual
    re-park decision).

    Returns the path to the parked.jsonl file.
    """

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    parked_path = output_dir / "parked.jsonl"

    record: dict[str, object] = {
        "sweep_id": sweep_id,
        "model_id": model_id,
        "run": run,
        "prompt_hash": prompt_hash,
        "reason": reason,
        "parked_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    if extra:
        record.update(extra)

    with parked_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    log.info(
        "provider_health: parked %s run %d (%s) → %s",
        model_id,
        run,
        reason,
        parked_path,
    )
    return parked_path
