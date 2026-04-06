"""Tests for aedist.query_decomposed — CSV merging and extraction."""

from aedist.query_decomposed import _extract_csv_text, _merge_csvs

# --- _merge_csvs ---


def test_merge_csvs_deduplicates_by_name():
    csv1 = "name,fuel,status,cod,province,capacity_mwe\nPha Lai,coal,operational,,Hai Duong,600\n"
    csv2 = "name,fuel,status,cod,province,capacity_mwe\nPha Lai,coal,operational,,Hai Duong,600\nVung Ang,coal,planned,,Ha Tinh,1200\n"
    merged = _merge_csvs([csv1, csv2])
    lines = merged.strip().split("\n")
    assert len(lines) == 3  # header + 2 unique plants


def test_merge_csvs_case_insensitive_dedup():
    csv1 = "name,fuel,status,cod,province,capacity_mwe\nPHA LAI,coal,,,Hai Duong,600\n"
    csv2 = "name,fuel,status,cod,province,capacity_mwe\npha lai,coal,,,Hai Duong,600\n"
    merged = _merge_csvs([csv1, csv2])
    lines = merged.strip().split("\n")
    assert len(lines) == 2  # header + 1 plant (deduped)


def test_merge_csvs_preserves_header():
    csv1 = "name,fuel,status,cod,province,capacity_mwe\nPlant A,coal,,,Hanoi,100\n"
    merged = _merge_csvs([csv1])
    assert merged.startswith("name,fuel,status,cod,province,capacity_mwe")


def test_merge_csvs_empty_input():
    assert _merge_csvs([]) == ""


def test_merge_csvs_skips_empty_names():
    csv1 = (
        "name,fuel,status,cod,province,capacity_mwe\n,coal,,,Hanoi,100\nPlant B,gas,,,HCMC,200\n"
    )
    merged = _merge_csvs([csv1])
    lines = merged.strip().split("\n")
    assert len(lines) == 2  # header + Plant B only


def test_merge_csvs_multiple_fuels():
    coal = "name,fuel,status,cod,province,capacity_mwe\nPlant A,coal,,,Hanoi,100\nPlant B,coal,,,HCMC,200\n"
    gas = "name,fuel,status,cod,province,capacity_mwe\nPlant C,gas,,,Da Nang,300\n"
    other = "name,fuel,status,cod,province,capacity_mwe\nPlant D,oil,,,Hue,50\n"
    merged = _merge_csvs([coal, gas, other])
    lines = merged.strip().split("\n")
    assert len(lines) == 5  # header + 4 plants


# --- _extract_csv_text ---


def test_extract_csv_text_fenced_block():
    response = "Here are the plants:\n\n```csv\nname,fuel,status,cod,province,capacity_mwe\nPha Lai,coal,operational,,Hai Duong,600\n```\n"
    result = _extract_csv_text(response)
    assert result is not None
    assert "Pha Lai" in result


def test_extract_csv_text_no_csv():
    result = _extract_csv_text("I don't have that information.")
    assert result is None


def test_extract_csv_text_inline_csv():
    response = "Results:\nname,fuel,status,cod,province,capacity_mwe\nVung Ang,coal,planned,,Ha Tinh,1200\n\nEnd of data."
    result = _extract_csv_text(response)
    assert result is not None
    assert "Vung Ang" in result
