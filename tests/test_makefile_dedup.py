"""Adherence guards for Makefile cross-file de-duplication (ticket 0354).

Shared plumbing lives once in experiments/common.mk: the canonical UV_RUN, the
OpenRouter worker-drain loop, and a single self-consistency producer. These
guards fail if a divergent copy creeps back in.

Orthogonal to tests/test_makefile_dag.py (DAG completeness, ticket 0363): this
asserts de-duplication invariants, not producer coverage.
"""

import re
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent


def _makefiles() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    files = []
    for rel in out.split("\0"):
        if not rel or rel.startswith("tickets/"):
            continue
        name = rel.rsplit("/", 1)[-1]
        if name == "Makefile" or rel.endswith(".mk"):
            files.append(REPO_ROOT / rel)
    return files


def test_no_uv_run_via_home_dotclaude_env():
    """ENV POLICY: project ../.env is the only key source; never $(HOME)/.claude/.env."""
    offenders = [
        str(p.relative_to(REPO_ROOT))
        for p in _makefiles()
        if "$(HOME)/.claude/.env" in p.read_text()
    ]
    assert not offenders, (
        "makefiles loading API keys from $(HOME)/.claude/.env (use ../.env): "
        f"{offenders}"
    )


def test_uv_run_defined_once():
    """The canonical UV_RUN base is defined only in common.mk; others include it."""
    pat = re.compile(r"^UV_RUN\s*:?=", re.M)
    hits = {
        str(p.relative_to(REPO_ROOT)): len(pat.findall(p.read_text()))
        for p in _makefiles()
    }
    total = sum(hits.values())
    assert total == 1, (
        f"UV_RUN must be defined once (in experiments/common.mk); found: "
        f"{ {k: v for k, v in hits.items() if v} }"
    )


def test_worker_drain_loop_defined_once():
    """The OpenRouter drain for-loop is factored into common.mk, not copy-pasted."""
    needle = "openrouter --drain & done"
    total = sum(p.read_text().count(needle) for p in _makefiles())
    assert total == 1, (
        f"worker drain for-loop appears {total}x across makefiles; "
        "it should live once in experiments/common.mk"
    )


def test_single_self_consistency_producer():
    """Exactly one makefile recipe invokes tabulate_self_consistency."""
    needle = "aedist.tabulate_self_consistency"
    hits = {
        str(p.relative_to(REPO_ROOT)): p.read_text().count(needle)
        for p in _makefiles()
    }
    total = sum(hits.values())
    assert total == 1, (
        f"tabulate_self_consistency must have a single producer; found: "
        f"{ {k: v for k, v in hits.items() if v} }"
    )
