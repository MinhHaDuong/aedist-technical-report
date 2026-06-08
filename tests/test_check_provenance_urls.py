"""Tests for check_provenance_urls.py — HTTP calls are always mocked."""

from unittest.mock import MagicMock, patch

import pytest

from aedist.check_provenance_urls import (
    _capacity_matches,
    _name_found,
    _parse_bibliography,
    _parse_capacity,
    _parse_table,
    _resolve_source_url,
    check_row,
    main,
    spot_check_run,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_PLANT_TABLE = """\
| Name (Vietnamese) | Name (English) | Province | Fuel | Technology | Units × MW | Total MWe | Status | Status as-of-date | COD | Owner/Developer | Confidence | Source 1 | Source 2 | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Nhiệt điện Phả Lại 1 | Pha Lai 1 | Hải Dương | Coal | Subcritical | 4 × 110 | 440 | Operating | 2023-06 | 1983 | EVN | MEDIUM | [1] | [3] | Soviet-era plant. |
| Nhiệt điện Uông Bí | Uong Bi TPP | Quảng Ninh | Coal | Subcritical | 1 × 300 | 300 | Operating | 2023-06 | 2014 | EVN | LOW | not found | — | Lead: Wikipedia. |
| Nhiệt điện Mông Dương 2 | Mong Duong 2 | Quảng Ninh | Coal | Subcritical | 2 × 620 | 1,240 | Operating | 2023-09 | 2015 | AES Corp | MEDIUM | [2] | — | BOT. |
| NĐ BOT Vân Phong 1 | Van Phong 1 | Khánh Hòa | Coal | Supercritical | 2 × 660 | 1,320 | Operating | 2025-05 | 2024 | Sumitomo Corp | HIGH | [99] | — | No bib entry. |
"""

_BIB_SECTION = """\
## Bibliography

**[1]** Green Finance DC. "PDP8." June 2023. URL: `https://greenfdc.org/pdp8/`. — *Drawn on for coal.*

**[2]** GEM. "Mong Duong 2." URL: `https://gem.wiki/mong_duong_2`. — *BOT details.*

**[3]** Baker McKenzie. "Analysis." December 2022. URL: `https://example.com/analysis`. — *Draft PDP8 analysis.*
"""

_FULL_MD = _PLANT_TABLE + "\n" + _BIB_SECTION


# ---------------------------------------------------------------------------
# _parse_bibliography
# ---------------------------------------------------------------------------


class TestParseBibliography:
    def test_extracts_urls(self):
        bib = _parse_bibliography(_FULL_MD)
        assert bib["1"] == "https://greenfdc.org/pdp8/"
        assert bib["2"] == "https://gem.wiki/mong_duong_2"
        assert bib["3"] == "https://example.com/analysis"

    def test_empty_if_no_bib_section(self):
        bib = _parse_bibliography(_PLANT_TABLE)
        assert bib == {}

    def test_entry_without_url_excluded(self):
        text = (
            "## Bibliography\n\n"
            "**[10]** Decision 500/QĐ-TTg. *PDP8*. — *No URL.*\n"
        )
        bib = _parse_bibliography(text)
        assert "10" not in bib


# ---------------------------------------------------------------------------
# _parse_table
# ---------------------------------------------------------------------------


class TestParseTable:
    def test_finds_header_and_rows(self):
        header, rows = _parse_table(_FULL_MD)
        assert "Source 1" in header
        assert len(rows) == 4

    def test_empty_on_no_table(self):
        header, rows = _parse_table("## Just text\nNo table here.")
        assert header == []
        assert rows == []


# ---------------------------------------------------------------------------
# _resolve_source_url
# ---------------------------------------------------------------------------


class TestResolveSourceUrl:
    def test_citation_key_resolves(self):
        bib = {"1": "https://greenfdc.org/pdp8/", "2": "https://gem.wiki/x"}
        assert _resolve_source_url("[1]", bib) == "https://greenfdc.org/pdp8/"

    def test_citation_key_missing_from_bib(self):
        bib = {"1": "https://greenfdc.org/pdp8/"}
        assert _resolve_source_url("[99]", bib) is None

    def test_inline_url(self):
        bib: dict = {}
        url = _resolve_source_url("See https://example.com/report", bib)
        assert url == "https://example.com/report"

    def test_notfound_returns_none(self):
        assert _resolve_source_url("not found", {}) is None

    def test_empty_returns_none(self):
        assert _resolve_source_url("", {}) is None

    def test_dash_returns_none(self):
        assert _resolve_source_url("—", {}) is None


# ---------------------------------------------------------------------------
# _name_found
# ---------------------------------------------------------------------------


class TestNameFound:
    def test_vi_name_match(self):
        assert _name_found("Nhiệt điện Phả Lại 1 is a coal plant", "Nhiệt điện Phả Lại 1", "")

    def test_en_name_match(self):
        assert _name_found("The Pha Lai power station", "", "Pha Lai")

    def test_case_insensitive(self):
        # Use ASCII English for case-insensitivity test — Vietnamese diacritics
        # do not round-trip through str.lower() in all locales.
        assert _name_found("PHU MY POWER CENTER", "", "Phu My")

    def test_not_found(self):
        assert not _name_found("Completely unrelated content", "Phả Lại", "Pha Lai")


# ---------------------------------------------------------------------------
# _capacity_matches
# ---------------------------------------------------------------------------


class TestCapacityMatches:
    def test_exact_mw(self):
        assert _capacity_matches("Total capacity: 440 MW", 440.0)

    def test_within_tolerance(self):
        assert _capacity_matches("1,200 MW installed", 1200.0)
        # 10% below
        assert _capacity_matches("1,080 MW", 1200.0)
        # 10% above
        assert _capacity_matches("1,320 MW", 1200.0)

    def test_outside_tolerance(self):
        assert not _capacity_matches("500 MW", 1200.0)

    def test_gw_conversion(self):
        # 1.2 GW = 1200 MWe claimed
        assert _capacity_matches("1.2 GW plant", 1200.0)

    def test_no_capacity_on_page(self):
        assert not _capacity_matches("No numbers here", 440.0)


# ---------------------------------------------------------------------------
# _parse_capacity
# ---------------------------------------------------------------------------


class TestParseCapacity:
    def test_plain_number(self):
        assert _parse_capacity("440") == 440.0

    def test_comma_thousands(self):
        assert _parse_capacity("1,240") == 1240.0

    def test_tilde_prefix(self):
        assert _parse_capacity("~600") == 600.0

    def test_invalid(self):
        assert _parse_capacity("unknown") is None


# ---------------------------------------------------------------------------
# check_row — with mocked HTTP
# ---------------------------------------------------------------------------


class TestCheckRow:
    def test_no_source(self):
        r = check_row("Nhà máy A", "Plant A", 440.0, "not found", {})
        assert r["verdict"] == "NO_SOURCE"

    def test_no_url(self):
        r = check_row("Nhà máy A", "Plant A", 440.0, "Decision 500/QD-TTg", {})
        assert r["verdict"] == "NO_URL"

    def test_citation_key_missing_from_bib(self):
        r = check_row("Nhà máy A", "Plant A", 440.0, "[99]", {})
        assert r["verdict"] == "NO_URL"

    def test_dry_run(self):
        bib = {"1": "https://example.com"}
        r = check_row("Nhà máy A", "Plant A", 440.0, "[1]", bib, dry_run=True)
        assert r["verdict"] == "DRY_RUN"
        assert "https://example.com" in r["detail"]

    def test_resolved_name_and_capacity_pass(self):
        bib = {"1": "https://greenfdc.org/pdp8/"}
        page_body = "Pha Lai 1 power station, capacity 440 MW, coal."
        mock_resp = MagicMock()
        mock_resp.text = page_body
        mock_resp.status_code = 200
        with patch("aedist.check_provenance_urls.httpx.get", return_value=mock_resp):
            r = check_row("Phả Lại 1", "Pha Lai 1", 440.0, "[1]", bib)
        assert r["verdict"] == "PASS"
        assert r["name_found"] == "yes"
        assert r["capacity_match"] == "yes"

    def test_resolved_name_not_found_fail(self):
        bib = {"1": "https://greenfdc.org/pdp8/"}
        page_body = "This page is about solar energy in Germany."
        mock_resp = MagicMock()
        mock_resp.text = page_body
        mock_resp.status_code = 200
        with patch("aedist.check_provenance_urls.httpx.get", return_value=mock_resp):
            r = check_row("Phả Lại 1", "Pha Lai 1", 440.0, "[1]", bib)
        assert r["verdict"] == "FAIL"
        assert r["name_found"] == "no"

    def test_http_404_unresolved(self):
        bib = {"1": "https://greenfdc.org/pdp8/"}
        mock_resp = MagicMock()
        mock_resp.text = ""
        mock_resp.status_code = 404
        with patch("aedist.check_provenance_urls.httpx.get", return_value=mock_resp):
            r = check_row("Phả Lại 1", "Pha Lai 1", 440.0, "[1]", bib)
        assert r["verdict"] == "UNRESOLVED"

    def test_network_error_unresolved(self):
        import httpx as _httpx

        bib = {"1": "https://greenfdc.org/pdp8/"}
        with patch(
            "aedist.check_provenance_urls.httpx.get", side_effect=_httpx.ConnectError("")
        ):
            r = check_row("Phả Lại 1", "Pha Lai 1", 440.0, "[1]", bib)
        assert r["verdict"] == "UNRESOLVED"

    def test_resolved_name_found_no_capacity(self):
        """Pass when name found and claimed_mwe is None (no capacity to check)."""
        bib = {"1": "https://example.com/report"}
        page_body = "Pha Lai 1 plant history."
        mock_resp = MagicMock()
        mock_resp.text = page_body
        mock_resp.status_code = 200
        with patch("aedist.check_provenance_urls.httpx.get", return_value=mock_resp):
            r = check_row("Phả Lại 1", "Pha Lai 1", None, "[1]", bib)
        assert r["verdict"] == "PASS"
        assert r["capacity_match"] == "n/a"

    def test_name_found_capacity_fails(self):
        """FAIL when name is on page but no capacity figure matches ±10%."""
        bib = {"1": "https://example.com/report"}
        page_body = "Pha Lai 1 capacity 50 MW (old units)."
        mock_resp = MagicMock()
        mock_resp.text = page_body
        mock_resp.status_code = 200
        with patch("aedist.check_provenance_urls.httpx.get", return_value=mock_resp):
            r = check_row("Phả Lại 1", "Pha Lai 1", 440.0, "[1]", bib)
        assert r["verdict"] == "FAIL"
        assert r["capacity_match"] == "no"


# ---------------------------------------------------------------------------
# spot_check_run — dry_run (no HTTP)
# ---------------------------------------------------------------------------


class TestSpotCheckRun:
    def test_dry_run_on_fixture(self, tmp_path):
        md_file = tmp_path / "run.md"
        md_file.write_text(_FULL_MD, encoding="utf-8")
        result = spot_check_run(md_file, n=3, seed=0, dry_run=True)
        assert result["n_sampled"] >= 1
        # Rows with resolvable URLs → DRY_RUN; rows with missing bib key ([99]) → NO_URL
        assert all(r["verdict"] in {"DRY_RUN", "NO_URL"} for r in result["rows"])
        # No PASS in dry-run
        assert result["n_pass"] == 0

    def test_empty_on_missing_table(self, tmp_path):
        md_file = tmp_path / "empty.md"
        md_file.write_text("## No table here\n", encoding="utf-8")
        result = spot_check_run(md_file)
        assert result["n_sampled"] == 0
        assert result["provenance_score"] is None

    def test_skips_notfound_rows(self, tmp_path):
        """Rows with 'not found' as Source 1 should not appear in the sample."""
        # Only 1 citeable row (Phả Lại 1, [1]); Uong Bi and Van Phong 1 have issues
        md_file = tmp_path / "run.md"
        md_file.write_text(_FULL_MD, encoding="utf-8")
        result = spot_check_run(md_file, n=10, seed=0, dry_run=True)
        # The "not found" row (Uong Bi) should not be in sampled plants
        sampled = result["sampled_plants"]
        assert "Uong Bi TPP" not in sampled

    def test_n_capped_at_candidates(self, tmp_path):
        """When n > number of citeable rows, sample all citeable rows."""
        md_file = tmp_path / "run.md"
        md_file.write_text(_FULL_MD, encoding="utf-8")
        result = spot_check_run(md_file, n=100, seed=0, dry_run=True)
        # _FULL_MD has 3 rows with non-empty, non-notfound Source 1
        # ([1], [2], [99]) but [99] has no bib entry → still included as candidate
        assert result["n_sampled"] == result["n_candidates"]

    def test_output_csv(self, tmp_path):
        md_file = tmp_path / "run.md"
        md_file.write_text(_FULL_MD, encoding="utf-8")
        out_csv = tmp_path / "out.csv"
        main(
            [
                "--md",
                str(md_file),
                "--output",
                str(out_csv),
                "--n",
                "2",
                "--dry-run",
            ]
        )
        assert out_csv.exists()
        text = out_csv.read_text(encoding="utf-8")
        assert "verdict" in text
        assert "DRY_RUN" in text

    def test_json_output(self, tmp_path):
        import json as _json

        md_file = tmp_path / "run.md"
        md_file.write_text(_FULL_MD, encoding="utf-8")
        out_json = tmp_path / "out.json"
        main(
            [
                "--md",
                str(md_file),
                "--json-output",
                str(out_json),
                "--n",
                "2",
                "--dry-run",
            ]
        )
        assert out_json.exists()
        data = _json.loads(out_json.read_text())
        assert "provenance_score" in data
        assert "rows" in data

    def test_main_missing_md_exits(self, tmp_path):
        with pytest.raises(SystemExit):
            main(["--md", str(tmp_path / "nonexistent.md")])
