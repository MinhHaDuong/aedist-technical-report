"""Write the Experiment 1 cost × quality audit CSV from measurements.jsonl.

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.

This is the table/view half of the Exp1 cost × quality artifact pair: it emits
the per-model summary CSV (``cost_quality.csv``) that backs the scatter figure
for audit. The figure itself is drawn by :mod:`aedist.plot_cost_quality`. Both
derive their rows from the shared :mod:`aedist.exp1_cost_quality` library — no
figure-script side-output that another rule consumes (ticket 0436).

Usage::

    uv run python -m aedist.tabulate_cost_quality \\
        --output report/inputs/generated/cost_quality.csv
"""

import argparse
import csv
import logging
from pathlib import Path

from .exp1_cost_quality import CSV_FIELDNAMES, load_cost_quality_rows

log = logging.getLogger(__name__)


def write_csv(rows: list[dict], output: Path) -> None:
    """Write the cost × quality summary rows to *output* (audit CSV)."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    log.info("Wrote %d rows to %s", len(rows), output)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Write the Experiment 1 cost × quality audit CSV",
    )
    parser.add_argument("--output", required=True, help="Path to write cost_quality.csv")
    args = parser.parse_args()

    rows = load_cost_quality_rows()
    write_csv(rows, Path(args.output))


if __name__ == "__main__":
    main()
