"""Reliability-vs-accuracy screen figure for Experiment 1 (ticket 0506).

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.

A label-free *source-reliability* screen plotted against reference-based
accuracy, showing that the inaccurate models are also the unreliable ones and
can be screened out without ground truth.

Ratified definitions (Imagine session 2026-06-09):
    * good run = a run with no zero on any of the 12 reference-free dimensions
      (coherence x3 incl. the inverted 1-veto, provenance x4, temporality x3,
      completeness x2).  Missing score = skip, not a doubt (only
      high_conf_dual_source is ever missing).  One doubt taints the whole run —
      the gate is a minimum, not an average.
    * Reliability (X, the control / label-free screen) = COUNT of good runs out
      of 5 reps, reported as the integer 0..5.  Unreliable models fall left,
      reliable right; the empty 2-3 columns are the screening cut.
    * Accuracy (Y, the effect) = AVERAGE F1 over the good runs.  For a model
      with zero good runs, Y = average F1 over all runs (caption says so).
    * Markers sit exactly on (integer count, F1) — no jitter, except the
      author-tuned <= one-dot-radius horizontal jitter for near-coincident F1
      pairs in the saturated 5/5 column.

The sensitivity sweep (annex companion) varies the gate threshold tau in
{0.0, 0.1, 0.2, 0.3} (discard run if min dimension <= tau) and the indicator
set {3 coherence-only, 7 discriminating, 12 all reference-free}, reporting per
cell the number of disqualified models (reliability <= 1), whether that set
equals the baseline trash floor, and Spearman(accuracy, reliability).

Usage:
    python -m aedist.plot_exp1_reliability \
        --input experiments/derived/exp1_cross_eval.csv \
        --output report/inputs/generated/fig_exp1_reliability.pdf
    python -m aedist.plot_exp1_reliability \
        --input experiments/derived/exp1_cross_eval.csv \
        --sensitivity-csv experiments/derived/exp1_reliability_sensitivity.csv \
        --annex-table report/inputs/generated/tab_exp1_reliability_sensitivity.tex
"""

import argparse
import csv
import logging
from collections import defaultdict
from pathlib import Path

log = logging.getLogger(__name__)

# ── Gate constants (documented module constants per the ticket) ──────────────

# The 12 reference-free quality dimensions: coherence x3 (incl. the run veto,
# rendered as its positive complement 1-veto), provenance x4, temporality x3,
# field completeness x2.  accuracy_* columns are reference-BASED and excluded.
DIMENSIONS_ALL: tuple[str, ...] = (
    "coherence_vocab_adherence",
    "coherence_capacity_nonnegative",
    "coherence_run_veto",
    "provenance_source_presence",
    "provenance_high_conf_dual_source",
    "provenance_source_diversity",
    "provenance_source_spread",
    "temporality_asof_presence",
    "temporality_plausible_range",
    "temporality_cod_plausible",
    "field_completeness_core",
    "field_completeness_capacity",
)

# Coherence-only indicator subset (sensitivity sweep: is coherence enough?).
DIMENSIONS_COHERENCE: tuple[str, ...] = (
    "coherence_vocab_adherence",
    "coherence_capacity_nonnegative",
    "coherence_run_veto",
)

# Default gate threshold: a run is discarded iff some dimension <= tau.
# tau = 0.0 is the ratified "no zero on any dimension" gate.
GATE_TAU: float = 0.0

# Reps per model in the parametric arm (X axis is the count 0..N_REPS).
N_REPS: int = 5

# A model is "disqualified" by the screen when at most this many runs are good.
FLOOR_MAX_GOOD_RUNS: int = 1

# Minimum across-model spread of per-model mean scores for a dimension to count
# as "discriminating" in the sensitivity sweep's middle indicator set (same
# convention as plot_quality_floor_heatmap_exp1._MIN_DISCRIMINATING_SPREAD).
MIN_DISCRIMINATING_SPREAD: float = 0.10

# The internal-coherence veto flag has inverted polarity (1 = vetoed/bad);
# every gate computation uses its positive complement 1-veto.
_VETO_COL = "coherence_run_veto"

# Sensitivity sweep grid.
SWEEP_TAUS: tuple[float, ...] = (0.0, 0.1, 0.2, 0.3)

# ── Figure label placement (author-tuned, ticket 0506) ───────────────────────

