"""Tests for the CSV/table extraction module."""

import json

import pytest

from aedist.extract import (
    ExtractStatus,
    _extract_pipe_tables,
    _headers_compatible,
    _is_inventory_header,
    _merge_pipe_table_candidates,
    count_best_table_rows,
    extract_fenced_blocks,
    extract_one,
    main,
    map_header_to_canonical,
    merge_fragmented_tables,
    norm_header,
    parse_and_canonicalize,
    score_csv_like_block,
    sniff_dialect,
)

# Verify the newly imported names are actually used below to prevent ruff stripping:
# merge_fragmented_tables is used in TestMergeFragmentedTables
# _headers_compatible is used in TestMergeFragmentedTables.test_headers_compatible_*


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

    def test_total_mwe_header(self):
        assert map_header_to_canonical(norm_header("Total MWe")) == "capacity_mwe"

    def test_installed_capacity_header(self):
        assert map_header_to_canonical(norm_header("Installed Capacity (MWe)")) == "capacity_mwe"

    def test_fuel_source_header(self):
        assert map_header_to_canonical(norm_header("Fuel Source")) == "fuel"

    def test_cod_status_header(self):
        assert map_header_to_canonical(norm_header("COD / Status")) == "status"

    def test_conf_provenance_header(self):
        assert map_header_to_canonical(norm_header("Conf. & Provenance")) == "confidence"

    def test_orig_cap_header(self):
        assert map_header_to_canonical(norm_header("Orig. Cap (MW)")) == "capacity_mwe"

    def test_current_status_resolution_header(self):
        assert map_header_to_canonical(norm_header("Current Status / Resolution")) == "status"

    def test_asset_name_header(self):
        """SOTA arm4 qwen run02 labels the plant-name column 'Asset Name'."""
        assert map_header_to_canonical(norm_header("Asset Name")) == "name"

    def test_asset_name_vn_en_header(self):
        """SOTA arm2 anthropic run02 header: 'Asset Name (VN / EN)'."""
        assert map_header_to_canonical(norm_header("Asset Name (VN / EN)")) == "name"

    def test_asset_bare_header(self):
        """Arm2 anthropic run04/run05 use bare 'Asset (...)' name columns."""
        assert map_header_to_canonical(norm_header("Asset (Viet / Eng)")) == "name"
        assert map_header_to_canonical(norm_header("Asset (Vietnamese)")) == "name"

    def test_capacity_mw_header(self):
        """SOTA arm4 qwen run02 uses 'Capacity (MW)' for capacity."""
        assert map_header_to_canonical(norm_header("Capacity (MW)")) == "capacity_mwe"


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
        results = _extract_pipe_tables(text)
        assert len(results) == 1
        lines = results[0].strip().splitlines()
        assert len(lines) == 3  # header + 2 data rows
        assert '"Name"' in lines[0]

    def test_no_pipe_table(self):
        assert _extract_pipe_tables("Just some text without tables.") == []

    def test_separator_row_excluded(self):
        text = "| A | B |\n| --- | --- |\n| 1 | 2 |\n"
        results = _extract_pipe_tables(text)
        lines = results[0].strip().splitlines()
        assert not any("---" in ln for ln in lines)

    def test_multiple_pipe_tables_split(self):
        text = (
            "| Fuel | GW |\n| --- | --- |\n| Coal | 24 |\n| Gas | 7 |\n\n"
            "Some prose in between.\n\n"
            "| Name | Fuel | Province |\n| --- | --- | --- |\n"
            "| Pha Lai | Coal | Hai Duong |\n| Uong Bi | Coal | Quang Ninh |\n"
        )
        results = _extract_pipe_tables(text)
        assert len(results) == 2
        assert '"Name"' in results[1]

    def test_merge_split_subtables_with_same_header(self):
        text = (
            "| Name | Fuel | Province |\n| --- | --- | --- |\n"
            "| Pha Lai | Coal | Hai Duong |\n"
            "| Uong Bi | Coal | Quang Ninh |\n\n"
            "Some prose in between.\n\n"
            "| Name | Fuel | Province |\n| --- | --- | --- |\n"
            "| Vinh Tan 1 | Coal | Binh Thuan |\n"
            "| Nghi Son 2 | Coal | Thanh Hoa |\n"
        )
        tables = _extract_pipe_tables(text)
        merged = _merge_pipe_table_candidates(tables)
        assert merged is not None
        lines = merged.strip().splitlines()
        assert len(lines) == 5  # header + 4 rows
        assert '"Name","Fuel","Province"' == lines[0]

    def test_merge_ignores_statistical_tables(self):
        text = (
            "| Fuel | Capacity |\n| --- | --- |\n| Coal | 2910 |\n\n"
            "| Fuel | Capacity |\n| --- | --- |\n| Gas | 900 |\n"
        )
        tables = _extract_pipe_tables(text)
        merged = _merge_pipe_table_candidates(tables)
        assert merged is None


