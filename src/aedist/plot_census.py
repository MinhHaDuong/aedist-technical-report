"""Generate census bar-chart CSV from all_metrics.json.

Writes a CSV with columns: model, f1, local
sorted by f1 descending. F1 is median across runs, as a decimal 0-1.
Local is 1 for Padme models, 0 otherwise.

Usage:
    uv run python -m aedist.plot_census \\
        --input results/summary/all_metrics.json \\
        --output slides/inputs/generated/census_bars.csv
"""

import argparse
import csv
import json
import logging
from pathlib import Path

from .tabulate_macros import _slug_from_label, load_and_summarize

log = logging.getLogger(__name__)


def build_census_rows(metrics: list[dict]) -> list[dict]:
    """Build sorted rows for the census bar chart.

    Returns list of dicts with keys: model, f1, local.
    Sorted by f1 descending.
    """
    summary = load_and_summarize(metrics)
    rows = [
        {
            "model": slug,
            "f1": info["median_f1"],
            "local": 1 if info["is_local"] else 0,
        }
        for slug, info in summary.items()
    ]
    rows.sort(key=lambda r: r["f1"], reverse=True)
    return rows


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Generate census bar-chart CSV from metrics JSON",
    )
    parser.add_argument("--input", required=True, help="Path to all_metrics.json")
    parser.add_argument("--output", required=True, help="Path to write census_bars.csv")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    with open(input_path) as f:
        metrics = json.load(f)

    rows = build_census_rows(metrics)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["model", "f1", "local"])
        writer.writeheader()
        writer.writerows(rows)

    log.info("Wrote %d rows to %s", len(rows), output_path)


if __name__ == "__main__":
    main()
