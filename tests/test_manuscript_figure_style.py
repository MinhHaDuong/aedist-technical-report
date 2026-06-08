"""Enforce option-1 inline-image convention in slides/manuscript/main.md.

Every image include must use an empty alt text: `![](path)` not `![Figure N](path)`
or `![*Figure N...*](path)`. Non-empty alt text causes pandoc's implicit_figures
to emit `\\caption{Figure N}`, which the LaTeX figure counter then prefixes again,
producing "Figure N: Figure N" in the built PDF.

See ticket 0448 for the defect history and option-1 rationale.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

MANUSCRIPT = (
    Path(__file__).resolve().parent.parent / "slides" / "manuscript" / "main.md"
)


def test_no_nonempty_alt_figure_includes() -> None:
    """All image includes must use empty alt text.

    Fail if any line matches `![<non-empty>](...)` — the defect pattern.
    """
    violations = []
    text = MANUSCRIPT.read_text(encoding="utf-8")
    for i, line in enumerate(text.splitlines(), 1):
        # Match any image include with a non-empty alt text
        if re.search(r"!\[[^\]]+\]\(", line):
            violations.append(f"{MANUSCRIPT.name}:{i}: {line.strip()}")
    assert not violations, (
        f"{len(violations)} figure include(s) with non-empty alt text — "
        "use `![](path)\\` (option-1 inline-image convention, ticket 0448):\n"
        + "\n".join(f"  {v}" for v in violations)
    )
