"""Radar/spider figures for Exp1 quality profiles.

Two modes:
  - Family 2×2 panels (default): one subplot per model family.
  - Single model (--model): one large spider for a single model,
    with 5 quality dimensions and 2 French-labelled indicators each.

Usage:
    python -m aedist.plot_quality_spider_exp1 \
        --input experiments/derived/exp1_cross_eval.csv \
        --output report/inputs/generated/fig_spider_exp1_families.pdf

    python -m aedist.plot_quality_spider_exp1 \
        --input experiments/derived/exp1_cross_eval.csv \
        --model claude-opus-4.6 \
        --output report/inputs/generated/fig_spider_exp1_claude.pdf
"""

import argparse
import csv
import logging
import math
from collections import defaultdict
from pathlib import Path

from .util import (
    COLOR_NEUTRAL,
    SLIDE_FIGSIZE_POLAR_SINGLE,
    SLIDE_FIGSIZE_POLAR_2x2,
    model_family,
    model_family_color,
)

log = logging.getLogger(__name__)

# ── Unified 5×2 axes: 5 quality dimensions, 2 indicators each ──────────────
#
# Ordered so adjacent pairs share a dimension and cardinal directions
# on the spider correspond to dimension centres.

SPIDER_AXES = [
    "accuracy_coverage",
    "accuracy_precision",
    "accuracy_fuel",
    "accuracy_status",
    "accuracy_province",
    "coherence_vocab_adherence",
    "provenance_source_diversity",
    "provenance_source_spread",
    "temporality_plausible_range",
    "temporality_cod_plausible",
]

SPIDER_DIMENSION = {
    "accuracy_coverage": "Exactitude",
    "accuracy_precision": "Exactitude",
    "accuracy_fuel": "Contenu",
    "accuracy_status": "Contenu",
    "accuracy_province": "Cohérence",
    "coherence_vocab_adherence": "Cohérence",
    "provenance_source_diversity": "Provenance",
    "provenance_source_spread": "Provenance",
    "temporality_plausible_range": "Temporalité",
    "temporality_cod_plausible": "Temporalité",
}

SPIDER_LABEL = {
    "accuracy_coverage": "Actifs\ntrouvés",
    "accuracy_precision": "Actifs\ncorrects",
    "accuracy_fuel": "Combustible\ncorrect",
    "accuracy_status": "Statut\ncorrect",
    "accuracy_province": "Province\ncorrecte",
    "coherence_vocab_adherence": "Vocabulaire\nrespecté",
    "provenance_source_diversity": "Diversité\ndes sources",
    "provenance_source_spread": "Répartition\ndes sources",
    "temporality_plausible_range": "Date\nplausible",
    "temporality_cod_plausible": "Date COD\nplausible",
}

