"""Tests for data/reference/GEM_aggregate.py — GEM unit -> plant aggregation.

The aggregator consumes gem_units.csv (the tracked GEM export) and rolls unit
rows into plant rows via Phase-aware grouping. Phase info embedded in Unit name
("Phase 1 Unit 2") is appended to Plant name to produce unique keys across
phase-split plants.

One invariant (ticket 0429, adapted from 0416):
- OUTPUT: the composite key (Name, Aggregated Units) must be unique.
  GEM intentionally lists the same physical plant in multiple rows with
  different fuels or statuses — bare Name is not unique. Only a truly
  duplicate row (same Name AND same Aggregated Units) is a hard failure.

The tracked raw input gem_units.csv is confirmed to reproduce the base columns
of gem_thermal.csv exactly (audit verified before implementation).
"""

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from data.reference.GEM_aggregate import (
    aggregate_table,
    validate_output_unique_plants,
)


def _units(rows: list[dict]) -> pd.DataFrame:
    """A unit-grain DataFrame with GEM schema columns."""
    cols = ["Plant name", "Unit name", "Province", "Fuel", "Capacity", "Status"]
    return pd.DataFrame([{c: r.get(c, "") for c in cols} for r in rows])


# --- argparse: --input and --output flags present in source -------------------


def test_argparse_flags_present():
    """GEM_aggregate.py must declare --input and --output (no hardcoded paths)."""
    src = Path(__file__).resolve().parent.parent / "data" / "reference" / "GEM_aggregate.py"
    code = src.read_text(encoding="utf-8")
    assert "--input" in code, "--input argparse flag missing from GEM_aggregate.py"
    assert "--output" in code, "--output argparse flag missing from GEM_aggregate.py"
    assert "if __name__" in code, "main() guard missing from GEM_aggregate.py"


# --- validate_output_unique_plants: uniqueness guard -------------------------


def test_uniqueness_guard_fires_on_identical_rows():
    """Identical (Name, Aggregated Units) is a hard failure."""
    out = pd.DataFrame(
        {
            "Name": ["Plant A", "Plant A"],
            "Aggregated Units": ["GT1", "GT1"],  # same key → duplicate
            "Province": ["P1", "P1"],
            "Status": ["operating", "operating"],
        }
    )
    with pytest.raises(ValueError, match="Plant A"):
        validate_output_unique_plants(out)


def test_uniqueness_guard_passes_same_name_different_units():
    """Same Name with different Aggregated Units is legitimate GEM multi-row behaviour."""
    out = pd.DataFrame(
        {
            "Name": ["Ba Ria", "Ba Ria"],
            "Aggregated Units": ["1", "2"],  # different units → distinct rows
            "Province": ["Ba Ria - Vung Tau", "Ba Ria - Vung Tau"],
            "Status": ["operating", "cancelled - inferred 4 y"],
        }
    )
    validate_output_unique_plants(out)  # must not raise


def test_uniqueness_guard_passes_clean_frame():
    """A frame with unique plant Names and units passes silently."""
    out = pd.DataFrame(
        {
            "Name": ["Plant A", "Plant B"],
            "Aggregated Units": ["GT1", "GT1"],
            "Province": ["P1", "P2"],
            "Status": ["operating", "operating"],
        }
    )
    validate_output_unique_plants(out)  # must not raise


# --- aggregate_table: core aggregation logic ----------------------------------


def test_aggregate_groupable_units_sum_capacity():
    """Two numbered units roll up to one plant: capacity summed, units joined."""
    df = _units(
        [
            {"Plant name": "Vinh Tan 2", "Unit name": "Unit 1", "Province": "Binh Thuan", "Fuel": "Coal", "Capacity": 622.0, "Status": "operating"},
            {"Plant name": "Vinh Tan 2", "Unit name": "Unit 2", "Province": "Binh Thuan", "Fuel": "Coal", "Capacity": 622.0, "Status": "operating"},
        ]
    )
    out = aggregate_table(df)
    assert len(out) == 1
    row = out.iloc[0]
    assert row["Name"] == "Vinh Tan 2"
    assert row["Capacity"] == 1244.0
    assert "Unit 1" in row["Aggregated Units"]
    assert "Unit 2" in row["Aggregated Units"]


