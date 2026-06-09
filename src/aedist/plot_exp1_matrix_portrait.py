"""Generate the Exp1 recognition matrix figure — transposed portrait variant.

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.

Transposed orientation: plant names on rows (read horizontally, no rotation),
runs as columns with a 3-level hierarchical header (family / version / run).

Legibility rationale (ticket 0451): the landscape variant (plot_exp1_matrix.py)
accepts texture-level plant labels (4pt at print scale, 0446). Portrait puts
the reference plants on rows so their names read left-to-right, which is the
only orientation where they can be genuinely legible. Physics: ~180 rows on
a single A4 portrait page gives ~4pt labels — below the ~5-6pt readability
floor. The solution is a two-page split by lifecycle stage (row counts are
derived from the reference at build time):

  Page 1 — terminal/active assets: operational + retired + cancelled
  Page 2 — pre-operational assets: proposed + planned + constructing

Both pages give ≥7pt per row at usable A4 portrait height (~9.7in), verified
empirically at build time (logged as INFO). Page 3 shows the top-N false
positives (rows = top-N FPs, columns = runs).

3-level column header (ticket 0451 spec): family-level spanning bar (claude /
deepseek / gpt / mistral / qwen), then version-level spanning bar (opus-4.6,
v4-pro, 5.5, …), then individual run labels (r1…r5). Levels are drawn as
text + horizontal rules on a reserved header band above the matrix axes.

Usage:
    uv run python -m aedist.plot_exp1_matrix_portrait \\
        --records-glob "experiments/outputs/exp1_batch2/*.record.json" \\
        --output report/inputs/generated/fig_exp1_recognition_matrix_portrait.pdf
"""

import argparse
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import ListedColormap

from .config import VN_THERMAL_PLANTS_RELEASE_CSV
from .exp1_recognition import (
    STATUS_LABELS_EN,
    load_exp1_recognition,
    top_false_positives,
)
from .plot_exp1_matrix import _order_plants, _order_runs
from .plot_method_convergence import _model_size_b
from .util import COLOR_ALERT, COLOR_MATCHED, model_family, model_family_color

log = logging.getLogger(__name__)

# A4 portrait usable area in inches (ISO 216: 210×297mm, typical margins).
_A4_USABLE_W = 6.7   # in  (full width: ~8.27in, minus margins)
_A4_USABLE_H = 9.7   # in  (full height: ~11.7in, minus margins)
_A4_FIG_W = 8.5      # figure canvas width (includes left-margin plant labels)
_A4_FIG_H = 12.0     # figure canvas height (includes header band)

# Status groups split into two pages:
#   Page 1 — terminal+active: operational, retired, cancelled
#   Page 2 — pipeline: proposed, planned, constructing
_PAGE_GROUPS = [
    ("terminal_active", ["operational", "retired", "cancelled"]),
    ("pipeline", ["proposed", "planned", "constructing"]),
]

# Header band height per level, in axes-fraction units (relative to n_rows).
_HEADER_LEVELS = 3    # family / version / run


def _build_run_header(
    runs: list[tuple[str, int]],
) -> tuple[list[str], list[tuple[str, int, int]], list[tuple[str, int, int]]]:
    """Build the 3-level column header structure.

    Returns:
        run_labels: per-column leaf label ("r1"…"r5").
        version_spans: list of (label, first_col, last_col) for version-level.
        family_spans: list of (label, first_col, last_col) for family-level.
    """
    run_labels = [f"r{run}" for _model, run in runs]

    # Version spans: group by model (each model has 5 consecutive reps).
    version_spans: list[tuple[str, int, int]] = []
    for j, (model, _run) in enumerate(runs):
        if version_spans and version_spans[-1][0] == model:
            version_spans[-1] = (model, version_spans[-1][1], j)
        else:
            version_spans.append((model, j, j))

    # Family spans: group by architectural family.
    family_spans: list[tuple[str, int, int]] = []
    for j, (model, _run) in enumerate(runs):
        fam = model_family(model)
        if family_spans and family_spans[-1][0] == fam:
            family_spans[-1] = (fam, family_spans[-1][1], j)
        else:
            family_spans.append((fam, j, j))

    return run_labels, version_spans, family_spans