_PANELS = [
    ("claude", "(a) Claude", {"claude"}),
    ("gpt", "(b) GPT", {"gpt"}),
    ("mistral", "(c) Mistral", {"mistral"}),
    ("qwen", "(d) Qwen", {"qwen"}),
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
    import matplotlib.colors as mcolors

    r, g, b = mcolors.to_rgb(hex_color)
    return (
        r + (1.0 - r) * amount,
        g + (1.0 - g) * amount,
        b + (1.0 - b) * amount,
    )


def _model_label(model: str) -> str:
    slug = model.lower()
    for tier in ("haiku", "sonnet", "opus", "small", "medium", "large"):
        if tier in slug:
            version = model.split("-")[-1]
            return f"{tier.capitalize()} {version}"
    fam = model_family(model)
    label = model
    if label.lower().startswith(fam):
        label = label[len(fam) :].lstrip("-_ ")
    return label or model


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
        for axis in SPIDER_AXES:
            value = _parse_optional_float(row.get(axis))
            if value is not None:
                by_model[model][axis].append(value)

    stats: dict[str, dict[str, dict[str, float]]] = {}
    for model, axis_values in by_model.items():
        if not axis_values:
            continue
        model_stats: dict[str, dict[str, float]] = {}
        for axis in SPIDER_AXES:
            values = axis_values.get(axis, [])
            if not values:
                continue
            model_stats[axis] = {
                "median": _median(values),
                "min": min(values),
                "max": max(values),
            }
        if model_stats:
            stats[model] = model_stats
    return stats


def _panel_models(stats: dict[str, dict[str, dict[str, float]]], families: set[str]) -> list[str]:
    models = [m for m in stats if model_family(m) in families]
    models.sort(key=lambda m: (_model_size_rank(m), m))
    return models


def _draw_axis_labels(
    ax, angles, axes_order, *, label_fontsize: float = 10, dim_fontsize: float = 12.5
):
    dimension_angles: dict[str, list[float]] = defaultdict(list)
    for theta, axis in zip(angles, axes_order, strict=True):
        dimension = SPIDER_DIMENSION[axis]
        ax.text(theta, 1.28, SPIDER_LABEL[axis], ha="center", va="center", fontsize=label_fontsize)
        dimension_angles[dimension].append(theta)

    for dimension, group in dimension_angles.items():
        center = math.atan2(sum(math.sin(a) for a in group), sum(math.cos(a) for a in group))
        radius = 1.46
        ax.text(
            center,
            radius,
            dimension,
            ha="center",
            va="center",
            fontsize=dim_fontsize,
            fontweight="bold",
            color=COLOR_NEUTRAL,
        )


def _style_polar_ax(ax, angles):
    ax.set_xticks(angles)
    ax.set_xticklabels([])
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels([])
    ax.set_ylim(0, 1.0)
    ax.grid(color=COLOR_NEUTRAL, alpha=0.30, linewidth=0.8)
    ax.spines["polar"].set_color(COLOR_NEUTRAL)


def make_figure(rows: list[dict[str, str]], output: Path) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    stats = _aggregate(rows)
    if not stats:
        msg = "exp1 spider: no profiles available from input"
        raise ValueError(msg)

    n_axes = len(SPIDER_AXES)
    fig, axes = plt.subplots(
        2, 2, figsize=SLIDE_FIGSIZE_POLAR_2x2, subplot_kw={"projection": "polar"}
    )
    angles = np.linspace(0, 2 * np.pi, n_axes, endpoint=False) + (np.pi / n_axes)
    closed_angles = np.concatenate((angles, [angles[0]]))

    for ax, (_panel_key, panel_title, families) in zip(axes.flatten(), _PANELS, strict=True):
        _draw_axis_labels(ax, angles, SPIDER_AXES, label_fontsize=7, dim_fontsize=8.5)
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)

        panel_models = _panel_models(stats, families)
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
                    med = [stats[model].get(a, {}).get("median", 0.0) for a in SPIDER_AXES]
                    low = [stats[model].get(a, {}).get("min", 0.0) for a in SPIDER_AXES]
                    high = [stats[model].get(a, {}).get("max", 0.0) for a in SPIDER_AXES]
                    med_closed = med + [med[0]]
                    low_closed = low + [low[0]]
                    high_closed = high + [high[0]]
                    ring_angles = list(closed_angles) + list(closed_angles[::-1])
                    ring_vals = high_closed + low_closed[::-1]

                    ax.fill(ring_angles, ring_vals, color=color, alpha=0.06, linewidth=0)
                    ax.plot(
                        closed_angles,
                        med_closed,
                        color=color,
                        linewidth=1.8,
                        label=_model_label(model),
                    )
        else:
            ax.text(0.5, 0.5, "No models", transform=ax.transAxes, ha="center", va="center")

        _style_polar_ax(ax, angles)
        if panel_models:
            ax.legend(
                loc="center left",
                bbox_to_anchor=(1.18, 0.5),
                title=panel_title,
                fontsize=7.5,
                title_fontsize=9,
                alignment="left",
                handlelength=1.4,
                borderaxespad=0.0,
                frameon=False,
            )

    fig.suptitle(
        "Source is the universal failure mode",
        fontsize=12,
        y=0.995,
    )
    fig.tight_layout(rect=(0, 0.03, 0.92, 0.95))
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", dpi=150)
    plt.close(fig)
    log.info("Wrote %s", output)


def make_single_model_figure(rows: list[dict[str, str]], model_slug: str, output: Path) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    stats = _aggregate(rows)
    if model_slug not in stats:
        msg = f"single-model spider: no profile for {model_slug!r}"
        raise ValueError(msg)

    n_axes = len(SPIDER_AXES)
    fig, ax = plt.subplots(figsize=SLIDE_FIGSIZE_POLAR_SINGLE, subplot_kw={"projection": "polar"})
    angles = np.linspace(0, 2 * np.pi, n_axes, endpoint=False) + (np.pi / n_axes)
    closed_angles = np.concatenate((angles, [angles[0]]))

    _draw_axis_labels(ax, angles, SPIDER_AXES)
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    _style_polar_ax(ax, angles)

    color = model_family_color(model_slug)
    profile = stats[model_slug]
    values = [profile.get(axis, {}).get("median", 0.0) for axis in SPIDER_AXES]
    closed_values = values + [values[0]]
    ax.plot(closed_angles, closed_values, color=color, linewidth=2.2)
    ax.fill(closed_angles, closed_values, color=color, alpha=0.12)

    ax.set_title(
        f"Profil de qualité — {_model_label(model_slug)} (Expérience 1)",
        fontsize=14,
        y=1.18,
        pad=6,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", dpi=150)
    plt.close(fig)
    log.info("Wrote %s (model: %s)", output, model_slug)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Render Exp1 quality spider chart")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("experiments/derived/exp1_cross_eval.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("report/inputs/generated/fig_spider_exp1_families.pdf"),
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="If set, render a single large spider for this model slug (e.g. 'claude-opus-4.6').",
    )
    # Kept for Makefile back-compat; --model takes priority.
    parser.add_argument("--family", type=str, default=None, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    rows = _load_rows(args.input)
    if args.model:
        make_single_model_figure(rows, args.model, args.output)
    elif args.family:
        stats = _aggregate(rows)
        match = next((m for m in stats if model_family(m) == args.family), None)
        if match is None:
            raise ValueError(f"--family {args.family!r}: no model found in data")
        make_single_model_figure(rows, match, args.output)
    else:
        make_figure(rows, args.output)


if __name__ == "__main__":
    main()
