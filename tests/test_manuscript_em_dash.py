"""Em-dash guards: encoding (ticket 0558) + density (ticket 0552).

Author decision (2026-06-12, ticket 0552 aspect 1): the canonical em-dash
encoding in manuscript prose is the literal Unicode em dash (U+2014), not
the LaTeX ``---`` ligature. With a single encoding, em-dash audits are a
one-line grep and the count cannot diverge between source and PDF (the
0543 waiver gap).

Author decision (2026-06-12, ticket 0552 aspect 2): em dashes stay legal —
the AI tell is clustering and monotony, not the character. Two standing
density guards enforce that:
- a local cap — no prose paragraph carries more than
  ``EM_DASH_PARAGRAPH_CAP`` em dashes (a paired parenthetical ``—like
  this—`` alone stays within the cap);
- a global ratchet — the total prose em-dash count never exceeds the
  committed ceiling in ``tests/data/emdash_ceiling.txt``. Lowering the
  ceiling is a deliberate commit; an edit pushing the count above it
  fails CI.

Excluded from all guards, matching the sweep's exclusions (one shared
definition of "prose" via :func:`_prose`):
- verbatim/quote environments (frozen quoted material — notably the as-sent
  Doc-07 prompt block in Annex B, which has its own drift guard, and the
  Glossary box);
- inline display-quoted verbatim strings (``\\emph{``…''}`` — the as-sent
  Phase B reply strings, frozen protocol text mirrored from
  ``experiments/sota/exp2_interactive_smoke.py``);
- LaTeX comments (source-maintenance notes are not prose).
"""

import re
from pathlib import Path

import pytest
from manuscript_source import raw, strip_comments

pytestmark = pytest.mark.adherence

EM_DASH_PARAGRAPH_CAP = 2
EM_DASH_CEILING_FILE = Path(__file__).resolve().parent / "data" / "emdash_ceiling.txt"

_QUOTED_ENV_RE = re.compile(
    r"\\begin\{(quote|quotation|verbatim|Verbatim|lstlisting|promptbox)\}"
    r".*?"
    r"\\end\{\1\}",
    re.DOTALL,
)
# Display-quoted verbatim strings (as-sent protocol text quoted in prose).
_INLINE_QUOTED_RE = re.compile(r"\\emph\{``.*?''\}", re.DOTALL)
# Anchor for the exclusion above: the as-sent Phase B reply strings. A new
# match would silently evade every guard, so the count is pinned (see
# test_inline_quoted_exclusion_anchor).
INLINE_QUOTED_SPAN_COUNT = 5
# Heading commands form their own block in _paragraphs(): a heading and its
# \addcontentsline twin both carry the title's em dash, which would otherwise
# consume the surrounding prose paragraph's whole cap budget.
_HEADING_LINE_RE = re.compile(
    r"\s*\\(section|subsection|subsubsection|paragraph|addcontentsline)\b"
)


def _blank(match: re.Match) -> str:
    """Newline-preserving replacement, so line numbers stay stable."""
    return "\n" * match.group(0).count("\n")


def _prose() -> str:
    """main.tex with comments stripped and quoted material blanked.

    Line-preserving: reported line numbers match the committed source.
    This is the single definition of "prose" shared by every em-dash
    guard in this module.
    """
    text = strip_comments(raw())
    text = _QUOTED_ENV_RE.sub(_blank, text)
    return _INLINE_QUOTED_RE.sub(_blank, text)


def _prose_lines() -> list[tuple[int, str]]:
    """(1-based line number, line) pairs of main.tex prose."""
    return list(enumerate(_prose().splitlines(), start=1))


def _paragraphs() -> list[tuple[int, str]]:
    """(1-based start line, text) of each blank-line-delimited prose block."""
    paras: list[tuple[int, str]] = []
    block: list[str] = []
    start = 0
    for n, line in _prose_lines():
        if _HEADING_LINE_RE.match(line):
            if block:
                paras.append((start, "\n".join(block)))
                block = []
            paras.append((n, line))
        elif line.strip():
            if not block:
                start = n
            block.append(line)
        elif block:
            paras.append((start, "\n".join(block)))
            block = []
    if block:
        paras.append((start, "\n".join(block)))
    return paras


def test_inline_quoted_exclusion_anchor():
    """The \\emph{``…''} exclusion blanks exactly the known as-sent protocol
    spans. A new match means a prose quote would silently evade every em-dash
    guard — acknowledge it deliberately by updating the pinned count."""
    spans = list(_INLINE_QUOTED_RE.finditer(strip_comments(raw())))
    assert len(spans) == INLINE_QUOTED_SPAN_COUNT, (
        f"{len(spans)} \\emph{{``…''}} spans found, expected "
        f"{INLINE_QUOTED_SPAN_COUNT}. These spans are excluded from all "
        "em-dash guards; if the new span is genuinely frozen as-sent text, "
        "update INLINE_QUOTED_SPAN_COUNT — otherwise unwrap the prose quote."
    )


def test_no_tex_em_dash_ligature_in_prose():
    """Manuscript prose carries no ``---`` ligature: the em dash is encoded
    as the literal Unicode glyph (ticket 0558)."""
    hits = [(n, line.strip()) for n, line in _prose_lines() if "---" in line]
    preview = "\n".join(f"  main.tex:{n}: {line}" for n, line in hits[:10])
    assert not hits, (
        f"{len(hits)} line(s) in slides/manuscript/main.tex prose still use "
        "the LaTeX --- ligature; the canonical em-dash encoding is the "
        f"literal Unicode glyph (ticket 0558). First hits:\n{preview}"
    )


def test_em_dash_paragraph_cap():
    """No prose paragraph carries more than EM_DASH_PARAGRAPH_CAP em dashes
    (ticket 0552): the AI tell is clustering, so density is capped locally."""
    over = [(n, p.count("—"), p) for n, p in _paragraphs() if p.count("—") > EM_DASH_PARAGRAPH_CAP]
    preview = "\n".join(
        f"  main.tex:{n}: {c} em dashes: {' '.join(p.split())[:120]}…" for n, c, p in over[:10]
    )
    assert not over, (
        f"{len(over)} paragraph(s) in slides/manuscript/main.tex prose exceed "
        f"the {EM_DASH_PARAGRAPH_CAP}-em-dash cap (ticket 0552). Diversify the "
        f"punctuation — commas, colons, parentheses, sentence splits:\n{preview}"
    )


def test_em_dash_global_ratchet():
    """Total prose em-dash count never exceeds the committed ceiling
    (ticket 0552). Lowering the ceiling is a deliberate commit; an edit
    pushing the count above it fails here."""
    assert EM_DASH_CEILING_FILE.exists(), (
        f"missing {EM_DASH_CEILING_FILE}: the em-dash ratchet ceiling must be "
        "committed (one line, the integer prose em-dash count)"
    )
    ceiling = int(EM_DASH_CEILING_FILE.read_text(encoding="utf-8").strip())
    count = _prose().count("—")
    assert count <= ceiling, (
        f"slides/manuscript/main.tex prose carries {count} em dashes, above "
        f"the committed ceiling of {ceiling} ({EM_DASH_CEILING_FILE}). Either "
        "diversify the new punctuation or raise the ceiling in a deliberate "
        "commit (ticket 0552)."
    )
