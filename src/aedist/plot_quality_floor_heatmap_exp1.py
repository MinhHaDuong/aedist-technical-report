"""Quality-floor heatmap for Experiment 1 (replaces decorative spider in manuscript).

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.

Rows = the exact model set the spider renders (families claude / gpt / mistral / qwen;
deepseek excluded — it has no spider panel).  Columns = all five scored criteria
(accuracy, coherence, field_completeness, provenance, temporality) and their
sub-scores, derived programmatically from the CSV header — never hardcoded.

A cell is RED iff a majority (≥ ceil(n/2)+1 of n) of that model's runs score zero —
indicating the model systematically fails on that criterion. A row with any red cell
marks the model as failing to clear the §2 quality bar.

Usage:
    python -m aedist.plot_quality_floor_heatmap_exp1 \
        --input experiments/derived/exp1_cross_eval.csv \
        --output report/inputs/generated/fig_quality_floor_heatmap_exp1.pdf
"""

import argparse
import csv
import logging
from collections import defaultdict
from pathlib import Path

from .plot_quality_spider_exp1 import (
    _PANELS,
    _aggregate,
    _load_rows,
    _model_size_rank,
    _parse_optional_float,
)
from .util import model_family, model_family_color

log = logging.getLogger(__name__)

# Non-scored bookkeeping columns to exclude.
_BOOKKEEPING_COLS = frozenset({"arm", "model", "run", "prompt_version", "reference", "n_rows"})

# The five criterion prefixes — order is preserved in the figure.
_CRITERION_ORDER = ("accuracy", "coherence", "field_completeness", "provenance", "temporality")

# Composite/derived columns to exclude from the heatmap (they are aggregates of
# other sub-scores already present, so including them would double-count).
_COMPOSITE_COLS = frozenset({"accuracy_f1"})

# Human-readable column labels for display.
COLUMN_LABELS: dict[str, str] = {
    "accuracy_coverage": "Coverage",
    "accuracy_precision": "Precision",
    "accuracy_fuel": "Fuel",
    "accuracy_status": "Status",
    "accuracy_province": "Province",
    "coherence_vocab_adherence": "Vocabulary",
    "coherence_capacity_nonnegative": "Capacity≥0",
    "field_completeness_core": "Core fields",
    "field_completeness_capacity": "Capacity",
    "provenance_source_presence": "Src presence",
    "provenance_high_conf_dual_source": "Dual source",
    "provenance_source_diversity": "Src diversity",
    "provenance_source_spread": "Src spread",
    "temporality_asof_presence": "As-of date",
    "temporality_plausible_range": "Date range",
    "temporality_cod_plausible": "COD date",
}

# Dimension group display names (keys = CSV prefixes).
_DIM_DISPLAY: dict[str, str] = {
    "accuracy": "Accuracy",
    "coherence": "Coherence",
    "field_completeness": "Field completeness",
    "provenance": "Provenance",
    "temporality": "Temporality",
}


def _col_criterion(col: str) -> str:
    """Return the criterion prefix for a column name.

    Handles compound prefixes: 'field_completeness_core' → 'field_completeness'.
    All other columns use the first underscore-segment as the criterion.
    """
    for criterion in _CRITERION_ORDER:
        if col.startswith(criterion + "_") or col == criterion:
            return criterion
    return col.split("_")[0]


def _scored_columns(csv_path: Path) -> list[str]:
    """Return the ordered list of scored sub-score columns from the CSV header.

    Excludes bookkeeping columns, annotation columns, and composite aggregates
    (accuracy_f1).  Orders by criterion prefix according to _CRITERION_ORDER,
    preserving original column order within each criterion group.
    """
    with csv_path.open(newline="", encoding="utf-8") as fh:
        header = next(csv.reader(fh))

    by_criterion: dict[str, list[str]] = defaultdict(list)
    for col in header:
        if col in _BOOKKEEPING_COLS:
            continue
        if col.endswith("_annotation"):
            continue
        if col in _COMPOSITE_COLS:
            continue
        by_criterion[_col_criterion(col)].append(col)

    result: list[str] = []
    for criterion in _CRITERION_ORDER:
        result.extend(by_criterion.get(criterion, []))
    return result


