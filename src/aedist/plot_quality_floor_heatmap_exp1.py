"""Quality-floor heatmap for Experiment 1 (replaces decorative spider in manuscript).

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.

Rows = the exact model set the spider renders (families claude / gpt / mistral / qwen;
deepseek excluded — it has no spider panel). Columns = the 10 SPIDER_AXES sub-scores.

A cell is RED iff a majority (≥ ceil(n/2)+1 of n) of that model's runs score zero —
indicating the model systematically fails on that criterion. A row with any red cell
marks the model as failing to clear the §2 quality bar.

Usage:
    python -m aedist.plot_quality_floor_heatmap_exp1 \
        --input experiments/derived/exp1_cross_eval.csv \
        --output report/inputs/generated/fig_quality_floor_heatmap_exp1.pdf
"""

import argparse
import logging
from collections import defaultdict
from pathlib import Path

from .plot_quality_spider_exp1 import (
    _PANELS,
    SPIDER_AXES,
    _aggregate,
    _load_rows,
    _model_size_rank,
    _parse_optional_float,
)
from .util import model_family, model_family_color

log = logging.getLogger(__name__)

# Human-readable column labels (same as spider indicator labels, single-line).
COLUMN_LABELS: dict[str, str] = {
    "accuracy_coverage": "Coverage",
    "accuracy_precision": "Precision",
    "accuracy_fuel": "Fuel",
    "accuracy_status": "Status",
    "accuracy_province": "Province",
    "coherence_vocab_adherence": "Vocabulary",
    "provenance_source_diversity": "Src diversity",
    "provenance_source_spread": "Src spread",
    "temporality_plausible_range": "Date range",
    "temporality_cod_plausible": "COD date",
}

# Dimension group labels and their member sub-scores (order matches SPIDER_AXES).
DIMENSION_GROUPS: list[tuple[str, list[str]]] = [
    ("Accuracy", ["accuracy_coverage", "accuracy_precision", "accuracy_fuel", "accuracy_status", "accuracy_province"]),
    ("Coherence", ["coherence_vocab_adherence"]),
    ("Provenance", ["provenance_source_diversity", "provenance_source_spread"]),
    ("Temporality", ["temporality_plausible_range", "temporality_cod_plausible"]),
]

# RGB arrays for heatmap cell colours (module-level to satisfy ruff N806).
CELL_COLOR_RED = (0.85, 0.22, 0.22)    # red  — disqualifying cell
CELL_COLOR_GREEN = (0.18, 0.63, 0.18)  # green — passing cell
CELL_COLOR_GREY = (0.88, 0.88, 0.88)   # light grey — no data


def cell_is_red(runs: list[float]) -> bool:
    """Return True iff a majority of runs scored zero on this sub-score.

    Majority = strictly more than half: n_zero >= ceil(len/2) + 1 for even,
    (len+1)//2 + 1 for odd.  For the standard case of 5 runs: 3/5 is red,
    2/5 is not.

    Missing/None values are excluded from both numerator and denominator —
    only valid (numeric) runs count.

    >>> cell_is_red([0.0, 0.0, 0.0, 0.4, 0.6])  # 3/5 zero
    True
    >>> cell_is_red([0.0, 0.0, 0.4, 0.5, 0.6])  # 2/5 zero
    False
    >>> cell_is_red([])  # no data — conservative: not red
    False
    """
    if not runs:
        return False
    n_zero = sum(1 for v in runs if v == 0.0)
    return n_zero > len(runs) / 2


def _spider_panel_models(rows: list[dict[str, str]]) -> list[str]:
    """Return the ordered model list the spider would render, from the same rows.

    Mirrors the logic in plot_quality_spider_exp1.make_figure: for each panel in
    _PANELS collect the models matching its family set, sorted by size rank then
    name.  DeepSeek is excluded because it has no panel in _PANELS.
    """
    stats = _aggregate(rows)
    result: list[str] = []
    for _panel_key, _panel_title, families in _PANELS:
        panel_models = [m for m in stats if model_family(m) in families]
        panel_models.sort(key=lambda m: (_model_size_rank(m), m))
        result.extend(panel_models)
    return result


def heatmap_models(rows: list[dict[str, str]]) -> list[str]:
    """Return the model list for the heatmap rows (equals spider panel models)."""
    return _spider_panel_models(rows)


def _compute_zero_fractions(
    rows: list[dict[str, str]],
    models: list[str],
) -> dict[str, dict[str, list[float]]]:
    """For each (model, sub-score), collect the list of numeric run values.

    Returns dict[model -> dict[sub_score -> list[float]]].
    """
    by_model: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        model = str(row.get("model", "")).strip()
        if model not in models:
            continue
        for axis in SPIDER_AXES:
            value = _parse_optional_float(row.get(axis))
            if value is not None:
                by_model[model][axis].append(value)
    return {m: dict(by_model[m]) for m in models}


