"""Tests for the CSV/table extraction module."""

from aedist.extract import (
    _extract_pipe_table,
    _map_header_to_canonical,
    _norm_header,
)


class TestHeaderMapping:
    """Header variants that LLMs actually produce must map to canonical names."""

    def test_power_plant_name(self):
        assert _map_header_to_canonical(_norm_header("Power Plant Name")) == "name"

    def test_plantname_no_space(self):
        assert _map_header_to_canonical(_norm_header("PlantName")) == "name"

    def test_plant_name(self):
        assert _map_header_to_canonical(_norm_header("Plant Name")) == "name"

    def test_generation_capacity(self):
        assert _map_header_to_canonical(_norm_header("Generation Capacity (MWe)")) == "capacity_mwe"


class TestPipeTable:
    """Markdown pipe tables should be converted to CSV."""

    def test_basic_pipe_table(self):
        text = (
            "Here are some plants:\n\n"
            "| Name | Fuel | Province |\n"
            "| --- | --- | --- |\n"
            "| Pha Lai | Coal | Hai Duong |\n"
            "| Uong Bi | Coal | Quang Ninh |\n"
        )
        result = _extract_pipe_table(text)
        assert result is not None
        lines = result.strip().splitlines()
        assert len(lines) == 3  # header + 2 data rows
        assert '"Name"' in lines[0]

    def test_no_pipe_table(self):
        assert _extract_pipe_table("Just some text without tables.") is None

    def test_separator_row_excluded(self):
        text = "| A | B |\n| --- | --- |\n| 1 | 2 |\n"
        result = _extract_pipe_table(text)
        lines = result.strip().splitlines()
        assert not any("---" in ln for ln in lines)
