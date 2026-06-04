"""Handoff-artifact guard for slides manuscript prereqs.

The slides sub-make (`slides/Makefile`) consumes
`$(LOCAL_ROOT_REPORT_GEN)/fig_capability_dag.pdf` as a manuscript prereq.
After ticket 0370, the writing build is clean-room: no producing recipe
exists in the writing-side Makefiles. The file must be a committed handoff
artifact. The producer rule lives in `experiments/render.mk` (the P3 render
phase, split out by ticket 0409).

This is the adherence companion to tickets 0367 and 0370.
"""

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.adherence
def test_fig_capability_dag_is_committed_artifact():
    """fig_capability_dag.pdf must be tracked in git as a handoff artifact."""
    result = subprocess.run(
        ["git", "ls-files", "report/inputs/generated/fig_capability_dag.pdf"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.stdout.strip(), (
        "report/inputs/generated/fig_capability_dag.pdf is not tracked by git — "
        "regenerate via `make -f experiments/render.mk chart-figures` "
        "then `git add -f` and commit."
    )
