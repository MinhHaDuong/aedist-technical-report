"""Grounding ladder figure: E1 → 1N → 1D → 5D (paired within-agent deltas).

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.

Each rung isolates one factor:
  E1 → 1N: harness + source tier (single-shot agentic scaffold, no documents)
  1N → 1D: documents (web/harness fixed in code; only change is provided docs)
  1D → 5D: multi-turn (turns 1 → 5 with documents)

Restricted to the 4 agents present in both Exp1 and Exp2, as defined by
``_AGENT_EXP1_SLUG`` in :mod:`aedist.plot_exp2_arms_split`.

Produces two panels:
  - Accuracy panel: F1 and coverage absolute values per rung, per agent.
  - Provenance panel: source_spread and source_diversity values per rung.

Each panel shows absolute values (not just deltas) so the ladder shape is
directly readable; within-agent pairing is enforced — one delta per agent per
rung, never pooled.

Usage:
    python -m aedist.plot_grounding_ladder \\
        --exp1 experiments/derived/exp1_cross_eval.csv \\
        --exp2 experiments/derived/sota_cross_eval.csv \\
        --output report/inputs/generated/fig_grounding_ladder.pdf
"""

import argparse
import csv
import logging
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from matplotlib.figure import Figure

from .plot_exp2_arms_split import _AGENT_EXP1_SLUG, _AGENT_MODEL
from .util import SLIDE_FIGSIZE_WIDE, model_family_color

log = logging.getLogger(__name__)

# Ladder rung ordering: E1 → 1N(arm1) → 1D(arm3) → 5D(arm4).  arm2 (5N) is
# deliberately omitted — the ladder step is documents, not multi-turn-no-docs.
_LADDER_RUNGS = ["e1", "arm1", "arm3", "arm4"]
_RUNG_LABEL = {"e1": "E1", "arm1": "1N", "arm3": "1D", "arm4": "5D"}

# Rung-pair labels (shown as arrows between rungs).
_STEP_LABELS = {
    ("e1", "arm1"): "harness\n+ tier",
    ("arm1", "arm3"): "documents",
    ("arm3", "arm4"): "multi-turn",
}

# Metrics to display, grouped by panel.
_ACCURACY_METRICS = ["accuracy_f1", "accuracy_coverage"]
_PROVENANCE_METRICS = ["provenance_source_spread", "provenance_source_diversity"]

_METRIC_LABEL = {
    "accuracy_f1": "F1",
    "accuracy_coverage": "Coverage",
    "provenance_source_spread": "Source spread",
    "provenance_source_diversity": "Source diversity",
}

# Human-readable labels for the 4 agents.
_AGENT_LABELS = {
    "anthropic": "Anthropic\nOpus 4.6",
    "mistral": "Mistral\nLarge 2512",
    "openai": "OpenAI\nGPT-5.5",
    "qwen": "Qwen3\nMax",
}
_AGENT_ORDER = ["anthropic", "mistral", "openai", "qwen"]

# Map Exp2 sota_cross_eval.csv model slugs to agent keys.
_EXP2_MODEL_TO_AGENT: dict[str, str] = {
    "claude-opus-4-6": "anthropic",
    "mistral-large-2512": "mistral",
    "gpt-5.5": "openai",
    "qwen3.7-max": "qwen",
}


# ── Data structures ────────────────────────────────────────────────────────────


@dataclass
class LadderStep:
    """A within-agent delta across one rung of the ladder."""

    agent: str
    from_rung: str
    to_rung: str
    metric: str
    delta: float
    from_value: float
    to_value: float


# ── Public API (consumed by tests) ────────────────────────────────────────────


def ladder_agents() -> set[str]:
    """Return the set of agent keys (keys of ``_AGENT_EXP1_SLUG``)."""
    return set(_AGENT_EXP1_SLUG)


