"""Quality-floor heatmap for Experiment 1 (replaces decorative spider in manuscript).

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.

Layout (transposed for readability):
    * Columns = the exact model set the direct-query census renders (Figure 2),
      laid out to match its family-then-size ordering: architectural family
      alphabetical, then a coarse name-based size tier descending (larger
      first), then name.  This name-tier rank approximates — and, for the
      fourteen-model cohort here, reproduces (verified against the committed
      fig_direct_p1_base.pdf) — Figure 2's parameter-count ordering without
      needing the per-record size_class the census reads.  DeepSeek IS included
      (it is one of the fourteen census models); the old four-panel spider
      excluded it, this figure does not.
    * Rows = the genuine 0–1 sub-scores across the five criteria (accuracy,
      coherence, field_completeness, provenance, temporality), derived
      programmatically from the CSV header — never hardcoded.  The raw *_distinct
      COUNT columns and the composite accuracy_f1 are diagnostic intermediates
      and excluded.  Sub-scores that do not separate the models (across-model
      spread of means below _MIN_DISCRIMINATING_SPREAD — the all-green rows)
      are dropped: a criterion no model fails carries no quality-floor signal.

A cell shows the **mean** of that model's per-run sub-score — a continuous 0–1
quality value rendered on a sequential red→green colour scale (0 = the whole
column fails the criterion, 1 = every run clears it).  The simple per-model mean
is enough: a model whose runs systematically zero a free criterion aggregates to
~0 and reads dark red, which is exactly the quality-bar "too weak to clear"
signal.

The internal-coherence screen is **merged into the Coherence dimension** rather
than added as a separate disqualifying column: the inverted veto flag
(coherence_run_veto, 1 = vetoed/degenerate) is shown as its positive complement
``1 − veto`` ("Internal coherence"), so higher is better in lockstep with every
other sub-score and the ρ=0.92 reference-free screen sits naturally beside
vocabulary adherence and capacity sanity.

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

from .plot_method_convergence import census_model_order
from .plot_quality_spider_exp1 import (
    _load_rows,
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

# Diagnostic intermediates in the Coherence group that are NOT 0–1 sub-scores:
# raw COUNTs of distinct capacities/statuses per run (values like 4, 26, 35…).
# They feed the veto rule (cap_distinct <= 4 OR status_distinct <= 1) but are not
# themselves quality scores, so they are excluded from the rendered grid.
_NON_SUBSCORE_COLS = frozenset({"coherence_capacity_distinct", "coherence_status_distinct"})

# Minimum across-model spread (max mean − min mean) for a sub-score to earn a
# row.  Sub-scores on which every model scores ~identically (the all-green rows:
# capacity sanity, core/capacity completeness, source presence, dual-source,
# as-of presence — uniformly ≈1.0 in the parametric arm) carry no quality-floor
# signal and are dropped.  The floor figure exists to show where models *fail*,
# so a criterion no model fails (and none separates on) is omitted.
_MIN_DISCRIMINATING_SPREAD = 0.10

# The internal-coherence veto flag (score_mechanical.py): "1" = run was vetoed
# (degenerate/repeated rows → bad), "0" = run passed the screen.  This is the
# paper's ρ=0.92 zero-reference screen.  Its polarity is INVERTED relative
# to a sub-score, so the rendered value is its positive complement (1 − veto)
# and it lives inside the Coherence dimension (not as a separate column).
_VETO_COL = "coherence_run_veto"

# Human-readable row labels for display.
COLUMN_LABELS: dict[str, str] = {
    "accuracy_coverage": "Coverage",
    "accuracy_precision": "Precision",
    "accuracy_fuel": "Fuel",
    "accuracy_status": "Status",
    "accuracy_province": "Province",
    "coherence_vocab_adherence": "Vocabulary",
    "coherence_capacity_nonnegative": r"Capacity $\geq$0",
    "coherence_run_veto": "Internal coherence",
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
    "field_completeness": "Field compl.",
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
    """Return the ordered list of rendered sub-scores from the CSV header.

    Excludes bookkeeping columns, annotation columns, composite aggregates
    (accuracy_f1), and non-sub-score diagnostic intermediates (the raw
    *_distinct COUNT columns).  The coherence veto flag IS retained — it is
    rendered inside the Coherence dimension as its positive complement
    (see _subscore_value).  Orders by criterion prefix according to
    _CRITERION_ORDER, preserving original column order within each group.
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
        if col in _NON_SUBSCORE_COLS:
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


