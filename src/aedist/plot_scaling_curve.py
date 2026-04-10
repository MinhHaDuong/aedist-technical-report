"""Generate Qwen 3.5 scaling curve: F1 vs model size under RAG wholesale.

Compares single-shot (parametric knowledge only) vs RAG wholesale
for the Qwen 3.5 family at 2B, 4B, 9B, 35B parameter counts.
Horizontal reference lines show best cloud API results.

Usage:
    uv run python -m aedist.plot_scaling_curve \
        --output slides/inputs/generated/fig_scaling_curve.pdf
"""

import argparse
import logging
import re
from collections import defaultdict
from pathlib import Path

from .measurements import SYNTHETIC_SUFFIXES, load

log = logging.getLogger(__name__)

# Qwen 3.5 local model sizes (parameter count in billions)
_MODEL_SIZES: dict[str, float] = {
    "qwen3.5:2b": 2,
    "qwen3.5:4b": 4,
    "qwen3.5:9b": 9,
    "qwen3.5:35b": 35,
}

# Fallback cloud reference F1 values (used only when no data is available).
# Source: measurements.jsonl best individual RAG runs as of 2026-04-01.
_CLOUD_REFS_FALLBACK: dict[str, float] = {
    "DeepSeek V3.2 (best run)": 0.6855,
    "GPT-5.4 (best run)": 0.9381,
}

# Pattern to strip '-runN' suffix from model slug for display grouping
_RUN_SUFFIX_RE = re.compile(r"-run\d+$")


def _compute_cloud_refs() -> dict[str, float]:
    """Compute cloud reference F1 from measurements at runtime.

    Filters for method=rag, non-local (non-Qwen-local) models, and takes
    the max F1 per model slug.  Falls back to ``_CLOUD_REFS_FALLBACK`` if
    no cloud RAG data is found.
    """
    cloud_best: dict[str, float] = {}
    for record in load():
        if record.method.value != "rag":
            continue
        pv = getattr(record.method_params, "prompt_version", None)
        if pv == "_extracted":
            continue
        model = record.method_params.model.split("/")[-1]
        if any(model.endswith(s) for s in SYNTHETIC_SUFFIXES):
            continue
        # Skip local models (those in _MODEL_SIZES are the Qwen local variants)
        if model in _MODEL_SIZES:
            continue
        f1 = record.result_summary.f1
        if f1 is None:
            continue
        # Normalize slug: strip -runN suffix
        slug = _RUN_SUFFIX_RE.sub("", model)
        if slug not in cloud_best or f1 > cloud_best[slug]:
            cloud_best[slug] = f1

    if not cloud_best:
        log.warning("No cloud RAG data found; using fallback cloud references")
        return dict(_CLOUD_REFS_FALLBACK)

    # Format display names: "Model (best run)"
    return {f"{slug} (best run)": f1 for slug, f1 in sorted(cloud_best.items())}


def _normalize_model(raw: str) -> str:
    """Normalize model name: strip provider prefix."""
    return raw.split("/")[-1]


def collect_data() -> dict[str, dict[float, list[float]]]:
    """Collect F1 scores grouped by method and model size.

    Returns: {"single": {2: [f1, ...], 4: [...], ...}, "rag": {...}}
    """
    data: dict[str, dict[float, list[float]]] = {
        "single": defaultdict(list),
        "rag": defaultdict(list),
    }

    for record in load():
        method = record.method.value
        if method not in ("single", "rag"):
            continue
        pv = getattr(record.method_params, "prompt_version", None)
        if pv == "_extracted":
            continue
        model = _normalize_model(record.method_params.model)
        if any(model.endswith(s) for s in SYNTHETIC_SUFFIXES):
            continue
        if model not in _MODEL_SIZES:
            continue
        f1 = record.result_summary.f1
        if f1 is None:
            continue
        size = _MODEL_SIZES[model]
        data[method][size].append(f1)

    return data


def write_pdf(data: dict[str, dict[float, list[float]]], output: Path) -> None:
    """Generate the scaling curve as PDF."""
    import matplotlib.pyplot as plt
    import numpy as np

    fig, ax = plt.subplots(figsize=(7, 4.5))

    sizes_all = sorted(set().union(*[d.keys() for d in data.values()]))

    if not sizes_all:
        log.warning("No data points to plot; skipping PDF generation")
        plt.close(fig)
        return

    # Color scheme
    colors = {"single": "#888888", "rag": "#2E86AB"}
    labels = {"single": "Single-shot (no docs)", "rag": "RAG wholesale (18 docs)"}
    markers = {"single": "s", "rag": "o"}

    for method in ("single", "rag"):
        method_data = data[method]
        if not method_data:
            continue

        sizes = sorted(method_data.keys())
        means = [np.mean(method_data[s]) for s in sizes]
        stds = [np.std(method_data[s]) for s in sizes]

        # Plot individual runs as small dots
        for s in sizes:
            for f1 in method_data[s]:
                ax.scatter(
                    s, f1,
                    c=colors[method], alpha=0.3, s=25,
                    marker=markers[method], zorder=3,
                )

        # Plot mean +/- std as line with error bars
        ax.errorbar(
            sizes, means, yerr=stds,
            color=colors[method], linewidth=2, capsize=4, capthick=1.5,
            marker=markers[method], markersize=7,
            label=labels[method], zorder=4,
        )

    # Cloud reference lines (computed from measurements at runtime)
    cloud_refs = _compute_cloud_refs()
    ref_colors = ["#E74C3C", "#F5A623"]
    ref_styles = ["--", "-."]
    for i, (name, f1) in enumerate(cloud_refs.items()):
        ax.axhline(
            y=f1, color=ref_colors[i % len(ref_colors)],
            linewidth=1.2, linestyle=ref_styles[i % len(ref_styles)],
            alpha=0.7, zorder=2,
        )
        ax.text(
            max(sizes_all) * 1.05, f1, name,
            fontsize=7, color=ref_colors[i % len(ref_colors)],
            va="center", ha="left",
        )

    ax.set_xscale("log", base=2)
    ax.set_xticks(sizes_all)
    ax.set_xticklabels([f"{int(s)}B" for s in sizes_all])
    ax.set_xlabel("Model size (parameters)", fontsize=11)
    ax.set_ylabel("F1 score", fontsize=11)
    ax.set_ylim(-0.02, 1.05)
    ax.set_xlim(1.5, 60)

    ax.legend(loc="upper left", fontsize=9, framealpha=0.9)
    ax.grid(axis="y", linewidth=0.3, alpha=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Annotate missing sizes if needed
    rag_sizes = set(data["rag"].keys())
    missing = set(_MODEL_SIZES.values()) - rag_sizes
    if missing:
        missing_str = ", ".join(f"{int(s)}B" for s in sorted(missing))
        ax.text(
            0.5, 0.02, f"RAG data for {missing_str} forthcoming",
            transform=ax.transAxes, fontsize=8, ha="center",
            style="italic", color="#666666",
        )

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", dpi=300)
    plt.close(fig)
    log.info("Wrote %s", output)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Generate Qwen 3.5 scaling curve (F1 vs model size)",
    )
    parser.add_argument("--output", required=True, help="Path to write PDF")
    args = parser.parse_args()

    data = collect_data()

    total_points = sum(len(fs) for d in data.values() for fs in d.values())
    log.info("Collected %d data points across %d methods", total_points, len(data))

    if total_points == 0:
        log.warning("No data points found; nothing to plot")
        return

    output = Path(args.output)
    write_pdf(data, output)


if __name__ == "__main__":
    main()
