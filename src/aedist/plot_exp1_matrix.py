"""Generate Exp1 recognition matrix figure (boolean heatmap).

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.

Rows: (model × run) pairs, ordered by model family then parameter count.
Columns: reference plants, ordered by status group then capacity descending.
Left panel: Top 40 false positives across all runs.

Usage:
    uv run python -m aedist.plot_exp1_matrix \\
        --records-glob "experiments/outputs/exp1_batch2/*.record.json" \\
        --output report/inputs/generated/fig_exp1_recognition_matrix.pdf
"""

import argparse
import logging
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from .config import DEFAULT_REFERENCE
from .exp1_recognition import get_top_false_positives, load_exp1_recognition_matrix
from .plot_method_convergence import _model_size_b
from .util import model_family

log = logging.getLogger(__name__)

# Status ordering for columns (ratified 2026-06-05)
_STATUS_ORDER = ["operational", "proposed", "planned", "constructing", "cancelled", "retired"]


def _sort_key_model_run(model_run: tuple[str, int], model_sizes: dict[str, float]) -> tuple:
    """Sort key for (model, run) pairs: family, then size desc, then model, then run."""
    model, run = model_run
    return (model_family(model), -model_sizes[model], model, run)


def _order_plants_by_status_capacity(
    cells: list,
) -> tuple[list[str], dict[str, tuple[str, float]]]:
    """Order plants by status group (status order), then capacity descending within group.

    Returns:
        (plant_names_ordered, plant_metadata)
        plant_metadata[name] = (status, capacity_mw)
    """
    # Collect unique plants with their status and capacity
    plant_info: dict[str, tuple[str, float]] = {}
    for cell in cells:
        if cell.plant_name not in plant_info:
            plant_info[cell.plant_name] = (cell.status, cell.capacity_mw)

    # Sort by status group, then capacity desc
    status_rank = {s: i for i, s in enumerate(_STATUS_ORDER)}
    ordered_names = sorted(
        plant_info.keys(),
        key=lambda name: (
            status_rank.get(plant_info[name][0], 999),  # status group
            -plant_info[name][1],  # capacity descending
        ),
    )

    return ordered_names, plant_info


