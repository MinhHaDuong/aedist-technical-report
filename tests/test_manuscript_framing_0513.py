"""Ticket 0513 — final framing + language pass on the arXiv manuscript.

Guards the prose-quality changes that ticket 0513 lands on
``slides/manuscript/main.tex``:

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


import pytest
from manuscript_source import body, section

pytestmark = pytest.mark.adherence

def _md() -> str:
    return body()


def _section_1_body() -> str:
    """Text of §1, the Introduction (label-keyed since ticket 0561)."""
    return section("sec:intro")


def test_no_contributions_heading() -> None:
    """Negative guard only: contributions must not get their own heading.

    The positive pin on the bold run-in label was demoted to
    docs/editorial-brief.md (CI polarity rule, 0557; author intro
    rewrite 2026-06-12 restructured §1).
    """
    sec1 = _section_1_body()
    assert "\\section{Contributions}" not in sec1 and "\\subsection{Contributions}" not in sec1, (
        "contributions stay inside §1 prose, never a separate heading"
    )


def test_plausible_text_generator_reframing() -> None:
    md = _md()
    assert "random words generator" not in md, (
        "'random words generator' was reframed away (0513); never reintroduce it"
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
