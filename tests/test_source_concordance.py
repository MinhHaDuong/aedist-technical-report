"""Ticket 0486 — source concordance table integrity + manuscript adherence.

Two invariants:
1. The committed CSV is bidirectional (neither GEM nor the reference is a
   superset) and internally consistent (per-status sums, matched + ref-only).
2. The §4/§5/Annex-B literals in main.md are re-derived from the committed
   macros artifact (mirrors test_abstract_numbers.py / 0501 guards).
"""

import csv
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = REPO_ROOT / "data" / "reference" / "tab_source_concordance.csv"
MACROS = REPO_ROOT / "report" / "inputs" / "generated" / "macros_source_concordance.tex"
MAIN_MD = REPO_ROOT / "slides" / "manuscript" / "main.md"


def _rows() -> list[dict]:
    if not CSV_PATH.exists():
        pytest.skip(f"{CSV_PATH} not generated — run: make -f experiments/render.mk report-tables")
    return list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))


def test_concordance_table_bidirectional():
    """Neither source is a superset: both GEM-only and reference-only are non-zero."""
    rows = _rows()
    cols = set(rows[0].keys())
    assert {"status", "gem_matched", "gem_reference_only", "gem_only", "wiki_matched"} <= cols
    total = next(r for r in rows if r["status"] == "All")
    assert int(total["gem_only"]) >= 1, "GEM-only must be non-zero (GEM is not a subset of the reference)"
    assert int(total["gem_reference_only"]) >= 1, "reference-only must be non-zero (reference is not a subset of GEM)"


def test_concordance_table_internally_consistent():
    """Per-status matched + reference_only == n_reference; the All row sums the statuses."""
    rows = _rows()
    status_rows = [r for r in rows if r["status"] != "All"]
    total = next(r for r in rows if r["status"] == "All")
    for r in status_rows:
        n = int(r["n_reference"])
        assert int(r["gem_matched"]) + int(r["gem_reference_only"]) == n, f"GEM split off for {r['status']}"
        assert int(r["wiki_matched"]) + int(r["wiki_reference_only"]) == n, f"Wiki split off for {r['status']}"
    for field in ("n_reference", "gem_matched", "gem_only", "wiki_matched"):
        assert sum(int(r[field]) for r in status_rows) == int(total[field]), f"All row mis-sums {field}"


def _macro(name: str) -> str:
    if not MACROS.exists():
        pytest.skip(f"{MACROS} not generated")
    m = re.search(rf"\\newcommand{{\\{name}}}{{([^}}]+)}}", MACROS.read_text(encoding="utf-8"))
    assert m, f"\\{name} not found in {MACROS}"
    return m.group(1)


def test_manuscript_concordance_numbers_match_artifact():
    """§4/§5/Annex-B coverage literals are present and match the generated macros."""
    if not MAIN_MD.exists():
        pytest.skip("main.md not found")
    md = MAIN_MD.read_text(encoding="utf-8")
    for name in ("GemReviewed", "GemReviewedPct", "WikiReviewed", "WikiReviewedPct", "GemOnly", "GemDistinct"):
        value = _macro(name)
        # percentages appear as "89%"; counts as bare integers in the prose/table
        needle = f"{value}%" if name.endswith("Pct") else value
        assert needle in md, (
            f"concordance literal {needle} (\\{name} from {MACROS.name}) missing from main.md"
        )