class TestInventoryHeaderDetection:
    def test_inventory_header_true(self):
        assert _is_inventory_header('"Name","Fuel","Province"') is True

    def test_statistical_header_false(self):
        assert _is_inventory_header('"Fuel","Capacity"') is False

    def test_inventory_header_variant_true(self):
        header = (
            '"Plant Name","Capacity (MW)","Owner / Operator",'
            '"Fuel Source","COD / Status","Conf. & Provenance"'
        )
        assert _is_inventory_header(header) is True

    def test_inventory_header_orig_cap_variant_true(self):
        header = (
            '"Plant Name","Orig. Cap (MW)","Original Sponsor",'
            '"Current Status / Resolution","Conf. & Provenance"'
        )
        assert _is_inventory_header(header) is True


class TestCountBestTableRows:
    def test_counts_single_table_rows(self):
        text = (
            "| Name | Fuel | Province |\n"
            "| --- | --- | --- |\n"
            "| Pha Lai | Coal | Hai Duong |\n"
            "| Uong Bi | Coal | Quang Ninh |\n"
        )
        assert count_best_table_rows(text) == 2

    def test_ignores_summary_table_when_inventory_table_present(self):
        text = (
            "# Report\n\n"
            "| Name | Fuel | Province | Capacity | Status | COD |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| Pha Lai | Coal | Hai Duong | 1040 | Operating | 1983 |\n"
            "| Uong Bi | Coal | Quang Ninh | 630 | Operating | 2002 |\n"
            "| Vinh Tan 1 | Coal | Binh Thuan | 1240 | Operating | 2018 |\n\n"
            "| Fuel | Capacity |\n"
            "| --- | --- |\n"
            "| Coal | 2910 |\n"
            "| Gas | 0 |\n"
        )
        assert count_best_table_rows(text) == 3

    def test_returns_zero_when_no_parseable_inventory_table_exists(self):
        text = "| Fuel | Capacity |\n| --- | --- |\n| Coal | 2910 |\n"
        assert count_best_table_rows(text) == 0

    def test_counts_rows_when_narrative_glued_to_header(self):
        """Arm3 (single-turn with docs) anthropic runs stream a reasoning
        preamble onto the same physical line as the table header, e.g.
        ``Let me search.| Name | Fuel |``. The glued prose must not add a
        phantom header cell that drops every data row as a count mismatch.
        """
        text = (
            "I need to research the current status of Vietnam's thermal "
            "projects. Let me conduct several targeted searches."
            "| Name | Fuel | Province | Capacity | Status | COD |\n"
            "|---|---|---|---|---|---|\n"
            "| Pha Lai | Coal | Hai Duong | 1040 | Operating | 1983 |\n"
            "| Uong Bi | Coal | Quang Ninh | 630 | Operating | 2002 |\n"
            "| Vinh Tan 1 | Coal | Binh Thuan | 1240 | Operating | 2018 |\n"
        )
        assert count_best_table_rows(text) == 3

    def test_merges_split_inventory_subtables_before_counting(self):
        text = (
            "| Name | Fuel | Province | Capacity | Status | COD |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| Pha Lai | Coal | Hai Duong | 1040 | Operating | 1983 |\n"
            "| Uong Bi | Coal | Quang Ninh | 630 | Operating | 2002 |\n\n"
            "| Name | Fuel | Province | Capacity | Status | COD |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| Vinh Tan 1 | Coal | Binh Thuan | 1240 | Operating | 2018 |\n"
            "| Nghi Son 2 | Coal | Thanh Hoa | 1320 | Operating | 2023 |\n"
        )
        assert count_best_table_rows(text) == 4

    def test_counts_asset_name_header_with_leading_index(self):
        """SOTA arm2 anthropic runs use an 'Asset Name (VN / EN)' name column
        preceded by a leading numeric '#' index column. The index column
        normalises to nothing (mapped to None) and must be tolerated; the
        plant-name column must still be recognised so rows are counted.
        """
        text = (
            "| # | Asset Name (VN / EN) | Province | Fuel | Units×MW | "
            "Total MWe | Status | COD / Expected | Owner / Operator | Confidence |\n"
            "|---|---|---|---|---|---|---|---|---|---|\n"
            "| 1 | Pha Lai 1 / Phả Lại 1 | Hai Duong | Coal | 4×110 | 440 | "
            "Operating | 1983 | EVN | HIGH |\n"
            "| 2 | Uong Bi MR | Quang Ninh | Coal | 1×300 | 300 | "
            "Operating | 2002 | EVN | MEDIUM |\n"
        )
        assert count_best_table_rows(text) == 2

    def test_counts_asset_name_capacity_mw_header(self):
        """SOTA arm4 qwen run02 header: 'Asset Name' + 'Capacity (MW)' columns."""
        text = (
            "| Asset Name | Fuel | Capacity (MW) | Status | Owner / Operator | "
            "COD / Target | As-Of / Status Note | Confidence | Source 1 | Source 2 |\n"
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
            "| Pha Lai 1 & 2 | Coal | 1040 | Operating | EVN GENCO 2 | "
            "2002 / 2007 | As-of 2018 AR | HIGH | evn_ar | https://evn.com.vn |\n"
            "| Quang Ninh 1 & 2 | Coal | 1200 | Operating | EVN GENCO 1 | "
            "2008 / 2010 | As-of 2018 AR | HIGH | evn_ar | https://evn.com.vn |\n"
        )
        assert count_best_table_rows(text) == 2

    def test_asset_inventory_wins_over_asset_recap_subtable(self):
        """With the asset->name mapping, a small 'Asset' recap table must not
        out-score the larger 'Asset' inventory table in the same response.
        Guards against the mapping being too loose for merge/selection.
        """
        text = (
            "| # | Asset | Province | Fuel | Total MWe | Status | COD |\n"
            "|---|---|---|---|---|---|---|\n"
            "| 1 | Pha Lai | Hai Duong | Coal | 440 | Operating | 1983 |\n"
            "| 2 | Uong Bi | Quang Ninh | Coal | 330 | Operating | 2011 |\n"
            "| 3 | Vinh Tan 1 | Binh Thuan | Coal | 1240 | Operating | 2018 |\n\n"
            "Planned pipeline summary:\n\n"
            "| # | Asset | Province | MW (planned) | Status |\n"
            "|---|---|---|---|---|\n"
            "| 1 | Future Plant | Quang Tri | 1320 | Planned |\n"
        )
        # The 3-row inventory table (more rows, more recognised columns) wins.
        assert count_best_table_rows(text) == 3


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

    def test_prose_with_keywords_not_captured(self):
        """A sentence mentioning keywords with only 1 comma is not a CSV header."""
        from aedist.extract import fallback_extract_inline_csv

        text = "The database tracks fuel, capacity for each plant.\n\nNo CSV here."
        assert fallback_extract_inline_csv(text) is None