def ladder_deltas(
    rung_means: dict[str, dict[str, dict[str, float]]],
    metrics: list[str] | None = None,
) -> list[LadderStep]:
    """Compute within-agent paired deltas across adjacent rungs.

    Parameters
    ----------
    rung_means:
        Nested dict ``{agent: {rung: {metric: mean_value}}}``.
    metrics:
        Metrics to include. Defaults to all accuracy + provenance metrics.

    Returns
    -------
    List of :class:`LadderStep` objects, one per (agent, adjacent-rung-pair,
    metric).  Each step's ``.agent`` is always set — pairing is strictly
    within-agent, never pooled.
    """
    if metrics is None:
        metrics = _ACCURACY_METRICS + _PROVENANCE_METRICS

    steps: list[LadderStep] = []
    rungs = _LADDER_RUNGS
    for agent in _AGENT_ORDER:
        agent_data = rung_means.get(agent, {})
        for i in range(len(rungs) - 1):
            from_rung = rungs[i]
            to_rung = rungs[i + 1]
            from_data = agent_data.get(from_rung, {})
            to_data = agent_data.get(to_rung, {})
            steps.extend(
                LadderStep(
                    agent=agent,
                    from_rung=from_rung,
                    to_rung=to_rung,
                    metric=metric,
                    delta=to_data[metric] - from_data[metric],
                    from_value=from_data[metric],
                    to_value=to_data[metric],
                )
                for metric in metrics
                if metric in from_data and metric in to_data
            )
    return steps


# ── Data loading ───────────────────────────────────────────────────────────────


def _exp2_agent_for(model: str) -> str | None:
    """Map an Exp2 model slug to an agent key (prefix match)."""
    for prefix, agent in _EXP2_MODEL_TO_AGENT.items():
        if model.startswith(prefix):
            return agent
    return None


def load_rung_means(
    exp1_path: Path,
    exp2_path: Path,
    all_metrics: list[str] | None = None,
) -> dict[str, dict[str, dict[str, float]]]:
    """Load and aggregate per-rung metric means for the 4 shared agents.

    Returns ``{agent: {rung: {metric: mean_value}}}``.
    """
    if all_metrics is None:
        all_metrics = _ACCURACY_METRICS + _PROVENANCE_METRICS

    # {agent: {rung: {metric: [values]}}}
    raw: dict[str, dict[str, dict[str, list[float]]]] = {
        agent: {rung: {m: [] for m in all_metrics} for rung in _LADDER_RUNGS}
        for agent in _AGENT_ORDER
    }

    # --- Exp1 (e1 rung) -------------------------------------------------------
    slug_to_agent = {v: k for k, v in _AGENT_EXP1_SLUG.items()}  # slug → agent key
    with exp1_path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            agent = slug_to_agent.get(row["model"])
            if agent is None:
                continue
            for metric in all_metrics:
                raw_val = row.get(metric, "")
                if raw_val:
                    raw[agent]["e1"][metric].append(float(raw_val))

    # --- Exp2 (arm1=1N, arm3=1D, arm4=5D) ------------------------------------
    arm_map_exp2 = {"naive": "arm1", "arm1": "arm1", "arm3": "arm3", "arm4": "arm4"}
    with exp2_path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            agent = _exp2_agent_for(row["model"])
            if agent is None:
                continue
            rung = arm_map_exp2.get(row["arm"])
            if rung is None:
                continue  # arm2 (5N) is not on this ladder
            for metric in all_metrics:
                raw_val = row.get(metric, "")
                if raw_val:
                    raw[agent][rung][metric].append(float(raw_val))

    # Collapse to means.
    result: dict[str, dict[str, dict[str, float]]] = {}
    for agent in _AGENT_ORDER:
        result[agent] = {}
        for rung in _LADDER_RUNGS:
            result[agent][rung] = {}
            for metric in all_metrics:
                vals = raw[agent][rung][metric]
                if vals:
                    result[agent][rung][metric] = statistics.mean(vals)

    return result


# ── Figure builder ─────────────────────────────────────────────────────────────


