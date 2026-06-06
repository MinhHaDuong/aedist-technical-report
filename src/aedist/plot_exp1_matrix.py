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

Readability (ticket 0446, author-arbitrated 2026-06-06): the figure targets a
full landscape page (aspect ``page_aspect``). All 170 plant-name labels and all
70 rep rows are kept — at print scale the names are texture, not text. The
y axis carries one label per model (centred on its 5-rep block); status-band
labels sit above the matrix on collision-avoiding levels and replace the old
panel title. Fonts are sized to survive the ~0.4x shrink to page width.

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

from .config import VN_THERMAL_PLANTS_RELEASE_CSV
from .exp1_recognition import (
    STATUS_LABELS,
    STATUS_ORDER,
    load_exp1_recognition,
    top_false_positives,
)
from .plot_method_convergence import _model_size_b
from .util import COLOR_ALERT, COLOR_MATCHED, model_family

log = logging.getLogger(__name__)

# Status column ordering and labels come from the shared exp1_recognition
# library (author-ratified 2026-06-05) so the matrix's column bands and the
# status difficulty table (0434) order statuses identically.
_STATUS_ORDER = STATUS_ORDER
_STATUS_LABELS = STATUS_LABELS


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
    (Formosa phases) keep distinct columns and the reference count stays exact.
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
    page_aspect: float = 1.7,
    models: list[str] | None = None,
    exclude_models: list[str] | None = None,
) -> None:
    """Render the Exp1 recognition matrix as a PDF (and optional macros).

    ``models`` (include list) / ``exclude_models`` filter the run rows by
    model *before* any derivation, so the FP top-N, row ordering, and macros
    are all recomputed for the selected cohort (0446: model-subset versions).
    """
    data = load_exp1_recognition(records_glob, reference_path)
    if models is not None or exclude_models is not None:
        keep = lambda m: (models is None or m in models) and (  # noqa: E731
            exclude_models is None or m not in exclude_models
        )
        data.cells = [c for c in data.cells if keep(c.model)]
        data.fp_presence = {k: v for k, v in data.fp_presence.items() if keep(k[0])}
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
    # Width in inches directly from the column count (`cell_size` inches per
    # column). Height follows `page_aspect`: the figure is meant to fill a
    # rotated A4 page (usable slot ~9.7 x 6.3 in, aspect ~1.55), so rows take
    # the full remaining budget instead of a per-row constant. `page_aspect`
    # applies to the axes core and defaults above the slot ratio because the
    # tight bounding box adds the label margins (plant names below, model
    # names left) mostly to the height (0446).
    gap_cols = 2  # blank columns separating FP panel from the reference matrix
    total_cols = n_fps + gap_cols + n_plants
    fig_w = max(8.0, cell_size * total_cols) * ui_scale
    fig_h = fig_w / page_aspect
    fig, (ax_fp, ax) = plt.subplots(
        1,
        2,
        figsize=(fig_w, fig_h),
        gridspec_kw={"width_ratios": [n_fps + gap_cols, n_plants], "wspace": 0.02},
    )

    tp_cmap = ListedColormap([COLOR_MATCHED])
    fp_cmap = ListedColormap([COLOR_ALERT])

    # Model blocks: contiguous 5-rep groups in row order. The y axis carries
    # one label per model, centred on its block — 14 readable names instead of
    # 70 unreadable `model · rN` repeats (0446).
    model_blocks: list[tuple[str, int, int]] = []  # (model, first_row, last_row)
    for i, (model, _run) in enumerate(runs):
        if model_blocks and model_blocks[-1][0] == model:
            model_blocks[-1] = (model, model_blocks[-1][1], i)
        else:
            model_blocks.append((model, i, i))

    # FP panel (left) — red marks.
    ax_fp.imshow(fp_mat, aspect="auto", cmap=fp_cmap, vmin=0, vmax=1, interpolation="nearest")
    ax_fp.set_xticks(range(n_fps))
    ax_fp.set_xticklabels(fp_names, rotation=90, fontsize=5.5 * ui_scale)
    ax_fp.set_yticks([(first + last) / 2 for _m, first, last in model_blocks])
    ax_fp.set_yticklabels([m for m, _f, _l in model_blocks], fontsize=16 * ui_scale)
    # Title pad lifts both panel titles above the band-label levels so
    # "En projet" (and friends) cannot collide with them (0446).
    title_pad = 85 * ui_scale
    ax_fp.set_title(
        f"{n_fps} most common false positives",
        fontsize=16 * ui_scale,
        color=COLOR_ALERT,
        pad=title_pad,
    )
    ax_fp.tick_params(length=0)
    for s in ax_fp.spines.values():
        s.set_visible(False)
    # Separating rule on the right edge of the FP panel.
    ax_fp.axvline(n_fps - 0.5 + gap_cols / 2, color="black", linewidth=1.0)

    # Recognition matrix (right) — blue marks. Panel title raised above the
    # band labels (author observation 4, 0446).
    ax.imshow(recog, aspect="auto", cmap=tp_cmap, vmin=0, vmax=1, interpolation="nearest")
    ax.set_xticks(range(n_plants))
    ax.set_xticklabels(plant_labels, rotation=90, fontsize=4.5 * ui_scale)
    ax.set_yticks([])
    ax.set_title(
        "Recognized reference plants (status group, then capacity descending)",
        fontsize=16 * ui_scale,
        color=COLOR_MATCHED,
        pad=title_pad,
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
                ax.axvline(j - 0.5, color="black", linewidth=1.2, alpha=0.9)
            start = j
    # Band labels above the matrix on collision-avoiding levels: a label wider
    # than the space left on a level moves one level up and gets a thin leader
    # line down to its band, so narrow bands (Annulée, Retirée) never
    # overprint their neighbours yet stay visually anchored (0446).
    band_fontsize = 15 * ui_scale
    levels_y = [-0.8, -2.9, -5.0]
    pad_cols = 3  # minimum clearance between same-level labels
    level_end = [float("-inf")] * len(levels_y)
    for first, last, status in bands:
        label = _STATUS_LABELS.get(status, status)
        cx = (first + last) / 2
        # Approximate label width in column units (0.6 em per char).
        half_w = len(label) * band_fontsize * 0.6 / 72.0 / cell_size / 2
        for li, ly in enumerate(levels_y):
            if cx - half_w > level_end[li] + pad_cols:
                ax.text(cx, ly, label, ha="center", va="bottom", fontsize=band_fontsize)
                level_end[li] = cx + half_w
                if li > 0:  # raised label: leader line down to its band
                    ax.plot(
                        [cx, cx],
                        [ly + 0.1, -0.4],
                        color="black",
                        linewidth=0.6,
                        alpha=0.6,
                        clip_on=False,
                    )
                break
        else:
            log.warning("Band label %r dropped: no free level", label)

    # Row separators: light between models, stronger between architectural
    # families (horizontal rules across both panels).
    prev_fam = None
    for model, first, _last in model_blocks:
        if first == 0:
            prev_fam = model_family(model)
            continue
        fam = model_family(model)
        heavy = fam != prev_fam
        for a in (ax_fp, ax):
            a.axhline(
                first - 0.5,
                color="black",
                linewidth=1.0 if heavy else 0.3,
                alpha=0.7 if heavy else 0.3,
            )
        prev_fam = fam

    # y > 1 lifts the suptitle clear of the panel titles (raised by
    # `title_pad`); bbox_inches="tight" extends the canvas to include it.
    fig.suptitle(
        "Which Vietnamese thermal assets does each model recognize?",
        fontsize=20 * ui_scale,
        y=1.02,
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
        default=VN_THERMAL_PLANTS_RELEASE_CSV,
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
    parser.add_argument(
        "--page-aspect",
        type=float,
        default=1.7,
        help="Figure width/height ratio; default matches a full landscape A4 page",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=None,
        help="Only include these models (FP list and macros recomputed for the subset)",
    )
    parser.add_argument(
        "--exclude-models",
        nargs="+",
        default=None,
        help="Exclude these models (FP list and macros recomputed for the subset)",
    )
    args = parser.parse_args(argv)

    write_pdf(
        records_glob=args.records_glob,
        reference_path=args.reference,
        output=args.output,
        output_macros=args.output_macros,
        fp_top_n=args.fp_top_n,
        fp_seed=args.fp_seed,
        ui_scale=args.ui_scale,
        page_aspect=args.page_aspect,
        models=args.models,
        exclude_models=args.exclude_models,
    )


if __name__ == "__main__":
    main()