# ---------------------------------------------------------------------------
# extract_fenced_blocks
# ---------------------------------------------------------------------------
class TestExtractFencedBlocks:
    def test_single_csv_block(self):
        text = "Here:\n```csv\nName,Fuel\nPha Lai,Coal\n```\nDone."
        blocks = extract_fenced_blocks(text)
        assert len(blocks) == 1
        assert "Pha Lai" in blocks[0]

    def test_multiple_blocks(self):
        text = "```\nA,B\n1,2\n```\ntext\n```csv\nC,D\n3,4\n```"
        blocks = extract_fenced_blocks(text)
        assert len(blocks) == 2

    def test_crlf_stripped(self):
        text = "```csv\r\nName,Fuel\r\nPha Lai,Coal\r\n```"
        blocks = extract_fenced_blocks(text)
        assert len(blocks) == 1
        assert "\r" not in blocks[0]

    def test_empty_block(self):
        text = "```\n\n```"
        blocks = extract_fenced_blocks(text)
        assert len(blocks) == 1
        assert blocks[0] == ""

    def test_case_insensitive(self):
        text = "```CSV\nName,Fuel\nPha Lai,Coal\n```"
        blocks = extract_fenced_blocks(text)
        assert len(blocks) == 1

    def test_no_blocks(self):
        assert extract_fenced_blocks("Just some text.") == []


