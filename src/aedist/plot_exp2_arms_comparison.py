"""Two-panel comparison figure for Exp2 4-arm design.

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
import random
from pathlib import Path

from .extract import count_best_table_rows
from .util import COLOR_REFERENCE, model_family_color

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

_ARM_STYLE = {
    "arm1": {"marker": "o", "filled": False, "offset": -0.27, "label": "Single query"},
    "arm2": {"marker": "D", "filled": False, "offset": -0.09, "label": "Multi-turn"},
    "arm3": {
        "marker": "o",
        "filled": True,
        "offset": +0.09,
        "label": "Single query with docs",
    },
    "arm4": {
        "marker": "D",
        "filled": True,
        "offset": +0.27,
        "label": "Multi-turn with docs",
    },
}

_ARM_ORDER = ["arm1", "arm2", "arm3", "arm4"]

_PANELS = [
    ("inventory_rows", "(a) Coverage", "Assets correctly identified"),
    ("cost_usd", "(b) Cost", "API cost per run (USD)"),
]


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
                "cost_usd": float(payload.get("cost_usd") or 0.0),
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


def _draw_panel(ax, rows: list[dict], metric: str, title: str, ylabel: str) -> None:
    rng = random.Random(42)

    for agent_idx, agent in enumerate(_AGENT_ORDER):
        for arm in _ARM_ORDER:
            style = _ARM_STYLE[arm]
            subset = [r for r in rows if r["agent"] == agent and r["arm"] == arm]
            if not subset:
                continue

            color = model_family_color(subset[0].get("model", _AGENT_MODEL[agent]))
            x_center = agent_idx + style["offset"]
            xs = [x_center + rng.uniform(-0.04, 0.04) for _ in subset]

            report_xs = [x for x, r in zip(xs, subset, strict=True) if r["is_report"]]
            report_ys = [r[metric] for r in subset if r["is_report"]]

            if report_xs:
                face = color if style["filled"] else "none"
                ax.scatter(
                    report_xs,
                    report_ys,
                    marker=style["marker"],
                    s=24,
                    facecolors=face,
                    edgecolors=color,
                    linewidths=1.0,
                    zorder=3,
                )

    ax.set_xticks(range(len(_AGENT_ORDER)))
    ax.set_xticklabels([_AGENT_LABELS[a] for a in _AGENT_ORDER], fontsize=7.5)
    ax.set_xlim(-0.5, len(_AGENT_ORDER) - 0.5)
    ax.set_ylabel(ylabel, fontsize=8)
    ax.tick_params(axis="y", labelsize=7.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if metric == "inventory_rows":
        ax.axhline(N_REFERENCE_PLANTS, color=COLOR_REFERENCE, linestyle="--", linewidth=1.0, zorder=1)
        ax.set_ylim(0, 180)
    else:
        ax.set_ylim(bottom=0)

    # Center panel captions below each subplot.
    ax.text(
        0.5,
        -0.23,
        title,
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=10,
        fontweight="bold",
    )


def make_figure(rows: list[dict], output: Path) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    fig, axes = plt.subplots(1, 2, figsize=(10.0, 5.1))
    no_report_rows = [r for r in rows if not r["is_report"]]
    if no_report_rows:
        sample = ", ".join(
            f"{r['arm']}/{r['agent']}/run{r['run']}" for r in no_report_rows[:6]
        )
        log.warning(
            "plot_exp2_arms_comparison: excluding %d no_report rows (pipeline bugs): %s",
            len(no_report_rows),
            sample,
        )
    rows = [r for r in rows if r["is_report"]]

    for ax, (metric, title, ylabel) in zip(axes, _PANELS, strict=True):
        _draw_panel(ax, rows, metric, title, ylabel)

    legend_handles = []
    legend_order = ["arm1", "arm3", "arm2", "arm4"]
    for arm in legend_order:
        style = _ARM_STYLE[arm]
        face = COLOR_REFERENCE if style["filled"] else "none"
        legend_handles.append(
            Line2D(
                [0],
                [0],
                marker=style["marker"],
                linestyle="",
                markerfacecolor=face,
                markeredgecolor=COLOR_REFERENCE,
                markersize=6,
                label=style["label"],
            )
        )
    fig.legend(
        handles=legend_handles,
        loc="upper center",
        ncol=4,
        fontsize=7.5,
        frameon=True,
        bbox_to_anchor=(0.5, 0.945),
        borderpad=0.6,
        labelspacing=0.6,
        columnspacing=1.2,
    )

    fig.suptitle(
        "One query, providing documents works better than a conversation with web search",
        fontsize=12,
        fontweight="bold",
        y=1.01,
    )
    fig.tight_layout(rect=(0.0, 0.08, 1.0, 0.92))
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
