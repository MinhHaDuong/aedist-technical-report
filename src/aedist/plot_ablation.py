"""Generate ablation result figures from measurements.jsonl.

Two figures:
1. Strip plot — prompt variants on Y, plant count on X, TP/FP dots
   (same visual language as fig_method_convergence.pdf)
2. Heatmap — 6 modules × 2 effects (composition ΔF1, ablation ΔF1)

Usage:
    uv run python -m aedist.plot_ablation \
        --strip slides/inputs/generated/fig_ablation_strip.pdf
    uv run python -m aedist.plot_ablation \
        --heatmap report/inputs/generated/fig_ablation_heatmap.pdf
"""

import argparse
import logging
from collections import defaultdict
from pathlib import Path

from .measurements import load
from .util import COLOR_HALLUC, COLOR_MATCHED, COLOR_REFERENCE, COLOR_REFUSAL, normalize_model

log = logging.getLogger(__name__)

# The 7 prompt modules in display order
_MODULES = [
    "persona",
    "overview",
    "citation_columns",
    "sourcing_ground",
    "narratives",
    "bibliography",
    "statistics",
]

# Display order for the strip plot: anchors, then single-module, then minus-one.
# "" entries mark section breaks (visual gaps in the strip plot).
_VARIANT_ORDER = [
    # Anchors
    "p2_census",
    "p2_base",
    "p2_composite",
    "p2_frontier",
    "",  # ── section break ──
    # Single-module (base + one module)
    "p2_persona",
    "p2_overview",
    "p2_citation_columns",
    "p2_sourcing_ground",
    "p2_narratives",
    "p2_bibliography",
    "p2_statistics",
    "",  # ── section break ──
    # Minus-one (composite - one module)
    "p2_no_persona",
    "p2_no_overview",
    "p2_no_citation_columns",
    "p2_no_sourcing_ground",
    "p2_no_narratives",
    "p2_no_bibliography",
    "p2_no_statistics",
]

_MODEL_SHORT_NAMES = {
    "deepseek-v3.2": "DS V3.2",
    "kimi-k2-thinking": "Kimi K2",
}

_VARIANT_LABELS = {
    "p2_census": "Census (anchor)",
    "p2_base": "Base (no modules)",
    "p2_composite": "Composite (all 7)",
    "p2_frontier": "Frontier (anchor)",
    "p2_persona": "+ Persona",
    "p2_overview": "+ Overview",
    "p2_citation_columns": "+ Citation columns",
    "p2_sourcing_ground": "+ Sourcing ground",
    "p2_narratives": "+ Narratives",
    "p2_bibliography": "+ Bibliography",
    "p2_statistics": "+ Statistics",
    "p2_no_persona": "All − Persona",
    "p2_no_overview": "All − Overview",
    "p2_no_citation_columns": "All − Citation columns",
    "p2_no_sourcing_ground": "All − Sourcing ground",
    "p2_no_narratives": "All − Narratives",
    "p2_no_bibliography": "All − Bibliography",
    "p2_no_statistics": "All − Statistics",
}


def load_ablation_data() -> list[dict]:
    """Load Phase 2 RAG ablation data from measurements.

    Returns list of dicts: {variant, model, tp, fp, fn, f1, is_refusal}.
    """
    rows = []
    for record in load():
        rf = record.result_file or ""
        if "ablation/rag/p2_" not in rf:
            continue
        pv = record.method_params.prompt_version
        if not pv or not pv.startswith("p2_"):
            continue
        model = normalize_model(record.method_params.model)
        s = record.result_summary
        is_refusal = s.status != "ok"
        rows.append(
            {
                "variant": pv,
                "model": model,
                "tp": s.tp or 0,
                "fp": s.fp or 0,
                "fn": s.fn or 0,
                "f1": s.f1 or 0.0,
                "is_refusal": is_refusal,
            }
        )
    return rows