# ---------------------------------------------------------------------------
# score_csv_like_block
# ---------------------------------------------------------------------------
class TestScoreCsvLikeBlock:
    def test_empty_block(self):
        assert score_csv_like_block("") == -1.0

    def test_pipe_table_rejected(self):
        """Blocks that look like pipe tables score -1."""
        assert score_csv_like_block("| A | B | C |\n| 1 | 2 | 3 |") == -1.0

    def test_csv_block_positive(self):
        block = "Name,Fuel,Status\nPha Lai,Coal,Operating\nUong Bi,Coal,Operating"
        assert score_csv_like_block(block) > 0

    def test_longer_block_scores_higher(self):
        short = "Name,Fuel\nPha Lai,Coal"
        long = "Name,Fuel\n" + "\n".join(f"Plant{i},Coal" for i in range(20))
        assert score_csv_like_block(long) > score_csv_like_block(short)

    def test_header_keywords_boost_score(self):
        with_kw = "Name,Fuel,Status\n1,2,3"
        no_kw = "X,Y,Z\n1,2,3"
        assert score_csv_like_block(with_kw) > score_csv_like_block(no_kw)


# ---------------------------------------------------------------------------
# sniff_dialect
# ---------------------------------------------------------------------------
class TestSniffDialect:
    def test_comma_delimited(self):
        d = sniff_dialect("Name,Fuel,Status\nPha Lai,Coal,Operating\n")
        assert d.delimiter == ","

    def test_semicolon_delimited(self):
        d = sniff_dialect("Name;Fuel;Status\nPha Lai;Coal;Operating\n")
        assert d.delimiter == ";"

    def test_tab_delimited(self):
        d = sniff_dialect("Name\tFuel\tStatus\nPha Lai\tCoal\tOperating\n")
        assert d.delimiter == "\t"

    def test_sep_hint_stripped(self):
        d = sniff_dialect("sep=;\nName;Fuel;Status\nPha Lai;Coal;Operating\n")
        assert d.delimiter == ";"

    def test_fallback_to_comma(self):
        """Unparseable input defaults to comma."""
        d = sniff_dialect("no delimiters here")
        assert d.delimiter == ","


# ---------------------------------------------------------------------------
# norm_header / _strip_diacritics
# ---------------------------------------------------------------------------
class TestNormHeaderDiacritics:
    """norm_header uses strip_diacritics from util.py (comprehensive tests in test_util.py)."""

    def test_norm_header_vietnamese(self):
        assert norm_header("Công suất (MWe)") == "cong_suat"

    def test_norm_header_accented(self):
        assert norm_header("Plántà Nàmé") == "planta_name"


