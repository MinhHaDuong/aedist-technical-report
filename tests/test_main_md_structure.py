"""Ticket 0469 — main.md restructured from synopsis to a proper IMRaD paper.

Adherence tests pin the structural invariants introduced in ticket 0469:

1. No "Synopsis" framing in the title.
2. Rhetorical "## First" / "## Second" / etc. headings replaced by numbered
   IMRaD sections.
3. A structured abstract is present and leads with the frontier-falls-short
   result (frontier agents fall short before the parametric ceiling).
4. Author and affiliation block present.
5. A numbered Introduction section (§1) exists.
6. A Conclusion section exists.
7. Related Work section exists in the body (not only as a standalone annex).
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
MAIN_MD = REPO_ROOT / "slides" / "manuscript" / "main.md"


def _text() -> str:
    if not MAIN_MD.exists():
        pytest.skip("main.md not found")
    return MAIN_MD.read_text(encoding="utf-8")


def test_no_synopsis_framing():
    md = _text()
    assert "Synopsis" not in md, "title still says 'Synopsis' — retitle to a real paper title"
    assert "## First" not in md, "rhetorical '## First' heading not replaced by IMRaD"
    assert "## Second" not in md, "rhetorical '## Second' heading not replaced by IMRaD"
    assert "## Third" not in md, (
        "rhetorical '## Third' heading not replaced by IMRaD — "
        "rename to numbered section heading"
    )
    assert "## Fourth" not in md, "rhetorical '## Fourth' heading not replaced by IMRaD"
    assert "## Fifth" not in md, "rhetorical '## Fifth' heading not replaced by IMRaD"


def test_abstract_present_and_leads_with_frontier():
    """Abstract must be present and lead with the frontier-falls-short result."""
    md = _text()
    assert "**Abstract.**" in md or "## Abstract" in md, (
        "no abstract found in main.md — add a structured abstract"
    )
    # The abstract must mention frontier agents falling short before the parametric ceiling
    abstract_start = md.find("**Abstract.**")
    if abstract_start == -1:
        abstract_start = md.find("## Abstract")
    assert abstract_start != -1
    # Check that "frontier" or "SOTA" appears in the abstract block
    abstract_block = md[abstract_start : abstract_start + 2000]
    assert "frontier" in abstract_block.lower() or "sota" in abstract_block.lower(), (
        "abstract does not mention frontier agents"
    )
    # The abstract mentions the key result: agents fall short of research-grade quality
    has_fall_short = (
        "fall short" in abstract_block.lower()
        or "falls short" in abstract_block.lower()
        or "still fall" in abstract_block.lower()
    )
    assert has_fall_short, (
        "abstract does not lead with the frontier-falls-short result"
    )


def test_abstract_numbers_in_body():
    """Key numeric claims in the abstract (F1 range, ρ) are consistent with the body.

    We check that the batch-2 canonical numbers (0.00, 0.67, 0.37, ρ = 0.92) appear
    somewhere in the manuscript body.  The deeper artifact-level guard lives in
    ``test_abstract_numbers.py::test_abstract_numbers_derived_from_artifact``.

    Ticket 0474 corrected the cohort from batch-1 (16 models / 80 runs) to the
    canonical batch-2 (14 models / 70 runs; exp1_cross_eval.csv).
    """
    md = _text()
    # These numbers appear in the Exp1 §4 results paragraph and §8 Conclusion.
    assert "0.00" in md, "F1 lower bound 0.00 missing from manuscript"
    assert "0.67" in md, "F1 upper bound 0.67 missing from manuscript"
    assert "0.37" in md, "mean F1 0.37 missing from manuscript"
    assert "0.92" in md, "coherence–F1 correlation ρ = 0.92 missing from manuscript"


def test_author_affiliation_present():
    md = _text()
    assert "CIRED" in md or "Ha-Duong" in md, (
        "author or affiliation block missing from main.md"
    )


def test_introduction_section_exists():
    md = _text()
    assert "## 1. Introduction" in md, (
        "numbered Introduction section §1 missing from main.md"
    )


def test_conclusion_section_exists():
    md = _text()
    assert "## 8. Conclusion" in md or "## Conclusion" in md, (
        "Conclusion section missing from main.md"
    )


def test_related_work_in_body():
    md = _text()
    assert "## 9. Related work" in md or "## Related work" in md, (
        "Related Work section missing from the body of main.md — "
        "it should appear as §9 or a named section, not only as an annex"
    )
