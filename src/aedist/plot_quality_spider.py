"""Radar/spider figure for Exp2 quality profiles.

Usage:
    python -m aedist.plot_quality_spider \
        --input experiments/derived/sota_cross_eval.csv \
        --config experiments/quality_spider_config.yaml \
        --output report/inputs/generated/fig_quality_spider.pdf
"""

import argparse
import csv
import logging
import math
from collections import defaultdict
from pathlib import Path

import yaml

from .util import COLOR_NEUTRAL, glyph_for_method, model_family_color

log = logging.getLogger(__name__)

# Indicator columns are defined by score_mechanical _CSV_COLUMNS and row writer.
_INDICATOR_TO_QUALITY_AXIS = {
    "accuracy_coverage": "Accuracy",
    "accuracy_precision": "Accuracy",
    "provenance_source_presence": "Provenance",
    "provenance_high_conf_dual_source": "Provenance",
    "temporality_asof_presence": "Temporality",
    "temporality_plausible_range": "Temporality",
    "field_completeness_core": "Completeness",
    "field_completeness_capacity": "Completeness",
}

_INDICATOR_LABEL = {
    "accuracy_coverage": "Find All\nAssets",
    "accuracy_precision": "Only Correct\nAssets",
    "provenance_source_presence": "One\nSource",
    "provenance_high_conf_dual_source": "Two\nSources",
    "temporality_asof_presence": "Mention\nstatus date",
    "temporality_plausible_range": "Date Looks\nReasonable",
    "field_completeness_core": "Key Fields\nAre Filled",
    "field_completeness_capacity": "Capacity Field\nIs Filled",
}

# Order is arranged so, after a 1/16-turn spin, each cardinal point represents
# a quality axis with its two indicators straddling that cardinal direction.
_DEFAULT_AXES = [
    "accuracy_precision",
    "provenance_source_presence",
    "provenance_high_conf_dual_source",
    "temporality_asof_presence",
    "temporality_plausible_range",
    "field_completeness_core",
    "field_completeness_capacity",
    "accuracy_coverage",
]

_ARM_STYLES = {
    "naive": {"linestyle": "--", "method": "arm1", "label": "naive", "alpha": 0.16},
    "optimised": {"linestyle": "-", "method": "arm2", "label": "optimised", "alpha": 0.10},
}

_CLOSE_TO_PLOT = {"Accuracy", "Temporality"}


def _parse_optional_float(raw: str | None) -> float | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _row_axis_score(row: dict[str, str], axis: str) -> float | None:
    return _parse_optional_float(row.get(axis))


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def _load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def _load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    models = data.get("modelset")
    if not isinstance(models, list) or not models:
        msg = "quality spider config requires non-empty 'modelset'"
        raise ValueError(msg)

    if len(models) > 4:
        msg = "quality spider supports at most 4 models in 'modelset'"
        raise ValueError(msg)

    axes = data.get("axes", list(_DEFAULT_AXES))
    if not isinstance(axes, list) or not axes:
        msg = "quality spider config requires non-empty 'axes'"
        raise ValueError(msg)
    invalid_axes = [axis for axis in axes if axis not in _INDICATOR_LABEL]
    if invalid_axes:
        msg = f"unknown axes in config: {', '.join(invalid_axes)}"
        raise ValueError(msg)
    if len(axes) != 8 or set(axes) != set(_INDICATOR_LABEL):
        msg = "quality spider requires exactly the 8 indicator axes (2 per quality axis)"
        raise ValueError(msg)

    arms = data.get("arms", ["naive", "optimised"])
    if not isinstance(arms, list) or not arms:
        msg = "quality spider config requires non-empty 'arms'"
        raise ValueError(msg)
    invalid_arms = [arm for arm in arms if arm not in _ARM_STYLES]
    if invalid_arms:
        msg = f"unknown arms in config: {', '.join(invalid_arms)}"
        raise ValueError(msg)

    aggregate = data.get("aggregate", "median")
    if aggregate != "median":
        msg = "quality spider currently supports only aggregate: median"
        raise ValueError(msg)

    return {
        "modelset": [str(model) for model in models],
        "axes": [str(axis) for axis in axes],
        "arms": [str(arm) for arm in arms],
        "aggregate": aggregate,
    }


