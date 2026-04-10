"""Generate method-convergence strip plot from measurements.jsonl.

For each method (Y axis), plots every run as a horizontal bar.
Each bar is a row of dots: 1 dot = 1 plant.
Blue dots = correctly identified (TP). Orange dots = hallucinated (FP).
Dashed green line at 163 = complete inventory.

A good method drives all bars to 163 with nothing in orange.

Usage:
    uv run python -m aedist.plot_method_convergence \
        --output slides/inputs/generated/fig_method_convergence.pdf
"""

import argparse
import csv
import logging
from collections import Counter, defaultdict
from pathlib import Path

from .measurements import load

log = logging.getLogger(__name__)

# Colors matching slides.tex definitions
_MATCHED = "#2E86AB"
_HALLUC = "#F5A623"

# Aggregation artifacts — not individual model runs
_EXCLUDE_SUFFIXES = ("-union", "-consolidated", "-filtered", "_filtered", "-unverified")

# Prompt versions that are duplicates of another method's data
_EXCLUDE_PROMPT_VERSIONS = ("_extracted",)

# Methods to include and display order (bottom to top in plot)
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


def core_models(rows: list[dict]) -> set[str]:
    """Find models that appear in all methods."""
    model_methods: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        model_methods[r["model"]].add(r["method"])
    all_methods = set(_METHOD_ORDER)
    return {m for m, methods in model_methods.items() if methods >= all_methods}


def write_csv(rows: list[dict], output: Path) -> None:
    """Write convergence data as CSV."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["method", "model", "tp", "fp", "fn"])
        writer.writeheader()
        writer.writerows(rows)
    log.info("Wrote %d rows to %s", len(rows), output)


def write_pdf(
    rows: list[dict],
    output: Path,
    models: set[str] | None = None,
    max_runs_per_model: int = 3,
    max_fp: int = 50,
) -> None:
    """Generate the method convergence strip plot as PDF.

    Each run becomes a thin horizontal line: blue segment from 0 to TP,
    orange segment from 0 to -FP. Within each method band, runs are
    stacked vertically and sorted by TP descending.
    """
    import matplotlib.pyplot as plt
    import numpy as np

    fig, ax = plt.subplots(figsize=(10, 5))

    y_offset = 0.0
    method_ticks = []
    spacing = 0.5
    gap = 1.8

    for method in _METHOD_ORDER:
        method_rows = [r for r in rows if r["method"] == method]
        if models:
            method_rows = [r for r in method_rows if r["model"] in models]
        if not method_rows:
            continue

        # Limit runs per model
        model_count: Counter[str] = Counter()
        filtered = []
        for r in method_rows:
            if model_count[r["model"]] < max_runs_per_model:
                filtered.append(r)
                model_count[r["model"]] += 1
        method_rows = filtered

        # Sort by TP descending
        method_rows.sort(key=lambda r: r["tp"], reverse=True)

        band_start = y_offset
        for i, run in enumerate(method_rows):
            y = y_offset + i * spacing
            tp = run["tp"]
            fp = min(run["fp"], max_fp)

            # TP dots (blue, right of 0) — 1 dot = 1 plant
            if tp > 0:
                xs = np.arange(1, tp + 1)
                ys = np.full_like(xs, y, dtype=float)
                ax.scatter(xs, ys, s=2, c=_MATCHED, marker="|", linewidths=0.4, zorder=3)

            # FP dots (orange, left of 0) — 1 dot = 1 hallucinated plant
            if fp > 0:
                xs = -np.arange(1, fp + 1)
                ys = np.full_like(xs, y, dtype=float)
                ax.scatter(xs, ys, s=2, c=_HALLUC, marker="|", linewidths=0.4, zorder=3)

        band_center = band_start + (len(method_rows) - 1) * spacing / 2
        method_ticks.append((band_center, method.replace("_", " ").title()))
        y_offset += len(method_rows) * spacing + gap

    # Reference line at 163
    ax.axvline(x=163, color="green", linewidth=0.8, linestyle="--", alpha=0.7, zorder=2)
    ax.text(164, y_offset - gap, "163", color="green", fontsize=7, va="top")

    # Zero line
    ax.axvline(x=0, color="black", linewidth=0.3, alpha=0.3, zorder=1)

    # Y axis: method labels
    ax.set_yticks([t[0] for t in method_ticks])
    ax.set_yticklabels([t[1] for t in method_ticks])
    ax.set_xlabel("Number of power plants")
    ax.set_xlim(-55, 180)
    ax.invert_yaxis()
    ax.grid(axis="x", linewidth=0.2, alpha=0.3)
    ax.set_axisbelow(True)

    # Legend
    ax.scatter([], [], s=10, c=_MATCHED, label="Correctly identified")
    ax.scatter([], [], s=10, c=_HALLUC, label="Hallucinated")
    ax.legend(loc="lower right", fontsize=7, framealpha=0.8)

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", dpi=300)
    plt.close(fig)
    log.info("Wrote %s", output)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Generate method-convergence strip plot",
    )
    parser.add_argument("--output", required=True, help="Path to write PDF or CSV")
    parser.add_argument(
        "--csv", default=None, help="Also write run-level CSV (for data inspection)"
    )
    parser.add_argument(
        "--core-only",
        action="store_true",
        help="Only models tested under all 5 methods",
    )
    parser.add_argument("--max-fp", type=int, default=50, help="Clip FP display (default 50)")
    args = parser.parse_args()

    rows = load_convergence_data()
    models = core_models(rows) if args.core_only else None

    output = Path(args.output)
    if output.suffix == ".pdf":
        write_pdf(rows, output, models=models, max_fp=args.max_fp)
    else:
        write_csv(rows, output)

    if args.csv:
        write_csv(rows, Path(args.csv))


if __name__ == "__main__":
    main()
