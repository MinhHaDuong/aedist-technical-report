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
    """All committed makefiles in the repo (root Makefile + *.mk, any depth)."""
    found = [
        p
        for pat in ("Makefile", "*.mk")
        for p in REPO_ROOT.rglob(pat)
        if ".git" not in p.parts
    ]
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


def _sets_directive(makefile: Path) -> bool:
    return ".DELETE_ON_ERROR" in makefile.read_text(encoding="utf-8")


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