def _subscore_value(col: str, run_value: float) -> float:
    """Map one raw run value to a 0–1 quality score where higher is better.

    Every genuine sub-score is already polarised so that 1.0 is good.  The
    internal-coherence veto flag is inverted (1.0 = vetoed/degenerate), so its
    rendered value is the positive complement ``1 − veto`` — merging the
    zero-reference screen into Coherence on the same "higher is better" scale.

    >>> _subscore_value("accuracy_coverage", 0.4)
    0.4
    >>> _subscore_value("coherence_run_veto", 1.0)  # vetoed run → 0 quality
    0.0
    >>> _subscore_value("coherence_run_veto", 0.0)  # passed screen → 1 quality
    1.0
    """
    return (1.0 - run_value) if col == _VETO_COL else run_value


def mean_score(col: str, runs: list[float]) -> float | None:
    """Return the simple mean quality score across a model's runs for a column.

    Polarity-corrected per :func:`_subscore_value` so higher is always better.
    Empty input → None (rendered as a no-data cell).  The plain mean is the
    deliberate aggregation choice: a model that zeros a free criterion on every
    run averages to 0 and reads dark red, which is the quality-floor signal.

    >>> mean_score("accuracy_coverage", [0.0, 0.0, 0.0, 0.4, 0.6])
    0.2
    >>> mean_score("coherence_run_veto", [1.0, 1.0, 1.0, 0.0, 0.0])  # 3/5 vetoed
    0.4
    >>> mean_score("accuracy_coverage", []) is None
    True
    """
    if not runs:
        return None
    vals = [_subscore_value(col, v) for v in runs]
    return sum(vals) / len(vals)


def discriminating_columns(
    columns: list[str],
    run_values: dict[str, dict[str, list[float]]],
    models: list[str],
    min_spread: float = _MIN_DISCRIMINATING_SPREAD,
) -> list[str]:
    """Drop sub-scores that do not separate the models (the all-green rows).

    A sub-score is kept only if the spread of per-model mean scores
    (max − min, polarity-corrected via :func:`mean_score`) reaches
    ``min_spread``.  Criteria every model clears uniformly (≈1.0 everywhere)
    add height without information to a quality-*floor* figure, so they are
    omitted.  The decision is data-driven — nothing about which columns survive
    is hardcoded — so a future arm where one of these criteria starts to
    discriminate re-earns its row automatically.
    """
    kept: list[str] = []
    for col in columns:
        means = [
            v
            for m in models
            if (v := mean_score(col, run_values.get(m, {}).get(col, []))) is not None
        ]
        if means and (max(means) - min(means)) >= min_spread:
            kept.append(col)
    return kept


def heatmap_models(rows: list[dict[str, str]]) -> list[str]:
    """Return the model column order: the canonical Figure 2 census order.

    Delegates to ``census_model_order`` (ticket 0504) — the single shared
    ordering, resolved from the model name alone, so the heatmap reads
    against its self-contained CSV without a per-record size_class (guarded
    by tests/test_census_model_order.py, verified against the committed
    figure). Unlike the four-panel spider, this includes DeepSeek.
    """
    models = {str(r.get("model", "")).strip() for r in rows if str(r.get("model", "")).strip()}
    return census_model_order(models)


def _collect_runs(
    rows: list[dict[str, str]],
    models: list[str],
    columns: list[str],
) -> dict[str, dict[str, list[float]]]:
    """For each (model, sub-score), collect the list of numeric run values."""
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


def _fmt_score(value: float) -> str:
    """Compact cell annotation: '1'/'0' only for exact values, else two decimals.

    The quality bar is a conjunction, so the printed extremes carry claims:
    '1' must mean every run cleared the criterion and '0' must mean every run
    failed it.  Values that merely round to the extremes display as '>.99' /
    '<.01' instead (e.g. vocab adherence 0.998 is not "all clear").

    >>> _fmt_score(1.0), _fmt_score(0.0), _fmt_score(0.52)
    ('1', '0', '.52')
    >>> _fmt_score(0.998), _fmt_score(0.003)
    ('>.99', '<.01')
    """
    if value == 1.0:
        return "1"
    if value == 0.0:
        return "0"
    if value >= 0.995:
        return ">.99"
    if value < 0.005:
        return "<.01"
    return f"{value:.2f}"[1:]


