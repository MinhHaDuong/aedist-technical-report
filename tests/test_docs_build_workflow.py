"""Structural adherence test for the docs-build GHA workflow.

The actual end-to-end test is the workflow itself running on a PR. This
adherence test guards the load-bearing pieces of the YAML — anything a
casual edit could break without notice.
"""

import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "docs-build.yml"


def _load() -> dict:
    assert WORKFLOW.exists(), f"missing workflow file: {WORKFLOW}"
    return yaml.safe_load(WORKFLOW.read_text())


def _triggers(wf: dict) -> dict:
    # YAML's `on:` key is sometimes parsed as the boolean True by PyYAML.
    triggers = wf.get("on") or wf.get(True)
    assert triggers, "no triggers defined"
    return triggers


def test_workflow_file_exists():
    assert WORKFLOW.exists(), f"missing workflow file: {WORKFLOW}"


def test_docs_build_runs_on_all_pull_requests():
    """The workflow must run on every PR for the required-check gate to clear.

    A `pull_request.paths` filter would skip chore-only PRs and leave the
    required `build` check pending forever. Heavy work is gated inside the
    `build` job via the `changes` job's `chore` output instead.
    """
    wf = _load()
    triggers = _triggers(wf)
    assert "pull_request" in triggers, "pull_request trigger missing"
    pr = triggers["pull_request"]
    # pull_request without a paths filter — None (bare `pull_request:`) or a
    # dict that does not key `paths`.
    assert pr is None or (isinstance(pr, dict) and "paths" not in pr), (
        "docs-build.yml must run on every PR for the required-check gate; "
        "use the internal `changes` job to skip heavy work on chore diffs."
    )


def test_push_main_and_dispatch_triggers():
    wf = _load()
    triggers = _triggers(wf)
    push = triggers.get("push") or {}
    assert "main" in (push.get("branches") or []), "push trigger must target main"
    assert "workflow_dispatch" in triggers, "workflow_dispatch trigger missing"


def test_changes_and_build_jobs_present():
    wf = _load()
    jobs = wf.get("jobs") or {}
    assert "changes" in jobs, "job named 'changes' is required (chore detector)"
    assert "build" in jobs, "job named 'build' is required (required-check id)"


def test_changes_job_uses_paths_filter():
    wf = _load()
    changes = wf["jobs"]["changes"]
    steps = changes.get("steps") or []
    uses = [s.get("uses", "") for s in steps]
    assert any("dorny/paths-filter" in u for u in uses), (
        "changes job must use dorny/paths-filter to compute chore output"
    )
    outputs = changes.get("outputs") or {}
    assert "non-chore" in outputs, "changes job must expose `non-chore` output"


def test_build_depends_on_changes():
    wf = _load()
    build = wf["jobs"]["build"]
    needs = build.get("needs")
    assert needs == "changes" or (isinstance(needs, list) and "changes" in needs), (
        "build job must declare `needs: changes`"
    )
    # `!cancelled()` so build still runs (as a no-op) when `changes` returns
    # chore=true; without it, a skipped dependency would skip `build` too.
    assert "cancelled()" in str(build.get("if", "")), (
        "build job must guard with `if: !cancelled()` so it always reports a status"
    )


def test_build_steps_gated_on_non_chore_flag():
    """Every concrete step in `build` must skip when the diff is chore-only."""
    wf = _load()
    steps = wf["jobs"]["build"].get("steps") or []
    assert steps, "build job has no steps"
    ungated = [
        s.get("name") or s.get("uses") or "<unnamed>"
        for s in steps
        if "needs.changes.outputs.non-chore != 'false'" not in str(s.get("if", ""))
    ]
    assert not ungated, f"every build step must gate on the non-chore flag; ungated: {ungated}"


def test_slides_step_has_continue_on_error():
    wf = _load()
    job = wf["jobs"]["build"]
    steps = job.get("steps") or []
    slides_steps = [
        s
        for s in steps
        if "slides" in (s.get("name") or "").lower()
        and "manuscript" not in (s.get("name") or "").lower()
    ]
    assert slides_steps, "no step named for slides"
    for s in slides_steps:
        assert s.get("continue-on-error") is True, (
            f"slides step '{s.get('name')}' must have continue-on-error: true "
            f"until fig_capability_dag precondition (ticket 0367) is fixed"
        )


def test_tectonic_version_pinned():
    text = WORKFLOW.read_text()
    assert "0.15.0" in text, "tectonic version must be pinned to 0.15.0"


def test_tectonic_cache_key():
    text = WORKFLOW.read_text()
    assert "tectonic-0.15.0-" in text, (
        "tectonic cache key must include version 0.15.0 for invalidation on bump"
    )


