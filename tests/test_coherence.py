"""Tests for coherence checks (ticket 0078)."""

import pytest

from aedist.coherence import (
    CoherenceIssue,
    ControlTotal,
    IssueLevel,
    IssueSeverity,
    check_aggregate_coherence,
    check_coherence,
    check_cross_row_coherence,
    check_row_coherence,
)
from aedist.schema import FuelType, Plant, PlantStatus


# ── Row-level ───────────────────────────────────────────────────────


def test_zero_capacity_flagged():
    plants = [Plant(name="Bad Plant", capacity_mwe=0, fuel=FuelType.COAL)]
    issues = check_row_coherence(plants)
    assert any(i.check == "zero_or_negative_capacity" for i in issues)


def test_negative_capacity_rejected_by_schema():
    """Pydantic enforces capacity_mwe >= 0 at schema level."""
    with pytest.raises(Exception):  # ValidationError
        Plant(name="Worse Plant", capacity_mwe=-100, fuel=FuelType.COAL)


def test_unknown_fuel_warned():
    plants = [Plant(name="Mystery Plant", fuel=FuelType.UNKNOWN)]
    issues = check_row_coherence(plants)
    assert any(i.check == "unknown_fuel" for i in issues)


def test_unknown_province_warned():
    plants = [Plant(name="Lost Plant", province="Atlantis", fuel=FuelType.COAL)]
    issues = check_row_coherence(plants)
    assert any(i.check == "unknown_province" for i in issues)


def test_known_province_ok():
    plants = [Plant(name="Good Plant", province="Quảng Ninh", fuel=FuelType.COAL)]
    issues = check_row_coherence(plants)
    assert not any(i.check == "unknown_province" for i in issues)


def test_ascii_province_alias_ok():
    """Reference uses ASCII-only spellings like 'Bac Giang'."""
    plants = [Plant(name="Good Plant", province="Bac Giang", fuel=FuelType.COAL)]
    issues = check_row_coherence(plants)
    assert not any(i.check == "unknown_province" for i in issues)


def test_retired_future_cod_flagged():
    plants = [Plant(
        name="Time Traveller",
        fuel=FuelType.COAL,
        status=PlantStatus.RETIRED,
        cod="2030",
    )]
    issues = check_row_coherence(plants)
    assert any(i.check == "retired_future_cod" for i in issues)


def test_clean_row_no_issues():
    plants = [Plant(
        name="Pha Lai",
        fuel=FuelType.COAL,
        status=PlantStatus.OPERATIONAL,
        province="Hải Dương",
        capacity_mwe=440,
    )]
    issues = check_row_coherence(plants)
    assert issues == []


# ── Cross-row ───────────────────────────────────────────────────────


def test_duplicate_detected():
    plants = [
        Plant(name="Pha Lai", province="Hai Duong", fuel=FuelType.COAL),
        Plant(name="Pha Lai", province="Hai Duong", fuel=FuelType.COAL),
    ]
    issues = check_cross_row_coherence(plants)
    assert any(i.check == "duplicate_plant" for i in issues)
    dup = [i for i in issues if i.check == "duplicate_plant"][0]
    assert dup.row_indices == [0, 1]


def test_same_name_different_province_ok():
    plants = [
        Plant(name="Solar Farm", province="Ninh Thuận", fuel=FuelType.COAL),
        Plant(name="Solar Farm", province="Bình Thuận", fuel=FuelType.COAL),
    ]
    issues = check_cross_row_coherence(plants)
    assert not any(i.check == "duplicate_plant" for i in issues)


def test_no_duplicates_no_issues():
    plants = [
        Plant(name="Plant A", province="Hà Nội", fuel=FuelType.COAL),
        Plant(name="Plant B", province="Hà Nội", fuel=FuelType.GAS),
    ]
    issues = check_cross_row_coherence(plants)
    assert issues == []


# ── Aggregate (control totals) ──────────────────────────────────────


def test_control_total_within_tolerance():
    plants = [
        Plant(name="A", fuel=FuelType.COAL, capacity_mwe=500),
        Plant(name="B", fuel=FuelType.COAL, capacity_mwe=480),
    ]
    totals = [ControlTotal(source="PDP8", fuel=FuelType.COAL, total_mw=1000)]
    issues = check_aggregate_coherence(plants, totals, tolerance_pct=5.0)
    assert issues == []  # 980/1000 = 2% deviation


def test_control_total_exceeded():
    plants = [
        Plant(name="A", fuel=FuelType.COAL, capacity_mwe=500),
        Plant(name="B", fuel=FuelType.COAL, capacity_mwe=200),
    ]
    totals = [ControlTotal(source="PDP8", fuel=FuelType.COAL, total_mw=1000)]
    issues = check_aggregate_coherence(plants, totals, tolerance_pct=5.0)
    assert any(i.check == "control_total_deviation" for i in issues)


def test_control_total_filters_by_fuel():
    plants = [
        Plant(name="Coal A", fuel=FuelType.COAL, capacity_mwe=500),
        Plant(name="Gas B", fuel=FuelType.GAS, capacity_mwe=300),
    ]
    totals = [ControlTotal(source="PDP8", fuel=FuelType.COAL, total_mw=500)]
    issues = check_aggregate_coherence(plants, totals, tolerance_pct=5.0)
    assert issues == []  # Gas plant excluded from coal check


def test_control_total_filters_by_province():
    plants = [
        Plant(name="A", fuel=FuelType.COAL, capacity_mwe=500, province="Quảng Ninh"),
        Plant(name="B", fuel=FuelType.COAL, capacity_mwe=300, province="Hà Tĩnh"),
    ]
    totals = [ControlTotal(
        source="Provincial plan",
        fuel=FuelType.COAL,
        province="Quảng Ninh",
        total_mw=500,
    )]
    issues = check_aggregate_coherence(plants, totals, tolerance_pct=5.0)
    assert issues == []  # Hà Tĩnh plant excluded


# ── Main entry point ────────────────────────────────────────────────


def test_check_coherence_runs_all_levels():
    plants = [
        Plant(name="Good", fuel=FuelType.COAL, capacity_mwe=100, province="Hà Nội"),
        Plant(name="Good", fuel=FuelType.COAL, capacity_mwe=100, province="Hà Nội"),  # dup
    ]
    issues = check_coherence(plants)
    levels = {i.level for i in issues}
    assert IssueLevel.CROSS_ROW in levels  # duplicate caught
