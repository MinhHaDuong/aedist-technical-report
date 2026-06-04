"""Coverage and Cost single-panel figures for Exp2, with Exp1 baseline bar.

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.

Each model group shows 5 bars:
  E1  = Experiment 1 parametric baseline (from cost_quality.csv)
  1N  = arm1: single-shot, no docs
  5N  = arm2: multi-turn, no docs
  1D  = arm3: single-shot, with docs
  5D  = arm4: multi-turn, with docs

Writes two separate PDF files:
  --coverage-output  diverging bar: matched assets above 0, hallucinations below 0
  --cost-output      positive bar: mean API cost per run (USD)

E1 bars use the same family colour as the model with diagonal hatching
to visually signal that they come from a different experiment.

Usage:
    python -m aedist.plot_exp2_arms_split \
        --input report/inputs/generated/tab_exp2_arms_runs_view.csv \
        --exp1-input report/inputs/generated/cost_quality.csv \
        --coverage-output report/inputs/generated/fig_exp2_coverage.pdf \
        --cost-output report/inputs/generated/fig_exp2_cost.pdf
"""

import argparse
import csv
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from matplotlib.figure import Figure

from .util import (
    COLOR_ALERT,
    COLOR_REFERENCE,
    SLIDE_FIGSIZE_FULL,
    model_family_color,
)

log = logging.getLogger(__name__)

N_REFERENCE_PLANTS = 163

_AGENT_LABELS = {
    "anthropic": "Anthropic\nOpus 4.6",
    "mistral": "Mistral\nLarge 2512",
    "openai": "OpenAI\nGPT-5.5",
    "qwen": "Qwen3\nMax",
}
_AGENT_ORDER = ["anthropic", "mistral", "openai", "qwen"]

_AGENT_MODEL = {
    "anthropic": "claude-opus-4-6",
    "mistral": "mistral-large-2512",
    "openai": "gpt-5.5",
    "qwen": "qwen3.7-max",
}

# Exp1 slugs in cost_quality.csv for each agent.
_AGENT_EXP1_SLUG = {
    "anthropic": "claude-opus-4.6",
    "mistral": "mistral-large-2512",
    "openai": "gpt-5.5",
    "qwen": "qwen3.7-max",
}

# Display order: E1 first, then the four Exp2 arms.
_CONDITIONS = ["arm1", "arm2", "arm3", "arm4"]
_CONDITION_LABEL = {"arm1": "1N", "arm2": "5N", "arm3": "1D", "arm4": "5D"}

# 5-bar layout: E1 + arm1..arm4, symmetric around the model centre.
_BAR_WIDTH = 0.14
_ALL_KEYS = ["e1", "arm1", "arm2", "arm3", "arm4"]
_CONDITION_OFFSET = {"e1": -0.36, "arm1": -0.18, "arm2": 0.00, "arm3": +0.18, "arm4": +0.36}


def _canonical_arm(raw: str) -> str:
    if raw == "naive":
        return "arm1"
    if raw == "optimised":
        return "arm2"
    return raw


# ---- data loading ------------------------------------------------------------


def load_exp2_rows(path: Path) -> list[dict]:
    """Load from tab_exp2_arms_runs_view.csv, which carries n_matched for all 4 arms."""
    rows = []
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            row["run"] = int(row["run"])
            raw_rows = row["inventory_rows"]
            row["inventory_rows"] = int(raw_rows) if raw_rows not in ("", "None") else 0
            raw_matched = row.get("n_matched", "")
            row["n_matched"] = int(raw_matched) if raw_matched not in ("", "None") else None
            row["cost_usd"] = float(row.get("cost_usd") or 0.0)
            row["arm"] = _canonical_arm(row["arm"])
            row["is_report"] = row["classification"] == "report"
            rows.append(row)
    return rows


def load_exp1_summary(path: Path) -> dict[str, dict]:
    """Return {exp1_slug: {median_tp, …, median_fp, …, min_cost, max_cost}} from cost_quality.csv."""
    summary: dict[str, dict] = {}
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            summary[row["model"]] = {
                "median_tp": int(row["median_tp"]),
                "min_tp": int(row["min_tp"]),
                "max_tp": int(row["max_tp"]),
                "median_fp": int(row.get("median_fp") or 0),
                "min_fp": int(row.get("min_fp") or 0),
                "max_fp": int(row.get("max_fp") or 0),
                "mean_cost": float(row["mean_cost"]),
                "min_cost": float(row.get("min_cost") or row["mean_cost"]),
                "max_cost": float(row.get("max_cost") or row["mean_cost"]),
            }
    return summary


