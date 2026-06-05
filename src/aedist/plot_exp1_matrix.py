"""Generate the Exp1 recognition matrix figure (boolean coverage heatmap).

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.

Unlike ``plot_method_convergence`` (which left-packs each run's recalled
plants), this figure aligns every plant on a fixed column so the reader can see
*which* reference assets each run missed.

Layout:
    * Right panel — recognition matrix. Rows = every (model, run): all 5 reps,
      ordered as ``fig_direct_p1_base`` (architectural family, then effective
      parameter count descending). Columns = reference plants ordered by status
      group, then capacity descending. A filled (blue) cell means the run
      recognized that plant (TP); empty means a miss (FN).
    * Left panel — the 40 most common false positives across all runs, count
      sorted descending (fixed-seed tie shuffle). A filled (red) cell means the
      run emitted that false positive. Visually separated from the reference
      columns by a gap and a rule. Red follows the FP convention (ticket 0403).

Derivation routes through ``aedist.exp1_recognition`` (shared library); the
status difficulty table (ticket 0434) derives the same data independently from
the same mart layer — consistency by common cause, no side-output file.

Usage:
    uv run python -m aedist.plot_exp1_matrix \\
        --records-glob "experiments/outputs/exp1_batch2/*.record.json" \\
        --output report/inputs/generated/fig_exp1_recognition_matrix.pdf \\
        --output-macros report/inputs/generated/macros_exp1_matrix.tex
"""

import argparse
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap

from .config import DEFAULT_REFERENCE
from .exp1_recognition import load_exp1_recognition, top_false_positives
from .plot_method_convergence import _model_size_b
from .util import COLOR_ALERT, COLOR_MATCHED, model_family

log = logging.getLogger(__name__)

# Status column ordering (author-ratified 2026-06-05): operational assets
# first (easiest to recall), then the pipeline statuses, ending with the
# historical/retired tail. Matches the status difficulty table (0434).
_STATUS_ORDER = ["operational", "proposed", "planned", "constructing", "cancelled", "retired"]
_STATUS_LABELS = {
    "operational": "Operational",
    "proposed": "Proposed",
    "planned": "Planned",
    "constructing": "Constructing",
    "cancelled": "Cancelled",
    "retired": "Retired",
}


def _order_runs(model_runs: list[tuple[str, int]], size_by_model: dict[str, float]) -> list:
    """Order (model, run) rows as fig_direct_p1_base: family, size desc, model, run.

    `plot_method_convergence` groups runs by architectural family, then by
    effective parameter count descending, so larger models land higher on the
    inverted Y axis. We reproduce that ordering, then keep all 5 reps per model
    in run-number order (the convergence figure shows only a min/median/max
    trio; this matrix shows every rep).
    """
    return sorted(
        model_runs,
        key=lambda mr: (model_family(mr[0]), -size_by_model[mr[0]], mr[0], mr[1]),
    )


def _order_plants(cells: list) -> tuple[list[int], dict[int, tuple[str, str, float]]]:
    """Order reference plants (by plant_id) by status group, then capacity desc.

    Returns (ordered_plant_ids, info) where info[plant_id] = (name, status,
    capacity_mw). Columns are keyed by plant_id so same-name reference plants
    (Formosa phases) keep distinct columns and the reference count stays at 163.
    """
    info: dict[int, tuple[str, str, float]] = {}
    for c in cells:
        info.setdefault(c.plant_id, (c.plant_name, c.status, c.capacity_mw))
    rank = {s: i for i, s in enumerate(_STATUS_ORDER)}
    ordered = sorted(
        info.keys(),
        key=lambda pid: (rank.get(info[pid][1], 999), -info[pid][2]),
    )
    return ordered, info


