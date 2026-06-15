"""Ticket 0629 — §7 closing subsection reframed as a rest stop.

Reading-3 (tracker 0605). The §7 subsection ``sec:ext-system`` ("What system
do the findings imply?") was a developed argument (stateful architecture,
narrative knowledge base, KG triples, method-quality-as-process). It is
reframed as a short rest stop bridging to §8/§9, and the surplus is relocated
to §9 (knowledge-base architecture) — without duplication.

Negative / structural guards only (CI polarity rule, 0557). We never pin the
positive authorial wording of the rest stop; positive intent lives in
``docs/editorial-brief.md``.

- Structural: the rest stop carries forward references to §8 and §9 (the two
  sections it bridges into) and the coverage-bar vocabulary the ticket fixes.
- Structural: the subsection is materially shorter than the §9 paragraph that
  now carries the relocated architecture material (a size sanity check, not a
  wording pin).
- Negative dedup guard: the relocated architecture sentences (the KG-triple
  mapping; the stateful-pipeline-built-on-the-corpus claim) appear at most
  once across the whole body, and not inside the §7 rest stop.
"""

import re

import pytest
from manuscript_source import body, section

pytestmark = pytest.mark.adherence


def test_rest_stop_bridges_to_discussion_and_future() -> None:
    """Structural: the rest stop forward-refs the two sections it bridges into.

    The label references are the load-bearing anchors; the prose around them is
    free to change. A rest stop that does not point at §8 and §9 is not a
    bridge.
    """
    s7 = section("sec:ext-system")
    for label in ("sec:discussion", "sec:future"):
        assert f"\\ref{{{label}}}" in s7, (
            f"§7 rest stop (sec:ext-system) must forward-reference "
            f"\\ref{{{label}}} — it bridges into §8 and §9 (ticket 0629)"
        )


def test_rest_stop_uses_coverage_bar_vocabulary() -> None:
    """Structural anchor: the fixed coverage-bar term (ticket 0615) is present.

    Loose structural anchor — pins a vocabulary the author does not own
    (the coverage bar defined in §exp1, ticket 0615), not a sentence the
    author wrote.
    """
    s7 = section("sec:ext-system")
    assert "coverage bar" in s7, (
        "§7 rest stop must place the experiments against the 'coverage bar' "
        "(the fixed term from ticket 0615) — Exp 1 below it, Exp 2 toward it "
        "(ticket 0629)"
    )


def test_rest_stop_is_short() -> None:
    """Structural size check: the rest stop is shorter than the §9 paragraph
    that now carries the relocated architecture material.

    Not a wording pin — a size sanity check that the developed argument was
    moved out of §7 rather than left in place. The §9 knowledge-base
    architecture paragraph (anchored by the KG-triple sentence) is the
    relocation target and must be the longer of the two.
    """
    s7 = section("sec:ext-system")
    s9 = section("sec:future")
    # The relocated architecture material lives in §9; the §7 rest stop must
    # be a fraction of the whole §9 section.
    assert len(s7) < len(s9), (
        "§7 rest stop (sec:ext-system) must be materially shorter than §9 "
        "(sec:future), which now carries the relocated architecture material "
        "(ticket 0629)"
    )


def test_relocated_architecture_sentences_not_duplicated() -> None:
    """Negative dedup guard: the relocated sentences appear at most once.

    The KG-triple mapping and the stateful-pipeline-built-on-the-corpus claim
    were moved from §7 to §9. They must not survive in §7 (would defeat the
    reframe) and must not appear twice in the body (would duplicate across
    §7/§8/§9). Lexically stable signatures, per the CI polarity asymmetry.
    """
    text = body()
    s7 = section("sec:ext-system")

    kg_triple = re.compile(r"knowledge-graph triple", re.IGNORECASE)
    # The §9 relocation signature (the full corpus-investment claim). The §7
    # subsection and the §fusion teaser may legitimately *point* at this idea
    # in different words; the dedup guard targets only the developed sentence.
    stateful = re.compile(
        r"invests in the corpus between runs rather than in a stronger model",
        re.IGNORECASE,
    )

    assert len(kg_triple.findall(text)) <= 1, (
        "the relocated 'knowledge-graph triple' mapping appears more than once "
        "across the body — it must live only in §9, not be duplicated "
        "(ticket 0629 dedup guard)"
    )
    assert len(stateful.findall(text)) <= 1, (
        "the relocated stateful-pipeline-built-on-the-corpus claim appears "
        "more than once — keep it once, in §9 (ticket 0629 dedup guard)"
    )
    assert not kg_triple.search(s7), (
        "the KG-triple architecture sentence must be relocated OUT of the §7 "
        "rest stop into §9 (ticket 0629)"
    )
    assert not stateful.search(s7), (
        "the stateful-architecture claim must be relocated OUT of the §7 rest "
        "stop into §9 (ticket 0629)"
    )
