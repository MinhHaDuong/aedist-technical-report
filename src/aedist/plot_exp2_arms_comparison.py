"""Single-panel comparison figures: Exp1 memory-only baseline plus Exp2 four arms.

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.

Usage:
    python -m aedist.plot_exp2_arms_comparison \
        --input report/inputs/generated/tab_exp2_arms_runs.csv \
        --panel coverage \
        --output report/inputs/generated/fig_exp2_arms_coverage.pdf

The figure was split (ticket 0583) into two single-panel artifacts:
    --panel coverage : plants enumerated (matched vs false-positive bars)
    --panel cost     : USD per run

Each panel groups by agent on the x-axis. Within each group, the hatched E1 bar
shows the Exp1 memory-only baseline, followed by the four Exp2 arms (1N/5N/1D/5D)
with project glyphs and per-model colours. Runs classified no_report are rendered
as x markers at y=0.
"""

import argparse
import csv
import json
import logging
from pathlib import Path

from matplotlib.figure import Figure

from .evaluate import reference_plant_count
from .exp1_cost_quality import load_cost_quality_rows, summary_by_slug
from .extract import count_best_table_rows
from .util import (
    COLOR_ALERT,
    COLOR_REFERENCE,
    SLIDE_FIGSIZE_FULL,
    model_family_color,
)

_CONDITION_LEGEND = (
    "E1 = Memory only (Exp 1)  ·  1N = Singleshot, no doc  ·  "
    "5N = Multiturn, no doc  ·  1D = Singleshot, docs  ·  5D = Multiturn, docs"
)

log = logging.getLogger(__name__)


def load_exp1_summary() -> dict[str, dict]:
    """Return {exp1_slug: {median_tp, ..., mean_cost, ...}}.

    Derived from the mart via the shared :mod:`aedist.exp1_cost_quality`
    library — common cause, not read from another figure script's CSV
    side-output (ticket 0436).
    """
    return summary_by_slug(load_cost_quality_rows())

# Reference inventory size — derived from the adopted release (ticket 0413,
# single source of truth). Used at the axhline reference line below.
N_REFERENCE_PLANTS = reference_plant_count()

_AGENT_LABELS = {
    "anthropic": "Anthropic\nOpus 4.6",
    "mistral": "Mistral\nLarge 2512",
    "openai": "OpenAI\nGPT-5.5",
    "qwen": "Qwen3\nMax",
}
_AGENT_ORDER = ["anthropic", "mistral", "openai", "qwen"]

_AGENT_MODEL = {
    "anthropic": "claude-opus-4-6",
    "mistral": "mistral-large-2512",
    "openai": "gpt-5.5",
    "qwen": "qwen3.7-max-2026-05-20",
}

# Exp1 slugs in cost_quality.csv for each agent — these differ from
# _AGENT_MODEL (dot vs dash, no date suffix). Copied from the split script
# so the E1 lookup hits the correct summary key.
_AGENT_EXP1_SLUG = {
    "anthropic": "claude-opus-4.6",
    "mistral": "mistral-large-2512",
    "openai": "gpt-5.5",
    "qwen": "qwen3.7-max",
}

# Five display slots per model group: E1 baseline + four Exp2 arms.
#   E1 = Experiment 1 parametric baseline (memory only)
#   1N = single-shot, no docs  (arm1 / naive)
#   5N = multi-turn,  no docs   (arm2 / optimised)
#   1D = single-shot, docs      (arm3)
#   5D = multi-turn,  docs      (arm4)
_CONDITIONS = ["arm1", "arm2", "arm3", "arm4"]
_CONDITION_LABEL = {"arm1": "1N", "arm2": "5N", "arm3": "1D", "arm4": "5D"}
# 5-bar layout: E1 + arm1..arm4, symmetric around the model centre.
_BAR_WIDTH = 0.14
_ALL_KEYS = ["e1", "arm1", "arm2", "arm3", "arm4"]
_CONDITION_OFFSET = {"e1": -0.36, "arm1": -0.18, "arm2": 0.00, "arm3": +0.18, "arm4": +0.36}


def _canonical_arm(raw: str) -> str:
    if raw == "naive":
        return "arm1"
    if raw == "optimised":
        return "arm2"
    return raw


