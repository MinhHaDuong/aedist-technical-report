"""Ticket 0433 — the manuscript's Exp2 tech-spec annex rewritten to the as-run story.

The annex labelled ``sec:annex-exp2`` of the preprint
(slides/manuscript/main.tex since ticket 0524) holds the Experiment 2
technical specification. Its annex letter churned with every restructure
(C originally, B after the 0469 restructure, C again after the 0482
reorder), so this file, its tests, and its extraction are keyed on the
stable label — never the letter, the title, or the neighbouring section
(ticket 0561; label-stability contract recorded in ticket 0560).

The annex was a PRE-RUN spec snapshot: it claimed Phase B at N=3, a $10/call
dollar cap, and carried a "not yet executed" bracketed status note. That
contradicted the as-run body (§5 "Experiment 2 — SOTA frontier", which states
two arms, N=5, a 2×2 factorial) and the committed artifacts
(tab_exp2_2x2.csv, tab_exp2_bib_quality).

This adherence test pins the rewrite's load-bearing invariants:

1. No stale pre-run marker survives in the annex: "N=3", the "not yet
   executed" note, the "$10.00" status cap, "≤$10" / "≤$31" budget figures.
2. The as-run facts are present: two named arms (naive/optimised), N=5, the
   dual-axis cap (50K tokens + $3 guard), and the 2×2 / four-arm framing the
   body's Figure 3 caption forward-references.
3. The Claude-optimised 0/5 exclusion, if mentioned, names its *dimension* —
   bibliography parsability, NOT F1-scorability (the F1 cell stays N=5). A flat
   "Claude excluded" would contradict the 2×2 F1 table.

The check reads the main.tex source rather than re-deriving numbers, so it
stays fast and offline. It runs on the normalized body (line-wraps joined,
``\\$``/``\\%`` unescaped), so the markers read as plain prose.
"""

import re

import pytest
from manuscript_source import body, section

pytestmark = pytest.mark.adherence


def _exp2_annex() -> str:
    """The normalized text of the Exp2 tech-spec annex (label-keyed, 0561)."""
    return section("sec:annex-exp2")


def test_exp2_annex_exists_and_nonempty():
    annex = _exp2_annex()
    assert len(annex.strip()) > 1000, "the Exp2 annex is missing or truncated"


def test_no_stale_pre_run_markers():
    annex = _exp2_annex()
    stale = [
        "N=3",
        "not yet executed",
        "$10.00",
        "≤$10",
        "≤$31",
        "conjectured-results",
        "Δ to N=3",
    ]
    found = [marker for marker in stale if marker in annex]
    assert not found, f"stale pre-run markers still in the Exp2 annex: {found}"


def test_as_run_two_arms_and_n5():
    annex = _exp2_annex().lower()
    assert "naive" in annex, "naive arm not named"
    assert "optimised" in annex or "optimized" in annex, "optimised arm not named"
    assert "n=5" in annex, "as-run N=5 not stated"


def test_dual_axis_cap_present():
    annex = _exp2_annex()
    assert "dual-axis" in annex.lower(), "dual-axis cap framing absent"
    # The two axes, traced to protocol_05: 50K tokens + $3 guard.
    assert "50 000 tokens" in annex or "50000 tokens" in annex or "50K tokens" in annex, (
        "token axis of the cap absent"
    )
    assert "$3" in annex, "the $3 dollar guard absent"


def test_factorial_framing_present():
    annex = _exp2_annex().lower()
    # The body's Figure 3 caption forward-references this annex for the 2x2.
    assert "2×2" in annex or "2x2" in annex, "2×2 factorial framing absent"


def test_no_registration_vocabulary():
    """Ticket 0567 — Experiment 2 is presented as a plain 2×2 four-arm
    design: no pre-registration framing anywhere in the manuscript body.
    "register" as a noun (the statistical register) stays legal; the
    banned forms are matched case-sensitively, as whole words."""
    text = body()
    banned = ["pre-registered", "unregistered", "registration", "registered"]
    found = sorted(form for form in banned if re.search(rf"\b{re.escape(form)}\b", text))
    assert not found, (
        f"registration vocabulary still in the manuscript body: {found} "
        "(Experiment 2 is a plain 2×2 four-arm design, ticket 0567)"
    )


def test_claude_0_of_5_names_the_parse_dimension():
    annex = _exp2_annex()
    if "0 of 5" not in annex and "0/5" not in annex:
        pytest.skip("Claude 0/5 exclusion not mentioned in the Exp2 annex")
    lowered = annex.lower()
    # Must name the dimension (bibliography parsability), not a flat exclusion.
    assert "parseable" in lowered or "parsab" in lowered or "bibliography-parsab" in lowered, (
        "0/5 exclusion does not name the bibliography-parse dimension"
    )
    # And must distinguish from F1-scorability, which stays N=5.
    assert "f1" in lowered, "0/5 prose must reference the F1 path it does NOT exclude on"


def test_classifier_named_as_run_not_pilot():
    """The dialogue classifier paragraph must name the as-run choice.

    The pre-reroll draft named the pilot `mistral-small-latest` as *the*
    classifier and disclosed a (false, for the as-run experiment) same-vendor
    Mistral pair. As run, the production classifier was deepseek-v4-pro
    (cross-vendor with all four subjects); nemotron was the earlier-run choice.
    Guard: the as-run classifier is named, and mistral-small no longer stands
    as the classifier.
    """
    annex = _exp2_annex()
    lowered = annex.lower()
    assert "deepseek-v4-pro" in lowered, (
        "the Exp2 annex must name the as-run dialogue classifier (deepseek-v4-pro)"
    )
    # mistral-small may appear only as the pilot footnote, never as THE classifier.
    # The false same-vendor-Mistral disclosure must be gone.
    assert "both mistral models" not in lowered, (
        "stale same-vendor-Mistral classifier disclosure still in the Exp2 annex"
    )
    assert "same-vendor pair" not in lowered, (
        "stale same-vendor classifier framing still in the Exp2 annex"
    )


def test_references_report_chapter():
    annex = _exp2_annex().lower()
    assert "technical report" in annex and "chapter" in annex, (
        "the Exp2 annex must reference the technical report's Exp2 chapter for the inferential analysis"
    )
