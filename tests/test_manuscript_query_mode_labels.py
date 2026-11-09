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

REPO = Path(__file__).resolve().parent.parent
MANUSCRIPT = REPO / "slides" / "manuscript" / "main.tex"
REPORT_DIR = REPO / "report"

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


# ---- Generated tables (ticket 0636) -------------------------------------
# The emitter-built tables the reader sees must not leak the retired words
# either: ticket 0620 swept the prose only, and tab_exp2_2x2_agents.tex kept
# "naive (single-shot)" rows. Scope: every generated table that main.tex or
# a report/*.tex file includes (\input / \InputIfFileExists). Macro files
# (macros_*.tex) are exempt: their identifiers are command names (see above).
_GEN_INCLUDE_RE = re.compile(
    r"\\(?:input|InputIfFileExists)\{(?:\.\./\.\./report/|)inputs/generated/(tab_[A-Za-z0-9_]+)(?:\.tex)?\}"
    r"|\\(?:input)\{\.\./\.\./report/inputs/generated/(tab_[A-Za-z0-9_]+)(?:\.tex)?\}"
)
_TABLE_FORBIDDEN_RE = re.compile(
    r"\b(?:naï?ve|naïf|optimi[sz](?:e|ed|ing|ation)?|optimisé)\b", re.IGNORECASE
)


def _included_generated_tables() -> list[Path]:
    gen = REPO / "report" / "inputs" / "generated"
    sources = [MANUSCRIPT, *sorted(REPORT_DIR.glob("*.tex"))]
    names: set[str] = set()
    for src in sources:
        text = _COMMENT_RE.sub("", src.read_text(encoding="utf-8"))
        for m in _GEN_INCLUDE_RE.finditer(text):
            names.add(m.group(1) or m.group(2))
    return sorted(p for n in names if (p := gen / f"{n}.tex").exists())


def test_included_generated_tables_found():
    """Positive control: the scan reaches the tables it is meant to guard."""
    names = {p.name for p in _included_generated_tables()}
    assert "tab_exp2_2x2_agents.tex" in names
    assert "tab_exp2_bib_quality.tex" in names


def test_no_naive_optimised_in_included_generated_tables():
    """No "naive"/"optimised" word in any generated table main.tex or the
    report includes (ticket 0636). The emitters must render single-shot /
    multi-turn."""
    hits = []
    for path in _included_generated_tables():
        raw = _COMMENT_RE.sub("", path.read_text(encoding="utf-8"))
        for n, line in enumerate(raw.splitlines(), start=1):
            if _TABLE_FORBIDDEN_RE.search(line):
                hits.append(f"  {path.name}:{n}: {line.strip()}")
    preview = "\n".join(hits[:10])
    assert not hits, (
        f"{len(hits)} line(s) in included generated tables use a retired "
        'query-mode word ("naive"/"optimised"); fix the emitter in '
        f"src/aedist/ and regenerate (ticket 0636). First hits:\n{preview}"
    )
