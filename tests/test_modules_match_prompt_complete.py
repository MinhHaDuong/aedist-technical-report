"""Verify that assembling all modules reproduces prompt_complete.txt content.

Every non-blank, non-header line in prompt_complete.txt must appear in the
assembled composite, and vice versa.  Headers and blank lines are stripped
for comparison since assembly joins modules with \\n\\n (which may differ
from the original whitespace).

Reconciled in ticket 0191: prompt_complete.txt was regenerated from the
post-rename modules via ``assemble_prompt`` so this adherence test is
active again as the regression guard against future module-rename drift.
"""

import re
from pathlib import Path

import pytest

EXPERIMENTS_DIR = Path(__file__).resolve().parent.parent / "experiments"


def _content_lines(text: str) -> set[str]:
    """Extract non-blank, non-header content lines, normalized."""
    lines: set[str] = set()
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if re.match(r"^#{1,4}\s", stripped):
            continue
        lines.add(stripped)
    return lines


@pytest.mark.adherence
def test_modules_cover_prompt_complete():
    """Assembled composite covers every content line of prompt_complete.txt."""
    from aedist.harness import assemble_prompt

    modules_dir = EXPERIMENTS_DIR / "prompts" / "modules"
    prompt_complete = (EXPERIMENTS_DIR / "prompts" / "prompt_complete.txt").read_text()

    all_stems = sorted(p.stem for p in modules_dir.glob("*.txt"))
    assembled = assemble_prompt(modules_dir, all_stems)

    expected = _content_lines(prompt_complete)
    actual = _content_lines(assembled)

    missing = expected - actual
    assert not missing, "Lines in prompt_complete but not in assembled composite:\n" + "\n".join(
        sorted(missing)
    )

    extra = actual - expected
    assert not extra, "Lines in assembled composite but not in prompt_complete:\n" + "\n".join(
        sorted(extra)
    )
