"""Conflict-resolution verification for the fusion primitive.

Tests the chrono + authority policy implemented in MasterRecord.update_field:

    Authority rule: higher tier wins.
    Within same tier, later year wins.
    A null incoming value never overwrites an existing value.

Actual behavior note on same-tier same-year:
    The condition `spec.tier == current.tier and spec.year >= current.year`
    means that when tier and year are identical the incoming value replaces
    the current value (silently, last-writer-wins).  The original ticket body
    mentioned "flagged in fusion_log" — that predated the implementation.
    No such flag exists in FusionDiff; this script documents and verifies
    the actual behavior.

Usage::

    uv run python scripts/verify/conflict_resolution_method.py
    uv run python scripts/verify/conflict_resolution_method.py --verbose
"""

import argparse
import sys
from dataclasses import dataclass

from aedist.prototype_v1_fusion import (
    FragmentSpec,
    MasterRecord,
    fuse_fragment,
)

# ---------------------------------------------------------------------------
# Synthetic fixtures
# ---------------------------------------------------------------------------

PLANT_NAME = "Test Plant Alpha"  # Unique enough for fuzzy match → itself


def make_plants(status: str, capacity: float) -> list[dict]:
    return [{"name": PLANT_NAME, "status": status, "capacity_mwe": capacity}]


SPEC_TIER3_2020 = FragmentSpec("s1.md", "SRC-TIER3-2020", tier=3, year=2020)
SPEC_TIER3_2023 = FragmentSpec("s2.md", "SRC-TIER3-2023", tier=3, year=2023)
SPEC_TIER2_2023 = FragmentSpec("s3.md", "SRC-TIER2-2023", tier=2, year=2023)
SPEC_TIER2_2020 = FragmentSpec("s4.md", "SRC-TIER2-2020", tier=2, year=2020)


# ---------------------------------------------------------------------------
# Fixture runners
# ---------------------------------------------------------------------------


@dataclass
class Fixture:
    name: str
    description: str


def run_fixture_1a() -> tuple[bool, str]:
    """Order A: tier-2 first, tier-3 second (same year) → tier-3 wins (update)."""
    master: list[MasterRecord] = []
    d1 = fuse_fragment(master, make_plants("under_construction", 300), SPEC_TIER2_2023)
    d2 = fuse_fragment(master, make_plants("cancelled", 300), SPEC_TIER3_2023)

    rec = master[0]
    ok = (
        rec.status is not None
        and rec.status.value == "cancelled"
        and rec.status.source_id == SPEC_TIER3_2023.source_id
        and rec.status.tier == 3
        and d1.added == 1
        and d2.field_updates >= 1
    )
    detail = (
        f"status={rec.status.value!r} src={rec.status.source_id!r} "
        f"tier={rec.status.tier} d1.added={d1.added} d2.field_updates={d2.field_updates}"
    )
    return ok, detail


def run_fixture_1b() -> tuple[bool, str]:
    """Order B: tier-3 first, tier-2 second (same year) → tier-3 survives (no update)."""
    master: list[MasterRecord] = []
    fuse_fragment(master, make_plants("cancelled", 300), SPEC_TIER3_2023)
    d2 = fuse_fragment(master, make_plants("under_construction", 300), SPEC_TIER2_2023)

    rec = master[0]
    ok = (
        rec.status is not None
        and rec.status.value == "cancelled"
        and rec.status.source_id == SPEC_TIER3_2023.source_id
        and d2.field_updates == 0
        and d2.unchanged >= 1
    )
    detail = (
        f"status={rec.status.value!r} src={rec.status.source_id!r} "
        f"d2.field_updates={d2.field_updates} d2.unchanged={d2.unchanged}"
    )
    return ok, detail


def run_fixture_2a() -> tuple[bool, str]:
    """Order A: 2020 first, 2023 second (same tier) → 2023 wins (update)."""
    master: list[MasterRecord] = []
    fuse_fragment(master, make_plants("operational", 300), SPEC_TIER3_2020)
    d2 = fuse_fragment(master, make_plants("cancelled", 300), SPEC_TIER3_2023)

    rec = master[0]
    ok = (
        rec.status is not None
        and rec.status.value == "cancelled"
        and rec.status.source_id == SPEC_TIER3_2023.source_id
        and rec.status.year == 2023
        and d2.field_updates >= 1
    )
    detail = (
        f"status={rec.status.value!r} src={rec.status.source_id!r} "
        f"year={rec.status.year} d2.field_updates={d2.field_updates}"
    )
    return ok, detail


