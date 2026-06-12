"""Em-dash encoding guard (ticket 0558).

Author decision (2026-06-12, ticket 0552 aspect 1): the canonical em-dash
encoding in manuscript prose is the literal Unicode em dash (U+2014), not
the LaTeX ``---`` ligature. With a single encoding, em-dash audits are a
one-line grep and the count cannot diverge between source and PDF (the
0543 waiver gap).

Excluded from the guard, matching the sweep's exclusions:
- verbatim/quote environments (frozen quoted material — notably the as-sent
  Doc-07 prompt block in Annex B, which has its own drift guard);
- LaTeX comments (source-maintenance notes are not prose).
"""

import re

import pytest
from manuscript_source import raw, strip_comments

pytestmark = pytest.mark.adherence

_QUOTED_ENV_RE = re.compile(
    r"\\begin\{(quote|quotation|verbatim|Verbatim|lstlisting)\}"
    r".*?"
    r"\\end\{\1\}",
    re.DOTALL,
)


def _prose_lines() -> list[tuple[int, str]]:
    """(1-based line number, line) pairs of main.tex prose.

    Comments are stripped and quoted/verbatim environments blanked
    line-by-line, so reported line numbers match the committed source.
    """
    text = strip_comments(raw())
    blanked = _QUOTED_ENV_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    return list(enumerate(blanked.splitlines(), start=1))


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
