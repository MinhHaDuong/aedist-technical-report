"""Ticket 0486 — source concordance table integrity + manuscript adherence.

Two invariants:
1. The committed CSV is bidirectional (neither GEM nor the reference is a
   superset) and internally consistent (per-status sums, matched + ref-only).
2. The §4/§5/Annex-B literals in main.tex are re-derived from the committed
   macros artifact (mirrors test_abstract_numbers.py / 0501 guards).
"""

import csv
import re
from pathlib import Path

import pytest
from manuscript_source import body, raw

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = REPO_ROOT / "data" / "reference" / "tab_source_concordance.csv"
MACROS = REPO_ROOT / "report" / "inputs" / "generated" / "macros_source_concordance.tex"
TABLE_TEX = REPO_ROOT / "report" / "inputs" / "generated" / "tab_source_concordance.tex"


def test_annex_table_is_generated_include():
    """The annex concordance table is a generated include re-derived from the CSV.

    Guards the no-hand-typed-numbers rule at the table grain (the macro guard
    below covers only the headline aggregates): every CSV row must appear as a
    tabular row in the generated .tex, and main.tex must \\input that file
    rather than carry a hand-typed table body.
    """
    assert TABLE_TEX.exists(), (
        f"{TABLE_TEX} not generated — run: make -f experiments/render.mk report-tables"
    )
    assert (
        "\\input{../../report/inputs/generated/tab_source_concordance.tex}" in raw()
    ), "main.tex must \\input the generated concordance table, not hand-type it"
    tex = TABLE_TEX.read_text(encoding="utf-8")
    for r in _rows():
        cells = [r["status"], r["n_reference"], r["gem_matched"], r["gem_only"], r["wiki_matched"]]
        if r["status"] == "All":
            cells = [f"\\textbf{{{c}}}" for c in cells]
        pattern = r"\s*&\s*".join(re.escape(c) for c in cells)
        assert re.search(pattern + r"\s*\\\\", tex), (
            f"row {r['status']!r} not re-derivable from {TABLE_TEX.name}"
        )


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
    md = body()
    for name in ("GemReviewed", "GemReviewedPct", "WikiReviewed", "WikiReviewedPct", "GemOnly", "GemDistinct"):
        value = _macro(name)
        # percentages appear as "89%"; counts as bare integers in the prose/table
        needle = f"{value}%" if name.endswith("Pct") else value
        assert needle in md, (
            f"concordance literal {needle} (\\{name} from {MACROS.name}) missing from main.tex"
        )
