"""No hardcoded ``figsize`` tuples in ``src/aedist/plot_*.py`` (ticket 0338).

All figure sizes route through the shared constants in
``aedist.util`` (e.g. ``SLIDE_FIGSIZE_FULL``, ``SLIDE_FIGSIZE_HALF``).
Inline ``figsize=(…)`` tuples are banned so every plot uses a standard
size — change the constant once and every figure updates on next
``make figures``.

Variables (``fig_width``, ``fig_height``) are allowed — they are not
hardcoded and may be parameterised from CLI args.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
PLOT_DIR = REPO_ROOT / "src" / "aedist"

# Match ``figsize=(...)`` with numeric values — not variable names.
_FIGSIZE_RE = re.compile(
    r"figsize\s*=\s*\(\s*[\d.]+\s*,\s*[\d.]+"  # figsize=(10, 5) etc.
)

# Variable names that are allowed (not hardcoded).
_ALLOWED_VARS = {"fig_width", "fig_height"}


def _plot_files() -> list[Path]:
    return sorted(PLOT_DIR.glob("plot_*.py"))


def test_no_hardcoded_figsize():
    violations = []
    for src in _plot_files():
        for i, line in enumerate(src.read_text().splitlines(), 1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            if _FIGSIZE_RE.search(stripped):
                violations.append(
                    f"{src.relative_to(REPO_ROOT)}:{i}: {stripped}"
                )
    assert not violations, (
        f"{len(violations)} hardcoded figsize tuple(s) in plot scripts — "
        "import and use a constant from aedist.util instead:\n"
        + "\n".join(f"  {v}" for v in violations)
    )
