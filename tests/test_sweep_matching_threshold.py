"""Tests for scripts/sweep_matching_threshold.py."""

import csv


def test_sweep_produces_sensitivity_csv(tmp_path):
    """Sweep script reads reconciliation CSVs and produces matching_sensitivity.csv."""
    # Create a minimal reconciliation CSV with similarity_score column
    recon_dir = tmp_path / "outputs" / "census"
    recon_dir.mkdir(parents=True)
    recon_csv = recon_dir / "reconciliation_test-model-run1.csv"
    with open(recon_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "match_type", "reference_name", "system_name",
            "reference_province", "system_province",
            "reference_fuel", "system_fuel",
            "reference_capacity_mwe", "system_capacity_mwe",
            "capacity_diff_pct", "fuel_match", "status_match",
            "province_match", "reference_source_ref", "system_source_ref",
            "similarity_score",
        ])
        # Exact match (score 100)
        w.writerow([
            "exact", "Plant A", "Plant A", "hanoi", "hanoi",
            "coal", "coal", "100", "100", "0.0",
            "True", "True", "True", "", "", "100",
        ])
        # Fuzzy match (score 92 -- above default threshold 90)
        w.writerow([
            "fuzzy", "Vung Ang 1", "Vung Ang I", "ha tinh", "ha tinh",
            "coal", "coal", "600", "600", "0.0",
            "True", "True", "True", "", "", "92",
        ])
        # Reference only (no score)
        w.writerow([
            "reference_only", "Missed Plant", "", "", "",
            "coal", "", "200", "", "",
            "", "", "", "", "", "",
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

    # Should have one row per threshold per model/method/run combination
    assert len(rows) > 0
    # Check expected columns
    expected_cols = {"model", "method", "run", "threshold", "f1", "precision", "coverage",
                     "n_matched", "n_fuzzy_above", "n_fuzzy_below"}
    assert expected_cols.issubset(set(reader.fieldnames))

    # At threshold 75, the fuzzy match (score 92) should be kept
    rows_t75 = [r for r in rows if r["threshold"] == "75"]
    assert len(rows_t75) == 1
    assert int(rows_t75[0]["n_matched"]) == 2  # exact + fuzzy

    # At threshold 95, the fuzzy match (score 92) should be demoted
    rows_t95 = [r for r in rows if r["threshold"] == "95"]
    assert len(rows_t95) == 1
    assert int(rows_t95[0]["n_matched"]) == 1  # only exact
