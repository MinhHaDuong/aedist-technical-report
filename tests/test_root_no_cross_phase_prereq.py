"""The root Makefile carries no cross-phase prerequisite edge.

Tracker 0406, step S5 (ticket 0415) rewrote the root Makefile to the ratified
shape: a developer loop (test/lint/check/...) plus EXACTLY TWO cross-phase
entries — ``make staleness`` (dry-run report of what would rebuild across
P2+P3+P4) and ``make world`` (deliberate, reviewed full re-run). Every phase
DAG lives behind ``-f``/``-C`` delegation in those two entries; the root file
itself names no generated artifact as a prerequisite.

Before S5 the root carried long P3 prerequisite lists on ``report/report.pdf``
and ``slides/slides.pdf`` and a ``$(MEASUREMENTS)`` wildcard rule — those edges
let an unrelated root target reach into the P2 scoring DAG, the seam the
phase split (tracker 0406) exists to close. This guard keeps the root free of
any such edge so the recursive ``world``/``staleness`` entries stay the single
visible path through the full DAG.

The check parses only the root ``Makefile`` (not the phase ``.mk`` files, which
legitimately carry these edges): for every rule, no prerequisite may resolve
under the P3 handoff tree (``report/inputs/generated/``), the P1/P2 derived
trees (``experiments/outputs/``, ``experiments/derived/``), or be
``measurements.jsonl``. The two recursive entries appear here as recipe
``$(MAKE)`` lines, never as prerequisite edges, so they are invisible to the
prereq scan — we assert their presence separately.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
ROOT_MAKEFILE = REPO_ROOT / "Makefile"

# A prerequisite token resolving under any of these is a cross-phase edge: a
# P2 outcome (measurements.jsonl), a P1 raw-reply / P2 derived path, or the P3
# render artifact handoff tree. Both the literal paths AND the variables the
# root historically used to name them ($(GEN) = the handoff tree,
# $(MEASUREMENTS) = measurements.jsonl) are matched, so the guard catches a
# reintroduced edge whether written as a path or behind a make variable. (The
# slides-side generated tree was retired in ticket 0408 — the one live P3 tree
# is the report-side one.)
CROSS_PHASE_PREREQ_RE = re.compile(
    r"report/inputs/generated/"
    r"|experiments/outputs/"
    r"|experiments/derived/"
    r"|(?<![\w./])measurements\.jsonl"
    r"|\$\(GEN\)"
    r"|\$\(MEASUREMENTS\)"
)


def _logical_lines(text: str) -> list[str]:
    return text.replace("\\\n", " ").splitlines()


def _rule_prereqs(text: str) -> list[tuple[str, str]]:
    """Return (target_side, prereq_side) for each rule line in the root Makefile.

    Recipe lines (TAB-indented) and variable assignments are skipped, so
    ``$(MAKE) -f experiments/...`` recipe invocations of the phase makefiles are
    never mistaken for prerequisite edges.
    """
    rules: list[tuple[str, str]] = []
    for raw in _logical_lines(text):
        if raw.startswith("\t"):
            continue
        line = raw.split("#", 1)[0]
        if not line.strip() or ":" not in line:
            continue
        # Skip variable assignments (`:=`, `?=`, `+=`, `=`).
        if re.match(r"^\s*[A-Za-z_][A-Za-z0-9_]*\s*(:=|\?=|\+=|=)", line):
            continue
        lhs, _, rhs = line.partition(":")
        rules.append((lhs.strip(), rhs.strip()))
    return rules


def test_root_makefile_exists():
    assert ROOT_MAKEFILE.is_file(), "root Makefile must exist"


def test_root_has_no_cross_phase_prereq_edge():
    text = ROOT_MAKEFILE.read_text()
    offending = []
    for target, prereqs in _rule_prereqs(text):
        if CROSS_PHASE_PREREQ_RE.search(prereqs):
            offending.append(f"  {target}: {prereqs}")
    assert not offending, (
        "Root Makefile carries a cross-phase prerequisite edge (a target whose "
        "prereqs reach into a P1/P2/P3 artifact path). The root exposes the full "
        "DAG only through the recursive `world`/`staleness` entries; per-phase "
        "rebuilds go through `-f experiments/<phase>.mk`.\n" + "\n".join(offending)
    )


def test_root_has_staleness_and_world_entries():
    text = ROOT_MAKEFILE.read_text()
    targets = {t.strip() for target, _ in _rule_prereqs(text) for t in target.split()}
    for entry in ("staleness", "world"):
        assert entry in targets, (
            f"Root Makefile must define the `{entry}` cross-phase entry "
            "(one of the two ratified DAG entries, tracker 0406 S5)."
        )
