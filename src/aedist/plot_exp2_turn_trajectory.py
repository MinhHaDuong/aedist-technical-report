"""Turn-by-turn inventory rows for Exp2 Arm 2 (optimised) — Figure 4.

Four panels, one per agent, sharing a common y-axis scale.  Each panel shows
N=5 runs as connected lines.  Filled dots = turn classified 'report'; open
circles = 'no_report'.  Colors from the model-family palette.

Data source: probes/ subdirectory of the optimised arm output directory.
Each run has per-turn raw API responses (*.raw.json) and classifier verdicts
(*.classification.json).

Usage:
    python -m aedist.plot_exp2_turn_trajectory \\
        --probes-dir experiments/outputs/sota_exp2_brerun1/probes \\
        --output report/inputs/generated/fig_exp2_turn_trajectory.pdf
"""

import argparse
import json
import logging
from pathlib import Path

from .util import model_family_color

log = logging.getLogger(__name__)

_AGENT_ORDER = ["anthropic", "mistral", "openai", "qwen"]
_AGENT_LABELS = {
    "anthropic": "Anthropic\nOpus 4.6",
    "mistral": "Mistral\nLarge 2512",
    "openai": "OpenAI\nGPT-5.5",
    "qwen": "Qwen3\nMax",
}
# Canonical model slug for palette lookup
_AGENT_MODEL = {
    "anthropic": "claude-opus-4-6",
    "mistral": "mistral-large-2512",
    "openai": "gpt-5.5",
    "qwen": "qwen3-max",
}


def _extract_text(d: dict) -> str:
    """Return assistant narrative from a raw API response dict."""
    # Anthropic Messages / Responses API
    if "content" in d and isinstance(d["content"], list):
        return " ".join(b.get("text", "") for b in d["content"] if b.get("type") == "text")
    # Qwen DashScope
    if isinstance(d.get("output"), dict) and "choices" in d["output"]:
        return d["output"]["choices"][0]["message"].get("content", "")
    # OpenAI Responses API
    if isinstance(d.get("output"), list):
        parts = []
        for item in d["output"]:
            if not isinstance(item, dict):
                continue
            parts.extend(
                block.get("text", "")
                for block in item.get("content", [])
                if isinstance(block, dict) and block.get("type") == "output_text"
            )
        return " ".join(p for p in parts if p)
    # Mistral Agents API
    if isinstance(d.get("outputs"), list):
        for o in reversed(d["outputs"]):
            if o.get("type") == "message.output":
                c = o.get("content", "")
                if isinstance(c, list):
                    return " ".join(x.get("text", "") for x in c if isinstance(x, dict))
                return str(c)
    return ""


def _count_table_rows(text: str) -> int:
    lines = text.splitlines()
    tbl = [line.strip() for line in lines if line.strip().startswith("|")]
    data = [line for line in tbl if not all(c in "-|: " for c in line)]
    return max(0, len(data) - 1)


def load_run_turns(probes_dir: Path, agent: str, run: int) -> list[dict]:
    """Return [{turn, rows, cls}, …] in turn order for one run."""
    run_dir = probes_dir / f"{agent}_run{run:02d}"
    if not run_dir.exists():
        return []
    result = []
    for raw_path in sorted(run_dir.glob(f"{agent}_turn_*.raw.json")):
        turn_num = int(raw_path.name.replace(".raw.json", "").split("_turn_")[1])
        cls_path = raw_path.parent / raw_path.name.replace(".raw.json", ".classification.json")
        cls = "no_report"
        if cls_path.exists():
            cls = json.loads(cls_path.read_text(encoding="utf-8")).get("class", "no_report")
        text = _extract_text(json.loads(raw_path.read_text(encoding="utf-8")))
        result.append({"turn": turn_num, "rows": _count_table_rows(text), "cls": cls})
    return result


def make_figure(probes_dir: Path, output: Path) -> None:
    import matplotlib.patches as mpatches
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 4, figsize=(10, 3.2), sharey=True)

    for ax, agent in zip(axes, _AGENT_ORDER, strict=True):
        color = model_family_color(_AGENT_MODEL[agent])
        for run in range(1, 6):
            turns = load_run_turns(probes_dir, agent, run)
            if not turns:
                continue
            xs = [t["turn"] for t in turns]
            ys = [t["rows"] for t in turns]
            ax.plot(xs, ys, color=color, linewidth=0.8, alpha=0.45, zorder=2)
            for t in turns:
                if t["cls"] == "report":
                    ax.scatter(
                        [t["turn"]],
                        [t["rows"]],
                        color=color,
                        s=24,
                        zorder=3,
                        linewidths=0,
                    )
                else:
                    ax.scatter(
                        [t["turn"]],
                        [t["rows"]],
                        facecolors="none",
                        edgecolors=color,
                        s=24,
                        zorder=3,
                        linewidths=1.1,
                    )

        ax.set_title(_AGENT_LABELS[agent], fontsize=8, loc="left")
        ax.set_xlabel("Turn", fontsize=7.5)
        ax.set_xticks([1, 2, 3, 4])
        ax.tick_params(labelsize=7.5)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_ylim(bottom=0)

    axes[0].set_ylabel("Inventory rows", fontsize=8)
    for ax in axes[1:]:
        ax.tick_params(left=False)

    legend_handles = [
        mpatches.Patch(color="#444444", label="● report"),
        plt.Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor="none",
            markeredgecolor="#444444",
            markersize=6,
            label="○ no_report",
        ),
    ]
    fig.legend(
        handles=legend_handles,
        loc="lower center",
        ncol=2,
        fontsize=8,
        frameon=False,
        bbox_to_anchor=(0.5, -0.06),
    )
    fig.suptitle(
        "Arm 2 (optimised) — inventory rows per turn, N=5 runs per agent",
        fontsize=9,
        y=1.01,
    )
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", dpi=150)
    plt.close(fig)
    log.info("Wrote %s", output)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Exp2 Arm 2 turn-trajectory figure")
    parser.add_argument("--probes-dir", required=True, help="Path to probes/ directory")
    parser.add_argument("--output", required=True, help="Path to write PDF figure")
    args = parser.parse_args(argv)
    make_figure(Path(args.probes_dir), Path(args.output))


if __name__ == "__main__":
    main()
