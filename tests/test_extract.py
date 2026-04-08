"""Tests for the CSV/table extraction module."""

from aedist.extract import (
    _extract_pipe_table,
    map_header_to_canonical,
    norm_header,
)


class TestHeaderMapping:
    """Header variants that LLMs actually produce must map to canonical names."""

    def test_power_plant_name(self):
        assert map_header_to_canonical(norm_header("Power Plant Name")) == "name"

    def test_plantname_no_space(self):
        assert map_header_to_canonical(norm_header("PlantName")) == "name"

    def test_plant_name(self):
        assert map_header_to_canonical(norm_header("Plant Name")) == "name"

    def test_power_plant_no_name_suffix(self):
        """Gemini-2.5-flash-lite run3 used quoted 'Power Plant' header."""
        assert map_header_to_canonical(norm_header("Power Plant")) == "name"

    def test_project_header(self):
        """Some models use 'Project' as the name column header."""
        assert map_header_to_canonical(norm_header("Project")) == "name"

    def test_generation_capacity(self):
        assert map_header_to_canonical(norm_header("Generation Capacity (MWe)")) == "capacity_mwe"


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


class TestFallbackInlineCSV:
    """fallback_extract_inline_csv detects CSV-like regions in plain text."""

    def test_classic_name_header(self):
        from aedist.extract import fallback_extract_inline_csv

        text = "Here are the plants:\nName,Fuel,Province\nPha Lai,Coal,Hai Duong\n"
        result = fallback_extract_inline_csv(text)
        assert result is not None
        assert "Name,Fuel,Province" in result
        assert "Pha Lai" in result

    def test_project_header_detected(self):
        """PR #152: 'Project' keyword triggers header detection."""
        from aedist.extract import fallback_extract_inline_csv

        text = "Project,Fuel,Capacity\nSon My 1,Coal,150\nVung Ang 2,Coal,600\n"
        result = fallback_extract_inline_csv(text)
        assert result is not None
        assert "Project,Fuel,Capacity" in result

    def test_fuel_keyword_detected(self):
        from aedist.extract import fallback_extract_inline_csv

        text = "Some intro.\nFuel,Status,Province\nCoal,Operational,Quang Ninh\n"
        result = fallback_extract_inline_csv(text)
        assert result is not None
        assert "Fuel,Status,Province" in result

    def test_no_csv_returns_none(self):
        from aedist.extract import fallback_extract_inline_csv

        text = "This is just a paragraph about power plants in Vietnam."
        assert fallback_extract_inline_csv(text) is None

    def test_stops_at_double_blank(self):
        """CSV region ends at two consecutive blank lines."""
        from aedist.extract import fallback_extract_inline_csv

        text = "Name,Fuel,Status\nPha Lai,Coal,Operating\n\n\nUnrelated text here"
        result = fallback_extract_inline_csv(text)
        assert result is not None
        assert "Unrelated" not in result
