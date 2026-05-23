"""Tests for extract_exp2_bib: bibliography quality metrics from Exp2 outputs."""

import csv
from pathlib import Path

import pytest

from aedist.extract_exp2_bib import (
    classify_source_tier,
    detect_citation_style,
    parse_md,
)

_NAIVE_DIR = Path("experiments/outputs/sota_exp2_naive_arm")
_OPTIMISED_DIR = Path("experiments/outputs/sota_exp2_brerun1")


class TestClassifySourceTier:
    """classify_source_tier maps references to primary/secondary/tertiary."""

    def test_evn_primary(self):
        assert classify_source_tier("EVN AR2023 p.44") == "primary"

    def test_moit_primary(self):
        assert classify_source_tier("MOIT Decision 500/QD-TTg") == "primary"

    def test_pvpower_primary(self):
        assert classify_source_tier("PV Power Annual Report 2023") == "primary"

    def test_gem_secondary(self):
        assert classify_source_tier("Global Energy Monitor GCPT") == "secondary"

    def test_kpmg_secondary(self):
        assert classify_source_tier("KPMG Vietnam Report") == "secondary"

    def test_wikipedia_tertiary(self):
        assert classify_source_tier("Wikipedia article on power") == "tertiary"

    def test_empty_tertiary(self):
        assert classify_source_tier("") == "tertiary"
        assert classify_source_tier("—") == "tertiary"

    def test_evn_domain(self):
        assert classify_source_tier("https://evn.com.vn/report") == "primary"

    def test_genco_primary(self):
        assert classify_source_tier("EVNGENCO3 Annual Report") == "primary"


class TestDetectCitationStyle:
    """detect_citation_style classifies source cells as key-ref or inline-ref."""

    def test_key_ref_bracket(self):
        cells = ["[B01]", "[B02]", "[B03]", "—", "[B01]", "[B04]"]
        assert detect_citation_style(cells) == "key-ref"

    def test_key_ref_bare(self):
        cells = ["S4", "S1", "S10", "S7", "—", "S4"]
        assert detect_citation_style(cells) == "key-ref"

    def test_key_ref_markdown_link(self):
        cells = ["[S01](https://evn.com.vn/report)", "[S02](https://example.com)"]
        assert detect_citation_style(cells) == "key-ref"

    def test_inline_ref(self):
        cells = ["EVN AR2023 p.44", "MOIT PSR2021", "GEM GCPT"]
        assert detect_citation_style(cells) == "inline-ref"

    def test_empty_cells(self):
        cells = ["", "—", "N/A"]
        assert detect_citation_style(cells) == "inline-ref"


class TestParseMd:
    """parse_md extracts bibliography quality metrics from markdown files."""

    def test_empty_file(self):
        """0-byte file produces n_rows=0 and citation_style='none'."""
        result = parse_md(_NAIVE_DIR / "mistral_run02.md")
        assert result["n_rows"] == 0
        assert result["citation_style"] == "none"

    def test_no_table_file(self):
        """File with no plant table (planning outline) produces n_rows=0."""
        result = parse_md(_NAIVE_DIR / "mistral_run03.md")
        assert result["n_rows"] == 0
        assert result["citation_style"] == "none"

    @pytest.mark.parametrize(
        "md_path",
        sorted(_NAIVE_DIR.glob("*.md")) + sorted(_OPTIMISED_DIR.glob("*.md")),
        ids=lambda p: f"{p.parent.name}/{p.name}",
    )
    def test_invariant_sum_equals_n_rows(self, md_path: Path):
        """src1_empty + src1_notfound + src1_present == n_rows (same for src2, notes)."""
        result = parse_md(md_path)
        n = result["n_rows"]
        for prefix in ("src1", "src2", "notes"):
            total = (
                result[f"{prefix}_empty"]
                + result[f"{prefix}_notfound"]
                + result[f"{prefix}_present"]
            )
            assert total == n, f"{md_path.name}: {prefix} sum={total} != n_rows={n}"

    def test_key_ref_run_has_valid_count(self):
        """A key-ref run should have src1_valid as int (not None)."""
        # anthropic_run02 optimised is reliably key-ref
        result = parse_md(_OPTIMISED_DIR / "anthropic_run02.md")
        assert result["citation_style"] == "key-ref"
        assert isinstance(result["src1_valid"], int)
        assert result["src1_valid"] >= 0

    def test_inline_ref_run_has_valid_none(self):
        """An inline-ref run should have src1_valid as None."""
        result = parse_md(_OPTIMISED_DIR / "qwen_run01.md")
        assert result["citation_style"] == "inline-ref"
        assert result["src1_valid"] is None

    def test_optimised_openai_has_bib(self):
        """OpenAI optimised runs have substantial bibliographies."""
        result = parse_md(_OPTIMISED_DIR / "openai_run01.md")
        assert result["bib_entries"] > 10

    def test_bib_valid_is_none_without_flag(self):
        """bib_valid is always None (only populated with --validate-urls)."""
        result = parse_md(_OPTIMISED_DIR / "openai_run01.md")
        assert result["bib_valid"] is None


@pytest.mark.integration
class TestBuildCsv:
    """Integration: build the full CSV and check row count."""

    def test_full_build(self, tmp_path: Path):
        from aedist.extract_exp2_bib import _FIELDS, build_bib_quality_csv

        rows = build_bib_quality_csv(_NAIVE_DIR, _OPTIMISED_DIR)
        assert len(rows) == 40  # 4 agents x 5 runs x 2 arms

        out = tmp_path / "test.csv"
        with out.open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=_FIELDS)
            writer.writeheader()
            writer.writerows(rows)

        with out.open() as fh:
            reader = list(csv.DictReader(fh))
            assert len(reader) == 40
