"""Generate method-convergence strip plot from measurements.jsonl.

For each method (Y axis), plots every run as a dot on the X axis.
Correct identifications (TP) shown as blue dots on the positive side.
Hallucinated plants (FP) shown as red dots on the negative side.
Reference total (163 plants) marked with a vertical dashed line.

A good method drives all dots to +163 with nothing in the red.

Outputs CSV for pgfplots in slides.

Usage:
    uv run python -m aedist.plot_method_convergence \
        --output slides/inputs/generated/method_convergence.csv
"""

import argparse
import csv
import logging
from pathlib import Path

from .measurements import load

log = logging.getLogger(__name__)

# Aggregation artifacts — not individual model runs
_EXCLUDE_SUFFIXES = ("-union", "-consolidated", "-filtered", "-unverified")

# Prompt versions that are duplicates of another method's data
_EXCLUDE_PROMPT_VERSIONS = ("_extracted",)

# Methods to include and display order (top to bottom in plot)
_METHOD_ORDER = ["single", "multiturn", "web", "rag", "decomposed"]


def _normalize_model(raw: str) -> str:
    """Normalize model name to slug (strip provider prefix)."""
    return raw.split("/")[-1]


def load_convergence_data() -> list[dict]:
    """Load and clean measurements for the convergence plot.

    Returns list of dicts with keys: method, model, tp, fp, fn.
    """
    rows = []
    for record in load():
        method = record.method.value
        if method not in _METHOD_ORDER:
            continue
        model = _normalize_model(record.method_params.model)
        if any(model.endswith(s) for s in _EXCLUDE_SUFFIXES):
            continue
        pv = record.method_params.prompt_version or ""
        if pv in _EXCLUDE_PROMPT_VERSIONS:
            continue
        s = record.result_summary
        if s.tp is None:
            continue
        rows.append(
            {
                "method": method,
                "model": model,
                "tp": s.tp or 0,
                "fp": s.fp or 0,
                "fn": s.fn or 0,
            }
        )
    return rows


def write_csv(rows: list[dict], output: Path) -> None:
    """Write convergence data as CSV."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["method", "model", "tp", "fp", "fn"])
        writer.writeheader()
        writer.writerows(rows)
    log.info("Wrote %d rows to %s", len(rows), output)


def _core_models(rows: list[dict]) -> set[str]:
    """Find models that appear in all methods."""
    from collections import defaultdict

    model_methods: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        model_methods[r["model"]].add(r["method"])
    all_methods = set(_METHOD_ORDER)
    return {m for m, methods in model_methods.items() if methods >= all_methods}


def expand_dots(
    rows: list[dict],
    max_runs_per_model: int = 3,
    models: set[str] | None = None,
    max_fp: int = 50,
) -> tuple[list[dict], list[tuple[str, float]]]:
    """Expand run-level data to one row per plant for dot rendering.

    Each output row has: x (plant position), y (row position), type (tp/fp).
    Within each method band, runs are stacked vertically and sorted by TP
    descending so the longest bars are at the top.

    Args:
        rows: run-level data from load_convergence_data()
        max_runs_per_model: limit runs per model per method (default 3)
        models: if given, include only these model slugs
        max_fp: clip FP count for display (avoids extreme outliers crushing scale)

    Returns (dots, method_labels) where method_labels maps method name to Y center.
    """
    dots = []
    y_offset = 0.0
    method_labels = []

    for method in _METHOD_ORDER:
        method_rows = [r for r in rows if r["method"] == method]
        if models:
            method_rows = [r for r in method_rows if r["model"] in models]
        if not method_rows:
            continue

        # Deduplicate: keep only max_runs_per_model per model
        from collections import Counter

        model_count: Counter[str] = Counter()
        filtered = []
        for r in method_rows:
            if model_count[r["model"]] < max_runs_per_model:
                filtered.append(r)
                model_count[r["model"]] += 1
        method_rows = filtered

        # Sort by TP descending (longest bars at top of band)
        method_rows.sort(key=lambda r: r["tp"], reverse=True)

        band_start = y_offset
        for i, run in enumerate(method_rows):
            y = y_offset + i * 0.35
            for x in range(1, run["tp"] + 1):
                dots.append({"x": x, "y": y, "type": "tp", "method": method})
            fp_display = min(run["fp"], max_fp)
            for x in range(1, fp_display + 1):
                dots.append({"x": -x, "y": y, "type": "fp", "method": method})

        y_offset += len(method_rows) * 0.35 + 1.5
        band_center = band_start + (len(method_rows) - 1) * 0.35 / 2
        method_labels.append((method, band_center))

    return dots, method_labels


def write_dots_csv(dots: list[dict], output: Path) -> None:
    """Write dot-level data as CSV for pgfplots scatter."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["x", "y", "type", "method"])
        writer.writeheader()
        writer.writerows(dots)
    log.info("Wrote %d dots to %s", len(dots), output)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Generate method-convergence strip plot data",
    )
    parser.add_argument("--output", required=True, help="Path to write run-level CSV")
    parser.add_argument("--dots", default=None, help="Path to write dot-level CSV for scatter")
    parser.add_argument(
        "--core-only",
        action="store_true",
        help="Dots: only models tested under all 5 methods",
    )
    parser.add_argument(
        "--max-fp", type=int, default=50, help="Clip FP count for dot display (default 50)"
    )
    args = parser.parse_args()

    rows = load_convergence_data()
    write_csv(rows, Path(args.output))

    if args.dots:
        models = _core_models(rows) if args.core_only else None
        dots, labels = expand_dots(rows, models=models, max_fp=args.max_fp)
        write_dots_csv(dots, Path(args.dots))
        for method, y_center in labels:
            log.info("  %s: y_center=%.1f", method, y_center)


if __name__ == "__main__":
    main()
