"""Tests for data/reference/aggregate_units.py — unit -> plant aggregation.

The aggregator consumes the unit-grain CSV produced by extract_ods.py (ticket
0420) and rolls unit rows up to plant rows. Under the three-column address
contract (ticket 0439) parentage is DATA: a unit row carries its parent in the
`plant` column, so grouping is `groupby(plant)` — never a name-string parse.
The forbidden `normalize_plant_name` of the old HDM_aggregate.py is gone.

The validators are the heart of the module (ticket 0416):

- INPUT: a duplicated unit row (same designation twice) is a hard failure —
  the "Quảng Trị 1 Unit 2" x2 case must abort, never silently sum 660+660.
- OUTPUT: a plant name appearing twice (the key is unique), a unit repeated in
  Units Included, or a unit landing in two groups is a refusal listing the
  offending groups. No plant name is ever synthesized — the output name is the
  `plant` cell (or `complex` for complex-grain rows), verbatim.

Status legitimately VARIES across units of one plant (units commission and
retire in phases — Dong Nai Formosa, Uong Bi I), so it is collapsed, never
asserted constant. Province and asset_type are plant-invariant and asserted.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

from data.reference.aggregate_units import (
    ASSET_TYPE_TO_FUEL,
    aggregate,
    collapse_status,
    derive_fuel,
    plant_key,
    validate_capacity_numeric,
    validate_input_no_duplicate_units,
    validate_output_unique_plants,
)


def _units(rows: list[dict[str, str]]) -> pd.DataFrame:
    """A unit-grain frame with the extract_ods output schema (all strings)."""
    cols = ["name", "complex", "plant", "unit", "province", "asset_type", "capacity_mwe", "status", "level"]
    return pd.DataFrame([{c: r.get(c, "") for c in cols} for r in rows], dtype=str)


# --- plant_key: the grouping identity (no name parsing) ------------------------


def test_plant_key_unit_row_is_plant_column():
    """A unit row's plant identity is its `plant` cell, not a parsed name."""
    df = _units([{"name": "An Khánh 1 Unit 1", "plant": "An Khánh 1", "unit": "Unit 1", "level": "unit"}])
    assert plant_key(df.iloc[0]) == "An Khánh 1"


def test_plant_key_plant_grain_is_plant_column():
    """A plant-grain row keys on its own plant cell."""
    df = _units([{"name": "Bà Rịa GT", "plant": "Bà Rịa GT", "unit": "", "level": "plant"}])
    assert plant_key(df.iloc[0]) == "Bà Rịa GT"


def test_plant_key_complex_grain_is_complex_column():
    """A complex-grain row (plant empty) keys on its `complex` cell."""
    df = _units([{"name": "LNG Mỹ Giang", "complex": "LNG Mỹ Giang", "plant": "", "unit": "", "level": "complex"}])
    assert plant_key(df.iloc[0]) == "LNG Mỹ Giang"


# --- derive_fuel: asset_type -> fuel (pipe-owned, contrat v2) ------------------


@pytest.mark.parametrize(
    ("asset_type", "fuel"),
    [
        ("Coal power plant", "coal"),
        ("Coal cogen plant", "coal"),
        ("Gas power plant", "gas"),
        ("Gas/Oil power plant", "gas/oil"),
    ],
)
def test_derive_fuel_known_asset_types(asset_type, fuel):
    """Every asset_type in the snapshot maps to a v1 fuel label."""
    assert derive_fuel(asset_type) == fuel


def test_derive_fuel_unknown_raises_keyerror():
    """An unmapped asset_type raises loudly — never a silent empty fuel."""
    with pytest.raises(KeyError):
        derive_fuel("Nuclear power plant")


def test_asset_fuel_table_has_no_blank_targets():
    """Every mapping target is a real fuel label (no empty-string holes)."""
    assert all(ASSET_TYPE_TO_FUEL.values())


# --- collapse_status: one status per plant, operating-aware -------------------


def test_collapse_status_all_same_passes_through():
    """A plant whose units share one status keeps it."""
    assert collapse_status(["6 operating", "6 operating"]) == "6 operating"


def test_collapse_status_operating_wins_over_retired():
    """Uong Bi I: an operating extension + retired old units -> operating.

    A naive numeric max would pick '10 retired' (10 > 6) and mislabel a live
    plant as retired. Any operating unit makes the plant operating.
    """
    assert collapse_status(["10 retired", "10 retired", "6 operating"]) == "6 operating"


def test_collapse_status_operating_wins_over_announced():
    """Dong Nai Formosa: operating base + announced expansion -> operating."""
    assert collapse_status(["6 operating", "6 operating", "1 announced"]) == "6 operating"


def test_collapse_status_no_operating_takes_most_advanced_pre_operating():
    """With no operating unit, the most-advanced pre-operating stage wins."""
    assert collapse_status(["2 proposed", "3 added to PDP"]) == "3 added to PDP"


