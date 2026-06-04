"""`experiments/derived/score.mk` is the P2 (score & consolidate) phase.

Ticket 0410 (tracker 0406, step S3) consolidated all P2 scoring/extraction
into `experiments/derived/score.mk` (folding in the former P2 score makefile
and pulling the P2 verbs out of the P1 makefile, now `experiments/acquire.mk`),
leaving the P3 strays in `experiments/render.mk`. score.mk is the *consumer* of
P1 outcomes
(`experiments/outputs/**`, the raw model replies) and the *producer* of the P2
outcomes (`measurements.jsonl`, `exp2_mart.jsonl`, the cross-eval CSVs).

The invariant this guard enforces is the OTHER seam: score.mk must never reach
DOWN into P1 (acquire). A P2 scoring/extraction dry-run must not fan out
manager/worker drains, run a sweep, or call an LLM adapter — the only way to
(re)acquire raw replies is `experiments/acquire.mk`'s P1 sweep verbs, which cost
money and rewrite `experiments/outputs/**`. score.mk reads those outputs as
committed sources; it carries no rule able to rebuild them.

Mirrors the structure of ``tests/test_render_build_clean_room.py`` (S2's guard
for the P2↔P3 seam) but inverts the forbidden set: render forbids P2 verbs
because render is P3; score.mk *is* P2 and legitimately calls
``aedist.extract``, ``aedist.evaluate``, ``aedist.score_exp1``,
``aedist.score_mechanical`` etc. — so the forbidden needles here are the
ACQUIRE-side scripts only (worker, manager, run_sweep, census/regimes drains,
``query_`` adapters).

CAUTION (0383 mart staleness): these verbs must NEVER be run for real — a real
``rebuild-measurements`` destroys every ``.record.json`` and rewrites the
committed mart. This test uses ``make -n`` (dry-run) exclusively. The .PHONY
verbs wrap ``$(MAKE) -f $(THIS_MK) ...``; recursive make propagates ``-n`` to
the inner invocation, so the trace stays a dry-run end to end.
"""

import re
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
SCORE_MK = REPO_ROOT / "experiments" / "derived" / "score.mk"

# P2 verbs that drive the full score surface. Dry-running each must not reach
# down into P1 acquire.
P2_VERBS = (
    "extract",
    "evaluate-all-records",
    "measurements.jsonl",
    "rebuild-measurements",
)

# Substrings in a recipe line that prove a P1 ACQUIRE step ran: manager/worker
# drains, sweep dispatch, the census/regimes/etc. sweep modules, or an LLM
# query adapter. score.mk (P2) must never invoke any of these.
FORBIDDEN_RECIPE_NEEDLES = (
    "aedist.worker",
    "aedist.manager",
    "aedist.run_sweep",
    "aedist.query_",
    "OR_DRAIN",
    "--drain",
    "--sweep",
    "census-run",
    "census-generate",
    "regimes-run",
    "sourced-run",
    "frontier-run",
)

# A rule whose TARGET is a path under experiments/outputs/ would mean score.mk
# claims it can rebuild a P1 raw reply (re-acquisition). The P2 pattern rules
# write ``*.record.json`` SIBLINGS next to those replies — a legitimate P2
# evaluation artifact, not a re-acquisition — so .record.json targets are
# exempt. Targets are written through path variables ($(SCORE_OUTPUTS), the
# shared $(ANALYSIS_OUTPUTS_DIR)) or as literal experiments/outputs/ paths;
# match all three forms. (Mirrors render's
# test_render_mk_has_no_p2_outcome_targets — a SOURCE scan of rule-target
# lines, not a recipe-write trace, which is the ticket's wording: "no TARGET
# under experiments/outputs/".)
OUTPUTS_TARGET_RE = re.compile(
    r"\$\(SCORE_OUTPUTS\)/\S+"
    r"|\$\(ANALYSIS_OUTPUTS_DIR\)/\S+"
    r"|(?:experiments/)?outputs/\S+"
)


def _dry_run(target: str) -> str:
    # -B forces every prerequisite stale so file targets (measurements.jsonl)
    # expand their full recipe — otherwise an up-to-date mart yields an empty
    # "est à jour" trace and the scan runs over nothing (a vacuous pass), and
    # measurements.jsonl is the verb most likely to pull in scoring. -n keeps
    # it a dry-run; -Bn descends the recursive sub-makes but executes nothing
    # (0383 mart-staleness: NEVER run these verbs for real).
    result = subprocess.run(
        ["make", "-f", str(SCORE_MK), "-Bn", target],
        capture_output=True,
        text=True,
        check=True,
        cwd=REPO_ROOT,
    )
    return result.stdout


def test_score_mk_exists():
    assert SCORE_MK.is_file(), (
        "experiments/derived/score.mk must exist (P2 score rules consolidated "
        "from the former P2 score makefile + the P1 makefile (now "
        "experiments/acquire.mk) by ticket 0410, tracker 0406 step S3)."
    )


@pytest.mark.parametrize("target", P2_VERBS)
def test_p2_verb_does_not_invoke_acquire(target):
    trace = _dry_run(target)
    offending = [
        line
        for line in trace.splitlines()
        if any(needle in line for needle in FORBIDDEN_RECIPE_NEEDLES)
    ]
    assert not offending, (
        f"`make -f experiments/derived/score.mk -n {target}` invokes a P1 "
        "acquire step (worker/manager/sweep/query). score.mk (P2) consumes "
        "experiments/outputs/** as committed sources only — re-acquisition "
        "lives in experiments/acquire.mk.\n" + "\n".join(offending)
    )


def test_score_mk_has_no_outputs_rule_target():
    """score.mk may name `experiments/outputs/` paths only as prerequisites.

    A rule whose TARGET is under outputs/ would claim score.mk can re-acquire a
    P1 raw reply. The only legitimate outputs/ targets are the `.record.json`
    evaluation siblings (P2 scoring artifacts) — those are exempt. This is a
    SOURCE scan of the makefile's rule-target lines (the ticket's wording: "no
    TARGET under experiments/outputs/"), mirroring render's
    test_render_mk_has_no_p2_outcome_targets.
    """
    text = SCORE_MK.read_text()
    offending = []
    for ln in text.splitlines():
        if ln.startswith("\t") or ":" not in ln:
            continue  # recipe line or non-rule
        lhs = ln.split(":", 1)[0]
        for m in OUTPUTS_TARGET_RE.finditer(lhs):
            if m.group(0).endswith(".record.json"):
                continue  # P2 evaluation sibling — legitimate
            offending.append(ln.rstrip())
    assert not offending, (
        "score.mk declares a rule whose TARGET is an experiments/outputs/ path "
        "other than a `.record.json` sibling — that is P1 territory (raw "
        "replies). score.mk produces P2 outcomes only (measurements.jsonl, "
        "derived/**) and reads outputs/ as committed sources.\n" + "\n".join(offending)
    )
