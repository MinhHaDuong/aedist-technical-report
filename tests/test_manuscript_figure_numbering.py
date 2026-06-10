"""Enforce gapless, ordered figure labels in slides/manuscript/main.md.

Since ticket 0518 the manuscript no longer hand-types figure numbers — the
auto-numbering is delegated to pandoc-crossref + LaTeX. The numbering invariant
is therefore expressed over the *order of `{#fig:…}` label definitions* rather
than over grepped integers:

  * the seven main-body figures appear, in document order, exactly as the
    expected id sequence (Figure 1..7 in the PDF);
  * the four supplementary figures (S1..S4) appear after them, in order; the
    recognition matrix (S4) is a raw-LaTeX `\\label{fig:recognition-matrix}`.

A reorder, insertion, deletion, or duplicate of a figure changes the rendered
numbers and breaks this test — the same protection the old literal "Figure N."
gapless-integer assertion gave, now expressed structurally.

See ticket 0483 (the original renumbering) and 0512 (S-scheme unification).
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

MANUSCRIPT = (
    Path(__file__).resolve().parent.parent / "slides" / "manuscript" / "main.md"
)

# Expected main-body figure labels, in the document order that yields Figure 1..7.
EXPECTED_MAIN = [
    "fig:longtail",
    "fig:capability-timeline",
    "fig:direct-base",
    "fig:cost-quality",
    "fig:quality-floor",
    "fig:exp2-arms",
    "fig:fusion-mvp",
]

# Expected supplementary figure labels, in the order that yields S1..S4. S4 is
# the raw-LaTeX recognition matrix, defined via \refstepcounter + \label.
EXPECTED_SUPP = [
    "fig:spider-families",
    "fig:capability-dag",
    "fig:coverage-certainty",
    "fig:recognition-matrix",
]

# A figure label is defined either as a pandoc image attribute `{#fig:id}` or a
# raw-LaTeX `\label{fig:id}` (the S4 includepdf case).
FIG_LABEL_RE = re.compile(r"\{#(fig:[a-z0-9-]+)\}|\\label\{(fig:[a-z0-9-]+)\}")


def _figure_labels_in_order() -> list[str]:
    text = MANUSCRIPT.read_text(encoding="utf-8")
    return [m.group(1) or m.group(2) for m in FIG_LABEL_RE.finditer(text)]


def test_figure_labels_are_ordered_and_gapless() -> None:
    """All figure labels appear in exactly the expected main-then-supp order."""
    labels = _figure_labels_in_order()
    assert labels == EXPECTED_MAIN + EXPECTED_SUPP, (
        "Figure label definitions (document order) must be the gapless "
        f"main-then-supplementary sequence.\n  expected: {EXPECTED_MAIN + EXPECTED_SUPP}\n"
        f"  got:      {labels}"
    )


def test_no_hand_typed_figure_numbers_in_captions() -> None:
    """No `*Figure N.*` literal caption paragraph survives the migration.

    The old captions were standalone italic paragraphs; pandoc-crossref now
    supplies the number, so a surviving literal would double-number.
    """
    text = MANUSCRIPT.read_text(encoding="utf-8")
    # A markdown italic caption paragraph: a line that is exactly *Figure N. …*
    literal = re.findall(r"(?m)^\*Figure S?\d+\.", text)
    assert not literal, (
        "Hand-typed italic figure caption(s) remain (should be image alt text "
        f"with a {{#fig:}} label instead): {literal}"
    )
