"""Summarize sweep results: aggregate 3 runs per model into median metrics.

Reads the per-run metrics from measurements.jsonl, computes cost/latency,
and produces a summary CSV.

Usage:
    uv run python -m aedist.summarize_sweep \
        --measurements measurements.jsonl \
        --output results/summary/sweep1_summary.csv
"""

import argparse
import csv
import logging
from pathlib import Path
from statistics import median

from .measurements_adapter import load_metrics_from_measurements
from .tabulate_macros import slug_from_label

log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Summarize sweep metrics")
    parser.add_argument("--measurements", required=True, help="Path to measurements.jsonl")
    parser.add_argument("--output", required=True, help="Output summary CSV path")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    metrics = load_metrics_from_measurements(args.measurements)

    # Group by model and collect cost/latency in a single pass
    by_model: dict[str, list[dict]] = {}
    cost_latency: dict[str, list[tuple[float, float]]] = {}
    for entry in metrics:
        model_short = slug_from_label(entry["label"])
        by_model.setdefault(model_short, []).append(entry)
        cost = entry.get("cost_usd", 0.0) or 0.0
        wall = entry.get("wall_seconds", 0.0) or 0.0
        cost_latency.setdefault(model_short, []).append((cost, wall))

    # Write summary
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for model_short, entries in sorted(by_model.items()):
        n_runs = len(entries)
        f1s = [e["f1"] for e in entries]
        coverages = [e["coverage"] for e in entries]
        precisions = [e["precision"] for e in entries]
        fuel_accs = [e.get("fuel_accuracy", 0) for e in entries]
        n_plants = [e.get("n_system", 0) for e in entries]

        cl = cost_latency.get(model_short, [])
        costs = [c for c, _ in cl] if cl else [0.0]
        latencies = [w for _, w in cl] if cl else [0.0]

        rows.append(
            {
                "model": model_short,
                "n_runs": n_runs,
                "median_f1": round(median(f1s), 4) if f1s else 0.0,
                "median_coverage": round(median(coverages), 4) if coverages else 0.0,
                "median_precision": round(median(precisions), 4) if precisions else 0.0,
                "median_fuel_accuracy": round(median(fuel_accs), 4) if fuel_accs else 0.0,
                "median_n_plants": round(median(n_plants)) if n_plants else 0,
                "total_cost_usd": round(sum(costs), 6),
                "median_latency_s": round(median(latencies), 1) if latencies else 0.0,
            }
        )

    # Sort by median F1 descending
    rows.sort(key=lambda r: r["median_f1"], reverse=True)

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys() if rows else [])
        writer.writeheader()
        writer.writerows(rows)

    log.info("Wrote %d model summaries to %s", len(rows), out_path)

    # Also print to console
    print(
        f"\n{'Model':<35s} {'Runs':>4s} {'F1':>6s} {'Cov':>6s} {'Prec':>6s} {'Cost':>8s} {'Lat(s)':>7s}"
    )
    print("-" * 75)
    for r in rows:
        print(
            f"{r['model']:<35s} {r['n_runs']:>4d} {r['median_f1']:>6.1%} {r['median_coverage']:>6.1%} "
            f"{r['median_precision']:>6.1%} ${r['total_cost_usd']:>7.4f} {r['median_latency_s']:>6.1f}"
        )


if __name__ == "__main__":
    main()
