"""Tests for aedist.tabulate_exp3_fn_triage.

These tests cover the summary/tabulation side (generate_summary, _generate_latex)
using a fixture CSV with known bucket counts — no arm3_flat data required.
The worksheet-generation path (generate_worksheet) is an integration test that
needs the real arm3_flat directory and is marked accordingly.
"""

import csv

import pytest

from aedist.tabulate_exp3_fn_triage import (
    ALLOWED_BUCKETS,
    _generate_latex,
    _in_gem,
    _mentioned_in_narrative,
    generate_summary,
)

# ---------------------------------------------------------------------------
# Unit tests — pure functions
# ---------------------------------------------------------------------------


def test_allowed_buckets_are_four():
    assert ALLOWED_BUCKETS == {"comparateur", "liste", "définition", "résidu"}


def test_in_gem_exact_match():
    assert _in_gem("Vinh Tan 1", ["Vinh Tan 1", "Vinh Tan 2"])


def test_in_gem_no_match():
    assert not _in_gem("Some Unknown Plant XYZ", ["Vinh Tan 1"])


def test_in_gem_empty_gem_list():
    assert not _in_gem("Any Plant", [])


def test_mentioned_in_narrative_full_name():
    assert _mentioned_in_narrative("Quảng Trạch 2", "The Quảng Trạch 2 plant is...")


def test_mentioned_in_narrative_long_word():
    # "Nhơn Trạch" contains "nhơn" (4 chars) and "trạch" (5 chars), both under 6.
    # Full name must match verbatim (same order) for a hit.
    assert _mentioned_in_narrative("LNG Nhơn Trạch 3", "the LNG Nhơn Trạch 3 facility")


def test_mentioned_in_narrative_short_name_needs_verbatim():
    # "LNG" is only 3 chars; full-name match "lng" in text will hit.
    # The function matches full name first before checking words.
    assert _mentioned_in_narrative("LNG", "this mentions LNG in context")


def test_mentioned_in_narrative_absent():
    assert not _mentioned_in_narrative("Very Obscure Plant Name", "nothing relevant here")


# ---------------------------------------------------------------------------
# generate_summary — fixture-based
# ---------------------------------------------------------------------------


def _write_fixture_csv(tmp_path, rows: list[dict]):
    """Write a fixture triage CSV and return its path."""
    from pathlib import Path as _Path

    p = _Path(tmp_path) / "fn_triage.csv"
    fieldnames = [
        "reference_name", "ref_fuel", "ref_status", "ref_capacity_mwe",
        "ref_province", "n_runs_missed", "in_gem", "mentioned_in_narrative",
        "bucket", "rationale",
    ]
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return p


def _fixture_row(name: str, bucket: str, n_runs: int = 5) -> dict:
    return {
        "reference_name": name,
        "ref_fuel": "gas",
        "ref_status": "6 operating",
        "ref_capacity_mwe": "300",
        "ref_province": "Hà Nội",
        "n_runs_missed": n_runs,
        "in_gem": "no",
        "mentioned_in_narrative": "no",
        "bucket": bucket,
        "rationale": "fixture",
    }


def test_generate_summary_counts_buckets(tmp_path):
    rows = [
        _fixture_row("Plant A", "comparateur"),
        _fixture_row("Plant B", "comparateur"),
        _fixture_row("Plant C", "liste"),
        _fixture_row("Plant D", "définition"),
        _fixture_row("Plant E", "résidu"),
        _fixture_row("Plant F", "résidu"),
        _fixture_row("Plant G", "résidu"),
    ]
    input_csv = _write_fixture_csv(tmp_path, rows)
    output_csv = tmp_path / "summary.csv"
    output_tex = tmp_path / "table.tex"

    summary = generate_summary(
        input_csv=input_csv, output_csv=output_csv, output_tex=output_tex
    )

    by_bucket = {r["bucket"]: r for r in summary}
    assert by_bucket["comparateur"]["n_plants"] == 2
    assert by_bucket["liste"]["n_plants"] == 1
    assert by_bucket["définition"]["n_plants"] == 1
    assert by_bucket["résidu"]["n_plants"] == 3


def test_generate_summary_pct_adds_to_100(tmp_path):
    rows = [_fixture_row(f"P{i}", b) for i, b in
            enumerate(["comparateur"] * 3 + ["résidu"] * 7)]
    input_csv = _write_fixture_csv(tmp_path, rows)
    output_csv = tmp_path / "summary.csv"
    output_tex = tmp_path / "table.tex"

    summary = generate_summary(
        input_csv=input_csv, output_csv=output_csv, output_tex=output_tex
    )
    total_pct = sum(float(r["pct_of_total"]) for r in summary)
    assert abs(total_pct - 100.0) < 0.5


