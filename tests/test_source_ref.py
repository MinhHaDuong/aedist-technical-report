"""Tests for source_ref provenance flow through the pipeline."""

import csv
from pathlib import Path

import pytest

from aedist.schema import FuelType, MatchType, Plant, PlantStatus, ReconciliationEntry
from aedist.reconcile import plants_to_dataframe, reconcile
from aedist.evaluate import load_plants_csv, _save_reconciliation_csv


# ---------------------------------------------------------------------------
# 1. load_plants_csv reads source_ref from CSV
# ---------------------------------------------------------------------------

def test_load_plants_csv_reads_source_ref(tmp_path: Path) -> None:
    csv_path = tmp_path / "plants.csv"
    csv_path.write_text(
        "name,fuel,capacity_mwe,source_ref\n"
        "Alpha,coal,100,Decision 1509/QD-BCT\n"
        "Beta,gas,200,\n"
        "Gamma,oil,300,Annexe II.1\n"
    )

    plants = load_plants_csv(csv_path)

    assert len(plants) == 3
    assert plants[0].source_ref == "Decision 1509/QD-BCT"
    assert plants[1].source_ref is None  # empty string becomes None
    assert plants[2].source_ref == "Annexe II.1"


# ---------------------------------------------------------------------------
# 2. plants_to_dataframe preserves source_ref
# ---------------------------------------------------------------------------

def test_plants_to_dataframe_preserves_source_ref() -> None:
    plants = [
        Plant(name="Alpha", capacity_mwe=100, source_ref="Doc A"),
        Plant(name="Beta", capacity_mwe=200, source_ref="Doc B"),
        Plant(name="Gamma", capacity_mwe=300),
    ]

    df = plants_to_dataframe(plants)

    assert "source_ref" in df.columns
    refs = df["source_ref"].tolist()
    assert "Doc A" in refs
    assert "Doc B" in refs


# ---------------------------------------------------------------------------
# 3. reconcile() propagates source_ref to ReconciliationEntry
# ---------------------------------------------------------------------------

def test_reconcile_propagates_source_ref() -> None:
    ref = [
        Plant(name="Alpha Coal", fuel=FuelType.COAL, capacity_mwe=100, source_ref="Ref-Doc-1"),
        Plant(name="Beta Gas", fuel=FuelType.GAS, capacity_mwe=200, source_ref="Ref-Doc-2"),
    ]
    sys = [
        Plant(name="Alpha Coal", fuel=FuelType.COAL, capacity_mwe=100, source_ref="Sys-Doc-1"),
        Plant(name="Beta Gas", fuel=FuelType.GAS, capacity_mwe=200, source_ref="Sys-Doc-2"),
    ]

    entries = reconcile(ref, sys)

    matched = [e for e in entries if e.match_type not in (MatchType.REFERENCE_ONLY, MatchType.SYSTEM_ONLY)]
    assert len(matched) == 2

    ref_srcs = {e.reference_source_ref for e in matched}
    sys_srcs = {e.system_source_ref for e in matched}
    assert ref_srcs == {"Ref-Doc-1", "Ref-Doc-2"}
    assert sys_srcs == {"Sys-Doc-1", "Sys-Doc-2"}


# ---------------------------------------------------------------------------
# 4. _save_reconciliation_csv includes source_ref columns
# ---------------------------------------------------------------------------

def test_save_reconciliation_csv_includes_source_ref(tmp_path: Path) -> None:
    entries = [
        ReconciliationEntry(
            reference_name="Alpha",
            system_name="Alpha",
            match_type=MatchType.EXACT,
            reference_source_ref="Ref-A",
            system_source_ref="Sys-A",
        ),
        ReconciliationEntry(
            reference_name="Beta",
            system_name=None,
            match_type=MatchType.REFERENCE_ONLY,
            reference_source_ref="Ref-B",
            system_source_ref=None,
        ),
    ]

    csv_path = tmp_path / "reconciliation.csv"
    _save_reconciliation_csv(entries, csv_path)

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert "reference_source_ref" in reader.fieldnames
    assert "system_source_ref" in reader.fieldnames

    assert rows[0]["reference_source_ref"] == "Ref-A"
    assert rows[0]["system_source_ref"] == "Sys-A"
    assert rows[1]["reference_source_ref"] == "Ref-B"
    assert rows[1]["system_source_ref"] == ""  # csv writes None as empty string
