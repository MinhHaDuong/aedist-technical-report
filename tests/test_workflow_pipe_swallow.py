"""Adherence guard against silent pipe-swallow failures in workflow YAML.

GitHub Actions runs `run:` blocks under `bash -e`. Without `pipefail`,
a piped command like `pandoc --version | head -n1` exits with `head`'s
status, masking upstream failures — e.g. `pandoc: command not found`
silently reports success because `head` reads empty stdin and returns 0.

This bit us in PR #636 (fixed in commit 750276e). Ticket 0378 adds this
static guard so the class cannot recur silently.
"""

import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = REPO_ROOT / ".github" / "workflows"

PIPE_SWALLOW = re.compile(r"(--version|--help)\s.*\|\s*(head|tail|grep|awk|cut|sed)")


def _scan_script(script: str) -> list[str]:
    """Return offending lines in a run-block. Empty if pipefail is set."""
    if not script:
        return []
    if "set -o pipefail" in script or "set -euo pipefail" in script:
        return []
    return [line for line in script.splitlines() if PIPE_SWALLOW.search(line)]


def test_no_silent_pipe_swallow_in_workflows():
    bad: list[tuple[str, str, str, str]] = []
    for wf in sorted(WORKFLOWS.glob("*.yml")):
        data = yaml.safe_load(wf.read_text()) or {}
        for jobname, job in data.get("jobs", {}).items():
            for step in job.get("steps", []) or []:
                bad.extend(
                    (wf.name, jobname, step.get("name", "?"), line.strip())
                    for line in _scan_script(step.get("run", ""))
                )
    assert not bad, (
        "Pipe-swallow risk: `cmd --version | head` masks command-not-found "
        "under `bash -e`. Add `set -euo pipefail` to the run-block or drop "
        "the pipe.\n" + "\n".join(f"  {wf}:{job}:{step}: {line}" for wf, job, step, line in bad)
    )


@pytest.mark.parametrize(
    "script, should_fire",
    [
        ("pandoc --version | head -n1", True),
        ("git --version | grep git", True),
        ("set -euo pipefail\npandoc --version | head -n1", False),
        ("set -o pipefail\ngit --version | grep git", False),
        ("pandoc --version", False),
        ('echo "ok"', False),
    ],
)
def test_pipe_swallow_regex_fires_as_specified(script: str, should_fire: bool):
    """Prove the rule fires when it should — TDD red-step substitute."""
    hits = _scan_script(script)
    if should_fire:
        assert hits, f"regex failed to flag: {script!r}"
    else:
        assert not hits, f"regex false-positived on: {script!r}"
