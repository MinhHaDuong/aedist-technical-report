"""Tests for Level enum, Plant.level field, and derive_reference_level.

Ticket 0401: schema-level enum + reference derivation.

Coverage:
- Level enum importable with five members.
- Plant / SourcedPlant round-trip with level field.
- derive_level_from_address: address column → Level mapping.
- derive_reference_level: reads v2 units CSV, returns correct levels.
- Taxonomy audit: operating/constructing plants ≤ 1600 MW; units ≤ 1350 MW.
"""

from pathlib import Path

import pytest

from aedist.reference_level import (
    AuditResult,
    audit_reference_taxonomy,
    derive_level_from_address,
    derive_reference_level,
)
from aedist.schema import Level, Plant, SourcedPlant

# ---------------------------------------------------------------------------
# Level enum
# ---------------------------------------------------------------------------


def test_level_enum_has_five_members():
    """Level has exactly the five canonical members."""
    assert set(Level) == {
        Level.UNIT,
        Level.BLOCK,
        Level.PLANT,
        Level.COMPLEX,
        Level.UNKNOWN,
    }


def test_level_enum_values():
    """Level members have the expected string values (StrEnum)."""
    assert Level.UNIT == "unit"
    assert Level.BLOCK == "block"
    assert Level.PLANT == "plant"
    assert Level.COMPLEX == "complex"
    assert Level.UNKNOWN == "unknown"


# ---------------------------------------------------------------------------
# Plant / SourcedPlant round-trip
# ---------------------------------------------------------------------------


def test_plant_level_default():
    """Plant.level defaults to Level.UNKNOWN."""
    p = Plant(name="Test Plant")
    assert p.level == Level.UNKNOWN


def test_plant_level_round_trip():
    """Plant serialises and deserialises level correctly."""
    p = Plant(name="Vinh Tan 2 Unit 1", level=Level.UNIT)
    data = p.model_dump()
    assert data["level"] == "unit"
    p2 = Plant.model_validate(data)
    assert p2.level == Level.UNIT


def test_sourced_plant_level_round_trip():
    """SourcedPlant inherits the level field and round-trips."""
    sp = SourcedPlant(name="LNG Mỹ Giang", level=Level.COMPLEX)
    data = sp.model_dump()
    assert data["level"] == "complex"
    sp2 = SourcedPlant.model_validate(data)
    assert sp2.level == Level.COMPLEX


def test_plant_all_levels_valid():
    """All five Level values are accepted by Plant."""
    for lv in Level:
        p = Plant(name=f"Plant {lv}", level=lv)
        assert p.level == lv


# ---------------------------------------------------------------------------
# derive_level_from_address
# ---------------------------------------------------------------------------


def test_derive_unit_when_unit_nonempty():
    assert derive_level_from_address("", "Vinh Tan 2", "Unit 1") == Level.UNIT


def test_derive_plant_when_unit_empty():
    assert derive_level_from_address("", "An Khánh - Bac Giang", "") == Level.PLANT


def test_derive_complex_when_only_complex():
    assert derive_level_from_address("LNG Mỹ Giang", "", "") == Level.COMPLEX


def test_derive_unknown_when_all_empty():
    assert derive_level_from_address("", "", "") == Level.UNKNOWN


def test_derive_unit_takes_priority_over_plant():
    """unit column wins even when plant is also set."""
    assert derive_level_from_address("", "Parent Plant", "Unit 1") == Level.UNIT


def test_derive_strips_whitespace():
    """Leading/trailing whitespace does not prevent derivation."""
    assert derive_level_from_address("  ", "  My Plant  ", "  ") == Level.PLANT


# ---------------------------------------------------------------------------
# derive_reference_level against live v2 CSV
# ---------------------------------------------------------------------------

_V2_UNITS_CSV = (
    Path(__file__).parent.parent / "data" / "reference" / "vietnam_thermal_units_v2.csv"
)


@pytest.mark.skipif(not _V2_UNITS_CSV.exists(), reason="v2 units CSV not present")
def test_derive_reference_level_returns_rows():
    """derive_reference_level returns one dict per CSV row."""
    rows = derive_reference_level()
    assert len(rows) > 0
    assert all("name" in r and "derived_level" in r for r in rows)


@pytest.mark.skipif(not _V2_UNITS_CSV.exists(), reason="v2 units CSV not present")
def test_derive_reference_level_no_unknown():
    """All v2 rows resolve to a non-Unknown level (address columns complete)."""
    rows = derive_reference_level()
    unknown = [r for r in rows if r["derived_level"] == Level.UNKNOWN]
    assert unknown == [], f"Unexpected Unknown rows: {[r['name'] for r in unknown]}"


@pytest.mark.skipif(not _V2_UNITS_CSV.exists(), reason="v2 units CSV not present")
def test_derive_reference_level_matches_recorded():
    """Derived level matches the pre-assigned level column for all v2 rows."""
    rows = derive_reference_level()
    mismatches = [
        r for r in rows if r["derived_level"].value != r["recorded_level"]
    ]
    assert mismatches == [], (
        f"Derived / recorded mismatch: {[(r['name'], r['derived_level'], r['recorded_level']) for r in mismatches]}"
    )


