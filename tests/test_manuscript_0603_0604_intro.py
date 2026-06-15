"""Tickets 0603 + 0604 — intro prose guards.

Negative guards only (CI polarity rule, 0557):

- 0603: "The benchmark earns its keep" sentence is gone from intro para 4;
  "human attention" is gone (subject shifts to correlation/consequence,
  "human" qualifier dropped).
- 0604: social-science jargon "as a lens for" and "We situate" are gone
  from the intro; roadmap sentence uses plain English instead.
"""

import pytest
from manuscript_source import body

pytestmark = pytest.mark.adherence


def _md() -> str:
    return body()


def test_no_earns_its_keep(md: str = "") -> None:
    """0603: 'The benchmark earns its keep' sentence is dropped."""
    md = _md()
    assert "earns its keep" not in md, (
        "'The benchmark earns its keep by being usable without the gold "
        "reference' must be removed from the intro (ticket 0603)"
    )


def test_no_human_attention(md: str = "") -> None:
    """0603: 'human attention' qualifier is dropped."""
    md = _md()
    assert "human attention" not in md, (
        "'human attention' must be dropped from the intro — "
        "plain 'attention' suffices (ticket 0603)"
    )


def test_no_as_a_lens_for(md: str = "") -> None:
    """0604: 'as a lens for' social-science jargon is dropped from intro."""
    md = _md()
    assert "as a lens for" not in md, (
        "'as a lens for' must be removed from the intro — "
        "use plain English (ticket 0604)"
    )


def test_no_we_situate(md: str = "") -> None:
    """0604: 'We situate' is dropped from the intro roadmap sentence."""
    md = _md()
    assert "We situate" not in md, (
        "'We situate the work against' must be removed from the intro — "
        "use plain English (ticket 0604)"
    )
