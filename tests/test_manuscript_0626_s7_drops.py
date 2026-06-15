"""Tickets 0626 + 0627 — §7 sentence drops.

Negative guards only (CI polarity rule, 0557):

- 0626: the §7 para-1 closing sentence "They are exploratory; each subsection
  summarises one analysis." is dropped — the paragraph ends on the
  audience-questions sentence.
- 0627: the §7.1 trailing clause ", so the low overall recognition is a
  property of the list's composition, not merely a model failure." is dropped —
  the sentence ends at "falls far below that of operational plants."
"""

import pytest
from manuscript_source import body

pytestmark = pytest.mark.adherence


def _md() -> str:
    return body()


def test_no_exploratory_subsection_sentence() -> None:
    """0626: the 'They are exploratory' closing sentence is gone."""
    md = _md()
    assert "They are exploratory" not in md, (
        "'They are exploratory; each subsection summarises one analysis.' "
        "must be dropped from §7 para 1 (ticket 0626)"
    )
    assert "each subsection summarises one analysis" not in md, (
        "'each subsection summarises one analysis' "
        "must be dropped from §7 para 1 (ticket 0626)"
    )


def test_no_composition_not_model_failure_clause() -> None:
    """0627: the 'not merely a model failure' clause is gone."""
    md = _md()
    assert "not merely a model failure" not in md, (
        "', so the low overall recognition is a property of the list's "
        "composition, not merely a model failure.' must be dropped from "
        "§7.1 (ticket 0627)"
    )
    assert "list's composition, not merely" not in md, (
        "the trailing 'list's composition, not merely a model failure' clause "
        "must be dropped from §7.1 (ticket 0627)"
    )
