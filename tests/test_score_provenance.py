"""Tests for provenance scoring (score_provenance.py)."""

import json

import pytest

from aedist.score_provenance import (
    _has_provenance_columns,
    score_directory,
    score_honesty,
    score_sourced_run,
    main,
)


class TestScoreSourcedRun:
    """score_sourced_run computes evidence quality from citation columns."""

    def test_basic_scoring(self, tmp_path):
        csv_text = (
            "name,fuel,status,cod,province,capacity_mwe,source_1,source_2,note\n"
            'Pha Lai,coal,operating,1983,Hai Duong,440,'
            '"Decision 1195/QD-TTg","EVN Annual Report 2017 p14","Soviet-built"\n'
            'Uong Bi,coal,operating,1964,Quang Ninh,105,'
            '"","",""\n'
        )
        csv_path = tmp_path / "run1.csv"
        csv_path.write_text(csv_text)

        result = score_sourced_run(csv_path)
        assert result["n_plants"] == 2
        assert "mean_evidence_score" in result
        assert "score_distribution" in result
        assert "primary_frac" in result
        assert "secondary_frac" in result
        assert "none_frac" in result
        # Pha Lai has two primary sources (score 4), Uong Bi has none (score 1)
        assert result["mean_evidence_score"] == 2.5

    def test_empty_sources_score_1(self, tmp_path):
        csv_text = (
            "name,fuel,status,cod,province,capacity_mwe,source_1,source_2,note\n"
            "Pha Lai,coal,operating,1983,Hai Duong,440,,,\n"
        )
        csv_path = tmp_path / "run.csv"
        csv_path.write_text(csv_text)

        result = score_sourced_run(csv_path)
        assert result["n_plants"] == 1
        assert result["mean_evidence_score"] == 1.0
        assert result["score_distribution"][1] == 1

    def test_two_primary_sources_score_4(self, tmp_path):
        csv_text = (
            "name,fuel,status,cod,province,capacity_mwe,source_1,source_2,note\n"
            'Plant A,coal,operating,2000,Ha Noi,600,'
            '"Decision 1509/QD-BCT","EVN Annual Report 2020 p14",""\n'
        )
        csv_path = tmp_path / "run.csv"
        csv_path.write_text(csv_text)

        result = score_sourced_run(csv_path)
        assert result["n_plants"] == 1
        assert result["mean_evidence_score"] == 4.0
        assert result["score_distribution"][4] == 1


class TestScoreHonesty:
    """score_honesty counts epistemic markers in note column."""

    def test_basic_honesty(self, tmp_path):
        csv_text = (
            "name,fuel,status,cod,province,capacity_mwe,source_1,source_2,note\n"
            'Plant A,coal,operating,2000,Ha Noi,600,"","","uncertain about COD"\n'
            'Plant B,coal,operating,2001,Ha Noi,300,"","","all data confirmed"\n'
            'Plant C,gas,operating,2005,HCMC,400,"","","conflicting sources on capacity"\n'
        )
        csv_path = tmp_path / "run.csv"
        csv_path.write_text(csv_text)

        result = score_honesty(csv_path)
        assert result["n_plants"] == 3
        assert result["n_with_note"] == 3
        assert result["n_with_epistemic_marker"] == 2  # "uncertain" and "conflicting"
        assert abs(result["honesty_rate"] - 2.0 / 3) < 0.01

    def test_no_notes(self, tmp_path):
        csv_text = (
            "name,fuel,status,cod,province,capacity_mwe,source_1,source_2,note\n"
            "Plant A,coal,operating,2000,Ha Noi,600,,,\n"
        )
        csv_path = tmp_path / "run.csv"
        csv_path.write_text(csv_text)

        result = score_honesty(csv_path)
        assert result["n_plants"] == 1
        assert result["n_with_note"] == 0
        assert result["n_with_epistemic_marker"] == 0
        assert result["honesty_rate"] == 0.0


# ---- _has_provenance_columns ----


class TestHasProvenanceColumns:
    """Tests for _has_provenance_columns helper."""

    def test_csv_with_source_1(self, tmp_path):
        csv_path = tmp_path / "sourced.csv"
        csv_path.write_text(
            "name,fuel,status,cod,province,capacity_mwe,source_1,source_2,note\n"
            "Plant A,coal,operating,2000,Ha Noi,600,ref1,ref2,ok\n"
        )
        assert _has_provenance_columns(csv_path) is True

    def test_csv_without_source_1(self, tmp_path):
        csv_path = tmp_path / "plain.csv"
        csv_path.write_text(
            "name,fuel,status,cod,province,capacity_mwe\n"
            "Plant A,coal,operating,2000,Ha Noi,600\n"
        )
        assert _has_provenance_columns(csv_path) is False

    def test_empty_csv(self, tmp_path):
        csv_path = tmp_path / "empty.csv"
        csv_path.write_text("")
        assert _has_provenance_columns(csv_path) is False


