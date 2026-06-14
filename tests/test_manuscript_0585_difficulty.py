"""Ticket 0585 — §7.1 plain difficulty story + Annex C cruft removal.

Reading-2 findings 13–17 (tracker 0578). Negative guards only (CI polarity
rule, 0557): two generation-instruction / data-flow literals that leaked into
the Annex C prose must not survive, and the composition table's stable
``\\label`` must stay attached to its content as it moves into §7.1.

Findings:
- 13: "names read left-to-right, no rotation" — a generation instruction
  surviving as prose — is dropped.
- 14: the "(… producer--consumer chaining)" parenthesis — a data-flow
  organisation detail — is dropped.
- 16: ``tbl:status-difficulty`` keeps its label (label-stability contract,
  editorial-brief entry label-stability-contract).
"""

import pytest
from manuscript_source import body

pytestmark = pytest.mark.adherence


def _md() -> str:
    return body()


def test_no_left_to_right_generation_instruction() -> None:
    """Finding 13: the leftover generation instruction is gone."""
    md = _md()
    assert "left-to-right, no rotation" not in md, (
        "generation instruction 'names read left-to-right, no rotation' "
        "must not survive as prose (finding 13)"
    )
    assert "no rotation" not in md, (
        "the 'no rotation' generation instruction must be dropped (finding 13)"
    )


def test_no_producer_consumer_dataflow_parenthesis() -> None:
    """Finding 14: the producer--consumer data-flow detail is gone."""
    md = _md()
    # normalized() folds the TeX '--' to an en dash, so match both surfaces.
    assert "producer–consumer chaining" not in md and "producer-consumer chaining" not in md, (
        "the '(... producer--consumer chaining)' data-flow parenthesis "
        "must be dropped (finding 14)"
    )


def test_status_difficulty_table_keeps_label() -> None:
    """Finding 16: the composition table keeps its stable label after the move."""
    md = _md()
    assert "\\label{tbl:status-difficulty}" in md, (
        "tbl:status-difficulty must keep its label as the table moves into "
        "§7.1 (label-stability-contract)"
    )
