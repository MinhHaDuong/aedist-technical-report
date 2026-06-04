"""Generate regimes scatter plot: 5 models × 3 methods, one dot per TP plant.

Shows how RAG lifts the identification floor across all models.
Median TP across runs per model-method combo.

Usage:
    uv run python -m aedist.plot_regimes_scatter \
        --output report/inputs/generated/fig_regimes_scatter.pdf
"""

import argparse
import logging
from collections import defaultdict
from pathlib import Path
from statistics import median

from .figures_config import load_modelset
from .measurements import SYNTHETIC_SUFFIXES, load
from .util import COLOR_REFERENCE, normalize_model

log = logging.getLogger(__name__)


def _get_models() -> list[tuple[str, str]]:
    """Load (slug, display_name) pairs from figures.toml regimes_scatter modelset."""
    models = load_modelset("regimes_scatter")
    return [(normalize_model(m["name"]), m["display_name"]) for m in models]


_METHODS = [
    ("direct", "Direct"),
    ("direct+multiturn", "Multi-tours"),
    ("rag", "RAG"),
]


def load_regimes_data(
    models: list[tuple[str, str]],
) -> dict[tuple[str, str], list[int]]:
    """Return {(model_slug, method): [tp, tp, ...]} for the target models."""
    model_slugs = {slug for slug, _ in models}
    method_values = {m for m, _ in _METHODS}

    tp_by_combo: dict[tuple[str, str], list[int]] = defaultdict(list)
    for record in load():
        model = normalize_model(record.method_params.model)
        method = record.method.value
        if model not in model_slugs or method not in method_values:
            continue
        if any(model.endswith(s) for s in SYNTHETIC_SUFFIXES):
            continue
        tp = record.result_summary.tp
        if tp is not None:
            tp_by_combo[(model, method)].append(tp)
    return dict(tp_by_combo)


def write_pdf(
    tp_by_combo: dict[tuple[str, str], list[int]],
    models: list[tuple[str, str]],
    output: Path,
) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    fig, ax = plt.subplots(figsize=(7, 5))
    fig.subplots_adjust(left=0.22)

    yticks = []
    ytick_labels = []
    model_label_ys = []

    for model_idx, (model_slug, model_name) in enumerate(models):
        base_y = model_idx * 4
        model_label_ys.append((base_y + 1, model_name))
        for method_idx, (method_value, method_label) in enumerate(_METHODS):
            y = base_y + method_idx
            yticks.append(y)
            ytick_labels.append(method_label)

            tp_values = tp_by_combo.get((model_slug, method_value), [])
            if tp_values:
                median_tp = int(median(tp_values))
                if median_tp > 0:
                    xs = np.arange(1, median_tp + 1)
                    ys = np.full_like(xs, y, dtype=float)
                    ax.scatter(
                        xs,
                        ys,
                        s=6,
                        c="black",
                        alpha=0.6,
                        marker=".",
                        linewidths=0,
                    )

    ax.axvline(x=163, color=COLOR_REFERENCE, linewidth=1, linestyle="--", alpha=0.7)

    ax.set_yticks(yticks)
    ax.set_yticklabels(ytick_labels, fontsize=7)
    ax.set_xlabel("Centrales identifiées (un point = une centrale)", fontsize=9)
    ax.set_xlim(0, 175)
    ymax = (len(models) - 1) * 4 + 2
    ax.set_ylim(-0.5, ymax + 0.5)
    ax.invert_yaxis()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for y_pos, name in model_label_ys:
        ax.annotate(
            name,
            xy=(0, y_pos),
            xycoords=("axes fraction", "data"),
            xytext=(-70, 0),
            textcoords="offset points",
            fontsize=8,
            fontweight="bold",
            ha="right",
            va="center",
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", dpi=300)
    plt.close(fig)
    log.info("Wrote %s", output)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Generate regimes scatter plot")
    parser.add_argument("--output", required=True, help="Path to write PDF")
    args = parser.parse_args()

    models = _get_models()
    data = load_regimes_data(models)
    write_pdf(data, models, Path(args.output))


if __name__ == "__main__":
    main()
