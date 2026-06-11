"""Tickets 0474 + 0532 — Exp1 F1 literals are re-derived from the committed artifact.

The adherence invariant (0474): whenever ``macros_exp1_run_stats.tex`` is
regenerated from ``exp1_cross_eval.csv``, the manuscript must still contain
the same rounded numbers wherever it quotes them.  The test fails if either
the macro file or the manuscript drifts independently.

Ticket 0532 round 2 (author reading-1 brief): F1 detail leaves the abstract,
so the quoted sites are now the [@sec:exp1] Results paragraph (min, mean, max)
and the Conclusion (min, max).  The abstract is asserted F1-free in
``test_manuscript_cohort_and_caveats.py::test_abstract_register_follows_author_brief``.

Pairs with ``test_main_md_structure.py::test_abstract_present_and_leads_with_frontier``,
which checks structural presence; this test checks numeric consistency.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
MAIN_MD = REPO_ROOT / "slides" / "manuscript" / "main.md"
MACROS_FILE = REPO_ROOT / "report" / "inputs" / "generated" / "macros_exp1_run_stats.tex"


def _text() -> str:
    if not MAIN_MD.exists():
        pytest.skip("main.md not found")
    return MAIN_MD.read_text(encoding="utf-8")


def _exp1_results_paragraph(md: str) -> str:
    """The [@sec:exp1] Results paragraph quoting the run statistics."""
    start = md.find("**Results: model memory alone yields")
    if start == -1:
        pytest.skip("Exp1 results paragraph not found in main.md")
    return md[start : md.find("\n", start)]


def _conclusion(md: str) -> str:
    heading = "## Conclusion {#sec:conclusion}"
    if heading not in md:
        pytest.skip("conclusion section not found in main.md")
    return md.split(heading)[1].split("\\appendix")[0]


def _parse_macro(tex: str, name: str) -> str:
    """Return the value inside \\newcommand{\\<name>}{<value>}."""
    match = re.search(rf"\\newcommand{{\\{re.escape(name)}}}{{([^}}]+)}}", tex)
    if not match:
        raise AssertionError(f"\\{name} not found in {MACROS_FILE}")
    return match.group(1)


def test_exp1_f1_numbers_derived_from_artifact():
    """Quoted F1 min, mean, max match the committed macros_exp1_run_stats.tex."""
    if not MACROS_FILE.exists():
        pytest.skip(
            f"{MACROS_FILE} not yet generated — "
            "run: make -f experiments/render.mk report-figures"
        )
    macros = MACROS_FILE.read_text(encoding="utf-8")
    min_f1 = float(_parse_macro(macros, "ExpOneFOneMin"))
    mean_f1 = float(_parse_macro(macros, "ExpOneFOneMean"))
    max_f1 = float(_parse_macro(macros, "ExpOneFOneMax"))

    md = _text()
    results = _exp1_results_paragraph(md)
    conclusion = _conclusion(md)

    for value, label in ((min_f1, "F1 lower bound"), (mean_f1, "mean F1"), (max_f1, "F1 upper bound")):
        assert f"{value:.2f}" in results, (
            f"{label} {value:.2f} (from macros_exp1_run_stats.tex) "
            "missing from the Exp1 results paragraph — update slides/manuscript/main.md"
        )
    for value, label in ((min_f1, "F1 lower bound"), (max_f1, "F1 upper bound")):
        assert f"{value:.2f}" in conclusion, (
            f"{label} {value:.2f} (from macros_exp1_run_stats.tex) "
            "missing from the conclusion — update slides/manuscript/main.md"
        )


def test_macros_exp1_run_stats_present():
    """The macro file exists and contains the expected macro names."""
    if not MACROS_FILE.exists():
        pytest.skip(
            f"{MACROS_FILE} not yet generated — "
            "run: make -f experiments/render.mk report-figures"
        )
    macros = MACROS_FILE.read_text(encoding="utf-8")
    for name in ("ExpOneFOneMin", "ExpOneFOneMean", "ExpOneFOneMax", "ExpOneNRuns", "ExpOneNModels"):
        assert f"\\{name}" in macros, (
            f"\\{name} missing from {MACROS_FILE} — "
            "regenerate with: make -f experiments/render.mk report-figures"
        )
