"""Structural adherence test for the CI GHA workflow.

The actual end-to-end test is the workflow itself running on a PR. This
adherence test guards the load-bearing pieces of the YAML — anything a
casual edit could break without notice.

Key invariant: the chore filter must use a SINGLE brace-expansion pattern
under predicate-quantifier: every.  If the filter is split into N separate
patterns, then every changed file must match ALL N patterns (picomatch
semantics of 'every'), which is impossible when the patterns cover disjoint
paths — making chore=false unconditionally.  See ticket 0377.
"""

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "CI.yml"


def _load() -> dict:
    assert WORKFLOW.exists(), f"missing workflow file: {WORKFLOW}"
    return yaml.safe_load(WORKFLOW.read_text())


def test_workflow_file_exists():
    assert WORKFLOW.exists(), f"missing workflow file: {WORKFLOW}"


def test_ci_runs_on_all_pull_requests():
    """The workflow must run on every PR for the required-check gate to clear.

    A `pull_request.paths` filter would skip chore-only PRs and leave the
    required check pending forever.  Heavy work is gated inside jobs via the
    `changes` job's `chore` output instead.
    """
    wf = _load()
    triggers = wf.get("on") or wf.get(True)
    assert triggers, "no triggers defined"
    assert "pull_request" in triggers, "pull_request trigger missing"
    pr = triggers["pull_request"]
    assert pr is None or (isinstance(pr, dict) and "paths" not in pr), (
        "CI.yml must run on every PR; use the internal `changes` job to skip "
        "heavy work on chore diffs."
    )


def test_changes_and_lint_tests_jobs_present():
    wf = _load()
    jobs = wf.get("jobs") or {}
    assert "changes" in jobs, "job named 'changes' is required (chore detector)"
    assert "lint" in jobs, "job named 'lint' is required"
    assert "tests" in jobs, "job named 'tests' is required"


def test_changes_job_uses_paths_filter():
    wf = _load()
    changes = wf["jobs"]["changes"]
    steps = changes.get("steps") or []
    uses = [s.get("uses", "") for s in steps]
    assert any("dorny/paths-filter" in u for u in uses), (
        "changes job must use dorny/paths-filter to compute chore output"
    )
    outputs = changes.get("outputs") or {}
    assert "chore" in outputs, "changes job must expose `chore` output"


def test_chore_filter_is_single_brace_pattern():
    """Guard against the predicate-quantifier: every + multi-pattern trap.

    Under predicate-quantifier: every, each changed file must match ALL
    patterns listed.  With mutually-exclusive positive patterns (tickets/**,
    STATE.md, etc.) no file can satisfy all patterns, so chore is always
    false.  The fix is exactly one brace-expansion pattern so the single
    picomatch call returns true whenever the file is in any branch of the
    brace set.
    """
    wf = _load()
    steps = wf["jobs"]["changes"].get("steps") or []
    filter_step = next(
        (s for s in steps if "dorny/paths-filter" in (s.get("uses") or "")),
        None,
    )
    assert filter_step is not None, "dorny/paths-filter step not found"
    raw_filters = (filter_step.get("with") or {}).get("filters", "")
    parsed = yaml.safe_load(raw_filters)
    chore_patterns = parsed.get("chore") or []
    assert len(chore_patterns) == 1, (
        f"chore filter must have exactly one brace-expansion pattern "
        f"(predicate-quantifier: every requires this); found {len(chore_patterns)} patterns: "
        f"{chore_patterns}"
    )
    pattern = chore_patterns[0]
    assert pattern.startswith("{") and pattern.endswith("}"), (
        f"chore filter pattern must be a brace expression like "
        f"'{{tickets/**,...}}'; got: {pattern!r}"
    )


def test_lint_and_tests_depend_on_changes():
    wf = _load()
    for job_name in ("lint", "tests"):
        job = wf["jobs"][job_name]
        needs = job.get("needs")
        assert needs == "changes" or (
            isinstance(needs, list) and "changes" in needs
        ), f"{job_name} job must declare `needs: changes`"
        assert "cancelled()" in str(job.get("if", "")), (
            f"{job_name} job must guard with `if: !cancelled()` so it always "
            "reports a status"
        )


def test_lint_and_tests_steps_gated_on_chore_flag():
    """Every concrete step in lint and tests must skip when the diff is chore-only."""
    wf = _load()
    for job_name in ("lint", "tests"):
        steps = wf["jobs"][job_name].get("steps") or []
        assert steps, f"{job_name} job has no steps"
        ungated = [
            s.get("name") or s.get("uses") or "<unnamed>"
            for s in steps
            if "needs.changes.outputs.chore" not in str(s.get("if", ""))
        ]
        assert not ungated, (
            f"every {job_name} step must gate on the chore flag; ungated: {ungated}"
        )
