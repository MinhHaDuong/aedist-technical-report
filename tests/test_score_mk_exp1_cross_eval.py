"""`experiments/derived/score.mk` — Exp1 cross-eval is a plain-file rule.

Ticket 0460 converted the `exp1_cross_eval` build from a sentinel-stamp rule
(`experiments/derived/exp1_cross_eval/.done`) to a plain-file rule on the single
known output `exp1_cross_eval.csv`. The stamp was ceremony — `score_exp1` writes
exactly one file and mkdirs its own parent — and its dedicated directory was an
orphan untracked dir (flagged at ticket 0444 close).

The conversion is only correct paired with `.DELETE_ON_ERROR`: `score_exp1`
appends, so the recipe `rm -f`s then writes; without atomicity a mid-write crash
would leave a partial CSV with a fresh mtime that Make treats as current. These
guards lock both halves so the stamp cannot creep back and atomicity cannot be
dropped.

The four `armN_flat/.done` stamps are the CORRECT idiom (dynamic multi-output,
un-enumerable filenames) and are intentionally NOT guarded against here.
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
SCORE_MK = REPO_ROOT / "experiments" / "derived" / "score.mk"
# score.mk includes ../paths.mk, where the directive now lives as the single
# source for both phases that read it (ticket 0461). A special target set in an
# included file is honoured for the whole invocation.
PATHS_MK = REPO_ROOT / "experiments" / "paths.mk"


def _score_mk_text() -> str:
    return SCORE_MK.read_text(encoding="utf-8")


def test_delete_on_error_is_set():
    """Atomicity: a crashed recipe must not leave a stale-but-fresh artifact.

    Since ticket 0461 the directive lives in the included ../paths.mk (single
    source for score.mk + render.mk), not literally in score.mk. We assert the
    guarantee is in force for the score phase regardless of which of the two
    files carries it. The whole-class guard is test_makefile_delete_on_error.py.
    """
    in_force = (
        ".DELETE_ON_ERROR:" in _score_mk_text()
        or ".DELETE_ON_ERROR:" in PATHS_MK.read_text(encoding="utf-8")
    )
    assert in_force, (
        "the score phase must have .DELETE_ON_ERROR in force (in score.mk or in "
        "the ../paths.mk it includes) so a recipe that crashes mid-write (e.g. "
        "score_exp1 appending to exp1_cross_eval.csv) does not leave a partial "
        "output with a current mtime"
    )


def test_exp1_cross_eval_is_plain_file_rule():
    """The CSV itself is a rule target, not a stamp side-effect."""
    text = _score_mk_text()
    # A rule line whose target resolves to exp1_cross_eval.csv. The makefile
    # uses the $(ANALYSIS_EXP1_CROSS_EVAL_CSV) variable; accept either the
    # variable-form target or the literal basename as a rule target.
    has_csv_target = any(
        line.lstrip().startswith(("$(ANALYSIS_EXP1_CROSS_EVAL_CSV):",))
        or "exp1_cross_eval.csv:" in line
        for line in text.splitlines()
    )
    assert has_csv_target, (
        "score.mk must declare exp1_cross_eval.csv as a plain-file rule target"
    )


def test_no_exp1_cross_eval_stamp():
    """The stamp + its orphan directory must be gone for good."""
    assert "exp1_cross_eval/.done" not in _score_mk_text(), (
        "exp1_cross_eval must not be keyed on a .done stamp — it has a single "
        "known output; the stamp's directory was an orphan untracked dir"
    )
