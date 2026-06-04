"""Produce a flat per-run CSV for Exp2 naive vs optimised arms.

Pipeline phase: P2 (score & consolidate) — invoked by experiments/derived/score.mk.

Usage:
    python -m aedist.tabulate_exp2_arms_runs --output report/inputs/generated/tab_exp2_arms_runs.csv

Reads per-run *.json metadata from both arm directories. When a paired *.md
report exists, inventory_rows is derived from the best plant-table candidate in
that markdown so both arms use the same canonical meaning. The JSON field is
used only as a fallback when no markdown report is available.

Canonical data sources
    Arm 1 (naive)     experiments/outputs/sota_exp2_naive_arm/
    Arm 2 (optimised) experiments/outputs/sota_exp2_brerun1/
    sota_exp2_phase_b_full/ is excluded (weak classifier).
"""

import argparse
import csv
import json
import logging
import re
from pathlib import Path

from .extract import count_best_table_rows

log = logging.getLogger(__name__)

_DEFAULT_NAIVE_DIR = Path("experiments/outputs/sota_exp2_naive_arm")
_DEFAULT_OPTIMISED_DIR = Path("experiments/outputs/sota_exp2_brerun1")

_FIELDS = [
    "arm",
    "agent",
    "model",
    "run",
    "classification",
    "narrative_chars",
    "inventory_rows",
    "cost_usd",
    "wall_s",
    "turns",
]

_RUN_RE = re.compile(r"^([a-z]+)_run(\d+)\.json$")


def _count_md_table_rows(md_path: Path) -> int:
    if not md_path.exists():
        return 0
    text = md_path.read_text(encoding="utf-8", errors="replace")
    return count_best_table_rows(text)


def _load_arm_runs(arm_dir: Path, arm_label: str) -> list[dict]:
    rows = []
    for json_path in sorted(arm_dir.glob("*.json")):
        m = _RUN_RE.match(json_path.name)
        if not m:
            continue
        agent, run_str = m.group(1), m.group(2)
        run = int(run_str)
        meta = json.loads(json_path.read_text())

        cost = meta.get("total_cost_usd", meta.get("cost_usd", 0.0))

        md_path = arm_dir / f"{agent}_run{run:02d}.md"
        if md_path.exists():
            inventory_rows = _count_md_table_rows(md_path)
        else:
            inventory_rows = meta.get("inventory_rows", 0)

        if arm_label == "naive":
            turns = 1
        else:
            turns = meta.get("turns", 1)

        rows.append(
            {
                "arm": arm_label,
                "agent": agent,
                "model": meta.get("model", ""),
                "run": run,
                "classification": meta.get("classification", ""),
                "narrative_chars": meta.get("narrative_chars", 0),
                "inventory_rows": inventory_rows,
                "cost_usd": cost,
                "wall_s": meta.get("wall_s", 0.0),
                "turns": turns,
            }
        )
    return rows


def build_runs_csv(naive_dir: Path, optimised_dir: Path) -> list[dict]:
    rows = _load_arm_runs(naive_dir, "naive") + _load_arm_runs(optimised_dir, "optimised")
    rows.sort(key=lambda r: (r["arm"], r["agent"], r["run"]))
    return rows


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Produce flat per-run CSV for Exp2 arms")
    parser.add_argument("--output", required=True, help="Path to write tab_exp2_arms_runs.csv")
    parser.add_argument("--naive-dir", default=str(_DEFAULT_NAIVE_DIR))
    parser.add_argument("--optimised-dir", default=str(_DEFAULT_OPTIMISED_DIR))
    args = parser.parse_args(argv)

    rows = build_runs_csv(Path(args.naive_dir), Path(args.optimised_dir))

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    log.info("Wrote %d rows to %s", len(rows), out)


if __name__ == "__main__":
    main()
