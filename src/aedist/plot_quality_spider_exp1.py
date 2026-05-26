"""Radar/spider figure for Exp1 quality profiles by model family.

Usage:
    python -m aedist.plot_quality_spider_exp1 \
        --input experiments/derived/exp1_cross_eval.csv \
        --output report/inputs/generated/fig_spider_exp1_families.pdf
"""

import argparse
import csv
import logging
from collections import defaultdict
from pathlib import Path

from .util import COLOR_NEUTRAL, SLIDE_FIGSIZE_POLAR_2x2, model_family, model_family_color

log = logging.getLogger(__name__)

_AXES = [
    "accuracy_coverage",
    "accuracy_precision",
    "accuracy_fuel",
    "accuracy_status",
    "accuracy_province",
    "provenance_source_presence",
    "temporality_asof_presence",
    "field_completeness_core",
]

_AXIS_LABELS = {
    "accuracy_coverage": "Coverage",
    "accuracy_precision": "Precision",
    "accuracy_fuel": "Fuel",
    "accuracy_status": "Status",
    "accuracy_province": "Province",
    "provenance_source_presence": "Source",
    "temporality_asof_presence": "As-of",
    "field_completeness_core": "Core fields",
}

_PANELS = [
    ("claude", "(a) Claude", {"claude"}),
    ("gpt", "(b) GPT", {"gpt"}),
    ("mistral", "(c) Mistral", {"mistral"}),
    ("qwen_deepseek", "(d) Qwen / DeepSeek", {"qwen", "deepseek"}),
]


def _parse_optional_float(raw: str | None) -> float | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as fh:
        return [r for r in csv.DictReader(fh) if str(r.get("arm", "")).strip() == "parametric"]


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def _lighten(hex_color: str, amount: float) -> tuple[float, float, float]:
    # amount=0.0 keeps original color, amount=1.0 becomes white.
    import matplotlib.colors as mcolors

    r, g, b = mcolors.to_rgb(hex_color)
    return (
        r + (1.0 - r) * amount,
        g + (1.0 - g) * amount,
        b + (1.0 - b) * amount,
    )


def _model_size_rank(model: str) -> int:
    slug = model.lower()
    if any(t in slug for t in ("haiku", "small", "20b", "flash")):
        return 1
    if any(t in slug for t in ("sonnet", "medium", "35b", "120b", "plus")):
        return 2
    if any(t in slug for t in ("opus", "large", "max", "pro", "5.5")):
        return 3
    return 2


def _aggregate(rows: list[dict[str, str]]) -> dict[str, dict[str, dict[str, float]]]:
    by_model: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        model = str(row.get("model", "")).strip()
        if not model:
            continue
        for axis in _AXES:
            value = _parse_optional_float(row.get(axis))
            if value is not None:
                by_model[model][axis].append(value)

    stats: dict[str, dict[str, dict[str, float]]] = {}
    for model, axis_values in by_model.items():
        if not axis_values:
            continue
        model_stats: dict[str, dict[str, float]] = {}
        for axis in _AXES:
            values = axis_values.get(axis, [])
            if not values:
                continue
            model_stats[axis] = {
                "median": _median(values),
                "min": min(values),
                "max": max(values),
            }
        if len(model_stats) == len(_AXES):
            stats[model] = model_stats
    return stats


def _panel_models(stats: dict[str, dict[str, dict[str, float]]], families: set[str]) -> list[str]:
    models = [m for m in stats if model_family(m) in families]
    models.sort(key=lambda m: (_model_size_rank(m), m))
    return models


def make_figure(rows: list[dict[str, str]], output: Path) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    stats = _aggregate(rows)
    if not stats:
        msg = "exp1 spider: no profiles available from input"
        raise ValueError(msg)

    fig, axes = plt.subplots(
        2, 2, figsize=SLIDE_FIGSIZE_POLAR_2x2, subplot_kw={"projection": "polar"}
    )
    angles = np.linspace(0, 2 * np.pi, len(_AXES), endpoint=False)
    closed_angles = np.concatenate((angles, [angles[0]]))

    med_prov = []
    med_temp = []

    for ax, (_panel_key, panel_title, families) in zip(axes.flatten(), _PANELS, strict=True):
        panel_models = _panel_models(stats, families)
        for theta, axis in zip(angles, _AXES, strict=True):
            ax.text(theta, 1.12, _AXIS_LABELS[axis], ha="center", va="center", fontsize=8)

        if panel_models:
            family_buckets: dict[str, list[str]] = defaultdict(list)
            for model in panel_models:
                family_buckets[model_family(model)].append(model)

            for fam_models in family_buckets.values():
                base_color = model_family_color(fam_models[0])
                n = len(fam_models)
                for i, model in enumerate(fam_models):
                    lighten = 0.55 - (0.50 * (i / max(1, n - 1)))
                    color = _lighten(base_color, max(0.0, lighten))
                    med = [stats[model][a]["median"] for a in _AXES]
                    low = [stats[model][a]["min"] for a in _AXES]
                    high = [stats[model][a]["max"] for a in _AXES]
                    med_closed = med + [med[0]]
                    low_closed = low + [low[0]]
                    high_closed = high + [high[0]]
                    ring_angles = list(closed_angles) + list(closed_angles[::-1])
                    ring_vals = high_closed + low_closed[::-1]

                    ax.fill(ring_angles, ring_vals, color=color, alpha=0.06, linewidth=0)
                    ax.plot(closed_angles, med_closed, color=color, linewidth=1.8, label=model)

                    med_prov.append(stats[model]["provenance_source_presence"]["median"])
                    med_temp.append(stats[model]["temporality_asof_presence"]["median"])
        else:
            ax.text(0.5, 0.5, "No models", transform=ax.transAxes, ha="center", va="center")

        ax.set_title(panel_title, loc="left", fontsize=10)
        ax.set_xticks(angles)
        ax.set_xticklabels([])
        ax.set_yticks([0.25, 0.5, 0.75, 1.0])
        ax.set_yticklabels([])
        ax.set_ylim(0, 1.0)
        ax.grid(color=COLOR_NEUTRAL, alpha=0.30, linewidth=0.8)
        ax.spines["polar"].set_color(COLOR_NEUTRAL)
        if panel_models:
            ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), fontsize=6.7, ncol=2)

    if med_prov and med_temp:
        prov_med = _median(med_prov)
        temp_med = _median(med_temp)
        if prov_med < 0.05 or temp_med < 0.05:
            fig.text(
                0.5,
                0.01,
                "Provenance and temporality remain near-zero across Exp1 models.",
                ha="center",
                va="bottom",
                fontsize=9,
                color=COLOR_NEUTRAL,
            )

    fig.suptitle("Experiment 1 quality profiles by model family", fontsize=13, y=0.995)
    fig.tight_layout(rect=(0, 0.03, 1, 0.97))
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", dpi=150)
    plt.close(fig)
    log.info("Wrote %s", output)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Render Exp1 family spider chart")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("experiments/derived/exp1_cross_eval.csv"),
        help="Path to exp1_cross_eval.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("report/inputs/generated/fig_spider_exp1_families.pdf"),
        help="Path to write PDF figure",
    )
    args = parser.parse_args(argv)
    make_figure(_load_rows(args.input), args.output)


if __name__ == "__main__":
    main()
