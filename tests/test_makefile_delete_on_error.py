"""Every build makefile that runs recipes must have `.DELETE_ON_ERROR` in force.

`.DELETE_ON_ERROR` makes Make delete a target whose recipe crashed mid-write,
instead of leaving a partial file with a fresh mtime that Make then treats as
up-to-date (a silent stale artifact). The directive is global to a single
`make` invocation, not per-rule, and it is honoured even when set in an
`include`d file. So a makefile is *covered* when the directive lives in the
file itself OR in any file it (transitively) includes.

This is the standing class guard (ticket 0461, generalising 0460 from score.mk):
a new phase makefile added later without the directive — directly or via a
shared include like `paths.mk`/`common.mk` — fails this test.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent

# `include <path>` — capture the raw argument. We resolve the project's two
# idioms: a plain relative path, and the cwd-independent
# `$(dir $(lastword $(MAKEFILE_LIST)))<rel>` prefix (which expands to the
# including makefile's own directory).
_INCLUDE_RE = re.compile(r"^\s*[-]?include\s+(\S.*?)\s*$", re.MULTILINE)
_MAKEFILE_LIST_DIR = "$(dir $(lastword $(MAKEFILE_LIST)))"


def _makefiles() -> list[Path]:
    """All git-tracked makefiles in the repo (root Makefile + *.mk, any depth).

    Sourced from `git ls-files`, not a working-tree `rglob`: untracked agent
    worktrees under `.claude/worktrees/` and untracked `attic/` artifacts carry
    their own Makefiles, and an `rglob` would flag those as orphaned outputs,
    making `make check` flaky whenever an agent worktree is present (ticket
    0595). Only tracked makefiles are real build outputs this guard governs.
    """
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    found = []
    for rel in out.split("\0"):
        if not rel:
            continue
        name = rel.rsplit("/", 1)[-1]
        if name == "Makefile" or rel.endswith(".mk"):
            found.append(REPO_ROOT / rel)
    return sorted(set(found))


def _resolve_include(makefile: Path, raw: str) -> Path | None:
    """Resolve an `include` argument to a path relative to `makefile`'s dir.

    Returns None for arguments we cannot statically resolve (variables we do
    not expand, globs) — those are simply not followed.
    """
    expr = raw.replace(_MAKEFILE_LIST_DIR, "").strip()
    if "$(" in expr or "*" in expr or "?" in expr:
        return None
    candidate = (makefile.parent / expr).resolve()
    return candidate if candidate.is_file() else None


def _includes(makefile: Path) -> list[Path]:
    text = makefile.read_text(encoding="utf-8")
    out = []
    for raw in _INCLUDE_RE.findall(text):
        resolved = _resolve_include(makefile, raw)
        if resolved is not None:
            out.append(resolved)
    return out


def _has_recipes(makefile: Path) -> bool:
    """True if the makefile defines at least one recipe.

    A recipe is a TAB-indented command line. We exclude TAB-indented
    backslash-continuations of a variable assignment (e.g. a `VAR = \\` list),
    which also start with a tab: a line is a recipe only when the *previous*
    physical line does not end with a backslash.
    """
    prev_continues = False
    for line in makefile.read_text(encoding="utf-8").splitlines():
        if line.startswith("\t") and not prev_continues:
            return True
        prev_continues = line.rstrip().endswith("\\")
    return False


# The directive as an actual special-target declaration: `.DELETE_ON_ERROR`
# at the start of a line (optional leading whitespace) followed by its colon.
# A line that merely MENTIONS the string in a comment (`# .DELETE_ON_ERROR …`)
# does not match — otherwise a makefile documenting the directive would be
# scored as setting it, and a real regression (the line deleted but a comment
# left behind) would slip through.
_DIRECTIVE_RE = re.compile(r"^[ \t]*\.DELETE_ON_ERROR[ \t]*:", re.MULTILINE)


def _sets_directive(makefile: Path) -> bool:
    return _DIRECTIVE_RE.search(makefile.read_text(encoding="utf-8")) is not None


def _reachable(makefile: Path, seen: set[Path] | None = None) -> bool:
    """True if `.DELETE_ON_ERROR` is set in `makefile` or anything it includes."""
    seen = seen if seen is not None else set()
    if makefile in seen:
        return False
    seen.add(makefile)
    if _sets_directive(makefile):
        return True
    return any(_reachable(inc, seen) for inc in _includes(makefile))


def test_recipe_makefiles_have_delete_on_error():
    recipe_makefiles = [m for m in _makefiles() if _has_recipes(m)]
    # Sanity: discovery actually found the build makefiles.
    assert recipe_makefiles, "no recipe-bearing makefiles discovered"

    uncovered = [
        m.relative_to(REPO_ROOT).as_posix()
        for m in recipe_makefiles
        if not _reachable(m)
    ]
    assert not uncovered, (
        ".DELETE_ON_ERROR not reachable (self or via include) in build "
        f"makefiles that run recipes: {uncovered}. Add `.DELETE_ON_ERROR:` to "
        "the file or to a shared include it reads (paths.mk / common.mk)."
    )


def test_discovery_ignores_untracked_worktrees_and_attic():
    """`_makefiles()` enumerates only git-tracked makefiles.

    Agent worktrees under `.claude/worktrees/` and untracked `attic/`
    directories carry their own Makefiles; before ticket 0595 the working-tree
    `rglob` scooped them up and the `attic/` Makefile (no `.DELETE_ON_ERROR`)
    failed this test locally whenever a worktree was present. A `git ls-files`
    source excludes anything untracked by construction.
    """
    discovered = {m.relative_to(REPO_ROOT).as_posix() for m in _makefiles()}
    leaked = [
        p
        for p in discovered
        if p.startswith((".claude/worktrees/", "attic/"))
    ]
    assert not leaked, (
        "discovery leaked untracked makefiles (must scan git-tracked paths "
        f"only): {leaked}"
    )

    # Cross-check: every discovered path is actually tracked by git.
    tracked = set(
        subprocess.run(
            ["git", "ls-files"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split("\n")
    )
    untracked = [p for p in discovered if p not in tracked]
    assert not untracked, f"discovered makefiles not tracked by git: {untracked}"


@pytest.mark.integration
def test_orphaned_tracked_makefile_still_detected(tmp_path, monkeypatch):
    """Detection of a genuine orphan is preserved; an untracked twin is ignored.

    Builds a throwaway git repo with two recipe-bearing Makefiles missing the
    directive: one tracked (must be flagged), one untracked under a worktree
    path (must be ignored). The fix must not weaken orphan detection on tracked
    files while it gains immunity to untracked worktree/attic artifacts.
    """
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    recipe = "all:\n\ttouch out\n"

    tracked_mk = tmp_path / "Makefile"
    tracked_mk.write_text(recipe, encoding="utf-8")

    untracked_dir = tmp_path / ".claude" / "worktrees" / "foo"
    untracked_dir.mkdir(parents=True)
    (untracked_dir / "Makefile").write_text(recipe, encoding="utf-8")

    subprocess.run(["git", "add", "Makefile"], cwd=tmp_path, check=True)


    monkeypatch.setattr(sys.modules[__name__], "REPO_ROOT", tmp_path)
    discovered = {m.relative_to(tmp_path).as_posix() for m in _makefiles()}

    assert "Makefile" in discovered, "tracked orphan must be discovered"
    assert ".claude/worktrees/foo/Makefile" not in discovered, (
        "untracked worktree Makefile must be ignored"
    )

    recipe_makefiles = [m for m in _makefiles() if _has_recipes(m)]
    uncovered = [
        m.relative_to(tmp_path).as_posix()
        for m in recipe_makefiles
        if not _reachable(m)
    ]
    assert uncovered == ["Makefile"], (
        "the tracked orphan must still be flagged as uncovered, and only it: "
        f"{uncovered}"
    )