def make_figure(rows: list[dict[str, str]], output: Path) -> None:
    """Build and save the quality-floor heatmap PDF."""
    import matplotlib.patches as mpatches
    import matplotlib.pyplot as plt
    import numpy as np

    models = heatmap_models(rows)
    if not models:
        msg = "quality floor heatmap: no models resolved from input rows"
        raise ValueError(msg)

    run_values = _compute_zero_fractions(rows, models)

    n_rows = len(models)
    n_cols = len(SPIDER_AXES)

    # Build the boolean red-cell matrix and zero-fraction matrix (for annotation).
    is_red = np.zeros((n_rows, n_cols), dtype=bool)
    zero_frac = np.full((n_rows, n_cols), np.nan)
    for i, model in enumerate(models):
        for j, axis in enumerate(SPIDER_AXES):
            runs = run_values.get(model, {}).get(axis, [])
            if runs:
                n_z = sum(1 for v in runs if v == 0.0)
                zero_frac[i, j] = n_z / len(runs)
                is_red[i, j] = cell_is_red(runs)

    # Disqualified rows = any red cell.
    disqualified = np.any(is_red, axis=1)

    # ── Layout ────────────────────────────────────────────────────────────────
    fig_width = max(9.0, n_cols * 0.85 + 3.0)
    fig_height = max(5.0, n_rows * 0.55 + 2.5)
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    # Background colour matrix: green for passing, red for failing, grey for no-data.
    rgb = np.full((n_rows, n_cols, 3), CELL_COLOR_GREY)
    for i in range(n_rows):
        for j in range(n_cols):
            if not np.isnan(zero_frac[i, j]):
                rgb[i, j] = CELL_COLOR_RED if is_red[i, j] else CELL_COLOR_GREEN

    ax.imshow(rgb, aspect="auto", origin="upper", interpolation="nearest")

    # Cell annotations: zero-fraction as percentage.
    for i in range(n_rows):
        for j in range(n_cols):
            if not np.isnan(zero_frac[i, j]):
                pct = zero_frac[i, j]
                label = f"{pct:.0%}" if pct > 0 else "0%"
                text_color = "white" if is_red[i, j] or pct > 0.5 else "black"
                ax.text(j, i, label, ha="center", va="center", fontsize=7.5, color=text_color)

    # Row labels: model names, coloured by family; disqualified rows get a ✗ marker.
    ax.set_yticks(range(n_rows))
    row_labels = []
    for i, model in enumerate(models):
        label = model
        if disqualified[i]:
            label = f"✗ {model}"
        row_labels.append(label)
    ax.set_yticklabels(row_labels, fontsize=8.5)

    # Colour the y-tick labels by family.
    for i, (tick, model) in enumerate(zip(ax.get_yticklabels(), models, strict=True)):
        tick.set_color(model_family_color(model))
        if disqualified[i]:
            tick.set_fontweight("bold")

    # Column labels: short sub-score names, angled.
    ax.set_xticks(range(n_cols))
    col_labels = [COLUMN_LABELS.get(a, a) for a in SPIDER_AXES]
    ax.set_xticklabels(col_labels, rotation=40, ha="right", fontsize=8)

    # Dimension group separators (vertical lines between groups).
    col_idx = 0
    for _dim, members in DIMENSION_GROUPS:
        col_idx += len(members)
        if col_idx < n_cols:
            ax.axvline(col_idx - 0.5, color="white", linewidth=2.0)

    # Dimension header strip above the column labels.
    col_idx = 0
    y_top = -0.8
    for dim, members in DIMENSION_GROUPS:
        start = col_idx
        end = col_idx + len(members) - 1
        mid = (start + end) / 2
        ax.text(
            mid, y_top, dim,
            ha="center", va="center", fontsize=9, fontweight="bold",
            transform=ax.get_xaxis_transform(),
        )
        col_idx += len(members)

    # Row group separators: thin horizontal line between families.
    prev_family = None
    for i, model in enumerate(models):
        fam = model_family(model)
        if prev_family and fam != prev_family:
            ax.axhline(i - 0.5, color="white", linewidth=2.0)
        prev_family = fam

    # Legend.
    red_patch = mpatches.Patch(color=CELL_COLOR_RED, label="Red: ≥3/5 runs score zero (disqualifying)")
    green_patch = mpatches.Patch(color=CELL_COLOR_GREEN, label="Green: < majority zeros")
    ax.legend(
        handles=[green_patch, red_patch],
        loc="lower center",
        bbox_to_anchor=(0.5, -0.26),
        ncol=2,
        fontsize=8,
        frameon=False,
    )

    ax.set_title(
        "Quality-floor heatmap — Experiment 1 (parametric arm)\n"
        "Any red cell ⇒ model fails the §2 quality bar",
        fontsize=10,
        pad=12,
    )

    # Grid lines between cells.
    ax.set_xticks(np.arange(-0.5, n_cols, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, n_rows, 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=0.5)
    ax.tick_params(which="minor", bottom=False, left=False)

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", dpi=150)
    plt.close(fig)
    log.info("Wrote %s", output)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Render Exp1 quality-floor heatmap (replaces spider in manuscript)"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("experiments/derived/exp1_cross_eval.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("report/inputs/generated/fig_quality_floor_heatmap_exp1.pdf"),
    )
    args = parser.parse_args(argv)
    rows = _load_rows(args.input)
    make_figure(rows, args.output)


if __name__ == "__main__":
    main()