# Near-coincident F1 pairs in the saturated 5/5 column get a horizontal jitter
# of <= one dot-radius — one left, one right, label on the matching side.  The
# ONLY jitter allowed, and only in that column.
JITTER_SIDE: dict[str, str] = {
    "gpt-5.5": "left",
    "claude-sonnet-4.6": "right",
    "deepseek-v4-pro": "left",
    "mistral-medium-3-5": "right",
    "qwen3.7-max": "left",
    "mistral-large-2512": "right",
}

# Author-set label sides outside the jitter pairs.
LABEL_SIDE: dict[str, str] = {
    "qwen3.6-35b-a3b": "left",
}


# ── Data loading and the gate ─────────────────────────────────────────────────


def load_rows(csv_path: Path | str) -> list[dict[str, str]]:
    """Load the cross-eval CSV rows (one row per model x run)."""
    with Path(csv_path).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _dim_value(row: dict[str, str], dim: str) -> float | None:
    """Polarity-corrected 0-1 value of one dimension; None when missing.

    The veto flag is inverted (1 = vetoed) so its quality value is 1-veto.
    """
    raw = (row.get(dim) or "").strip()
    if not raw:
        return None
    value = float(raw)
    return 1.0 - value if dim == _VETO_COL else value


def is_good_run(
    row: dict[str, str],
    dims: tuple[str, ...] = DIMENSIONS_ALL,
    tau: float = GATE_TAU,
) -> bool:
    """The gate: True iff no scored dimension is <= tau.

    Missing score = skip (not a doubt).  One failing dimension taints the
    whole run — the gate is a minimum over dimensions, not an average.
    """
    for dim in dims:
        value = _dim_value(row, dim)
        if value is not None and value <= tau:
            return False
    return True


def reliability_by_model(
    csv_path: Path | str,
    dims: tuple[str, ...] = DIMENSIONS_ALL,
    tau: float = GATE_TAU,
) -> dict[str, int]:
    """Reliability = integer count of good runs out of N_REPS, per model."""
    counts: dict[str, int] = defaultdict(int)
    for row in load_rows(csv_path):
        model = row["model"].strip()
        counts[model] += int(is_good_run(row, dims, tau))
    return dict(counts)


def mean_f1_good_by_model(
    csv_path: Path | str,
    dims: tuple[str, ...] = DIMENSIONS_ALL,
    tau: float = GATE_TAU,
) -> dict[str, float]:
    """Accuracy = mean F1 over the good runs (expectation of one good run).

    For a model with zero good runs the mean is over ALL its runs — no good
    run exists, and the figure caption says so.
    """
    good: dict[str, list[float]] = defaultdict(list)
    all_runs: dict[str, list[float]] = defaultdict(list)
    for row in load_rows(csv_path):
        model = row["model"].strip()
        f1 = float(row["accuracy_f1"])
        all_runs[model].append(f1)
        if is_good_run(row, dims, tau):
            good[model].append(f1)
    return {
        model: (sum(vals) / len(vals) if (vals := good.get(model)) else sum(runs) / len(runs))
        for model, runs in all_runs.items()
    }


def discriminating_dimensions(
    rows: list[dict[str, str]],
    min_spread: float = MIN_DISCRIMINATING_SPREAD,
) -> tuple[str, ...]:
    """Reference-free dimensions whose per-model mean spread >= min_spread.

    Same data-driven convention as the quality-floor heatmap: a dimension every
    model clears uniformly carries no screening signal.  Derived from the data,
    never hardcoded — the sweep's middle indicator set.
    """
    per_model: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        model = row["model"].strip()
        for dim in DIMENSIONS_ALL:
            value = _dim_value(row, dim)
            if value is not None:
                per_model[model][dim].append(value)
    kept: list[str] = []
    for dim in DIMENSIONS_ALL:
        means = [
            sum(vals) / len(vals)
            for scores in per_model.values()
            if (vals := scores.get(dim))
        ]
        if means and max(means) - min(means) >= min_spread:
            kept.append(dim)
    return tuple(kept)


# ── Sensitivity sweep ─────────────────────────────────────────────────────────


def spearman(xs: list[float], ys: list[float]) -> float:
    """Spearman rank correlation (tie-aware, via scipy)."""
    from scipy.stats import spearmanr

    rho = spearmanr(xs, ys).statistic
    return float(rho)