def make_figure(rows: list[dict[str, str]], input_path: Path, output: Path) -> None:
    """Build and save the quality-floor heatmap PDF.

    Rows are sub-scores (grouped by the five dimensions, derived programmatically
    from the CSV header); columns are the fourteen census models in Figure 2
    order.  Each cell is the per-model mean sub-score on a continuous red→green
    scale.
    """
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib import colormaps
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize

    models = heatmap_models(rows)
    if not models:
        msg = "quality floor heatmap: no models resolved from input rows"
        raise ValueError(msg)

    candidate_cols = _scored_columns(input_path)
    run_values = _collect_runs(rows, models, candidate_cols)
    # Keep only sub-scores that actually separate the models; the all-green
    # criteria (uniformly cleared) are not interesting on a quality-floor figure.
    subscores = discriminating_columns(candidate_cols, run_values, models)
    if not subscores:
        msg = (
            "quality floor heatmap: no discriminating sub-scores survive the "
            f"spread filter (>= {_MIN_DISCRIMINATING_SPREAD}) across "
            f"{len(models)} model(s) — refusing to emit an empty figure"
        )
        raise ValueError(msg)
    dim_groups = _dimension_groups(subscores)

    n_rows = len(subscores)  # sub-scores
    n_cols = len(models)

    # Mean-score matrix: rows = sub-scores, cols = models. NaN = no data.
    scores = np.full((n_rows, n_cols), np.nan)
    for i, col in enumerate(subscores):
        for j, model in enumerate(models):
            runs = run_values.get(model, {}).get(col, [])
            value = mean_score(col, runs)
            if value is not None:
                scores[i, j] = value

    # ── Layout ────────────────────────────────────────────────────────────────
    fig_width = max(9.0, n_cols * 0.62 + 3.4)
    fig_height = max(6.0, n_rows * 0.42 + 2.4)
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    cmap = colormaps["RdYlGn"].copy()
    cmap.set_bad(color="lightgray")  # neutral placeholder for no-data cells
    norm = Normalize(vmin=0.0, vmax=1.0)
    masked = np.ma.masked_invalid(scores)
    ax.imshow(masked, aspect="auto", cmap=cmap, norm=norm, interpolation="nearest")

    # Cell annotations: the mean score (higher = better, green). Text colour
    # follows cell luminance so it reads on both red and green extremes.
    for i in range(n_rows):
        for j in range(n_cols):
            if np.isnan(scores[i, j]):
                continue
            r, g, b, _ = cmap(norm(scores[i, j]))
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            ax.text(
                j, i, _fmt_score(scores[i, j]),
                ha="center", va="center", fontsize=6.5,
                color="black" if lum > 0.55 else "white",
            )

    # Row labels (sub-scores).
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels([COLUMN_LABELS.get(c, c) for c in subscores], fontsize=8.5)

    # Column labels (models), at the top, angled and coloured by family.
    ax.xaxis.set_ticks_position("top")
    ax.xaxis.set_label_position("top")
    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(models, rotation=45, ha="left", fontsize=8.0)
    for tick, model in zip(ax.get_xticklabels(), models, strict=True):
        tick.set_color(model_family_color(model))

    # Dimension row-group separators (horizontal lines between groups) and a
    # bold dimension label in the left margin spanning each group.
    trans = ax.get_yaxis_transform()  # x in axes fraction, y in data coords
    row_idx = 0
    for dim, members in dim_groups:
        start = row_idx
        end = row_idx + len(members) - 1
        ax.text(
            -0.30, (start + end) / 2, dim,
            transform=trans, rotation=90, ha="center", va="center",
            fontsize=8.5, fontweight="bold",
        )
        row_idx += len(members)
        if row_idx < n_rows:
            ax.axhline(row_idx - 0.5, color="white", linewidth=2.5)

    # Family column separators (vertical lines between architectural families).
    prev_family = None
    for j, model in enumerate(models):
        fam = model_family(model)
        if prev_family and fam != prev_family:
            ax.axvline(j - 0.5, color="white", linewidth=2.5)
        prev_family = fam

    # Thin white grid between every cell.
    ax.set_xticks(np.arange(-0.5, n_cols, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, n_rows, 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=0.5)
    ax.tick_params(which="minor", bottom=False, top=False, left=False)

    # Colourbar: the continuous quality scale.
    cbar = fig.colorbar(
        ScalarMappable(norm=norm, cmap=cmap),
        ax=ax, fraction=0.025, pad=0.02,
    )
    cbar.set_label("Mean sub-score across runs  (0 = all runs fail · 1 = all clear)", fontsize=8)
    cbar.ax.tick_params(labelsize=7)

    # NB: not "reference-free" — the Accuracy rows are the reference-full axis.
    ax.set_title(
        "Quality-floor heatmap — Experiment 1 (parametric arm)\n"
        "Per-model mean of each quality sub-score; dark red ⇒ the quality bar is not cleared",
        fontsize=10, pad=28,
    )

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
