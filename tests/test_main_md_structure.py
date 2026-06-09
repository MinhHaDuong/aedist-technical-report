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


MACROS_FILE = REPO_ROOT / "report" / "inputs" / "generated" / "macros_exp1_run_stats.tex"


def _parse_macro(tex: str, name: str) -> str:
    """Return the value inside \\newcommand{\\<name>}{<value>} (string-based, no regex)."""
    marker = "\\newcommand{\\" + name + "}{"
    start = tex.find(marker)
    assert start != -1, f"macro {name} not found in {MACROS_FILE.name}"
    start += len(marker)
    return tex[start : tex.index("}", start)]


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
    """Key numeric claims (F1 min/mean/max, ρ) appear in the manuscript body.

    The F1 stats are read from ``macros_exp1_run_stats.tex`` (regenerated from
    ``exp1_cross_eval.csv``) rather than hardcoded, so a re-score that shifts the
    numbers cannot leave this guard silently stale — it tracks the artifact, like
    ``test_abstract_numbers.py::test_abstract_numbers_derived_from_artifact``.

    Ticket 0474 corrected the cohort from batch-1 (16 models / 80 runs) to the
    canonical batch-2 (14 models / 70 runs; exp1_cross_eval.csv). Ticket 0497
    de-hardcoded the F1 literals after the 180→177 reference re-score.
    """
    md = _text()
    if not MACROS_FILE.exists():
        pytest.skip(f"{MACROS_FILE.name} not yet generated")
    macros = MACROS_FILE.read_text(encoding="utf-8")
    # These F1 stats appear in the Exp1 §4 results paragraph and the abstract.
    for macro in ("ExpOneFOneMin", "ExpOneFOneMean", "ExpOneFOneMax"):
        val = _parse_macro(macros, macro)
        assert val in md, f"F1 stat {val} ({macro}) missing from manuscript body — update main.md"
    # ρ = 0.92 has no generated macro (coherence–F1 Spearman computed in §4); literal guard.
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
