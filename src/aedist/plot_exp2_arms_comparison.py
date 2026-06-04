"""Two-panel comparison figure for Exp2 4-arm design.

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.

Usage:
    python -m aedist.plot_exp2_arms_comparison \
        --input report/inputs/generated/tab_exp2_arms_runs.csv \
        --output report/inputs/generated/fig_exp2_arms_comparison.pdf

Panels (left to right):
    (a) coverage (plants enumerated)
    (b) cost (USD per run)

Each panel groups by agent on the x-axis. Within each group, all four arms are
shown with project glyphs and per-model colours. Runs classified no_report are
rendered as x markers at y=0.
"""

import argparse
import csv
import json
import logging
from pathlib import Path

from .extract import count_best_table_rows
from .util import (
    COLOR_HALLUC,
    COLOR_REFERENCE,
    SLIDE_FIGSIZE_WIDE,
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
    "qwen": "qwen3.7-max-2026-05-20",
}

# Four experimental conditions, in display order within each model group.
#   1N = single-shot, no docs  (arm1 / naive)
#   5N = multi-turn,  no docs   (arm2 / optimised)
#   1D = single-shot, docs      (arm3)
#   5D = multi-turn,  docs      (arm4)
_CONDITIONS = ["arm1", "arm2", "arm3", "arm4"]
_CONDITION_LABEL = {"arm1": "1N", "arm2": "5N", "arm3": "1D", "arm4": "5D"}
# Within-group bar centers; integer gap between models, small gap within a model.
_CONDITION_OFFSET = {"arm1": -0.30, "arm2": -0.10, "arm3": +0.10, "arm4": +0.30}
_BAR_WIDTH = 0.17


def _canonical_arm(raw: str) -> str:
    if raw == "naive":
        return "arm1"
    if raw == "optimised":
        return "arm2"
    return raw


def _inventory_rows_from_flat(json_path: Path) -> int:
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    for key in ("inventory_rows", "n_rows"):
        val = payload.get(key)
        if isinstance(val, int):
            return val
    md_path = json_path.with_suffix(".md")
    if md_path.exists():
        return count_best_table_rows(md_path.read_text(encoding="utf-8"))
    return 0


def _load_pack_arm_rows(base_dir: Path, arm: str) -> list[dict]:
    if not base_dir.exists():
        return []
    rows: list[dict] = []
    for json_path in sorted(base_dir.glob("*.json")):
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        agent = str(payload.get("agent") or "").strip()
        if agent not in _AGENT_ORDER:
            continue
        model = str(payload.get("model") or _AGENT_MODEL[agent])
        run = int(payload.get("run") or 0)
        classification = str(payload.get("classification") or "report")
        rows.append(
            {
                "arm": arm,
                "agent": agent,
                "model": model,
                "run": run,
                "classification": classification,
                "inventory_rows": _inventory_rows_from_flat(json_path),
                # arm3/arm4 are unscored (no cross-eval coverage) -> no matched count.
                "n_matched": None,
                "cost_usd": float(payload.get("total_cost_usd", payload.get("cost_usd")) or 0.0),
                "is_report": classification == "report",
            }
        )
    return rows


def _load_csv(path: Path) -> list[dict]:
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

    present_arms = {r["arm"] for r in rows}
    root = path.parents[3]
    if "arm3" not in present_arms:
        rows.extend(_load_pack_arm_rows(root / "experiments/derived/arm3_flat", "arm3"))
    if "arm4" not in present_arms:
        rows.extend(_load_pack_arm_rows(root / "experiments/derived/arm4_flat", "arm4"))
    return rows


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _draw_whiskers(ax, x_center: float, values: list[float]) -> None:
    """Thin black vertical line spanning the run range + one short horizontal
    segment per run, to show inter-run dispersion (ticket 0332)."""
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


