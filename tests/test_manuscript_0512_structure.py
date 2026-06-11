"""Ticket 0512 — structural revisions to slides/manuscript/main.md.

Adherence tests pinning the §3-review restructuring:

1. A numbered §2 "Related Work — Empirical landscape" heading exists.
2. An unnumbered "Related Work — Methods" section appears *before* the
   Conclusion (the theoretical/methods RW was relocated out of the front).
3. No internal scaffolding remains in main.md: PR refs (``#NNN``), bare
   four-digit ticket refs (``0NNN``, modulo legitimate ORCID digits),
   ``palette.toml``, and commit-hash references.
4. The long-tail recognition figure is referenced (0514 fold-in), and its
   caption layer counts are re-derived from the committed CSV.
"""

import csv
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
MAIN_MD = REPO_ROOT / "slides" / "manuscript" / "main.md"
LONGTAIL_CSV = REPO_ROOT / "data" / "reference" / "tab_longtail_layers.csv"


def _md() -> str:
    if not MAIN_MD.exists():
        pytest.skip("main.md not found")
    return MAIN_MD.read_text(encoding="utf-8")


def test_empirical_related_work_section_exists():
    md = _md()
    # Ticket 0518: number is now symbolic ({#sec:related-empirical}, auto §2).
    assert "## Related Work — Empirical landscape {#sec:related-empirical}" in md, (
        "labelled §2 empirical Related Work heading missing"
    )


def test_methods_related_work_before_conclusion():
    md = _md()
    methods = md.find("## Related Work — Methods")
    assert methods != -1, "unnumbered 'Related Work — Methods' section missing"
    conclusion = md.find("## Conclusion {#sec:conclusion}")
    if conclusion == -1:
        conclusion = md.find("## Conclusion")
    assert conclusion != -1, "Conclusion heading missing"
    assert methods < conclusion, (
        "'Related Work — Methods' must appear before the Conclusion"
    )


def test_why_we_redo_gem_paragraph_present():
    md = _md()
    # The why-we-redo-GEM paragraph motivates re-compiling GEM with per-cell
    # provenance / reproducible compilation / licence.
    assert "per-cell provenance" in md or "per-cell\nprovenance" in md, (
        "why-we-redo-GEM paragraph (per-cell provenance) missing from §2"
    )


def test_no_pr_references():
    md = _md()
    hits = re.findall(r"#\d{3}\b", md)
    assert not hits, f"internal PR references must be stripped from main.md: {hits}"


def test_no_palette_toml():
    md = _md()
    assert "palette.toml" not in md, "internal palette.toml reference must be stripped"


def test_no_ticket_scaffolding():
    """No bare four-digit ticket refs remain.

    ORCID identifiers contain legitimate ``0000``/``0001``/``9988`` groups; we
    exclude any digit-group that is part of the ORCID URL or label line.
    """
    md = _md()
    # Drop the ORCID line(s) before scanning.
    scrubbed = "\n".join(
        line for line in md.splitlines() if "orcid" not in line.lower()
    )
    # Match a bare 0NNN token (ticket-id shaped) not part of a longer number.
    hits = re.findall(r"(?<![\d.\-])0\d{3}(?![\d.\-])", scrubbed)
    assert not hits, f"bare ticket-id scaffolding must be stripped from main.md: {hits}"


def test_no_commit_hash_reference():
    md = _md()
    assert "85a0e6c" not in md, "commit-hash reference must be stripped from main.md"


def test_longtail_figure_referenced():
    md = _md()
    assert "fig_longtail_recognition.pdf" in md, (
        "long-tail recognition figure (0514) must be referenced in main.md"
    )


def test_longtail_caption_counts_match_csv():
    md = _md()
    if not LONGTAIL_CSV.exists():
        pytest.skip(f"{LONGTAIL_CSV} not found")
    rows = list(csv.DictReader(LONGTAIL_CSV.open(encoding="utf-8")))
    gold = sum(int(r["in_gold"]) for r in rows)
    gem = sum(int(r["in_gem"]) for r in rows)
    wiki = sum(int(r["in_wiki"]) for r in rows)
    census = sum(1 for r in rows if int(r["census_count"]) > 0)
    assert gold == 177
    # Each derived layer count must appear verbatim in the manuscript prose.
    for val in (str(gem), str(wiki), str(census)):
        assert val in md, (
            f"long-tail layer count {val} (re-derived from CSV) missing from main.md"
        )


def test_perimeters_paragraph_present():
    md = _md()
    # The statistical-perimeters paragraph defines "complete" per use case.
    assert "market dispatch" in md.lower(), (
        "statistical-perimeters paragraph (0514) missing from §2"
    )