# --- INPUT validation: duplicated unit rows hard-fail ------------------------


def test_input_duplicate_unit_row_raises():
    """The 'Quảng Trị 1 Unit 2' x2 case must abort — never sum 660+660."""
    df = _units(
        [
            {"name": "Quảng Trị 1 Unit 2", "plant": "Quảng Trị 1", "unit": "Unit 2", "capacity_mwe": "660", "level": "unit"},
            {"name": "Quảng Trị 1 Unit 2", "plant": "Quảng Trị 1", "unit": "Unit 2", "capacity_mwe": "660", "level": "unit"},
        ]
    )
    with pytest.raises(ValueError, match="Quảng Trị 1 Unit 2"):
        validate_input_no_duplicate_units(df)


def test_input_distinct_units_pass():
    """Two distinct units of one plant are fine."""
    df = _units(
        [
            {"name": "Quảng Trị 1 Unit 1", "plant": "Quảng Trị 1", "unit": "Unit 1", "level": "unit"},
            {"name": "Quảng Trị 1 Unit 2", "plant": "Quảng Trị 1", "unit": "Unit 2", "level": "unit"},
        ]
    )
    validate_input_no_duplicate_units(df)  # must not raise


# --- capacity validation: spreadsheet error values hard-fail -----------------


def test_capacity_err_value_raises():
    """A leaked spreadsheet error (Err:510) is corruption — hard stop, named.

    Summing around it would silently understate the plant. This is the real
    Vung Ang 2 case in the current snapshot.
    """
    df = _units(
        [
            {"name": "Vung Ang 2 Unit 1", "plant": "Vung Ang 2", "unit": "Unit 1", "capacity_mwe": "Err:510", "level": "unit"},
        ]
    )
    with pytest.raises(ValueError, match="Vung Ang 2 Unit 1"):
        validate_capacity_numeric(df)


def test_capacity_empty_is_allowed():
    """An empty capacity cell is legitimately-unknown, not corruption — allowed."""
    df = _units([{"name": "NĐ Miền Bắc 1", "plant": "NĐ Miền Bắc 1", "capacity_mwe": "", "level": "plant"}])
    validate_capacity_numeric(df)  # must not raise


def test_capacity_numeric_passes():
    """Numeric capacities pass."""
    df = _units([{"name": "A", "plant": "A", "capacity_mwe": "650", "level": "plant"}])
    validate_capacity_numeric(df)  # must not raise


def test_aggregate_empty_capacity_sums_as_zero():
    """A plant whose only unit has unknown (empty) capacity reports 0."""
    df = _units(
        [
            {"name": "NĐ Miền Bắc 1", "plant": "NĐ Miền Bắc 1", "unit": "", "province": "X", "asset_type": "Coal power plant", "capacity_mwe": "", "status": "2 proposed", "level": "plant"},
        ]
    )
    out = aggregate(df)
    assert out.iloc[0]["capacity_mwe"] == "0"


# --- OUTPUT validation: plant name is the unique key -------------------------


def test_output_duplicate_plant_name_raises():
    """A plant name appearing twice in the output violates the unique key."""
    out = pd.DataFrame(
        {
            "name": ["Plant A", "Plant A"],
            "units_included": ["Plant A Unit 1", "Plant A Unit 2"],
        }
    )
    with pytest.raises(ValueError, match="Plant A"):
        validate_output_unique_plants(out)


def test_output_repeated_unit_in_units_included_raises():
    """A unit listed twice within one plant's Units Included is a refusal."""
    out = pd.DataFrame(
        {
            "name": ["Plant A"],
            "units_included": ["Plant A Unit 1, Plant A Unit 1"],
        }
    )
    with pytest.raises(ValueError, match="Plant A Unit 1"):
        validate_output_unique_plants(out)


def test_output_unit_in_two_groups_raises():
    """A unit appearing in two different plants' Units Included is a refusal."""
    out = pd.DataFrame(
        {
            "name": ["Plant A", "Plant B"],
            "units_included": ["Shared Unit 1", "Shared Unit 1"],
        }
    )
    with pytest.raises(ValueError, match="Shared Unit 1"):
        validate_output_unique_plants(out)


def test_output_clean_passes():
    """A well-formed plant table is accepted silently."""
    out = pd.DataFrame(
        {
            "name": ["Plant A", "Plant B"],
            "units_included": ["Plant A Unit 1, Plant A Unit 2", "Plant B"],
        }
    )
    validate_output_unique_plants(out)  # must not raise


# --- aggregate: end-to-end on a synthetic frame ------------------------------


