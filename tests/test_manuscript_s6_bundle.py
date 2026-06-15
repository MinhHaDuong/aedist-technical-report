"""Tickets 0618 / 0619 / 0621 — §6 (Experiment 2) prose cleanup.

Reading-3 (tracker 0605). Three §6 edits, each guarded by a NEGATIVE pin only
(CI polarity rule, 0557 — forbid the dropped phrasing, never pin the new
wording):

- 0618: the §6 second paragraph (which-quality-dimensions-we-don't-measure
  scope caveat) is dropped — its "require \\emph{peer cross-evaluation}" /
  "are out of scope here" signature is absent from §6, and the figure it
  cited (fig:coverage-certainty) is not orphaned (still referenced elsewhere).
- 0619: the unsupported "under-indexed by Western search" claim is gone from
  the whole body (§6 body AND the annex echo).
- 0621: the "independent sweep, not a … baseline" / "Read with that caveat"
  not-comparable hand-wave is absent from §6.
"""

import re

import pytest
from manuscript_source import body, section

pytestmark = pytest.mark.adherence


def test_0618_exp2_scope_caveat_paragraph_dropped() -> None:
    """The §6 second paragraph's scope-caveat signature is gone.

    Negative guard: the dropped paragraph's distinctive phrasings — the
    "require peer cross-evaluation" qualifier and the "out of scope here"
    disclaimer — must not survive in §6 (sec:exp2). The implied scope lives
    in the section title and the later restatement; this paragraph is the
    one removed.
    """
    exp2 = section("sec:exp2")
    assert "peer cross-evaluation" not in exp2, (
        "the dropped §6 second paragraph's 'require \\emph{peer "
        "cross-evaluation}' signature must not reappear in §6 (ticket 0618)"
    )
    assert "out of scope here" not in exp2, (
        "the dropped §6 second paragraph's 'are out of scope here' disclaimer "
        "must not reappear in §6 (ticket 0618)"
    )


def test_0618_coverage_certainty_figure_not_orphaned() -> None:
    """Dropping the §6 second paragraph must not orphan its figure ref.

    Structural guard: fig:coverage-certainty is defined in the annex and was
    cited by the dropped paragraph; it must still be referenced somewhere in
    the body (the Provenance paragraph carries it).
    """
    text = body()
    assert "\\label{fig:coverage-certainty}" in text, (
        "fig:coverage-certainty must still be defined (ticket 0618)"
    )
    assert "\\ref{fig:coverage-certainty}" in text, (
        "fig:coverage-certainty must still be referenced somewhere in the "
        "body after dropping the §6 second paragraph — not orphaned "
        "(ticket 0618)"
    )


def test_0619_under_indexed_claim_gone_everywhere() -> None:
    """The unsupported "under-indexed by Western search" claim is gone.

    Negative guard: the claim appeared twice (§6 body and annex). Lack of
    evidence means it must survive in neither place — scan the whole body.
    """
    text = body()
    assert "under-indexed by Western search" not in text, (
        "the unsupported 'under-indexed by Western search' claim must not "
        "appear anywhere in the manuscript body (ticket 0619)"
    )


def test_0621_not_comparable_handwave_gone() -> None:
    """The single-shot-arm "not comparable / read with that caveat" framing is gone.

    Negative guard: the not-comparable hand-wave ("independent sweep, not a
    … baseline" plus "Read with that caveat") is replaced by a positive
    explanation of the Exp-1 difference. Forbid the hand-wave; do not pin the
    new wording.
    """
    exp2 = section("sec:exp2")
    assert "Read with that caveat" not in exp2, (
        "the dropped 'Read with that caveat' not-comparable hand-wave must "
        "not reappear in §6 (ticket 0621)"
    )
    handwave = re.compile(r"independent sweep,\s*not a", re.IGNORECASE)
    assert not handwave.search(exp2), (
        "the dropped 'independent sweep, not a … baseline' not-comparable "
        "framing must not reappear in §6 (ticket 0621)"
    )
