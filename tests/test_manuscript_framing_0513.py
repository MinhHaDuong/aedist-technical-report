"""Ticket 0513 — final framing + language pass on the arXiv manuscript.

Guards the prose-quality changes that ticket 0513 lands on
``slides/manuscript/main.md``:

1. A three-item Contributions list at the end of §1 (between the §1 and §2
   headings).
2. The "plausible-text generator" reframing replaces "random words generator".
3. The false-positive label is "unmatched", never "unrecognized plants" or
   "hallucinated" (project FP-labelling rule). Legitimate uses of "recognized"
   / "recognition" (true positives, the recognition matrix) must survive, so we
   assert on the exact FP phrases, not the "recogni" substring.
4. Annex A keeps the T1/T2 snapshot-vs-flow paragraphs but drops the
   Parmenides/Heraclitus philosophy genealogy.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

MAIN_MD = (
    Path(__file__).resolve().parent.parent / "slides" / "manuscript" / "main.md"
)


def _md() -> str:
    if not MAIN_MD.exists():
        pytest.skip("main.md not found")
    return MAIN_MD.read_text(encoding="utf-8")


def _section_1_body() -> str:
    """Text between the `## 1.` and `## 2.` headings (the whole of §1)."""
    md = _md()
    start = re.search(r"^## 1\. ", md, re.MULTILINE)
    end = re.search(r"^## 2\. ", md, re.MULTILINE)
    assert start and end, "could not locate §1 / §2 headings"
    return md[start.start() : end.start()]


def test_contributions_list_at_end_of_section_1() -> None:
    """A Contributions run-in label plus three list items live inside §1."""
    sec1 = _section_1_body()
    assert "**Contributions.**" in sec1, (
        "§1 must end with a bold 'Contributions.' run-in label, not a heading"
    )
    # Three list items: count markdown list bullets after the label.
    tail = sec1[sec1.index("**Contributions.**") :]
    items = re.findall(r"^\s*(?:\d+\.|[-*])\s+", tail, re.MULTILINE)
    assert len(items) >= 3, (
        f"Contributions list should name three contributions; found {len(items)} items"
    )


def test_plausible_text_generator_reframing() -> None:
    md = _md()
    assert "plausible-text generator" in md, (
        "the 'plausible-text generator' reframing must be present"
    )
    assert "random words generator" not in md, (
        "'random words generator' must be replaced by 'plausible-text generator'"
    )


def test_unmatched_terminology_in_fp_context() -> None:
    md = _md()
    assert "unmatched" in md, "the FP label 'unmatched' must be present"
    assert "unrecognized plants" not in md, (
        "FP framing 'unrecognized plants' must become 'unmatched'"
    )
    assert "unrecognised plants" not in md, (
        "FP framing 'unrecognised plants' must become 'unmatched'"
    )
    assert "hallucinat" not in md.lower(), (
        "the FP convention forbids 'hallucinated'; use 'unmatched'"
    )


def test_research_grade_question_reframed() -> None:
    md = _md()
    assert "research-grade statistical datasets" in md
    assert "research-quality statistical datasets" not in md, (
        "the §6 opening question should read 'research-grade', not 'research-quality'"
    )
    assert "state of the art tools perform when it comes to" not in md, (
        "the §6 opening question should be tightened to 'state-of-the-art ... at producing'"
    )


def test_annex_a_keeps_t1_t2_drops_philosophy() -> None:
    md = _md()
    # T1/T2 snapshot-vs-flow content stays.
    assert "T1 — Snapshot currency" in md or "T1 —" in md, (
        "Annex A must keep the T1 snapshot-currency paragraph"
    )
    assert "T2 — Historical reconstructability" in md or "T2 —" in md, (
        "Annex A must keep the T2 historical-reconstructability paragraph"
    )
    # Philosophy genealogy is cut.
    for term in ("Parmenides", "Heraclitus", "Whitehead"):
        assert term not in md, (
            f"Annex A philosophy genealogy keyword '{term}' must be removed"
        )
