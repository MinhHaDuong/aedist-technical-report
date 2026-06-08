"""Ticket 0433 — main.md Annex C rewritten to the as-run Exp2 story.

Annex C of the preprint (slides/manuscript/main.md) was a PRE-RUN spec
snapshot: it claimed Phase B at N=3, a $10/call dollar cap, and carried a
"not yet executed" bracketed status note. That contradicted the as-run body
(§4 "Experiment 2 — SOTA frontier", which states two arms, N=5, a 2×2
factorial) and the committed artifacts (tab_exp2_2x2.csv, tab_exp2_bib_quality).

This adherence test pins the rewrite's load-bearing invariants:

1. No stale pre-run marker survives in Annex C: "N=3", the "not yet executed"
   note, the "$10.00" status cap, "≤$10" / "≤$31" budget figures.
2. The as-run facts are present: two named arms (naive/optimised), N=5, the
   dual-axis cap (50K tokens + $3 guard), and the 2×2 / four-arm framing the
   body's Figure 3 caption forward-references.
3. The Claude-optimised 0/5 exclusion, if mentioned, names its *dimension* —
   bibliography parsability, NOT F1-scorability (the F1 cell stays N=5). A flat
   "Claude excluded" would contradict the 2×2 F1 table.

The check reads main.md source rather than re-deriving numbers, so it stays
fast and offline.
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
MAIN_MD = REPO_ROOT / "slides" / "manuscript" / "main.md"


def _annex_c() -> str:
    """The text of Annex C — from its heading up to the next top-level heading."""
    text = MAIN_MD.read_text(encoding="utf-8")
    start = text.index("## Annex C — Experiment 2: Technical specification")
    rest = text[start:]
    nxt = rest.index("\n## Annex D", 1)
    return rest[:nxt]


def test_annex_c_exists_and_nonempty():
    annex = _annex_c()
    assert len(annex.strip()) > 1000, "Annex C is missing or truncated"


def test_no_stale_pre_run_markers():
    annex = _annex_c()
    stale = [
        "N=3",
        "not yet executed",
        "$10.00",
        r"≤\$10",
        r"≤\$31",
        "conjectured-results",
        "Δ to N=3",
    ]
    found = [marker for marker in stale if marker in annex]
    assert not found, f"stale pre-run markers still in Annex C: {found}"


def test_as_run_two_arms_and_n5():
    annex = _annex_c().lower()
    assert "naive" in annex, "naive arm not named"
    assert "optimised" in annex or "optimized" in annex, "optimised arm not named"
    assert "n=5" in annex, "as-run N=5 not stated"


def test_dual_axis_cap_present():
    annex = _annex_c()
    assert "dual-axis" in annex.lower(), "dual-axis cap framing absent"
    # The two axes, traced to protocol_05: 50K tokens + $3 guard.
    assert "50 000 tokens" in annex or "50000 tokens" in annex or "50K tokens" in annex, (
        "token axis of the cap absent"
    )
    assert r"\$3" in annex, "the $3 dollar guard absent"


def test_factorial_framing_present():
    annex = _annex_c().lower()
    # The body's Figure 3 caption forward-references Annex C for the 2x2.
    assert "2×2" in annex or "2x2" in annex, "2×2 factorial framing absent"
    assert "exploratory" in annex, "the unregistered with-docs arms not labelled exploratory"


def test_preregistration_named():
    annex = _annex_c().lower()
    assert "pre-registered" in annex or "registration" in annex or "registered" in annex, (
        "Annex C does not disclose the preregistration"
    )


def test_claude_0_of_5_names_the_parse_dimension():
    annex = _annex_c()
    if "0 of 5" not in annex and "0/5" not in annex:
        pytest.skip("Claude 0/5 exclusion not mentioned in Annex C")
    lowered = annex.lower()
    # Must name the dimension (bibliography parsability), not a flat exclusion.
    assert "parseable" in lowered or "parsab" in lowered or "bibliography-parsab" in lowered, (
        "0/5 exclusion does not name the bibliography-parse dimension"
    )
    # And must distinguish from F1-scorability, which stays N=5.
    assert "f1" in lowered, "0/5 prose must reference the F1 path it does NOT exclude on"


def test_references_report_chapter():
    annex = _annex_c().lower()
    assert "technical report" in annex and "chapter" in annex, (
        "Annex C must reference the technical report's Exp2 chapter for the registered analysis"
    )
