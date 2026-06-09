"""Ticket 0501 — manuscript body numbers are re-derived from committed artifacts.

Companion to ``test_manuscript_reference_count.py`` (the plant-count literal)
and ``test_abstract_numbers.py`` (the abstract F1 literals). This file closes
the remaining ungoverned literals that #906 drifted silently: the Annex B fuel
split, the §7 difficulty-table total recognition rate, and the §6 run-fusion
numbers. Each assertion re-derives the value from its source artifact by an
independent parse, then asserts the rounded literal is present in main.md.

Scope note: the §4 per-run attribute accuracies (fuel/status/province) are
deliberately NOT guarded here — ticket 0502 owns the province 0.61→0.89
anomaly, which is a scoring change, not a 177 re-score effect.
"""

import csv
import re
import statistics
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
MAIN_MD = REPO_ROOT / "slides" / "manuscript" / "main.md"
REF_CSV = REPO_ROOT / "data" / "reference" / "vietnam_thermal_plants_v2_classified.csv"
SWEEP_CSV = REPO_ROOT / "experiments" / "derived" / "aggregation_sweep.csv"
XEVAL_CSV = REPO_ROOT / "experiments" / "derived" / "exp1_cross_eval.csv"
DIFF_TEX = REPO_ROOT / "report" / "inputs" / "generated" / "tab_status_difficulty.tex"


def _md() -> str:
    if not MAIN_MD.exists():
        pytest.skip("main.md not found")
    return MAIN_MD.read_text(encoding="utf-8")


def _sweep_cell(method: str, rule: str, pool: int) -> dict:
    if not SWEEP_CSV.exists():
        pytest.skip(f"{SWEEP_CSV} not generated")
    for r in csv.DictReader(SWEEP_CSV.open(encoding="utf-8")):
        if (
            r["merge_method"] == method
            and r["diversity_rule"] == rule
            and r["pool_size"] == str(pool)
        ):
            return r
    raise AssertionError(f"sweep cell {method}/{rule}/pool{pool} not in {SWEEP_CSV}")


def test_annex_b_fuel_split_matches_reference():
    """Annex B 'coal (N) and gas/gas-oil (M)' matches the reference CSV fuel column."""
    if not REF_CSV.exists():
        pytest.skip(f"{REF_CSV} not found")
    rows = list(csv.DictReader(REF_CSV.open(encoding="utf-8")))
    coal = sum(1 for r in rows if r["fuel"] == "coal")
    non_coal = len(rows) - coal
    md = _md()
    assert f"coal ({coal})" in md, f"Annex B coal count should be {coal}"
    assert f"gas/gas-oil ({non_coal})" in md, (
        f"Annex B gas/gas-oil count should be {non_coal} (all non-coal)"
    )


def test_difficulty_table_total_rate_matches_artifact():
    """§7 'All' overall recognition rate matches the Ensemble row of the generated table."""
    if not DIFF_TEX.exists():
        pytest.skip(f"{DIFF_TEX} not generated")
    tex = DIFF_TEX.read_text(encoding="utf-8")
    m = re.search(r"Ensemble\s*&\s*\d+\s*&\s*[\d.]+\\%\s*&\s*([\d.]+)\\%", tex)
    assert m, "could not parse the Ensemble row recognition rate from the artifact"
    rate = m.group(1)  # e.g. "26.6"
    assert f"{rate}%" in _md(), (
        f"§7 difficulty-table overall recognition rate should be {rate}% (from {DIFF_TEX.name})"
    )


def test_fusion_numbers_match_sweep():
    """§6 union recall/F1 and intra-model recall match aggregation_sweep.csv."""
    md = _md()
    best_union = _sweep_cell("union", "cross_model_high", 3)
    recall = float(best_union["mean_recall"])
    f1 = float(best_union["mean_f1"])
    intra = _sweep_cell("union", "intra_model", 3)
    intra_recall = float(intra["mean_recall"])
    assert f"{recall:.3f}" in md, f"§6 best-union recall should be {recall:.3f}"
    assert f"{f1:.3f}" in md, f"§6 best-union F1 should be {f1:.3f}"
    assert f"{intra_recall:.3f}" in md, f"§6 intra-model recall should be {intra_recall:.3f}"


def test_fusion_single_run_baseline_matches_xeval():
    """§6 single-run mean recall matches the Experiment 1 cross-eval artifact."""
    if not XEVAL_CSV.exists():
        pytest.skip(f"{XEVAL_CSV} not generated")
    rows = list(csv.DictReader(XEVAL_CSV.open(encoding="utf-8")))
    mean_recall = statistics.mean(float(r["accuracy_coverage"]) for r in rows)
    assert f"{mean_recall:.3f}" in _md(), (
        f"§6 single-run mean recall should be {mean_recall:.3f}"
    )


def test_attribute_accuracies_match_xeval():
    """§4 fuel/status/province matched-row accuracies match the cross-eval artifact.

    Ticket 0502: these three literals were frozen at the 16-model/80-run vintage
    and drifted (province 0.61 vs artifact 0.89) until this guard. Each mean is
    re-derived from exp1_cross_eval.csv and asserted present in the manuscript.
    """
    if not XEVAL_CSV.exists():
        pytest.skip(f"{XEVAL_CSV} not generated")
    rows = list(csv.DictReader(XEVAL_CSV.open(encoding="utf-8")))
    md = _md()
    for col, label in (
        ("accuracy_fuel", "fuel"),
        ("accuracy_status", "status"),
        ("accuracy_province", "province"),
    ):
        vals = [
            float(r[col]) for r in rows if r.get(col) not in (None, "", "nan")
        ]
        mean = statistics.mean(vals)
        assert f"{mean:.2f}" in md, (
            f"§4 mean {label} accuracy should be {mean:.2f} (from {XEVAL_CSV.name})"
        )
