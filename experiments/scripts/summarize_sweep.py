"""Summarize sweep results: aggregate 3 runs per model into median metrics.

Reads the per-run metrics from evaluate-all output and the JSON query records
to compute cost/latency, then produces a summary CSV.

Usage:
    uv run python scripts/summarize_sweep.py \
        --metrics results/sweep1_census/all_metrics.json \
        --queries outputs/sweep1_census/ \
        --output results/sweep1_census/summary.csv
"""

import argparse
import csv
import json
import logging
import re
from pathlib import Path
from statistics import median

log = logging.getLogger(__name__)


def _parse_label(label: str) -> tuple[str, int]:
    """Extract model short name and run number from label like '2026-04-01/deepseek-v3.2-run2'."""
    stem = label.split("/")[-1] if "/" in label else label
    m = re.match(r"(.+)-run(\d+)$", stem)
    if m:
        return m.group(1), int(m.group(2))
    return stem, 1


def main():
    parser = argparse.ArgumentParser(description="Summarize sweep metrics")
    parser.add_argument("--metrics", required=True, help="Path to all_metrics.json")
    parser.add_argument("--queries", required=True, help="Query output dir (for cost/latency)")
    parser.add_argument("--output", required=True, help="Output summary CSV path")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Load evaluation metrics
    with open(args.metrics) as f:
        all_metrics = json.load(f)

    # Group by model
    by_model: dict[str, list[dict]] = {}
    for entry in all_metrics:
        model_short, run = _parse_label(entry["label"])
        by_model.setdefault(model_short, []).append(entry)

    # Load cost/latency from JSON query records
    query_dir = Path(args.queries)
    cost_latency: dict[str, list[tuple[float, float]]] = {}
    for jf in sorted(query_dir.rglob("*.json")):
        try:
            record = json.loads(jf.read_text())
        except Exception:
            continue
        model_id = record.get("model", "")
        short = model_id.split("/")[-1] if "/" in model_id else model_id
        # Remove :free suffix for matching
        base_short = re.sub(r"-run\d+$", "", jf.stem)
        cost = record.get("cost_usd", 0.0) or 0.0
        wall = record.get("wall_seconds", 0.0) or 0.0
        cost_latency.setdefault(base_short, []).append((cost, wall))

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

        rows.append({
            "model": model_short,
            "n_runs": n_runs,
            "median_f1": round(median(f1s), 4),
            "median_coverage": round(median(coverages), 4),
            "median_precision": round(median(precisions), 4),
            "median_fuel_accuracy": round(median(fuel_accs), 4),
            "median_n_plants": round(median(n_plants)),
            "total_cost_usd": round(sum(costs), 6),
            "median_latency_s": round(median(latencies), 1),
        })

    # Sort by median F1 descending
    rows.sort(key=lambda r: r["median_f1"], reverse=True)

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys() if rows else [])
        writer.writeheader()
        writer.writerows(rows)

    log.info("Wrote %d model summaries to %s", len(rows), out_path)

    # Also print to console
    print(f"\n{'Model':<35s} {'Runs':>4s} {'F1':>6s} {'Cov':>6s} {'Prec':>6s} {'Cost':>8s} {'Lat(s)':>7s}")
    print("-" * 75)
    for r in rows:
        print(f"{r['model']:<35s} {r['n_runs']:>4d} {r['median_f1']:>6.1%} {r['median_coverage']:>6.1%} "
              f"{r['median_precision']:>6.1%} ${r['total_cost_usd']:>7.4f} {r['median_latency_s']:>6.1f}")


if __name__ == "__main__":
    main()
