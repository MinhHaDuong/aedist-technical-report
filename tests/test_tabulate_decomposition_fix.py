"""Tests for tabulate_decomposition_fix: FP rate before/after prompt fix."""

from pathlib import Path

import pytest


def _write_reconciliation_csv(directory: Path, model: str, run: int, rows: list[dict]) -> Path:
    """Write a synthetic reconciliation CSV."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"reconciliation_{model}-run{run}.csv"
    header = "match_type,reference_name,system_name,reference_province,system_province,reference_fuel,system_fuel,reference_capacity_mwe,system_capacity_mwe,capacity_diff_pct,fuel_match,status_match,province_match,reference_source_ref,system_source_ref,similarity_score"
    lines = [header]
    for row in rows:
        mt = row["match_type"]
        lines.append(f"{mt},ref,sys,prov,prov,coal,coal,100,100,0,True,True,True,,,100")
    path.write_text("\n".join(lines) + "\n")
    return path


def test_fp_rate_from_reconciliation(tmp_path):
    """Known match_type values produce correct FP rate."""
    from aedist.tabulate_decomposition_fix import fp_rate_from_csv

    rows = [
        {"match_type": "exact"},
        {"match_type": "exact"},
        {"match_type": "system_only"},
        {"match_type": "fuzzy_capacity_diff"},
        {"match_type": "reference_only"},  # excluded from denominator
        {"match_type": "system_only"},
    ]
    path = _write_reconciliation_csv(tmp_path, "test-model", 1, rows)
    fp_count, fp_rate = fp_rate_from_csv(path)

    # 2 system_only out of 5 non-reference_only rows
    assert fp_count == 2
    assert fp_rate == pytest.approx(2 / 5)


def test_fp_rate_zero_when_no_system_only(tmp_path):
    """Zero FP when no system_only rows."""
    from aedist.tabulate_decomposition_fix import fp_rate_from_csv

    rows = [
        {"match_type": "exact"},
        {"match_type": "fuzzy"},
        {"match_type": "reference_only"},
    ]
    path = _write_reconciliation_csv(tmp_path, "clean-model", 1, rows)
    fp_count, fp_rate = fp_rate_from_csv(path)
    assert fp_count == 0
    assert fp_rate == 0.0


def test_compute_table_structure(tmp_path):
    """Verify returned dict structure with synthetic before/after dirs."""
    from aedist.tabulate_decomposition_fix import compute_table

    before = tmp_path / "before"
    after = tmp_path / "after"

    # Model alpha: 3 runs before with high FP, 3 runs after with low FP
    for run in range(1, 4):
        _write_reconciliation_csv(
            before,
            "alpha",
            run,
            [{"match_type": "exact"}] * 5 + [{"match_type": "system_only"}] * 5,
        )
        _write_reconciliation_csv(
            after,
            "alpha",
            run,
            [{"match_type": "exact"}] * 9 + [{"match_type": "system_only"}] * 1,
        )

    table = compute_table(before_dir=before, after_dir=after)

    assert "before" in table
    assert "after" in table
    assert len(table["before"]) == 1
    assert len(table["after"]) == 1

    before_row = table["before"][0]
    assert before_row["model"] == "alpha"
    assert len(before_row["runs"]) == 3
    assert before_row["mean_fp_rate"] == pytest.approx(0.5)

    after_row = table["after"][0]
    assert after_row["model"] == "alpha"
    assert len(after_row["runs"]) == 3
    assert after_row["mean_fp_rate"] == pytest.approx(0.1)


def test_cli_writes_tex(tmp_path):
    """main() writes valid LaTeX with model names."""
    from aedist.tabulate_decomposition_fix import main

    before = tmp_path / "before"
    after = tmp_path / "after"

    for run in range(1, 4):
        _write_reconciliation_csv(
            before,
            "gpt-5.4",
            run,
            [{"match_type": "exact"}] * 5 + [{"match_type": "system_only"}] * 3,
        )
        _write_reconciliation_csv(
            after,
            "gpt-5.4",
            run,
            [{"match_type": "exact"}] * 7 + [{"match_type": "system_only"}] * 1,
        )

    out = tmp_path / "tab_decomposition_fix.tex"
    main(
        [
            "--output",
            str(out),
            "--before-dir",
            str(before),
            "--after-dir",
            str(after),
        ]
    )

    text = out.read_text()
    assert "\\begin{table}" in text
    assert "GPT-5.4" in text
    assert "decomposition-fix" in text


def test_defaults_point_at_derived_decomp_fix():
    """Defaults must point at the P2 reconcile-from-archive outputs (0424).

    The archive dirs hold raw model CSVs, not reconciliation CSVs; the
    score.mk decomp-fix step regenerates reconciliation_*.csv under
    experiments/derived/decomp_fix/. Source inspection, no subprocess.
    """
    src = Path("src/aedist/tabulate_decomposition_fix.py").read_text()
    assert 'Path("experiments/derived/decomp_fix/rag_per_fuel")' in src
    assert 'Path("experiments/derived/decomp_fix/rag_per_fuel_v2")' in src
