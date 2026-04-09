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
