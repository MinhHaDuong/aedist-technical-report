"""Ticket 0512 — structural revisions to the manuscript (now main.tex, 0524).

Adherence tests pinning the §3-review restructuring (decision pins updated
by ticket 0562, back-half restructure):

1. A numbered "Related Work — Empirical landscape" section exists.
2. The methods review lives in a numbered "Future research" section
   (lessons from the field + programme, ticket 0562); no unnumbered
   "Related Work — Methods" section remains in the body.
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
from manuscript_source import body, section

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
LONGTAIL_CSV = REPO_ROOT / "data" / "reference" / "tab_longtail_layers.csv"


def test_empirical_related_work_section_exists():
    assert "\\section{Related Work — Empirical landscape}\\label{sec:related-empirical}" in body(), (
        "labelled empirical Related Work heading missing"
    )


def test_future_research_section_absorbs_methods_review():
    """Ticket 0562 (tracker 0560): the methods review is absorbed into the
    numbered Future research section; the unnumbered 'Related Work — Methods'
    section is gone. Ticket 0589 (Finding 41): the juxtaposed literature blocks
    are replaced by research axes with woven literature — the old bridge
    paragraph 'From lessons to programme' must be gone."""
    text = body()
    assert "\\section*{Related Work" not in text, (
        "unnumbered 'Related Work — Methods' section must be gone: the "
        "methods review now lives inside the numbered Future research section "
        "(ticket 0562)"
    )
    assert "\\section{Future research}\\label{sec:future}" in text, (
        "numbered, labelled Future research section missing (ticket 0562)"
    )
    future = section("sec:future")
    assert "From lessons to programme" not in future, (
        "Ticket 0589 (Finding 41): literature is woven into the research axes; "
        "the old 'From lessons to programme' bridge paragraph must be gone"
    )


def test_no_companion_paper_promise_in_body():
    """Negative guard for the no-companion-paper-promise brief entry
    (tickets 0562, 0563): the manuscript frames forward-looking work as
    programme (sec:future) or not-measured-here scoping, never as a
    commitment to a specific forthcoming publication. Ticket 0563 stripped
    the Temporality annex's "subsequent paper" sentence, so the guard now
    scans the full body with no carve-out."""
    text = body()
    for promise in (
        "companion paper",
        "follow-on paper",
        "planned cross-evaluation",
        "subsequent paper",
        "in preparation",
        "working title",
    ):
        assert promise not in text, (
            f"publication promise {promise!r} found in the manuscript body "
            "(no-companion-paper-promise, docs/editorial-brief.md, ticket 0562)"
        )


def test_supplementary_figures_annex_dissolved():
    """Ticket 0563 (tracker 0560): the Supplementary-figures annex is gone.

    Both of its figures live in their natural annexes (coverage-certainty in
    the Experiment 2 annex, capability-dag in the rollout annex); the
    ``sec:annex-suppfigs`` label and every reference to it are deleted —
    the only label the 0560 stability contract removes by design."""
    assert "sec:annex-suppfigs" not in body(), (
        "sec:annex-suppfigs label or reference remains — the Supplementary "
        "figures annex must be dissolved (ticket 0563)"
    )


def test_capability_dag_figure_referenced():
    """Ticket 0563: fig:capability-dag is anchored by at least one \\ref —
    it was previously an unreferenced float in the suppfigs annex."""
    assert "\\ref{fig:capability-dag}" in body(), (
        "fig:capability-dag is never \\ref'd — the rollout annex must tie "
        "the transition-matrix figure to its prose (ticket 0563)"
    )


def test_clearpage_between_annexes():
    """Ticket 0563: every annex opens on a fresh page.

    Loose between-blocks check, not an "immediately preceded by \\clearpage"
    pin (a blank or comment line would spuriously fail that): at least one
    \\clearpage occurs in the gap before the first annex \\section after
    \\appendix, and in the gap between each pair of consecutive annex
    \\section headings."""
    text = body()
    assert "\\appendix" in text, "no \\appendix divider in main.tex"
    appendix = text.split("\\appendix", 1)[1]
    starts = [m.start() for m in re.finditer(r"(?<!sub)\\section\{", appendix)]
    assert len(starts) >= 2, "expected several annex sections after \\appendix"
    bounds = [0, *starts[:-1]]
    for gap_start, section_start in zip(bounds, starts, strict=True):
        gap = appendix[gap_start:section_start]
        assert "\\clearpage" in gap, (
            "annex \\section without a \\clearpage between it and the "
            f"previous block (ticket 0563): ...{appendix[section_start : section_start + 60]}"
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