def _gate_summary(
    rows: list[dict[str, str]], dims: tuple[str, ...], tau: float
) -> tuple[dict[str, int], dict[str, float]]:
    """Reliability counts and accuracy means for one (dims, tau) gate."""
    counts: dict[str, int] = defaultdict(int)
    good_f1: dict[str, list[float]] = defaultdict(list)
    all_f1: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        model = row["model"].strip()
        f1 = float(row["accuracy_f1"])
        all_f1[model].append(f1)
        if is_good_run(row, dims, tau):
            counts[model] += 1
            good_f1[model].append(f1)
        else:
            counts.setdefault(model, 0)
    accuracy = {
        m: (sum(vals) / len(vals) if (vals := good_f1.get(m)) else sum(runs) / len(runs))
        for m, runs in all_f1.items()
    }
    return dict(counts), accuracy


def sensitivity_sweep(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Sweep tau x indicator set; report per cell vs the baseline floor.

    Baseline floor = models with <= FLOOR_MAX_GOOD_RUNS good runs under the
    main-figure gate (all 12 dimensions, tau = GATE_TAU).
    """
    disc = discriminating_dimensions(rows)
    indicator_sets: list[tuple[str, tuple[str, ...]]] = [
        ("coherence_only", DIMENSIONS_COHERENCE),
        ("discriminating", disc),
        ("all_reference_free", DIMENSIONS_ALL),
    ]
    base_counts, _ = _gate_summary(rows, DIMENSIONS_ALL, GATE_TAU)
    base_floor = {m for m, n in base_counts.items() if n <= FLOOR_MAX_GOOD_RUNS}

    cells: list[dict[str, str]] = []
    for name, dims in indicator_sets:
        for tau in SWEEP_TAUS:
            counts, accuracy = _gate_summary(rows, dims, tau)
            models = sorted(counts)
            disq = {m for m in models if counts[m] <= FLOOR_MAX_GOOD_RUNS}
            rho = spearman([float(counts[m]) for m in models], [accuracy[m] for m in models])
            cells.append(
                {
                    "indicator_set": name,
                    "n_dims": str(len(dims)),
                    "tau": f"{tau:.1f}",
                    "n_disqualified": str(len(disq)),
                    "equals_floor": "yes" if disq == base_floor else "no",
                    "spearman": f"{rho:.4f}",
                    "disqualified_models": ";".join(sorted(disq)),
                }
            )
    return cells


def write_sweep_csv(cells: list[dict[str, str]], output: Path) -> None:
    """Write the sensitivity sweep artifact (committed handoff CSV)."""
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(cells[0].keys())
    with output.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(cells)
    log.info("Wrote %s", output)


_SET_DISPLAY = {
    "coherence_only": "Coherence only",
    "discriminating": "Discriminating",
    "all_reference_free": "All reference-free",
}


def write_annex_table(cells: list[dict[str, str]], output: Path) -> None:
    """Render the sweep as a LaTeX tabular for the annex."""
    lines = [
        "% Generated by aedist.plot_exp1_reliability — do not edit.",
        r"\begin{tabular}{llrrcr}",
        r"\toprule",
        r"Indicator set & $n$ dims & $\tau$ & \#disqualified & = floor & Spearman $\rho$ \\",
        r"\midrule",
    ]
    prev_set = None
    for cell in cells:
        name = _SET_DISPLAY.get(cell["indicator_set"], cell["indicator_set"])
        if prev_set is not None and cell["indicator_set"] != prev_set:
            lines.append(r"\addlinespace")
        shown = name if cell["indicator_set"] != prev_set else ""
        n_dims = cell["n_dims"] if cell["indicator_set"] != prev_set else ""
        lines.append(
            f"{shown} & {n_dims} & {cell['tau']} & {cell['n_disqualified']} & "
            f"{cell['equals_floor']} & {float(cell['spearman']):.2f} \\\\"
        )
        prev_set = cell["indicator_set"]
    lines += [r"\bottomrule", r"\end{tabular}", ""]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    log.info("Wrote %s", output)


# ── Figure ────────────────────────────────────────────────────────────────────

# One dot-radius in X-axis data units; the maximum (and only) jitter magnitude.
_DOT_RADIUS_X = 0.045
# Minimum vertical gap between stacked labels, in F1 units.
_LABEL_GAP = 0.034
# Horizontal offset from marker to label anchor, in X data units.
_LABEL_DX = 0.16


def _stack_labels(f1s: list[float]) -> list[float]:
    """De-collide label y-positions within one column side (descending order)."""
    placed: list[float] = []
    for y in f1s:
        if placed and placed[-1] - y < _LABEL_GAP:
            y = placed[-1] - _LABEL_GAP
        placed.append(y)
    return placed


def _label_side(model: str, count: int, rank_in_column: int) -> str:
    """Side the label goes on: ticket-set sides first, then balance.

    Low-reliability columns label right; the saturated 5/5 column splits
    left/right so neither side stacks more than ~4 (jitter pairs keep the
    matching side; remaining models alternate by F1 rank).
    """
    if model in JITTER_SIDE:
        return JITTER_SIDE[model]
    if model in LABEL_SIDE:
        return LABEL_SIDE[model]
    if count < N_REPS:
        return "right"
    return "right" if rank_in_column % 2 == 0 else "left"


def make_figure(csv_path: Path, output: Path) -> None:
    """Render the reliability-vs-accuracy scatter to PDF."""
    import matplotlib.pyplot as plt

    from .evaluate import reference_plant_count
    from .util import COLOR_MATCHED

    rel = reliability_by_model(csv_path)
    acc = mean_f1_good_by_model(csv_path)
    models = sorted(rel)

    fig, ax = plt.subplots(figsize=(7.2, 4.6))

    # Group models by reliability column to drive jitter and label stacking.
    by_column: dict[int, list[str]] = defaultdict(list)
    for model in models:
        by_column[rel[model]].append(model)

    for count, column in sorted(by_column.items()):
        column.sort(key=lambda m: -acc[m])
        sides: dict[str, list[str]] = {"left": [], "right": []}
        for rank, model in enumerate(column):
            sides[_label_side(model, count, rank)].append(model)
        for side, members in sides.items():
            sign = -1 if side == "left" else 1
            label_ys = _stack_labels([acc[m] for m in members])
            for model, label_y in zip(members, label_ys, strict=True):
                # Markers sit exactly on (integer count, F1) — the ONLY jitter
                # is the <= one-dot-radius horizontal nudge for the author-set
                # near-coincident pairs in the saturated column.
                x = count + (sign * _DOT_RADIUS_X if model in JITTER_SIDE else 0.0)
                ax.plot(x, acc[model], "o", markersize=6, color=COLOR_MATCHED, zorder=3)
                ax.annotate(
                    model,
                    xy=(x, acc[model]),
                    xytext=(x + sign * _LABEL_DX, label_y),
                    fontsize=7.5,
                    ha="left" if side == "right" else "right",
                    va="center",
                    arrowprops={"arrowstyle": "-", "linewidth": 0.5, "color": "0.6", "shrinkB": 0},
                    zorder=2,
                )

    # The left margin makes room for the one left-labelled model at column 0
    # (qwen3.6-35b-a3b, author-set side) without clipping the axis frame.
    ax.set_xlim(-1.7, 5.9)
    ax.set_xticks(range(N_REPS + 1))
    ax.set_ylim(0.0, max(acc.values()) + 0.08)
    ax.set_xlabel("Reliability — good runs out of 5 (no reference needed)")
    ax.set_ylabel(f"Accuracy — F1 against the {reference_plant_count()}-plant reference")
    ax.set_title(
        "Inaccurate models are also unreliable — and can be screened out\n"
        "good run = no zero on any of 12 quality dimensions",
        fontsize=11,
    )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", linewidth=0.3, alpha=0.5)

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    log.info("Wrote %s", output)


# ── CLI ───────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Reliability-vs-accuracy screen figure + sensitivity sweep (Exp1)"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("experiments/derived/exp1_cross_eval.csv"),
        help="cross-eval CSV (parametric arm, post-0505)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="figure PDF output (skip to not render the figure)",
    )
    parser.add_argument(
        "--sensitivity-csv",
        type=Path,
        default=None,
        help="write the tau x indicator-set sweep CSV here",
    )
    parser.add_argument(
        "--annex-table",
        type=Path,
        default=None,
        help="write the LaTeX annex table for the sweep here",
    )
    args = parser.parse_args(argv)

    if args.output is None and args.sensitivity_csv is None and args.annex_table is None:
        args.output = Path("report/inputs/generated/fig_exp1_reliability.pdf")

    if args.output is not None:
        make_figure(args.input, args.output)
    if args.sensitivity_csv is not None or args.annex_table is not None:
        cells = sensitivity_sweep(load_rows(args.input))
        if args.sensitivity_csv is not None:
            write_sweep_csv(cells, args.sensitivity_csv)
        if args.annex_table is not None:
            write_annex_table(cells, args.annex_table)


if __name__ == "__main__":
    main()
