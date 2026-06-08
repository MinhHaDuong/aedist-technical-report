"""Tests for aedist.aggregate_runs — run aggregation primitives.

Fixture: 3 synthetic runs over 4 plants:
  Run 1: {A, B}
  Run 2: {B, C}
  Run 3: {B, D}

Expected:
  union = {A, B, C, D}
  majority(k=2) = {B}   (B appears in all 3; A, C, D appear in only 1)
  majority(k=1) = {A, B, C, D}
  confidence-weighted with threshold = sum of scores for plant B across 3 runs

Ticket 0375.
"""

import csv
from pathlib import Path

from aedist.aggregate_runs import (
    has_confidence_data,
    load_run_confidence,
    load_run_names,
    merge_confidence_weighted,
    merge_majority,
    merge_union,
)

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

_RUN1 = ["A", "B"]
_RUN2 = ["B", "C"]
_RUN3 = ["B", "D"]
_ALL_RUNS = [_RUN1, _RUN2, _RUN3]


def _make_csv(tmp_path: Path, rows: list[dict[str, str]], suffix: str = ".csv") -> Path:
    """Write a CSV file with the given rows and return its path."""
    path = tmp_path / f"run{suffix}"
    fieldnames = list(rows[0].keys()) if rows else ["name"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


# ---------------------------------------------------------------------------
# merge_union
# ---------------------------------------------------------------------------


def test_union_all_four_plants():
    result = merge_union(_ALL_RUNS)
    assert result == ["A", "B", "C", "D"]


def test_union_single_run():
    result = merge_union([["A", "B"]])
    assert result == ["A", "B"]


def test_union_empty_runs():
    result = merge_union([[], [], []])
    assert result == []


def test_union_overlapping():
    result = merge_union([["X", "Y"], ["Y", "Z"]])
    assert result == ["X", "Y", "Z"]


# ---------------------------------------------------------------------------
# merge_majority
# ---------------------------------------------------------------------------


def test_majority_k2_only_b():
    result = merge_majority(_ALL_RUNS, k=2)
    assert result == ["B"]


def test_majority_k1_all_plants():
    result = merge_majority(_ALL_RUNS, k=1)
    assert result == ["A", "B", "C", "D"]


def test_majority_k3_only_b():
    result = merge_majority(_ALL_RUNS, k=3)
    assert result == ["B"]


def test_majority_k4_empty():
    result = merge_majority(_ALL_RUNS, k=4)
    assert result == []


def test_majority_duplicate_names_within_run():
    # Duplicate within a single run should still count as 1 for that run.
    result = merge_majority([["A", "A", "B"], ["A", "C"]], k=2)
    assert result == ["A"]


# ---------------------------------------------------------------------------
# merge_confidence_weighted
# ---------------------------------------------------------------------------


def test_confidence_weighted_basic():
    # Plant B is mentioned in all 3 runs with HIGH confidence (score 1.0 each = 3.0)
    # Plant A is mentioned once with HIGH confidence (score 1.0)
    conf1 = {"A": 1.0, "B": 1.0}
    conf2 = {"B": 1.0, "C": 0.5}
    conf3 = {"B": 1.0, "D": 0.25}
    result = merge_confidence_weighted([conf1, conf2, conf3], threshold=2.0)
    assert result == ["B"]


def test_confidence_weighted_threshold_exact():
    # A scores exactly threshold = 1.0
    conf1 = {"A": 1.0}
    result = merge_confidence_weighted([conf1], threshold=1.0)
    assert result == ["A"]


def test_confidence_weighted_all_included():
    conf1 = {"A": 1.0, "B": 1.0}
    conf2 = {"B": 1.0, "C": 1.0}
    result = merge_confidence_weighted([conf1, conf2], threshold=0.5)
    assert result == ["A", "B", "C"]


def test_confidence_weighted_empty_maps():
    result = merge_confidence_weighted([{}, {}, {}], threshold=0.5)
    assert result == []


# ---------------------------------------------------------------------------
# has_confidence_data
# ---------------------------------------------------------------------------


def test_has_confidence_data_true():
    assert has_confidence_data([{"A": 1.0, "B": 0.5}])


def test_has_confidence_data_false_all_zeros():
    assert not has_confidence_data([{"A": 0.0}, {"B": 0.0}])


def test_has_confidence_data_false_empty():
    assert not has_confidence_data([{}, {}])


# ---------------------------------------------------------------------------
# load_run_names  (I/O integration)
# ---------------------------------------------------------------------------


def test_load_run_names(tmp_path):
    rows = [
        {"name": "Plant Alpha", "fuel": "Coal", "capacity_mwe": "500"},
        {"name": "Plant Beta", "fuel": "Gas", "capacity_mwe": "300"},
    ]
    csv_path = _make_csv(tmp_path, rows)
    names = load_run_names(csv_path)
    assert names == ["Plant Alpha", "Plant Beta"]


def test_load_run_names_skips_empty(tmp_path):
    rows = [
        {"name": "Plant Alpha"},
        {"name": ""},
        {"name": "Plant Beta"},
    ]
    csv_path = _make_csv(tmp_path, rows)
    names = load_run_names(csv_path)
    assert names == ["Plant Alpha", "Plant Beta"]


# ---------------------------------------------------------------------------
# load_run_confidence  (I/O integration)
# ---------------------------------------------------------------------------


def test_load_run_confidence(tmp_path):
    rows = [
        {"name": "Plant Alpha", "confidence": "HIGH"},
        {"name": "Plant Beta", "confidence": "MEDIUM"},
        {"name": "Plant Gamma", "confidence": "LOW"},
    ]
    csv_path = _make_csv(tmp_path, rows)
    scores = load_run_confidence(csv_path)
    assert scores["Plant Alpha"] == 1.0
    assert scores["Plant Beta"] == 0.5
    assert scores["Plant Gamma"] == 0.25


def test_load_run_confidence_missing_column(tmp_path):
    """When no confidence column, all plants score 0.0."""
    rows = [
        {"name": "Plant Alpha", "fuel": "Coal"},
        {"name": "Plant Beta", "fuel": "Gas"},
    ]
    csv_path = _make_csv(tmp_path, rows)
    scores = load_run_confidence(csv_path)
    assert all(v == 0.0 for v in scores.values())


def test_load_run_confidence_case_insensitive(tmp_path):
    """Confidence values should be case-insensitive."""
    rows = [
        {"name": "Plant Alpha", "confidence": "high"},
        {"name": "Plant Beta", "confidence": "Medium"},
    ]
    csv_path = _make_csv(tmp_path, rows)
    scores = load_run_confidence(csv_path)
    assert scores["Plant Alpha"] == 1.0
    assert scores["Plant Beta"] == 0.5
