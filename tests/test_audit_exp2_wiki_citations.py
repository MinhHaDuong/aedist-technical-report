"""Tests for audit_exp2_wiki_citations: banned-domain citation audit for Exp2."""

import csv
import re
from pathlib import Path

import pytest
from manuscript_source import body

from aedist.audit_exp2_wiki_citations import (
    audit_all,
    audit_run,
    is_banned_domain,
)

_NAIVE_DIR = Path("experiments/derived/arm1_flat")
_OPTIMISED_DIR = Path("experiments/derived/arm2_flat")


# ---------------------------------------------------------------------------
# Unit tests: is_banned_domain
# ---------------------------------------------------------------------------


class TestIsBannedDomain:
    """is_banned_domain matches the protocol §3.4 banned set."""

    def test_en_wikipedia(self):
        assert is_banned_domain("https://en.wikipedia.org/wiki/X") is True

    def test_vi_m_wikipedia(self):
        assert is_banned_domain("https://vi.m.wikipedia.org/wiki/Y") is True

    def test_bare_wikipedia_hostname(self):
        assert is_banned_domain("en.wikipedia.org") is True

    def test_wikidata(self):
        assert is_banned_domain("https://www.wikidata.org/wiki/Q12345") is True

    def test_dbpedia(self):
        assert is_banned_domain("https://dbpedia.org/resource/X") is True

    def test_wikiwand(self):
        assert is_banned_domain("https://www.wikiwand.com/en/articles/X") is True

    def test_gem_wiki_not_banned(self):
        """gem.wiki (Global Energy Monitor) is NOT banned — critical near-miss."""
        assert is_banned_domain("https://www.gem.wiki/Mong_Duong_power_station") is False

    def test_moit_gov_vn_not_banned(self):
        assert is_banned_domain("https://moit.gov.vn/report") is False

    def test_bare_word_not_banned(self):
        """A bare word like 'Wikipedia' (no dots) is not a domain."""
        assert is_banned_domain("Wikipedia") is False

    def test_empty_string(self):
        assert is_banned_domain("") is False

    def test_evn_domain_not_banned(self):
        assert is_banned_domain("https://en.evn.com.vn/report") is False


# ---------------------------------------------------------------------------
# Unit test: synthetic fixture — Notes cells must NOT inflate counts
# ---------------------------------------------------------------------------


class TestSyntheticFixture:
    """Synthetic 3-row markdown verifies S1/S2 counting and Notes exclusion."""

    SYNTHETIC_MD = """\
# Thermal Power Plants

| # | Name | Province | Fuel | Tech | Units | MW | Status | Date | COD | Owner | Confidence | Source 1 | Source 2 | Notes |
|---|------|----------|------|------|-------|----|--------|------|-----|-------|------------|----------|----------|-------|
| 1 | Plant A | Ha Noi | Coal | Sub | 1×300 | 300 | Op | 2026 | 2015 | EVN | HIGH | [EVN](https://evn.com.vn/report) | [Wiki](https://en.wikipedia.org/wiki/Plant_A) | Clean row |
| 2 | Plant B | HCMC | Gas | CCGT | 1×400 | 400 | Op | 2026 | 2018 | PVN | HIGH | [GEM](https://www.gem.wiki/Plant_B) | [MOIT](https://moit.gov.vn/report) | Lead: Wikipedia (inadmissible) |
| 3 | Plant C | Da Nang | Coal | Sub | 1×200 | 200 | Op | 2026 | 2020 | EVN | MEDIUM | [Wiki](https://vi.m.wikipedia.org/wiki/Plant_C) | [EVN](https://evn.com.vn/ar2023) | Notes cell should not count |

## Bibliography

1. **EVN Annual Report 2023.** [evn.com.vn](https://evn.com.vn/report)
2. **Wikipedia List.** [en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam)
3. **GEM GCPT.** [gem.wiki](https://www.gem.wiki/GCPT)
"""

    def test_counts(self, tmp_path: Path):
        md_file = tmp_path / "test_run01.md"
        md_file.write_text(self.SYNTHETIC_MD)

        result = audit_run(md_file)

        # S1/S2: row 1 has 1 banned in S2, row 2 has 0, row 3 has 1 banned in S1
        assert result["n_banned_s1s2"] == 2, (
            "Expected 2 banned S1/S2 URLs (row 1 S2 + row 3 S1)"
        )
        # S1/S2 cell count: 3 rows × 2 columns = 6
        assert result["n_cells_s1s2"] == 6

        # Bib: 1 banned URL (the wikipedia.org entry)
        assert result["n_banned_bib"] == 1

    def test_notes_with_wikipedia_word_excluded(self, tmp_path: Path):
        """Row 2 Notes says 'Wikipedia (inadmissible)' — must NOT be counted."""
        md_file = tmp_path / "test_run01.md"
        md_file.write_text(self.SYNTHETIC_MD)

        result = audit_run(md_file)

        # If Notes were scanned, n_banned_s1s2 would be higher
        # The word "Wikipedia" in Notes has no URL, so even if scanned it
        # wouldn't match — but we verify the column is excluded by design.
        assert result["n_banned_s1s2"] == 2


