"""Generate Pareto-front CSV from all_metrics.json.

Writes a CSV with columns: model, f1, cost_usd, local
sorted by f1 descending.

Usage:
    uv run python -m aedist.plot_pareto \\
        --input results/summary/all_metrics.json \\
        --costs results/summary/sweep1_summary.csv \\
        --output slides/inputs/generated/pareto.csv
"""

import argparse
import csv
import json
import logging
from pathlib import Path

from .tabulate_macros import load_and_summarize

log = logging.getLogger(__name__)


def load_costs(csv_path: Path) -> dict[str, float]:
    """Load per-run cost from sweep summary CSV.

    Returns {model_slug: cost_per_run} where cost_per_run = total_cost / n_runs.
    """
    costs: dict[str, float] = {}
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            n_runs = int(row["n_runs"])
            total = float(row["total_cost_usd"])
            costs[row["model"]] = total / n_runs if n_runs > 0 else 0.0
    return costs


def build_pareto_rows(
    metrics: list[dict],
    costs: dict[str, float] | None = None,
) -> list[dict]:
    """Build rows for the Pareto chart.

    Returns list of dicts with keys: model, f1, cost_usd, local.
    Sorted by f1 descending.
    """
    if costs is None:
        costs = {}
    summary = load_and_summarize(metrics)
    rows = [
        {
            "model": slug,
            "f1": info["median_f1"],
            "cost_usd": round(costs.get(slug, 0.0), 6),
            "local": 1 if info["is_local"] else 0,
        }
        for slug, info in summary.items()
    ]
    rows.sort(key=lambda r: r["f1"], reverse=True)
    return rows


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Generate Pareto-front CSV from metrics JSON",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", help="Path to all_metrics.json (legacy)")
    source.add_argument("--measurements", help="Path to measurements.jsonl")
    parser.add_argument("--costs", default=None, help="Path to sweep summary CSV with cost data")
    parser.add_argument("--output", required=True, help="Path to write pareto.csv")
    args = parser.parse_args()

    output_path = Path(args.output)

    if args.measurements:
        from .measurements_adapter import load_metrics_from_measurements

        metrics = load_metrics_from_measurements(args.measurements)
        # When loading from measurements, cost is already in the records
        # so --costs CSV is not needed (but still supported for override)
    else:
        with open(args.input) as f:
            metrics = json.load(f)

    costs = None
    if args.costs:
        costs = load_costs(Path(args.costs))
        log.info("Loaded costs for %d models from %s", len(costs), args.costs)

    rows = build_pareto_rows(metrics, costs)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["model", "f1", "cost_usd", "local"])
        writer.writeheader()
        writer.writerows(rows)

    log.info("Wrote %d rows to %s", len(rows), output_path)


if __name__ == "__main__":
    main()
