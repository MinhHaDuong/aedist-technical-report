"""Tests for source URL verification audit (scripts/audit_source_urls.py)."""

from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_CSV_HEADER = "name,fuel,status,cod,province,capacity_mwe,source_1,source_2,note"

_SOURCED_ROWS = (
    f"{_CSV_HEADER}\n"
    "Pha Lai,coal,operating,1983,Hai Duong,440,"
    '"Decision 1195/QD-TTg","EVN Annual Report 2017 p14","Soviet-built"\n'
    'Uong Bi,coal,operating,1964,Quang Ninh,105,"","",""\n'
    "Vinh Tan,coal,operating,2014,Binh Thuan,1200,"
    '"Wikipedia article on Vinh Tan thermal power plant complex","",""\n'
    "Mong Duong 2,coal,operating,2015,Quang Ninh,1120,"
    '"PDP7A capacity list","Decision 428/QD-BCT","BOT project"\n'
)


@pytest.fixture()
def sourced_csv(tmp_path):
    csv_path = tmp_path / "sourced.csv"
    csv_path.write_text(_SOURCED_ROWS)
    return csv_path


@pytest.fixture()
def gem_csv(tmp_path):
    gem_text = (
        "Name,Province,Fuel,Capacity,Status,Aggregated Units\n"
        "Pha Lai 1,Hai Duong,Coal,440.0,operating,Unit 1\n"
        "Vinh Tan 4,Binh Thuan,Coal,1200.0,operating,Unit 1\n"
        "Mong Duong 2,Quang Ninh,Coal,1120.0,operating,Unit 1\n"
    )
    csv_path = tmp_path / "gem_thermal.csv"
    csv_path.write_text(gem_text)
    return csv_path


# ---------------------------------------------------------------------------
# extract_and_stratify
# ---------------------------------------------------------------------------


class TestExtractAndStratify:
    """extract_and_stratify reads sourced CSV and groups by evidence tier."""

    def test_groups_by_score_tier(self, sourced_csv):
        from scripts.audit_source_urls import extract_and_stratify

        result = extract_and_stratify(sourced_csv)

        # Pha Lai: 2 primary sources -> score 4
        assert 4 in result
        assert any(r["name"] == "Pha Lai" for r in result[4])

        # Uong Bi: no sources -> score 1
        assert 1 in result
        assert any(r["name"] == "Uong Bi" for r in result[1])

        # Vinh Tan: 1 secondary source -> score 2
        assert 2 in result
        assert any(r["name"] == "Vinh Tan" for r in result[2])

    def test_mong_duong_primary_pair(self, sourced_csv):
        """PDP7A + Decision -> both primary -> tier 4."""
        from scripts.audit_source_urls import extract_and_stratify

        result = extract_and_stratify(sourced_csv)
        assert 4 in result
        assert any(r["name"] == "Mong Duong 2" for r in result[4])

    def test_all_rows_present(self, sourced_csv):
        """Every row from the CSV should appear in exactly one tier."""
        from scripts.audit_source_urls import extract_and_stratify

        result = extract_and_stratify(sourced_csv)
        total = sum(len(rows) for rows in result.values())
        assert total == 4

    def test_processes_all_three_runs(self, tmp_path):
        """When given multiple CSV paths, merges and deduplicates."""
        from scripts.audit_source_urls import extract_and_stratify

        for i in range(1, 4):
            path = tmp_path / f"run{i}.csv"
            path.write_text(_SOURCED_ROWS)

        paths = sorted(tmp_path.glob("run*.csv"))
        result = extract_and_stratify(paths)
        # With 3 identical runs, dedup by name -> still 4 unique plants
        total = sum(len(rows) for rows in result.values())
        assert total == 4


# ---------------------------------------------------------------------------
# select_sample
# ---------------------------------------------------------------------------


class TestSelectSample:
    """select_sample picks deterministic subset per tier."""

    def test_deterministic(self, sourced_csv):
        from scripts.audit_source_urls import extract_and_stratify, select_sample

        stratified = extract_and_stratify(sourced_csv)
        s1 = select_sample(stratified, n_per_tier=10)
        s2 = select_sample(stratified, n_per_tier=10)

        names1 = [r["name"] for r in s1]
        names2 = [r["name"] for r in s2]
        assert names1 == names2

    def test_has_evidence_tier_field(self, sourced_csv):
        from scripts.audit_source_urls import extract_and_stratify, select_sample

        stratified = extract_and_stratify(sourced_csv)
        sample = select_sample(stratified, n_per_tier=10)
        for row in sample:
            assert "evidence_tier" in row


# ---------------------------------------------------------------------------
# verify_url
# ---------------------------------------------------------------------------


class TestVerifyUrl:
    """verify_url extracts URLs from citation text and checks HTTP status."""

    def test_no_url_in_text(self):
        from scripts.audit_source_urls import verify_url

        result = verify_url("EVN Annual Report 2017 p14")
        assert result["has_url"] is False
        assert result["status_code"] is None

    def test_extracts_url(self):
        from scripts.audit_source_urls import verify_url

        result = verify_url("See https://example.com/page for details")
        assert result["has_url"] is True
        # status_code depends on network, but function should not crash


