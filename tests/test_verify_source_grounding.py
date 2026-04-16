"""Tests for verify_source_grounding module."""

import textwrap

import pytest

from aedist.verify_source_grounding import (
    match_citation_to_corpus,
    plant_name_in_file,
    verify_source_grounding,
)

# ---------------------------------------------------------------------------
# Corpus filenames used in tests (subset of the real 18)
# ---------------------------------------------------------------------------

CORPUS_FILENAMES = [
    "EVN_Annual_Report_2010_2011_CapacitiesTable.md",
    "EVN_Annual_Report_2017_CapacitiesTable.md",
    "EVN_Annual_Report_2018_CapacitiesTable.md",
    "PDP7A_annex1_table1.md",
    "PDP7_annex1.md",
    "PDP7_annex2.md",
    "PDP8_annex2_table1.md",
    "PDP8_annex2_table2.md",
    "Report_32_annex1.md",
    "Report_58_annex.md",
    "Study_E542_table_9.1.md",
    "Study_E542_table_9.2.md",
]


# ---------------------------------------------------------------------------
# match_citation_to_corpus
# ---------------------------------------------------------------------------


class TestMatchCitationToCorpus:
    def test_source_file_found(self):
        """Citation mentioning PDP8 annex2 table1 matches the corpus file."""
        citation = "PDP8 Annex II Table 1 (NMNĐ Sơn Mỹ II 2250MW giai đoạn 2021-2030)"
        result = match_citation_to_corpus(citation, CORPUS_FILENAMES)
        assert result == "PDP8_annex2_table1.md"

    def test_evn_report_matches(self):
        """EVN Annual Report 2010-2011 p13 should match the EVN 2010_2011 file."""
        citation = "EVN Annual Report 2010-2011 p13"
        result = match_citation_to_corpus(citation, CORPUS_FILENAMES)
        assert result is not None
        assert "2010_2011" in result

    def test_report_32(self):
        """Report 32 Appendix 1 matches Report_32_annex1.md."""
        citation = "Report 32 Appendix 1 (NĐ Thái Bình I 2x300MW)"
        result = match_citation_to_corpus(citation, CORPUS_FILENAMES)
        assert result == "Report_32_annex1.md"

    def test_report_58(self):
        """Report 58 Appendix matches Report_58_annex.md."""
        citation = "Report 58 Appendix (NĐ Nghi Sơn 2 2x600MW chậm ~1 năm 2022)"
        result = match_citation_to_corpus(citation, CORPUS_FILENAMES)
        assert result == "Report_58_annex.md"

    def test_source_file_missing(self):
        """Citation mentioning a nonexistent document returns None."""
        citation = "World Bank Report 2023 on Vietnamese energy transition"
        result = match_citation_to_corpus(citation, CORPUS_FILENAMES)
        assert result is None

    def test_empty_citation(self):
        """Empty citation returns None without error."""
        assert match_citation_to_corpus("", CORPUS_FILENAMES) is None
        assert match_citation_to_corpus("  ", CORPUS_FILENAMES) is None

    def test_pdp7a_matches(self):
        """PDP7A Table 1 matches PDP7A_annex1_table1.md."""
        citation = "PDP7A Table 1 (NĐ Na Dương II 110MW listed 2019)"
        result = match_citation_to_corpus(citation, CORPUS_FILENAMES)
        assert result is not None
        assert "PDP7A" in result


# ---------------------------------------------------------------------------
# plant_name_in_file
# ---------------------------------------------------------------------------


class TestPlantNameInFile:
    def test_exact_match(self):
        """Plant name appears exactly in file content."""
        content = "| Duyên Hải 1 | 1245 MW | Trà Vinh |"
        assert plant_name_in_file("Duyen Hai 1", content) is True

    def test_no_match(self):
        """Plant name not in file content."""
        content = "| Phú Mỹ 1 | 1108 MW | Bà Rịa-Vũng Tàu |"
        assert plant_name_in_file("Duyen Hai 1", content) is False

    def test_diacritical_fuzzy(self):
        """Vietnamese diacriticals match via fuzzy partial ratio."""
        content = "NĐ Vĩnh Tân IV 2x600MW vận hành sớm 3 tháng 2017-2018"
        assert plant_name_in_file("Vinh Tan 4", content) is True

    def test_empty_name(self):
        """Empty plant name returns False."""
        assert plant_name_in_file("", "some content") is False

    def test_source_content_found(self):
        """File exists and contains plant name -> verified."""
        content = textwrap.dedent("""\
            ## Bảng 2: Danh mục các nhà máy nhiệt điện than
            | NĐ Duyên Hải III | 2x622MW | vận hành sớm 6 tháng 2016 |
            | NĐ Thái Bình I | 2x300MW | đã vận hành đúng tiến độ 2017 |
        """)
        assert plant_name_in_file("Duyen Hai 3", content) is True
        assert plant_name_in_file("Thai Binh 1", content) is True


# ---------------------------------------------------------------------------
# verify_source_grounding (integration with temp corpus)
# ---------------------------------------------------------------------------


