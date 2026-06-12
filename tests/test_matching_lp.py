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


# ---------------------------------------------------------------------------
# Digit-asymmetric veto (ticket 0551): base name vs phase-suffixed sibling
# ---------------------------------------------------------------------------


def test_base_vs_phase_sibling_vetoed_lp():
    """'ca na' (no digits) must NOT match phase sibling 'ca na 2' (partial_ratio 100)."""
    ref = pd.DataFrame(
        [
            _row("Cà Ná 2", "ca na 2", 1500.0),
            _row("Cà Ná 3", "ca na 3", 1500.0),
        ]
    )
    sys = pd.DataFrame([_row("Cà Ná", "ca na", 1500.0)])

    result = reconcile(ref, sys)

    system_only = result[result["status"] == "Only in file2"]
    assert len(system_only) == 1, "base name 'ca na' must not match a phase-suffixed sibling"


def test_same_digit_pair_still_blocked_lp():
    """'vung ang 1' vs 'vung ang 2' stays blocked by the symmetric veto."""
    ref = pd.DataFrame([_row("Vũng Áng 1", "vung ang 1", 1200.0)])
    sys = pd.DataFrame([_row("Vũng Áng 2", "vung ang 2", 1200.0)])

    result = reconcile(ref, sys)

    assert not result["status"].str.startswith("Matched").any()


def test_digit_free_distinct_pair_stays_matchable_lp():
    """A digit-free fuzzy pair matches even when the base is phase-ambiguous.

    'long son' is ambiguous (siblings 2 and 3 present), so pairings with the
    digit-suffixed siblings are vetoed — but the digit-free pairing with
    'long son chemical' must survive and win.
    """
    ref = pd.DataFrame(
        [
            _row("Long Sơn chemical", "long son chemical", 1500.0),
            _row("Long Sơn 2", "long son 2", 1500.0),
            _row("Long Sơn 3", "long son 3", 1500.0),
        ]
    )
    sys = pd.DataFrame([_row("Long Sơn", "long son", 1500.0)])

    result = reconcile(ref, sys)

    matched = result[result["status"].str.startswith("Matched")]
    assert len(matched) == 1
    assert matched.iloc[0]["name_file1"] == "Long Sơn chemical"


def test_ambiguous_phase_bases_helper():
    """Bases with >= 2 digit variants are ambiguous; single-variant bases are not."""
    from aedist.matching.lp import ambiguous_phase_bases

    names = ["ca na 2", "ca na 3", "lng quang ninh 1", "long son chemical"]
    assert ambiguous_phase_bases(names) == frozenset({"ca na"})


def test_digit_veto_helper_branches():
    """Unit coverage of digit_veto: symmetric, asymmetric-ambiguous, digit-free."""
    from aedist.matching.lp import digit_veto

    ambiguous = frozenset({"ca na"})
    # Symmetric branch: differing digit sets — vetoed regardless of ambiguity.
    assert digit_veto("vung ang 1", "vung ang 2")
    # Equal digit sets — allowed.
    assert not digit_veto("mong duong 2", "na duong 2")
    # Asymmetric, base ambiguous — vetoed (either argument order).
    assert digit_veto("ca na", "ca na 2", ambiguous)
    assert digit_veto("ca na 2", "ca na", ambiguous)
    # Asymmetric, base not ambiguous — allowed.
    assert not digit_veto("lng quang ninh", "lng quang ninh 1", ambiguous)
    # Asymmetric and ambiguous, but stripped names differ at word level — allowed.
    assert not digit_veto("an khanh 1", "an khe", frozenset({"an khanh"}))
    # Digit-free both sides — never vetoed.
    assert not digit_veto("long son", "long son chemical", ambiguous)


def test_unambiguous_base_vs_single_sibling_matches_lp():
    """With a single phase sibling, the bare base name stays matchable (no ambiguity)."""
    ref = pd.DataFrame([_row("LNG Quảng Ninh 1", "lng quang ninh 1", 1500.0)])
    sys = pd.DataFrame([_row("LNG Quảng Ninh", "lng quang ninh", 1500.0)])

    result = reconcile(ref, sys)

    assert result["status"].str.startswith("Matched").any()


def test_base_vs_phase_sibling_vetoed_phased():
    """The phased matcher's digit guard must also block base-vs-sibling pairs."""
    from aedist.matching.phased import reconcile as phased_reconcile

    ref = pd.DataFrame(
        [
            _row("Cà Ná 2", "ca na 2", 1500.0),
            _row("Cà Ná 3", "ca na 3", 1500.0),
        ]
    )
    sys = pd.DataFrame([_row("Cà Ná", "ca na", 1500.0)])

    result = phased_reconcile(ref, sys)

    assert not result["status"].str.startswith("Matched").any()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
