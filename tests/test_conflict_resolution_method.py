"""Tests for scripts/verify/conflict_resolution_method.py.

Unit tests only — no LLM calls.  All fixtures use synthetic MasterRecord,
FragmentSpec, and SourcedField instances.

Covers:
- Higher authority (tier) wins over lower authority, regardless of arrival order.
- More recent year wins within same tier, regardless of arrival order.
- Cancellation amendment: later/higher-authority source overrides status.
- Same tier + same year: last-writer-wins (actual behavior; no flag raised).

Each rule is tested in both orderings so the test suite checks the property
(not just one direction of the comparison).

FusionDiff accounting is checked alongside master state:
- Update happened → diff.field_updates >= 1
- No update → diff.field_updates == 0 and diff.unchanged >= 1
"""

from pathlib import Path

from aedist.prototype_v1_fusion import (
    FragmentSpec,
    MasterRecord,
    fuse_fragment,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

PLANT_NAME = "Test Plant Alpha"


def _plants(status: str, capacity: float = 300.0) -> list[dict]:
    return [{"name": PLANT_NAME, "status": status, "capacity_mwe": capacity}]


SPEC_TIER3_2020 = FragmentSpec("s1.md", "SRC-TIER3-2020", tier=3, year=2020)
SPEC_TIER3_2023 = FragmentSpec("s2.md", "SRC-TIER3-2023", tier=3, year=2023)
SPEC_TIER2_2023 = FragmentSpec("s3.md", "SRC-TIER2-2023", tier=2, year=2023)
SPEC_TIER2_2020 = FragmentSpec("s4.md", "SRC-TIER2-2020", tier=2, year=2020)


# ---------------------------------------------------------------------------
# Rule 1: higher authority wins — both orderings
# ---------------------------------------------------------------------------


def test_higher_authority_wins_same_time_low_then_high():
    """Order A: tier-2 arrives first, tier-3 arrives second → tier-3 wins."""
    master: list[MasterRecord] = []
    d1 = fuse_fragment(master, _plants("under_construction"), SPEC_TIER2_2023)
    d2 = fuse_fragment(master, _plants("cancelled"), SPEC_TIER3_2023)

    rec = master[0]
    assert rec.status is not None, "status should be set"
    assert rec.status.value == "cancelled", f"expected 'cancelled', got {rec.status.value!r}"
    assert rec.status.source_id == SPEC_TIER3_2023.source_id, (
        f"provenance should be tier-3 source, got {rec.status.source_id!r}"
    )
    assert rec.status.tier == 3, f"tier should be 3, got {rec.status.tier}"
    assert d1.added == 1, "first fragment should add the plant"
    assert d2.field_updates >= 1, "tier-3 should update at least one field"


def test_higher_authority_wins_same_time_high_then_low():
    """Order B: tier-3 arrives first, tier-2 arrives second → tier-3 survives (no update)."""
    master: list[MasterRecord] = []
    fuse_fragment(master, _plants("cancelled"), SPEC_TIER3_2023)
    d2 = fuse_fragment(master, _plants("under_construction"), SPEC_TIER2_2023)

    rec = master[0]
    assert rec.status is not None, "status should be set"
    assert rec.status.value == "cancelled", (
        f"tier-3 value should survive, got {rec.status.value!r}"
    )
    assert rec.status.source_id == SPEC_TIER3_2023.source_id, (
        f"provenance should remain tier-3, got {rec.status.source_id!r}"
    )
    assert d2.field_updates == 0, "tier-2 should NOT update any field already set by tier-3"
    assert d2.unchanged >= 1, "plant should be counted as unchanged"


# ---------------------------------------------------------------------------
# Rule 2: more recent year wins within same tier — both orderings
# ---------------------------------------------------------------------------


def test_more_recent_wins_same_tier_old_then_new():
    """Order A: 2020 arrives first, 2023 arrives second → 2023 wins."""
    master: list[MasterRecord] = []
    fuse_fragment(master, _plants("operational"), SPEC_TIER3_2020)
    d2 = fuse_fragment(master, _plants("cancelled"), SPEC_TIER3_2023)

    rec = master[0]
    assert rec.status is not None
    assert rec.status.value == "cancelled", f"expected 'cancelled', got {rec.status.value!r}"
    assert rec.status.source_id == SPEC_TIER3_2023.source_id, (
        f"provenance should be 2023 source, got {rec.status.source_id!r}"
    )
    assert rec.status.year == 2023, f"year should be 2023, got {rec.status.year}"
    assert d2.field_updates >= 1, "newer source should update the field"


def test_more_recent_wins_same_tier_new_then_old():
    """Order B: 2023 arrives first, 2020 arrives second → 2023 survives (no update)."""
    master: list[MasterRecord] = []
    fuse_fragment(master, _plants("cancelled"), SPEC_TIER3_2023)
    d2 = fuse_fragment(master, _plants("operational"), SPEC_TIER3_2020)

    rec = master[0]
    assert rec.status is not None
    assert rec.status.value == "cancelled", f"2023 value should survive, got {rec.status.value!r}"
    assert rec.status.source_id == SPEC_TIER3_2023.source_id, (
        f"provenance should remain 2023, got {rec.status.source_id!r}"
    )
    assert d2.field_updates == 0, "older source should NOT overwrite newer"
    assert d2.unchanged >= 1, "plant should be counted as unchanged"


# ---------------------------------------------------------------------------
# Rule 3: cancellation amendment
# ---------------------------------------------------------------------------


def test_cancellation_amendment():
    """PDP7 (tier3, 2011) says operational; PDP8 (tier3, 2023) says cancelled → cancelled wins."""
    spec_pdp7 = FragmentSpec("pdp7.md", "PDP7-2011", tier=3, year=2011)
    spec_pdp8 = FragmentSpec("pdp8.md", "PDP8-2023", tier=3, year=2023)

    master: list[MasterRecord] = []
    fuse_fragment(master, _plants("operational", 600), spec_pdp7)
    d2 = fuse_fragment(master, _plants("cancelled", 600), spec_pdp8)

    rec = master[0]
    assert rec.status is not None
    assert rec.status.value == "cancelled", (
        f"master should show cancelled, got {rec.status.value!r}"
    )
    assert rec.status.source_id == "PDP8-2023", (
        f"provenance should be PDP8-2023, got {rec.status.source_id!r}"
    )
    assert rec.status.tier == 3
    assert rec.status.year == 2023
    assert d2.field_updates >= 1, "amendment should record a field update"


# ---------------------------------------------------------------------------
# Rule 4: same tier + same year — actual behavior (last-writer-wins)
# ---------------------------------------------------------------------------


def test_same_tier_same_year_last_writer_wins():
    """Same tier and year: incoming replaces current on >= comparison.

    This documents actual behavior: the implementation uses `year >= current.year`
    so when tier and year are both equal the incoming value wins silently.
    No flag is raised in FusionDiff.  This test will break if flagging is added,
    making the behavior change visible.
    """
    spec_a = FragmentSpec("sa.md", "SRC-A", tier=3, year=2023)
    spec_b = FragmentSpec("sb.md", "SRC-B", tier=3, year=2023)

    master: list[MasterRecord] = []
    fuse_fragment(master, _plants("operational"), spec_a)
    d2 = fuse_fragment(master, _plants("cancelled"), spec_b)

    rec = master[0]
    assert rec.status is not None
    # Actual behavior: incoming wins (last-writer-wins on >=)
    assert rec.status.value == "cancelled", (
        f"expected last-writer 'cancelled', got {rec.status.value!r}"
    )
    assert rec.status.source_id == "SRC-B", (
        f"provenance should be SRC-B, got {rec.status.source_id!r}"
    )
    assert d2.field_updates >= 1, "same-tier same-year should count as a field update"


# ---------------------------------------------------------------------------
# Null value never overwrites
# ---------------------------------------------------------------------------


def test_null_value_does_not_overwrite():
    """A null incoming value never overwrites an existing value."""
    master: list[MasterRecord] = []
    fuse_fragment(master, _plants("operational"), SPEC_TIER3_2020)
    # Second fragment has status=None (field absent)
    d2 = fuse_fragment(master, [{"name": PLANT_NAME, "status": None}], SPEC_TIER3_2023)

    rec = master[0]
    assert rec.status is not None
    assert rec.status.value == "operational", (
        f"null should not overwrite operational, got {rec.status.value!r}"
    )
    # No field update because incoming status is None
    assert d2.field_updates == 0, "null incoming should not trigger a field update"


# ---------------------------------------------------------------------------
# Script-level integration: run_all returns 0 failures
# ---------------------------------------------------------------------------


def test_script_run_all_passes():
    """The verify script's run_all() function reports zero failures."""
    import importlib.util

    script_path = (
        Path(__file__).parent.parent / "scripts" / "verify" / "conflict_resolution_method.py"
    )
    spec = importlib.util.spec_from_file_location("conflict_resolution_method", script_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    failures = mod.run_all(verbose=False)
    assert failures == 0, f"run_all() reported {failures} fixture failure(s)"
