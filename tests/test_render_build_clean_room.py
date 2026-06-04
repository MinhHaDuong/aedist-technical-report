"""`experiments/render.mk` is the P3 (render) phase — it never regenerates P2.

Ticket 0409 (tracker 0406, step S2) split every render rule out of
`experiments/analysis.mk` into `experiments/render.mk`, so a figure/table/view
build can no longer trigger the scoring/extraction cascade that produced the
2026-06-03 mart staleness incident (ticket 0383).

render.mk consumes committed P2 outcomes (``measurements.jsonl``,
``experiments/derived/exp2_mart.jsonl``, the cross-eval CSVs,
``experiments/outputs/**``) as *sources* — they appear only as prerequisites,
never as targets, and render.mk carries no rule able to rebuild them. Their
absence must be a hard "No rule to make target" error, never a silent rebuild.

This adherence test dry-runs each P3 aggregate target through render.mk and
asserts the recipe trace contains:

* no P2 scoring/extraction/acquire invocation — ``aedist.build_exp2_mart``
  (the standalone mart builder, *not* ``build_exp2_mart_views``, which is the
  P3 projection and is explicitly allowed), ``extract_``, ``evaluate_``,
  ``score_``, worker drains, or ``query_`` adapters; and
* no *target* path under a P2 outcome location (``exp2_mart.jsonl``, the
  cross-eval CSVs, ``experiments/outputs/``).

The needles are deliberately precise: ``aedist.build_exp2_mart `` (with the
trailing space) matches the mart builder module invocation but not
``aedist.build_exp2_mart_views``; ``--output .*exp2_mart.jsonl`` catches any
rule writing the mart.
"""

import re
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
RENDER_MK = REPO_ROOT / "experiments" / "render.mk"

# P3 aggregate targets that drive the full render surface.
P3_AGGREGATE_TARGETS = (
    "exp2-analysis-report",
    "exp1-analysis-figures",
    "report-tables",
    "report-figures",
    "chart-figures",
)

# Substrings in a recipe line that prove a P2 (score/extract/acquire) step ran.
# build_exp2_mart_views is the P3 projection and is explicitly NOT forbidden.
FORBIDDEN_RECIPE_NEEDLES = (
    "aedist.build_exp2_mart ",  # trailing space: mart builder, not _views
    "aedist.extract_",
    "aedist.evaluate_",
    "aedist.score_",
    "aedist.run_worker",
    "aedist.query_",
)

# A recipe writing to one of these is regenerating a P2 outcome.
FORBIDDEN_OUTPUT_RE = re.compile(
    r"--output\S*\s+\S*(?:exp2_mart\.jsonl|sota_cross_eval\.csv|exp1_cross_eval\.csv)"
)

# A rule target (left of ':' in `make -p`/`-n` is not exposed; instead we scan
# the makefile source for targets under P2 outcome paths).
P2_OUTCOME_TARGET_RE = re.compile(
    r"^\s*\$\(ANALYSIS_EXP2_MART_JSONL\)\s*:"
    r"|^\s*\$\(ANALYSIS_EXP2_CROSS_EVAL_CSV\)\s*:"
    r"|^\s*\$\(ANALYSIS_EXP1_CROSS_EVAL_CSV\)\s*:"
    r"|experiments/outputs/\S*\s*:"
    r"|experiments/derived/\S*exp2_mart\.jsonl\s*:",
    re.MULTILINE,
)


def _dry_run(target: str) -> str:
    result = subprocess.run(
        ["make", "-f", str(RENDER_MK), "-n", target],
        capture_output=True,
        text=True,
        check=True,
        cwd=REPO_ROOT,
    )
    return result.stdout


def test_render_mk_exists():
    assert RENDER_MK.is_file(), (
        "experiments/render.mk must exist (P3 render rules extracted from "
        "analysis.mk by ticket 0409)."
    )


@pytest.mark.parametrize("target", P3_AGGREGATE_TARGETS)
def test_p3_target_does_not_invoke_p2_scoring(target):
    trace = _dry_run(target)
    offending = []
    for line in trace.splitlines():
        if "build_exp2_mart_views" in line:
            continue  # the P3 projection — allowed
        if any(needle in line for needle in FORBIDDEN_RECIPE_NEEDLES):
            offending.append(line)
        if FORBIDDEN_OUTPUT_RE.search(line):
            offending.append(line)
    assert not offending, (
        f"`make -f experiments/render.mk -n {target}` regenerates a P2 outcome "
        "(scoring/extraction). render.mk must consume committed P2 outcomes as "
        "sources only.\n" + "\n".join(offending)
    )


def test_render_mk_has_no_p2_outcome_targets():
    """render.mk may name P2 outcomes only as prerequisites, never as targets."""
    text = RENDER_MK.read_text()
    rule_lines = [ln for ln in text.splitlines() if not ln.startswith("\t") and ":" in ln]
    offending = [ln for ln in rule_lines if P2_OUTCOME_TARGET_RE.search(ln + "\n")]
    assert not offending, (
        "render.mk declares a rule whose target is a P2 outcome (mart / "
        "cross-eval / experiments outputs). Those rules belong in analysis.mk; "
        "render.mk references them only as prerequisites.\n" + "\n".join(offending)
    )


def test_render_mk_views_rule_is_present():
    """The mart→view projection (P3) lives in render.mk, not analysis.mk."""
    text = RENDER_MK.read_text()
    assert "build_exp2_mart_views" in text, (
        "render.mk must carry the ANALYSIS_EXP2_MART_VIEWS projection rule "
        "(views are render-time shaping, P3)."
    )
