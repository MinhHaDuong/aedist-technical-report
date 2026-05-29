"""Tests for aedist.tabulate_stat_tests — directional stats on arm1 vs arm2."""

from aedist.tabulate_stat_tests import (
    binomial_upper_tail,
    compute_stats,
    median_or_none,
    parse_row,
)


def test_binomial_upper_tail_full_tail_is_one() -> None:
    # P(X >= 0) covers the whole distribution.
    assert binomial_upper_tail(0, 5) == 1.0


def test_binomial_upper_tail_single_extreme() -> None:
    # P(X >= 3) for Binomial(3, 0.5) = (0.5)^3.
    assert binomial_upper_tail(3, 3) == 0.125


def test_binomial_upper_tail_symmetric_half() -> None:
    # P(X >= 1) for Binomial(1, 0.5) = 0.5.
    assert binomial_upper_tail(1, 1) == 0.5


def test_median_or_none_empty() -> None:
    assert median_or_none([]) is None


def test_median_or_none_odd_and_even() -> None:
    assert median_or_none([3, 1, 2]) == 2
    assert median_or_none([1, 2, 3, 4]) == 2.5


def test_parse_row_types_and_blank_n_matched() -> None:
    row = {
        "arm": " naive ",
        "agent": " openai ",
        "run": "2",
        "inventory_rows": "114",
        "n_matched": "",
        "classification": " report ",
    }
    parsed = parse_row(row)
    assert parsed == {
        "arm": "naive",
        "agent": "openai",
        "run": 2,
        "inventory_rows": 114,
        "n_matched": None,
        "classification": "report",
    }


def test_parse_row_scored_n_matched() -> None:
    row = {
        "arm": "optimised",
        "agent": "openai",
        "run": "1",
        "inventory_rows": "120",
        "n_matched": "100",
        "classification": "report",
    }
    assert parse_row(row)["n_matched"] == 100


def test_compute_stats_returns_report_text() -> None:
    records = [
        {"arm": "naive", "agent": "openai", "run": r, "inventory_rows": 100,
         "n_matched": 80 + r, "classification": "report"}
        for r in range(1, 6)
    ] + [
        {"arm": "optimised", "agent": "openai", "run": r, "inventory_rows": 110,
         "n_matched": 90 + r, "classification": "report"}
        for r in range(1, 6)
    ]
    text = compute_stats(records)
    assert "Statistical tests" in text
    assert "Sign test on n_matched" in text
    assert "openai" in text
