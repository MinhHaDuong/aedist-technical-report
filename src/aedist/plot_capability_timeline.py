"""Render the capability-rollout swimlane for §3 of the manuscript.

For each lab in Experiment 1's panel (Anthropic, OpenAI, Mistral, Alibaba,
DeepSeek), place a marker at the date the lab first shipped each of the
seven capability stages as a consumer-facing product surface. Rows are
stages (1 base instruct → 7 multi-agent); markers are coloured by lab.

The figure is descriptive: it visualises the *industry envelope* — the
outer surface of commercially attainable capability — pushing outward.
It does not claim that any lab is "ahead" or that the order is forced.

Data source: ``data/capability_timeline.csv`` (one row per (lab, stage)
cell). Cells with an empty ``date`` field render as a "TBD" annotation
at the right margin of the row, so honest gaps stay visible.

Usage:
    uv run python -m aedist.plot_capability_timeline \\
        --input data/capability_timeline.csv \\
        --output slides/inputs/generated/fig_capability_timeline.pdf
"""

import argparse
import csv
import logging
from collections import defaultdict
from datetime import date
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from .util import model_family_color

logger = logging.getLogger(__name__)

LAB_ORDER = ["Anthropic", "OpenAI", "Mistral", "Alibaba", "DeepSeek"]

# Per-lab colours from the architectural-model-family palette
# (palette.toml [model_families]). One distinct colour per lab; shapes
# are kept lab-specific for accessibility (B&W printing, colorblind
# belt-and-suspenders).
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
    2: "2. Retrieval / file upload",
    3: "3. Browsing / web search",
    4: "4. Reasoning",
    5: "5. Deep research",
    6: "6. External tool use (MCP-like)",
    7: "7. Multi-agent (recursion)",
}


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def render(rows: list[dict[str, str]], output: Path) -> None:
    by_stage: dict[int, list[tuple[str, date]]] = defaultdict(list)
    missing_by_stage: dict[int, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

    for row in rows:
        stage = int(row["stage"])
        lab = row["lab"]
        raw_date = row["date"].strip()
        if not raw_date:
            kind = row.get("source_kind", "TBD").strip() or "TBD"
            missing_by_stage[stage][kind].append(lab)
            continue
        try:
            ship_date = date.fromisoformat(raw_date)
        except ValueError:
            logger.warning("unparseable date %r for %s/%s — skipping", raw_date, lab, stage)
            continue
        by_stage[stage].append((lab, ship_date))

    fig, ax = plt.subplots(figsize=(9, 4.5))

    # One y position per stage; stage 1 at the top.
    stages_sorted = sorted(STAGE_LABELS)
    y_for_stage = {s: len(stages_sorted) - i for i, s in enumerate(stages_sorted)}

    for stage in stages_sorted:
        y = y_for_stage[stage]
        for lab, ship_date in by_stage[stage]:
            ax.scatter(
                ship_date,
                y,
                s=140,
                marker=LAB_MARKER[lab],
                color=LAB_COLOR[lab],
                edgecolor="black",
                linewidth=0.6,
                zorder=3,
            )

    # Annotate dateless cells at the right margin, labelling by source_kind
    # so confirmed absences (absent) read differently from open gaps (TBD).
    right_x = mdates.date2num(date(2025, 12, 31))
    for stage, by_kind in missing_by_stage.items():
        y = y_for_stage[stage]
        parts = []
        for kind in ("absent", "TBD"):
            labs = by_kind.get(kind, [])
            if labs:
                parts.append(f"{kind}: {', '.join(labs)}")
        if not parts:
            continue
        ax.text(
            right_x,
            y,
            "  " + " | ".join(parts),
            fontsize=7,
            va="center",
            color="gray",
            zorder=2,
        )

    ax.set_yticks([y_for_stage[s] for s in stages_sorted])
    ax.set_yticklabels([STAGE_LABELS[s] for s in stages_sorted])
    ax.set_ylim(0.5, len(stages_sorted) + 0.5)

    ax.set_xlim(date(2022, 9, 1), date(2026, 1, 1))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=[1, 7]))
    ax.tick_params(axis="x", which="minor", length=3)

    ax.grid(axis="x", which="major", linestyle=":", alpha=0.4)
    ax.grid(axis="y", which="major", linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    handles = [
        plt.Line2D(
            [],
            [],
            linestyle="",
            marker=LAB_MARKER[lab],
            markerfacecolor=LAB_COLOR[lab],
            markeredgecolor="black",
            markersize=9,
            label=lab,
        )
        for lab in LAB_ORDER
    ]
    ax.legend(
        handles=handles,
        loc="upper left",
        bbox_to_anchor=(0.01, -0.10),
        ncol=5,
        frameon=False,
        fontsize=9,
    )

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
        help="path to the capability-timeline CSV",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("slides/inputs/generated/fig_capability_timeline.pdf"),
        help="output PDF path",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    rows = load_rows(args.input)
    render(rows, args.output)


if __name__ == "__main__":
    main()