def test_generate_summary_skips_empty_bucket(tmp_path):
    rows = [
        _fixture_row("Plant A", "résidu"),
        {**_fixture_row("Plant B", ""), "bucket": ""},  # empty bucket
    ]
    input_csv = _write_fixture_csv(tmp_path, rows)
    output_csv = tmp_path / "summary.csv"
    output_tex = tmp_path / "table.tex"

    summary = generate_summary(
        input_csv=input_csv, output_csv=output_csv, output_tex=output_tex
    )
    # Total should only count the 1 filled row
    by_bucket = {r["bucket"]: r for r in summary}
    assert by_bucket["résidu"]["n_plants"] == 1


def test_generate_summary_raises_on_bad_bucket(tmp_path):
    rows = [_fixture_row("Plant A", "wrong_bucket")]
    input_csv = _write_fixture_csv(tmp_path, rows)
    output_csv = tmp_path / "summary.csv"
    output_tex = tmp_path / "table.tex"

    with pytest.raises(ValueError, match="Unknown bucket value"):
        generate_summary(
            input_csv=input_csv, output_csv=output_csv, output_tex=output_tex
        )


def test_generate_summary_writes_csv(tmp_path):
    rows = [_fixture_row("Plant A", "résidu"), _fixture_row("Plant B", "liste")]
    input_csv = _write_fixture_csv(tmp_path, rows)
    output_csv = tmp_path / "summary.csv"
    output_tex = tmp_path / "table.tex"

    generate_summary(input_csv=input_csv, output_csv=output_csv, output_tex=output_tex)

    assert output_csv.exists()
    with output_csv.open() as f:
        reader = csv.DictReader(f)
        rows_out = list(reader)
    assert len(rows_out) == 4  # four buckets always present
    fields = set(rows_out[0].keys())
    assert "bucket" in fields
    assert "n_plants" in fields
    assert "pct_of_total" in fields


# ---------------------------------------------------------------------------
# _generate_latex
# ---------------------------------------------------------------------------


def test_generate_latex_contains_four_rows():
    summary_rows = [
        {"bucket": "comparateur", "n_plants": 5, "pct_of_total": 25.0},
        {"bucket": "liste", "n_plants": 5, "pct_of_total": 25.0},
        {"bucket": "définition", "n_plants": 5, "pct_of_total": 25.0},
        {"bucket": "résidu", "n_plants": 5, "pct_of_total": 25.0},
    ]
    tex = _generate_latex(summary_rows, total=20)
    for bucket_label in [
        "Comparateur", "Liste", "D", "R"
    ]:
        assert bucket_label in tex
    assert "20" in tex  # total row


def test_generate_latex_label():
    summary_rows = [{"bucket": "résidu", "n_plants": 10, "pct_of_total": 100.0}]
    tex = _generate_latex(summary_rows, total=10)
    assert "tab:exp3-fn-triage" in tex


# ---------------------------------------------------------------------------
# Integration test — needs real arm3_flat data
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_generate_worksheet_integration(tmp_path):
    """Generate the worksheet from the real arm3_flat directory.

    Requires experiments/derived/arm3_flat to exist (committed data).
    Marked integration because it reads real flat files.
    """
    from pathlib import Path

    arm3_dir = Path("experiments/derived/arm3_flat")
    if not arm3_dir.exists():
        pytest.skip("arm3_flat not found — skipping integration test")

    output = tmp_path / "exp3_fn_triage.csv"
    from aedist.tabulate_exp3_fn_triage import generate_worksheet

    rows = generate_worksheet(arm3_dir=arm3_dir, output=output)

    # Sanity checks on the produced worksheet
    assert len(rows) > 0, "Expected at least one FN"
    assert len(rows) <= 100, f"Unexpectedly large FN count: {len(rows)}"
    # Every row has the required fields
    for row in rows:
        assert row["reference_name"], "reference_name must not be empty"
        assert row["bucket"] == "", "bucket must be empty in worksheet"
        assert row["rationale"] == "", "rationale must be empty in worksheet"
        assert row["in_gem"] in ("yes", "no")
        assert row["mentioned_in_narrative"] in ("yes", "no")