def _draw_hierarchical_header(
    ax: plt.Axes,
    runs: list[tuple[str, int]],
    run_labels: list[str],
    version_spans: list[tuple[str, int, int]],
    family_spans: list[tuple[str, int, int]],
    n_cols: int,
    fontsize_run: float,
    fontsize_version: float,
    fontsize_family: float,
    header_rows: float,
) -> None:
    """Draw 3-level hierarchical header above the matrix on ax.

    The header occupies [−header_rows, 0) in the y-axis (which runs 0..n_rows
    with origin at top after set_ylim). Labels are drawn at y < 0 using
    clip_on=False; horizontal rules separate levels.

    Args:
        ax: the matrix axes.
        runs: ordered (model, run) list.
        run_labels: per-column leaf label.
        version_spans, family_spans: from _build_run_header().
        n_cols: total column count (== len(runs)).
        fontsize_*: font sizes in points.
        header_rows: total header height in row units.
    """
    # Level positions (y < 0): family at top, version in middle, run at bottom.
    # header_rows is split: family=40%, version=35%, run=25%.
    y_family_top = -header_rows
    y_version_top = -header_rows * 0.60
    y_run_top = -header_rows * 0.25

    # Run-level labels (bottom of header, just above row 0).
    for j, label in enumerate(run_labels):
        ax.text(
            j, y_run_top * 0.5, label,
            ha="center", va="center",
            fontsize=fontsize_run,
            clip_on=False,
        )

    # Version-level spanning labels with thin vertical separators.
    for label, first, last in version_spans:
        cx = (first + last) / 2
        # Shorten model name for display: strip "claude-", "deepseek-v", etc.
        # and keep only the version tag.
        parts = label.split("-")
        # Keep last meaningful tokens (version number / name).
        short = "-".join(parts[1:]) if len(parts) > 2 else label
        ax.text(
            cx, (y_version_top + y_run_top) / 2, short,
            ha="center", va="center",
            fontsize=fontsize_version,
            clip_on=False,
        )
        if last < n_cols - 1:
            ax.axvline(last + 0.5, ymin=0, ymax=1, color="black",
                       linewidth=0.4, alpha=0.4, clip_on=True)

    # Family-level spanning labels with colored background bands and thick
    # vertical separators between families.
    for fam, first, last in family_spans:
        cx = (first + last) / 2
        color = model_family_color(
            next((m for m, _r in runs if model_family(m) == fam), fam)
        )
        ax.text(
            cx, (y_family_top + y_version_top) / 2, fam.upper(),
            ha="center", va="center",
            fontsize=fontsize_family,
            fontweight="bold",
            color=color,
            clip_on=False,
        )
        # Thick separator between families.
        if last < n_cols - 1:
            ax.axvline(last + 0.5, ymin=0, ymax=1, color="black",
                       linewidth=1.0, alpha=0.7, clip_on=True)

    # Horizontal rules separating header levels.
    for y_rule in [y_run_top, y_version_top]:
        ax.axhline(y_rule, color="black", linewidth=0.5, alpha=0.5,
                   clip_on=False, xmin=0, xmax=1)