# ---------------------------------------------------------------------------
# parse_and_canonicalize
# ---------------------------------------------------------------------------
class TestParseAndCanonicalize:
    def test_basic_csv(self):
        csv_text = (
            "Name,Fuel,Status,COD,Province,Capacity\nPha Lai,Coal,Operating,2001,Hai Duong,600"
        )
        result = parse_and_canonicalize(csv_text)
        assert "Pha Lai" in result
        assert "600.0" in result

    def test_missing_columns_filled(self):
        csv_text = "Name,Fuel\nPha Lai,Coal\n"
        result = parse_and_canonicalize(csv_text)
        lines = result.strip().splitlines()
        assert (
            lines[0]
            == "name,fuel,status,status_as_of,cod,province,capacity_mwe,confidence,source_1,source_2,note"
        )
        header = lines[0].split(",")
        row = lines[1].split(",")
        row_map = dict(zip(header, row, strict=False))
        assert row_map["name"] == "Pha Lai"
        assert row_map["status"] == ""  # status missing
        assert row_map["status_as_of"] == ""  # as-of missing
        assert row_map["confidence"] == ""  # confidence missing

    def test_capacity_normalized(self):
        csv_text = "Name,Capacity\nPha Lai,1200\n"
        result = parse_and_canonicalize(csv_text)
        assert "1200.0" in result

    def test_invalid_capacity_defaults_to_zero(self):
        csv_text = "Name,Capacity\nPha Lai,unknown\n"
        result = parse_and_canonicalize(csv_text)
        assert ",0," in result or result.endswith(",0\r\n") or ",0\n" in result

    def test_total_mwe_header_is_parsed(self):
        csv_text = "Name,Total MWe\nPha Lai,440\n"
        result = parse_and_canonicalize(csv_text)
        assert "440.0" in result

    def test_capacity_value_with_annotation_is_parsed(self):
        csv_text = 'Name,Total MWe\nVan Phong 1,"1,320 net"\n'
        result = parse_and_canonicalize(csv_text)
        assert "1320.0" in result

    def test_empty_csv_raises(self):
        with pytest.raises(ValueError, match="empty"):
            parse_and_canonicalize("Name,Fuel\n")

    def test_no_name_column_raises(self):
        with pytest.raises(ValueError, match="name"):
            parse_and_canonicalize("Foo,Bar\n1,2\n")

    def test_sep_hint_handled(self):
        csv_text = "sep=;\nName;Fuel;Status\nPha Lai;Coal;Operating\n"
        result = parse_and_canonicalize(csv_text)
        assert "Pha Lai" in result

    def test_empty_name_rows_skipped(self):
        csv_text = "Name,Fuel\nPha Lai,Coal\n,\n"
        result = parse_and_canonicalize(csv_text)
        lines = result.strip().splitlines()
        assert len(lines) == 2  # header + 1 data row

    def test_provenance_columns_preserved(self):
        """parse_and_canonicalize keeps source_1, source_2, note from sourced runs."""
        csv_text = (
            "name,fuel,status,cod,province,capacity_mwe,source_1,source_2,note\n"
            "Pha Lai,coal,operational,1983,Hai Duong,440,"
            '"Decision 1195/QD-TTg","EVN Annual Report 2017 p14","4x110MW Soviet-built"\n'
        )
        result = parse_and_canonicalize(csv_text)
        header = result.splitlines()[0]
        assert "source_1" in header, f"source_1 missing from header: {header}"
        assert "source_2" in header, f"source_2 missing from header: {header}"
        assert "note" in header, f"note missing from header: {header}"
        row = result.splitlines()[1]
        assert "Decision 1195/QD-TTg" in row
        assert "EVN Annual Report 2017 p14" in row
        assert "4x110MW Soviet-built" in row

    def test_provenance_columns_empty_when_absent(self):
        """CSVs without provenance columns get empty source_1/source_2/note."""
        csv_text = "Name,Fuel\nPha Lai,Coal\n"
        result = parse_and_canonicalize(csv_text)
        header = result.splitlines()[0]
        assert "source_1" in header
        row = result.splitlines()[1]
        fields = row.split(",")
        # source_1, source_2, note should be empty (last 3 fields)
        assert fields[-3] == ""  # source_1
        assert fields[-2] == ""  # source_2
        assert fields[-1].strip() == ""  # note


class TestAblationPromptColumns:
    """Columns from the ablation prompt (Name_VI, Name_EN, extra Source columns)."""

    def test_name_vi_maps_to_canonical_name(self):
        assert map_header_to_canonical(norm_header("Name_VI")) == "name"

    def test_name_en_maps_to_canonical_name(self):
        assert map_header_to_canonical(norm_header("Name_EN")) == "name"

    def test_name_vi_column_parsed_by_canonicalize(self):
        csv_text = "Name_VI,Name_EN,Fuel,Status\nPhả Lại,Pha Lai,Coal,Operational\n"
        result = parse_and_canonicalize(csv_text)
        assert "Phả Lại" in result

    def test_extra_columns_ignored_by_evaluator(self, tmp_path):
        """load_plants_csv silently ignores columns it doesn't map."""
        from aedist.evaluate import load_plants_csv

        csv_text = (
            "Name_VI,Fuel,Status,Province,Capacity_MWe,Source_1,Source_2\n"
            "Phả Lại,Coal,Operational,Hải Dương,600,Decision 123,EVN Report\n"
        )
        tmp = tmp_path / "ablation_test.csv"
        tmp.write_text(csv_text, encoding="utf-8")
        plants = load_plants_csv(tmp)
        assert len(plants) == 1
        assert plants[0].name == "Phả Lại"


class TestHeaderVariantsProvenance:
    """Header variant mappings for provenance columns."""

    def test_header_variant_source_maps_to_source_1(self):
        """'source' and 'reference' headers map to source_1."""
        assert map_header_to_canonical(norm_header("Source")) == "source_1"
        assert map_header_to_canonical(norm_header("Reference")) == "source_1"
        assert map_header_to_canonical(norm_header("Citation")) == "source_1"

    def test_header_variant_notes_maps_to_note(self):
        """'notes' and 'comment' headers map to note."""
        assert map_header_to_canonical(norm_header("Notes")) == "note"
        assert map_header_to_canonical(norm_header("Comment")) == "note"


