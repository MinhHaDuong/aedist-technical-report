"""Ticket 0588 — §8 (Discussion) condensation, new opening, scoring levels.

Reading-2 finding 40 (tracker 0578). The Discussion was condensed to ~1.5
pages, given a new opening that names the limits-and-potential framing, and
extended with a three-level scoring discussion (method / run / model quality)
grounded in ``docs/scoring-contract.md`` and the screening subsection.

Negative / structural guards only (CI polarity rule, 0557):
- the dropped "consistent reading … summarised in the Introduction" sentence
  signature is absent from the whole body (negative guard, the ticket's test);
- the scoring-levels discussion is anchored by the fixed label references it
  must cite (cost-quality figure, reliability figure, screen subsection) —
  structural presence of label citations, not authorial wording.
"""

import re

import pytest
from manuscript_source import body, section

pytestmark = pytest.mark.adherence


def test_consistent_reading_summary_sentence_dropped() -> None:
    """Finding 40: the "how to NOT say a thing" opener is gone.

    The author flagged "support a consistent reading, summarised in the
    Introduction" as an empty self-reference. This is a pure negative guard:
    the signature phrase must not reappear anywhere in the body.
    """
    text = body()
    forbidden = re.compile(r"consistent reading", re.IGNORECASE)
    assert not forbidden.search(text), (
        "the dropped '… support a consistent reading, summarised in the "
        "Introduction' sentence (reading-2 finding 40) must not reappear in "
        "the manuscript body (ticket 0588)"
    )


def test_discussion_scoring_levels_cite_their_anchors() -> None:
    """The scoring-levels discussion cites the figures/subsection it rests on.

    Structural guard (not a wording pin): the three-level scoring discussion
    (method quality = resources vs result, run quality, model quality) is
    grounded in the cost-versus-F1 figure, the model reliability figure, and
    the screening subsection. Those label references are the load-bearing
    anchors; their wording around them is free to change.
    """
    disc = section("sec:discussion")
    for label in ("fig:cost-quality", "fig:reliability", "sec:ext-screen"):
        assert f"\\ref{{{label}}}" in disc, (
            f"§8 (sec:discussion) must cite \\ref{{{label}}} — the "
            "three-level scoring discussion rests on it (ticket 0588, "
            "finding 40)"
        )
