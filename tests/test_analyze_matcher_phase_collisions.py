"""Ticket 0544 — structural false-match set of the partial_ratio threshold.

Pins the phase-collision analysis on the real reference: Vũng Áng 1/2 must
appear in the structural false-match set at threshold 90 (partial_ratio is
structurally high across phases), and must be flagged veto_blocked=True
(digit tokens differ, so the LP unit-number veto fires — ``digit_veto`` in
matching/lp.py).
"""

import pytest

from aedist.analyze_matcher_phase_collisions import structural_false_matches


@pytest.fixture(scope="module")
def pairs_at_90() -> dict[tuple[str, str], tuple[float, bool]]:
    return structural_false_matches(threshold=90)


@pytest.mark.parametrize(
    "name_a,name_b,in_set,veto_blocked",
    [
        # Vũng Áng 1 vs 2: high partial_ratio across phases — MUST appear in the
        # structural false-match set at t=90 (original ticket red test), and MUST
        # be flagged veto_blocked=True (digit tokens differ → LP veto fires)
        ("vung ang 1", "vung ang 2", True, True),
        # A same-plant pair: never in the set (distinct-plants guard)
        ("vung ang 1", "vung ang 1", False, None),
        # Base name vs phase-suffixed sibling: blocked by the digit-asymmetric
        # guard (ticket 0551) — exactly one side carries digits and the
        # digit-stripped names are identical.
        ("ca na", "ca na 2", True, True),
        # Residual exposure that survives both veto branches: digit-free pair
        # with a word-level difference.
        ("long son", "long son chemical", True, False),
    ],
)
def test_structural_set_and_veto_flag(pairs_at_90, name_a, name_b, in_set, veto_blocked):
    pairs = pairs_at_90
    key = (name_a, name_b) if (name_a, name_b) in pairs else (name_b, name_a)
    assert (key in pairs) == in_set
    if in_set:
        score, blocked = pairs[key]
        assert score >= 90
        assert blocked == veto_blocked


def test_set_nonempty_at_90(pairs_at_90):
    """The threshold's raw exposure on the real reference is non-empty."""
    assert len(pairs_at_90) > 0


def test_residual_side_of_veto_flag(pairs_at_90):
    """Pin the veto_blocked=False side on the real reference (anti-tautology).

    After the digit-asymmetric guard (ticket 0551), base-name vs
    phase-suffixed siblings ("ca na" vs "ca na 2") are veto-blocked; the
    residual side is digit-free pairs with word-level differences
    ("long son" vs "long son chemical"). Both sides must be represented.
    """
    residual = {k for k, (_, blocked) in pairs_at_90.items() if not blocked}
    blocked = {k for k, (_, is_blocked) in pairs_at_90.items() if is_blocked}
    assert ("ca na", "ca na 2") in blocked
    assert ("long son", "long son chemical") in residual
    assert residual and blocked