def test_setup_uv_action_used():
    text = WORKFLOW.read_text()
    assert "astral-sh/setup-uv@v4" in text, "uv setup action must be pinned to v4"


def test_build_runner_pinned():
    wf = _load()
    assert wf["jobs"]["build"].get("runs-on") == "ubuntu-24.04", (
        "build job must pin runner to ubuntu-24.04 for reproducibility"
    )


def _filter_patterns() -> tuple[str, list[str]]:
    """Return (filter_name, patterns) from the paths-filter step."""
    wf = _load()
    steps = wf["jobs"]["changes"].get("steps") or []
    filter_step = next(
        (s for s in steps if "dorny/paths-filter" in (s.get("uses") or "")),
        None,
    )
    assert filter_step is not None, "dorny/paths-filter step not found"
    raw_filters = (filter_step.get("with") or {}).get("filters", "")
    parsed = yaml.safe_load(raw_filters)
    assert len(parsed) == 1, f"expected exactly one filter, got {list(parsed)}"
    name, patterns = next(iter(parsed.items()))
    return name, patterns


def _glob_match(path: str, pattern: str) -> bool:
    """Minimal picomatch subset covering the workflow's patterns.

    Supports brace expansion `{a,b}`, the catch-all `**`, `dir/**`
    prefixes, and literal filenames — nothing more.
    """
    if pattern.startswith("{") and pattern.endswith("}"):
        return any(_glob_match(path, p) for p in pattern[1:-1].split(","))
    if pattern == "**":
        return True
    if pattern.endswith("/**"):
        return path.startswith(pattern[:-2])
    return path == pattern


def _paths_filter_output(changed_files: list[str], patterns: list[str]) -> bool:
    """Emulate dorny/paths-filter with predicate-quantifier: every.

    The filter output is true iff ANY changed file matches ALL patterns;
    a leading `!` negates the individual pattern (per upstream README).
    """

    def file_matches(path: str) -> bool:
        for pat in patterns:
            if pat.startswith("!"):
                if _glob_match(path, pat[1:]):
                    return False
            elif not _glob_match(path, pat):
                return False
        return True

    return any(file_matches(f) for f in changed_files)


def _gate_allows(cond: str, output: str, name: str) -> bool:
    """Evaluate the non-chore comparison clause inside one `if:` condition."""
    expr = cond.replace("${{", "").replace("}}", "").strip()
    match = re.search(
        rf"needs\.changes\.outputs\.{re.escape(name)}\s*(==|!=)\s*'([^']*)'", expr
    )
    assert match, f"no {name} comparison found in gate {cond!r}"
    op, rhs = match.groups()
    equal = output == rhs
    return equal if op == "==" else not equal


def _build_runs(filter_output: bool | None) -> bool:
    """Evaluate every build-step gate as GitHub Actions would.

    `filter_output is None` models an empty/errored filter output (the
    expression then compares against the empty string). All steps must
    agree — a step whose gate diverges from the others is an error.
    """
    wf = _load()
    steps = wf["jobs"]["build"].get("steps") or []
    output = "" if filter_output is None else str(filter_output).lower()
    name, _ = _filter_patterns()
    verdicts = {_gate_allows(str(s.get("if", "")), output, name) for s in steps}
    assert len(verdicts) == 1, f"build steps disagree on the {name} gate"
    return verdicts.pop()


def test_chore_only_diff_skips_build():
    """A purely-chore diff (tickets/** alone) must skip the heavy build."""
    _, patterns = _filter_patterns()
    output = _paths_filter_output(["tickets/closed/0523-fix-tau.erg"], patterns)
    assert not _build_runs(output), "chore-only diff must skip the build steps"


def test_mixed_diff_runs_build():
    """A mixed diff (tickets/** + slides/**) must run the full build.

    This is the ticket 0525 regression: PR #938 changed
    slides/manuscript/main.tex alongside a ticket file and the entire
    docs-build was skipped.
    """
    _, patterns = _filter_patterns()
    output = _paths_filter_output(
        ["tickets/closed/0523-fix-tau.erg", "slides/manuscript/main.tex"],
        patterns,
    )
    assert _build_runs(output), "mixed diff must run the build steps"


def test_source_only_diff_runs_build():
    _, patterns = _filter_patterns()
    output = _paths_filter_output(["slides/Makefile"], patterns)
    assert _build_runs(output), "non-chore diff must run the build steps"


def test_empty_filter_output_runs_build():
    """Fail-safe: an empty/errored filter output must still build."""
    assert _build_runs(None), "ambiguous filter output must default to building"
