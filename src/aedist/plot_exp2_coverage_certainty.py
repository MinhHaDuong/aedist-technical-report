"""Coverage vs. certainty scatter for all Exp2 runs.

Usage:
    python -m aedist.plot_exp2_coverage_certainty \
        --input report/inputs/generated/tab_exp2_bib_quality.csv \
        --output report/inputs/generated/fig_exp2_coverage_certainty.pdf
"""

import argparse
import csv
import logging
from pathlib import Path

from .util import model_family_color

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


def _load_csv(path: Path) -> list[dict]:
    rows = []
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            n_rows = int(row["n_rows"])
            if n_rows == 0:
                continue
            rows.append(
                {
                    "agent": row["agent"],
                    "arm": row["arm"],
                    "run": int(row["run"]),
                    "n_rows": n_rows,
                    "src2_present": int(row["src2_present"]),
                }
            )
    return rows


def make_figure(rows: list[dict], output: Path) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(5.5, 4.0))

    for agent, color in _AGENT_COLORS.items():
        for arm in ("naive", "optimised"):
            subset = [r for r in rows if r["agent"] == agent and r["arm"] == arm]
            if not subset:
                continue
            xs = [r["n_rows"] for r in subset]
            ys = [r["src2_present"] for r in subset]

            if arm == "optimised":
                ax.scatter(
                    xs,
                    ys,
                    color=color,
                    s=40,
                    zorder=3,
                    label=f"{_AGENT_LABELS[agent]} opt.",
                    linewidths=0.5,
                    edgecolors="white",
                )
            else:
                ax.scatter(
                    xs,
                    ys,
                    facecolors="none",
                    edgecolors=color,
                    s=40,
                    zorder=3,
                    linewidths=1.2,
                    label=f"{_AGENT_LABELS[agent]} naive",
                )

    max_val = max(max(r["n_rows"], r["src2_present"]) for r in rows)
    ax.plot([0, max_val], [0, max_val], color="0.75", linewidth=0.8, zorder=1, linestyle="--")

    for r in rows:
        if r["n_rows"] > 140 or r["src2_present"] > 100:
            ax.annotate(
                f"{_AGENT_LABELS[r['agent']].split()[0]} r{r['run']}",
                (r["n_rows"], r["src2_present"]),
                fontsize=5.5,
                xytext=(4, 4),
                textcoords="offset points",
                color=_AGENT_COLORS[r["agent"]],
                alpha=0.7,
            )

    ax.set_xlabel("Inventory rows (coverage)", fontsize=9)
    ax.set_ylabel("Rows with Source 2 (corroboration)", fontsize=9)
    ax.set_xlim(left=-5)
    ax.set_ylim(bottom=-5)
    ax.tick_params(labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    handles, labels = ax.get_legend_handles_labels()
    ax.legend(
        handles,
        labels,
        fontsize=6.5,
        ncol=2,
        loc="upper left",
        frameon=False,
        handletextpad=0.3,
        columnspacing=1.0,
    )

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", dpi=150)
    plt.close(fig)
    log.info("Wrote %s (%d points)", output, len(rows))


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Coverage vs. certainty scatter for Exp2 runs",
    )
    parser.add_argument("--input", required=True, help="Path to tab_exp2_bib_quality.csv")
    parser.add_argument("--output", required=True, help="Path to write PDF figure")
    args = parser.parse_args(argv)
    rows = _load_csv(Path(args.input))
    assert len(rows) > 0, f"No data rows loaded from {args.input}"
    make_figure(rows, Path(args.output))


if __name__ == "__main__":
    main()
