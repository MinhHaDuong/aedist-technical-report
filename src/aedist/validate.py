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
from typing import Any, Literal, get_args

Category = Literal[
    "ok",
    "truncated_input",
    "truncated_output",
    "empty",
    "provider_error",
]

_VALID_CATEGORIES = frozenset(get_args(Category))

# Finish-reason values that indicate the output was cut off by the
# provider rather than ending on its own terms.
_TRUNCATING_FINISH_REASONS = frozenset({"length", "content_filter", "error"})

# Fraction of ctx_window above which the prompt is judged to have
# crowded out the output budget.
_INPUT_CTX_THRESHOLD = 0.9

# Response-content length (characters, stripped) below which a ``stop``
# finish is flagged as a voluntary short stop. Soft signal only, data is
# still usable. Content length is used instead of completion_tokens
# because some backends (Ollama) count internal/reasoning tokens in
# completion_tokens — the canonical degenerate RAG run
# ``experiments/outputs/rag/qwen3.5-2b-run2.json`` reports 17182 tokens
# for a 94-character response (an empty CSV shell).
_SHORT_STOP_CHARS = 200


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
        category = d.get("category", "ok")
        if category not in _VALID_CATEGORIES:
            raise ValueError(
                f"Unknown validation category {category!r}; "
                f"expected one of {sorted(_VALID_CATEGORIES)}"
            )
        return cls(
            ok=bool(d.get("ok", False)),
            category=category,  # type: ignore[arg-type]
            flags=list(d.get("flags", [])),
        )


def _has_provider_error(raw: dict) -> bool:
    """Detect an OpenRouter-style error object wrapped in an HTTP-200 body."""
    err = raw.get("error")
    if not err:
        return False
    # Accept either a string or a dict; either counts as an error.
    return bool(err)


def _response_content(raw: dict) -> str | None:
    """Return the string response body of a run record, or None.

    Single-turn records have a top-level ``response`` field. Multiturn
    records (see ``aedist.query_multiturn``) store a list of ``turns``
    with no top-level response; the assistant content is the
    concatenation of every assistant turn's ``content``. Mirrors the
    shape handled by ``_classify_orphan`` in ``aedist.evaluate``.
    """
    response = raw.get("response")
    if isinstance(response, str):
        return response
    turns = raw.get("turns")
    if isinstance(turns, list):
        assistant_parts = [
            t.get("content", "")
            for t in turns
            if isinstance(t, dict) and t.get("role") == "assistant"
        ]
        if assistant_parts:
            return "\n".join(p for p in assistant_parts if isinstance(p, str))
    return None


def _is_empty_content(raw: dict) -> bool:
    """Non-empty stripped content is required (catches ticket 0041).

    Handles both single-turn (``response``) and multiturn (``turns``)
    record shapes via ``_response_content``.
    """
    content = _response_content(raw)
    if content is None:
        return True
    return content.strip() == ""


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
    """Voluntary-short-stop: model ended on 'stop' with a tiny response body.

    Uses the stripped character length of the response content rather
    than completion_tokens, because Ollama and other backends count
    reasoning/internal tokens in completion_tokens. The flag must catch
    the 94-char CSV-header-only shell from qwen3.5-2b-run2 even though
    its completion_tokens is 17182.
    """
    if raw.get("finish_reason") != "stop":
        return False
    content = _response_content(raw)
    if content is None:
        return False
    stripped_len = len(content.strip())
    return 0 < stripped_len < _SHORT_STOP_CHARS


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
