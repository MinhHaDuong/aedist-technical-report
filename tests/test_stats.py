"""Tests for aedist.stats — bootstrap CIs and paired significance tests."""

import random

import pytest

from aedist.stats import bootstrap_ci, paired_bootstrap_test

# --- bootstrap_ci ---


def test_bootstrap_ci_known_distribution():
    """100 draws from N(0.5, 0.1) — CI should contain 0.5."""
    rng = random.Random(42)
    values = [rng.gauss(0.5, 0.1) for _ in range(100)]
    mean, lo, hi = bootstrap_ci(values, seed=42)
    assert lo < 0.5 < hi


def test_bootstrap_ci_three_samples():
    """With n=3, CI is wide but still computable."""
    mean, lo, hi = bootstrap_ci([0.90, 0.93, 0.91], seed=42)
    assert lo < mean < hi
    assert hi - lo > 0.01  # CI is non-trivial with n=3


def test_bootstrap_ci_single_value():
    """Single value → degenerate CI at that value."""
    mean, lo, hi = bootstrap_ci([0.85], seed=42)
    assert mean == 0.85
    assert lo == 0.85
    assert hi == 0.85


def test_bootstrap_ci_empty():
    """Empty input → zeros."""
    assert bootstrap_ci([]) == (0.0, 0.0, 0.0)


def test_bootstrap_ci_deterministic_with_seed():
    """Same seed → same result."""
    a = bootstrap_ci([0.90, 0.93, 0.91], seed=123)
    b = bootstrap_ci([0.90, 0.93, 0.91], seed=123)
    assert a == b


def test_bootstrap_ci_confidence_level():
    """99% CI should be wider than 90% CI."""
    values = [0.80, 0.85, 0.90, 0.88, 0.82]
    _, lo90, hi90 = bootstrap_ci(values, confidence=0.90, seed=42)
    _, lo99, hi99 = bootstrap_ci(values, confidence=0.99, seed=42)
    assert (hi99 - lo99) >= (hi90 - lo90)


# --- paired_bootstrap_test ---


def test_paired_test_identical():
    """Identical samples → p > 0.05."""
    p = paired_bootstrap_test([0.9, 0.9, 0.9], [0.9, 0.9, 0.9], seed=42)
    assert p > 0.5


def test_paired_test_different():
    """Well-separated samples → p < 0.05 (needs n>=8 for power)."""
    p = paired_bootstrap_test(
        [0.90, 0.91, 0.92, 0.89, 0.93, 0.88, 0.94, 0.90],
        [0.50, 0.51, 0.52, 0.49, 0.53, 0.48, 0.54, 0.50],
        seed=42,
    )
    assert p < 0.05


def test_paired_test_empty():
    """Empty inputs → p = 1.0."""
    assert paired_bootstrap_test([], []) == 1.0


def test_paired_test_length_mismatch():
    """Mismatched lengths → ValueError."""
    with pytest.raises(ValueError, match="equal-length"):
        paired_bootstrap_test([0.9, 0.91], [0.5])


def test_paired_test_deterministic_with_seed():
    """Same seed → same p-value."""
    p1 = paired_bootstrap_test([0.9, 0.91, 0.92], [0.85, 0.86, 0.87], seed=99)
    p2 = paired_bootstrap_test([0.9, 0.91, 0.92], [0.85, 0.86, 0.87], seed=99)
    assert p1 == p2
