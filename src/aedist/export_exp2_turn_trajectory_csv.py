"""Export the legacy Exp2 turn-trajectory CSV from raw probe artifacts.

Pipeline phase: P2 (score & consolidate) — invoked by experiments/derived/score.mk.
"""

import argparse
import csv
import logging
from pathlib import Path

from .plot_exp2_turn_trajectory import load_run_turns

log = logging.getLogger(__name__)

_FIELDS = ["agent", "arm", "run", "turn", "rows", "cls"]
_AGENTS = ["anthropic", "mistral", "openai", "qwen"]


def build_turn_trajectory_csv(probes_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for agent in _AGENTS:
        for run in range(1, 6):
            rows.extend(
                [
                    {
                        "agent": agent,
                        "arm": "optimised",
                        "run": run,
                        "turn": turn["turn"],
                        "rows": turn["rows"],
                        "cls": turn["cls"],
                    }
                    for turn in load_run_turns(probes_dir, agent, run)
                ]
            )
    rows.sort(key=lambda row: (row["agent"], row["run"], row["turn"]))
    return rows


def write_turn_trajectory_csv(probes_dir: Path, output: Path) -> list[dict]:
    rows = build_turn_trajectory_csv(probes_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Export the legacy Exp2 turn trajectory CSV")
    parser.add_argument("--probes-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    rows = write_turn_trajectory_csv(Path(args.probes_dir), Path(args.output))
    log.info("Wrote %d rows to %s", len(rows), args.output)


if __name__ == "__main__":
    main()