# ---- score_directory ----

# Helper CSV content for directory tests
_SOURCED_CSV_1 = (
    "name,fuel,status,cod,province,capacity_mwe,source_1,source_2,note\n"
    'Plant A,coal,operating,2000,Ha Noi,600,"Decision 1195/QD-TTg","EVN Report","uncertain about COD"\n'
    'Plant B,gas,operating,2005,HCMC,400,"","","all data confirmed"\n'
)

_SOURCED_CSV_2 = (
    "name,fuel,status,cod,province,capacity_mwe,source_1,source_2,note\n"
    'Plant C,coal,operating,2010,Quang Ninh,800,"MOIT decision","","conflicting sources"\n'
)

_PLAIN_CSV = (
    "name,fuel,status,cod,province,capacity_mwe\n"
    "Plant X,coal,operating,2000,Ha Noi,600\n"
)


class TestScoreDirectory:
    """Tests for score_directory aggregation."""

    def test_aggregates_multiple_sourced_csvs(self, tmp_path):
        (tmp_path / "run1.csv").write_text(_SOURCED_CSV_1)
        (tmp_path / "run2.csv").write_text(_SOURCED_CSV_2)

        result = score_directory(tmp_path)
        assert "runs" in result
        assert "aggregate" in result
        assert len(result["runs"]) == 2
        assert "run1" in result["runs"]
        assert "run2" in result["runs"]
        # Aggregate checks
        agg = result["aggregate"]
        assert agg["mean_evidence_score"] > 0
        assert 0 <= agg["primary_frac"] <= 1
        assert 0 <= agg["honesty_rate"] <= 1

    def test_skips_csvs_without_provenance(self, tmp_path):
        (tmp_path / "sourced.csv").write_text(_SOURCED_CSV_1)
        (tmp_path / "plain.csv").write_text(_PLAIN_CSV)

        result = score_directory(tmp_path)
        assert len(result["runs"]) == 1
        assert "sourced" in result["runs"]

    def test_no_sourced_csvs_raises(self, tmp_path):
        (tmp_path / "plain.csv").write_text(_PLAIN_CSV)

        with pytest.raises(SystemExit, match="No sourced CSV"):
            score_directory(tmp_path)

    def test_empty_directory_raises(self, tmp_path):
        with pytest.raises(SystemExit, match="No sourced CSV"):
            score_directory(tmp_path)

    def test_aggregate_totals_correct(self, tmp_path):
        """Verify aggregate values are correct cross-run sums."""
        (tmp_path / "run1.csv").write_text(_SOURCED_CSV_1)
        (tmp_path / "run2.csv").write_text(_SOURCED_CSV_2)

        result = score_directory(tmp_path)
        runs = result["runs"]

        # Total plants should be sum of individual runs
        total_plants = sum(r["n_plants"] for r in runs.values())
        assert total_plants == 3  # 2 from run1 + 1 from run2


# ---- main (CLI) ----


class TestMainCLI:
    """Tests for main() CLI entry point."""

    def test_main_writes_json(self, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "run1.csv").write_text(_SOURCED_CSV_1)

        output_file = tmp_path / "output" / "summary.json"

        main(["--input", str(input_dir), "--output", str(output_file)])

        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert "runs" in data
        assert "aggregate" in data

    def test_main_creates_output_parents(self, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "run1.csv").write_text(_SOURCED_CSV_1)

        output_file = tmp_path / "deep" / "nested" / "summary.json"

        main(["--input", str(input_dir), "--output", str(output_file)])

        assert output_file.exists()

    def test_main_invalid_input_dir(self, tmp_path):
        output_file = tmp_path / "summary.json"

        with pytest.raises(SystemExit, match="Input dir not found"):
            main(["--input", str(tmp_path / "nonexistent"), "--output", str(output_file)])

    def test_main_input_is_file_not_dir(self, tmp_path):
        not_a_dir = tmp_path / "afile.txt"
        not_a_dir.write_text("hello")
        output_file = tmp_path / "summary.json"

        with pytest.raises(SystemExit, match="Input dir not found"):
            main(["--input", str(not_a_dir), "--output", str(output_file)])
