"""Tests for tabulate_reconciliation helpers."""

from types import SimpleNamespace

import pytest

from aedist.tabulate_reconciliation import _cohens_kappa_fuel, _is_synthetic_slug


def _make_pair(ref: str, sys: str) -> SimpleNamespace:
    return SimpleNamespace(reference_fuel=ref, system_fuel=sys)


def test_cohens_kappa_wikipedia_example():
    # Wikipedia 2x2 example: p_o=0.7, p_e=0.5, kappa=0.4
    matched = (
        [_make_pair("yes", "yes")] * 20
        + [_make_pair("yes", "no")] * 5
        + [_make_pair("no", "yes")] * 10
        + [_make_pair("no", "no")] * 15
    )
    assert _cohens_kappa_fuel(matched) == pytest.approx(0.4)


def test_cohens_kappa_perfect_agreement():
    matched = [_make_pair("coal", "coal"), _make_pair("gas", "gas"), _make_pair("oil", "oil")]
    assert _cohens_kappa_fuel(matched) == pytest.approx(1.0)


def test_cohens_kappa_all_same_category_returns_one():
    # Degenerate p_e == 1.0 case (only one category present).
    matched = [_make_pair("coal", "coal")] * 5
    assert _cohens_kappa_fuel(matched) == pytest.approx(1.0)


def test_cohens_kappa_fewer_than_two_pairs_returns_none():
    assert _cohens_kappa_fuel([]) is None
    assert _cohens_kappa_fuel([_make_pair("coal", "coal")]) is None


def test_cohens_kappa_ignores_missing_fuel():
    matched = [
        _make_pair("coal", "coal"),
        _make_pair("gas", "gas"),
        _make_pair(None, "coal"),
        _make_pair("coal", None),
    ]
    assert _cohens_kappa_fuel(matched) == pytest.approx(1.0)


def test_is_synthetic_slug_matches_suffixes():
    assert _is_synthetic_slug("gpt-5.4-union")
    assert _is_synthetic_slug("gpt-5.4-consolidated")
    assert _is_synthetic_slug("gpt-5.4-filtered")
    assert _is_synthetic_slug("gpt-5.4_filtered")
    assert _is_synthetic_slug("gpt-5.4-unverified")


def test_is_synthetic_slug_rejects_plain_run_slugs():
    assert not _is_synthetic_slug("gpt-5.4")
    assert not _is_synthetic_slug("padme-qwen3.5-122b")
