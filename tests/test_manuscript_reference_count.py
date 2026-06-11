"""Ticket 0501 — the manuscript reference-count literal is re-derived from the artifact.

The adherence invariant: every mention of the reference plant count in
``slides/manuscript/main.tex`` equals ``reference_plant_count()`` (the count
derived from the adopted reference CSV). Pairs with
``test_reference_count.py`` (which pins the CSV-derived count) and
``test_abstract_numbers.py`` (which guards the abstract F1 literals).

This closes the gap that let #906 move the data to 177 while the manuscript
silently stayed at 173: ``test_no_hardcoded_reference_size.py`` scans ``src/``
only, never the manuscript prose.
"""

from pathlib import Path

import pytest
from manuscript_source import body

from aedist.evaluate import reference_plant_count

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent

# Vintages the manuscript must NOT carry as a reference-count literal.
# 177 (v2.4) is current; 170/173/176/180 are superseded. Phrased as the
# count-bearing collocations that actually appear in the prose/captions, so a
# year or unrelated 173 cannot trip the test.
_STALE_COLLOCATIONS = [
    "{n}-plant",
    "{n} plant-level",
    "{n} thermal plants",
    "{n} reference plants",
    "at {n}",  # "dashed reference line at 173"
    "the {n} reference",
]
_STALE_VINTAGES = (170, 173, 176, 180)


def _text() -> str:
    return body()


def test_manuscript_count_matches_reference():
    """No superseded reference-count literal survives in main.tex."""
    md = _text()
    violations = []
    for vintage in _STALE_VINTAGES:
        for template in _STALE_COLLOCATIONS:
            needle = template.format(n=vintage)
            if needle in md:
                violations.append(needle)
    assert not violations, (
        "stale reference-count literals still in slides/manuscript/main.tex: "
        f"{violations} — reconcile to reference_plant_count()="
        f"{reference_plant_count()}"
    )


def test_manuscript_carries_current_count():
    """The current reference count appears as a count literal in main.tex."""
    n = reference_plant_count()
    md = _text()
    assert f"{n}-plant" in md or f"{n} thermal plants" in md, (
        f"current reference count {n} not present as a count literal in main.tex"
    )
