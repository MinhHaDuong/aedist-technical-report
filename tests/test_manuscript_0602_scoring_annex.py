"""Ticket 0602 — Scoring annex + intro corroboration/hedge guards.

CI polarity rule (0557): negative guards + loose structural anchors only,
never a pinned positive authorial sentence.

- Negative guard: the unmeasured "corroboration" claim is gone from the
  intro's benchmark definition. (The Exp2 sections legitimately report
  Source-2 double-sourcing as "corroboration", so the guard is scoped to
  the Introduction, not the whole document.)
- Negative guard: the operational citation hedge no longer sits in the
  intro.
- Loose structural anchor: a Scoring annex (sec:annex-scoring) exists,
  marks itself version 0.1, and names all four dimension markers — a
  vocabulary the author does not own, not a sentence the author wrote.
- Loose structural anchor: §3 references the Scoring annex as the
  implementation (the symbolic \\ref is present in sec:quality).
"""

import pytest
from manuscript_source import section

pytestmark = pytest.mark.adherence


def test_intro_drops_corroboration_claim() -> None:
    """0602: the intro no longer claims corroboration is measured."""
    intro = section("sec:intro")
    assert "corroborat" not in intro.lower(), (
        "the benchmark does not measure corroboration (no corroborat* in "
        "src/aedist/score_*.py) — drop the claim from the Introduction"
    )


def test_intro_drops_operational_citation_hedge() -> None:
    """0602: the per-cell citation hedge moved out of the intro."""
    intro = section("sec:intro")
    assert "does not verify each cited source against each cell" not in intro, (
        "the operational citation hedge belongs in §3's provenance "
        "discussion, not the Introduction"
    )


def test_scoring_annex_exists_marked_v0_1() -> None:
    """0602 (loose anchor): a Scoring annex exists and marks itself v0.1."""
    annex = section("sec:annex-scoring")
    assert "version 0.1" in annex, (
        "the Scoring annex must mark itself version 0.1 of the benchmark"
    )


def test_scoring_annex_names_four_dimensions() -> None:
    """0602 (loose anchor): the four dimension markers are present in the annex.

    Anchors on the four-dimension vocabulary (accuracy/coherence/provenance/
    temporality) the §3 quality bar defines — not on any authored sentence.
    """
    annex = section("sec:annex-scoring").lower()
    for marker in ("accuracy", "coherence", "provenance", "temporality"):
        assert marker in annex, (
            f"Scoring annex must cover the {marker} dimension"
        )


def test_section3_references_scoring_annex() -> None:
    """0602 (loose anchor): §3 points at the Scoring annex as the implementation."""
    quality = section("sec:quality")
    assert "\\ref{sec:annex-scoring}" in quality, (
        "§3 (sec:quality) must reference the Scoring annex (sec:annex-scoring)"
    )
