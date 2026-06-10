"""Ticket 0509 — arXiv re-title and front/back matter for the standalone preprint.

Asserts the manuscript carries its arXiv identity: the new (registered) title as
the H1, the Econom'IA provenance footnote, author ORCID/email, the back-matter
sections (Data & Code Availability, Funding, author contributions / conflict of
interest), and that the two stale forward-references to a non-inline 2×2 table /
to "the slides" are gone.
"""

import csv
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
MAIN_MD = REPO_ROOT / "slides" / "manuscript" / "main.md"
EXP2_2X2_CSV = REPO_ROOT / "experiments" / "derived" / "tab_exp2_2x2.csv"

NEW_TITLE_SUBSTR = "Can Frontier AI Build a Statistical Register?"

# Maps the markdown agent label to the CSV `agent` value, and the markdown
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


def _md() -> str:
    return MAIN_MD.read_text(encoding="utf-8")


def _h1_line() -> str:
    for line in _md().splitlines():
        if line.startswith("# "):
            return line
    raise AssertionError("no H1 line found in main.md")


def test_new_title_is_h1():
    """The H1 carries the new title; 'Beyond RAG' must not be the H1 title."""
    h1 = _h1_line()
    assert NEW_TITLE_SUBSTR in h1, f"new title missing from H1; got: {h1}"
    assert "Beyond RAG" not in h1, (
        "old 'Beyond RAG' title must not remain the H1 (it may survive only "
        f"inside the Econom'IA provenance footnote); got: {h1}"
    )


def test_data_and_code_availability_present():
    assert "Data & Code Availability" in _md()


def test_funding_present():
    assert re.search(r"\*\*Funding\.\*\*", _md()), "Funding back-matter section missing"


def test_orcid_present():
    assert "0000-0001-9988-2100" in _md(), "author ORCID missing"


def test_conflict_of_interest_present():
    assert "conflicts of interest" in _md(), "author conflict-of-interest disclosure missing"


def test_no_dangling_forward_references():
    md = _md()
    assert "see the 2×2 factorial table" not in md, (
        "stale forward-ref to a non-inline 2×2 table must be removed"
    )
    assert "appears in the slides" not in md, (
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


def _parse_table_rows() -> list[tuple[str, str, str, float, float]]:
    """Parse Table 1 markdown rows: (agent_label, mode, docs, f1, cost)."""
    rows: list[tuple[str, str, str, float, float]] = []
    in_table = False
    for line in _md().splitlines():
        stripped = line.strip()
        if stripped.startswith("| Agent ") and "F1 (mean)" in stripped:
            in_table = True
            continue
        if in_table:
            if not stripped.startswith("|"):
                break
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if set(cells[0]) <= {"-", " "}:  # the |---|---| separator row
                continue
            agent, mode, docs, f1, cost = cells[:5]
            rows.append((agent, mode, docs, float(f1), float(cost)))
    return rows


def test_table1_values_match_source_csv():
    """Every Table 1 cell re-derives from experiments/derived/tab_exp2_2x2.csv.

    Guards the 0452 failure mode: hand-typed manuscript numbers silently drift
    when the source CSV is regenerated. Each markdown cell is re-parsed and
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