class TestHeaderVariantsConfidenceTemporality:
    """Header variant mappings for confidence and as-of columns."""

    def test_header_variant_confidence_maps_to_confidence(self):
        assert map_header_to_canonical(norm_header("Confidence")) == "confidence"
        assert map_header_to_canonical(norm_header("Confidence level")) == "confidence"

    def test_header_variant_status_as_of_maps_to_status_as_of(self):
        assert map_header_to_canonical(norm_header("Status as-of-date")) == "status_as_of"
        assert map_header_to_canonical(norm_header("As-of date")) == "status_as_of"

    def test_status_as_of_and_confidence_preserved(self):
        csv_text = (
            "Name,Fuel,Status,Status as-of-date,COD,Province,Capacity,Confidence\n"
            "Pha Lai,Coal,Operating,2024 est.,1983,Hai Duong,440,HIGH\n"
        )
        result = parse_and_canonicalize(csv_text)
        header = result.splitlines()[0].split(",")
        row = result.splitlines()[1].split(",")
        row_map = dict(zip(header, row, strict=False))
        assert row_map["status_as_of"] == "2024 est."
        assert row_map["confidence"] == "HIGH"


# ---------------------------------------------------------------------------
# extract_one (integration)
# ---------------------------------------------------------------------------
class TestExtractOne:
    def test_writes_csv(self, tmp_path):
        json_data = {"response": "```csv\nName,Fuel\nPha Lai,Coal\n```"}
        jf = tmp_path / "model.json"
        jf.write_text(json.dumps(json_data))
        out = tmp_path / "out"
        out.mkdir()
        res = extract_one(jf, out, overwrite=False)
        assert res.status is ExtractStatus.WROTE
        assert (out / "model.csv").exists()

    def test_skip_existing(self, tmp_path):
        json_data = {"response": "```csv\nName,Fuel\nPha Lai,Coal\n```"}
        jf = tmp_path / "model.json"
        jf.write_text(json.dumps(json_data))
        out = tmp_path / "out"
        out.mkdir()
        (out / "model.csv").write_text("existing")
        res = extract_one(jf, out, overwrite=False)
        assert res.status is ExtractStatus.SKIPPED
        assert (out / "model.csv").read_text() == "existing"

    def test_overwrite(self, tmp_path):
        json_data = {"response": "```csv\nName,Fuel\nPha Lai,Coal\n```"}
        jf = tmp_path / "model.json"
        jf.write_text(json.dumps(json_data))
        out = tmp_path / "out"
        out.mkdir()
        (out / "model.csv").write_text("old")
        res = extract_one(jf, out, overwrite=True)
        assert res.status is ExtractStatus.WROTE
        assert "Pha Lai" in (out / "model.csv").read_text()

    def test_invalid_json(self, tmp_path):
        jf = tmp_path / "bad.json"
        jf.write_text("{broken")
        out = tmp_path / "out"
        out.mkdir()
        res = extract_one(jf, out, overwrite=False)
        assert res.status is ExtractStatus.FAILED

    def test_no_response(self, tmp_path):
        jf = tmp_path / "empty.json"
        jf.write_text(json.dumps({"model": "test"}))
        out = tmp_path / "out"
        out.mkdir()
        res = extract_one(jf, out, overwrite=False)
        assert res.status is ExtractStatus.FAILED

    def test_multiturn_format(self, tmp_path):
        json_data = {
            "turns": [
                {"role": "user", "content": "give me data"},
                {"role": "assistant", "content": "```csv\nName,Fuel\nPha Lai,Coal\n```"},
            ]
        }
        jf = tmp_path / "multi.json"
        jf.write_text(json.dumps(json_data))
        out = tmp_path / "out"
        out.mkdir()
        res = extract_one(jf, out, overwrite=False)
        assert res.status is ExtractStatus.WROTE

    def test_no_csv_found(self, tmp_path):
        jf = tmp_path / "nocsvs.json"
        jf.write_text(json.dumps({"response": "No tables here, sorry."}))
        out = tmp_path / "out"
        out.mkdir()
        res = extract_one(jf, out, overwrite=False)
        assert res.status is ExtractStatus.FAILED

    def test_extract_one_merges_split_subtables(self, tmp_path):
        response = (
            "| Name | Fuel | Province | Capacity | Status | COD |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| Pha Lai | Coal | Hai Duong | 1040 | Operating | 1983 |\n"
            "| Uong Bi | Coal | Quang Ninh | 630 | Operating | 2002 |\n\n"
            "Narrative break.\n\n"
            "| Name | Fuel | Province | Capacity | Status | COD |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| Vinh Tan 1 | Coal | Binh Thuan | 1240 | Operating | 2018 |\n"
            "| Nghi Son 2 | Coal | Thanh Hoa | 1320 | Operating | 2023 |\n"
        )
        jf = tmp_path / "split.json"
        jf.write_text(json.dumps({"response": response}), encoding="utf-8")
        out = tmp_path / "out"
        out.mkdir()
        res = extract_one(jf, out, overwrite=False)
        assert res.status is ExtractStatus.WROTE
        csv_out = (out / "split.csv").read_text(encoding="utf-8")
        # Header + 4 rows
        assert len([ln for ln in csv_out.splitlines() if ln.strip()]) == 5


