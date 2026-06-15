"""Ticket 0600 — Exp 2 costs reported as un-optimised upper bound.

Loose structural anchor (CI polarity rule, ticket 0557): the Exp 2 cost
region (§6, near fig:exp2-arms-cost) must carry a caching/upper-bound
caveat. We assert presence of caveat vocabulary in the §6 body — NOT a
pinned sentence, so any legitimate rewrite of the wording passes.

The caveat vocabulary class: "upper bound", "not minimis", "no prompt
caching", or "cache management". At least one of these must appear in §6.
"""

import pytest
from manuscript_source import section

pytestmark = pytest.mark.adherence

_CAVEAT_MARKERS = [
    "upper bound",
    "not minimis",
    "no prompt caching",
    "cache management",
]


def test_exp2_cost_upper_bound_caveat_present() -> None:
    """§6 must contain a caching/upper-bound caveat in the cost region."""
    sec6 = section("sec:exp2")
    found = any(marker in sec6 for marker in _CAVEAT_MARKERS)
    assert found, (
        "§6 (sec:exp2) must carry an un-optimised/upper-bound cost caveat "
        "(ticket 0600). Expected at least one of: "
        + ", ".join(repr(m) for m in _CAVEAT_MARKERS)
        + " — none found. The reported Exp 2 costs are un-optimised "
        "(no caching, reference pack resent every call) and must be "
        "framed as an upper bound on production cost, not a floor."
    )
