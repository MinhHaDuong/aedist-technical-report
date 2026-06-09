"""Ticket 0494 — Wikipedia recall bar: two-regime invariant + manuscript adherence.

The bar's scientific claim is the two-regime split: the built fleet is well
covered by the author-seeded Wikipedia lists (high bar — scoring below it is
failing to retrieve knowledge demonstrably in the training corpus), while the
forward-looking pipeline is barely covered (the reference's unique
contribution). The first test pins that claim to the committed artifact; the
adherence test re-derives the prose literals from it.
"""

import csv
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = REPO_ROOT / "data" / "reference" / "tab_wikipedia_recall_bar.csv"
MAIN_MD = REPO_ROOT / "slides" / "manuscript" / "main.md"

BUILT = ("operating", "construction", "permitted")
PIPELINE = ("proposed", "announced")


def _rows() -> list[dict]:
    if not CSV_PATH.exists():
        pytest.skip(f"{CSV_PATH} not generated — run: make -f experiments/render.mk report-tables")
    return list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))


def test_wikipedia_bar_table_has_two_regimes():
    """Built-fleet coverage is high, pipeline coverage low — on real data."""
    rows = _rows()
    by = {r["status"]: float(r["coverage"]) for r in rows}
    built = sum(by[s] for s in BUILT) / len(BUILT)
    pipeline = sum(by[s] for s in PIPELINE) / len(PIPELINE)
    assert built > 0.85, f"built-fleet mean {built:.2f} — the high-bar regime no longer holds"
    assert pipeline < 0.6, f"pipeline mean {pipeline:.2f} — the low-bar regime no longer holds"


def test_recall_bar_consistent_with_concordance():
    """The bar's All row equals the concordance's Wikipedia totals (same machinery)."""
    rows = _rows()
    total = next(r for r in rows if r["status"] == "All")
    conc_path = REPO_ROOT / "data" / "reference" / "tab_source_concordance.csv"
    if not conc_path.exists():
        pytest.skip(f"{conc_path} not generated")
    conc_total = next(r for r in csv.DictReader(conc_path.open(encoding="utf-8")) if r["status"] == "All")
    assert int(total["covered"]) == int(conc_total["wiki_matched"])
    assert int(total["n_reference"]) == int(conc_total["n_reference"])


def test_manuscript_recall_bar_numbers_match_artifact():
    """§4/§7 two-regime literals are re-derived from the committed artifact."""
    if not MAIN_MD.exists():
        pytest.skip("main.md not found")
    md = MAIN_MD.read_text(encoding="utf-8")
    rows = _rows()
    by = {r["status"]: float(r["coverage"]) for r in rows}
    built = sum(by[s] for s in BUILT) / len(BUILT)
    pipeline = sum(by[s] for s in PIPELINE) / len(PIPELINE)
    operating = by["operating"]
    for value, what in (
        (built, "built-fleet mean"),
        (pipeline, "pipeline mean"),
        (operating, "operating coverage"),
    ):
        needle = f"{round(value * 100)}%"
        assert needle in md, (
            f"recall-bar literal {needle} ({what}, from {CSV_PATH.name}) missing from main.md"
        )
