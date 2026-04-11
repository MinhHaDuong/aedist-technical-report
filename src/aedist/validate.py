"""Run validation layer for measurement hygiene (ticket 0072).

Every saved run record in ``experiments/outputs/<condition>/*.json`` is a
normalized wrapper around whatever a provider returned. The harness only
checks ``HTTP 200``; it does not look at the body. Corrupted bodies (empty
content, ``finish_reason=length``, prompt that blew past the context
window, OpenRouter error object embedded in a 200 response) slip through
and contaminate method F1 estimates.

``validate_run(raw_dict)`` is the read-time trust boundary. It inspects
one raw record and returns a ``ValidationResult`` describing whether the
record is a clean observation of the method x model cell under test.

Framing: this is not model QA. A truncated run is a corrupted
observation, not a weak model. Corrupted runs should be flagged and
excluded from method aggregates, not treated as low scores.

Categories (first-failing wins):

    provider_error  - body contains a provider error object on HTTP 200
    empty           - content is missing or whitespace-only
    truncated_output- finish_reason in {length, content_filter, error}
    truncated_input - prompt tokens exceeded 90% of context window
    ok              - passed every check

Soft flags may coexist with ``category=ok``; e.g. ``voluntary_short_stop``
records short ``stop`` completions without dropping the data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Category = Literal[
    "ok",
    "corrupted",
    "truncated_input",
    "truncated_output",
    "empty",
    "provider_error",
]

# Finish-reason values that indicate the output was cut off by the
# provider rather than ending on its own terms.
_TRUNCATING_FINISH_REASONS = frozenset({"length", "content_filter", "error"})

# Fraction of ctx_window above which the prompt is judged to have
# crowded out the output budget.
_INPUT_CTX_THRESHOLD = 0.9

# Completion-token count below which a ``stop`` finish is flagged as
# a voluntary short stop. Soft signal only, data is still usable.
_SHORT_STOP_TOKENS = 500


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of validating one raw run record."""

    ok: bool
    category: Category
    flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "category": self.category, "flags": list(self.flags)}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ValidationResult:
        return cls(
            ok=bool(d.get("ok", False)),
            category=d.get("category", "ok"),  # type: ignore[arg-type]
            flags=list(d.get("flags", [])),
        )


def _has_provider_error(raw: dict) -> bool:
    """Detect an OpenRouter-style error object wrapped in an HTTP-200 body."""
    err = raw.get("error")
    if not err:
        return False
    # Accept either a string or a dict; either counts as an error.
    return bool(err)


def _is_empty_content(raw: dict) -> bool:
    """Non-empty stripped content is required (catches ticket 0041)."""
    response = raw.get("response")
    if response is None:
        return True
    if not isinstance(response, str):
        return False
    return response.strip() == ""


def _is_truncated_output(raw: dict) -> bool:
    reason = raw.get("finish_reason")
    return isinstance(reason, str) and reason in _TRUNCATING_FINISH_REASONS


def _is_truncated_input(raw: dict) -> bool:
    """Return True iff prompt tokens exceed the configured ctx fraction.

    Returns False when context_window is unknown — absence of information
    is not evidence of corruption.
    """
    usage = raw.get("usage") or {}
    prompt_tokens = usage.get("prompt_tokens")
    if not isinstance(prompt_tokens, int) or prompt_tokens <= 0:
        return False
    meta = raw.get("model_metadata") or {}
    ctx = meta.get("context_window")
    if not isinstance(ctx, int) or ctx <= 0:
        return False
    return prompt_tokens > ctx * _INPUT_CTX_THRESHOLD


def _is_short_stop(raw: dict) -> bool:
    """Voluntary-short-stop: model ended on 'stop' with few tokens generated."""
    if raw.get("finish_reason") != "stop":
        return False
    usage = raw.get("usage") or {}
    completion = usage.get("completion_tokens")
    if not isinstance(completion, int):
        return False
    return 0 < completion < _SHORT_STOP_TOKENS


def validate_run(raw: dict) -> ValidationResult:
    """Inspect a raw run record and return its ValidationResult.

    ``raw`` is the dict loaded from an ``experiments/outputs/*.json`` file.
    The record shape is normalized upstream by ``aedist.harness`` so this
    function does not branch on provider.
    """
    flags: list[str] = []

    # Hard checks, in precedence order. First failing check wins the category.
    if _has_provider_error(raw):
        flags.append("provider_error_body")
        return ValidationResult(ok=False, category="provider_error", flags=flags)

    if _is_empty_content(raw):
        flags.append("empty_content")
        return ValidationResult(ok=False, category="empty", flags=flags)

    if _is_truncated_output(raw):
        flags.append(f"finish_reason_{raw.get('finish_reason')}")
        return ValidationResult(ok=False, category="truncated_output", flags=flags)

    if _is_truncated_input(raw):
        flags.append("prompt_over_ctx_threshold")
        return ValidationResult(ok=False, category="truncated_input", flags=flags)

    # Soft flags do not flip the category.
    if _is_short_stop(raw):
        flags.append("voluntary_short_stop")

    return ValidationResult(ok=True, category="ok", flags=flags)
