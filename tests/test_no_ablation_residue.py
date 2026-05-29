"""No residue of the retired modular prompt-composition ablation (ticket 0361).

§Exp3 (`report/inputs/plan_ablation.tex`, `sec:exp3`) is the modular
prompt-composition / ablation experiment: designed, never run, pilot
invalidated. 0361 deletes it and the stale Exp1 census figure, salvaging the
live verification framing into the manuscript. These guards fail if any
residue of the dead experiment survives in the live tree.

Scan covers the live build inputs only — report/slides .tex, the root Makefile,
and src/aedist/*.py — not tests/ (this file names the tokens as literals) and
not archived material.
"""

import re
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent

# Tokens that must not survive anywhere in the live build tree once 0361 lands.
FORBIDDEN_TOKENS = (
    "sec:exp3",
    "plan_ablation",
    "base_vs_census",
    "fig_ablation_",
    "plot_ablation",
    "models_ablation",
)


def _live_build_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    files: list[Path] = []
    for rel in out.split("\0"):
        if not rel:
            continue
        keep = (
            (rel.startswith("report/") and rel.endswith(".tex"))
            or (rel.startswith("slides/") and rel.endswith(".tex"))
            or rel == "Makefile"
            or (rel.startswith("src/aedist/") and rel.endswith(".py"))
        )
        if keep:
            files.append(REPO_ROOT / rel)
    return files


def test_no_ablation_residue_tokens():
    violations = []
    for f in _live_build_files():
        text = f.read_text()
        violations.extend(
            f"{f.relative_to(REPO_ROOT)} :: {tok}"
            for tok in FORBIDDEN_TOKENS
            if tok in text
        )
    assert not violations, (
        "retired-ablation residue in the live build tree:\n"
        + "\n".join(f"  {v}" for v in violations)
    )


def test_exactly_one_experience_3_heading():
    """The zombie §Exp3 and RAG-wholesale §Exp3 both render 'Expérience 3'.

    Deleting plan_ablation.tex must leave exactly one across all report .tex.
    """
    heading = re.compile(r"\\(?:sub)*section\{[^}]*Exp[ée]rience[~ ]*3")
    hits = []
    for f in _live_build_files():
        if not (str(f).startswith(str(REPO_ROOT / "report")) and f.suffix == ".tex"):
            continue
        for i, line in enumerate(f.read_text().splitlines(), 1):
            if heading.search(line):
                hits.append(f"{f.relative_to(REPO_ROOT)}:{i}")
    assert len(hits) == 1, (
        f"expected exactly one 'Expérience 3' heading in report .tex, "
        f"found {len(hits)}: {hits}"
    )