def _aggregate_profiles(rows: list[dict[str, str]], config: dict) -> dict[tuple[str, str], dict[str, float]]:
    seen_models = {str(row.get("model", "")) for row in rows}
    selected_models = []
    for model in config["modelset"]:
        if model in seen_models:
            selected_models.append(model)
        else:
            log.warning("quality spider: unknown model in config, skipping: %s", model)

    grouped_values: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        model = str(row.get("model", ""))
        arm = str(row.get("arm", ""))
        if model not in selected_models or arm not in config["arms"]:
            continue
        for axis in config["axes"]:
            score = _row_axis_score(row, axis)
            if score is not None:
                grouped_values[(model, arm)][axis].append(score)

    profiles: dict[tuple[str, str], dict[str, float]] = {}
    for key, axis_values in grouped_values.items():
        axis_profile: dict[str, float] = {}
        for axis in config["axes"]:
            value = _median(axis_values.get(axis, []))
            if value is not None:
                axis_profile[axis] = value
        if axis_profile:
            profiles[key] = axis_profile
    return profiles


def make_figure(rows: list[dict[str, str]], config: dict, output: Path) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    axes = config["axes"]
    profiles = _aggregate_profiles(rows, config)

    fig, ax = plt.subplots(figsize=(7.4, 5.6), subplot_kw={"projection": "polar"})
    # Spin by 1/16 turn so cardinal points correspond to quality-axis centers.
    angles = np.linspace(0, 2 * np.pi, len(axes), endpoint=False) + (np.pi / 8)
    closed_angles = np.concatenate((angles, [angles[0]]))

    for theta, axis in zip(angles, axes, strict=True):
        quality_axis = _INDICATOR_TO_QUALITY_AXIS[axis]
        indicator_radius = 1.17 if quality_axis in _CLOSE_TO_PLOT else 1.3
        ax.text(
            theta,
            indicator_radius,
            _INDICATOR_LABEL[axis],
            ha="center",
            va="center",
            fontsize=12.2,
        )

    quality_axis_angles: dict[str, list[float]] = defaultdict(list)
    for theta, axis in zip(angles, axes, strict=True):
        quality_axis_angles[_INDICATOR_TO_QUALITY_AXIS[axis]].append(theta)

    for quality_axis, axis_angles in quality_axis_angles.items():
        center = math.atan2(
            sum(math.sin(a) for a in axis_angles),
            sum(math.cos(a) for a in axis_angles),
        )
        axis_radius = 1.25 if quality_axis in _CLOSE_TO_PLOT else 1.4
        ax.text(
            center,
            axis_radius,
            quality_axis,
            ha="center",
            va="center",
            fontsize=13.4,
            fontweight="bold",
            color=COLOR_NEUTRAL,
        )

    # Rotate the web spokes with the same 1/16-turn shift as the data points.
    ax.set_xticks(angles)
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticklabels([])
    ax.set_rlabel_position(0)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels([])
    ax.set_ylim(0, 1)
    ax.grid(color=COLOR_NEUTRAL, alpha=0.35, linewidth=0.8)
    ax.spines["polar"].set_color(COLOR_NEUTRAL)

    plotted = 0
    for model in config["modelset"]:
        for arm in config["arms"]:
            key = (model, arm)
            profile = profiles.get(key)
            if not profile:
                continue
            values = [profile.get(axis, 0.0) for axis in axes]
            closed_values = values + [values[0]]
            family_color = model_family_color(model)
            style = _ARM_STYLES[arm]
            glyph = glyph_for_method(style["method"])
            ax.plot(
                closed_angles,
                closed_values,
                color=family_color,
                linestyle=style["linestyle"],
                marker=str(glyph["marker"]),
                markersize=max(4.0, float(glyph["s"]) ** 0.5),
                linewidth=1.9,
                label=f"{model} ({style['label']})",
            )
            # Fill lightly to keep profile shape legible without hiding overlaps.
            ax.fill(closed_angles, closed_values, color=family_color, alpha=style["alpha"])
            plotted += 1

    if plotted == 0:
        msg = "quality spider: no model/arm profile could be drawn from input and config"
        raise ValueError(msg)

    ax.set_title(
        "Quality of LLM-generated statistical table",
        fontsize=14,
        y=1.23,
        pad=6,
    )
    legend = ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2, fontsize=12)
    handles = getattr(legend, "legend_handles", getattr(legend, "legendHandles", []))
    for handle in handles:
        handle.set_linewidth(2.1)

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", dpi=150)
    plt.close(fig)
    log.info("Wrote %s", output)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Render Exp2 quality spider chart")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("experiments/derived/sota_cross_eval.csv"),
        help="Path to sota_cross_eval.csv",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("experiments/quality_spider_config.yaml"),
        help="YAML file with modelset, axes, arms, and aggregate",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("report/inputs/generated/fig_quality_spider.pdf"),
        help="Path to write PDF figure",
    )
    args = parser.parse_args(argv)
    make_figure(_load_rows(args.input), _load_config(args.config), args.output)


if __name__ == "__main__":
    main()
