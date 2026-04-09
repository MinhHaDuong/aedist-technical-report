"""Tests for provenance scoring (score_provenance.py)."""

import csv
import io
import json
from pathlib import Path

import pytest


class TestScoreSourcedRun:
    """score_sourced_run computes evidence quality from citation columns."""

    def test_basic_scoring(self, tmp_path):
        from aedist.score_provenance import score_sourced_run

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
        # Pha Lai has primary sources, Uong Bi has none
        assert result["mean_evidence_score"] > 1.0

    def test_empty_sources_score_1(self, tmp_path):
        from aedist.score_provenance import score_sourced_run

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
        from aedist.score_provenance import score_sourced_run

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
        from aedist.score_provenance import score_honesty

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
        from aedist.score_provenance import score_honesty

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
