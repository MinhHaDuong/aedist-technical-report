"""Test that verify_tool uses the LP reconciler, not naive fuzzy matching.

The old implementation matched 'Mông Dương 2' to 'Na Dương 2' and
'LNG Quảng Ninh' to 'LNG Quảng Nam' via name-only fuzzy matching.
The LP reconciler considers capacity and province, preferring the
correct match when both candidates are in the reference.
"""

import pytest

from aedist.verify import verify_tool


@pytest.fixture
def reference_csv(tmp_path):
    """Reference with both correct and confusable candidates.

    Each test case has the CORRECT match and a WRONG match that
    naive fuzzy matching would prefer. The LP reconciler should
    pick the correct one (or leave unmatched if no correct option).
    """
    ref = tmp_path / "reference.csv"
    ref.write_text(
        "name,province,fuel,capacity_mwe,status\n"
        # Correct match for "Vũng Áng 2" (diacritics)
        "Vung Ang 2,Hà Tĩnh,Coal,1200,Constructing\n"
        # Wrong candidate for "LNG Quảng Ninh" — correct one also present
        "LNG Quảng Nam,Quảng Nam,LNG,1500,Planned\n"
        "LNG Quảng Ninh 1,Quảng Ninh,LNG,1500,Planned\n"
        # Wrong candidate for "Mông Dương 2" — no correct one
        "Na Dương 2,Lạng Sơn,Coal,110,Operational\n"
        "Mông Dương 1,Quảng Ninh,Coal,1080,Operational\n"
        # "Cam Pha 3" should not match "Cam Pha 1 & 2"
        "Cam Pha 3,Quảng Ninh,Coal,350,Operational\n"
        "Cẩm Phả 1,Quảng Ninh,Coal,300,Operational\n"
        "Cẩm Phả 2,Quảng Ninh,Coal,300,Operational\n"
        # "LNG Bình Định" should not match "Bình Định 1" (coal)
        "LNG Bình Định,Bình Định,LNG,1500,Planned\n"
        # Padding to make LP solver behave realistically
        "Ninh Bình,Ninh Bình,Coal,100,Operational\n"
        "Phả Lại 1,Hải Dương,Coal,400,Operational\n"
        "Phả Lại 2,Hải Dương,Coal,600,Operational\n"
        "Thái Bình 1,Thái Bình,Coal,600,Operational\n"
        "Thái Bình 2,Thái Bình,Coal,600,Constructing\n"
    )
    return ref


def test_prefers_correct_match_over_province_confusion(reference_csv):
    """LNG Quảng Ninh should match LNG Quảng Ninh 1, not LNG Quảng Nam."""
    rows = [
        {"name": "LNG Quảng Ninh", "fuel": "LNG", "province": "Quảng Ninh",
         "capacity_mwe": "1500"},
    ]
    annotated, _ = verify_tool(rows, reference_csv)
    assert annotated[0]["evidence_score"] == "3"
    assert "Quảng Ninh" in annotated[0]["verification_source"]
    assert "Quảng Nam" not in annotated[0]["verification_source"]


def test_rejects_different_plant_when_no_correct_match(reference_csv):
    """Mông Dương 2 should not match Na Dương 2 (different plant, different province)."""
    rows = [
        {"name": "Mông Dương 2", "fuel": "Coal", "province": "Quảng Ninh",
         "capacity_mwe": "1120"},
    ]
    annotated, _ = verify_tool(rows, reference_csv)
    # Should either match Mông Dương 1 (same complex) or be unmatched
    source = annotated[0].get("verification_source", "")
    assert "Na Dương" not in source, f"Matched wrong plant: {source}"


@pytest.mark.xfail(reason="LP reconciler does not yet penalize fuel mismatches (ticket 0035)")
def test_rejects_wrong_fuel(reference_csv):
    """Bình Định 1 (Coal, 1200 MW) should not match LNG Bình Định (LNG, 1500 MW)."""
    rows = [
        {"name": "Bình Định 1", "fuel": "Coal", "province": "Bình Định",
         "capacity_mwe": "1200"},
    ]
    annotated, _ = verify_tool(rows, reference_csv)
    source = annotated[0].get("verification_source", "")
    if annotated[0]["evidence_score"] == "3":
        # If matched, it should NOT be LNG Bình Định
        assert "LNG" not in source, f"Coal plant matched LNG reference: {source}"


def test_accepts_diacritics_variant(reference_csv):
    """Vũng Áng 2 should match Vung Ang 2 (same plant, diacritics differ)."""
    rows = [
        {"name": "Vũng Áng 2", "fuel": "Coal", "province": "Hà Tĩnh",
         "capacity_mwe": "1200"},
    ]
    annotated, _ = verify_tool(rows, reference_csv)
    assert annotated[0]["evidence_score"] == "3"
    assert "Vung Ang" in annotated[0]["verification_source"]


def test_uses_lp_not_naive_fuzzy(reference_csv):
    """Verify that the function uses reconcile(), not fuzzy_match_reference().

    With multiple system plants, LP global matching should produce different
    (better) results than greedy name-only matching.
    """
    rows = [
        {"name": "LNG Quảng Ninh", "fuel": "LNG", "province": "Quảng Ninh",
         "capacity_mwe": "1500"},
        {"name": "LNG Quảng Nam", "fuel": "LNG", "province": "Quảng Nam",
         "capacity_mwe": "1500"},
    ]
    annotated, summary = verify_tool(rows, reference_csv)

    # Both should match their correct counterpart
    sources = {r["name"]: r.get("verification_source", "") for r in annotated}
    assert "Quảng Ninh" in sources["LNG Quảng Ninh"]
    assert "Quảng Nam" in sources["LNG Quảng Nam"]
