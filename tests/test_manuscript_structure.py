"""Ticket 0469 — the manuscript restructured from synopsis to a proper IMRaD paper.

Adherence tests pin the structural invariants introduced in ticket 0469
(retargeted at slides/manuscript/main.tex by ticket 0524):

1. No "Synopsis" framing in the title.
2. Rhetorical "First" / "Second" / etc. section headings replaced by IMRaD.
3. A structured abstract is present and leads with the frontier-falls-short
   result (frontier agents fall short before the parametric ceiling).
4. Author and affiliation block present.
5. A labelled Introduction section exists.
6. A Conclusion section exists.
7. Related Work section exists in the body (not only as a standalone annex).
"""

from pathlib import Path

import pytest
from manuscript_source import body, raw

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
MACROS_FILE = REPO_ROOT / "report" / "inputs" / "generated" / "macros_exp1_run_stats.tex"


def _parse_macro(tex: str, name: str) -> str:
    """Return the value inside \\newcommand{\\<name>}{<value>} (string-based, no regex)."""
    marker = "\\newcommand{\\" + name + "}{"
    start = tex.find(marker)
    assert start != -1, f"macro {name} not found in {MACROS_FILE.name}"
    start += len(marker)
    return tex[start : tex.index("}", start)]


def test_no_synopsis_framing():
    text = body()
    assert "Synopsis" not in raw(), "title still says 'Synopsis' — retitle to a real paper title"
    for word in ("First", "Second", "Third", "Fourth", "Fifth"):
        assert f"\\section{{{word}}}" not in text, (
            f"rhetorical '{word}' section heading not replaced by IMRaD"
        )


def test_abstract_present_and_leads_with_frontier():
    """Abstract must be present and lead with the frontier-falls-short result."""
    text = body()
    assert "\\begin{abstract}" in text, (
        "no abstract environment found in main.tex — add a structured abstract"
    )
    abstract_block = text[text.find("\\begin{abstract}") :][:2200]
    assert "frontier" in abstract_block.lower() or "sota" in abstract_block.lower(), (
        "abstract does not mention frontier agents"
    )
    has_fall_short = (
        "fall short" in abstract_block.lower()
        or "falls short" in abstract_block.lower()
        or "still fall" in abstract_block.lower()
    )
    assert has_fall_short, "abstract does not lead with the frontier-falls-short result"


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
    text = body()
    if not MACROS_FILE.exists():
        pytest.skip(
            f"{MACROS_FILE} not yet generated — "
            "run: make -f experiments/render.mk report-figures"
        )
    macros = MACROS_FILE.read_text(encoding="utf-8")
    for macro in ("ExpOneFOneMin", "ExpOneFOneMean", "ExpOneFOneMax"):
        val = _parse_macro(macros, macro)
        assert val in text, f"F1 stat {val} ({macro}) missing from manuscript body — update main.tex"
    # ρ = 0.92 has no generated macro (coherence–F1 Spearman computed in §4); literal guard.
    assert "0.92" in text, "coherence–F1 correlation ρ = 0.92 missing from manuscript"


def test_author_affiliation_present():
    text = raw()
    assert "CIRED" in text or "Ha-Duong" in text, (
        "author or affiliation block missing from main.tex"
    )


def test_introduction_section_exists():
    """Introduction section present and symbolically labelled."""
    assert "\\section{Introduction}\\label{sec:intro}" in body(), (
        "labelled Introduction section missing from main.tex"
    )


def test_conclusion_section_exists():
    """Conclusion heading present and symbolically labelled."""
    assert "\\section{Conclusion}\\label{sec:conclusion}" in body(), (
        "labelled Conclusion section missing from main.tex"
    )


def test_related_work_in_body():
    """Related Work must appear in the body, not only as an annex.

    Ticket 0512 split Related Work into a numbered empirical-landscape section
    and an unnumbered methods section before the Conclusion.
    """
    assert "\\section{Related Work — Empirical landscape}\\label{sec:related-empirical}" in body(), (
        "Related Work — Empirical landscape section missing from the body of "
        "main.tex — it should appear as a labelled section, not only as an annex"
    )
