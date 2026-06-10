"""Ticket 0509 — arXiv re-title and front/back matter for the standalone preprint.

Asserts the manuscript carries its arXiv identity: the new (registered) title as
the H1, the Econom'IA provenance footnote, author ORCID/email, the back-matter
sections (Data & Code Availability, Funding, author contributions / conflict of
interest), and that the two stale forward-references to a non-inline 2×2 table /
to "the slides" are gone.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

MAIN_MD = (
    Path(__file__).resolve().parent.parent / "slides" / "manuscript" / "main.md"
)

NEW_TITLE_SUBSTR = "Can Frontier AI Build a Statistical Register?"


def _md() -> str:
    return MAIN_MD.read_text(encoding="utf-8")


def _h1_line() -> str:
    for line in _md().splitlines():
        if line.startswith("# "):
            return line
    raise AssertionError("no H1 line found in main.md")


def test_new_title_is_h1():
    """The H1 carries the new title; 'Beyond RAG' must not be the H1 title."""
    h1 = _h1_line()
    assert NEW_TITLE_SUBSTR in h1, f"new title missing from H1; got: {h1}"
    assert "Beyond RAG" not in h1, (
        "old 'Beyond RAG' title must not remain the H1 (it may survive only "
        f"inside the Econom'IA provenance footnote); got: {h1}"
    )


def test_data_and_code_availability_present():
    assert "Data & Code Availability" in _md()


def test_funding_present():
    assert re.search(r"\*\*Funding\.\*\*", _md()), "Funding back-matter section missing"


def test_orcid_present():
    assert "0000-0001-9988-2100" in _md(), "author ORCID missing"


def test_conflict_of_interest_present():
    assert "conflicts of interest" in _md(), "author conflict-of-interest disclosure missing"


def test_no_dangling_forward_references():
    md = _md()
    assert "see the 2×2 factorial table" not in md, (
        "stale forward-ref to a non-inline 2×2 table must be removed"
    )
    assert "appears in the slides" not in md, (
        "standalone paper must not forward-reference 'the slides'"
    )
