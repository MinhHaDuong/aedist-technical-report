#
# Minh Ha-Duong, CNRS (2025)
# CC-BY-SA

"""Tests for LP-specific matching behaviour: combined-unit expansion and base/extension handling."""

import pandas as pd
import pytest

from aedist.matching.lp import expand_combined_units, reconcile

# ---------------------------------------------------------------------------
# expand_combined_units unit tests
# ---------------------------------------------------------------------------


def _row(name: str, name_clean: str, capacity: float) -> dict:
    return {"name": name, "name_clean": name_clean, "capacity_clean": capacity}


def test_expand_ampersand_splits_row():
    """'nhon trach 3 & 4' expands to two rows: 'nhon trach 3' and 'nhon trach 4'."""
    df = pd.DataFrame([_row("Nhơn Trạch 3 & 4", "nhon trach 3 & 4", 1500.0)])
    result = expand_combined_units(df)
    assert len(result) == 2
    names = set(result["name_clean"])
    assert names == {"nhon trach 3", "nhon trach 4"}


def test_expand_va_splits_row():
    """'nhon trach 3 va 4' (Vietnamese 'và') expands to two rows."""
    df = pd.DataFrame([_row("Nhơn Trạch 3 và 4", "nhon trach 3 va 4", 1500.0)])
    result = expand_combined_units(df)
    assert len(result) == 2
    names = set(result["name_clean"])
    assert names == {"nhon trach 3", "nhon trach 4"}


def test_expand_no_space_ampersand():
    """'nhon trach 3&4' (no spaces) expands to two rows."""
    df = pd.DataFrame([_row("NMĐ Nhơn Trạch 3&4", "nhon trach 3&4", 0.0)])
    result = expand_combined_units(df)
    assert len(result) == 2
    names = set(result["name_clean"])
    assert names == {"nhon trach 3", "nhon trach 4"}


def test_expand_preserves_non_combined():
    """Rows without combined patterns are unchanged."""
    df = pd.DataFrame(
        [
            _row("Na Duong 1", "na duong 1", 110.0),
            _row("Na Duong 2", "na duong 2", 110.0),
        ]
    )
    result = expand_combined_units(df)
    assert len(result) == 2
    assert set(result["name_clean"]) == {"na duong 1", "na duong 2"}


def test_expand_mixed_df():
    """Mixed DataFrame: combined row expands, others unchanged."""
    df = pd.DataFrame(
        [
            _row("Nhơn Trạch 3 & 4", "nhon trach 3 & 4", 1500.0),
            _row("Na Duong 1", "na duong 1", 110.0),
        ]
    )
    result = expand_combined_units(df)
    assert len(result) == 3
    assert "nhon trach 3" in result["name_clean"].values
    assert "nhon trach 4" in result["name_clean"].values
    assert "na duong 1" in result["name_clean"].values


def test_expand_empty_df():
    """Empty DataFrame returns empty DataFrame."""
    df = pd.DataFrame(columns=["name", "name_clean", "capacity_clean"])
    result = expand_combined_units(df)
    assert result.empty


# ---------------------------------------------------------------------------
# Integration: combined-unit row matches reference via LP reconcile
# ---------------------------------------------------------------------------


def test_combined_unit_matches_reference():
    """'Nhơn Trạch 3 & 4' system row matches reference 'LNG Nhơn Trạch 3' and 'LNG Nhơn Trạch 4'.

    First failing test from ticket 0393: a system list ["Nhơn Trạch 3 & 4"] against a
    reference ["LNG Nhơn Trạch 3", "LNG Nhơn Trạch 4"] yields two matched entries (or
    one matched + no FP), not a SYSTEM_ONLY.
    """
    ref = pd.DataFrame(
        [
            _row("LNG Nhơn Trạch 3", "nhon trach 3", 750.0),
            _row("LNG Nhơn Trạch 4", "nhon trach 4", 750.0),
        ]
    )
    sys = pd.DataFrame([_row("Nhơn Trạch 3 & 4", "nhon trach 3 & 4", 1500.0)])

    result = reconcile(ref, sys)

    system_only = result[result["status"] == "Only in file2"]
    assert len(system_only) == 0, (
        f"Expected no SYSTEM_ONLY rows, got: {system_only[['name_file2', 'status']].to_dict('records')}"
    )
    matched = result[result["status"].str.startswith("Matched")]
    assert len(matched) >= 1, "Expected at least one matched pair"


def test_combined_unit_ca_mau():
    """'ca mau 1 & 2' system row matches reference 'ca mau 1' and 'ca mau 2'."""
    ref = pd.DataFrame(
        [
            _row("LNG Cà Mau 1", "ca mau 1", 750.0),
            _row("LNG Cà Mau 2", "ca mau 2", 750.0),
        ]
    )
    sys = pd.DataFrame([_row("Cà Mau 1 & 2", "ca mau 1 & 2", 1500.0)])

    result = reconcile(ref, sys)

    system_only = result[result["status"] == "Only in file2"]
    assert len(system_only) == 0, (
        f"Expected no SYSTEM_ONLY rows, got: {system_only[['name_file2', 'status']].to_dict('records')}"
    )


def test_sibling_not_in_ref_stays_unmatched():
    """'song hau 3' (sibling not in ref) must NOT be force-matched to 'song hau 1' or 'song hau 2'.

    No precision regression: the unit-number veto must still block cross-unit FPs.
    """
    ref = pd.DataFrame(
        [
            _row("Sông Hậu 1", "song hau 1", 1200.0),
            _row("Sông Hậu 2", "song hau 2", 1200.0),
        ]
    )
    sys = pd.DataFrame([_row("Sông Hậu 3", "song hau 3", 1200.0)])

    result = reconcile(ref, sys)

    system_only = result[result["status"] == "Only in file2"]
    assert len(system_only) == 1, "song hau 3 must remain unmatched (sibling not in ref)"
    assert system_only.iloc[0]["name_file2"] == "Sông Hậu 3"


def test_base_and_extension_both_match():
    """Base 'duyen hai 3' and extension 'duyen hai 3 extension' both match when both present.

    Exit criterion 3 from ticket 0393.
    """
    ref = pd.DataFrame(
        [
            _row("Duyen Hai 3", "duyen hai 3", 1244.0),
            _row("Duyen Hai 3 extension", "duyen hai 3 extension", 660.0),
        ]
    )
    sys = pd.DataFrame(
        [
            _row("Duyen Hai 3", "duyen hai 3", 1244.0),
            _row("Duyen Hai 3 extension", "duyen hai 3 extension", 660.0),
        ]
    )

    result = reconcile(ref, sys)

    assert len(result) == 2
    statuses = set(result["status"])
    assert statuses.issubset({"Matched", "Matched (Fuzzy)"}), (
        f"Expected only matched statuses, got: {statuses}"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
