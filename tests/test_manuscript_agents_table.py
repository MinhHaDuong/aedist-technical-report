"""Ticket 0584 — Annex B agents table: drop Country column, fix Qwen version.

The Annex B "Agents" longtable (under ``\\subsection*{Agents}`` in
``slides/manuscript/main.tex``) lists the four cloud agents used in
Experiment 2. Two adherence invariants are pinned here:

1. **Structural** — the table has no "Country" column. The country facts are
   stated inline in the §6 prose; the table column was redundant and was
   dropped (the remaining columns size naturally, no fixed ``\\real{0.20}``
   widths).

2. **Artifact-derived model identity** — the Exp 2 Qwen agent is the
   ``qwen3.7-max-2026-05-20`` entry in ``experiments/models.yaml`` (and the
   ``"model": "qwen3.7-max-2026-05-20"`` recorded in the Exp 3/sota run
   records). The manuscript must name it with the version the artifact
   attests (``Qwen3.7 Max``), never the stale ``Qwen3-Max``. The expected
   display token is *re-derived from models.yaml*, so a future version bump
   in the registry cannot leave this guard silently stale (project rule:
   derive prose from artifacts, never from memory).
"""

import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
MANUSCRIPT = REPO_ROOT / "slides" / "manuscript" / "main.tex"
REPORT = REPO_ROOT / "report" / "report.tex"
MODELS_PATH = REPO_ROOT / "experiments" / "models.yaml"

# The models.yaml slug for the Exp 2 Qwen agent (cross-checked against the
# sota run records: ``"model": "qwen3.7-max-2026-05-20"``).
EXP2_QWEN_SLUG = "qwen3.7-max-2026-05-20"


def _agents_table() -> str:
    """The ``\\begin{longtable}...\\end{longtable}`` block whose header lists
    the agent columns (# / Vendor / Model / Surface)."""
    text = MANUSCRIPT.read_text(encoding="utf-8")
    for m in re.finditer(r"\\begin\{longtable\}.*?\\end\{longtable\}", text, re.DOTALL):
        block = m.group(0)
        if "Vendor" in block and "Surface" in block:
            return block
    raise AssertionError("agents longtable (Vendor/Surface header) not found in main.tex")


def _expected_qwen_display() -> str:
    """Re-derive the human display token (``Qwen3.7 Max``) from the model
    slug in models.yaml, so the manuscript value tracks the registry."""
    models = yaml.safe_load(MODELS_PATH.read_text(encoding="utf-8"))
    entry = next((e for e in models if e.get("name") == EXP2_QWEN_SLUG), None)
    assert entry is not None, (
        f"Exp 2 Qwen slug {EXP2_QWEN_SLUG!r} no longer in models.yaml — "
        "the manuscript agents table must track the registry; update both."
    )
    # slug 'qwen3.7-max-2026-05-20' -> version 'qwen3.7', kind 'max'
    version, kind = entry["name"].split("-", 2)[:2]
    return f"{version.capitalize()} {kind.capitalize()}"


def test_agents_table_no_country_column():
    """The agents table dropped the Country column."""
    block = _agents_table()
    header = block.split("\\midrule", 1)[0]
    assert "Country" not in header, (
        "agents table still has a Country column — ticket 0584 dropped it "
        "(country facts stay inline in the §6 prose)"
    )


def test_agents_table_widths_not_fixed_equal():
    """Column widths size naturally — the five forced-equal ``\\real{0.2000}``
    colspecs were removed."""
    block = _agents_table()
    colspec = block.split("\\toprule", 1)[0]
    assert "\\real{0.2000}" not in colspec, (
        "agents table colspec still forces equal 0.20 widths — ticket 0584 "
        "switched to natural column widths"
    )


def test_qwen_version_matches_models_yaml():
    """The Qwen agent is named with the version models.yaml attests."""
    expected = _expected_qwen_display()  # 'Qwen3.7 Max'
    block = _agents_table()
    assert expected in block, (
        f"agents table does not name the Qwen agent {expected!r} (the version "
        f"derived from models.yaml slug {EXP2_QWEN_SLUG!r})"
    )


def test_no_stale_qwen_version_in_manuscript():
    """Negative guard: the stale ``Qwen3-Max`` string must not appear anywhere
    in the manuscript (the artifact says 3.7, not 3)."""
    text = MANUSCRIPT.read_text(encoding="utf-8")
    assert "Qwen3-Max" not in text, (
        "stale 'Qwen3-Max' string present in main.tex — the Exp 2 Qwen agent "
        f"is {EXP2_QWEN_SLUG!r} (Qwen3.7 Max) per models.yaml and the run records"
    )


def test_no_stale_qwen_version_in_report():
    """Negative guard (ticket 0594): the stale ``Qwen3-Max`` string must not
    appear in the French report either — same defect class as main.tex, same
    artifact ground truth (``Qwen3.7 Max`` per models.yaml slug
    ``qwen3.7-max-2026-05-20``)."""
    text = REPORT.read_text(encoding="utf-8")
    assert "Qwen3-Max" not in text, (
        "stale 'Qwen3-Max' string present in report/report.tex — the Exp 2 "
        f"Qwen agent is {EXP2_QWEN_SLUG!r} (Qwen3.7 Max) per models.yaml and "
        "the run records"
    )
