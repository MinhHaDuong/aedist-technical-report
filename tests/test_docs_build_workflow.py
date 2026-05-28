"""Structural adherence test for the docs-build GHA workflow.

The actual end-to-end test is the workflow itself running on a PR. This
adherence test guards the load-bearing pieces of the YAML — anything a
casual edit could break without notice.
"""

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "docs-build.yml"


def _load() -> dict:
    assert WORKFLOW.exists(), f"missing workflow file: {WORKFLOW}"
    return yaml.safe_load(WORKFLOW.read_text())


def test_workflow_file_exists():
    assert WORKFLOW.exists(), f"missing workflow file: {WORKFLOW}"


def test_pull_request_paths_cover_build_inputs():
    wf = _load()
    # YAML's `on:` key is sometimes parsed as the boolean True by PyYAML.
    triggers = wf.get("on") or wf.get(True)
    assert triggers, "no triggers defined"
    pr = triggers.get("pull_request")
    assert pr, "pull_request trigger missing"
    paths = pr.get("paths") or []
    required = {"report/**", "slides/**", "Makefile"}
    missing = required - set(paths)
    assert not missing, f"pull_request.paths missing entries: {missing}"


def test_push_main_and_dispatch_triggers():
    wf = _load()
    triggers = wf.get("on") or wf.get(True)
    push = triggers.get("push") or {}
    assert "main" in (push.get("branches") or []), "push trigger must target main"
    assert "workflow_dispatch" in triggers, "workflow_dispatch trigger missing"


def test_build_job_present():
    wf = _load()
    jobs = wf.get("jobs") or {}
    assert "build" in jobs, "job named 'build' is required (required-check id)"


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
