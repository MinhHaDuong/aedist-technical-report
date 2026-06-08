"""Fixture-collection TDD regression suite for the LP matcher.

Each subdirectory of tests/fixtures/lp_matcher/ is one test scenario.  The
test parametrises over all subdirectories, loads reference.csv / system.csv /
expected.csv, runs aedist.reconcile.reconcile(), and compares actual
(reference_name, system_name) pairs to expected.

Fixture directories:
- tp_alias/           — diacritics-variant names that clean to the same string → matched
- tn_hallucinated/    — system output names with no reference counterpart → system_only
- near_miss_unit/     — unit-number veto prevents cross-unit false positives
- duplicate_resolve/  — LP 1:1 constraint resolves two confusable candidates correctly
- mismatched_split/   — LP-forced below-threshold pair → split into reference_only +
                        system_only (documents the ticket 0302 fix)

expected.csv convention (two columns: reference_name, system_name):
- Matched pair:    reference_name=X, system_name=Y
- Reference-only:  reference_name=X, system_name=""
- System-only:     reference_name="", system_name=Y

Note: no @pytest.mark.integration — these fixtures are tiny committed CSVs,
not production data files. exit criterion 4 requires make check-fast passes,
and check-fast excludes integration tests.
"""

from pathlib import Path

import pandas as pd
import pytest

from aedist.reconcile import reconcile
from aedist.schema import FuelType, MatchType, Plant, PlantStatus

_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "lp_matcher"


def _load_plants(csv_path: Path) -> list[Plant]:
    """Load a reference or system CSV as a list of Plant objects.

    Required column: name
    Optional columns: fuel, capacity_mwe, status, province
    """
    df = pd.read_csv(csv_path, dtype=str)
    plants = []
    for _, row in df.iterrows():
        name = row["name"].strip()
        fuel_raw = row.get("fuel", "").strip() if "fuel" in row else ""
        try:
            fuel = FuelType(fuel_raw) if fuel_raw else FuelType.UNKNOWN
        except ValueError:
            fuel = FuelType.UNKNOWN
        status_raw = row.get("status", "").strip() if "status" in row else ""
        try:
            status = PlantStatus(status_raw) if status_raw else PlantStatus.UNKNOWN
        except ValueError:
            status = PlantStatus.UNKNOWN
        cap_raw = row.get("capacity_mwe", "") if "capacity_mwe" in row else ""
        try:
            capacity_mwe = float(cap_raw) if cap_raw and cap_raw.strip() else None
        except (ValueError, TypeError):
            capacity_mwe = None
        province_raw = row.get("province", "") if "province" in row else ""
        province = province_raw.strip() if province_raw and province_raw.strip() else None
        plants.append(
            Plant(
                name=name,
                fuel=fuel,
                status=status,
                capacity_mwe=capacity_mwe,
                province=province,
            )
        )
    return plants


def _load_expected(csv_path: Path) -> list[tuple[str | None, str | None]]:
    """Load expected.csv as a sorted list of (reference_name, system_name) pairs.

    Empty string cells become None (system_only / reference_only entries).
    The list is sorted for stable comparison against actual results.
    """
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    pairs = []
    for _, row in df.iterrows():
        ref = row["reference_name"].strip() or None
        sys = row["system_name"].strip() or None
        pairs.append((ref, sys))
    return sorted(pairs, key=lambda p: (p[0] or "", p[1] or ""))


def _reconcile_to_pairs(
    reference: list[Plant], system: list[Plant]
) -> list[tuple[str | None, str | None]]:
    """Run reconcile() and return sorted (reference_name, system_name) pairs."""
    entries = reconcile(reference, system)
    pairs = []
    for entry in entries:
        ref_name = entry.reference_name or None
        sys_name = entry.system_name or None
        pairs.append((ref_name, sys_name))
    return sorted(pairs, key=lambda p: (p[0] or "", p[1] or ""))