def _inventory_rows_from_flat(json_path: Path) -> int:
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    for key in ("inventory_rows", "n_rows"):
        val = payload.get(key)
        if isinstance(val, int):
            return val
    md_path = json_path.with_suffix(".md")
    if md_path.exists():
        return count_best_table_rows(md_path.read_text(encoding="utf-8"))
    return 0


def _load_pack_arm_rows(base_dir: Path, arm: str) -> list[dict]:
    if not base_dir.exists():
        return []
    rows: list[dict] = []
    for json_path in sorted(base_dir.glob("*.json")):
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        agent = str(payload.get("agent") or "").strip()
        if agent not in _AGENT_ORDER:
            continue
        model = str(payload.get("model") or _AGENT_MODEL[agent])
        run = int(payload.get("run") or 0)
        classification = str(payload.get("classification") or "report")
        rows.append(
            {
                "arm": arm,
                "agent": agent,
                "model": model,
                "run": run,
                "classification": classification,
                "inventory_rows": _inventory_rows_from_flat(json_path),
                # arm3/arm4 are unscored (no cross-eval coverage) -> no matched count.
                "n_matched": None,
                "cost_usd": float(payload.get("total_cost_usd", payload.get("cost_usd")) or 0.0),
                "is_report": classification == "report",
            }
        )
    return rows


def _load_csv(path: Path) -> list[dict]:
    rows = []
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            row["run"] = int(row["run"])
            raw_rows = row["inventory_rows"]
            row["inventory_rows"] = int(raw_rows) if raw_rows not in ("", "None") else 0
            raw_matched = row.get("n_matched", "")
            row["n_matched"] = int(raw_matched) if raw_matched not in ("", "None") else None
            row["cost_usd"] = float(row.get("cost_usd") or 0.0)
            row["arm"] = _canonical_arm(row["arm"])
            row["is_report"] = row["classification"] == "report"
            rows.append(row)

    present_arms = {r["arm"] for r in rows}
    root = path.parents[3]
    if "arm3" not in present_arms:
        rows.extend(_load_pack_arm_rows(root / "experiments/derived/arm3_flat", "arm3"))
    if "arm4" not in present_arms:
        rows.extend(_load_pack_arm_rows(root / "experiments/derived/arm4_flat", "arm4"))
    return rows


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _draw_whiskers(ax, x_center: float, values: list[float]) -> None:
    """Thin black vertical line spanning the run range + one short horizontal
    segment per run, to show inter-run dispersion (ticket 0332)."""
    if not values:
        return
    seg = _BAR_WIDTH * 0.6
    ax.vlines(x_center, min(values), max(values), color="black", linewidth=0.7, zorder=5)
    ax.hlines(
        values,
        x_center - seg / 2,
        x_center + seg / 2,
        color="black",
        linewidth=0.8,
        zorder=5,
    )


def _wiki_coverage() -> tuple[int, int]:
    """Wikipedia reviewed coverage of the reference (count, pct) from the 0486 artifact.

    Reads the committed concordance CSV so the Exp2 Wikipedia coverage line tracks
    the same number as the manuscript's \\WikiReviewed macro (single source of truth).
    """
    from aedist.config import SOURCE_CONCORDANCE_CSV

    with open(SOURCE_CONCORDANCE_CSV, newline="", encoding="utf-8") as fh:
        total = next(r for r in csv.DictReader(fh) if r["status"] == "All")
    count = int(total["wiki_matched"])
    return count, round(count / int(total["n_reference"]) * 100)