def write_pdf(
    records_glob: str,
    reference_path: Path,
    output: Path,
    output_macros: Path | None = None,
    fp_top_n: int = 40,
    fp_seed: int = 42,
    cell_size: float = 0.11,
    ui_scale: float = 1.0,
) -> None:
    """Render the Exp1 recognition matrix as a PDF (and optional macros)."""
    data = load_exp1_recognition(records_glob, reference_path)
    if not data.cells:
        log.warning("No recognition data for pattern: %s", records_glob)
        return

    # Plant (column) order, keyed by plant_id.
    plant_order, plant_info = _order_plants(data.cells)
    n_plants = len(plant_order)
    plant_col = {pid: j for j, pid in enumerate(plant_order)}
    plant_labels = [plant_info[pid][0] for pid in plant_order]

    # Run (row) order.
    run_recog: dict[tuple[str, int], dict[int, bool]] = {}
    for c in data.cells:
        run_recog.setdefault((c.model, c.run), {})[c.plant_id] = c.recognized
    size_by_model: dict[str, float] = {}
    size_class_by_model: dict[str, str | None] = {}
    for c in data.cells:
        size_class_by_model.setdefault(c.model, c.size_class)
    for model, sc in size_class_by_model.items():
        size_by_model[model] = _model_size_b(model, sc)
    runs = _order_runs(list(run_recog.keys()), size_by_model)
    n_runs = len(runs)

    # Recognition matrix: NaN = empty (miss), 1 = recognized (TP).
    recog = np.full((n_runs, n_plants), np.nan)
    for i, (model, run) in enumerate(runs):
        for pid, hit in run_recog[(model, run)].items():
            if hit:
                recog[i, plant_col[pid]] = 1.0

    # FP panel: top-N false positives as columns; per-run presence.
    top_fps = top_false_positives(data.fp_presence, top_n=fp_top_n, seed=fp_seed)
    fp_names = [name for name, _ in top_fps]
    n_fps = len(fp_names)
    fp_col = {name: j for j, name in enumerate(fp_names)}
    fp_mat = np.full((n_runs, n_fps), np.nan)
    for i, (model, run) in enumerate(runs):
        for name in data.fp_presence.get((model, run), set()):
            if name in fp_col:
                fp_mat[i, fp_col[name]] = 1.0

    # --- figure geometry ----------------------------------------------------
    # Size in inches directly from the cell counts so each cell stays roughly
    # square and labels remain legible. `cell_size` is inches per cell.
    gap_cols = 2  # blank columns separating FP panel from the reference matrix
    total_cols = n_fps + gap_cols + n_plants
    fig_w = max(8.0, cell_size * total_cols) * ui_scale
    fig_h = max(5.0, cell_size * n_runs * 1.6) * ui_scale
    fig, (ax_fp, ax) = plt.subplots(
        1,
        2,
        figsize=(fig_w, fig_h),
        gridspec_kw={"width_ratios": [n_fps + gap_cols, n_plants], "wspace": 0.02},
    )

    tp_cmap = ListedColormap([COLOR_MATCHED])
    fp_cmap = ListedColormap([COLOR_ALERT])

    # FP panel (left) — red marks.
    ax_fp.imshow(fp_mat, aspect="auto", cmap=fp_cmap, vmin=0, vmax=1, interpolation="nearest")
    ax_fp.set_xticks(range(n_fps))
    ax_fp.set_xticklabels(fp_names, rotation=90, fontsize=5.5 * ui_scale)
    ax_fp.set_yticks(range(n_runs))
    ax_fp.set_yticklabels([f"{m} · r{r}" for m, r in runs], fontsize=5.5 * ui_scale)
    ax_fp.set_title(f"{n_fps} most common false positives", fontsize=8 * ui_scale, color=COLOR_ALERT)
    ax_fp.tick_params(length=0)
    for s in ax_fp.spines.values():
        s.set_visible(False)
    # Separating rule on the right edge of the FP panel.
    ax_fp.axvline(n_fps - 0.5 + gap_cols / 2, color="black", linewidth=1.0)

    # Recognition matrix (right) — blue marks.
    ax.imshow(recog, aspect="auto", cmap=tp_cmap, vmin=0, vmax=1, interpolation="nearest")
    ax.set_xticks(range(n_plants))
    ax.set_xticklabels(plant_labels, rotation=90, fontsize=4.5 * ui_scale)
    ax.set_yticks([])
    ax.set_title(
        "Recognized reference plants (status group, then capacity descending)",
        fontsize=8 * ui_scale,
        color=COLOR_MATCHED,
    )
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)

    # Status group separators + centred labels along the top. Build each band
    # as (start_col, end_col, status) so the label uses the band's own status.
    bands: list[tuple[int, int, str]] = []
    start = 0
    for j in range(1, n_plants + 1):
        if j == n_plants or plant_info[plant_order[j]][1] != plant_info[plant_order[start]][1]:
            bands.append((start, j - 1, plant_info[plant_order[start]][1]))
            if j < n_plants:
                ax.axvline(j - 0.5, color="black", linewidth=0.6, alpha=0.6)
            start = j
    for first, last, status in bands:
        ax.text(
            (first + last) / 2,
            -1.5,
            _STATUS_LABELS.get(status, status),
            ha="center",
            va="bottom",
            fontsize=6 * ui_scale,
        )

    # Architectural-family separators (horizontal rules across both panels).
    prev_fam = None
    for i, (model, _run) in enumerate(runs):
        fam = model_family(model)
        if prev_fam is not None and fam != prev_fam:
            for a in (ax_fp, ax):
                a.axhline(i - 0.5, color="black", linewidth=0.4, alpha=0.4)
        prev_fam = fam

    fig.suptitle(
        "Which Vietnamese thermal assets does each model recognize?",
        fontsize=10 * ui_scale,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=200, bbox_inches="tight")
    plt.close(fig)
    log.info("Wrote recognition matrix to %s", output)
    log.info("  %d runs x %d plants; %d FP columns", n_runs, n_plants, n_fps)

    if output_macros is not None:
        output_macros.parent.mkdir(parents=True, exist_ok=True)
        output_macros.write_text(
            "% Auto-generated by aedist.plot_exp1_matrix — do not edit.\n"
            f"\\newcommand{{\\ExpOneMatrixPlants}}{{{n_plants}}}\n"
            f"\\newcommand{{\\ExpOneMatrixRuns}}{{{n_runs}}}\n"
            f"\\newcommand{{\\ExpOneMatrixFPs}}{{{n_fps}}}\n",
            encoding="utf-8",
        )
        log.info("Wrote macros to %s", output_macros)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Generate the Exp1 recognition matrix figure (boolean heatmap)"
    )
    parser.add_argument(
        "--records-glob",
        default="experiments/outputs/exp1_batch2/*.record.json",
        help="Glob for exp1_batch2 record.json files",
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=DEFAULT_REFERENCE,
        help="Reference CSV (gold list); read at build time, no hardcoded count",
    )
    parser.add_argument("--output", type=Path, required=True, help="Output PDF path")
    parser.add_argument(
        "--output-macros",
        type=Path,
        default=None,
        help="Optional .tex macros file (plant/run/FP counts)",
    )
    parser.add_argument("--fp-top-n", type=int, default=40, help="Top-N false positives to show")
    parser.add_argument(
        "--fp-seed", type=int, default=42, help="Seed for FP tie-breaking (rebuild-stable)"
    )
    parser.add_argument("--ui-scale", type=float, default=1.0, help="Global font/size scale")
    args = parser.parse_args(argv)

    write_pdf(
        records_glob=args.records_glob,
        reference_path=args.reference,
        output=args.output,
        output_macros=args.output_macros,
        fp_top_n=args.fp_top_n,
        fp_seed=args.fp_seed,
        ui_scale=args.ui_scale,
    )


if __name__ == "__main__":
    main()
