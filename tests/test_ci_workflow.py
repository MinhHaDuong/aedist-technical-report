"""Structural adherence test for the CI GHA workflow.

The actual end-to-end test is the workflow itself running on a PR. This
adherence test guards the load-bearing pieces of the YAML — anything a
casual edit could break without notice.

Key invariant (tickets 0525/0527): under dorny/paths-filter, a filter's
output is true when ANY changed file matches it, and predicate-quantifier:
every quantifies over PATTERNS per file, not over files.  A positive
`chore` filter therefore fired on mixed diffs and skipped lint + tests.
The filter is inverted (`non-chore: ['**', '!{...}']`) and steps gate on
`!= 'false'`, so only a purely-chore diff skips.  The emulation tests below
replay chore-only, mixed, source-only, and empty-output diffs against the
actual patterns in the workflow file.
"""

from pathlib import Path

import pytest
import yaml

from tests.workflow_filter_helpers import filter_patterns, job_runs, paths_filter_output

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "CI.yml"

GATED_JOBS = ("lint", "tests")


def _load() -> dict:
    assert WORKFLOW.exists(), f"missing workflow file: {WORKFLOW}"
    return yaml.safe_load(WORKFLOW.read_text())


def test_workflow_file_exists():
    assert WORKFLOW.exists(), f"missing workflow file: {WORKFLOW}"


def test_ci_runs_on_all_pull_requests():
    """The workflow must run on every PR for the required-check gate to clear.

    A `pull_request.paths` filter would skip chore-only PRs and leave the
    required check pending forever.  Heavy work is gated inside jobs via the
    `changes` job's `non-chore` output instead.
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
        "changes job must use dorny/paths-filter to compute the non-chore output"
    )
    outputs = changes.get("outputs") or {}
    assert "non-chore" in outputs, "changes job must expose `non-chore` output"


def test_lint_and_tests_depend_on_changes():
    wf = _load()
    for job_name in GATED_JOBS:
        job = wf["jobs"][job_name]
        needs = job.get("needs")
        assert needs == "changes" or (
            isinstance(needs, list) and "changes" in needs
        ), f"{job_name} job must declare `needs: changes`"
        assert "cancelled()" in str(job.get("if", "")), (
            f"{job_name} job must guard with `if: !cancelled()` so it always "
            "reports a status"
        )


def test_lint_and_tests_steps_gated_on_non_chore_flag():
    """Every concrete step in lint and tests must skip when the diff is chore-only."""
    wf = _load()
    for job_name in GATED_JOBS:
        steps = wf["jobs"][job_name].get("steps") or []
        assert steps, f"{job_name} job has no steps"
        ungated = [
            s.get("name") or s.get("uses") or "<unnamed>"
            for s in steps
            if "needs.changes.outputs.non-chore != 'false'" not in str(s.get("if", ""))
        ]
        assert not ungated, (
            f"every {job_name} step must gate on the non-chore flag; ungated: {ungated}"
        )


def test_chore_only_diff_skips_lint_and_tests():
    """A purely-chore diff (tickets/** alone) must skip lint + tests."""
    wf = _load()
    _, patterns = filter_patterns(wf)
    output = paths_filter_output(["tickets/closed/0523-fix-tau.erg"], patterns)
    for job_name in GATED_JOBS:
        assert not job_runs(wf, job_name, output), (
            f"chore-only diff must skip {job_name} steps"
        )


def test_mixed_diff_runs_lint_and_tests():
    """A mixed diff (tickets/** + src/**) must run full CI.

    This is the ticket 0527 regression (sibling of 0525 in docs-build):
    a ticket file changed alongside source code and lint + tests were
    skipped entirely.
    """
    wf = _load()
    _, patterns = filter_patterns(wf)
    output = paths_filter_output(
        ["tickets/closed/0523-fix-tau.erg", "src/aedist/util.py"],
        patterns,
    )
    for job_name in GATED_JOBS:
        assert job_runs(wf, job_name, output), f"mixed diff must run {job_name} steps"


def test_source_only_diff_runs_lint_and_tests():
    wf = _load()
    _, patterns = filter_patterns(wf)
    output = paths_filter_output(["src/aedist/util.py"], patterns)
    for job_name in GATED_JOBS:
        assert job_runs(wf, job_name, output), (
            f"non-chore diff must run {job_name} steps"
        )


def test_empty_filter_output_runs_lint_and_tests():
    """Fail-safe: an empty/errored filter output must still run full CI."""
    wf = _load()
    for job_name in GATED_JOBS:
        assert job_runs(wf, job_name, None), (
            f"ambiguous filter output must default to running {job_name}"
        )