def _dimension_groups(columns: list[str]) -> list[tuple[str, list[str]]]:
    """Group columns by criterion prefix, preserving _CRITERION_ORDER."""
    by_criterion: dict[str, list[str]] = defaultdict(list)
    for col in columns:
        by_criterion[_col_criterion(col)].append(col)
    return [
        (_DIM_DISPLAY.get(c, c), by_criterion[c])
        for c in _CRITERION_ORDER
        if c in by_criterion
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
    columns: list[str],
) -> dict[str, dict[str, list[float]]]:
    """For each (model, sub-score), collect the list of numeric run values.

    Returns dict[model -> dict[sub_score -> list[float]]].
    """
    by_model: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        model = str(row.get("model", "")).strip()
        if model not in models:
            continue
        for col in columns:
            value = _parse_optional_float(row.get(col))
            if value is not None:
                by_model[model][col].append(value)
    return {m: dict(by_model[m]) for m in models}


def make_figure(rows: list[dict[str, str]], input_path: Path, output: Path) -> None:
    """Build and save the quality-floor heatmap PDF.

    Columns are derived programmatically from the CSV header so the figure
    always covers all five scored criteria without hardcoding.
    """
    import matplotlib.patches as mpatches
    import matplotlib.pyplot as plt
    import numpy as np

    columns = _scored_columns(input_path)
    dim_groups = _dimension_groups(columns)

    models = heatmap_models(rows)
    if not models:
        msg = "quality floor heatmap: no models resolved from input rows"
        raise ValueError(msg)

    run_values = _compute_zero_fractions(rows, models, columns)

    n_rows = len(models)
    n_cols = len(columns)

    # Build the boolean red-cell matrix and zero-fraction matrix (for annotation).
    is_red = np.zeros((n_rows, n_cols), dtype=bool)
    zero_frac = np.full((n_rows, n_cols), np.nan)
    for i, model in enumerate(models):
        for j, col in enumerate(columns):
            runs = run_values.get(model, {}).get(col, [])
            if runs:
                n_z = sum(1 for v in runs if v == 0.0)
                zero_frac[i, j] = n_z / len(runs)
                is_red[i, j] = cell_is_red(runs)

    # Disqualified rows = any red cell.
    disqualified = np.any(is_red, axis=1)

    # ── Layout ────────────────────────────────────────────────────────────────
    fig_width = max(10.0, n_cols * 0.95 + 3.5)
    fig_height = max(5.0, n_rows * 0.55 + 3.0)
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
                ax.text(j, i, label, ha="center", va="center", fontsize=7.0, color=text_color)

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
    col_labels = [COLUMN_LABELS.get(c, c) for c in columns]
    ax.set_xticklabels(col_labels, rotation=45, ha="right", fontsize=7.5)

    # Dimension group separators (vertical lines between groups).
    col_idx = 0
    for _dim, members in dim_groups:
        col_idx += len(members)
        if col_idx < n_cols:
            ax.axvline(col_idx - 0.5, color="white", linewidth=2.0)

    # Dimension header strip above the column labels.
    col_idx = 0
    y_top = -0.72
    for dim, members in dim_groups:
        start = col_idx
        end = col_idx + len(members) - 1
        mid = (start + end) / 2
        ax.text(
            mid, y_top, dim,
            ha="center", va="center", fontsize=8.5, fontweight="bold",
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
    green_patch = mpatches.Patch(color=CELL_COLOR_GREEN, label="Green: passes (< majority zeros)")
    ax.legend(
        handles=[green_patch, red_patch],
        loc="lower center",
        bbox_to_anchor=(0.5, -0.30),
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
    make_figure(rows, args.input, args.output)


if __name__ == "__main__":
    main()
