"""Negative guard: the Exp 2 query-mode axis is never labelled "naive" /
"optimised" in manuscript prose (ticket 0620).

Author decision (2026-06-15, ticket 0620): the query-mode arms are named
by what they are — *single-shot* (arms 1, 3) and *multi-turn* (arms 2, 4) —
coherent with the figure code and subtitles. The register words "naive" and
"optimised"/"optimized" are retired from the prose, including the Exp 1
baseline-prompt usage ("the naive prompt").

CI polarity (rules/writing.md, ticket 0557): this is prose, so the guard is
**negative only** — it forbids the old register words. It must never pin the
new wording ("single-shot"/"multi-turn"); positive pins break on every
legitimate rewrite.

Two deliberate exemptions, neither a register word a reader sees:
- generated value-macro *identifiers* (``\\ExpTwoFOneMistralNaive``,
  ``\\ExpTwoCostOpenAIOptimised``, …) are LaTeX command names defined by the
  pipeline's emitter scripts, not prose. Renaming them is a cross-file
  pipeline change out of this sweep's scope;
- the filename token ``protocol_07_naive_prompt`` is code (an annex file
  path), kept verbatim by the ticket's judgment call.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

MANUSCRIPT = (
    Path(__file__).resolve().parent.parent / "slides" / "manuscript" / "main.tex"
)

_COMMENT_RE = re.compile(r"(?<!\\)%.*$", re.MULTILINE)
# Exempt: generated value-macro identifiers carrying the old arm names.
_MACRO_TOKEN_RE = re.compile(r"\\[A-Za-z]*(?:Naive|Optimised|Optimized)")
# Exempt: the annex file-path token (code, not prose).
_FILENAME_TOKEN_RE = re.compile(r"protocol_07_naive_prompt")
# The forbidden query-mode register words, as whole words (case-insensitive).
_FORBIDDEN_RE = re.compile(r"\b(?:naï?ve|optimi[sz](?:e|ed|ing|ation)?)\b", re.IGNORECASE)


def _prose_lines() -> list[tuple[int, str]]:
    """(1-based line, line) of main.tex with comments, exempt macro
    identifiers, and the exempt filename token blanked — line-preserving."""
    raw = MANUSCRIPT.read_text(encoding="utf-8")
    raw = _COMMENT_RE.sub("", raw)
    raw = _MACRO_TOKEN_RE.sub("", raw)
    raw = _FILENAME_TOKEN_RE.sub("", raw)
    return list(enumerate(raw.splitlines(), start=1))


def test_no_naive_optimised_query_mode_labels():
    """No "naive"/"optimised"/"optimized" register word in manuscript prose
    (ticket 0620). Macro identifiers and the annex filename token are exempt."""
    hits = [
        (n, m.group(0), line.strip())
        for n, line in _prose_lines()
        for m in [_FORBIDDEN_RE.search(line)]
        if m
    ]
    preview = "\n".join(f"  main.tex:{n}: {word!r} in: {line}" for n, word, line in hits[:10])
    assert not hits, (
        f"{len(hits)} line(s) in slides/manuscript/main.tex prose still use a "
        '"naive"/"optimised" register word; the query-mode arms are named '
        "single-shot / multi-turn (ticket 0620). Macro identifiers "
        "(\\ExpTwo…Naive/Optimised) and the filename token "
        f"protocol_07_naive_prompt are exempt. First hits:\n{preview}"
    )
