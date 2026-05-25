"""Turn-by-turn inventory rows for Exp2 Arm 2 (optimised) — Figure 4.

Four panels, one per agent, sharing a common y-axis scale.  Each panel shows
N=5 runs as connected lines.  Filled dots = turn classified 'report'; open
circles = 'no_report'.  Colors from the model-family palette.

Data source: the mart-derived `exp2_turn_trajectory_view.csv` view.
The legacy probes/ reader remains available for backward-compatible tests.

Usage:
    python -m aedist.plot_exp2_turn_trajectory \
        --input report/inputs/generated/exp2_turn_trajectory_view.csv \
        --output report/inputs/generated/fig_exp2_turn_trajectory.pdf
"""

import argparse
import csv
import json
import logging
from pathlib import Path

from .extract import count_best_table_rows
from .util import COLOR_NEUTRAL, glyph_legend_handles, glyph_scatter_kwargs, model_family_color

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
            content = item.get("content")
            if not isinstance(content, list):
                continue
            parts.extend(
                block.get("text", "")
                for block in content
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
    return count_best_table_rows(text)


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


def _load_view_turns(view_csv: Path) -> list[dict]:
    with view_csv.open(newline="", encoding="utf-8") as fh:
        return [
            {
                "agent": row["agent"],
                "arm": row["arm"],
                "run": int(row["run"]),
                "turn": int(row["turn"]),
                "rows": int(row["rows"]),
                "cls": row["cls"],
            }
            for row in csv.DictReader(fh)
        ]


def make_figure_from_view(rows: list[dict], output: Path) -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 4, figsize=(10, 3.2), sharey=True)

    for ax, agent in zip(axes, _AGENT_ORDER, strict=True):
        color = model_family_color(_AGENT_MODEL[agent])
        for run in range(1, 6):
            turns = [r for r in rows if r["agent"] == agent and r["run"] == run]
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
                        **glyph_scatter_kwargs("arm2", color),
                        zorder=3,
                    )
                else:
                    ax.scatter(
                        [t["turn"]],
                        [t["rows"]],
                        **glyph_scatter_kwargs("arm3", color),
                        zorder=3,
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

    legend_handles = glyph_legend_handles(
        ["arm2", "arm3"],
        color=COLOR_NEUTRAL,
        label_overrides={"arm2": "report", "arm3": "no_report"},
    )
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


def make_figure(probes_dir: Path, output: Path) -> None:
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
                        **glyph_scatter_kwargs("arm2", color),
                        zorder=3,
                    )
                else:
                    ax.scatter(
                        [t["turn"]],
                        [t["rows"]],
                        **glyph_scatter_kwargs("arm3", color),
                        zorder=3,
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

    legend_handles = glyph_legend_handles(
        ["arm2", "arm3"],
        color=COLOR_NEUTRAL,
        label_overrides={"arm2": "report", "arm3": "no_report"},
    )
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
    parser.add_argument("--input", default="report/inputs/generated/exp2_turn_trajectory_view.csv")
    parser.add_argument("--probes-dir", default=None, help="Legacy probes/ directory input")
    parser.add_argument("--output", required=True, help="Path to write PDF figure")
    args = parser.parse_args(argv)

    if args.probes_dir:
        make_figure(Path(args.probes_dir), Path(args.output))
    else:
        make_figure_from_view(_load_view_turns(Path(args.input)), Path(args.output))


if __name__ == "__main__":
    main()
