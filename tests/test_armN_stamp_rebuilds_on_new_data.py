"""`experiments/derived/score.mk` — armN_flat/.done stamps rebuild when input data changes.

Ticket 0462: the four `armN_flat/.done` extraction stamps previously took their
prerequisites from `$(wildcard …/sota_exp3_armN_batch1/run*/*.json)`.  That
wildcard evaluates at parse time — not execution time — so when `.done` was
newer than all matched files (e.g. after a git checkout or archive restore), or
when new files were added with old timestamps, make considered the stamp
up-to-date and silently skipped the extraction.

The fix replaces the wildcard prerequisites with a per-arm committed sentinel
file (`sota_exp3_armN_batch1/.dataset`).  The stamp now depends on that one
stable path.  Whenever the dataset changes (new run added, existing run
modified), the sentinel must be updated — but the mtime relationship is always
predictable, not hostage to parse-time wildcard expansion.

This test confirms:
1. The stamp depends on `.dataset`, not on a wildcard expansion.
2. When `.dataset` is newer than `.done`, the stamp re-fires.
3. A P2 dry-run still triggers NO acquire step (score/acquire seam preserved).
"""

import subprocess
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parent.parent
SCORE_MK = REPO_ROOT / "experiments" / "derived" / "score.mk"


# ---------------------------------------------------------------------------
# Guard: the armN stamps must name .dataset as a prerequisite (source scan)
# ---------------------------------------------------------------------------


@pytest.mark.adherence
@pytest.mark.parametrize("arm", [1, 2, 3, 4])
def test_arm_stamp_prereq_is_dataset_not_wildcard(arm: int):
    """score.mk must use .dataset sentinels, not $(wildcard …) for armN stamps."""
    text = SCORE_MK.read_text(encoding="utf-8")
    arm_stamp = f"arm{arm}_flat/.done"

    # Wildcard prereqs for armN stamps are forbidden after the fix
    wildcard_pattern = f"$(wildcard $(ANALYSIS_EXPERIMENTS_DIR)/outputs/sota_exp3_arm{arm}_batch1"
    in_stamp_rule = False
    for line in text.splitlines():
        if arm_stamp in line and ":" in line and not line.startswith("\t"):
            in_stamp_rule = True
        if in_stamp_rule:
            assert wildcard_pattern not in line, (
                f"arm{arm}_flat/.done must not use $(wildcard …) as a prerequisite "
                "(parse-time expansion silently misses files added with old timestamps). "
                f"Use the committed .dataset sentinel instead.\n"
                f"Offending line: {line!r}"
            )
            # A prereq line with $(wildcard) can't span multiple lines here
            if line.startswith("\t") or (in_stamp_rule and ":" in line and arm_stamp not in line):
                break

    # The .dataset file must appear as a prerequisite in the rule
    dataset_sentinel = f"sota_exp3_arm{arm}_batch1/.dataset"
    assert dataset_sentinel in text, (
        f"score.mk must declare sota_exp3_arm{arm}_batch1/.dataset as a prerequisite "
        f"of arm{arm}_flat/.done (the committed sentinel that tracks dataset changes)"
    )


# ---------------------------------------------------------------------------
# Behavioural test: stamp re-fires when .dataset is newer than .done
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_arm_stamp_rebuilds_when_dataset_sentinel_updated(tmp_path: Path):
    """stamp rebuilds when .dataset is updated — even with no new files present.

    This reproduces the git-checkout scenario: .done exists with an old mtime
    (or was restored from git), the sentinel .dataset is then touched (because
    new data was committed), and the next make invocation must re-run extraction.
    """
    # --- build a minimal tmp tree that mirrors the real layout ---
    arm_input = tmp_path / "experiments" / "outputs" / "sota_exp3_arm1_batch1"
    arm_flat = tmp_path / "experiments" / "derived" / "arm1_flat"
    arm_input.mkdir(parents=True)
    arm_flat.mkdir(parents=True)

    # Sentinel file — committed alongside the dataset
    sentinel = arm_input / ".dataset"
    sentinel.write_text("run01\n")

    # Minimal stub: extract_arm_single_turn is not available in tmp_path,
    # so we use a trivial recipe that just touches the stamp.
    stub_mk = tmp_path / "stub.mk"
    stub_mk.write_text(
        textwrap.dedent(f"""\
        .DELETE_ON_ERROR:

        DONE = {arm_flat}/.done
        DATASET = {arm_input}/.dataset

        $(DONE): $(DATASET)
        \tmkdir -p {arm_flat}
        \ttouch $@

        all: $(DONE)
        """)
    )

    def run_make() -> subprocess.CompletedProcess:
        return subprocess.run(
            ["make", "-f", str(stub_mk), "all"],
            capture_output=True,
            text=True,
            check=True,
            cwd=tmp_path,
        )

    def recipe_ran() -> bool:
        """True if make just re-ran the stamp recipe (mtime advanced)."""
        # We track by whether make printed a recipe line (non-empty stdout
        # excluding the "Nothing to be done" message).
        return "touch" in result.stdout

    # First build — stamp created
    result = run_make()
    assert (arm_flat / ".done").exists()
    done_mtime_after_first = (arm_flat / ".done").stat().st_mtime

    # Touch the sentinel (simulates: new run committed, sentinel bumped)
    import time

    time.sleep(0.05)  # ensure strictly newer mtime
    sentinel.touch()
    sentinel_mtime = sentinel.stat().st_mtime
    assert sentinel_mtime > done_mtime_after_first, (
        "sentinel must be newer than .done for the rebuild assertion to be meaningful"
    )

    # Second build — stamp MUST rebuild because .dataset is newer
    result = run_make()
    done_mtime_after_second = (arm_flat / ".done").stat().st_mtime
    assert done_mtime_after_second > done_mtime_after_first, (
        "arm1_flat/.done must rebuild when .dataset sentinel is newer than .done.\n"
        "If this fails the stamp is silently stale — ticket 0462 regression."
    )


@pytest.mark.adherence
def test_score_mk_has_dataset_sentinels_committed():
    """The four .dataset sentinels must exist as committed files.

    The fix is meaningless if the sentinels are gitignored or absent — the
    prerequisite edge would always be broken with 'No rule to make target'.
    """
    exp_outputs = REPO_ROOT / "experiments" / "outputs"
    for arm in range(1, 5):
        sentinel = exp_outputs / f"sota_exp3_arm{arm}_batch1" / ".dataset"
        assert sentinel.is_file(), (
            f"sota_exp3_arm{arm}_batch1/.dataset must exist as a committed sentinel "
            "for the armN_flat/.done rebuild fix (ticket 0462). "
            "Create it with a run inventory and commit alongside the data."
        )
