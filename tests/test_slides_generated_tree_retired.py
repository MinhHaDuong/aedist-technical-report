"""The slides/inputs/generated/ tree is retired (ticket 0408, tracker 0406 S1).

P3 has a single deliverable tree: report/inputs/generated/. The slide build
consumes every artifact from there; no producer writes into a slides-side
generated tree and no source references one.

This guard asserts two invariants:

  1. No build/code surface references the literal slides-generated path — the
     surfaces where a live reference would actually wire the retired tree back
     into the pipeline: Makefiles/.mk, .tex, .py, .gitignore, shell scripts, and
     CI workflows. Markdown docs are narrative (they legitimately document the
     retirement) and tickets/ is append-only history, so both are excluded; this
     guard file builds the needle dynamically so it does not self-trip.
  2. No path under that tree survives in the git index.

Reintroducing either fails this test, keeping the single-tree rule durable.
"""

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
# Built from parts so this guard file's own occurrences do not match.
NEEDLE = "slides/inputs" + "/generated"
SELF = Path(__file__).name
# Build/code surfaces where a live reference would re-wire the pipeline. Markdown
# docs are narrative (they document the retirement) and excluded by suffix.
CODE_SUFFIXES = (".mk", ".tex", ".py", ".sh", ".yml", ".yaml", ".toml", ".cfg")
CODE_NAMES = ("Makefile", ".gitignore")


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [rel for rel in out.split("\0") if rel]


def test_no_reference_to_retired_slides_tree():
    offenders: list[str] = []
    for rel in _tracked_files():
        # tickets/ is append-only history; this guard excludes its own file.
        if rel.startswith("tickets/") or rel.rsplit("/", 1)[-1] == SELF:
            continue
        name = rel.rsplit("/", 1)[-1]
        if not (name in CODE_NAMES or name.endswith(CODE_SUFFIXES)):
            continue
        try:
            text = (REPO_ROOT / rel).read_text(errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if NEEDLE in line:
                offenders.append(f"{rel}:{i}: {line.strip()}")
    assert not offenders, (
        f"{len(offenders)} reference(s) to the retired slides-generated tree "
        "(ticket 0408 — single P3 tree is report/inputs/generated/):\n" + "\n".join(offenders)
    )


def test_retired_slides_tree_absent_from_index():
    out = subprocess.run(
        ["git", "ls-files", "-z", "--", NEEDLE],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    tracked = [rel for rel in out.split("\0") if rel]
    assert not tracked, (
        "Paths still tracked under the retired slides-generated tree:\n" + "\n".join(tracked)
    )
