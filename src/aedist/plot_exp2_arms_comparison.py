"""Four-panel coverage comparison figure for Exp2 2x2 arm design.

Usage:
    python -m aedist.plot_exp2_arms_comparison \
        --input report/inputs/generated/tab_exp2_arms_runs.csv \
        --output report/inputs/generated/fig_exp2_arms_comparison.pdf

Panels (2x2): one panel per arm.
    (a) arm1 — web, single-shot
    (b) arm2 — web, multi-turn
    (c) arm3 — web + evidence pack, single-shot
    (d) arm4 — web + evidence pack, multi-turn

Each panel: four agent groups on the x-axis, y-axis is enumerated plants
(coverage). Individual run points are jittered; a thick horizontal bar marks
the median report value. Runs classified no_report are rendered as x markers
at y=0.
"""

import argparse
import csv
import json
import logging
import random
from pathlib import Path

from .extract import count_best_table_rows
from .util import COLOR_REFERENCE, model_family_color

log = logging.getLogger(__name__)

N_REFERENCE_PLANTS = 163

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

_ARM_STYLE = {
    "arm1": {"marker": "o", "filled": False, "label": "(a) arm1 — web, single-shot"},
    "arm2": {"marker": "D", "filled": False, "label": "(b) arm2 — web, multi-turn"},
    "arm3": {"marker": "o", "filled": True, "label": "(c) arm3 — +pack, single-shot"},
    "arm4": {"marker": "D", "filled": True, "label": "(d) arm4 — +pack, multi-turn"},
}


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


def _draw_panel(ax, rows: list[dict], arm: str, title: str) -> None:
    import numpy as np

    rng = random.Random(42)
    style = _ARM_STYLE[arm]

    for agent_idx, agent in enumerate(_AGENT_ORDER):
        subset = [r for r in rows if r["agent"] == agent and r["arm"] == arm]
        if not subset:
            continue

        color = model_family_color(subset[0].get("model", _AGENT_MODEL[agent]))
        x_center = agent_idx
        xs = [x_center + rng.uniform(-0.06, 0.06) for _ in subset]

        report_xs = [x for x, r in zip(xs, subset, strict=True) if r["is_report"]]
        report_ys = [r["inventory_rows"] for r in subset if r["is_report"]]
        noreport_xs = [x for x, r in zip(xs, subset, strict=True) if not r["is_report"]]

        if report_xs:
            face = color if style["filled"] else "none"
            ax.scatter(
                report_xs,
                report_ys,
                marker=style["marker"],
                s=26,
                facecolors=face,
                edgecolors=color,
                linewidths=1.1,
                zorder=3,
            )
        if noreport_xs:
            ax.scatter(
                noreport_xs,
                [0] * len(noreport_xs),
                color=color,
                s=24,
                zorder=3,
                marker="x",
                linewidths=1.2,
            )

        if report_ys:
            med = float(np.median(report_ys))
            ax.hlines(
                med,
                x_center - 0.10,
                x_center + 0.10,
                colors=color,
                linewidths=2.0,
                zorder=4,
            )

    ax.set_title(title, fontsize=8, loc="left")
    ax.set_xticks(range(len(_AGENT_ORDER)))
    ax.set_xticklabels([_AGENT_LABELS[a] for a in _AGENT_ORDER], fontsize=7.5)
    ax.set_xlim(-0.5, len(_AGENT_ORDER) - 0.5)
    ax.tick_params(axis="y", labelsize=7.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.axhline(N_REFERENCE_PLANTS, color=COLOR_REFERENCE, linestyle="--", linewidth=1.0, zorder=1)
    ax.set_ylim(0, 180)


def make_figure(rows: list[dict], output: Path) -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(9.2, 5.8), sharey=True)
    arm_order = ["arm1", "arm2", "arm3", "arm4"]
    for ax, arm in zip(axes.flatten(), arm_order, strict=True):
        _draw_panel(ax, rows, arm, _ARM_STYLE[arm]["label"])
        if arm in ("arm1", "arm3"):
            ax.set_ylabel("Plants enumerated", fontsize=8)

    fig.suptitle("Experiment 2 — 4-arm coverage comparison (N=5 per agent)", fontsize=9, y=1.01)
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", dpi=150)
    plt.close(fig)
    log.info("Wrote %s", output)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="4-arm Exp2 coverage comparison figure")
    parser.add_argument("--input", required=True, help="Path to tab_exp2_arms_runs.csv")
    parser.add_argument("--output", required=True, help="Path to write PDF figure")
    args = parser.parse_args(argv)
    make_figure(_load_csv(Path(args.input)), Path(args.output))


if __name__ == "__main__":
    main()
