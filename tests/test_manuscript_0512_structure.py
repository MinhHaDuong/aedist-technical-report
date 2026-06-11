"""Ticket 0512 — structural revisions to the manuscript (now main.tex, 0524).

Adherence tests pinning the §3-review restructuring:

1. A numbered "Related Work — Empirical landscape" section exists.
2. An unnumbered "Related Work — Methods" section appears *before* the
   Conclusion (the theoretical/methods RW was relocated out of the front).
3. No internal scaffolding remains in the body: PR refs (``#NNN``), bare
   four-digit ticket refs (``0NNN``, modulo legitimate ORCID digits),
   ``palette.toml``, and commit-hash references.
4. The long-tail recognition figure is referenced (0514 fold-in), and its
   caption layer counts are re-derived from the committed CSV.
"""

import csv
import re
from pathlib import Path

import pytest
from manuscript_source import body

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
LONGTAIL_CSV = REPO_ROOT / "data" / "reference" / "tab_longtail_layers.csv"


def test_empirical_related_work_section_exists():
    assert "\\section{Related Work — Empirical landscape}\\label{sec:related-empirical}" in body(), (
        "labelled empirical Related Work heading missing"
    )


def test_methods_related_work_before_conclusion():
    text = body()
    methods = text.find("\\section*{Related Work — Methods}")
    assert methods != -1, "unnumbered 'Related Work — Methods' section missing"
    conclusion = text.find("\\section{Conclusion}\\label{sec:conclusion}")
    assert conclusion != -1, "Conclusion heading missing"
    assert methods < conclusion, (
        "'Related Work — Methods' must appear before the Conclusion"
    )


def test_why_we_redo_gem_paragraph_present():
    assert "per-cell provenance" in body(), (
        "why-we-redo-GEM paragraph (per-cell provenance) missing from §2"
    )


def test_no_pr_references():
    hits = re.findall(r"#\d{3}\b", body())
    assert not hits, f"internal PR references must be stripped from main.tex: {hits}"


def test_no_palette_toml():
    assert "palette.toml" not in body(), "internal palette.toml reference must be stripped"


def test_no_ticket_scaffolding():
    """No bare four-digit ticket refs remain in the document body.

    ORCID identifiers contain legitimate ``0000``/``0001``/``9988`` groups; the
    ORCID lives in the preamble title block, outside the scanned body. Preamble
    maintenance comments (which may cite ticket numbers) are stripped by the
    body() normalizer.
    """
    text = body()
    scrubbed = re.sub(r"\S*orcid\S*", " ", text, flags=re.IGNORECASE)
    hits = re.findall(r"(?<![\d.\-])0\d{3}(?![\d.\-])", scrubbed)
    assert not hits, f"bare ticket-id scaffolding must be stripped from main.tex: {hits}"


def test_no_commit_hash_reference():
    assert "85a0e6c" not in body(), "commit-hash reference must be stripped from main.tex"


def test_longtail_figure_referenced():
    assert "fig_longtail_recognition.pdf" in body(), (
        "long-tail recognition figure (0514) must be referenced in main.tex"
    )


def test_longtail_caption_counts_match_csv():
    text = body()
    if not LONGTAIL_CSV.exists():
        pytest.skip(f"{LONGTAIL_CSV} not found")
    rows = list(csv.DictReader(LONGTAIL_CSV.open(encoding="utf-8")))
    gold = sum(int(r["in_gold"]) for r in rows)
    gem = sum(int(r["in_gem"]) for r in rows)
    wiki = sum(int(r["in_wiki"]) for r in rows)
    osm = sum(int(r["in_osm"]) for r in rows)
    assert gold == 177
    # Each derived layer count must appear verbatim in the manuscript prose.
    for val in (str(gem), str(wiki), str(osm)):
        assert val in text, (
            f"long-tail layer count {val} (re-derived from CSV) missing from main.tex"
        )


def test_perimeters_paragraph_present():
    assert "market dispatch" in body().lower(), (
        "statistical-perimeters paragraph (0514) missing from §2"
    )
