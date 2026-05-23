"""Three-panel comparison figure for Exp2 naive vs optimised arms.

Usage:
    python -m aedist.plot_exp2_arms_comparison \\
        --input report/inputs/generated/tab_exp2_arms_runs.csv \\
        --output report/inputs/generated/fig_exp2_arms_comparison.pdf

Panels (left to right):
    A  inventory_rows  — enumerated plants (proxy for coverage)
    B  narrative_chars — report length in thousands of characters
    C  cost_usd        — total cost per run in USD

Each panel: four agent groups on the x-axis.  Within each group, two
columns (naive | optimised).  Individual run dots are jittered; a thick
horizontal bar marks the median.  Runs classified no_report are shown as
x markers at y=0 (structural zeros, not low performers).
"""

import argparse
import csv
import logging
import random
from pathlib import Path

from .util import COLOR_ARM_NAIVE, COLOR_ARM_OPTIMISED

log = logging.getLogger(__name__)

_AGENT_LABELS = {
    "anthropic": "Anthropic\nOpus 4.6",
    "mistral": "Mistral\nLarge 2512",
    "openai": "OpenAI\nGPT-5.5",
    "qwen": "Qwen3\nMax",
}
_AGENT_ORDER = ["anthropic", "mistral", "openai", "qwen"]

_ARM_STYLE = {
    "naive": {"color": COLOR_ARM_NAIVE, "label": "Naive (single-shot)", "offset": -0.18},
    "optimised": {
        "color": COLOR_ARM_OPTIMISED,
        "label": "Optimised (multi-turn)",
        "offset": +0.18,
    },
}

_PANELS = [
    ("inventory_rows", "Inventory rows", "A — Coverage"),
    ("narrative_chars_k", "Report length (k chars)", "B — Output richness"),
    ("cost_usd", "Cost (USD)", "C — Cost"),
]


def _load_csv(path: Path) -> list[dict]:
    rows = []
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            row["run"] = int(row["run"])
            raw_rows = row["inventory_rows"]
            row["inventory_rows"] = int(raw_rows) if raw_rows not in ("", "None") else 0
            row["narrative_chars_k"] = int(row["narrative_chars"]) / 1000
            row["cost_usd"] = float(row["cost_usd"])
            row["is_report"] = row["classification"] == "report"
            rows.append(row)
    return rows


def _draw_panel(ax, rows: list[dict], metric: str, title: str) -> None:
    import numpy as np

    rng = random.Random(42)

    for agent_idx, agent in enumerate(_AGENT_ORDER):
        for arm, style in _ARM_STYLE.items():
            subset = [r for r in rows if r["agent"] == agent and r["arm"] == arm]
            if not subset:
                continue

            x_center = agent_idx + style["offset"]
            xs = [x_center + rng.uniform(-0.06, 0.06) for _ in subset]

            report_xs = [x for x, r in zip(xs, subset, strict=True) if r["is_report"]]
            report_ys = [r[metric] for r in subset if r["is_report"]]
            noreport_xs = [x for x, r in zip(xs, subset, strict=True) if not r["is_report"]]

            ax.scatter(report_xs, report_ys, color=style["color"], s=22, zorder=3, linewidths=0)
            if noreport_xs:
                ax.scatter(
                    noreport_xs,
                    [0] * len(noreport_xs),
                    color=style["color"],
                    s=22,
                    zorder=3,
                    marker="x",
                    linewidths=1.2,
                )

            if report_ys:
                med = float(np.median(report_ys))
                ax.hlines(
                    med,
                    x_center - 0.10,
                    x_center + 0.10,
                    colors=style["color"],
                    linewidths=2.0,
                    zorder=4,
                )

    ax.set_title(title, fontsize=8, loc="left")
    ax.set_xticks(range(len(_AGENT_ORDER)))
    ax.set_xticklabels([_AGENT_LABELS[a] for a in _AGENT_ORDER], fontsize=7.5)
    ax.set_xlim(-0.5, len(_AGENT_ORDER) - 0.5)
    ax.tick_params(axis="y", labelsize=7.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_ylim(bottom=0)


def make_figure(rows: list[dict], output: Path) -> None:
    import matplotlib.patches as mpatches
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(9, 3.2))

    for ax, (metric, ylabel, title) in zip(axes, _PANELS, strict=True):
        _draw_panel(ax, rows, metric, title)
        ax.set_ylabel(ylabel, fontsize=8)

    legend_handles = [
        mpatches.Patch(color=style["color"], label=style["label"]) for style in _ARM_STYLE.values()
    ]
    fig.legend(
        handles=legend_handles,
        loc="lower center",
        ncol=2,
        fontsize=8,
        frameon=False,
        bbox_to_anchor=(0.5, -0.06),
    )
    fig.suptitle("Experiment 2 — Naive vs optimised arm (N=5 per agent)", fontsize=9, y=1.01)
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", dpi=150)
    plt.close(fig)
    log.info("Wrote %s", output)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Three-panel Exp2 arm comparison figure")
    parser.add_argument("--input", required=True, help="Path to tab_exp2_arms_runs.csv")
    parser.add_argument("--output", required=True, help="Path to write PDF figure")
    args = parser.parse_args(argv)
    make_figure(_load_csv(Path(args.input)), Path(args.output))


if __name__ == "__main__":
    main()