@pytest.fixture()
def mini_corpus(tmp_path):
    """Create a minimal corpus directory with 2 files."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()

    (corpus / "PDP8_annex2_table1.md").write_text(
        "## Bảng 1: Danh mục các nhà máy nhiệt điện LNG\n"
        "| LNG Quảng Ninh | 1500 MW | 2021-2030 |\n"
        "| LNG Thái Bình | 1500 MW | 2021-2030 |\n"
        "| NMNĐ Nhơn Trạch 3 | 750 MW | 2021-2030 |\n",
        encoding="utf-8",
    )

    (corpus / "Report_32_annex1.md").write_text(
        "## Phụ lục 1\n"
        "| NĐ Thái Bình I | 2x300MW | đúng tiến độ 2017 |\n"
        "| NĐ Duyên Hải III | 2x622MW | sớm 6 tháng 2016 |\n",
        encoding="utf-8",
    )

    return corpus


class TestVerifySourceGrounding:
    def test_verified_plant(self, mini_corpus):
        """Plant with correct citation and name in file -> all True."""
        rows = [
            {
                "name": "Nhon Trach 3",
                "source_1": "PDP8 Annex II Table 1 (NMNĐ Nhơn Trạch 3 750MW)",
                "source_2": "",
            }
        ]
        annotated, summary = verify_source_grounding(rows, mini_corpus)
        assert annotated[0]["source_file_found"] == "True"
        assert annotated[0]["source_content_found"] == "True"
        assert annotated[0]["source_verified"] == "True"
        assert summary["traceability_rate"] == 1.0

    def test_file_found_but_plant_missing(self, mini_corpus):
        """Citation matches a file but plant name is not in that file."""
        rows = [
            {
                "name": "Vinh Tan 4",
                "source_1": "PDP8 Annex II Table 1 (something)",
                "source_2": "",
            }
        ]
        annotated, summary = verify_source_grounding(rows, mini_corpus)
        assert annotated[0]["source_file_found"] == "True"
        assert annotated[0]["source_content_found"] == "False"
        assert annotated[0]["source_verified"] == "False"

    def test_empty_source(self, mini_corpus):
        """Empty source_1 -> source_verified=False (not an error)."""
        rows = [
            {
                "name": "Some Plant",
                "source_1": "",
                "source_2": "",
            }
        ]
        annotated, summary = verify_source_grounding(rows, mini_corpus)
        assert annotated[0]["source_file_found"] == "False"
        assert annotated[0]["source_verified"] == "False"
        assert summary["source_rate"] == 0.0

    def test_no_source_columns(self, mini_corpus):
        """Rows without source_1/source_2 keys -> graceful degradation."""
        rows = [{"name": "Thai Binh 1"}]
        annotated, summary = verify_source_grounding(rows, mini_corpus)
        assert annotated[0]["source_verified"] == "False"
        assert summary["source_rate"] == 0.0

    def test_2x2_counts(self, mini_corpus):
        """Verify the 2x2 table counts are correct."""
        rows = [
            # Traceable AND in reference
            {
                "name": "Nhon Trach 3",
                "source_1": "PDP8 Annex II Table 1 (NMNĐ Nhơn Trạch 3 750MW)",
                "source_2": "",
            },
            # NOT traceable but in reference (file citation wrong)
            {
                "name": "Thai Binh 1",
                "source_1": "World Bank Report 2025",
                "source_2": "",
            },
            # NOT traceable and NOT in reference
            {
                "name": "Fictional Plant X",
                "source_1": "",
                "source_2": "",
            },
        ]
        annotated, summary = verify_source_grounding(rows, mini_corpus)
        c = summary["counts_2x2"]
        assert c["tt"] == 1  # Nhon Trach 3: traceable + in ref
        assert c["ft"] == 1  # Thai Binh 1: not traceable + in ref
        assert c["ff"] == 1  # Fictional: not traceable + not in ref

    def test_source_2_fallback(self, mini_corpus):
        """If source_1 doesn't match, try source_2."""
        rows = [
            {
                "name": "Thai Binh 1",
                "source_1": "Some unknown document",
                "source_2": "Report 32 Appendix 1 (NĐ Thái Bình I 2x300MW)",
            }
        ]
        annotated, summary = verify_source_grounding(rows, mini_corpus)
        assert annotated[0]["source_file_found"] == "True"
        assert annotated[0]["source_content_found"] == "True"
        assert annotated[0]["source_verified"] == "True"

    def test_summary_rates(self, mini_corpus):
        """Check aggregate rate calculations."""
        rows = [
            {
                "name": "Nhon Trach 3",
                "source_1": "PDP8 Annex II Table 1",
                "source_2": "",
            },
            {
                "name": "Missing Plant",
                "source_1": "",
                "source_2": "",
            },
        ]
        annotated, summary = verify_source_grounding(rows, mini_corpus)
        assert summary["total_plants"] == 2
        assert summary["source_rate"] == 0.5  # 1/2 has source
        assert summary["grounding_rate"] == 0.5  # 1/2 file found