# ---- drawing helpers ---------------------------------------------------------


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _draw_whiskers(ax, x_center: float, values: list[float]) -> None:
    if not values:
        return
    seg = _BAR_WIDTH * 0.6
    ax.vlines(x_center, min(values), max(values), color="black", linewidth=0.7, zorder=5)
    ax.hlines(
        values,
        x_center - seg / 2,
        x_center + seg / 2,
        color="black",
        linewidth=0.8,
        zorder=5,
    )


def _annotate_bar_labels(ax, include_e1: bool = True) -> None:
    """Small condition labels (E1/1N/5N/1D/5D) just inside the baseline."""
    y0 = ax.get_ylim()[0]
    span = ax.get_ylim()[1] - y0
    keys = (["e1"] if include_e1 else []) + _CONDITIONS
    for agent_idx in range(len(_AGENT_ORDER)):
        for key in keys:
            label = "E1" if key == "e1" else _CONDITION_LABEL[key]
            ax.text(
                agent_idx + _CONDITION_OFFSET[key],
                y0 + span * 0.015,
                label,
                ha="center",
                va="bottom",
                fontsize=11,
                color="0.30",
                zorder=6,
            )


def _style_axis(ax) -> None:
    ax.set_xticks(range(len(_AGENT_ORDER)))
    ax.set_xticklabels([_AGENT_LABELS[a] for a in _AGENT_ORDER], fontsize=8)
    ax.set_xlim(-0.65, len(_AGENT_ORDER) - 0.35)
    ax.tick_params(axis="y", labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


# ---- figure builders ---------------------------------------------------------


def make_coverage_figure(
    exp2_rows: list[dict],
    exp1_summary: dict[str, dict],
    output: Path,
) -> "Figure":
    import matplotlib.pyplot as plt

    exp2_rows = [r for r in exp2_rows if r["is_report"]]

    fig, ax = plt.subplots(figsize=SLIDE_FIGSIZE_FULL)

    for agent_idx, agent in enumerate(_AGENT_ORDER):
        color = model_family_color(_AGENT_MODEL[agent])

        # E1 bar
        exp1_slug = _AGENT_EXP1_SLUG[agent]
        if exp1_slug in exp1_summary:
            e1 = exp1_summary[exp1_slug]
            x = agent_idx + _CONDITION_OFFSET["e1"]
            ax.bar(x, e1["median_tp"], _BAR_WIDTH, color=color, alpha=0.55, hatch="//", zorder=3)
            if e1["median_fp"] > 0:
                ax.bar(
                    x,
                    -e1["median_fp"],
                    _BAR_WIDTH,
                    color=COLOR_ALERT,
                    alpha=0.7,
                    hatch="//",
                    zorder=3,
                )
            _draw_whiskers(ax, x, [e1["min_tp"], e1["max_tp"]])

        # Exp2 arms
        for cond in _CONDITIONS:
            subset = [r for r in exp2_rows if r["agent"] == agent and r["arm"] == cond]
            if not subset:
                continue
            x = agent_idx + _CONDITION_OFFSET[cond]
            scored = [r for r in subset if r["n_matched"] is not None]
            if scored:
                matched_vals = [r["n_matched"] for r in scored]
                halluc_vals = [max(0, r["inventory_rows"] - r["n_matched"]) for r in scored]
                mean_matched = _mean(matched_vals)
                mean_halluc = _mean(halluc_vals)
                ax.bar(x, mean_matched, _BAR_WIDTH, color=color, alpha=0.85, zorder=3)
                if mean_halluc > 0:
                    # Same red as the E1 FP bar — the title promises "red = false positives"
                    ax.bar(x, -mean_halluc, _BAR_WIDTH, color=COLOR_ALERT, alpha=0.9, zorder=3)
                _draw_whiskers(ax, x, matched_vals)
            else:
                inv_vals = [r["inventory_rows"] for r in subset if r["inventory_rows"] > 0]
                ax.bar(x, _mean(inv_vals), _BAR_WIDTH, color="0.70", alpha=0.85, zorder=3)
                _draw_whiskers(ax, x, inv_vals)

    ax.axhline(0, color=COLOR_REFERENCE, linewidth=1.4, zorder=2)
    ax.axhline(N_REFERENCE_PLANTS, color=COLOR_REFERENCE, linestyle="--", linewidth=1.0, zorder=1)
    ax.yaxis.set_major_formatter(lambda val, pos: str(abs(int(val))))
    ax.set_ylim(-50, 150)
    ax.set_yticks([-50, 0, 50, 100, 150])
    ax.text(-0.55, 150, "163 plants", ha="left", va="bottom", fontsize=8, fontweight="bold")
    _style_axis(ax)
    _annotate_bar_labels(ax, include_e1=True)
    ax.set_title(
        "Number of assets identified  (hatched = Exp 1 memory-only baseline; red = false positives)",
        fontsize=10,
        fontweight="bold",
        pad=10,
    )
    fig.suptitle(
        "Coverage  ·  E1 = memory only  ·  1N = 1-shot no doc  ·  5N = 5-turn no doc  ·  "
        "1D = 1-shot + doc  ·  5D = 5-turn + doc",
        fontsize=8,
        y=0.02,
    )
    fig.tight_layout(rect=(0.0, 0.06, 1.0, 1.0))
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", dpi=150)
    plt.close(fig)
    log.info("Wrote %s", output)
    return fig


def make_cost_figure(
    exp2_rows: list[dict],
    exp1_summary: dict[str, dict],
    output: Path,
) -> "Figure":
    import matplotlib.pyplot as plt

    exp2_rows = [r for r in exp2_rows if r["is_report"]]

    fig, ax = plt.subplots(figsize=SLIDE_FIGSIZE_FULL)

    for agent_idx, agent in enumerate(_AGENT_ORDER):
        color = model_family_color(_AGENT_MODEL[agent])

        # E1 bar
        exp1_slug = _AGENT_EXP1_SLUG[agent]
        if exp1_slug in exp1_summary:
            x = agent_idx + _CONDITION_OFFSET["e1"]
            e1 = exp1_summary[exp1_slug]
            mean_cost = e1["mean_cost"]
            ax.bar(x, mean_cost, _BAR_WIDTH, color=color, alpha=0.55, hatch="//", zorder=3)
            _draw_whiskers(ax, x, [e1["min_cost"], e1["max_cost"]])

        # Exp2 arms
        for cond in _CONDITIONS:
            subset = [r for r in exp2_rows if r["agent"] == agent and r["arm"] == cond]
            if not subset:
                continue
            x = agent_idx + _CONDITION_OFFSET[cond]
            cost_vals = [r["cost_usd"] for r in subset]
            ax.bar(x, _mean(cost_vals), _BAR_WIDTH, color=color, alpha=0.85, zorder=3)
            _draw_whiskers(ax, x, cost_vals)

    ax.set_ylim(bottom=0)
    _style_axis(ax)
    _annotate_bar_labels(ax, include_e1=True)
    ax.set_title(
        "API cost per run, USD  (hatched = Exp 1 memory-only baseline)",
        fontsize=10,
        fontweight="bold",
        pad=10,
    )
    fig.suptitle(
        "Cost  ·  E1 = memory only  ·  1N = 1-shot no doc  ·  5N = 5-turn no doc  ·  "
        "1D = 1-shot + doc  ·  5D = 5-turn + doc",
        fontsize=8,
        y=0.02,
    )
    fig.tight_layout(rect=(0.0, 0.06, 1.0, 1.0))
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", dpi=150)
    plt.close(fig)
    log.info("Wrote %s", output)
    return fig


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Split Exp2 arms figure into separate coverage and cost panels with Exp1 baseline"
    )
    parser.add_argument("--input", required=True, help="Path to tab_exp2_arms_runs_view.csv")
    parser.add_argument(
        "--exp1-input", required=True, help="Path to cost_quality.csv (Exp1 summary)"
    )
    parser.add_argument("--coverage-output", required=True, help="Path to write coverage PDF")
    parser.add_argument("--cost-output", required=True, help="Path to write cost PDF")
    args = parser.parse_args(argv)

    exp2_rows = load_exp2_rows(Path(args.input))
    exp1_summary = load_exp1_summary(Path(args.exp1_input))

    make_coverage_figure(exp2_rows, exp1_summary, Path(args.coverage_output))
    make_cost_figure(exp2_rows, exp1_summary, Path(args.cost_output))


if __name__ == "__main__":
    main()
