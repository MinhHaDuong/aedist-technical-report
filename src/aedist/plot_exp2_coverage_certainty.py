"""Coverage vs. corroboration scatter for all Exp2 runs.

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.

X = assets correctly identified (``n_matched``, same axis as the coverage
figure); Y = assets backed by two sources (``src2_present``). One point per
run; per-model colour; condition (1N/5N/1D/5D) shown by glyph. Individual runs
are drawn at low alpha and the per-(model, condition) means at full alpha.

Glyph encoding (two-dimensional):
  Shape  — tours:     cercle (o) = 1 tour,  carré (s) = multitour (5 tours)
  Fill   — documents: plein (filled) = avec docs (D),  vide (empty) = sans docs (N)
  Colour — model family

D-arm data (arm3, arm4): from tab_exp2_bib_quality_view.csv + tab_exp2_arms_runs_view.csv.
N-arm data (naive, optimised): from sota_cross_eval.csv
  X = accuracy_coverage × N_REF_PLANTS
  Y = provenance_high_conf_dual_source × n_rows  (skip if missing)

Usage:
    python -m aedist.plot_exp2_coverage_certainty \
        --input report/inputs/generated/tab_exp2_bib_quality_view.csv \
        --arms-input report/inputs/generated/tab_exp2_arms_runs_view.csv \
        --cross-eval experiments/derived/sota_cross_eval.csv \
        --output report/inputs/generated/fig_exp2_coverage_certainty.pdf
"""

import argparse
import csv
import logging
from collections import defaultdict
from pathlib import Path

from .evaluate import reference_plant_count
from .util import SLIDE_FIGSIZE_FULL, model_family_color

log = logging.getLogger(__name__)

# Coverage-ratio denominator — derived from the adopted release (ticket 0413,
# single source of truth). Used to reconstruct n_matched = coverage × N below;
# coverage is itself computed over this same count, so they must agree.
_N_REFERENCE_PLANTS = reference_plant_count()

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

# Model name → agent family (cross-eval uses versioned model names)
_MODEL_TO_AGENT: dict[str, str] = {
    "claude-opus-4-6": "anthropic",
    "mistral-large-2512": "mistral",
    "gpt-5.5": "openai",
    "gpt-5.5-2026-04-23": "openai",
    "qwen3.7-max-2026-05-20": "qwen",
}

# Glyph encoding: shape = tours (cercle=1, carré=5); fill = docs (plein=D, vide=N)
_COND_LABEL = {"naive": "1N", "optimised": "5N", "arm3": "1D", "arm4": "5D"}
_COND_MARKER = {"naive": "o", "optimised": "s", "arm3": "o", "arm4": "s"}
_COND_FILLED = {"naive": False, "optimised": False, "arm3": True, "arm4": True}
# Legend order: 1D, 1N, 5D, 5N (cercles first, then carrés)
_COND_ORDER = ["arm3", "naive", "arm4", "optimised"]

_N_ARMS = {"naive", "optimised"}
_D_ARMS = {"arm3", "arm4"}


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


def _load_d_points(bib_path: Path, matched: dict[tuple[str, str, int], int]) -> list[dict]:
    """D-arm points: join bib-quality src2_present with n_matched."""
    points: list[dict] = []
    with bib_path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            agent = row["agent"]
            arm = row["arm"]
            if agent not in _AGENT_SLUG or arm not in _D_ARMS:
                continue
            src2 = int(row["src2_present"])
            if src2 == 0 and int(row.get("n_rows", 0)) == 0:
                continue  # mart parse failure: no bib data for this run
            key = (agent, arm, int(row["run"]))
            n_matched = matched.get(key)
            if n_matched is None:
                continue
            points.append(
                {
                    "agent": agent,
                    "arm": arm,
                    "run": int(row["run"]),
                    "x": n_matched,
                    "y": src2,
                }
            )
    return points


def _load_n_points(cross_eval_path: Path) -> list[dict]:
    """N-arm points from cross-eval CSV: coverage→n_matched, dual_source×n_rows→src2."""
    points: list[dict] = []
    with cross_eval_path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            arm = row.get("arm", "")
            if arm not in _N_ARMS:
                continue
            agent = _MODEL_TO_AGENT.get(row.get("model", ""))
            if agent not in _AGENT_SLUG:
                continue
            cov_raw = row.get("accuracy_coverage", "")
            dual_raw = row.get("provenance_high_conf_dual_source", "")
            n_rows_raw = row.get("n_rows", "")
            if not cov_raw or not dual_raw or not n_rows_raw:
                continue
            n_matched = round(float(cov_raw) * _N_REFERENCE_PLANTS)
            src2 = round(float(dual_raw) * int(n_rows_raw))
            points.append(
                {
                    "agent": agent,
                    "arm": arm,
                    "run": int(row["run"]),
                    "x": n_matched,
                    "y": src2,
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
            linewidths=1.2,
            alpha=0.15 if filled else 0.40,
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
            s=80,
            facecolors=color if filled else "none",
            edgecolors="black" if filled else color,
            linewidths=0.8 if filled else 2.0,
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
        pad=28,
    )
    ax.text(
        0.5,
        1.02,
        "rond = 1 tour   carré = 5 tours   |   plein = avec documents   vide = sans documents",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=8.5,
        color="0.45",
    )
    ax.set_xlim(left=-3)
    ax.set_ylim(bottom=-3)
    ax.tick_params(labelsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

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
    n_d = sum(1 for p in points if p["arm"] in _D_ARMS)
    n_n = sum(1 for p in points if p["arm"] in _N_ARMS)
    log.info("Wrote %s (%d D-arm + %d N-arm points)", output, n_d, n_n)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Coverage vs. corroboration scatter for Exp2 runs",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to tab_exp2_bib_quality_view.csv (D-arm src2_present)",
    )
    parser.add_argument(
        "--arms-input",
        default="report/inputs/generated/tab_exp2_arms_runs_view.csv",
        help="Path to tab_exp2_arms_runs_view.csv (D-arm n_matched)",
    )
    parser.add_argument(
        "--cross-eval",
        default="experiments/derived/sota_cross_eval.csv",
        help="Path to sota_cross_eval.csv (N-arm coverage and dual_source)",
    )
    parser.add_argument("--output", required=True, help="Path to write PDF figure")
    args = parser.parse_args(argv)
    matched = _load_matched(Path(args.arms_input))
    points = _load_d_points(Path(args.input), matched)
    points += _load_n_points(Path(args.cross_eval))
    assert len(points) > 0, "No points loaded"
    make_figure(points, Path(args.output))


if __name__ == "__main__":
    main()
