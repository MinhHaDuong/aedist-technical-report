"""Ticket 0509 — arXiv re-title and front/back matter for the standalone preprint.

Asserts the manuscript (main.tex since ticket 0524) carries its arXiv identity:
the new (registered) title in \\title{}, the Econom'IA provenance footnote,
author ORCID/email, the back-matter sections (Data & Code Availability,
Funding, author contributions / conflict of interest), and that the two stale
forward-references to a non-inline 2×2 table / to "the slides" are gone.
"""

import csv
from pathlib import Path

import pytest
from manuscript_source import body, raw, title

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
EXP2_2X2_CSV = REPO_ROOT / "experiments" / "derived" / "tab_exp2_2x2.csv"

NEW_TITLE_SUBSTR = "Can Frontier AI Build a Statistical Register?"

# Maps the table agent label to the CSV `agent` value, and the table
# query-mode/documents cell pair to the CSV (`arm`, `docs`) key. The CSV uses
# arm names (naive/optimised/arm3/arm4); the table re-labels them by the 2×2
# factors it presents (query mode × documents).
_AGENT_LABEL_TO_CSV = {
    "Anthropic": "anthropic",
    "Mistral": "mistral",
    "OpenAI": "openai",
    "Qwen": "qwen",
}
_CELL_TO_CSV_ARM = {
    ("naive (single-shot)", "no"): "naive",
    ("optimised (multi-turn)", "no"): "optimised",
    ("naive (single-shot)", "yes"): "arm3",
    ("optimised (multi-turn)", "yes"): "arm4",
}


def test_new_title_present():
    """\\title{} carries the new title; 'Beyond RAG' must not be the title."""
    t = title()
    assert NEW_TITLE_SUBSTR in t, f"new title missing from \\title{{}}; got: {t}"
    # The Econom'IA provenance footnote (\thanks) legitimately cites the old
    # talk title; strip it before asserting the headline title.
    headline = t.split("\\thanks", 1)[0]
    assert "Beyond RAG" not in headline, (
        "old 'Beyond RAG' title must not remain the headline title (it may "
        f"survive only inside the Econom'IA provenance footnote); got: {headline}"
    )


def test_econom_ia_provenance_footnote():
    assert "Econom'IA 2026" in title(), "Econom'IA provenance footnote missing from title"


def test_data_and_code_availability_present():
    assert "Data & Code Availability" in body()


def test_funding_present():
    assert "\\textbf{Funding.}" in body(), "Funding back-matter section missing"


def test_orcid_present():
    # The ORCID lives in the \\author{} block of the preamble.
    assert "0000-0001-9988-2100" in raw(), "author ORCID missing"


def test_conflict_of_interest_present():
    assert "conflicts of interest" in body(), "author conflict-of-interest disclosure missing"


def test_no_dangling_forward_references():
    text = body()
    assert "see the 2×2 factorial table" not in text, (
        "stale forward-ref to a non-inline 2×2 table must be removed"
    )
    assert "appears in the slides" not in text, (
        "standalone paper must not forward-reference 'the slides'"
    )


def _csv_lookup() -> dict[tuple[str, str, str], tuple[float, float]]:
    """(agent, arm, docs) -> (f1_mean, cost_mean) parsed from the source CSV."""
    out: dict[tuple[str, str, str], tuple[float, float]] = {}
    with EXP2_2X2_CSV.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            key = (row["agent"], row["arm"], row["docs"])
            out[key] = (float(row["f1_mean"]), float(row["cost_mean"]))
    return out


AGENTS_TABLE_TEX = REPO_ROOT / "report" / "inputs" / "generated" / "tab_exp2_2x2_agents.tex"


def _parse_table_rows() -> list[tuple[str, str, str, float, float]]:
    """Parse Table 1 rows from the generated include (ticket 0547):
    (agent_label, mode, docs, f1, cost)."""
    rows: list[tuple[str, str, str, float, float]] = []
    for line in AGENTS_TABLE_TEX.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.endswith("\\\\"):
            continue
        cells = [c.strip() for c in line[:-2].split("&")]
        if len(cells) < 5 or cells[0] == "Agent":
            continue
        agent, mode, docs, f1, cost = cells[:5]
        rows.append((agent, mode, docs, float(f1), float(cost)))
    return rows


def test_table1_is_generated_include():
    """Table 1 is a generated include, not a hand-typed longtable (ticket 0547)."""
    assert AGENTS_TABLE_TEX.exists(), (
        f"{AGENTS_TABLE_TEX} not generated — run: make -f experiments/render.mk exp2-analysis-report"
    )
    assert "\\input{../../report/inputs/generated/tab_exp2_2x2_agents.tex}" in raw(), (
        "main.tex must \\input the generated 2x2 agents table, not hand-type it"
    )


def test_table1_values_match_source_csv():
    """Every Table 1 cell re-derives from experiments/derived/tab_exp2_2x2.csv.

    Guards the 0452 failure mode: hand-typed manuscript numbers silently drift
    when the source CSV is regenerated. Each table cell is re-parsed and
    compared (to the table's 2-decimal precision) against the CSV.
    """
    csv_data = _csv_lookup()
    table_rows = _parse_table_rows()
    assert len(table_rows) == 16, f"expected 16 Table 1 data rows, got {len(table_rows)}"
    for agent_label, mode, docs, f1_md, cost_md in table_rows:
        csv_agent = _AGENT_LABEL_TO_CSV[agent_label]
        csv_arm = _CELL_TO_CSV_ARM[(mode, docs)]
        f1_csv, cost_csv = csv_data[(csv_agent, csv_arm, docs)]
        assert round(f1_csv, 2) == f1_md, (
            f"{agent_label} {mode} docs={docs}: F1 {f1_md} != CSV {round(f1_csv, 2)}"
        )
        assert round(cost_csv, 2) == cost_md, (
            f"{agent_label} {mode} docs={docs}: cost {cost_md} != CSV {round(cost_csv, 2)}"
        )