def test_aggregate_phase_split_creates_distinct_keys():
    """Phase-split units produce distinct plant keys (An Khanh Phase 1, Phase 2).

    This is the core GEM data model: Phase is embedded in Unit name and appended
    to Plant name, so phases get distinct keys rather than colliding.
    """
    df = _units(
        [
            {"Plant name": "An Khanh", "Unit name": "Phase 1 Unit 1", "Province": "Thai Nguyen", "Fuel": "Coal", "Capacity": 100.0, "Status": "operating"},
            {"Plant name": "An Khanh", "Unit name": "Phase 1 Unit 2", "Province": "Thai Nguyen", "Fuel": "Coal", "Capacity": 100.0, "Status": "operating"},
            {"Plant name": "An Khanh", "Unit name": "Phase 2 Unit 1", "Province": "Thai Nguyen", "Fuel": "Coal", "Capacity": 150.0, "Status": "pre-permit"},
        ]
    )
    out = aggregate_table(df)
    assert len(out) == 2
    names = set(out["Name"])
    assert "An Khanh Phase 1" in names
    assert "An Khanh Phase 2" in names
    phase1 = out[out["Name"] == "An Khanh Phase 1"].iloc[0]
    assert phase1["Capacity"] == 200.0


def test_aggregate_non_groupable_passes_through():
    """A unit whose name doesn't match the groupable pattern passes through."""
    df = _units(
        [
            {"Plant name": "Some Plant", "Unit name": "GT1", "Province": "Hanoi", "Fuel": "Gas", "Capacity": 150.0, "Status": "operating"},
        ]
    )
    out = aggregate_table(df)
    assert len(out) == 1
    assert out.iloc[0]["Name"] == "Some Plant"
    assert out.iloc[0]["Aggregated Units"] == "GT1"


def test_aggregate_same_name_different_units_is_valid():
    """Same plant name with different unit names produces two rows — legitimate GEM output."""
    # GT1 / GT2: non-groupable, different unit names → different Aggregated Units → valid
    df = _units(
        [
            {"Plant name": "Dup Plant", "Unit name": "GT1", "Province": "P1", "Fuel": "Gas", "Capacity": 100.0, "Status": "operating"},
            {"Plant name": "Dup Plant", "Unit name": "GT2", "Province": "P1", "Fuel": "Gas", "Capacity": 100.0, "Status": "pre-permit"},
        ]
    )
    out = aggregate_table(df)
    assert len(out) == 2  # two distinct rows, no guard firing


def test_aggregate_uniqueness_guard_fires_on_identical_composite_key():
    """The output uniqueness guard fires on truly identical (Name, Aggregated Units)."""
    # Same plant name + same non-groupable unit name → duplicate composite key after aggregation.
    df = _units(
        [
            {"Plant name": "Dup Plant", "Unit name": "GT1", "Province": "P1", "Fuel": "Gas", "Capacity": 100.0, "Status": "operating"},
            {"Plant name": "Dup Plant", "Unit name": "GT1", "Province": "P1", "Fuel": "Gas", "Capacity": 150.0, "Status": "operating"},
        ]
    )
    with pytest.raises(ValueError, match="Dup Plant"):
        aggregate_table(df)


# --- integration: script runs end-to-end via subprocess ----------------------


@pytest.mark.integration
def test_script_runs_with_real_gem_units(tmp_path):
    """GEM_aggregate.py --input gem_units.csv --output <tmp> exits 0.

    Verifies the script is callable with tracked input and produces 153 rows,
    matching the committed gem_thermal.csv (base columns, before classification).
    GEM legitimately has duplicate plant Names (same physical plant listed with
    different fuels or statuses); the composite key (Name, Aggregated Units)
    is unique — that is what the script's guard checks.
    """
    repo_root = Path(__file__).resolve().parent.parent
    script = repo_root / "data" / "reference" / "GEM_aggregate.py"
    gem_units = repo_root / "data" / "reference" / "gem_units.csv"
    out = tmp_path / "gem_aggregated.csv"

    r = subprocess.run(
        [sys.executable, str(script), "--input", str(gem_units), "--output", str(out)],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, (r.stdout, r.stderr)

    result = pd.read_csv(out)
    assert len(result) == 153, f"Expected 153 GEM plants, got {len(result)}"
    # Composite key must be unique (GEM's real invariant — bare Name is not unique by design)
    assert not result.duplicated(subset=["Name", "Aggregated Units"]).any(), (
        "Duplicate (Name, Aggregated Units) composite key in output"
    )
    assert {"Name", "Province", "Fuel", "Capacity", "Status", "Aggregated Units"} <= set(result.columns)


@pytest.mark.integration
def test_script_missing_input_exits_nonzero(tmp_path):
    """GEM_aggregate.py exits 1 when --input file does not exist."""
    repo_root = Path(__file__).resolve().parent.parent
    script = repo_root / "data" / "reference" / "GEM_aggregate.py"
    out = tmp_path / "out.csv"

    r = subprocess.run(
        [sys.executable, str(script), "--input", str(tmp_path / "nonexistent.csv"), "--output", str(out)],
        capture_output=True,
        text=True,
    )
    assert r.returncode != 0
