"""Cross-experiment spider multiplot: E1 (centre) + 4 Exp2 conditions (corners).

Layout (3×3 grid, 5 panels occupied):

   [1N]       [5N]
         [E1]
   [1D]       [5D]

Each panel shows the 4 shared models superposed.
Both Exp1 and Exp2 CSVs must have the 10 SPIDER_AXES columns.

Usage:
    python -m aedist.plot_spider_cross_exp \
        --exp1 experiments/derived/exp1_cross_eval.csv \
        --exp2 experiments/derived/sota_cross_eval.csv \
        --output report/inputs/generated/fig_spider_cross_exp.pdf
"""

import argparse
import csv
import logging
from collections import defaultdict
from pathlib import Path

from .plot_quality_spider_exp1 import (
    SPIDER_AXES,
    _draw_axis_labels,
    _median,
    _parse_optional_float,
    _style_polar_ax,
)
from .util import model_family_color

log = logging.getLogger(__name__)

# Models shown in every panel; slug normalisation handles dot-vs-dash variants
_MODEL_CANONICAL = [
    "claude-opus",
    "gpt-5.5",
    "mistral-large",
    "qwen3.7-max",
]

_MODEL_DISPLAY = {
    "claude-opus": "Claude Opus",
    "gpt-5.5": "GPT-5.5",
    "mistral-large": "Mistral Large",
    "qwen3.7-max": "Qwen 3.7 Max",
}

# Representative model slug for colour lookup (must be in the actual data)
_MODEL_COLOR_SLUG = {
    "claude-opus": "claude-opus-4-6",
    "gpt-5.5": "gpt-5.5",
    "mistral-large": "mistral-large-2512",
    "qwen3.7-max": "qwen3.7-max-2026-05-20",
}

# Conditions: (label, arm_filter, csv_source) — csv_source is "exp1" or "exp2"
_CONDITIONS = [
    ("E1\n(param.)", "parametric", "exp1"),
    ("1N\n(naïf, 1 tour)", "naive", "exp2"),
    ("5N\n(optim., 5 tours)", "optimised", "exp2"),
    ("1D\n(naïf+docs, 1 tour)", "arm3", "exp2"),
    ("5D\n(optim.+docs, 5 tours)", "arm4", "exp2"),
]

# Panel positions in a 3×3 grid (row, col)
_PANEL_POS = {
    "E1\n(param.)": (1, 1),  # centre
    "1N\n(naïf, 1 tour)": (0, 0),  # top-left
    "5N\n(optim., 5 tours)": (0, 2),  # top-right
    "1D\n(naïf+docs, 1 tour)": (2, 0),  # bottom-left
    "5D\n(optim.+docs, 5 tours)": (2, 2),  # bottom-right
}


def _normalize_model_slug(slug: str) -> str:
    return slug.lower().replace(".", "-")


def _canonical_model(slug: str) -> str | None:
    normalized = _normalize_model_slug(slug)
    for canon in _MODEL_CANONICAL:
        if normalized.startswith(canon.replace(".", "-")):
            return canon
    return None


def _load_rows(path: Path, arm: str) -> list[dict[str, str]]:
    with path.open(newline="") as fh:
        return [r for r in csv.DictReader(fh) if r.get("arm", "").strip() == arm]


def _aggregate_condition(
    rows: list[dict[str, str]],
) -> dict[str, dict[str, float]]:
    """Return {canonical_model: {axis: median_score}} for the 4 shared models."""
    by_model: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        slug = row.get("model", "").strip()
        canon = _canonical_model(slug)
        if canon is None:
            continue
        for axis in SPIDER_AXES:
            value = _parse_optional_float(row.get(axis))
            if value is not None:
                by_model[canon][axis].append(value)

    result: dict[str, dict[str, float]] = {}
    for canon, axis_vals in by_model.items():
        profile = {axis: _median(vals) for axis, vals in axis_vals.items() if vals}
        if profile:
            result[canon] = profile
    return result


def make_figure(
    exp1_path: Path,
    exp2_path: Path,
    output: Path,
) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    n_axes = len(SPIDER_AXES)
    angles = np.linspace(0, 2 * np.pi, n_axes, endpoint=False) + (np.pi / n_axes)
    closed_angles = np.concatenate((angles, [angles[0]]))

    # Build one figure with a 3×3 polar subplot grid
    fig = plt.figure(figsize=(14, 11))
    ax_grid: dict[tuple[int, int], plt.Axes] = {}
    for row_i in range(3):
        for col_i in range(3):
            ax = fig.add_subplot(3, 3, row_i * 3 + col_i + 1, projection="polar")
            ax_grid[(row_i, col_i)] = ax

    # Hide unused cells
    used_positions = set(_PANEL_POS.values())
    for pos, ax in ax_grid.items():
        if pos not in used_positions:
            ax.set_visible(False)

    for label, arm, csv_src in _CONDITIONS:
        pos = _PANEL_POS[label]
        ax = ax_grid[pos]
        path = exp1_path if csv_src == "exp1" else exp2_path
        rows = _load_rows(path, arm)
        profiles = _aggregate_condition(rows)

        _draw_axis_labels(ax, angles, SPIDER_AXES, label_fontsize=5.5, dim_fontsize=6.5)
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        _style_polar_ax(ax, angles)

        for canon in _MODEL_CANONICAL:
            profile = profiles.get(canon)
            if not profile:
                continue
            color = model_family_color(_MODEL_COLOR_SLUG[canon])
            values = [profile.get(axis, 0.0) for axis in SPIDER_AXES]
            closed_values = values + [values[0]]
            ax.plot(
                closed_angles,
                closed_values,
                color=color,
                linewidth=1.6,
                label=_MODEL_DISPLAY[canon],
            )
            ax.fill(closed_angles, closed_values, color=color, alpha=0.06)

        ax.set_title(label, fontsize=9, pad=16, fontweight="bold")

    # Shared legend below the figure
    handles, labels = ax_grid[(1, 1)].get_legend_handles_labels()
    if handles:
        fig.legend(
            handles,
            labels,
            loc="lower center",
            ncol=4,
            fontsize=10,
            frameon=False,
            bbox_to_anchor=(0.5, 0.01),
        )

    fig.suptitle(
        "Profils de qualité — Exp 1 et Exp 2 (4 modèles, 10 indicateurs)",
        fontsize=13,
        y=0.99,
    )
    fig.tight_layout(rect=(0, 0.06, 1, 0.97))
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", dpi=150)
    plt.close(fig)
    log.info("Wrote %s", output)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Cross-experiment spider multiplot")
    parser.add_argument(
        "--exp1",
        type=Path,
        default=Path("experiments/derived/exp1_cross_eval.csv"),
    )
    parser.add_argument(
        "--exp2",
        type=Path,
        default=Path("experiments/derived/sota_cross_eval.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("report/inputs/generated/fig_spider_cross_exp.pdf"),
    )
    args = parser.parse_args(argv)
    make_figure(args.exp1, args.exp2, args.output)


if __name__ == "__main__":
    main()