class TestMainSkipsDerivedJson:
    def test_eval_json_ignored(self, tmp_path, monkeypatch):
        """main() must not attempt to extract .eval.json files."""
        inp = tmp_path / "inp"
        inp.mkdir()
        out = tmp_path / "out"
        out.mkdir()
        # Real model reply
        (inp / "model-run1.json").write_text(
            json.dumps({"response": "```csv\nName,Fuel\nPha Lai,Coal\n```"})
        )
        # Eval file that should be skipped
        (inp / "model-run1.eval.json").write_text(json.dumps({"f1": 0.5, "precision": 0.6}))
        main(["--input", str(inp), "--output", str(out)])
        # Only the model reply should produce a CSV
        assert (out / "model-run1.csv").exists()
        assert not (out / "model-run1.eval.csv").exists()

    def test_record_and_summary_json_ignored(self, tmp_path, monkeypatch):
        """main() skips .record.json, _summary.json, and other non-reply files."""
        inp = tmp_path / "inp"
        inp.mkdir()
        out = tmp_path / "out"
        out.mkdir()
        # Real model reply
        (inp / "model-run1.json").write_text(
            json.dumps({"response": "```csv\nName,Fuel\nPha Lai,Coal\n```"})
        )
        # Derived files that should be skipped (whitelist excludes these)
        (inp / "model-run1.record.json").write_text(json.dumps({"f1": 0.5}))
        (inp / "tavily_cache.json").write_text(json.dumps({}))
        (inp / "self_consistency_summary.json").write_text(json.dumps({}))
        monkeypatch.setattr("sys.argv", ["extract", "--input", str(inp), "--output", str(out)])
        main()
        assert (out / "model-run1.csv").exists()
        # None of the derived files should produce CSVs
        csv_files = list(out.glob("*.csv"))
        assert len(csv_files) == 1, f"Expected 1 CSV, got {[f.name for f in csv_files]}"


