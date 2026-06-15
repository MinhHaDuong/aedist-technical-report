"""Negative guards for the 'answer key' → 'coverage bar' rename (ticket 0615).

Reading-3 retires the term 'answer key' (a reading-2 coinage) in favour of
'coverage bar'. These are negative guards only, per the CI polarity rule
(`.claude/rules/writing.md`): we forbid the obsolete term and the two
trailing caption clauses that ticket 0615 dropped. We never pin the new
positive authorial wording — that would break on the next legitimate
rewrite.

- The literal string 'answer key' (any case) must not survive anywhere in
  `main.tex`.
- The Figure 3 caption (`fig:direct-base`) must no longer carry the dropped
  tail: neither "every model should recover" nor "Models grouped on the
  vertical axis" — a structural assertion that the caption was shortened.
"""

import re

import pytest
from manuscript_source import raw, strip_comments

pytestmark = pytest.mark.adherence

_FIG3_RE = re.compile(
    r"\\caption\{(?P<body>.*?)\}\\label\{fig:direct-base\}",
    re.DOTALL,
)


def test_answer_key_term_absent():
    """The obsolete 'answer key' term must not appear in main.tex."""
    body = strip_comments(raw())
    assert "answer key" not in body.lower(), (
        "'answer key' was retired by ticket 0615 in favour of 'coverage bar'; "
        "a surviving occurrence means the rename is incomplete."
    )


def test_fig3_caption_dropped_trailing_clauses():
    """Figure 3 caption no longer carries the clauses ticket 0615 removed."""
    text = strip_comments(raw())
    m = _FIG3_RE.search(text)
    assert m is not None, "fig:direct-base caption not found in main.tex"
    caption = m.group("body")
    for dropped in ("every model should recover", "Models grouped"):
        assert dropped not in caption, (
            f"Figure 3 caption still contains the dropped clause {dropped!r}; "
            "ticket 0615 shortened the caption to end on the coverage-bar "
            "definition."
        )
