"""Ticket 0531 — macros everywhere: manuscript numbers via generated macros.

Three layers of guard:

1. **Fragment vs artifact** — a sample of macro values is re-derived from the
   source CSVs by an INDEPENDENT parse and compared against the committed
   fragment. Never prose-vs-macro (tautological after the conversion: the
   prose IS the macro).
2. **Structural** — the manuscript preamble \\inputs the consolidated
   macros_manuscript.tex; the consolidated file defines no macro twice
   (tectonic would die on `\\newcommand` redefinition).
3. **Usage ratchet** — the UNexpanded body actually uses the macros (a
   revert to literals would pass layer 1 silently), and the review-listed
   stale literals are gone for good.
"""

import csv
import re
import statistics
from pathlib import Path

import pytest
from manuscript_source import MANUSCRIPT, body_raw, raw, strip_comments

from aedist.evaluate import reference_plant_count

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
GEN = REPO_ROOT / "report" / "inputs" / "generated"
CONSOLIDATED = GEN / "macros_manuscript.tex"
REF_CSV = REPO_ROOT / "data" / "reference" / "vietnam_thermal_plants_v2_classified.csv"
XEVAL_CSV = REPO_ROOT / "experiments" / "derived" / "exp1_cross_eval.csv"
SWEEP_CSV = REPO_ROOT / "experiments" / "derived" / "aggregation_sweep.csv"
SCREEN_CSV = GEN / "tab_screen_validation_within_model.csv"
FUSION_CSV = GEN / "fusion_mvp.csv"


def _macro(name: str) -> str:
    """Value of \\newcommand{\\<name>}{...} in the consolidated file."""
    if not CONSOLIDATED.exists():
        pytest.skip(f"{CONSOLIDATED} not generated")
    m = re.search(
        rf"\\newcommand{{\\{re.escape(name)}}}{{([^}}]*)}}",
        CONSOLIDATED.read_text(encoding="utf-8"),
    )
    assert m, f"\\{name} not defined in {CONSOLIDATED.name}"
    return m.group(1)


def _screen_metric(metric: str) -> str:
    if not SCREEN_CSV.exists():
        pytest.skip(f"{SCREEN_CSV} not generated")
    for row in csv.DictReader(SCREEN_CSV.open(encoding="utf-8")):
        if row["metric"] == metric:
            return row["value"]
    raise AssertionError(f"metric {metric!r} not in {SCREEN_CSV.name}")


# --- 1. Fragment vs artifact (independent parse) ------------------------------


def test_screen_tau_cap_matches_artifact():
    assert _macro("ScreenTauCap") == _screen_metric("stratified_kendall_tau_cap_distinct")


def test_screen_binary_gap_matches_artifact():
    assert _macro("ScreenBinaryGap") == _screen_metric("per_model_binary_gap")


def test_exp1_f1_mean_matches_artifact():
    rows = list(csv.DictReader(XEVAL_CSV.open(encoding="utf-8")))
    mean = statistics.mean(float(r["accuracy_f1"]) for r in rows if r.get("accuracy_f1"))
    assert _macro("ExpOneFOneMean") == f"{mean:.2f}"


def test_exp1_status_acc_matches_artifact():
    rows = list(csv.DictReader(XEVAL_CSV.open(encoding="utf-8")))
    vals = [float(r["accuracy_status"]) for r in rows if r.get("accuracy_status") not in (None, "", "nan")]
    assert _macro("ExpOneStatusAcc") == f"{statistics.mean(vals):.2f}"


def test_reference_count_matches_csv_and_library():
    rows = list(csv.DictReader(REF_CSV.open(encoding="utf-8")))
    n = reference_plant_count()
    assert len(rows) == n, "CSV row count and reference_plant_count() diverge"
    assert _macro("NumRefPlants") == str(n)


def test_reference_coal_count_matches_csv():
    rows = list(csv.DictReader(REF_CSV.open(encoding="utf-8")))
    coal = sum(1 for r in rows if r["fuel"] == "coal")
    assert _macro("RefCoalCount") == str(coal)
    assert _macro("RefGasOilCount") == str(len(rows) - coal)


def test_agg_best_union_recall_matches_sweep():
    if not SWEEP_CSV.exists():
        pytest.skip(f"{SWEEP_CSV} not generated")
    for r in csv.DictReader(SWEEP_CSV.open(encoding="utf-8")):
        if (
            r["merge_method"] == "union"
            and r["diversity_rule"] == "cross_model_high"
            and r["pool_size"] == "3"
        ):
            assert _macro("AggBestUnionRecall") == f"{float(r['mean_recall']):.3f}"
            return
    raise AssertionError("best-union sweep cell not found")


def test_fusion_r2_e1_tp_matches_csv():
    if not FUSION_CSV.exists():
        pytest.skip(f"{FUSION_CSV} not generated")
    for r in csv.DictReader(FUSION_CSV.open(encoding="utf-8")):
        if r["regime"] == "E1" and r["rule"] == "r2_models":
            assert _macro("FusionRTwoEOneTP") == r["tp"]
            return
    raise AssertionError("E1/r2_models row not found in fusion_mvp.csv")


# --- 2. Structural -------------------------------------------------------------


def test_preamble_inputs_consolidated_macros():
    preamble = strip_comments(raw().split("\\begin{document}", 1)[0])
    assert "\\input{../../report/inputs/generated/macros_manuscript.tex}" in preamble, (
        "manuscript preamble must \\input the consolidated macros_manuscript.tex"
    )


def test_consolidated_macros_define_nothing_twice():
    if not CONSOLIDATED.exists():
        pytest.skip(f"{CONSOLIDATED} not generated")
    names = re.findall(
        r"\\newcommand{\\([A-Za-z]+)}", CONSOLIDATED.read_text(encoding="utf-8")
    )
    dups = sorted({n for n in names if names.count(n) > 1})
    assert not dups, f"duplicate macro definitions in {CONSOLIDATED.name}: {dups}"


def test_macro_names_are_letters_only():
    """Digits in a \\newcommand name silently truncate the TeX control word
    (the \\FusionNE1Runs lesson) — ban them in the consolidated file."""
    if not CONSOLIDATED.exists():
        pytest.skip(f"{CONSOLIDATED} not generated")
    bad = re.findall(
        r"\\newcommand{\\[A-Za-z]*[0-9][^}]*}",
        CONSOLIDATED.read_text(encoding="utf-8"),
    )
    assert not bad, f"macro names must be letters-only: {bad}"


# --- 3. Usage ratchet -----------------------------------------------------------


def _unexpanded_body() -> str:
    """The body WITHOUT macro expansion — what the author actually typed."""
    if not MANUSCRIPT.exists():
        pytest.skip("main.tex not found")
    return strip_comments(body_raw())


def test_body_uses_the_macros():
    text = _unexpanded_body()
    for name in ("\\ScreenTauCap", "\\NumRefPlants", "\\ExpOneFOneMean", "\\AggUnionGainX"):
        assert name in text, f"manuscript body no longer uses {name} — literal crept back?"


def test_stale_review_literals_gone():
    """The 2026-06-11 review-listed stale numbers must never reappear."""
    text = _unexpanded_body()
    for needle in ("+0.215", "\\$2.85", "0.146", "(65 concordant"):
        assert needle not in text, f"stale literal {needle!r} back in main.tex"