def _write_placeholder_pdf(output: Path, message: str) -> None:
    """Write a one-page placeholder PDF so downstream Make/LaTeX targets resolve."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 2))
    ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=11, color="gray")
    ax.set_axis_off()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", dpi=150)
    plt.close(fig)


def write_strip_pdf(rows: list[dict], output: Path, max_fp: int = 160) -> None:
    """Generate ablation strip plot as PDF.

    Y-axis: prompt variants grouped by section.
    X-axis: plant count. Blue = TP, orange = FP, gray X = refusal.
    """
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.lines import Line2D

    if not rows:
        log.warning("No ablation data; writing placeholder strip plot")
        _write_placeholder_pdf(output, "Ablation data not yet collected")
        return

    fig, ax = plt.subplots(figsize=(10, 7.5))

    y_offset = 0.0
    variant_ticks = []
    run_spacing = 0.35
    model_gap = 0.1
    section_gap = 1.2
    variant_gap = 0.8

    for variant in _VARIANT_ORDER:
        if variant == "":
            y_offset += section_gap
            continue

        variant_rows = [r for r in rows if r["variant"] == variant]
        if not variant_rows:
            continue

        # Sort by model, then TP descending
        variant_rows.sort(key=lambda r: (r["model"], -r["tp"]))

        band_start = y_offset
        prev_model = None
        n_plotted = 0
        for run in variant_rows:
            if prev_model is not None and run["model"] != prev_model:
                y_offset += model_gap
            y = y_offset + n_plotted * run_spacing
            prev_model = run["model"]
            n_plotted += 1

            if run["is_refusal"]:
                # Mark refusal with gray X at x=0
                ax.scatter(
                    [0],
                    [y],
                    s=40,
                    c=COLOR_REFUSAL,
                    marker="x",
                    linewidths=1.5,
                    zorder=3,
                )
                ax.text(
                    3,
                    y,
                    "refusal",
                    fontsize=5,
                    color=COLOR_REFUSAL,
                    va="center",
                    ha="left",
                    style="italic",
                )
                continue

            tp = run["tp"]
            fp_raw = run["fp"]
            fp = min(fp_raw, max_fp)

            # TP dots (blue, right of 0)
            if tp > 0:
                xs = np.arange(1, tp + 1)
                ys = np.full_like(xs, y, dtype=float)
                ax.scatter(
                    xs,
                    ys,
                    s=4,
                    c=COLOR_MATCHED,
                    marker="|",
                    linewidths=0.5,
                    zorder=3,
                )

            # FP dots (orange, left of 0)
            if fp > 0:
                xs = -np.arange(1, fp + 1)
                ys = np.full_like(xs, y, dtype=float)
                ax.scatter(
                    xs,
                    ys,
                    s=4,
                    c=COLOR_HALLUC,
                    marker="|",
                    linewidths=0.5,
                    zorder=3,
                )
                if fp_raw > max_fp:
                    ax.text(
                        -fp - 1,
                        y,
                        f"({fp_raw})",
                        fontsize=5,
                        color=COLOR_HALLUC,
                        va="center",
                        ha="right",
                    )

        band_center = band_start + (n_plotted - 1) * run_spacing / 2
        label = _VARIANT_LABELS.get(variant, variant)
        variant_ticks.append((band_center, label))
        y_offset += n_plotted * run_spacing + variant_gap

    # Reference line at 163
    ax.axvline(x=163, color=COLOR_REFERENCE, linewidth=1, linestyle="--", alpha=0.7, zorder=2)
    ax.text(165, -0.5, "163\nplants", color=COLOR_REFERENCE, fontsize=8, va="top", ha="left")

    # Zero line
    ax.axvline(x=0, color="black", linewidth=0.5, alpha=0.4, zorder=1)

    # Y axis
    ax.set_yticks([t[0] for t in variant_ticks])
    ax.set_yticklabels([t[1] for t in variant_ticks], fontsize=11)
    ax.set_xlabel("Number of power plants", fontsize=11)
    ax.set_xlim(-max_fp - 15, 185)
    ax.invert_yaxis()
    ax.grid(axis="x", linewidth=0.2, alpha=0.3)
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", labelsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Legend
    legend_handles = [
        Line2D([0], [0], color=COLOR_MATCHED, linewidth=3, label="Correctly identified"),
        Line2D([0], [0], color=COLOR_HALLUC, linewidth=3, label="Hallucinated"),
        Line2D(
            [0],
            [0],
            color=COLOR_REFUSAL,
            linewidth=0,
            marker="x",
            markersize=6,
            label="Refusal (tool_calls)",
        ),
    ]
    ax.legend(handles=legend_handles, loc="lower right", fontsize=8, framealpha=0.9)

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", dpi=300)
    plt.close(fig)
    log.info("Wrote strip plot: %s", output)


def write_heatmap_pdf(rows: list[dict], output: Path) -> None:
    """Generate module effect heatmap as PDF.

    Rows: 6 modules. Columns: composition ΔF1, ablation ΔF1, per model.
    """
    import matplotlib.pyplot as plt
    import numpy as np

    # Guard: empty data produces no figure
    non_refusal = [r for r in rows if not r["is_refusal"]]
    if not non_refusal:
        log.warning("No non-refusal ablation data; writing placeholder heatmap")
        _write_placeholder_pdf(output, "Ablation data not yet collected")
        return

    # Compute mean F1 per (variant, model) excluding refusals
    mean_f1: dict[tuple[str, str], float] = {}
    groups: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in non_refusal:
        groups[(r["variant"], r["model"])].append(r["f1"])
    for key, values in groups.items():
        mean_f1[key] = sum(values) / len(values)

    models = sorted({r["model"] for r in rows})

    # Build delta matrix: rows=modules, cols=models×2 (composition, ablation)
    n_modules = len(_MODULES)
    n_cols = len(models) * 2
    matrix = np.full((n_modules, n_cols), np.nan)
    col_labels = []
    for mi, model in enumerate(models):
        short = _MODEL_SHORT_NAMES.get(model, model.split("-", 1)[-1][:10])
        col_labels.extend([f"{short}\n+module", f"{short}\n−module"])
        base_f1 = mean_f1.get(("p2_base", model))
        comp_f1 = mean_f1.get(("p2_composite", model))
        for ri, mod in enumerate(_MODULES):
            # Composition delta: base+module vs base
            plus_f1 = mean_f1.get((f"p2_{mod}", model))
            if plus_f1 is not None and base_f1 is not None:
                matrix[ri, mi * 2] = (plus_f1 - base_f1) * 100

            # Ablation delta: composite-module vs composite
            minus_f1 = mean_f1.get((f"p2_no_{mod}", model))
            if minus_f1 is not None and comp_f1 is not None:
                matrix[ri, mi * 2 + 1] = (minus_f1 - comp_f1) * 100

    fig, ax = plt.subplots(figsize=(7, 4))

    # Use diverging colormap, centered at 0
    vmax = max(30, np.nanmax(np.abs(matrix)))
    im = ax.imshow(
        matrix,
        cmap="RdBu",
        vmin=-vmax,
        vmax=vmax,
        aspect="auto",
        interpolation="nearest",
    )

    # Annotate cells
    for i in range(n_modules):
        for j in range(n_cols):
            val = matrix[i, j]
            if np.isnan(val):
                ax.text(j, i, "—", ha="center", va="center", fontsize=8, color="gray")
            else:
                color = "white" if abs(val) > vmax * 0.6 else "black"
                ax.text(
                    j,
                    i,
                    f"{val:+.1f}",
                    ha="center",
                    va="center",
                    fontsize=8,
                    fontweight="bold",
                    color=color,
                )

    # Axes
    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(col_labels, fontsize=8)
    ax.set_yticks(range(n_modules))
    ax.set_yticklabels([m.capitalize() for m in _MODULES], fontsize=9)

    # Vertical separator between models
    for mi in range(1, len(models)):
        ax.axvline(x=mi * 2 - 0.5, color="white", linewidth=2)

    cbar = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
    cbar.set_label("ΔF1 (percentage points)", fontsize=9)

    ax.set_title("Prompt module effects on F1 — RAG regime", fontsize=11, pad=10)

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", dpi=300)
    plt.close(fig)
    log.info("Wrote heatmap: %s", output)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Generate ablation figures")
    parser.add_argument("--strip", default=None, help="Path to write strip plot PDF")
    parser.add_argument("--heatmap", default=None, help="Path to write heatmap PDF")
    args = parser.parse_args()

    if not args.strip and not args.heatmap:
        parser.error("At least one of --strip or --heatmap is required")

    rows = load_ablation_data()
    log.info("Loaded %d ablation records", len(rows))

    if args.strip:
        write_strip_pdf(rows, Path(args.strip))
    if args.heatmap:
        write_heatmap_pdf(rows, Path(args.heatmap))


if __name__ == "__main__":
    main()
