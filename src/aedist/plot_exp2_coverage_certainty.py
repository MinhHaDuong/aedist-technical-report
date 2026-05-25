"""Coverage vs. certainty scatter for all Exp2 runs.

Usage:
    python -m aedist.plot_exp2_coverage_certainty \
        --input report/inputs/generated/tab_exp2_bib_quality.csv \
        --output report/inputs/generated/fig_exp2_coverage_certainty.pdf
"""

import argparse
import csv
import logging
import re
from pathlib import Path

from .extract_exp2_bib import parse_md
from .util import glyph_scatter_kwargs, model_family_color

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

_ARM_GLYPH = {
    "naive": "arm1",
    "optimised": "arm2",
    "arm3": "arm3",
    "arm4": "arm4",
}


def _load_arm_pack_rows(base_dir: Path, arm: str) -> list[dict]:
    rows: list[dict] = []
    if not base_dir.exists():
        return rows

    run_re = re.compile(r"^(?P<agent>[a-z0-9]+)_run(?P<run>\d{2})\.md$")
    for md_path in sorted(base_dir.glob("*.md")):
        name = md_path.name
        if name.endswith("_bib.md"):
            continue
        m = run_re.match(name)
        if not m:
            continue
        agent = m.group("agent")
        if agent not in _AGENT_SLUG:
            continue
        summary = parse_md(md_path)
        rows.append(
            {
                "agent": agent,
                "arm": arm,
                "run": int(m.group("run")),
                "n_rows": int(summary.get("n_rows") or 0),
                "src2_present": int(summary.get("src2_present") or 0),
            }
        )
    return rows


def _load_csv(path: Path) -> list[dict]:
    rows = []
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            n_rows = int(row["n_rows"])
            rows.append(
                {
                    "agent": row["agent"],
                    "arm": row["arm"],
                    "run": int(row["run"]),
                    "n_rows": n_rows,
                    "src2_present": int(row["src2_present"]),
                }
            )

    # Add arm3/arm4 datapack runs so the scatter covers all 4 arms x 4 agents x 5 reps.
    root = path.parents[3]
    rows.extend(_load_arm_pack_rows(root / "experiments/derived/arm3_flat", "arm3"))
    rows.extend(_load_arm_pack_rows(root / "experiments/derived/arm4_flat", "arm4"))
    return rows


def make_figure(rows: list[dict], output: Path) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    fig, ax = plt.subplots(figsize=(5.5, 4.0))

    rows = [r for r in rows if r["n_rows"] > 0]

    for agent, color in _AGENT_COLORS.items():
        for arm in ("naive", "optimised", "arm3", "arm4"):
            subset = [r for r in rows if r["agent"] == agent and r["arm"] == arm]
            if not subset:
                continue
            xs = [r["n_rows"] for r in subset]
            ys = [r["src2_present"] for r in subset]

            if arm in _ARM_GLYPH:
                ax.scatter(
                    xs,
                    ys,
                    **glyph_scatter_kwargs(_ARM_GLYPH[arm], color),
                    zorder=3,
                )

    if rows:
        max_val = max(max(r["n_rows"], r["src2_present"]) for r in rows)
        ax.plot([0, max_val], [0, max_val], color="0.75", linewidth=0.8, zorder=1, linestyle="--")

    ax.set_xlabel("Assets correctly identified (coverage)", fontsize=9)
    ax.set_ylabel("Assets from two sources (corroboration)", fontsize=9)
    ax.set_title(
        "Coverage vs. Corroboration (out of 163 assets)",
        fontsize=11,
        fontweight="bold",
        pad=8,
    )
    ax.set_xlim(left=-5)
    ax.set_ylim(bottom=-5)
    ax.tick_params(labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Legend 1: model colour mapping.
    model_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="",
            markerfacecolor=color,
            markeredgecolor=color,
            markersize=6,
            label=_AGENT_LABELS[agent],
        )
        for agent, color in _AGENT_COLORS.items()
    ]
    model_legend = ax.legend(
        model_handles,
        [h.get_label() for h in model_handles],
        title="Model color",
        fontsize=6.5,
        title_fontsize=7,
        loc="upper left",
        frameon=False,
    )
    ax.add_artist(model_legend)

    # Legend 2: glyph style mapping.
    glyph_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="",
            markerfacecolor="none",
            markeredgecolor="black",
            markersize=6,
            label="arm1 (single-shot)",
        ),
        Line2D(
            [0],
            [0],
            marker="D",
            linestyle="",
            markerfacecolor="none",
            markeredgecolor="black",
            markersize=6,
            label="arm2 (multi-turn)",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="",
            markerfacecolor="black",
            markeredgecolor="black",
            markersize=6,
            label="arm3 (+sources, single-shot)",
        ),
        Line2D(
            [0],
            [0],
            marker="D",
            linestyle="",
            markerfacecolor="black",
            markeredgecolor="black",
            markersize=6,
            label="arm4 (+sources, multi-turn)",
        ),
    ]
    ax.legend(
        glyph_handles,
        [h.get_label() for h in glyph_handles],
        title="Glyph style",
        fontsize=6.5,
        title_fontsize=7,
        loc="lower right",
        frameon=False,
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
