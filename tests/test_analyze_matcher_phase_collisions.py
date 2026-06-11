"""Ticket 0544 — structural false-match set of the partial_ratio threshold.

Pins the phase-collision analysis on the real reference: Vũng Áng 1/2 must
appear in the structural false-match set at threshold 90 (partial_ratio is
structurally high across phases), and must be flagged veto_blocked=True
(digit tokens differ, so the LP unit-number veto fires — lp.py:203–208).
"""

import pytest

from aedist.analyze_matcher_phase_collisions import structural_false_matches


@pytest.fixture(scope="module")
def pairs_at_90() -> dict[tuple[str, str], bool]:
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
        # Residual exposure (veto_blocked=False side, derived from the generated
        # tab_phase_collisions.csv): the veto needs digit tokens on BOTH sides,
        # so a bare base name vs a phase-suffixed sibling slips through.
        ("ca na", "ca na 2", True, False),
    ],
)
def test_structural_set_and_veto_flag(pairs_at_90, name_a, name_b, in_set, veto_blocked):
    pairs = pairs_at_90
    key = (name_a, name_b) if (name_a, name_b) in pairs else (name_b, name_a)
    assert (key in pairs) == in_set
    if in_set:
        assert pairs[key] == veto_blocked


def test_set_nonempty_at_90(pairs_at_90):
    """The threshold's raw exposure on the real reference is non-empty."""
    assert len(pairs_at_90) > 0


def test_residual_side_of_veto_flag(pairs_at_90):
    """Pin the veto_blocked=False side on the real reference (anti-tautology).

    The residual set at t=90 is non-empty (70 pairs in the generated
    tab_phase_collisions.csv): the unit-number veto needs digit tokens on both
    sides, so base-name vs phase-suffixed siblings ("ca na" vs "ca na 2")
    slip through. Both sides of the veto flag must be represented.
    """
    residual = {k for k, blocked in pairs_at_90.items() if not blocked}
    blocked = {k for k, is_blocked in pairs_at_90.items() if is_blocked}
    assert ("ca na", "ca na 2") in residual
    assert residual and blocked