def write_pdf(
    records_glob: str,
    reference_path: Path,
    output: Path,
    fig_width: float = 14.0,
    fig_height: float = 10.0,
    fp_panel_width_ratio: float = 0.2,
    fp_top_n: int = 40,
    fp_seed: int = 42,
) -> None:
    """Generate the Exp1 recognition matrix figure as PDF.

    Args:
        records_glob: Glob pattern for exp1_batch2 record.json files
        reference_path: Path to reference CSV (vietnam_thermal_v1.csv)
        output: Output PDF path
        fig_width: Figure width in inches
        fig_height: Figure height in inches
        fp_panel_width_ratio: Width ratio for FP panel (0.2 = 20% of width)
        fp_top_n: Number of top FPs to show
        fp_seed: Random seed for FP tie-breaking
    """
    # Load recognition matrix
    cells = load_exp1_recognition_matrix(records_glob, reference_path)
    if not cells:
        log.warning("No recognition data found for pattern: %s", records_glob)
        return

    # Build (model, run) → {plant: recognized} map
    run_recognition: dict[tuple[str, int], dict[str, bool]] = defaultdict(dict)
    for cell in cells:
        run_recognition[(cell.model, cell.run)][cell.plant_name] = cell.recognized

    # Order plants (columns)
    plant_names_ordered, plant_metadata = _order_plants_by_status_capacity(cells)

    # Order runs (rows): family → size → model → run
    model_runs = sorted(run_recognition.keys())
    # Resolve size per model (same as plot_method_convergence.py)
    model_sizes: dict[str, float] = {}
    for model, _ in model_runs:
        if model not in model_sizes:
            # Use empty size_class for simplicity — _model_size_b handles it
            model_sizes[model] = _model_size_b(model, size_class=None)
    model_runs.sort(key=lambda mr: _sort_key_model_run(mr, model_sizes))

    # Build boolean matrix
    n_runs = len(model_runs)
    n_plants = len(plant_names_ordered)
    matrix = np.zeros((n_runs, n_plants), dtype=float)
    for i, (model, run) in enumerate(model_runs):
        for j, plant in enumerate(plant_names_ordered):
            if run_recognition[(model, run)].get(plant, False):
                matrix[i, j] = 1.0

    # Get top FPs
    fp_list = get_top_false_positives(records_glob, reference_path, top_n=fp_top_n, seed=fp_seed)
    n_fps = len(fp_list)
    fp_matrix = np.zeros((n_runs, n_fps), dtype=float)
    # For FPs, check if the plant appears in the system output (would need reconcile data)
    # For now, just show FP names; actual per-run FP data requires more complex logic
    # Simplification: leave FP panel as placeholder structure

    # Create figure with two panels
    fig = plt.figure(figsize=(fig_width, fig_height))
    gs = fig.add_gridspec(
        1, 2, width_ratios=[fp_panel_width_ratio, 1 - fp_panel_width_ratio], wspace=0.05
    )

    # FP panel (left)
    ax_fp = fig.add_subplot(gs[0])
    # Placeholder: just show FP names as Y labels, empty matrix for now
    # Full implementation would require per-run FP tracking
    ax_fp.set_xlim(-0.5, 0.5)
    ax_fp.set_ylim(-0.5, n_runs - 0.5)
    ax_fp.set_xticks([])
    ax_fp.set_yticks(range(n_runs))
    ax_fp.set_yticklabels([])
    ax_fp.set_ylabel("Runs (model × rep)", fontsize=9)
    ax_fp.text(
        0,
        n_runs,
        f"Top {fp_top_n} FPs\n(placeholder)",
        ha="center",
        va="bottom",
        fontsize=8,
        style="italic",
    )
    ax_fp.spines["top"].set_visible(False)
    ax_fp.spines["right"].set_visible(False)
    ax_fp.spines["bottom"].set_visible(False)

    # Recognition matrix panel (right)
    ax = fig.add_subplot(gs[1])
    im = ax.imshow(
        matrix,
        aspect="auto",
        cmap="Blues",
        vmin=0,
        vmax=1,
        interpolation="nearest",
    )

    # X-axis: plant names (rotated, small font)
    ax.set_xticks(range(n_plants))
    ax.set_xticklabels(plant_names_ordered, rotation=90, ha="right", fontsize=5)
    ax.set_xlabel("Reference plants (ordered: status × capacity desc)", fontsize=9)

    # Y-axis: model × run labels
    run_labels = [f"{model}\nR{run}" for model, run in model_runs]
    ax.set_yticks(range(n_runs))
    ax.set_yticklabels(run_labels, fontsize=6)
    ax.set_ylabel("Model × Run", fontsize=9)

    # Add status group separators (vertical lines)
    status_boundaries = []
    prev_status = None
    for i, plant in enumerate(plant_names_ordered):
        status = plant_metadata[plant][0]
        if prev_status is not None and status != prev_status:
            status_boundaries.append(i - 0.5)
        prev_status = status
    for x in status_boundaries:
        ax.axvline(x, color="gray", linewidth=0.5, alpha=0.5)

    # Add model family separators (horizontal lines)
    family_boundaries = []
    prev_family = None
    for i, (model, _) in enumerate(model_runs):
        fam = model_family(model)
        if prev_family is not None and fam != prev_family:
            family_boundaries.append(i - 0.5)
        prev_family = fam
    for y in family_boundaries:
        ax.axhline(y, color="gray", linewidth=0.5, alpha=0.5)

    plt.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150, bbox_inches="tight")
    plt.close(fig)
    log.info("Wrote recognition matrix to %s", output)
    log.info("  Matrix size: %d runs × %d plants", n_runs, n_plants)
    log.info("  Recognition rate: %.1f%%", 100 * matrix.sum() / matrix.size)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Generate Exp1 recognition matrix figure (boolean heatmap)"
    )
    parser.add_argument(
        "--records-glob",
        required=True,
        help="Glob pattern for exp1_batch2 record.json files",
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=DEFAULT_REFERENCE,
        help="Reference CSV (vietnam_thermal_v1.csv)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output PDF path",
    )
    parser.add_argument(
        "--fp-top-n",
        type=int,
        default=40,
        help="Number of top FPs to show in left panel",
    )
    parser.add_argument(
        "--fp-seed",
        type=int,
        default=42,
        help="Random seed for FP tie-breaking (rebuild-stable)",
    )
    args = parser.parse_args(argv)

    write_pdf(
        records_glob=args.records_glob,
        reference_path=args.reference,
        output=args.output,
        fp_top_n=args.fp_top_n,
        fp_seed=args.fp_seed,
    )


if __name__ == "__main__":
    main()
