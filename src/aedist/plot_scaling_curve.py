"""Scaling curve: F1 vs active parameters under RAG wholesale.

Compares single-shot (parametric knowledge only) vs RAG wholesale
for two model families (Qwen 3.5, Gemma 4) from edge to cloud.
X-axis: active parameters (log scale) — relevant for MoE models.
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
from .util import COLOR_ALERT, COLOR_HALLUC, FAMILY_COLORS, normalize_model

log = logging.getLogger(__name__)

# Model families: model_id -> active parameters in billions
_FAMILIES: dict[str, dict[str, float]] = {
    "Qwen 3.5": {
        "qwen3.5:2b": 2,
        "qwen3.5:4b": 4,
        "qwen3.5:9b": 9,
        "qwen3.5:35b": 35,
        "qwen3.5-122b-a10b": 10,  # MoE: 10B active
    },
    "Gemma 4": {
        "gemma4:e2b": 2,
        "gemma4:e4b": 4,
        "gemma4:31b": 31,
        "gemma-4-26b-a4b-it": 3.8,  # MoE: 3.8B active
        "gemma-4-31b-it": 31,  # same arch via cloud
    },
}

# Reverse lookup: normalized model -> (family, active_params)
_MODEL_LOOKUP: dict[str, tuple[str, float]] = {}
for _fam, _models in _FAMILIES.items():
    for _mid, _params in _models.items():
        _MODEL_LOOKUP[_mid] = (_fam, _params)

# All local model IDs (for filtering cloud references)
_LOCAL_MODELS = set(_MODEL_LOOKUP.keys())

# Fallback cloud reference F1 values (used only when no data is available).
_CLOUD_REFS_FALLBACK: dict[str, float] = {
    "DeepSeek V3.2 (best run)": 0.6855,
    "GPT-5.4 (best run)": 0.9381,
}

# Pattern to strip '-runN' suffix from model slug for display grouping
_RUN_SUFFIX_RE = re.compile(r"-run\d+$")


def _compute_cloud_refs() -> dict[str, float]:
    """Compute cloud reference F1 from measurements at runtime.

    Filters for method=rag, non-family models, and takes the max F1 per slug.
    Falls back to ``_CLOUD_REFS_FALLBACK`` if no cloud RAG data is found.
    """
    cloud_best: dict[str, float] = {}
    for record in load():
        if record.method.value != "rag":
            continue
        pv = getattr(record.method_params, "prompt_version", None)
        if pv == "_extracted":
            continue
        model = normalize_model(record.method_params.model)
        if any(model.endswith(s) for s in SYNTHETIC_SUFFIXES):
            continue
        if model in _LOCAL_MODELS:
            continue
        f1 = record.result_summary.f1
        if f1 is None:
            continue
        slug = _RUN_SUFFIX_RE.sub("", model)
        if slug not in cloud_best or f1 > cloud_best[slug]:
            cloud_best[slug] = f1

    if not cloud_best:
        log.warning("No cloud RAG data found; using fallback cloud references")
        return dict(_CLOUD_REFS_FALLBACK)

    return {f"{slug} (best run)": f1 for slug, f1 in sorted(cloud_best.items())}


# Per-family, per-method data: family -> method -> active_params -> [f1]
FamilyData = dict[str, dict[str, dict[float, list[float]]]]


def collect_data() -> FamilyData:
    """Collect F1 scores grouped by family, method, and active param count."""
    data: FamilyData = {
        fam: {"single": defaultdict(list), "rag": defaultdict(list)} for fam in _FAMILIES
    }

    for record in load():
        method = record.method.value
        if method not in ("single", "rag"):
            continue
        pv = getattr(record.method_params, "prompt_version", None)
        if pv == "_extracted":
            continue
        model = normalize_model(record.method_params.model)
        if any(model.endswith(s) for s in SYNTHETIC_SUFFIXES):
            continue
        if model not in _MODEL_LOOKUP:
            continue
        f1 = record.result_summary.f1
        if f1 is None:
            continue
        family, active_params = _MODEL_LOOKUP[model]
        data[family][method][active_params].append(f1)

    return data


def write_pdf(data: FamilyData, output: Path) -> None:
    """Generate the two-family scaling curve as PDF."""
    import matplotlib.pyplot as plt
    import numpy as np

    fig, ax = plt.subplots(figsize=(8, 5))

    fc = FAMILY_COLORS
    family_colors = {"Qwen 3.5": fc["qwen"], "Gemma 4": fc["gemma"]}
    markers = {"single": "s", "rag": "o"}
    all_sizes: set[float] = set()

    for family, fam_data in data.items():
        colors = family_colors.get(family, fc["fallback"])

        for method in ("single", "rag"):
            method_data = fam_data[method]
            if not method_data:
                continue

            sizes = sorted(method_data.keys())
            all_sizes.update(sizes)
            means = [np.mean(method_data[s]) for s in sizes]
            stds = [np.std(method_data[s]) for s in sizes]

            # Individual runs as small dots
            for s in sizes:
                for f1 in method_data[s]:
                    ax.scatter(
                        s,
                        f1,
                        c=colors[method],
                        alpha=0.3,
                        s=20,
                        marker=markers[method],
                        zorder=3,
                    )

            method_label = "single-shot" if method == "single" else "RAG wholesale"
            ax.errorbar(
                sizes,
                means,
                yerr=stds,
                color=colors[method],
                linewidth=2,
                capsize=4,
                capthick=1.5,
                marker=markers[method],
                markersize=7,
                label=f"{family} — {method_label}",
                zorder=4,
            )

    # Cloud reference lines
    cloud_refs = _compute_cloud_refs()
    ref_colors = [COLOR_ALERT, COLOR_HALLUC]
    ref_styles = ["--", "-."]
    max_size = max(all_sizes) if all_sizes else 35
    for i, (name, f1) in enumerate(cloud_refs.items()):
        ax.axhline(
            y=f1,
            color=ref_colors[i % len(ref_colors)],
            linewidth=1.2,
            linestyle=ref_styles[i % len(ref_styles)],
            alpha=0.7,
            zorder=2,
        )
        ax.text(
            max_size * 1.15,
            f1,
            name,
            fontsize=7,
            color=ref_colors[i % len(ref_colors)],
            va="center",
            ha="left",
        )

    ax.set_xscale("log", base=2)
    if all_sizes:
        ticks = sorted(all_sizes)
        ax.set_xticks(ticks)
        ax.set_xticklabels([f"{s:g}B" for s in ticks])
    ax.set_xlabel("Active parameters (billions, log scale)", fontsize=11)
    ax.set_ylabel("F1 score", fontsize=11)
    ax.set_ylim(-0.02, 1.05)
    if all_sizes:
        ax.set_xlim(min(all_sizes) * 0.7, max_size * 1.8)

    ax.legend(loc="upper left", fontsize=8, framealpha=0.9, ncol=2)
    ax.grid(axis="y", linewidth=0.3, alpha=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", dpi=300)
    plt.close(fig)
    log.info("Wrote %s", output)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Generate scaling curve: F1 vs active params, two model families",
    )
    parser.add_argument("--output", required=True, help="Path to write PDF")
    args = parser.parse_args()

    data = collect_data()

    total_points = sum(len(fs) for fam in data.values() for d in fam.values() for fs in d.values())
    log.info("Collected %d data points across %d families", total_points, len(data))

    if total_points == 0:
        log.warning("No data points found; nothing to plot")
        return

    output = Path(args.output)
    write_pdf(data, output)


if __name__ == "__main__":
    main()
