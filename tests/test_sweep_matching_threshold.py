"""Tests for scripts/sweep_matching_threshold.py."""

import csv
import json

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RECON_HEADER = [
    "match_type", "reference_name", "system_name",
    "reference_province", "system_province",
    "reference_fuel", "system_fuel",
    "reference_capacity_mwe", "system_capacity_mwe",
    "capacity_diff_pct", "fuel_match", "status_match",
    "province_match", "reference_source_ref", "system_source_ref",
    "similarity_score",
]


def _write_recon_csv(path, rows):
    """Write a reconciliation CSV with the standard header."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(RECON_HEADER)
        for row in rows:
            w.writerow(row)


# ---------------------------------------------------------------------------
# Core sweep test
# ---------------------------------------------------------------------------


def test_sweep_produces_sensitivity_csv(tmp_path):
    """Sweep script reads reconciliation CSVs and produces matching_sensitivity.csv."""
    recon_dir = tmp_path / "outputs" / "census"
    recon_dir.mkdir(parents=True)
    _write_recon_csv(recon_dir / "reconciliation_test-model-run1.csv", [
        # Exact match (score 100)
        ["exact", "Plant A", "Plant A", "hanoi", "hanoi",
         "coal", "coal", "100", "100", "0.0",
         "True", "True", "True", "", "", "100"],
        # Fuzzy match (score 92 -- above default threshold 90)
        ["fuzzy", "Vung Ang 1", "Vung Ang I", "ha tinh", "ha tinh",
         "coal", "coal", "600", "600", "0.0",
         "True", "True", "True", "", "", "92"],
        # Reference only (no score)
        ["reference_only", "Missed Plant", "", "", "",
         "coal", "", "200", "", "",
         "", "", "", "", "", ""],
    ])

    out_path = tmp_path / "derived" / "matching_sensitivity.csv"

    from scripts.sweep_matching_threshold import sweep_thresholds

    sweep_thresholds(
        recon_root=tmp_path / "outputs",
        output_path=out_path,
    )

    assert out_path.exists(), "matching_sensitivity.csv was not created"

    with open(out_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) > 0
    expected_cols = {"model", "method", "run", "threshold", "f1", "precision", "coverage",
                     "n_matched", "n_fuzzy_above", "n_fuzzy_below"}
    assert expected_cols.issubset(set(reader.fieldnames))

    rows_t75 = [r for r in rows if r["threshold"] == "75"]
    assert len(rows_t75) == 1
    assert int(rows_t75[0]["n_matched"]) == 2  # exact + fuzzy

    rows_t95 = [r for r in rows if r["threshold"] == "95"]
    assert len(rows_t95) == 1
    assert int(rows_t95[0]["n_matched"]) == 1  # only exact


# ---------------------------------------------------------------------------
# Stability analysis tests
# ---------------------------------------------------------------------------


def test_sweep_writes_stability_json(tmp_path):
    """Sweep produces a stability_analysis.json with rank_flips, slopes, and stable_core."""
    recon_dir = tmp_path / "outputs" / "census"
    recon_dir.mkdir(parents=True)

    # Model A: all exact matches (threshold-insensitive)
    _write_recon_csv(recon_dir / "reconciliation_model-a-run1.csv", [
        ["exact", "P1", "P1", "", "", "coal", "coal", "100", "100", "0", "", "", "", "", "", "100"],
        ["exact", "P2", "P2", "", "", "coal", "coal", "200", "200", "0", "", "", "", "", "", "100"],
        ["reference_only", "P3", "", "", "", "coal", "", "300", "", "", "", "", "", "", "", ""],
    ])

    # Model B: one fuzzy match at 88 (demoted at thresholds > 88)
    _write_recon_csv(recon_dir / "reconciliation_model-b-run1.csv", [
        ["exact", "P1", "P1", "", "", "coal", "coal", "100", "100", "0", "", "", "", "", "", "100"],
        ["fuzzy", "P2", "P2x", "", "", "coal", "coal", "200", "200", "0", "", "", "", "", "", "88"],
        ["reference_only", "P3", "", "", "", "coal", "", "300", "", "", "", "", "", "", "", ""],
    ])

    out_csv = tmp_path / "derived" / "matching_sensitivity.csv"

    from scripts.sweep_matching_threshold import sweep_thresholds

    sweep_thresholds(
        recon_root=tmp_path / "outputs",
        output_path=out_csv,
    )

    # Check stability JSON was written alongside CSV
    stability_path = out_csv.parent / "matching_stability.json"
    assert stability_path.exists(), "matching_stability.json was not created"

    data = json.loads(stability_path.read_text(encoding="utf-8"))

    assert "rank_flips" in data
    assert "slopes" in data
    assert "stable_core" in data

    # Model A has no fuzzy matches -> slope should be 0
    a_slopes = [s for s in data["slopes"] if s["model"] == "model-a"]
    assert len(a_slopes) > 0
    assert a_slopes[0]["f1_slope"] == 0.0

    # Model B has a fuzzy match at 88 -> non-zero slope
    b_slopes = [s for s in data["slopes"] if s["model"] == "model-b"]
    assert len(b_slopes) > 0
    assert b_slopes[0]["f1_slope"] < 0.0  # F1 drops as threshold rises


def test_sweep_detects_rank_flip(tmp_path):
    """Sweep detects a rank flip when two models cross at some threshold."""
    recon_dir = tmp_path / "outputs" / "census"
    recon_dir.mkdir(parents=True)

    # Model A: 2 exact + 0 fuzzy => F1 stable; 2 TP out of 3 ref
    _write_recon_csv(recon_dir / "reconciliation_model-a-run1.csv", [
        ["exact", "P1", "P1", "", "", "coal", "coal", "100", "100", "0", "", "", "", "", "", "100"],
        ["exact", "P2", "P2", "", "", "coal", "coal", "200", "200", "0", "", "", "", "", "", "100"],
        ["reference_only", "P3", "", "", "", "coal", "", "300", "", "", "", "", "", "", "", ""],
    ])

    # Model B: 1 exact + 2 fuzzy (scores 80, 93) => beats A at low threshold, loses at high
    _write_recon_csv(recon_dir / "reconciliation_model-b-run1.csv", [
        ["exact", "P1", "P1", "", "", "coal", "coal", "100", "100", "0", "", "", "", "", "", "100"],
        ["fuzzy", "P2", "P2x", "", "", "coal", "coal", "200", "200", "0", "", "", "", "", "", "93"],
        ["fuzzy", "P3", "P3x", "", "", "coal", "coal", "300", "300", "0", "", "", "", "", "", "80"],
    ])

    out_csv = tmp_path / "derived" / "matching_sensitivity.csv"

    from scripts.sweep_matching_threshold import sweep_thresholds

    sweep_thresholds(
        recon_root=tmp_path / "outputs",
        output_path=out_csv,
    )

    stability_path = out_csv.parent / "matching_stability.json"
    data = json.loads(stability_path.read_text(encoding="utf-8"))

    # At threshold 75: B has 3 TP / 0 FP / 0 FN => F1=1.0; A has 2 TP / 0 FP / 1 FN => F1=0.8
    # At threshold 95: B has 1 TP / 2 FP / 0 FN => F1=0.5; A has 2 TP / 0 FP / 1 FN => F1=0.8
    # So there's a flip: B > A at 75, A > B at 95
    assert len(data["rank_flips"]) > 0
    flip_pairs = [(f["model_1"], f["model_2"]) for f in data["rank_flips"]]
    assert ("model-a", "model-b") in flip_pairs or ("model-b", "model-a") in flip_pairs


def test_stable_core_excludes_flipping_models(tmp_path):
    """Stable core should not include models involved in rank flips."""
    recon_dir = tmp_path / "outputs" / "census"
    recon_dir.mkdir(parents=True)

    # Model A: stable (all exact)
    _write_recon_csv(recon_dir / "reconciliation_model-a-run1.csv", [
        ["exact", "P1", "P1", "", "", "coal", "coal", "100", "100", "0", "", "", "", "", "", "100"],
        ["exact", "P2", "P2", "", "", "coal", "coal", "200", "200", "0", "", "", "", "", "", "100"],
        ["reference_only", "P3", "", "", "", "coal", "", "300", "", "", "", "", "", "", "", ""],
    ])

    # Model B: flips with C
    _write_recon_csv(recon_dir / "reconciliation_model-b-run1.csv", [
        ["exact", "P1", "P1", "", "", "coal", "coal", "100", "100", "0", "", "", "", "", "", "100"],
        ["fuzzy", "P2", "P2x", "", "", "coal", "coal", "200", "200", "0", "", "", "", "", "", "93"],
        ["fuzzy", "P3", "P3x", "", "", "coal", "coal", "300", "300", "0", "", "", "", "", "", "80"],
    ])

    # Model C: flips with B (2 exact, 1 ref only - same as A but different for the flip)
    _write_recon_csv(recon_dir / "reconciliation_model-c-run1.csv", [
        ["exact", "P1", "P1", "", "", "coal", "coal", "100", "100", "0", "", "", "", "", "", "100"],
        ["exact", "P2", "P2", "", "", "coal", "coal", "200", "200", "0", "", "", "", "", "", "100"],
        ["reference_only", "P3", "", "", "", "coal", "", "300", "", "", "", "", "", "", "", ""],
    ])

    out_csv = tmp_path / "derived" / "matching_sensitivity.csv"

    from scripts.sweep_matching_threshold import sweep_thresholds

    sweep_thresholds(recon_root=tmp_path / "outputs", output_path=out_csv)

    stability_path = out_csv.parent / "matching_stability.json"
    data = json.loads(stability_path.read_text(encoding="utf-8"))

    # Models involved in flips should not be in stable_core
    flipping = set()
    for f in data["rank_flips"]:
        flipping.add(f["model_1"])
        flipping.add(f["model_2"])

    for m in data["stable_core"]:
        assert m not in flipping, f"{m} is in stable_core but involved in rank flips"
