"""Render the empirical capability-ordering figure for §3.

Panel A: 8×8 heatmap showing, for each ordered pair (i, j) of
capability stages, the fraction of labs where stage i shipped before
stage j (conditional on both being present).  N is labelled per cell.

Panel B: dot-range plot for transitions with N ≥ 4, showing the
time gap (months) between stage i and stage j for each lab.

Data source: ``data/capability_timeline.csv``.

Usage:
    uv run python -m aedist.plot_capability_dag \
        --input data/capability_timeline.csv \
        --output slides/inputs/generated/fig_capability_dag.pdf
"""

import argparse
import csv
import logging
from collections import defaultdict
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from .util import model_family_color

logger = logging.getLogger(__name__)

LAB_ORDER = ["Anthropic", "OpenAI", "Mistral", "Alibaba", "DeepSeek"]

LAB_COLOR = {
    "Anthropic": model_family_color("claude"),
    "OpenAI": model_family_color("gpt"),
    "Mistral": model_family_color("mistral"),
    "Alibaba": model_family_color("qwen"),
    "DeepSeek": model_family_color("deepseek"),
}

LAB_MARKER = {
    "Anthropic": "o",
    "OpenAI": "s",
    "Mistral": "D",
    "Alibaba": "^",
    "DeepSeek": "v",
}

STAGE_LABELS = {
    1: "1. Chat LLM",
    2: "2. Retrieval",
    3: "3. Browsing",
    4: "4. Code exec.",
    5: "5. Reasoning",
    6: "6. Deep research",
    7: "7. Tool use",
    8: "8. Multi-agent",
}

N_STAGES = 8
MIN_N_PANEL_B = 4


def load_lab_dates(path: Path) -> dict[str, dict[int, date]]:
    lab_dates: dict[str, dict[int, date]] = defaultdict(dict)
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            raw = row["date"].strip()
            if raw:
                try:
                    lab_dates[row["lab"]][int(row["stage"])] = date.fromisoformat(raw)
                except ValueError:
                    logger.warning("unparseable date %r — skipping", raw)
    return dict(lab_dates)


def compute_matrix(
    lab_dates: dict[str, dict[int, date]],
) -> tuple[np.ndarray, np.ndarray]:
    stages = range(1, N_STAGES + 1)
    frac = np.full((N_STAGES, N_STAGES), np.nan)
    counts = np.zeros((N_STAGES, N_STAGES), dtype=int)

    for i in stages:
        for j in stages:
            if i == j:
                continue
            n_before = 0
            n_total = 0
            for lab in lab_dates:
                if i in lab_dates[lab] and j in lab_dates[lab]:
                    n_total += 1
                    if lab_dates[lab][i] < lab_dates[lab][j]:
                        n_before += 1
            counts[i - 1, j - 1] = n_total
            if n_total >= 2:
                frac[i - 1, j - 1] = n_before / n_total
    return frac, counts


def render_heatmap(ax: plt.Axes, frac: np.ndarray, counts: np.ndarray) -> None:
    cmap = plt.cm.Greens

    masked = np.ma.masked_invalid(frac)
    ax.imshow(masked, cmap=cmap, vmin=0.0, vmax=1.0, aspect="equal", origin="upper")

    for i in range(N_STAGES):
        for j in range(N_STAGES):
            if i == j:
                ax.text(j, i, "—", ha="center", va="center", fontsize=7, color="gray")
                continue
            n = counts[i, j]
            if n < 2:
                ax.text(j, i, f"N={n}", ha="center", va="center", fontsize=6, color="gray")
                continue
            f = frac[i, j]
            text_color = "white" if f > 0.75 else "black"
            label = f"{f:.0%}\nN={n}" if f > 0 else f"N={n}"
            ax.text(j, i, label, ha="center", va="center", fontsize=6, color=text_color)

    labels = [STAGE_LABELS[s] for s in range(1, N_STAGES + 1)]
    ax.set_xticks(range(N_STAGES))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
    ax.set_yticks(range(N_STAGES))
    ax.set_yticklabels(labels, fontsize=7)
    ax.set_xlabel("Stage j (column)", fontsize=8)
    ax.set_ylabel("Stage i (row)", fontsize=8)
    ax.set_title("(a) Fraction of labs where i shipped before j", fontsize=9, pad=8)


def render_dotrange(
    ax: plt.Axes,
    lab_dates: dict[str, dict[int, date]],
    frac: np.ndarray,
    counts: np.ndarray,
) -> None:
    transitions = []
    for i in range(1, N_STAGES + 1):
        for j in range(i + 1, N_STAGES + 1):
            n = counts[i - 1, j - 1]
            if n >= MIN_N_PANEL_B:
                f = frac[i - 1, j - 1]
                transitions.append((i, j, n, f))

    transitions.sort(key=lambda t: t[3], reverse=True)

    y_positions = list(range(len(transitions)))
    y_labels = []

    for y_pos, (i, j, n, _f) in enumerate(transitions):
        gaps = []
        for lab in LAB_ORDER:
            if i in lab_dates.get(lab, {}) and j in lab_dates.get(lab, {}):
                gap_days = (lab_dates[lab][j] - lab_dates[lab][i]).days
                gap_months = gap_days / 30.44
                gaps.append((lab, gap_months))
                ax.scatter(
                    gap_months,
                    y_pos,
                    s=60,
                    marker=LAB_MARKER[lab],
                    color=LAB_COLOR[lab],
                    edgecolor="black",
                    linewidth=0.5,
                    zorder=3,
                )
        if gaps:
            values = [g for _, g in gaps]
            ax.plot(
                [min(values), max(values)],
                [y_pos, y_pos],
                color="gray",
                linewidth=1,
                zorder=1,
            )
        y_labels.append(f"{i}→{j} (N={n})")

    ax.axvline(0, color="gray", linewidth=0.5, linestyle="--", zorder=0)
    ax.set_yticks(y_positions)
    ax.set_yticklabels(y_labels, fontsize=7)
    ax.set_xlabel("Gap (months, i before j)", fontsize=8)
    ax.set_title(f"(b) Time gap for transitions with N ≥ {MIN_N_PANEL_B}", fontsize=9, pad=8)
    ax.invert_yaxis()
    ax.grid(axis="x", linestyle=":", alpha=0.4)

    handles = [
        plt.Line2D(
            [],
            [],
            linestyle="",
            marker=LAB_MARKER[lab],
            markerfacecolor=LAB_COLOR[lab],
            markeredgecolor="black",
            markersize=7,
            label=lab,
        )
        for lab in LAB_ORDER
    ]
    ax.legend(
        handles=handles,
        loc="lower right",
        fontsize=7,
        frameon=True,
        framealpha=0.9,
    )


def render(lab_dates: dict[str, dict[int, date]], output: Path) -> None:
    frac, counts = compute_matrix(lab_dates)

    fig, (ax_heat, ax_dots) = plt.subplots(
        1,
        2,
        figsize=(12, 5.5),
        gridspec_kw={"width_ratios": [1, 1.2]},
    )

    render_heatmap(ax_heat, frac, counts)
    render_dotrange(ax_dots, lab_dates, frac, counts)

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight")
    logger.info("wrote %s", output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/capability_timeline.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("slides/inputs/generated/fig_capability_dag.pdf"),
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    lab_dates = load_lab_dates(args.input)
    render(lab_dates, args.output)


if __name__ == "__main__":
    main()