def make_figure(
    exp1_path: Path,
    exp2_path: Path,
    output: Path,
) -> "Figure":
    """Build the grounding-ladder figure and save to *output*.

    Two vertically stacked panels:
    - Top: accuracy_f1 and accuracy_coverage across the four rungs.
    - Bottom: provenance_source_spread and provenance_source_diversity.

    Each panel has one sub-group per agent; rungs are the x-axis.
    Lines connect rungs within an agent to show the ladder trajectory.
    """
    import matplotlib.pyplot as plt

    rung_means = load_rung_means(exp1_path, exp2_path)

    fig, axes = plt.subplots(
        2, 1, figsize=SLIDE_FIGSIZE_WIDE, constrained_layout=True, sharex=False
    )

    panel_metrics = [_ACCURACY_METRICS, _PROVENANCE_METRICS]
    panel_titles = [
        "Accuracy ladder  (F1 and Coverage)",
        "Provenance / grounding ladder  (Source spread and Source diversity)",
    ]

    rung_x = {rung: i for i, rung in enumerate(_LADDER_RUNGS)}
    x_labels = [_RUNG_LABEL[r] for r in _LADDER_RUNGS]

    # Separate cluster offset per agent within the same rung x-position.
    n_agents = len(_AGENT_ORDER)
    agent_offsets = {
        agent: (idx - (n_agents - 1) / 2) * 0.18
        for idx, agent in enumerate(_AGENT_ORDER)
    }

    for panel_idx, (metrics, title) in enumerate(zip(panel_metrics, panel_titles, strict=True)):
        ax = axes[panel_idx]

        line_styles = ["-", "--"]
        for m_idx, metric in enumerate(metrics):
            metric_label = _METRIC_LABEL[metric]
            ls = line_styles[m_idx]
            for agent in _AGENT_ORDER:
                color = model_family_color(_AGENT_MODEL[agent])
                agent_data = rung_means.get(agent, {})
                xs = []
                ys = []
                for rung in _LADDER_RUNGS:
                    val = agent_data.get(rung, {}).get(metric)
                    if val is not None:
                        xs.append(rung_x[rung] + agent_offsets[agent])
                        ys.append(val)
                if len(xs) >= 2:
                    label = (
                        f"{_AGENT_LABELS[agent].replace(chr(10), ' ')} · {metric_label}"
                        if panel_idx == 0 and m_idx == 0
                        else None
                    )
                    ax.plot(
                        xs,
                        ys,
                        marker="o",
                        ms=6,
                        color=color,
                        linestyle=ls,
                        linewidth=1.5,
                        alpha=0.85,
                        label=label,
                    )

        # Annotate rung-transition step labels at the top of the panel.
        ax.set_xticks(list(rung_x.values()))
        ax.set_xticklabels(x_labels, fontsize=10)
        ax.set_xlim(-0.6, len(_LADDER_RUNGS) - 0.4)
        ax.set_ylim(0.0, 1.05)
        ax.set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
        ax.yaxis.set_major_formatter(lambda val, pos: f"{val:.0%}")
        ax.set_title(title, fontsize=10, fontweight="bold", pad=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(axis="y", labelsize=8)

        # Step annotations between rungs.
        y_ann = 1.02
        for (from_rung, to_rung), step_text in _STEP_LABELS.items():
            x_mid = (rung_x[from_rung] + rung_x[to_rung]) / 2
            ax.annotate(
                step_text,
                xy=(x_mid, y_ann),
                xycoords=("data", "axes fraction"),
                ha="center",
                va="bottom",
                fontsize=7,
                color="0.40",
                annotation_clip=False,
            )

        # Solid line = first metric, dashed = second (in legend).
        handles_metric = [
            plt.Line2D([0], [0], color="0.4", linestyle=ls, linewidth=1.5, label=_METRIC_LABEL[m])
            for m, ls in zip(metrics, line_styles, strict=True)
        ]
        # Agent color patches.
        handles_agent = [
            plt.Line2D(
                [0],
                [0],
                color=model_family_color(_AGENT_MODEL[agent]),
                marker="o",
                ms=5,
                linestyle="none",
                label=_AGENT_LABELS[agent].replace("\n", " "),
            )
            for agent in _AGENT_ORDER
        ]
        ax.legend(
            handles=handles_metric + handles_agent,
            fontsize=7,
            loc="lower right",
            ncol=2,
            framealpha=0.7,
        )

    fig.suptitle(
        "Grounding ladder: E1 (memory only) → 1N (harness, no docs) → 1D (+ docs) → 5D (multi-turn + docs)\n"
        "Within-agent paired means · 4 shared agents · solid = first metric, dashed = second",
        fontsize=8,
        y=0.0,
        va="top",
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", dpi=150)
    plt.close(fig)
    log.info("Wrote %s", output)
    return fig


# ── Entry point ────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="E1→1N→1D→5D grounding ladder figure (paired within-agent)"
    )
    parser.add_argument(
        "--exp1",
        default="experiments/derived/exp1_cross_eval.csv",
        help="Path to exp1_cross_eval.csv",
    )
    parser.add_argument(
        "--exp2",
        default="experiments/derived/sota_cross_eval.csv",
        help="Path to sota_cross_eval.csv",
    )
    parser.add_argument(
        "--output",
        default="report/inputs/generated/fig_grounding_ladder.pdf",
        help="Path to write the output PDF",
    )
    args = parser.parse_args(argv)
    make_figure(Path(args.exp1), Path(args.exp2), Path(args.output))


if __name__ == "__main__":
    main()