# ---------------------------------------------------------------------------
# merge_fragmented_tables — compatible-header merge (ticket 0279)
# ---------------------------------------------------------------------------
class TestMergeFragmentedTables:
    """merge_fragmented_tables merges inventory sub-tables with compatible but
    non-identical headers (fuel-split fragments) within a 50-line proximity window.

    The heuristic requires: same column count AND compatible headers (>=2 shared
    canonical names) AND proximity within 50 source lines.
    """

    def test_merges_three_compatible_tables_consecutive(self):
        """Three consecutive compatible tables (coal/gas/LNG split, same col count)
        are merged. Merged row count equals the sum of data rows across all three.

        Canonical test for the fragmented-table scenario described in ticket 0279:
        headers have the same number of columns but differ in one column label
        (e.g. coal table has "Technology" while gas table has "Owner").
        """
        text = (
            "**Coal plants:**\n\n"
            # 6-column header: Name Province Fuel Technology Total_MWe Status
            "| Name | Province | Fuel | Technology | Total MWe | Status |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| Pha Lai | Hai Duong | Coal | Subcritical | 440 | Operating |\n"
            "| Uong Bi | Quang Ninh | Coal | Subcritical | 630 | Operating |\n\n"
            "**Gas plants:**\n\n"
            # 6-column header: Name Province Fuel Owner Total_MWe Status
            "| Name | Province | Fuel | Owner | Total MWe | Status |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| Phu My 1 | Ba Ria-Vung Tau | Gas | EVN | 1090 | Operating |\n"
            "| Ca Mau 1 | Ca Mau | Gas | PetroVietnam | 750 | Operating |\n"
            "| Ca Mau 2 | Ca Mau | Gas | PetroVietnam | 750 | Operating |\n\n"
            "**LNG plants:**\n\n"
            # 6-column header: Name Province Fuel COD Total_MWe Status
            "| Name | Province | Fuel | COD | Total MWe | Status |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| Nhon Trach 3 | Dong Nai | LNG | 2026 | 750 | Construction |\n"
        )
        tables = _extract_pipe_tables(text)
        merged = merge_fragmented_tables(text, tables)
        assert merged is not None, "Expected compatible tables to be merged"
        lines = [ln for ln in merged.splitlines() if ln.strip()]
        # header + 6 data rows (2+3+1)
        assert len(lines) == 7, f"Expected 7 lines (header+6 rows), got {len(lines)}: {lines}"

    def test_merges_compatible_tables_with_prose_paragraph(self):
        """Compatible sub-tables (same col count, compatible headers) separated by
        ~10 prose lines are still merged (within the 50-line proximity window).
        """
        prose_block = "\n".join(
            [
                "",
                "The following gas-fired power plants are also part of the inventory.",
                "They were developed under BOT contracts with EVN.",
                "Capacity figures represent gross installed capacity in MWe.",
                "Status reflects commissioning as of the latest available data.",
                "Sources include GEM Global Gas Plant Tracker and EVN Annual Reports.",
                "Plants marked Planned have financial close pending.",
                "COD dates for planned plants are indicative estimates only.",
                "This section covers all gas plants above 30 MW nameplate capacity.",
                "LNG regasification terminal details are excluded from this table.",
                "",
            ]
        )
        text = (
            # 6-column coal table: Name Province Fuel Technology Total_MWe Status
            "| Name | Province | Fuel | Technology | Total MWe | Status |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| Pha Lai | Hai Duong | Coal | Subcritical | 440 | Operating |\n"
            "| Uong Bi | Quang Ninh | Coal | Subcritical | 630 | Operating |\n"
            + prose_block
            # 6-column gas table: Name Province Fuel Owner Total_MWe Status
            + "| Name | Province | Fuel | Owner | Total MWe | Status |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| Phu My 1 | Ba Ria-Vung Tau | Gas | EVN | 1090 | Operating |\n"
            "| Ca Mau 1 | Ca Mau | Gas | PetroVietnam | 750 | Operating |\n"
        )
        tables = _extract_pipe_tables(text)
        merged = merge_fragmented_tables(text, tables)
        assert merged is not None, "Tables within 50-line window should be merged"
        lines = [ln for ln in merged.splitlines() if ln.strip()]
        # header + 4 data rows
        assert len(lines) == 5, f"Expected 5 lines (header+4 rows), got {len(lines)}"

    def test_no_merge_for_unrelated_tables_different_column_counts(self):
        """Tables with different column counts are not merged even if headers share
        some keywords. A statistical recap table (2 cols) must not be fused with
        the inventory table (6 cols).
        """
        text = (
            "| Name | Province | Fuel | Total MWe | Status | COD |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| Pha Lai | Hai Duong | Coal | 440 | Operating | 1983 |\n"
            "| Uong Bi | Quang Ninh | Coal | 630 | Operating | 2002 |\n\n"
            "Summary by fuel:\n\n"
            "| Fuel | Total MWe |\n"
            "| --- | --- |\n"
            "| Coal | 1070 |\n"
            "| Gas | 900 |\n"
        )
        tables = _extract_pipe_tables(text)
        merged = merge_fragmented_tables(text, tables)
        # The summary table (2 cols) must not be merged with the inventory (6 cols).
        assert merged is None, "Unrelated tables with different column counts must not be merged"

    def test_headers_compatible_detects_shared_canonical_columns(self):
        """_headers_compatible returns True when two CSV header lines share >=2
        canonical column names even with different raw labels.
        """
        # Both have name, province, fuel, capacity_mwe, status in common (5 shared)
        h1 = '"Name","Province","Fuel","Technology","Total MWe","Status","COD"'
        h2 = '"Name","Province","Fuel","Owner","Total MWe","Status","COD"'
        assert _headers_compatible(h1, h2) is True

    def test_headers_incompatible_for_unrelated_tables(self):
        """_headers_compatible returns False when headers share fewer than 2
        canonical columns (e.g. only one canonical column in common).
        """
        # Only 'capacity_mwe' is shared canonical between these two
        h_inventory = '"Name","Province","Fuel","Total MWe","Status","COD"'
        h_other = '"Rank","Region","Total MWe"'
        assert _headers_compatible(h_inventory, h_other) is False