def _draw_coverage_panel(ax, rows: list[dict], exp1_summary: dict[str, dict]) -> None:
    """Diverging bars: matched assets (model colour, above 0), hallucinations /
    false positives (red, below 0). E1 baseline bars are hatched. 1D/5D (no
    scoring) render as gray bars."""
    for agent_idx, agent in enumerate(_AGENT_ORDER):
        color = model_family_color(_AGENT_MODEL[agent])

        # E1 bar (Exp1 memory-only baseline, hatched)
        exp1_slug = _AGENT_EXP1_SLUG[agent]
        if exp1_slug in exp1_summary:
            e1 = exp1_summary[exp1_slug]
            x = agent_idx + _CONDITION_OFFSET["e1"]
            ax.bar(x, e1["median_tp"], _BAR_WIDTH, color=color, alpha=0.55, hatch="//", zorder=3)
            if e1["median_fp"] > 0:
                ax.bar(
                    x,
                    -e1["median_fp"],
                    _BAR_WIDTH,
                    color=COLOR_ALERT,
                    alpha=0.7,
                    hatch="//",
                    zorder=3,
                )
            _draw_whiskers(ax, x, [e1["min_tp"], e1["max_tp"]])

        # Exp2 arms
        for cond in _CONDITIONS:
            subset = [
                r for r in rows if r["agent"] == agent and r["arm"] == cond and r["is_report"]
            ]
            if not subset:
                continue
            x = agent_idx + _CONDITION_OFFSET[cond]

            scored = [r for r in subset if r["n_matched"] is not None]
            if scored:
                matched_vals = [r["n_matched"] for r in scored]
                halluc_vals = [max(0, r["inventory_rows"] - r["n_matched"]) for r in scored]
                mean_matched = _mean(matched_vals)
                mean_halluc = _mean(halluc_vals)
                ax.bar(x, mean_matched, _BAR_WIDTH, color=color, alpha=0.85, zorder=3)
                if mean_halluc > 0:
                    ax.bar(x, -mean_halluc, _BAR_WIDTH, color=COLOR_ALERT, alpha=0.9, zorder=3)
                _draw_whiskers(ax, x, matched_vals)
            else:
                # 1D/5D or all-None scored runs: show inventory size, unscored gray.
                inv_vals = [r["inventory_rows"] for r in subset if r["inventory_rows"] > 0]
                ax.bar(x, _mean(inv_vals), _BAR_WIDTH, color="0.70", alpha=0.85, zorder=3)
                _draw_whiskers(ax, x, inv_vals)

    ax.axhline(0, color=COLOR_REFERENCE, linewidth=1.4, zorder=2)
    ax.axhline(N_REFERENCE_PLANTS, color=COLOR_REFERENCE, linestyle="--", linewidth=1.0, zorder=1)
    # Wikipedia coverage bar (ticket 0622): light-grey dotted line at Wikipedia's
    # reviewed coverage of the reference (\\WikiReviewed, single source of truth).
    _wiki_n, _wiki_pct = _wiki_coverage()
    ax.axhline(_wiki_n, color="0.6", linestyle=":", linewidth=1.0, zorder=1)
    ax.text(
        len(_AGENT_ORDER) - 0.5, _wiki_n, f"Wikipedia {_wiki_pct}%", ha="right", va="bottom", fontsize=8, color="0.45"
    )
    ax.yaxis.set_major_formatter(lambda val, pos: str(abs(int(val))))
    # Top of the axis tracks the reference size so the dashed line stays visible.
    ax.set_ylim(-50, N_REFERENCE_PLANTS + 15)
    ax.set_yticks([-50, 0, 50, 100, 150])
    # Reference-line label, horizontal, on the dashed line.
    ax.text(
        -0.5,
        N_REFERENCE_PLANTS,
        f"{N_REFERENCE_PLANTS} plants",
        ha="left",
        va="bottom",
        fontsize=8,
        fontweight="bold",
    )
    _style_panel(
        ax,
        "Number of assets identified (hatched = Exp 1 baseline; red = False Positives)",
    )