def _fixture_ids() -> list[str]:
    """Return sorted list of fixture directory names."""
    if not _FIXTURE_ROOT.exists():
        return []
    return sorted(d.name for d in _FIXTURE_ROOT.iterdir() if d.is_dir())


@pytest.mark.parametrize("fixture_name", _fixture_ids())
def test_lp_matcher_fixture(fixture_name: str) -> None:
    """Run reconcile() on a fixture and compare to expected pairs.

    Each fixture directory must contain reference.csv, system.csv, expected.csv.
    """
    fixture_dir = _FIXTURE_ROOT / fixture_name
    ref_path = fixture_dir / "reference.csv"
    sys_path = fixture_dir / "system.csv"
    exp_path = fixture_dir / "expected.csv"

    assert ref_path.exists(), f"Missing reference.csv in {fixture_dir}"
    assert sys_path.exists(), f"Missing system.csv in {fixture_dir}"
    assert exp_path.exists(), f"Missing expected.csv in {fixture_dir}"

    reference = _load_plants(ref_path)
    system = _load_plants(sys_path)
    expected = _load_expected(exp_path)

    actual = _reconcile_to_pairs(reference, system)

    assert actual == expected, (
        f"Fixture '{fixture_name}' mismatch.\n"
        f"Expected: {expected}\n"
        f"Actual:   {actual}"
    )


def test_mismatched_split_produces_two_entries() -> None:
    """The 0302 fix: LP-forced below-threshold match emits 2 entries, not 1.

    Before ticket 0302, a 'Mismatched' LP result was mapped to EXACT_CAPACITY_DIFF
    (one entry). The fix routes it through the split path: one REFERENCE_ONLY entry
    and one SYSTEM_ONLY entry.

    'Pha Lai 2' vs 'Hai Phong 2' has partial_ratio ~61.5 on their cleaned names
    ('pha lai 2' vs 'hai phong 2'), below the default threshold of 90.  With only
    one candidate in each set, the LP prefers to pair them (cost 1000) rather than
    leave both unmatched (cost 20000). The split path must produce exactly two entries.
    """
    reference = [Plant(name="Pha Lai 2", fuel=FuelType.COAL, capacity_mwe=600)]
    system = [Plant(name="Hai Phong 2", fuel=FuelType.COAL, capacity_mwe=600)]

    entries = reconcile(reference, system)

    match_types = {e.match_type for e in entries}
    assert len(entries) == 2, (
        f"Expected 2 entries from Mismatched split, got {len(entries)}: {entries}"
    )
    assert MatchType.REFERENCE_ONLY in match_types
    assert MatchType.SYSTEM_ONLY in match_types
    ref_entry = next(e for e in entries if e.match_type == MatchType.REFERENCE_ONLY)
    sys_entry = next(e for e in entries if e.match_type == MatchType.SYSTEM_ONLY)
    assert ref_entry.reference_name == "Pha Lai 2"
    assert sys_entry.system_name == "Hai Phong 2"


def test_unit_veto_prevents_cross_unit_match() -> None:
    """Unit-number veto: 'Na Duong 1' must not match 'Na Duong 2'.

    The LP matcher imposes a veto cost (2 * dummy_cost + 1) when two plant names
    share a base but differ on trailing unit digits, making it cheaper for the LP
    to leave both unmatched than to accept the cross-unit false positive.
    """
    reference = [Plant(name="Na Duong 1", fuel=FuelType.COAL, capacity_mwe=110)]
    system = [Plant(name="Na Duong 2", fuel=FuelType.COAL, capacity_mwe=110)]

    entries = reconcile(reference, system)

    assert len(entries) == 2
    match_types = {e.match_type for e in entries}
    assert MatchType.REFERENCE_ONLY in match_types
    assert MatchType.SYSTEM_ONLY in match_types
    # The reference plant must NOT be paired with the wrong unit
    ref_entry = next(e for e in entries if e.match_type == MatchType.REFERENCE_ONLY)
    assert ref_entry.reference_name == "Na Duong 1"
    assert ref_entry.system_name is None
