"""Adherence: every /skill reference in AGENTS.md resolves to a real skill.

Ticket 0426: the skills table in AGENTS.md is maintained by hand and can
accumulate ghost references when skills are renamed or removed in IDH.
This test flags those ghosts so they surface locally before the next rename.

Resolution order (first match wins):
1. ``~/.claude/skills/<name>/`` — user-level IDH skills
2. ``.claude/skills/<name>/`` — project-level skills (none currently)
3. Hard-coded builtin list — Claude Code native skills (review, simplify, …)

Exception marker: if the same line that contains the ``/skill-name`` backtick
reference also contains the text ``à créer``, the reference is considered
intentionally planned and is exempt from the check.  Example:
  ``| `/update-publist` | … (à créer, IDH 0214) | … |``
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_MD = REPO_ROOT / "AGENTS.md"

# Skills that are native Claude Code builtins — not installed as SKILL.md files
# but always available inside a Claude Code session.  Keep this list conservative:
# only add a skill here when it appears in the Claude Code system-reminder catalog
# and is never installed under ~/.claude/skills/.
_BUILTINS: frozenset[str] = frozenset(
    [
        "code-review",
        "deep-research",
        "init",
        "keybindings-help",
        "review",
        "run",
        "security-review",
        "simplify",
        "update-config",
        "verify",
    ]
)


def _user_skills() -> frozenset[str]:
    """Return skill names installed under ~/.claude/skills/."""
    base = Path.home() / ".claude" / "skills"
    if not base.is_dir():
        return frozenset()
    return frozenset(p.name for p in base.iterdir() if p.is_dir())


def _project_skills() -> frozenset[str]:
    """Return skill names installed under .claude/skills/ in the repo."""
    base = REPO_ROOT / ".claude" / "skills"
    if not base.is_dir():
        return frozenset()
    return frozenset(p.name for p in base.iterdir() if p.is_dir())


def _parse_skill_refs(md_path: Path) -> list[tuple[str, str]]:
    """Return (skill_name, raw_line) for every `/skill-name` backtick in md_path.

    Only references without the exception marker ``à créer`` on the same line
    are included — planned skills are exempt.
    """
    pattern = re.compile(r"`/([a-z][a-z0-9-]*[a-z0-9])`")
    refs: list[tuple[str, str]] = []
    for line in md_path.read_text(encoding="utf-8").splitlines():
        # Skip planned-skill lines (exception marker).
        if "à créer" in line:
            continue
        refs.extend((m.group(1), line.strip()) for m in pattern.finditer(line))
    return refs


@pytest.mark.skipif(
    not (Path.home() / ".claude" / "skills").is_dir(),
    reason="IDH skills not installed (e.g. CI); AGENTS.md skill resolution is a local-only adherence check",
)
def test_agents_md_skill_refs_resolve():
    """Every non-exempt /skill reference in AGENTS.md must resolve."""
    known = _user_skills() | _project_skills() | _BUILTINS
    refs = _parse_skill_refs(AGENTS_MD)

    phantoms = [
        f"  /{name!r} — not found in user/project skills or builtins\n    line: {line}"
        for name, line in refs
        if name not in known
    ]
    assert not phantoms, (
        f"{len(phantoms)} phantom /skill reference(s) in AGENTS.md:\n"
        + "\n".join(phantoms)
    )


def test_agents_md_exists():
    """AGENTS.md must be present at the repo root (sanity guard)."""
    assert AGENTS_MD.is_file(), f"AGENTS.md not found at {AGENTS_MD}"
