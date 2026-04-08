"""Generate Pareto-front CSV from measurements.jsonl.

Writes a CSV with columns: model, f1, cost_usd, local
sorted by f1 descending.

Usage:
    uv run python -m aedist.plot_pareto \\
        --measurements measurements.jsonl \\
        --output slides/inputs/generated/pareto.csv
"""

import argparse
import csv
import logging
from pathlib import Path

from .tabulate_macros import load_and_summarize

log = logging.getLogger(__name__)


def build_pareto_rows(metrics: list[dict]) -> list[dict]:
    """Build rows for the Pareto chart.

    Returns list of dicts with keys: model, f1, cost_usd, local.
    Sorted by f1 descending.

    Cost is computed as per-model mean from metrics cost_usd fields.
    """
    summary = load_and_summarize(metrics)

    from .tabulate_utils import strip_label as slug_from_label

    cost_lists: dict[str, list[float]] = {}
    for entry in metrics:
        c = entry.get("cost_usd")
        if c is not None and c > 0:
            slug = slug_from_label(entry["label"])
            cost_lists.setdefault(slug, []).append(c)
    costs = {slug: sum(vals) / len(vals) for slug, vals in cost_lists.items()}

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
        description="Generate Pareto-front CSV from measurements.jsonl",
    )
    parser.add_argument("--output", required=True, help="Path to write pareto.csv")
    args = parser.parse_args()

    output_path = Path(args.output)

    from .measurements import load_metrics

    metrics = load_metrics()

    rows = build_pareto_rows(metrics)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["model", "f1", "cost_usd", "local"])
        writer.writeheader()
        writer.writerows(rows)

    log.info("Wrote %d rows to %s", len(rows), output_path)


if __name__ == "__main__":
    main()
