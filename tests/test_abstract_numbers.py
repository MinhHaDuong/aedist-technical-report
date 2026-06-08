"""Ticket 0474 — abstract F1 literals are re-derived from the committed artifact.

The adherence invariant: whenever ``macros_exp1_run_stats.tex`` is regenerated
from ``exp1_cross_eval.csv``, the abstract in ``main.md`` must still contain
the same rounded numbers.  The test fails if either the macro file or the
manuscript drifts independently.

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


def _abstract_block(md: str) -> str:
    """Return the abstract paragraph (up to 2000 chars from '**Abstract.**')."""
    start = md.find("**Abstract.**")
    if start == -1:
        pytest.skip("no abstract block found in main.md")
    return md[start : start + 2000]


def _parse_macro(tex: str, name: str) -> str:
    """Return the value inside \\newcommand{\\<name>}{<value>}."""
    match = re.search(rf"\\newcommand{{\\{re.escape(name)}}}{{([^}}]+)}}", tex)
    if not match:
        raise AssertionError(f"\\{name} not found in {MACROS_FILE}")
    return match.group(1)


def test_abstract_numbers_derived_from_artifact():
    """Abstract F1 min, mean, max match the committed macros_exp1_run_stats.tex."""
    if not MACROS_FILE.exists():
        pytest.skip(
            f"{MACROS_FILE} not yet generated — "
            "run: make -f experiments/render.mk report-figures"
        )
    macros = MACROS_FILE.read_text(encoding="utf-8")
    min_f1 = float(_parse_macro(macros, "ExpOneFOneMin"))
    mean_f1 = float(_parse_macro(macros, "ExpOneFOneMean"))
    max_f1 = float(_parse_macro(macros, "ExpOneFOneMax"))

    abstract = _abstract_block(_text())

    assert f"{min_f1:.2f}" in abstract, (
        f"F1 lower bound {min_f1:.2f} (from macros_exp1_run_stats.tex) "
        "missing from the abstract — update slides/manuscript/main.md"
    )
    assert f"{mean_f1:.2f}" in abstract, (
        f"mean F1 {mean_f1:.2f} (from macros_exp1_run_stats.tex) "
        "missing from the abstract — update slides/manuscript/main.md"
    )
    assert f"{max_f1:.2f}" in abstract, (
        f"F1 upper bound {max_f1:.2f} (from macros_exp1_run_stats.tex) "
        "missing from the abstract — update slides/manuscript/main.md"
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
