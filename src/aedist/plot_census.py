"""Generate census bar-chart CSV from measurements.jsonl.

Writes census_bars.csv with columns: model, f1, n_tp, n_fp, local
sorted by f1 descending. f1 is median across runs as a decimal 0-1.
n_tp and n_fp are median matched/hallucinated plant counts (integers).
local is 1 for Padme models, 0 otherwise.

Also writes census_scatter_tp.csv and census_scatter_fp.csv alongside
census_bars.csv — one row per plant, used by the dot-per-plant slide chart.

Usage:
    uv run python -m aedist.plot_census \\
        --measurements measurements.jsonl \\
        --output slides/inputs/generated/census_bars.csv
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


def build_scatter_rows(census_rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Generate one row per plant for the dot-per-plant scatter chart.

    Model index 0 = best model (highest f1). pgfplots y dir=reverse puts it
    at the top of the horizontal chart.

    Returns (tp_rows, fp_rows):
      tp_rows — matched plants, x = 1..n_tp, plotted in positive territory
      fp_rows — hallucinated plants, x = -1..-n_fp, plotted in negative territory
    """
    tp_rows: list[dict] = []
    fp_rows: list[dict] = []
    for model_idx, row in enumerate(census_rows):
        y = model_idx
        for pi in range(1, int(row["n_tp"]) + 1):
            tp_rows.append({"x": pi, "y": y})
        for pi in range(1, int(row["n_fp"]) + 1):
            fp_rows.append({"x": -pi, "y": y})
    return tp_rows, fp_rows


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

    tp_rows, fp_rows = build_scatter_rows(rows)
    tp_path = output_path.parent / "census_scatter_tp.csv"
    fp_path = output_path.parent / "census_scatter_fp.csv"
    for path, data in [(tp_path, tp_rows), (fp_path, fp_rows)]:
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["x", "y"])
            writer.writeheader()
            writer.writerows(data)
        log.info("Wrote %d rows to %s", len(data), path)


if __name__ == "__main__":
    main()
