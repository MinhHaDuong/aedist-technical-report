"""Adherence tests for data/capability_timeline.csv."""

import csv
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

DATA = Path(__file__).parent.parent / "data" / "capability_timeline.csv"
FOCUS_LABS = {"Anthropic", "OpenAI", "Mistral", "Alibaba", "DeepSeek"}


def _rows() -> list[dict[str, str]]:
    with DATA.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_no_tbd_in_focus_panel():
    """No TBD source_kind cells remain for the five Exp 1 labs."""
    rows = _rows()
    tbd = [r for r in rows if r["lab"] in FOCUS_LABS and r["source_kind"] == "TBD"]
    assert tbd == [], f"unresolved TBD cells: {tbd}"
