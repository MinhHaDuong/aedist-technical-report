"""The slides writing build must be clean-room: no `uv run` in `make slides`.

Ticket 0370 extended the 0352 clean-room invariant to slides: `make slides`
compiles from committed handoff artifacts only — never invoking the Python
data pipeline. This test guards that invariant.

The check uses `make -n` (and a force-rebuild variant) on the slides target
and asserts the recipe trace contains no `uv run` invocation. Producer rules
belong in `experiments/render.mk` (the P3 render phase); the root Makefile's
`slides/slides.pdf`
rule must depend only on committed artifacts or targets produced by
`$(MAKE) -C slides` (i.e. tectonic itself).
"""

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent


def _make_dry_run(*extra_flags: str) -> str:
    result = subprocess.run(
        ["make", *extra_flags, "-n", "slides"],
        capture_output=True,
        text=True,
        check=True,
        cwd=REPO_ROOT,
    )
    return result.stdout


def _assert_no_uv_run(trace: str, label: str) -> None:
    offending = [line for line in trace.splitlines() if "uv run" in line]
    assert not offending, (
        f"{label} must not invoke `uv run` (writing build = clean-room). "
        "Move producer rules to experiments/render.mk.\n" + "\n".join(offending)
    )


def test_make_n_slides_has_no_uv_run():
    _assert_no_uv_run(_make_dry_run(), "make -n slides")


def test_make_force_rebuild_slides_has_no_uv_run():
    _assert_no_uv_run(_make_dry_run("-B"), "make -B -n slides")
