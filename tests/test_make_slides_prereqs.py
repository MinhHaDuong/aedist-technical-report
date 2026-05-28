"""Recursive-make visibility guard for `slides/slides.pdf`.

The slides sub-make (`slides/Makefile`) consumes
`$(LOCAL_ROOT_REPORT_GEN)/fig_capability_dag.pdf`. The recursive sub-make
cannot resolve that target on its own — root must list it as a prereq of
the `slides/slides.pdf` rule so the producing recipe (defined at root)
fires before `$(MAKE) -C slides` runs.

Without this, `make slides` fails with
`No rule to make target '…fig_capability_dag.pdf'` from the sub-make even
though a producing rule exists at root.

This is the adherence companion to ticket 0367. It is integration-marked
because it shells out via `make -n`.
"""

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.adherence
@pytest.mark.integration
def test_make_slides_lists_fig_capability_dag_as_prereq():
    """The root `make -n slides` plan must reference fig_capability_dag.pdf.

    "Reference" = the root recipe to (re)build the figure appears in the
    dry-run plan on stdout. Before ticket 0367's fix, the file was not a
    prereq of `slides/slides.pdf` so root never planned to build it, and
    the sub-make failed at runtime. After the fix, root sees it as a
    prereq and either invokes the producing recipe or treats it as
    up-to-date — either way it appears on stdout (when missing on disk,
    as a recipe; when present, the dry-run still surfaces it).
    """
    # -B forces make to plan every recipe regardless of file mtimes. Without
    # it, after a successful `make slides` the targets are up-to-date and
    # `make -n` emits only "Nothing to be done", hiding what we're guarding.
    result = subprocess.run(
        ["make", "-B", "-n", "slides"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    # Search stdout only — stderr would catch the sub-make's *failure*
    # message, which is what we are guarding against, not evidence of success.
    assert "fig_capability_dag.pdf" in result.stdout, (
        "Root `make -n slides` does not reference fig_capability_dag.pdf — "
        "add it to the slides/slides.pdf prereq list in the root Makefile so "
        "the recursive sub-make can resolve the dependency.\n\n"
        f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
    )
