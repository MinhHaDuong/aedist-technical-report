"""Tests for aedist.plot_quality_spider — profile aggregation from metrics rows."""

from aedist.plot_quality_spider import (
    _aggregate_profiles,
    _median,
    _parse_optional_float,
    _row_axis_score,
)


def test_parse_optional_float_handles_blank_and_none() -> None:
    assert _parse_optional_float(None) is None
    assert _parse_optional_float("") is None
    assert _parse_optional_float("  ") is None
    assert _parse_optional_float("not-a-number") is None
    assert _parse_optional_float("0.75") == 0.75


def test_median_odd_even_and_empty() -> None:
    assert _median([]) is None
    assert _median([3, 1, 2]) == 2
    assert _median([1, 2, 3, 4]) == 2.5


def test_row_axis_score_reads_named_column() -> None:
    assert _row_axis_score({"Accuracy": "0.5"}, "Accuracy") == 0.5
    assert _row_axis_score({"Accuracy": ""}, "Accuracy") is None


def test_aggregate_profiles_medians_per_model_arm() -> None:
    config = {
        "modelset": ["gpt-5.5"],
        "arms": ["naive"],
        "axes": ["Accuracy"],
    }
    rows = [
        {"model": "gpt-5.5", "arm": "naive", "Accuracy": "0.4"},
        {"model": "gpt-5.5", "arm": "naive", "Accuracy": "0.6"},
        {"model": "gpt-5.5", "arm": "naive", "Accuracy": "0.8"},
        # Different arm — must be ignored.
        {"model": "gpt-5.5", "arm": "optimised", "Accuracy": "0.1"},
        # Unknown model — must be ignored.
        {"model": "other", "arm": "naive", "Accuracy": "0.0"},
    ]
    profiles = _aggregate_profiles(rows, config)
    assert profiles == {("gpt-5.5", "naive"): {"Accuracy": 0.6}}


def test_aggregate_profiles_skips_axis_with_no_values() -> None:
    config = {"modelset": ["m"], "arms": ["naive"], "axes": ["Accuracy"]}
    rows = [{"model": "m", "arm": "naive", "Accuracy": ""}]
    assert _aggregate_profiles(rows, config) == {}
