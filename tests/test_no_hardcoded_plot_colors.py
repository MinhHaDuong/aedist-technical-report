"""No hardcoded colour literals in `src/aedist/plot_*.py` (ticket 0194).

All figure colours route through the shared palette (``palette.toml`` +
``aedist.util``). Inline hex literals (``"#FF00FF"``) and RGB tuples
(``color=(0.1, 0.2, 0.3)``) are banned in plot scripts so the palette
remains the single source of truth — change it once and every figure
updates on the next ``make -f experiments/render.mk chart-figures``.

A small list of named-colour exceptions (``"black"``, ``"white"``,
``"gray"``) is allowed for axis spines, separators, and placeholder
messages where neutrality is the point.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
PLOT_DIR = REPO_ROOT / "src" / "aedist"

# Match six- and three-digit hex literals inside Python source.
_HEX_RE = re.compile(r"\"#[0-9A-Fa-f]{3,8}\"|'#[0-9A-Fa-f]{3,8}'")
# Match RGB tuples passed to a `color=` kwarg.
_RGB_TUPLE_RE = re.compile(r"color\s*=\s*\(\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+")


def _plot_files() -> list[Path]:
    return sorted(PLOT_DIR.glob("plot_*.py"))


def test_no_hex_in_plot_scripts():
    violations = []
    for src in _plot_files():
        for i, line in enumerate(src.read_text().splitlines(), 1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue  # full-line comment — colour talk in prose is fine
            # Drop inline trailing comments before scanning so commentary like
            # "# was #1A5070" cannot trip the test.
            code = line.split("#", 1)[0] if "  #" in line else line
            if _HEX_RE.search(code):
                violations.append(f"{src.relative_to(REPO_ROOT)}:{i}: {stripped}")
    assert not violations, (
        f"{len(violations)} hardcoded hex colour(s) in plot scripts — "
        "route through aedist.util (palette.toml) instead:\n"
        + "\n".join(f"  {v}" for v in violations)
    )


def test_no_rgb_tuples_in_plot_scripts():
    violations = []
    for src in _plot_files():
        for i, line in enumerate(src.read_text().splitlines(), 1):
            if _RGB_TUPLE_RE.search(line):
                violations.append(f"{src.relative_to(REPO_ROOT)}:{i}: {line.lstrip()}")
    assert not violations, (
        f"{len(violations)} hardcoded RGB tuple(s) in plot scripts — "
        "route through aedist.util (palette.toml) instead:\n"
        + "\n".join(f"  {v}" for v in violations)
    )