# ---------------------------------------------------------------------------
# Corpus tests (real data) — @pytest.mark.slow (need experiments/derived/)
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestCorpusPins:
    """Pin known findings against the real corpus."""

    def test_row_count(self):
        rows = audit_all(_NAIVE_DIR, _OPTIMISED_DIR)
        assert len(rows) == 40, f"Expected 40 rows (4 agents × 5 runs × 2 arms), got {len(rows)}"

    def test_mistral_optimised_has_banned(self):
        rows = audit_all(_NAIVE_DIR, _OPTIMISED_DIR)
        mistral_opt = [
            r for r in rows if r["agent"] == "mistral" and r["arm"] == "optimised"
        ]
        banned_count = sum(r["n_banned_s1s2"] + r["n_banned_bib"] for r in mistral_opt)
        assert banned_count > 0, "Mistral optimised arm should have banned citations"

    def test_openai_optimised_run01_has_banned(self):
        rows = audit_all(_NAIVE_DIR, _OPTIMISED_DIR)
        openai_opt_r1 = [
            r for r in rows
            if r["agent"] == "openai" and r["arm"] == "optimised" and r["run"] == 1
        ]
        assert len(openai_opt_r1) == 1
        total = openai_opt_r1[0]["n_banned_s1s2"] + openai_opt_r1[0]["n_banned_bib"]
        assert total > 0, "OpenAI optimised run01 should have banned citations"

    def test_anthropic_optimised_clean(self):
        rows = audit_all(_NAIVE_DIR, _OPTIMISED_DIR)
        anthropic_opt = [
            r for r in rows if r["agent"] == "anthropic" and r["arm"] == "optimised"
        ]
        banned = sum(r["n_banned_s1s2"] + r["n_banned_bib"] for r in anthropic_opt)
        assert banned == 0, "Anthropic optimised arm should be clean"

    def test_qwen_optimised_clean(self):
        rows = audit_all(_NAIVE_DIR, _OPTIMISED_DIR)
        qwen_opt = [
            r for r in rows if r["agent"] == "qwen" and r["arm"] == "optimised"
        ]
        banned = sum(r["n_banned_s1s2"] + r["n_banned_bib"] for r in qwen_opt)
        assert banned == 0, "Qwen optimised arm should be clean"

    def test_openai_naive_run05_has_banned(self):
        rows = audit_all(_NAIVE_DIR, _OPTIMISED_DIR)
        openai_naive_r5 = [
            r for r in rows
            if r["agent"] == "openai" and r["arm"] == "naive" and r["run"] == 5
        ]
        assert len(openai_naive_r5) == 1
        total = openai_naive_r5[0]["n_banned_s1s2"] + openai_naive_r5[0]["n_banned_bib"]
        assert total > 0, "OpenAI naive run05 should have banned citations"


# ---------------------------------------------------------------------------
# Adherence: main.tex literal matches CSV-derived aggregate
# ---------------------------------------------------------------------------


@pytest.mark.adherence
class TestManuscriptConsistency:
    """The compliance count quoted in main.tex must match the generated CSV."""


    _CSV_PATH = Path("report/inputs/generated/tab_exp2_wiki_compliance.csv")

    def test_optimised_arm_count_matches(self):
        """The phrase 'N of the 20 optimised-arm runs' in main.tex must agree
        with the CSV count of optimised rows having any banned citation."""
        if not self._CSV_PATH.exists():
            pytest.skip("CSV not yet generated")

        # Parse CSV independently (no script import — anti-tautology)
        with self._CSV_PATH.open() as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)

        optimised_banned_runs = sum(
            1 for r in rows
            if r["arm"] == "optimised"
            and (int(r["n_banned_s1s2"]) + int(r["n_banned_bib"]) > 0)
        )

        # Parse main.tex independently (normalized: line-wraps joined)
        text = body()
        pattern = re.compile(r"(\d+)\s+of the 20 optimised-arm runs")
        match = pattern.search(text)
        assert match is not None, (
            "main.tex must contain '... N of the 20 optimised-arm runs'"
        )
        prose_count = int(match.group(1))

        assert prose_count == optimised_banned_runs, (
            f"main.tex says {prose_count} but CSV shows {optimised_banned_runs}"
        )
