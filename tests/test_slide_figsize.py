"""Beamer slide figure-size constants and the décalage-droite guard (tickets 0338, 0330).

Full-slide figures are included with
``\\includegraphics[width=\\paperwidth,height=\\paperheight,keepaspectratio]``.
When the source figure is wider than 16:9 (aspect ratio > 1.78),
``height=\\paperheight`` dominates and matplotlib renders the figure wider than
the slide — its right edge is clipped. The fix is to size full-slide figures
from the shared ``SLIDE_FIGSIZE_*`` constants in ``aedist.util`` rather than
hardcoded tuples, so the ratio can never silently regress.

Two guards live here:

1. Pin the constant values and assert the full-slide ones stay at ratio ≤ 1.78.
2. An adherence check: every ``figsize=`` in a *slide-bound* plot script must be
   a named reference (a constant), never an inline tuple literal. Report-only
   plot scripts are deliberately out of scope — their figures are not subject to
   the ``height=\\paperheight`` clipping.
"""

import ast
from pathlib import Path

import pytest

from aedist.util import (
    SLIDE_FIGSIZE_FULL,
    SLIDE_FIGSIZE_HALF,
    SLIDE_FIGSIZE_WIDE,
    SLIDE_FIGSIZE_POLAR_2x2,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
PLOT_DIR = REPO_ROOT / "src" / "aedist"

# 16:9 — the most a full-slide figure may be without the right edge clipping.
MAX_FULL_SLIDE_RATIO = 16 / 9  # ≈ 1.778

# Scripts whose output appears as a full-slide \includegraphics in slides.tex.
# Only these must route figsize through a constant; report-only scripts are
# free to size their figures however the page layout needs.
SLIDE_BOUND_PLOT_SCRIPTS = {
    "plot_cost_quality.py",
    "plot_exp2_arms_comparison.py",
    "plot_capability_timeline.py",
    "plot_quality_spider_exp1.py",
    "plot_exp2_coverage_certainty.py",
}


def test_slide_figsize_constant_values() -> None:
    """Pin the exact constant values (ticket 0338 §Actions)."""
    assert SLIDE_FIGSIZE_FULL == (10.0, 5.625)
    assert SLIDE_FIGSIZE_WIDE == (11.2, 6.3)
    assert SLIDE_FIGSIZE_HALF == (5.5, 4.0)
    assert SLIDE_FIGSIZE_POLAR_2x2 == (10.0, 8.0)


@pytest.mark.parametrize(
    "figsize",
    [SLIDE_FIGSIZE_FULL, SLIDE_FIGSIZE_WIDE],
    ids=["full", "wide"],
)
def test_full_slide_ratio_within_16_9(figsize: tuple[float, float]) -> None:
    """Full-slide figures must not exceed 16:9 or they clip on the right."""
    width, height = figsize
    ratio = width / height
    # 1e-6 tolerance so values engineered to be exactly 16:9 (e.g. 11.2/6.3)
    # are not tripped by float rounding on either side of the bound.
    assert ratio <= MAX_FULL_SLIDE_RATIO + 1e-6, (
        f"figsize {figsize} has aspect ratio {ratio:.3f} > {MAX_FULL_SLIDE_RATIO:.3f} "
        "(16:9) — would clip on the right when rendered full-slide."
    )


def _figsize_nodes(src: Path) -> list[ast.AST]:
    """Return the AST value node of every ``figsize=`` keyword in *src*."""
    tree = ast.parse(src.read_text())
    return [
        kw.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        for kw in node.keywords
        if kw.arg == "figsize"
    ]


@pytest.mark.adherence
def test_slide_bound_figsize_use_constants() -> None:
    """No inline ``figsize=(...)`` tuple in any slide-bound plot script.

    A constant reference parses to an ``ast.Name`` (e.g. ``SLIDE_FIGSIZE_FULL``);
    an inline tuple literal parses to an ``ast.Tuple`` — that is the regression
    this guard catches.
    """
    violations: list[str] = []
    for name in sorted(SLIDE_BOUND_PLOT_SCRIPTS):
        src = PLOT_DIR / name
        assert src.exists(), f"slide-bound plot script not found: {src}"
        violations.extend(
            f"{src.relative_to(REPO_ROOT)}: figsize={ast.unparse(value)}"
            for value in _figsize_nodes(src)
            if not isinstance(value, ast.Name)
        )
    assert not violations, (
        f"{len(violations)} hardcoded figsize in slide-bound plot script(s) — "
        "use a SLIDE_FIGSIZE_* constant from aedist.util:\n"
        + "\n".join(f"  {v}" for v in violations)
    )