@pytest.mark.skipif(not _V2_UNITS_CSV.exists(), reason="v2 units CSV not present")
def test_derive_complex_row_example():
    """LNG Mỹ Giang is Complex (bare complex column, no plant/unit)."""
    rows = {r["name"]: r for r in derive_reference_level()}
    assert "LNG Mỹ Giang" in rows
    assert rows["LNG Mỹ Giang"]["derived_level"] == Level.COMPLEX


@pytest.mark.skipif(not _V2_UNITS_CSV.exists(), reason="v2 units CSV not present")
def test_derive_plant_row_example():
    """An Khánh - Bac Giang is Plant (plant column set, unit empty)."""
    rows = {r["name"]: r for r in derive_reference_level()}
    assert "An Khánh - Bac Giang" in rows
    assert rows["An Khánh - Bac Giang"]["derived_level"] == Level.PLANT


@pytest.mark.skipif(not _V2_UNITS_CSV.exists(), reason="v2 units CSV not present")
def test_derive_unit_row_example():
    """An Khánh 1 Unit 1 is Unit (unit column set)."""
    rows = {r["name"]: r for r in derive_reference_level()}
    assert "An Khánh 1 Unit 1" in rows
    assert rows["An Khánh 1 Unit 1"]["derived_level"] == Level.UNIT


# ---------------------------------------------------------------------------
# Taxonomy audit
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _V2_UNITS_CSV.exists(), reason="v2 units CSV not present")
def test_audit_passes_on_v2():
    """Taxonomy audit passes on the v2 reference (no cap violations)."""
    result = audit_reference_taxonomy()
    assert isinstance(result, AuditResult)
    assert result.passed, (
        f"Audit failed. Violations: {result.violations}"
    )


@pytest.mark.skipif(not _V2_UNITS_CSV.exists(), reason="v2 units CSV not present")
def test_audit_no_unknown_rows():
    """Audit reports zero Unknown rows for the v2 reference."""
    result = audit_reference_taxonomy()
    assert result.unknown_count == 0


@pytest.mark.skipif(not _V2_UNITS_CSV.exists(), reason="v2 units CSV not present")
def test_audit_operating_plants_under_cap():
    """No operating/constructing Plant row exceeds 1600 MW (the audit assertion
    that would catch a broken derivation labelling a 6000 MW Complex as Plant).
    """
    rows = derive_reference_level()
    op_plant_caps = [
        r["capacity_mwe"]
        for r in rows
        if r["derived_level"] == Level.PLANT
        and r["status"] in ("5 construction", "6 operating")
        and r["capacity_mwe"] is not None
    ]
    assert op_plant_caps, "No operating/constructing plant rows found — check the CSV"
    assert max(op_plant_caps) <= 1600.0, (
        f"Operating/constructing plant cap violation: max={max(op_plant_caps)} MW"
    )


@pytest.mark.skipif(not _V2_UNITS_CSV.exists(), reason="v2 units CSV not present")
def test_audit_units_under_cap():
    """No Unit row exceeds 1350 MW (world-record single shaft ceiling)."""
    rows = derive_reference_level()
    unit_caps = [
        r["capacity_mwe"]
        for r in rows
        if r["derived_level"] == Level.UNIT and r["capacity_mwe"] is not None
    ]
    assert unit_caps, "No unit rows found — check the CSV"
    assert max(unit_caps) <= 1350.0, (
        f"Unit cap violation: max={max(unit_caps)} MW"
    )


@pytest.mark.skipif(not _V2_UNITS_CSV.exists(), reason="v2 units CSV not present")
def test_audit_level_counts_plausible():
    """Audit reports non-zero counts for unit, plant, and complex levels."""
    result = audit_reference_taxonomy()
    assert result.level_counts.get("unit", 0) > 0
    assert result.level_counts.get("plant", 0) > 0
    assert result.level_counts.get("complex", 0) > 0


def test_audit_accepts_custom_csv(tmp_path):
    """audit_reference_taxonomy accepts a custom CSV path."""
    csv_text = (
        "name,complex,plant,unit,province,asset_type,capacity_mwe,status,level\n"
        "My Complex,My Complex,,,Province A,Coal power plant,4000,2 proposed,complex\n"
        "My Plant,,My Plant,,Province A,Coal power plant,600,6 operating,plant\n"
        "My Unit,,My Plant,Unit 1,Province A,Coal power plant,300,6 operating,unit\n"
    )
    csv_file = tmp_path / "test_units.csv"
    csv_file.write_text(csv_text, encoding="utf-8")

    result = audit_reference_taxonomy(units_csv=csv_file)
    assert result.passed
    assert result.total == 3
    assert result.unknown_count == 0
    assert result.level_counts["complex"] == 1
    assert result.level_counts["plant"] == 1
    assert result.level_counts["unit"] == 1


def test_audit_detects_cap_violation(tmp_path):
    """audit_reference_taxonomy flags a Plant row that exceeds the op cap."""
    csv_text = (
        "name,complex,plant,unit,province,asset_type,capacity_mwe,status,level\n"
        # 2000 MW operating plant — exceeds 1600 MW cap
        "Huge Plant,,Huge Plant,,Province A,Coal power plant,2000,6 operating,plant\n"
    )
    csv_file = tmp_path / "test_units.csv"
    csv_file.write_text(csv_text, encoding="utf-8")

    result = audit_reference_taxonomy(units_csv=csv_file)
    assert not result.passed
    assert len(result.violations) == 1
    assert result.violations[0][0] == "Huge Plant"
