"""Verify that assembling all modules reproduces prompt_complete.txt content.

Every non-blank, non-header line in prompt_complete.txt must appear in the
assembled composite, and vice versa.  Headers (lines starting with #) and
blank lines are structural scaffolding that modules don't replicate.
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
    from aedist.harness import KNOWN_MODULES, assemble_prompt

    modules_dir = EXPERIMENTS_DIR / "prompts" / "modules"
    prompt_complete = (EXPERIMENTS_DIR / "prompts" / "prompt_complete.txt").read_text()

    assembled = assemble_prompt(modules_dir, sorted(KNOWN_MODULES))

    expected = _content_lines(prompt_complete)
    actual = _content_lines(assembled)

    missing = expected - actual
    assert not missing, f"Lines in prompt_complete but not in assembled composite:\n" + "\n".join(
        sorted(missing)
    )

    extra = actual - expected
    assert not extra, f"Lines in assembled composite but not in prompt_complete:\n" + "\n".join(
        sorted(extra)
    )