def run_fixture_2b() -> tuple[bool, str]:
    """Order B: 2023 first, 2020 second (same tier) → 2023 survives (no update)."""
    master: list[MasterRecord] = []
    fuse_fragment(master, make_plants("cancelled", 300), SPEC_TIER3_2023)
    d2 = fuse_fragment(master, make_plants("operational", 300), SPEC_TIER3_2020)

    rec = master[0]
    ok = (
        rec.status is not None
        and rec.status.value == "cancelled"
        and rec.status.source_id == SPEC_TIER3_2023.source_id
        and d2.field_updates == 0
        and d2.unchanged >= 1
    )
    detail = (
        f"status={rec.status.value!r} src={rec.status.source_id!r} "
        f"d2.field_updates={d2.field_updates} d2.unchanged={d2.unchanged}"
    )
    return ok, detail


def run_fixture_3() -> tuple[bool, str]:
    """Cancellation amendment: operational (tier3, 2011) → cancelled (tier3, 2023).

    PDP7-style source says operational; PDP8-style says cancelled.
    Higher year within same tier wins → master shows cancelled, provenance = 2023 source.
    """
    spec_pdp7 = FragmentSpec("pdp7.md", "PDP7-2011", tier=3, year=2011)
    spec_pdp8 = FragmentSpec("pdp8.md", "PDP8-2023", tier=3, year=2023)

    master: list[MasterRecord] = []
    fuse_fragment(master, make_plants("operational", 600), spec_pdp7)
    d2 = fuse_fragment(master, make_plants("cancelled", 600), spec_pdp8)

    rec = master[0]
    ok = (
        rec.status is not None
        and rec.status.value == "cancelled"
        and rec.status.source_id == "PDP8-2023"
        and rec.status.tier == 3
        and rec.status.year == 2023
        and d2.field_updates >= 1
    )
    detail = (
        f"status={rec.status.value!r} src={rec.status.source_id!r} "
        f"tier={rec.status.tier} year={rec.status.year} d2.field_updates={d2.field_updates}"
    )
    return ok, detail


def run_fixture_4() -> tuple[bool, str]:
    """Same tier + same year: incoming replaces current (last-writer-wins on >=).

    This records actual behavior.  The original ticket expected a flag in
    fusion_log; no such flag is implemented.  If same-tier same-year flagging
    is added later, this test will detect the behavior change.
    """
    spec_a = FragmentSpec("sa.md", "SRC-A", tier=3, year=2023)
    spec_b = FragmentSpec("sb.md", "SRC-B", tier=3, year=2023)

    master: list[MasterRecord] = []
    fuse_fragment(master, make_plants("operational", 300), spec_a)
    d2 = fuse_fragment(master, make_plants("cancelled", 300), spec_b)

    rec = master[0]
    # Actual behavior: incoming wins on >= (last-writer-wins), no flag raised.
    ok = (
        rec.status is not None
        and rec.status.value == "cancelled"
        and rec.status.source_id == "SRC-B"
        and d2.field_updates >= 1
    )
    detail = (
        f"status={rec.status.value!r} src={rec.status.source_id!r} "
        f"d2.field_updates={d2.field_updates} [last-writer-wins, no flag]"
    )
    return ok, detail


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

FIXTURES: list[tuple[str, str, object]] = [
    (
        "1a",
        "higher_authority_wins  order=low-then-high  (tier-2 first, tier-3 second)",
        run_fixture_1a,
    ),
    (
        "1b",
        "higher_authority_wins  order=high-then-low  (tier-3 first, tier-2 second, no update)",
        run_fixture_1b,
    ),
    (
        "2a",
        "more_recent_wins       order=old-then-new   (2020 first, 2023 second)",
        run_fixture_2a,
    ),
    (
        "2b",
        "more_recent_wins       order=new-then-old   (2023 first, 2020 second, no update)",
        run_fixture_2b,
    ),
    (
        "3",
        "cancellation_amendment               (PDP7 operational → PDP8 cancelled)",
        run_fixture_3,
    ),
    (
        "4",
        "same_tier_same_year_actual_behavior  (last-writer-wins, no flag)",
        run_fixture_4,
    ),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_all(verbose: bool = False) -> int:
    """Run all fixtures; return count of failures."""
    failures = 0
    width = max(len(desc) for _, desc, _ in FIXTURES)

    print("\nConflict-resolution verification")
    print("=" * (width + 20))

    for fid, desc, fn in FIXTURES:
        ok, detail = fn()
        status = "PASS" if ok else "FAIL"
        print(f"  [{fid}] {status}  {desc}")
        if verbose or not ok:
            print(f"         {detail}")
        if not ok:
            failures += 1

    print("=" * (width + 20))
    print(
        f"  {len(FIXTURES) - failures}/{len(FIXTURES)} passed"
        + (" — all OK" if failures == 0 else f" — {failures} FAILED")
    )
    print()
    return failures


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--verbose", "-v", action="store_true", help="Show detail for every fixture")
    args = p.parse_args(argv)

    failures = run_all(verbose=args.verbose)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