def _draw_coverage_panel(ax, rows: list[dict]) -> None:
    """Diverging bars: matched assets (model colour, above 0), hallucinations /
    false positives (red, below 0). 1D/5D (no scoring) render as gray bars."""
    for agent_idx, agent in enumerate(_AGENT_ORDER):
        for cond in _CONDITIONS:
            subset = [
                r for r in rows if r["agent"] == agent and r["arm"] == cond and r["is_report"]
            ]
            if not subset:
                continue
            x = agent_idx + _CONDITION_OFFSET[cond]
            color = model_family_color(subset[0].get("model", _AGENT_MODEL[agent]))

            scored = [r for r in subset if r["n_matched"] is not None]
            if scored:
                matched_vals = [r["n_matched"] for r in scored]
                halluc_vals = [max(0, r["inventory_rows"] - r["n_matched"]) for r in scored]
                mean_matched = _mean(matched_vals)
                mean_halluc = _mean(halluc_vals)
                ax.bar(x, mean_matched, _BAR_WIDTH, color=color, alpha=0.85, zorder=3)
                if mean_halluc > 0:
                    ax.bar(x, -mean_halluc, _BAR_WIDTH, color=COLOR_HALLUC, alpha=0.9, zorder=3)
                _draw_whiskers(ax, x, matched_vals)
            else:
                # 1D/5D or all-None scored runs: show inventory size, unscored gray.
                inv_vals = [r["inventory_rows"] for r in subset if r["inventory_rows"] > 0]
                ax.bar(x, _mean(inv_vals), _BAR_WIDTH, color="0.70", alpha=0.85, zorder=3)
                _draw_whiskers(ax, x, inv_vals)

    ax.axhline(0, color=COLOR_REFERENCE, linewidth=1.4, zorder=2)
    ax.axhline(N_REFERENCE_PLANTS, color=COLOR_REFERENCE, linestyle="--", linewidth=1.0, zorder=1)
    ax.yaxis.set_major_formatter(lambda val, pos: str(abs(int(val))))
    ax.set_ylim(-50, 150)
    ax.set_yticks([-50, 0, 50, 100, 150])
    # Y-axis label, horizontal, at the top of the axis.
    ax.text(
        -0.5,
        150,
        "163 plants",
        ha="left",
        va="bottom",
        fontsize=8,
        fontweight="bold",
    )
    _style_panel(ax, "Number of assets identified (red are False Positives)")


def _draw_cost_panel(ax, rows: list[dict]) -> None:
    """Mean API cost per run, 4 bars per model with inter-run whiskers."""
    for agent_idx, agent in enumerate(_AGENT_ORDER):
        for cond in _CONDITIONS:
            subset = [
                r for r in rows if r["agent"] == agent and r["arm"] == cond and r["is_report"]
            ]
            if not subset:
                continue
            x = agent_idx + _CONDITION_OFFSET[cond]
            color = model_family_color(subset[0].get("model", _AGENT_MODEL[agent]))
            cost_vals = [r["cost_usd"] for r in subset]
            ax.bar(x, _mean(cost_vals), _BAR_WIDTH, color=color, alpha=0.85, zorder=3)
            _draw_whiskers(ax, x, cost_vals)

    ax.set_ylim(bottom=0)
    ax.set_title("API Cost per run, USD", fontsize=9, fontweight="bold", pad=6)
    _style_panel(ax, None)


def _annotate_conditions(ax) -> None:
    """Small 1N/5N/1D/5D labels just below each bar, inside the axes."""
    y0 = ax.get_ylim()[0]
    span = ax.get_ylim()[1] - y0
    for agent_idx in range(len(_AGENT_ORDER)):
        for cond in _CONDITIONS:
            ax.text(
                agent_idx + _CONDITION_OFFSET[cond],
                y0 + span * 0.015,
                _CONDITION_LABEL[cond],
                ha="center",
                va="bottom",
                fontsize=6.0,
                color="0.30",
                zorder=6,
            )


def _style_panel(ax, ylabel: str | None) -> None:
    ax.set_xticks(range(len(_AGENT_ORDER)))
    ax.set_xticklabels([_AGENT_LABELS[a] for a in _AGENT_ORDER], fontsize=7.5)
    ax.set_xlim(-0.6, len(_AGENT_ORDER) - 0.4)
    if ylabel:
        ax.set_title(ylabel, fontsize=9, fontweight="bold", pad=6)
    ax.tick_params(axis="y", labelsize=7.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    _annotate_conditions(ax)


def make_figure(rows: list[dict], output: Path) -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=SLIDE_FIGSIZE_WIDE)
    no_report_rows = [r for r in rows if not r["is_report"]]
    if no_report_rows:
        sample = ", ".join(f"{r['arm']}/{r['agent']}/run{r['run']}" for r in no_report_rows[:6])
        log.warning(
            "plot_exp2_arms_comparison: excluding %d no_report rows (pipeline bugs): %s",
            len(no_report_rows),
            sample,
        )
    rows = [r for r in rows if r["is_report"]]

    _draw_coverage_panel(axes[0], rows)
    _draw_cost_panel(axes[1], rows)

    fig.suptitle("Coverage and costs, experiment 2", fontsize=13, fontweight="bold", y=0.99)
    fig.text(
        0.5,
        0.925,
        "1N = Singleshot, no doc  ·  5N = Multiturn, no doc  ·  "
        "1D = Singleshot, docs  ·  5D = Multiturn, docs",
        ha="center",
        va="top",
        fontsize=8.5,
    )
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.90))
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", dpi=150)
    plt.close(fig)
    log.info("Wrote %s", output)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="2-panel Exp2 4-arm comparison figure")
    parser.add_argument("--input", required=True, help="Path to tab_exp2_arms_runs.csv")
    parser.add_argument("--output", required=True, help="Path to write PDF figure")
    args = parser.parse_args(argv)
    make_figure(_load_csv(Path(args.input)), Path(args.output))


if __name__ == "__main__":
    main()
