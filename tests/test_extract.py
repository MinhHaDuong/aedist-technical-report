"""Tests for the CSV/table extraction module."""

import json

import pytest

from aedist.extract import (
    ExtractStatus,
    _extract_pipe_tables,
    extract_fenced_blocks,
    extract_one,
    main,
    map_header_to_canonical,
    norm_header,
    parse_and_canonicalize,
    score_csv_like_block,
    sniff_dialect,
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
        csv_text = "Name,Fuel,Status,COD,Province,Capacity\nPha Lai,Coal,Operating,2001,Hai Duong,600"
        result = parse_and_canonicalize(csv_text)
        assert "Pha Lai" in result
        assert "600.0" in result

    def test_missing_columns_filled(self):
        csv_text = "Name,Fuel\nPha Lai,Coal\n"
        result = parse_and_canonicalize(csv_text)
        lines = result.strip().splitlines()
        assert lines[0] == "name,fuel,status,cod,province,capacity_mwe"
        row = lines[1].split(",")
        assert row[0] == "Pha Lai"
        assert row[2] == ""  # status missing

    def test_capacity_normalized(self):
        csv_text = "Name,Capacity\nPha Lai,1200\n"
        result = parse_and_canonicalize(csv_text)
        assert "1200.0" in result

    def test_invalid_capacity_defaults_to_zero(self):
        csv_text = "Name,Capacity\nPha Lai,unknown\n"
        result = parse_and_canonicalize(csv_text)
        assert ",0," in result or result.endswith(",0\r\n") or ",0\n" in result

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


class TestMainSkipsEvalJson:
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
        (inp / "model-run1.eval.json").write_text(
            json.dumps({"f1": 0.5, "precision": 0.6})
        )
        monkeypatch.setattr("sys.argv", ["extract", "--input", str(inp), "--output", str(out)])
        main()
        # Only the model reply should produce a CSV
        assert (out / "model-run1.csv").exists()
        assert not (out / "model-run1.eval.csv").exists()
