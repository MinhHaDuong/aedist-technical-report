"""The stale Exp2 'arms' report table is retired for the 2x2 (ticket 0362).

The report presents Experiment 2 as the live 2x2 features design (tab_exp2_2x2),
not the old arm-level table (tab_exp2_arms). Only the dead report-table producer
(tabulate_exp2_arms) is removed. The 'arms' MART pipeline is the 2x2's data
foundation and produces the slides' coverage/cost figures (plot_exp2_arms_split,
tabulate_exp2_arms_runs), and plot_exp2_arms_comparison still feeds the live
manuscript (slides/manuscript/main.md, Figure 3) — all must survive, guarded
below. (Renaming the mart-internal 'arms' terminology is out of scope: 0364.)
"""

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent


def _tracked(predicate) -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [REPO_ROOT / rel for rel in out.split("\0") if rel and predicate(rel)]


def test_report_presents_2x2_not_arms_table():
    report_tex = _tracked(lambda r: r.startswith("report/") and r.endswith(".tex"))
    arms_hits = [
        str(f.relative_to(REPO_ROOT))
        for f in report_tex
        if "tab_exp2_arms" in f.read_text()
    ]
    has_2x2 = any("tab_exp2_2x2" in f.read_text() for f in report_tex)
    assert not arms_hits, f"report still includes the retired tab_exp2_arms: {arms_hits}"
    assert has_2x2, "report Exp2 must present the 2x2 (tab_exp2_2x2)"


def test_root_makefile_drops_arms_table():
    makefile = (REPO_ROOT / "Makefile").read_text()
    assert "tab_exp2_arms.tex" not in makefile, (
        "root Makefile still references the retired tab_exp2_arms.tex table"
    )


def test_dead_arms_report_table_producer_removed():
    dead = "src/aedist/tabulate_exp2_arms.py"
    assert not (REPO_ROOT / dead).exists(), (
        f"the dead report-table producer should be deleted: {dead}"
    )


def test_load_bearing_arms_modules_kept():
    """Regression guard: these feed the live 2x2, the slides coverage/cost figs,
    and the manuscript (plot_exp2_arms_comparison -> main.md Figure 3)."""
    required = [
        "src/aedist/plot_exp2_arms_split.py",
        "src/aedist/tabulate_exp2_arms_runs.py",
        "src/aedist/plot_exp2_arms_comparison.py",
    ]
    missing = [p for p in required if not (REPO_ROOT / p).exists()]
    assert not missing, f"load-bearing 'arms' modules must NOT be deleted: {missing}"