def test_aggregate_sums_capacity_and_joins_units():
    """Two units roll up to one plant: capacity summed, units joined."""
    df = _units(
        [
            {"name": "An Khánh 1 Unit 1", "plant": "An Khánh 1", "unit": "Unit 1", "province": "Thai Nguyen", "asset_type": "Coal power plant", "capacity_mwe": "58", "status": "6 operating", "level": "unit"},
            {"name": "An Khánh 1 Unit 2", "plant": "An Khánh 1", "unit": "Unit 2", "province": "Thai Nguyen", "asset_type": "Coal power plant", "capacity_mwe": "58", "status": "6 operating", "level": "unit"},
        ]
    )
    out = aggregate(df)
    assert len(out) == 1
    row = out.iloc[0]
    assert row["name"] == "An Khánh 1"
    assert row["capacity_mwe"] == "116"
    assert row["fuel"] == "coal"
    assert row["units_included"] == "An Khánh 1 Unit 1, An Khánh 1 Unit 2"
    assert row["level"] == "plant"


def test_aggregate_plant_grain_passes_through():
    """A plant-grain row becomes its own plant; units_included is the name."""
    df = _units(
        [
            {"name": "Bà Rịa GT", "plant": "Bà Rịa GT", "unit": "", "province": "BR-VT", "asset_type": "Gas power plant", "capacity_mwe": "46", "status": "6 operating", "level": "plant"},
        ]
    )
    out = aggregate(df)
    assert len(out) == 1
    assert out.iloc[0]["name"] == "Bà Rịa GT"
    assert out.iloc[0]["units_included"] == "Bà Rịa GT"
    assert out.iloc[0]["fuel"] == "gas"


def test_aggregate_complex_grain_passes_through():
    """A complex-grain LNG row passes through keyed on its complex cell."""
    df = _units(
        [
            {"name": "LNG Cà Ná", "complex": "LNG Cà Ná", "plant": "", "unit": "", "province": "Ninh Thuan", "asset_type": "Gas power plant", "capacity_mwe": "1500", "status": "3 added to PDP", "level": "complex"},
        ]
    )
    out = aggregate(df)
    assert len(out) == 1
    assert out.iloc[0]["name"] == "LNG Cà Ná"
    assert out.iloc[0]["units_included"] == "LNG Cà Ná"


def test_aggregate_multi_status_plant_collapses_not_refuses():
    """A phased-lifecycle plant (operating + announced) aggregates to ONE row.

    Dong Nai Formosa's units span statuses by design; the aggregator collapses
    status (operating wins) rather than refusing — defect-3 resolved, not
    surviving.
    """
    df = _units(
        [
            {"name": "Dong Nai Formosa Unit 1", "plant": "Dong Nai Formosa", "unit": "Unit 1", "province": "Dong Nai", "asset_type": "Coal power plant", "capacity_mwe": "150", "status": "6 operating", "level": "unit"},
            {"name": "Dong Nai Formosa Unit 2", "plant": "Dong Nai Formosa", "unit": "Unit 2", "province": "Dong Nai", "asset_type": "Coal power plant", "capacity_mwe": "150", "status": "6 operating", "level": "unit"},
            {"name": "Dong Nai Formosa Unit 3", "plant": "Dong Nai Formosa", "unit": "Unit 3", "province": "Dong Nai", "asset_type": "Coal power plant", "capacity_mwe": "150", "status": "1 announced", "level": "unit"},
        ]
    )
    out = aggregate(df)
    assert len(out) == 1
    assert out.iloc[0]["name"] == "Dong Nai Formosa"
    assert out.iloc[0]["capacity_mwe"] == "450"
    assert out.iloc[0]["status"] == "6 operating"


def test_aggregate_non_constant_province_raises():
    """A plant whose units claim two provinces is a master error — hard stop."""
    df = _units(
        [
            {"name": "Split Unit 1", "plant": "Split", "unit": "Unit 1", "province": "Prov A", "asset_type": "Coal power plant", "capacity_mwe": "100", "status": "6 operating", "level": "unit"},
            {"name": "Split Unit 2", "plant": "Split", "unit": "Unit 2", "province": "Prov B", "asset_type": "Coal power plant", "capacity_mwe": "100", "status": "6 operating", "level": "unit"},
        ]
    )
    with pytest.raises(ValueError, match="Split"):
        aggregate(df)


def test_aggregate_rejects_duplicate_unit_input():
    """The input guard fires inside aggregate (defense in depth)."""
    df = _units(
        [
            {"name": "Quảng Trị 1 Unit 2", "plant": "Quảng Trị 1", "unit": "Unit 2", "province": "QT", "asset_type": "Coal power plant", "capacity_mwe": "660", "status": "5 construction", "level": "unit"},
            {"name": "Quảng Trị 1 Unit 2", "plant": "Quảng Trị 1", "unit": "Unit 2", "province": "QT", "asset_type": "Coal power plant", "capacity_mwe": "660", "status": "5 construction", "level": "unit"},
        ]
    )
    with pytest.raises(ValueError, match="Quảng Trị 1 Unit 2"):
        aggregate(df)


