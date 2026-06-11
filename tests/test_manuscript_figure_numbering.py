"""Enforce gapless, ordered figure labels in slides/manuscript/main.tex.

Since ticket 0518 the manuscript no longer hand-types figure numbers — the
auto-numbering is LaTeX's (ticket 0524 made the source hand-curated LaTeX).
The numbering invariant is expressed over the *order of figure ``\\label``
definitions* rather than over grepped integers:

  * the seven main-body figures appear, in document order, exactly as the
    expected id sequence (Figure 1..7 in the PDF);
  * the four supplementary figures (S1..S4) appear after them, in order; the
    recognition matrix (S4) is a `\\refstepcounter{figure}\\label{…}` +
    `\\includepdf` block.

A reorder, insertion, deletion, or duplicate of a figure changes the rendered
numbers and breaks this test — the same protection the old literal "Figure N."
gapless-integer assertion gave, now expressed structurally.

See ticket 0483 (the original renumbering) and 0512 (S-scheme unification).
"""

import re
from pathlib import Path

import pytest
from manuscript_source import MANUSCRIPT, body_raw

pytestmark = pytest.mark.adherence

# Expected main-body figure labels, in the document order that yields Figure 1..7.
# Ticket 0507: the reliability-vs-accuracy scatter replaces the quality-floor
# heatmap as the section-4 headline quality figure.
EXPECTED_MAIN = [
    "fig:longtail",
    "fig:capability-timeline",
    "fig:direct-base",
    "fig:cost-quality",
    "fig:reliability",
    "fig:exp2-arms",
    "fig:fusion-mvp",
]

# Expected supplementary figure labels, in the order that yields S1..S4. The
# recognition matrix is defined via \refstepcounter + \label.
# Ticket 0507: the quality-floor heatmap moved to the Exp1 scoring annex
# (becoming S1) and the spider (old S1) left the paper (kept in slides).
EXPECTED_SUPP = [
    "fig:quality-floor",
    "fig:capability-dag",
    "fig:coverage-certainty",
    "fig:recognition-matrix",
]

FIG_LABEL_RE = re.compile(r"\\label\{(fig:[a-z0-9-]+)\}")


def _figure_labels_in_order() -> list[str]:
    return FIG_LABEL_RE.findall(body_raw())


def test_figure_labels_are_ordered_and_gapless() -> None:
    """All figure labels appear in exactly the expected main-then-supp order."""
    labels = _figure_labels_in_order()
    assert labels == EXPECTED_MAIN + EXPECTED_SUPP, (
        "Figure label definitions (document order) must be the gapless "
        f"main-then-supplementary sequence.\n  expected: {EXPECTED_MAIN + EXPECTED_SUPP}\n"
        f"  got:      {labels}"
    )


def test_spider_removed_but_module_kept() -> None:
    """Ticket 0507: the Exp1 spider left the paper but its module stays.

    The reliability scatter inherits the spider's thesis, so the figure is
    redundant in the paper — but plot_quality_floor_heatmap_exp1 imports
    helpers from the spider module and slides.tex still renders spiders.
    """
    text = MANUSCRIPT.read_text(encoding="utf-8")
    assert "fig_spider_exp1_families" not in text, "spider figure still in paper"
    assert (
        Path(__file__).resolve().parent.parent / "src" / "aedist" / "plot_quality_spider_exp1.py"
    ).exists(), "spider module must be kept (imported by heatmap + used by slides)"


def test_reliability_in_text_heatmap_in_annex() -> None:
    """Ticket 0507: scatter is the section-4 figure; heatmap is annex support."""
    text = body_raw()
    parts = text.split("\n\\appendix\n", 1)
    assert len(parts) == 2, "no \\appendix divider found in main.tex"
    body_part, annex = parts
    assert "fig_exp1_reliability" in body_part, "reliability scatter not in main text"
    assert "fig_quality_floor_heatmap_exp1" not in body_part, "heatmap still in main text"
    assert "fig_quality_floor_heatmap_exp1" in annex, "heatmap not in annex"


def test_no_hand_typed_figure_numbers_in_captions() -> None:
    """No `\\caption{Figure N. …}` literal prefix survives the migration.

    LaTeX supplies the "Figure N:" label itself; a literal "Figure 3." left at
    the start of a caption would double-number in the PDF.
    """
    text = body_raw()
    literal = re.findall(r"\\caption\{\s*\*?Figure S?\d+[.:]", text)
    assert not literal, (
        f"Hand-typed figure-number caption prefix(es) remain: {literal}"
    )
