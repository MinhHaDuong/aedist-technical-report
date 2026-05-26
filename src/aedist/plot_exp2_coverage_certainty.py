"""Coverage vs. corroboration scatter for all Exp2 runs.

X = assets correctly identified (``n_matched``, same axis as the coverage
figure); Y = assets backed by two sources (``src2_present``). One point per
run; per-model colour; condition (1N/5N/1D/5D) shown by glyph. Individual runs
are drawn at low alpha and the per-(model, condition) means at full alpha.

Glyph encoding (two-dimensional):
  Shape  — tours:     cercle (o) = 1 tour,  carré (s) = multitour (5 tours)
  Fill   — documents: plein (filled) = avec docs (D),  vide (empty) = sans docs (N)
  Colour — model family

Usage:
    python -m aedist.plot_exp2_coverage_certainty \
        --input report/inputs/generated/tab_exp2_bib_quality_view.csv \
        --arms-input report/inputs/generated/tab_exp2_arms_runs_view.csv \
        --output report/inputs/generated/fig_exp2_coverage_certainty.pdf
"""

import argparse
import csv
import logging
from collections import defaultdict
from pathlib import Path

from .util import SLIDE_FIGSIZE_FULL, model_family_color

log = logging.getLogger(__name__)

_AGENT_SLUG = {
    "anthropic": "claude",
    "openai": "gpt",
    "mistral": "mistral",
    "qwen": "qwen",
}

_AGENT_LABELS = {
    "anthropic": "Claude Opus 4.6",
    "openai": "GPT-5.5",
    "mistral": "Mistral Large",
    "qwen": "Qwen3-Max",
}

_AGENT_COLORS = {agent: model_family_color(slug) for agent, slug in _AGENT_SLUG.items()}

# Glyph encoding: shape = tours (cercle=1, carré=5); fill = docs (plein=D, vide=N)
_COND_LABEL = {"naive": "1N", "optimised": "5N", "arm3": "1D", "arm4": "5D"}
_COND_MARKER = {"naive": "o", "optimised": "s", "arm3": "o", "arm4": "s"}
_COND_FILLED = {"naive": False, "optimised": False, "arm3": True, "arm4": True}
# Legend order: 1D, 1N, 5D, 5N (cercles first, then carrés)
_COND_ORDER = ["arm3", "naive", "arm4", "optimised"]


def _load_matched(path: Path) -> dict[tuple[str, str, int], int]:
    """Map (agent, arm, run) -> n_matched from the arms-runs mart view."""
    matched: dict[tuple[str, str, int], int] = {}
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            raw = row.get("n_matched", "")
            if raw in ("", "None"):
                continue
            matched[(row["agent"], row["arm"], int(row["run"]))] = int(raw)
    return matched


def _load_points(bib_path: Path, matched: dict[tuple[str, str, int], int]) -> list[dict]:
    """Join bib-quality src2_present with arms n_matched on (agent, arm, run)."""
    points: list[dict] = []
    with bib_path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            agent = row["agent"]
            arm = row["arm"]
            if agent not in _AGENT_SLUG or arm not in _COND_LABEL:
                continue
            key = (agent, arm, int(row["run"]))
            n_matched = matched.get(key)
            if n_matched is None:
                # Unscored run (no cross-eval coverage): cannot place on X axis.
                continue
            points.append(
                {
                    "agent": agent,
                    "arm": arm,
                    "run": int(row["run"]),
                    "x": n_matched,
                    "y": int(row["src2_present"]),
                }
            )
    return points


def make_figure(points: list[dict], output: Path) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    fig, ax = plt.subplots(figsize=SLIDE_FIGSIZE_FULL)

    # Individual runs: faint. Means per (agent, condition): full alpha.
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for p in points:
        grouped[(p["agent"], p["arm"])].append(p)
        filled = _COND_FILLED[p["arm"]]
        color = _AGENT_COLORS[p["agent"]]
        ax.scatter(
            p["x"],
            p["y"],
            marker=_COND_MARKER[p["arm"]],
            s=28,
            facecolors=color if filled else "none",
            edgecolors="none" if filled else color,
            linewidths=0.8,
            alpha=0.15,
            zorder=2,
        )

    for (agent, arm), pts in grouped.items():
        mean_x = sum(p["x"] for p in pts) / len(pts)
        mean_y = sum(p["y"] for p in pts) / len(pts)
        filled = _COND_FILLED[arm]
        color = _AGENT_COLORS[agent]
        ax.scatter(
            mean_x,
            mean_y,
            marker=_COND_MARKER[arm],
            s=70,
            facecolors=color if filled else "none",
            edgecolors="black" if filled else color,
            linewidths=0.8 if filled else 1.2,
            alpha=0.95,
            zorder=4,
        )

    if points:
        hi = max(max(p["x"], p["y"]) for p in points)
        ax.plot([0, hi], [0, hi], color="0.75", linewidth=0.8, linestyle="--", zorder=1)

    ax.set_xlabel("Assets correctly identified (coverage)", fontsize=10)
    ax.set_ylabel("Assets from two sources (corroboration)", fontsize=10)
    ax.set_title(
        "How many rows are justified by two sources?",
        fontsize=13,
        fontweight="bold",
        pad=18,
    )
    ax.set_xlim(left=-3)
    ax.set_ylim(bottom=-3)
    ax.tick_params(labelsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Glyph legend row above the plot, encoding explanation as figure footnote
    cond_handles = [
        Line2D(
            [0],
            [0],
            marker=_COND_MARKER[cond],
            linestyle="",
            markerfacecolor="0.4" if _COND_FILLED[cond] else "none",
            markeredgecolor="0.4",
            markersize=7,
            label=_COND_LABEL[cond],
        )
        for cond in _COND_ORDER
    ]
    cond_legend = ax.legend(
        handles=cond_handles,
        loc="lower center",
        bbox_to_anchor=(0.5, 1.0),
        ncol=4,
        fontsize=9,
        frameon=False,
        handletextpad=0.3,
        columnspacing=1.4,
    )
    ax.add_artist(cond_legend)
    fig.text(
        0.5,
        0.01,
        "rond = 1 tour   carré = 5 tours   |   plein = avec documents   vide = sans documents",
        ha="center",
        fontsize=7.5,
        color="0.4",
    )

    model_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="",
            markerfacecolor=color,
            markeredgecolor=color,
            markersize=7,
            label=_AGENT_LABELS[agent],
        )
        for agent, color in _AGENT_COLORS.items()
    ]
    ax.legend(
        handles=model_handles,
        title="Model colour",
        loc="lower right",
        fontsize=8,
        title_fontsize=8.5,
        frameon=False,
    )

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", dpi=150)
    plt.close(fig)
    log.info("Wrote %s (%d run points)", output, len(points))


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Coverage vs. corroboration scatter for Exp2 runs",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to tab_exp2_bib_quality_view.csv (provides src2_present)",
    )
    parser.add_argument(
        "--arms-input",
        default="report/inputs/generated/tab_exp2_arms_runs_view.csv",
        help="Path to tab_exp2_arms_runs_view.csv (provides n_matched for the X axis)",
    )
    parser.add_argument("--output", required=True, help="Path to write PDF figure")
    args = parser.parse_args(argv)
    matched = _load_matched(Path(args.arms_input))
    points = _load_points(Path(args.input), matched)
    assert len(points) > 0, f"No joined points from {args.input} + {args.arms_input}"
    make_figure(points, Path(args.output))


if __name__ == "__main__":
    main()
