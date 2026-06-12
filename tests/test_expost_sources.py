"""Tests for aedist.expost.sources — ex post source handling (ticket 0292)."""

import json

from aedist.expost import (
    append_sources_section,
    parse_numbered_bibliography,
    render_mistral_content_with_sources,
    resolve_source_cells,
    strip_preamble,
)

BIB = """\
## Annotated Bibliography

1. **Global Energy Monitor**
   - *URL:* [https://globalenergymonitor.org/](https://globalenergymonitor.org/)
   - *Summary:* Tracker.

2. **EVN Annual Report**
   - *URL:* [https://en.evn.com.vn/report](https://en.evn.com.vn/report)

6. **Vietnam Investment Review**
   - *URL:* [https://www.vir.com.vn/](https://www.vir.com.vn/)
"""

TABLE = """\
# Inventory

| Plant name | Capacity (MWe) | Source 1 | Source 2 |
|---|---:|---|---|
| Vung Ang 1 | 1,200 | 1 | |
| Vung Ang 2 | 1,320 |6,76| 2 |
"""


class TestParseNumberedBibliography:
    def test_maps_numbers_to_urls(self):
        mapping = parse_numbered_bibliography(BIB)
        assert mapping == {
            1: "https://globalenergymonitor.org/",
            2: "https://en.evn.com.vn/report",
            6: "https://www.vir.com.vn/",
        }

    def test_url_on_entry_line(self):
        mapping = parse_numbered_bibliography("3. [GEM](https://gem.example/x)")
        assert mapping == {3: "https://gem.example/x"}

    def test_ignores_numbered_rows_inside_tables(self):
        text = "| n | name |\n|---|---|\n| 1 | https://nope.example/ |\n"
        assert parse_numbered_bibliography(text) == {}

    def test_entry_without_url_is_omitted(self):
        assert parse_numbered_bibliography("1. Title only, no link\n\n") == {}


class TestResolveSourceCells:
    def test_resolves_bare_numbers_to_hyperlinks(self):
        resolved, audit = resolve_source_cells(TABLE + "\n" + BIB)
        assert "[1](https://globalenergymonitor.org/)" in resolved
        assert "[2](https://en.evn.com.vn/report)" in resolved
        assert "[6](https://www.vir.com.vn/)" in resolved
        assert audit["n_resolved"] == 3

    def test_unresolved_reference_keeps_number_and_flags_audit(self):
        resolved, audit = resolve_source_cells(TABLE + "\n" + BIB)
        # 76 is not in the bibliography: kept bare, flagged in the audit trail.
        assert "[76](" not in resolved
        assert audit["unresolved"] == [76]
        assert audit["audit_status"] == "in_progress"
        assert audit["n_refs"] == 4

    def test_complete_when_all_resolve(self):
        text = TABLE.replace("|6,76|", "| 6 |") + "\n" + BIB
        _, audit = resolve_source_cells(text)
        assert audit["audit_status"] == "complete"
        assert audit["unresolved"] == []

    def test_no_bibliography_leaves_markdown_unchanged(self):
        resolved, audit = resolve_source_cells(TABLE)
        assert resolved == TABLE
        assert audit["audit_status"] == "no_bibliography"

    def test_non_source_columns_untouched(self):
        resolved, _ = resolve_source_cells(TABLE + "\n" + BIB)
        assert "| 1,200 |" in resolved  # capacity cell not rewritten


class TestStripPreamble:
    def test_drops_prose_before_first_heading(self):
        text = "Sure! Here is the inventory you asked for.\n\n# Inventory\n| a |\n"
        assert strip_preamble(text) == "# Inventory\n| a |\n"

    def test_drops_prose_before_first_table_row(self):
        text = "Preamble chatter.\n| Plant | Fuel |\n|---|---|\n"
        assert strip_preamble(text) == "| Plant | Fuel |\n|---|---|\n"

    def test_no_table_or_heading_returns_unchanged(self):
        text = "Just a refusal, sorry.\n"
        assert strip_preamble(text) == text

    def test_already_clean_is_identity(self):
        assert strip_preamble(TABLE) == TABLE

    def test_salvages_header_fused_onto_preamble_line(self):
        # Frozen raw records (arm3 claude-opus runs 3-5, arm1 run 4) carry the
        # table header glued onto the last preamble sentence with no newline.
        # The header row must survive the strip or the run becomes unparseable.
        text = "Let me conduct several targeted searches.| Plant | Fuel |\n|---|---|\n| A | Coal |\n"
        assert strip_preamble(text) == "| Plant | Fuel |\n|---|---|\n| A | Coal |\n"

    def test_mid_line_pipe_without_separator_is_still_preamble(self):
        # A '|' in running prose must not trigger salvage.
        text = "Caveat: data | may vary.\n\n| Plant | Fuel |\n|---|---|\n"
        assert strip_preamble(text) == "| Plant | Fuel |\n|---|---|\n"


class TestMistralRendering:
    def test_interleaves_tool_references_inline(self):
        content = [
            {"type": "text", "text": "| Plant | "},
            {"type": "tool_reference", "title": "GEM", "url": "https://gem.example/"},
            {"type": "text", "text": " |"},
        ]
        text, sources = render_mistral_content_with_sources(content)
        assert text == "| Plant | [GEM](https://gem.example/) |"
        assert sources == [("GEM", "https://gem.example/")]

    def test_append_sources_section_dedupes(self):
        out = append_sources_section(
            "body", [("A", "https://a.example/"), ("A", "https://a.example/")]
        )
        assert out.count("https://a.example/") == 1
        assert "## Sources" in out


class TestFlattenIntegration:
    """Single-turn extractor applies citation mapping + preamble strip + audit."""

    def _make_run(self, tmp_path):
        run_dir = tmp_path / "input" / "run01"
        run_dir.mkdir(parents=True)
        narrative = "Here is my report.\n\n" + TABLE + "\n" + BIB
        payload = {
            "outputs": [
                {"role": "assistant", "content": [{"type": "text", "text": narrative}]}
            ]
        }
        (run_dir / "mistral_probe.raw.json").write_text(json.dumps(payload))
        (run_dir / "mistral.json").write_text(json.dumps({"agent": "mistral", "run": 1}))
        return tmp_path / "input", tmp_path / "flat"

    def test_flat_md_has_links_and_audit_file(self, tmp_path):
        from aedist.extract_arm_single_turn import flatten_single_turn_arm

        input_dir, output_dir = self._make_run(tmp_path)
        flatten_single_turn_arm(input_dir, output_dir)

        md = (output_dir / "mistral_run01.md").read_text()
        assert md.startswith("# Inventory")  # preamble stripped
        assert "[6](https://www.vir.com.vn/)" in md  # citation mapped

        audit = json.loads((output_dir / "mistral_run01_source_audit.json").read_text())
        assert audit["audit_status"] == "in_progress"
        assert audit["unresolved"] == [76]

        meta = json.loads((output_dir / "mistral_run01.json").read_text())
        assert meta["n_sources_resolved"] == 3
        assert meta["n_sources_unresolved"] == 1
