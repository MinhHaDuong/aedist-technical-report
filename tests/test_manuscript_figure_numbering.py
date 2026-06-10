"""Enforce consecutive, gapless figure numbering in slides/manuscript/main.md.

Main-text and Annex E figure captions must be numbered 1..7 in document order
with no gaps and no non-standard suffixes (the former "Figure 2b" is banned).
Annex D supplementary captions ("Figure S1" … "Figure S3") are a separate
series and are intentionally excluded from this check by the `\\d+` regex,
which does not match the leading "S".

See ticket 0483 for the renumbering rationale (a uniform permutation that moved
the §3 capability-timeline figure to Figure 1 and absorbed the quality-floor
heatmap "Figure 2b" into a consecutive Figure 4).
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

MANUSCRIPT = (
    Path(__file__).resolve().parent.parent / "slides" / "manuscript" / "main.md"
)

# Caption lines look like `*Figure 1. ...*`. The `\d+` (not `\d+\w*`) makes the
# match SKIP `*Figure S1.*` (Annex D) and would also skip a malformed `*Figure 2b.*`.
CAPTION_RE = re.compile(r"^\*Figure (\d+)\.", re.MULTILINE)


def test_figure_captions_are_consecutive() -> None:
    """Main-body caption numbers in document order must be gapless 1..7.

    Ticket 0512 unified all annex figures onto the S-scheme (S1, S2, …), so the
    former Annex E "Figure 7" became "Figure S4", and the new §2 long-tail
    figure entered the main-body series as Figure 1 (document order). The
    main-body integer series is therefore 1..7; the S-series captions are
    matched by a separate regex that does not capture the leading "S".
    """
    text = MANUSCRIPT.read_text(encoding="utf-8")
    numbers = CAPTION_RE.findall(text)
    assert numbers == ["1", "2", "3", "4", "5", "6", "7"], (
        "Main-body figure caption numbers (document order) must be a gapless "
        f"1..7 sequence; got {numbers}"
    )


def test_no_figure_2b() -> None:
    """The non-standard 'Figure 2b' label must not appear anywhere."""
    text = MANUSCRIPT.read_text(encoding="utf-8")
    assert "Figure 2b" not in text, (
        "'Figure 2b' is a non-standard caption label and must be renumbered "
        "to a consecutive integer (ticket 0483)"
    )
