"""Generate Pareto-front CSV and scatter PDF from measurements.jsonl.

Writes a CSV with columns: model, f1, cost_usd, local
sorted by f1 descending.  Optionally writes a PDF scatter plot.

Usage:
    uv run python -m aedist.plot_pareto \\
        --output slides/inputs/generated/pareto.csv \\
        --figure slides/inputs/generated/fig_pareto.pdf
"""

import argparse
import csv
import logging
from pathlib import Path

from .tabulate_macros import load_and_summarize
from .util import COLOR_MATCHED

log = logging.getLogger(__name__)

# Darker blue for local models (matched colour mixed with black).
_COLOR_LOCAL = "#1A5070"


def write_pdf(rows: list[dict], output: Path) -> None:
    """Write a Pareto scatter plot (F1 vs cost) to *output* as PDF."""
    import matplotlib.pyplot as plt

    # Keep local models (cost=0 is expected) but drop cloud models without cost data.
    filtered = [r for r in rows if r["cost_usd"] > 0 or r["local"] == 1]

    cloud = [r for r in filtered if r["local"] == 0]
    local = [r for r in filtered if r["local"] == 1]

    fig, ax = plt.subplots(figsize=(7, 4.5))

    if cloud:
        ax.scatter(
            [r["cost_usd"] for r in cloud],
            [r["f1"] for r in cloud],
            color=COLOR_MATCHED,
            marker="o",
            s=40,
            label="Modèles cloud",
            zorder=3,
        )
    if local:
        ax.scatter(
            [r["cost_usd"] for r in local],
            [r["f1"] for r in local],
            color=_COLOR_LOCAL,
            marker="^",
            s=50,
            label="Modèles locaux",
            zorder=3,
        )

    ax.set_xlabel("Coût par requête (USD)")
    ax.set_ylabel("Score F1")
    ax.set_xlim(-0.005, 0.30)
    ax.set_ylim(0, 1.0)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right", fontsize="small")

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", dpi=300)
    plt.close(fig)
    log.info("Wrote %s", output)


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
        description="Generate Pareto-front CSV and/or scatter PDF",
    )
    parser.add_argument("--output", help="Path to write pareto.csv")
    parser.add_argument("--figure", help="Path to write scatter PDF")
    args = parser.parse_args()

    if not args.output and not args.figure:
        parser.error("at least one of --output or --figure is required")

    from .measurements import load_metrics

    metrics = load_metrics()
    rows = build_pareto_rows(metrics)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["model", "f1", "cost_usd", "local"])
            writer.writeheader()
            writer.writerows(rows)
        log.info("Wrote %d rows to %s", len(rows), output_path)

    if args.figure:
        write_pdf(rows, Path(args.figure))


if __name__ == "__main__":
    main()
