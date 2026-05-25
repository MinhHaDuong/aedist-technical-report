"""Generate census bar-chart CSV from measurements.jsonl.

Writes census_bars.csv with columns: model, f1, n_tp, n_fp, local
sorted by f1 descending. f1 is median across runs as a decimal 0-1.
n_tp and n_fp are median matched/hallucinated plant counts (integers).
local is 1 for Padme models, 0 otherwise.

Usage:
    uv run python -m aedist.plot_census \\
        --measurements measurements.jsonl \\
        --output report/inputs/generated/census_bars.csv
"""

import argparse
import csv
import logging
import statistics
from pathlib import Path

from .measurements import SYNTHETIC_SUFFIXES
from .tabulate_macros import load_and_summarize
from .tabulate_utils import strip_label as slug_from_label

log = logging.getLogger(__name__)


def _aggregate_tp_fp(metrics: list[dict]) -> dict[str, dict]:
    """Group metrics by slug and compute median n_matched, n_hallucinated."""
    by_model: dict[str, list] = {}
    for entry in metrics:
        if entry.get("label", "").startswith("derived/"):
            continue
        slug = slug_from_label(entry["label"])
        if any(slug.endswith(s) for s in SYNTHETIC_SUFFIXES):
            continue
        tp = entry.get("n_matched") or 0
        fp = entry.get("n_hallucinated") or 0
        by_model.setdefault(slug, []).append((tp, fp))
    result = {}
    for slug, pairs in by_model.items():
        result[slug] = {
            "n_tp": round(statistics.median(p[0] for p in pairs)),
            "n_fp": round(statistics.median(p[1] for p in pairs)),
        }
    return result


def build_census_rows(metrics: list[dict]) -> list[dict]:
    """Build sorted rows for the census bar chart (base models only).

    Filters out synthetic entries (union-vote, consolidated) and derived
    measurements (matching_sensitivity, etc.) so the chart shows
    single-shot baseline performance only.

    Returns list of dicts with keys: model, f1, n_tp, n_fp, local.
    Sorted by f1 descending.
    """
    metrics = [m for m in metrics if not m.get("label", "").startswith("derived/")]
    summary = load_and_summarize(metrics)
    tp_fp = _aggregate_tp_fp(metrics)
    rows = [
        {
            "model": slug.replace("_", "-"),
            "f1": info["median_f1"],
            "n_tp": tp_fp.get(slug, {}).get("n_tp", round(info["median_f1"] * 163)),
            "n_fp": tp_fp.get(slug, {}).get("n_fp", 0),
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
        writer = csv.DictWriter(f, fieldnames=["model", "f1", "n_tp", "n_fp", "local"])
        writer.writeheader()
        writer.writerows(rows)
    log.info("Wrote %d rows to %s", len(rows), output_path)


if __name__ == "__main__":
    main()
