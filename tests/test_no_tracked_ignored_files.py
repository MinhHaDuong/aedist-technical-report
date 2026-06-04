"""No file may be tracked and ignore-matched at the same time.

The phase-stratified artifact policy (ticket 0405, docs/pipeline-phases.md)
classifies every generated file as either a phase OUTCOME (tracked) or an
intra-phase INTERMEDIATE (ignored). A file that is both committed AND matched
by a .gitignore pattern is a dead-letter ambiguity: the ignore line claims the
file is regenerable while the index keeps it as durable state. Reconciling the
two is the whole point of the policy.

`git ls-files -i -c --exclude-standard` lists exactly those ambiguous files
(tracked in the index `-c`, matched by the standard ignore set `-i`). It must
stay empty so a file can never again be tracked and ignore-matched at once.
"""

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_no_tracked_ignored_files():
    result = subprocess.run(
        ["git", "ls-files", "-i", "-c", "--exclude-standard"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    offending = [line for line in result.stdout.splitlines() if line.strip()]
    assert not offending, (
        f"{len(offending)} file(s) are both tracked and gitignore-matched "
        "(dead-letter artifact ambiguity). Classify each per "
        "docs/pipeline-phases.md: a phase OUTCOME needs its ignore line "
        "negated/removed; an intra-phase INTERMEDIATE needs `git rm --cached` "
        "(keep the working-tree copy and the ignore line).\n" + "\n".join(offending)
    )