# ---------------------------------------------------------------------------
# build_calibration_table
# ---------------------------------------------------------------------------


class TestBuildCalibrationTable:
    """build_calibration_table aggregates per-tier verification rates."""

    def test_structure(self):
        from scripts.audit_source_urls import build_calibration_table

        audit_rows = [
            {
                "name": "A",
                "evidence_tier": 4,
                "has_url": True,
                "status_code": 200,
                "entity_found": True,
                "fabrication_suspect": False,
                "is_primary_pattern": True,
            },
            {
                "name": "B",
                "evidence_tier": 1,
                "has_url": False,
                "status_code": None,
                "entity_found": False,
                "fabrication_suspect": None,
                "is_primary_pattern": False,
            },
        ]
        table = build_calibration_table(audit_rows)
        assert 4 in table
        assert 1 in table
        assert table[4]["n_sampled"] == 1
        assert table[4]["url_resolve_rate"] == 1.0
        assert table[1]["n_sampled"] == 1
        assert table[1]["url_resolve_rate"] == 0.0


# ---------------------------------------------------------------------------
# cross_reference_gem
# ---------------------------------------------------------------------------


class TestCrossReferenceGem:
    """cross_reference_gem fuzzy-matches audited plants against GEM."""

    def test_match_found(self, gem_csv):
        from scripts.audit_source_urls import cross_reference_gem

        audit_rows = [{"name": "Mong Duong 2"}]
        result = cross_reference_gem(audit_rows, gem_csv)
        assert result[0]["gem_match"] == "Mong Duong 2"
        assert result[0]["gem_agrees"] is True

    def test_no_match(self, gem_csv):
        from scripts.audit_source_urls import cross_reference_gem

        audit_rows = [{"name": "Nonexistent Plant XYZ"}]
        result = cross_reference_gem(audit_rows, gem_csv)
        assert result[0]["gem_match"] is None


# ---------------------------------------------------------------------------
# CLI dry-run
# ---------------------------------------------------------------------------


class TestCLIDryRun:
    """CLI --dry-run completes without network calls."""

    def test_dry_run(self, sourced_csv, gem_csv, tmp_path):
        from scripts.audit_source_urls import main

        output_dir = tmp_path / "audit_out"
        main(
            [
                "--input",
                str(sourced_csv),
                "--gem",
                str(gem_csv),
                "--output-dir",
                str(output_dir),
                "--dry-run",
            ]
        )
        # Dry-run should create the calibration table (from stratification only)
        assert (output_dir / "calibration_table.json").exists()


# ---------------------------------------------------------------------------
# Disambiguation of ambiguous identifiers (DEC PDP-7 scenario)
# ---------------------------------------------------------------------------


class TestSearchQueryDisambiguation:
    """Verify that PDP7/PDP8 searches include Vietnam context.

    Without disambiguation, searching for "PDP7" returns results about the
    DEC PDP-7 minicomputer rather than Vietnam's Power Development Plan 7.
    """

    def test_extract_citation_key_disambiguates_pdp(self):
        """_extract_citation_key prepends Vietnam context for PDP identifiers."""
        from scripts.audit_source_urls import _extract_citation_key

        key = _extract_citation_key("PDP7A capacity list")
        assert "Vietnam" in key
        assert "PDP7" in key

    def test_extract_citation_key_disambiguates_qh(self):
        """_extract_citation_key prepends Vietnam context for QH identifiers."""
        from scripts.audit_source_urls import _extract_citation_key

        key = _extract_citation_key("QH8 approved plan")
        assert "Vietnam" in key
        assert "QH8" in key

    def test_extract_citation_key_no_change_for_decisions(self):
        """Decision identifiers are already specific enough."""
        from scripts.audit_source_urls import _extract_citation_key

        key = _extract_citation_key("Decision 1195/QD-TTg")
        assert key == "Decision 1195/QD-TTg"
        assert "Vietnam" not in key

    def test_fabrication_check_irrelevant_results(self):
        """Mocked Tavily returning DEC PDP-7 content flags fabrication suspect.

        Even with disambiguation, if search results contain only irrelevant
        content (DEC minicomputers), the identifier should not be confirmed.
        """
        from scripts.audit_source_urls import check_fabrication

        dec_pdp7_results = [
            {
                "title": "PDP-7 - Wikipedia",
                "url": "https://en.wikipedia.org/wiki/PDP-7",
                "content": (
                    "The PDP-7 is a minicomputer produced by Digital Equipment "
                    "Corporation as part of the PDP series. The first PDP-7 was "
                    "produced in 1964."
                ),
            },
            {
                "title": "PDP-7 - Computer History Museum",
                "url": "https://computerhistory.org/pdp7",
                "content": (
                    "The DEC PDP-7 was an 18-bit minicomputer. Ken Thompson "
                    "wrote the first version of Unix on a PDP-7."
                ),
            },
        ]

        with patch("aedist.query_livesearch.tavily_search", return_value=dec_pdp7_results):
            result = check_fabrication("PDP7A capacity list", tavily_key="fake-key")

        assert result["is_primary_pattern"] is True
        assert result["identifier"] is not None
        # The identifier "PDP7A" should not be found in DEC PDP-7 content
        assert result["fabrication_suspect"] is True