def _draw_page(
    pdf: PdfPages,
    page_label: str,
    plant_order_page: list[int],
    plant_info: dict,
    recog: np.ndarray,
    run_row: dict,
    runs: list[tuple[str, int]],
    run_labels: list[str],
    version_spans: list[tuple[str, int, int]],
    family_spans: list[tuple[str, int, int]],
    n_plants: int,
    n_runs: int,
    tp_cmap: object,
    ui_scale: float,
) -> None:
    """Render one page of the portrait matrix and append to pdf."""
    # Per-row height in points (usable height / n_rows * 72).
    pt_per_row = _A4_USABLE_H * 72 / n_plants
    log.info(
        "  Page '%s': %d rows × %d cols → %.1f pt/row (target ≥5pt)",
        page_label, n_plants, n_runs, pt_per_row,
    )

    # Header band height in row units — reserve ~15% of page.
    header_rows = max(3, int(n_plants * 0.15))

    fig, ax = plt.subplots(figsize=(_A4_FIG_W, _A4_FIG_H))

    # Build sub-matrix for this page.
    sub_mat = np.full((n_plants, n_runs), np.nan)
    for i, pid in enumerate(plant_order_page):
        for j, run_key in enumerate(runs):
            hit = run_row.get(run_key, {}).get(pid)
            if hit:
                sub_mat[i, j] = 1.0

    ax.imshow(
        sub_mat, aspect="auto", cmap=tp_cmap, vmin=0, vmax=1,
        interpolation="nearest",
    )

    # Row labels (plant names) on the left y-axis — this is the portrait win.
    plant_labels_page = [plant_info[pid][0] for pid in plant_order_page]
    ax.set_yticks(range(n_plants))
    ax.set_yticklabels(plant_labels_page, fontsize=6.5 * ui_scale)
    ax.tick_params(axis="y", length=0)
    ax.yaxis.set_tick_params(pad=2)

    # Column ticks (run labels) suppressed — header band carries them.
    ax.set_xticks([])

    for s in ax.spines.values():
        s.set_visible(False)

    # Status-band horizontal separators and right-margin labels.
    # Within a page group, identify sub-band boundaries by status.
    prev_status = plant_info[plant_order_page[0]][1]
    status_start = 0
    band_list: list[tuple[int, int, str]] = []
    for i, pid in enumerate(plant_order_page):
        status = plant_info[pid][1]
        if status != prev_status:
            band_list.append((status_start, i - 1, prev_status))
            ax.axhline(i - 0.5, color="black", linewidth=1.2, alpha=0.7)
            status_start = i
            prev_status = status
    band_list.append((status_start, n_plants - 1, prev_status))

    # Status labels on the right margin.
    fontsize_status = 8.0 * ui_scale
    for first_row, last_row, status in band_list:
        label = STATUS_LABELS_EN.get(status, status)
        cy = (first_row + last_row) / 2
        ax.text(
            n_runs + 0.5, cy, label,
            ha="left", va="center",
            fontsize=fontsize_status,
            color="black",
            clip_on=False,
        )

    # Model-family separators (column direction): thin between models,
    # thick between families — matches landscape convention.
    prev_fam = None
    for j, (model, _run) in enumerate(runs):
        if j == 0:
            prev_fam = model_family(model)
            continue
        fam = model_family(model)
        if _run == 1:  # first rep of new model
            heavy = fam != prev_fam
            ax.axvline(
                j - 0.5,
                color="black",
                linewidth=1.0 if heavy else 0.3,
                alpha=0.7 if heavy else 0.3,
            )
        if fam != prev_fam:
            prev_fam = fam

    # 3-level hierarchical header above the matrix.
    _draw_hierarchical_header(
        ax=ax,
        runs=runs,
        run_labels=run_labels,
        version_spans=version_spans,
        family_spans=family_spans,
        n_cols=n_runs,
        fontsize_run=5.5 * ui_scale,
        fontsize_version=5.5 * ui_scale,
        fontsize_family=7.0 * ui_scale,
        header_rows=header_rows,
    )

    # Pin y-limits: matrix rows 0..n_plants-1 in row space, header below 0.
    ax.set_ylim(n_plants - 0.5, -header_rows)

    ax.set_title(
        f"Recognized reference plants — {page_label.replace('_', ' ').title()}",
        fontsize=10 * ui_scale,
        color=COLOR_MATCHED,
        pad=4,
    )

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _draw_fp_page(
    pdf: PdfPages,
    fp_names: list[str],
    fp_mat: np.ndarray,
    runs: list[tuple[str, int]],
    run_labels: list[str],
    version_spans: list[tuple[str, int, int]],
    family_spans: list[tuple[str, int, int]],
    n_runs: int,
    fp_cmap: object,
    ui_scale: float,
) -> None:
    """Render the false-positive page (rows = FP names, cols = runs)."""
    n_fps = len(fp_names)
    pt_per_row = _A4_USABLE_H * 72 / n_fps
    log.info(
        "  FP page: %d rows × %d cols → %.1f pt/row",
        n_fps, n_runs, pt_per_row,
    )

    header_rows = max(3, int(n_fps * 0.15))

    fig, ax = plt.subplots(figsize=(_A4_FIG_W, _A4_FIG_H))

    ax.imshow(
        fp_mat, aspect="auto", cmap=fp_cmap, vmin=0, vmax=1,
        interpolation="nearest",
    )

    ax.set_yticks(range(n_fps))
    ax.set_yticklabels(fp_names, fontsize=6.5 * ui_scale)
    ax.tick_params(axis="y", length=0)
    ax.yaxis.set_tick_params(pad=2)
    ax.set_xticks([])

    for s in ax.spines.values():
        s.set_visible(False)

    # Model/family column separators.
    prev_fam = None
    for j, (model, _run) in enumerate(runs):
        if j == 0:
            prev_fam = model_family(model)
            continue
        fam = model_family(model)
        if _run == 1:
            heavy = fam != prev_fam
            ax.axvline(
                j - 0.5,
                color="black",
                linewidth=1.0 if heavy else 0.3,
                alpha=0.7 if heavy else 0.3,
            )
        if fam != prev_fam:
            prev_fam = fam

    _draw_hierarchical_header(
        ax=ax,
        runs=runs,
        run_labels=run_labels,
        version_spans=version_spans,
        family_spans=family_spans,
        n_cols=n_runs,
        fontsize_run=5.5 * ui_scale,
        fontsize_version=5.5 * ui_scale,
        fontsize_family=7.0 * ui_scale,
        header_rows=header_rows,
    )

    ax.set_ylim(n_fps - 0.5, -header_rows)

    ax.set_title(
        f"{n_fps} most common false positives",
        fontsize=10 * ui_scale,
        color=COLOR_ALERT,
        pad=4,
    )

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def write_pdf(
    records_glob: str,
    reference_path: Path,
    output: Path,
    fp_top_n: int = 40,
    fp_seed: int = 42,
    ui_scale: float = 1.0,
    models: list[str] | None = None,
    exclude_models: list[str] | None = None,
) -> None:
    """Render the Exp1 recognition matrix portrait variant as a multi-page PDF.

    Produces three pages:
    - Page 1: operational + retired + cancelled plants (~78 rows × 70 cols).
    - Page 2: proposed + planned + constructing plants (~98 rows × 70 cols).
    - Page 3: top-N false positives (~40 rows × 70 cols).

    Plant names are row labels (read left-to-right, legible at ≥7pt at A4
    usable height). Columns carry a 3-level hierarchical header: family /
    version / run. Legibility is logged (pt/row) so "measured, not asserted"
    (ticket 0451 exit criterion).
    """
    data = load_exp1_recognition(records_glob, reference_path)
    if models is not None or exclude_models is not None:

        def keep(m: str) -> bool:
            return (models is None or m in models) and (
                exclude_models is None or m not in exclude_models
            )

        data.cells = [c for c in data.cells if keep(c.model)]
        data.fp_presence = {k: v for k, v in data.fp_presence.items() if keep(k[0])}
    if not data.cells:
        log.warning("No recognition data for pattern: %s", records_glob)
        return

    # Plant and run ordering (reuse landscape helpers).
    plant_order, plant_info = _order_plants(data.cells)

    run_recog: dict[tuple[str, int], dict[int, bool]] = {}
    for c in data.cells:
        run_recog.setdefault((c.model, c.run), {})[c.plant_id] = c.recognized

    size_class_by_model: dict[str, str | None] = {}
    for c in data.cells:
        size_class_by_model.setdefault(c.model, c.size_class)
    size_by_model = {m: _model_size_b(m, sc) for m, sc in size_class_by_model.items()}

    runs = _order_runs(list(run_recog.keys()), size_by_model)
    n_runs = len(runs)
    n_plants = len(plant_order)

    # Build run→column index map and per-run recognition lookup.
    run_row = run_recog  # (model, run) -> {plant_id: bool}

    # Column header structure.
    run_labels, version_spans, family_spans = _build_run_header(runs)

    # FP panel data.
    top_fps = top_false_positives(data.fp_presence, top_n=fp_top_n, seed=fp_seed)
    fp_names = [name for name, _ in top_fps]
    n_fps = len(fp_names)
    fp_col = {name: j for j, name in enumerate(fp_names)}
    fp_mat = np.full((n_fps, n_runs), np.nan)
    for j, run_key in enumerate(runs):
        for name in data.fp_presence.get(run_key, set()):
            if name in fp_col:
                fp_mat[fp_col[name], j] = 1.0

    tp_cmap = ListedColormap([COLOR_MATCHED])
    fp_cmap = ListedColormap([COLOR_ALERT])

    log.info(
        "Portrait matrix: %d plants × %d runs (pages: %d status groups + 1 FP)",
        n_plants, n_runs, len(_PAGE_GROUPS),
    )

    output.parent.mkdir(parents=True, exist_ok=True)

    with PdfPages(output) as pdf:
        for page_label, status_list in _PAGE_GROUPS:
            # Select plant rows for this page.
            status_set = set(status_list)
            page_plant_order = [
                pid for pid in plant_order
                if plant_info[pid][1] in status_set
            ]
            if not page_plant_order:
                log.warning("Page '%s': no plants matched statuses %s", page_label, status_list)
                continue

            _draw_page(
                pdf=pdf,
                page_label=page_label,
                plant_order_page=page_plant_order,
                plant_info=plant_info,
                recog=None,  # unused — draw_page builds its own sub_mat
                run_row=run_row,
                runs=runs,
                run_labels=run_labels,
                version_spans=version_spans,
                family_spans=family_spans,
                n_plants=len(page_plant_order),
                n_runs=n_runs,
                tp_cmap=tp_cmap,
                ui_scale=ui_scale,
            )

        _draw_fp_page(
            pdf=pdf,
            fp_names=fp_names,
            fp_mat=fp_mat,
            runs=runs,
            run_labels=run_labels,
            version_spans=version_spans,
            family_spans=family_spans,
            n_runs=n_runs,
            fp_cmap=fp_cmap,
            ui_scale=ui_scale,
        )

    log.info("Wrote portrait recognition matrix to %s (%d pages)", output, len(_PAGE_GROUPS) + 1)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Generate the Exp1 recognition matrix — portrait (transposed) variant"
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
        help="Reference CSV (gold list)",
    )
    parser.add_argument("--output", type=Path, required=True, help="Output PDF path")
    parser.add_argument("--fp-top-n", type=int, default=40, help="Top-N false positives to show")
    parser.add_argument("--fp-seed", type=int, default=42, help="Seed for FP tie-breaking")
    parser.add_argument("--ui-scale", type=float, default=1.0, help="Global font/size scale")
    parser.add_argument(
        "--models",
        nargs="+",
        default=None,
        help="Only include these models",
    )
    parser.add_argument(
        "--exclude-models",
        nargs="+",
        default=None,
        help="Exclude these models",
    )
    args = parser.parse_args(argv)

    write_pdf(
        records_glob=args.records_glob,
        reference_path=args.reference,
        output=args.output,
        fp_top_n=args.fp_top_n,
        fp_seed=args.fp_seed,
        ui_scale=args.ui_scale,
        models=args.models,
        exclude_models=args.exclude_models,
    )


if __name__ == "__main__":
    main()
