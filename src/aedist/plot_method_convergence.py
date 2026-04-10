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


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Generate method-convergence strip plot data",
    )
    parser.add_argument("--output", required=True, help="Path to write CSV")
    args = parser.parse_args()

    rows = load_convergence_data()
    write_csv(rows, Path(args.output))


if __name__ == "__main__":
    main()
