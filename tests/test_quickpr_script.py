"""Smoke + fence tests for scripts/quickpr.sh.

The script encodes a chore-fence: it refuses to run when any staged file
is under src/, tests/, or experiments/. We verify the fence here so an
agent can't accidentally route implementation work through quickpr.
"""

import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "quickpr.sh"


def test_script_exists_and_executable():
    assert SCRIPT.exists(), f"missing: {SCRIPT}"
    assert os.access(SCRIPT, os.X_OK), f"not executable: {SCRIPT}"


def test_help_prints_usage():
    result = subprocess.run([str(SCRIPT), "--help"], capture_output=True, text=True, check=True)
    assert "quickpr" in result.stdout
    assert "Usage:" in result.stdout


@pytest.mark.parametrize(
    "path",
    ["src/aedist/__init__.py", "tests/test_quickpr_script.py"],
)
def test_chore_fence_refuses_implementation_paths(path: str):
    """Fence must fire before any git work happens."""
    target = REPO_ROOT / path
    if not target.exists():
        pytest.skip(f"prereq absent: {path}")
    result = subprocess.run(
        [str(SCRIPT), "test message", str(target)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode != 0, "fence should reject implementation paths"
    assert "src/tests/experiments" in result.stderr, (
        f"expected fence message in stderr, got:\n{result.stderr}"
    )
