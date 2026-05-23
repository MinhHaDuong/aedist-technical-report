"""Produce a flat per-run CSV for Exp2 naive vs optimised arms.

Usage:
    python -m aedist.tabulate_exp2_arms_runs --output report/inputs/generated/tab_exp2_arms_runs.csv

Reads per-run *.json metadata from both arm directories.  For the naive arm,
inventory_rows is estimated by counting markdown table rows in the paired *.md
file (same heuristic used inline by the optimised-arm harness).  For the
optimised arm it is read directly from the JSON.

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
    lines = md_path.read_text(encoding="utf-8", errors="replace").splitlines()
    table_lines = [line for line in lines if line.startswith("|") and line.endswith("|")]
    return max(0, len(table_lines) - 2)


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

        if arm_label == "naive":
            md_path = arm_dir / f"{agent}_run{run:02d}.md"
            inventory_rows = _count_md_table_rows(md_path)
            turns = 1
        else:
            inventory_rows = meta.get("inventory_rows")
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