# --- integration: the real extracted units CSV aggregates green ---------------


@pytest.mark.integration
def test_real_units_aggregate_synthetic_clean_frame(tmp_path):
    """A clean unit frame aggregates to unique plants, capacity = sum of units.

    This anchors the end-to-end contract to a small synthetic frame so failures
    localize to the aggregator, independent of master-snapshot content (see
    test_real_snapshot_aggregates_green for the real-snapshot path). Plant names
    are unique, none synthesized; capacity is the unit sum.
    """
    import subprocess

    df = _units(
        [
            {"name": "An Khánh 1 Unit 1", "plant": "An Khánh 1", "unit": "Unit 1", "province": "Thai Nguyen", "asset_type": "Coal power plant", "capacity_mwe": "58", "status": "6 operating", "level": "unit"},
            {"name": "An Khánh 1 Unit 2", "plant": "An Khánh 1", "unit": "Unit 2", "province": "Thai Nguyen", "asset_type": "Coal power plant", "capacity_mwe": "58", "status": "6 operating", "level": "unit"},
            {"name": "Bà Rịa GT", "plant": "Bà Rịa GT", "unit": "", "province": "BR-VT", "asset_type": "Gas power plant", "capacity_mwe": "46", "status": "6 operating", "level": "plant"},
            {"name": "LNG Cà Ná", "complex": "LNG Cà Ná", "plant": "", "unit": "", "province": "Ninh Thuan", "asset_type": "Gas power plant", "capacity_mwe": "1500", "status": "3 added to PDP", "level": "complex"},
        ]
    )
    units = tmp_path / "units.csv"
    plants = tmp_path / "plants.csv"
    df.to_csv(units, index=False)

    repo_root = Path(__file__).resolve().parent.parent
    aggregate_script = repo_root / "data" / "reference" / "aggregate_units.py"
    r = subprocess.run(
        [sys.executable, str(aggregate_script), "--input", str(units), "--output", str(plants)],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, (r.stdout, r.stderr)

    out = pd.read_csv(plants, dtype=str)
    assert not out["name"].duplicated().any()
    assert len(out) == 3
    assert {"name", "province", "fuel", "capacity_mwe", "status", "units_included", "level"} <= set(out.columns)
    an_khanh = out[out["name"] == "An Khánh 1"].iloc[0]
    assert an_khanh["capacity_mwe"] == "116"


@pytest.mark.integration
def test_real_snapshot_aggregates_green(tmp_path):
    """The pinned snapshot extracts and aggregates end-to-end without refusal.

    History: the first 2026-06-05 capture carried a leaked spreadsheet Err:510
    in Vung Ang 2's capacity and this test asserted REFUSAL (non-numeric
    capacity is corruption, not data). The author fixed the formula in the
    master and the snapshot was same-day recaptured (see PROVENANCE.md), so the
    real-snapshot path now asserts the green pipeline: unique plant names, no
    synthesized names, numeric capacities throughout.
    """
    import subprocess

    from aedist.config import VN_THERMAL_MASTER_SNAPSHOT_ODS

    repo_root = Path(__file__).resolve().parent.parent
    extract = repo_root / "data" / "reference" / "extract_ods.py"
    aggregate_script = repo_root / "data" / "reference" / "aggregate_units.py"
    units = tmp_path / "units.csv"
    plants = tmp_path / "plants.csv"

    r1 = subprocess.run(
        [sys.executable, str(extract), "--input", str(VN_THERMAL_MASTER_SNAPSHOT_ODS), "--output", str(units)],
        capture_output=True,
        text=True,
    )
    assert r1.returncode == 0, (r1.stdout, r1.stderr)

    r2 = subprocess.run(
        [sys.executable, str(aggregate_script), "--input", str(units), "--output", str(plants)],
        capture_output=True,
        text=True,
    )
    assert r2.returncode == 0, (r2.stdout, r2.stderr)

    out = pd.read_csv(plants, dtype=str)
    assert len(out) == 173  # pinned snapshot: 170 v2 plants -> 173 v2.1 (extensions standalone, 0445)
    assert not out["name"].duplicated().any()
    assert (out["name"].str.strip() != "").all()
    capacities = pd.to_numeric(out["capacity_mwe"], errors="coerce")
    assert capacities.notna().all()
    assert (capacities >= 0).all()
    # Zero capacity is legitimate only for placeholder rows the master keeps
    # for traceability: exploring (no design yet) or cancelled (never built).
    zero_cap = out[capacities == 0]
    assert zero_cap["status"].isin(["0 exploring", "9 cancelled"]).all(), (
        zero_cap[["name", "status"]].to_string()
    )