def _draw_cost_panel(ax, rows: list[dict], exp1_summary: dict[str, dict]) -> None:
    """Mean API cost per run, 5 bars per model (E1 + 4 arms) with inter-run whiskers."""
    for agent_idx, agent in enumerate(_AGENT_ORDER):
        color = model_family_color(_AGENT_MODEL[agent])

        # E1 bar (Exp1 memory-only baseline, hatched)
        exp1_slug = _AGENT_EXP1_SLUG[agent]
        if exp1_slug in exp1_summary:
            x = agent_idx + _CONDITION_OFFSET["e1"]
            e1 = exp1_summary[exp1_slug]
            mean_cost = e1["mean_cost"]
            ax.bar(x, mean_cost, _BAR_WIDTH, color=color, alpha=0.55, hatch="//", zorder=3)
            _draw_whiskers(ax, x, [e1["min_cost"], e1["max_cost"]])

        # Exp2 arms
        for cond in _CONDITIONS:
            subset = [
                r for r in rows if r["agent"] == agent and r["arm"] == cond and r["is_report"]
            ]
            if not subset:
                continue
            x = agent_idx + _CONDITION_OFFSET[cond]
            cost_vals = [r["cost_usd"] for r in subset]
            ax.bar(x, _mean(cost_vals), _BAR_WIDTH, color=color, alpha=0.85, zorder=3)
            _draw_whiskers(ax, x, cost_vals)

    ax.set_ylim(bottom=0)
    ax.set_title(
        "API cost per run, USD (hatched = Exp 1 baseline)",
        fontsize=9,
        fontweight="bold",
        pad=6,
    )
    _style_panel(ax, None)


def _annotate_conditions(ax) -> None:
    """Small E1/1N/5N/1D/5D labels just below each bar, inside the axes."""
    y0 = ax.get_ylim()[0]
    span = ax.get_ylim()[1] - y0
    for agent_idx in range(len(_AGENT_ORDER)):
        for key in _ALL_KEYS:
            label = "E1" if key == "e1" else _CONDITION_LABEL[key]
            ax.text(
                agent_idx + _CONDITION_OFFSET[key],
                y0 + span * 0.015,
                label,
                ha="center",
                va="bottom",
                fontsize=6.0,
                color="0.30",
                zorder=6,
            )


def _style_panel(ax, ylabel: str | None) -> None:
    ax.set_xticks(range(len(_AGENT_ORDER)))
    ax.set_xticklabels([_AGENT_LABELS[a] for a in _AGENT_ORDER], fontsize=7.5)
    ax.set_xlim(-0.65, len(_AGENT_ORDER) - 0.35)
    if ylabel:
        ax.set_title(ylabel, fontsize=9, fontweight="bold", pad=6)
    ax.tick_params(axis="y", labelsize=7.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    _annotate_conditions(ax)


_PANEL_TITLE = {
    "coverage": "Coverage, experiment 2",
    "cost": "Costs, experiment 2",
}


def make_figure(
    rows: list[dict],
    output: Path,
    panel: str,
    exp1_summary: dict[str, dict] | None = None,
) -> Figure:
    import matplotlib.pyplot as plt

    if panel not in _PANEL_TITLE:
        raise ValueError(f"unknown panel {panel!r}; expected one of {sorted(_PANEL_TITLE)}")

    if exp1_summary is None:
        exp1_summary = load_exp1_summary()

    fig, ax = plt.subplots(1, 1, figsize=SLIDE_FIGSIZE_FULL)
    no_report_rows = [r for r in rows if not r["is_report"]]
    if no_report_rows:
        sample = ", ".join(f"{r['arm']}/{r['agent']}/run{r['run']}" for r in no_report_rows[:6])
        log.warning(
            "plot_exp2_arms_comparison: excluding %d no_report rows (pipeline bugs): %s",
            len(no_report_rows),
            sample,
        )
    rows = [r for r in rows if r["is_report"]]

    if panel == "coverage":
        _draw_coverage_panel(ax, rows, exp1_summary)
    else:
        _draw_cost_panel(ax, rows, exp1_summary)

    fig.suptitle(_PANEL_TITLE[panel], fontsize=13, fontweight="bold", y=0.99)
    fig.text(0.5, 0.93, _CONDITION_LEGEND, ha="center", va="top", fontsize=8.5)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.90))
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", dpi=150)
    plt.close(fig)
    log.info("Wrote %s", output)
    return fig


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Single-panel Exp2 4-arm comparison figure")
    parser.add_argument("--input", required=True, help="Path to tab_exp2_arms_runs.csv")
    parser.add_argument(
        "--panel",
        required=True,
        choices=sorted(_PANEL_TITLE),
        help="Which panel to render (coverage or cost)",
    )
    parser.add_argument("--output", required=True, help="Path to write PDF figure")
    args = parser.parse_args(argv)
    make_figure(_load_csv(Path(args.input)), Path(args.output), panel=args.panel)


if __name__ == "__main__":
    main()
