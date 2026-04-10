"""Generate census bar-chart CSV from measurements.jsonl.

Writes a CSV with columns: model, f1, local
sorted by f1 descending. F1 is median across runs, as a decimal 0-1.
Local is 1 for Padme models, 0 otherwise.

Usage:
    uv run python -m aedist.plot_census \\
        --measurements measurements.jsonl \\
        --output slides/inputs/generated/census_bars.csv
"""

import argparse
import csv
import logging
from pathlib import Path

from .measurements import SYNTHETIC_SUFFIXES
from .tabulate_macros import load_and_summarize

log = logging.getLogger(__name__)


def build_census_rows(metrics: list[dict]) -> list[dict]:
    """Build sorted rows for the census bar chart (base models only).

    Filters out synthetic entries (union-vote, consolidated) so the chart
    shows single-shot baseline performance only.

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
        if not any(slug.endswith(s) for s in SYNTHETIC_SUFFIXES)
    ]
    rows.sort(key=lambda r: r["f1"], reverse=True)
    return rows


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Generate census bar-chart CSV from measurements.jsonl",
    )
    parser.add_argument("--output", required=True, help="Path to write census_bars.csv")
    args = parser.parse_args()

    output_path = Path(args.output)

    from .measurements import load_metrics

    metrics = load_metrics()

    rows = build_census_rows(metrics)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["model", "f1", "local"])
        writer.writeheader()
        writer.writerows(rows)

    log.info("Wrote %d rows to %s", len(rows), output_path)


if __name__ == "__main__":
    main()
