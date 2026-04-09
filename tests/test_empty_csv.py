# tests/test_empty_csv.py
"""Tests for empty CSV / empty plant list handling in the reconciliation pipeline."""

import pytest
from aedist.reconcile import plants_to_dataframe, reconcile
from aedist.schema import MatchType, Plant, FuelType, PlantStatus


class TestPlantsToDataframeEmpty:
    """plants_to_dataframe must return a valid cleaned DataFrame for empty input."""

    def test_empty_list_returns_dataframe_with_cleaned_columns(self):
        """plants_to_dataframe([]) returns a zero-row DataFrame with the
        columns that the LP matcher requires (name, name_clean, capacity_clean)
        plus the auxiliary cleaned columns. No exception raised."""
        df = plants_to_dataframe([])
        assert len(df) == 0
        # LP matcher requires these three columns
        assert "name" in df.columns
        assert "name_clean" in df.columns
        assert "capacity_clean" in df.columns
        # Auxiliary columns from cleaner
        assert "province_clean" in df.columns
        assert "fuel_clean" in df.columns
        assert "status_clean" in df.columns


class TestReconcileEmptySystem:
    """reconcile(reference, []) produces all-REFERENCE_ONLY entries."""

    @pytest.fixture
    def three_reference_plants(self):
        return [
            Plant(name="Pha Lai", fuel=FuelType.COAL, capacity_mwe=600),
            Plant(name="Uong Bi", fuel=FuelType.COAL, capacity_mwe=300),
            Plant(name="Ninh Binh", fuel=FuelType.COAL, capacity_mwe=100),
        ]

    def test_all_entries_are_reference_only(self, three_reference_plants):
        entries = reconcile(three_reference_plants, [])
        assert len(entries) == 3
        for e in entries:
            assert e.match_type == MatchType.REFERENCE_ONLY

    def test_empty_system_metrics_are_zero(self, three_reference_plants):
        from aedist.metrics import compute_metrics
        entries = reconcile(three_reference_plants, [])
        m = compute_metrics(entries)
        assert m.f1 == 0.0
        assert m.n_matched == 0
        assert m.n_missed == 3
        assert m.n_hallucinated == 0
