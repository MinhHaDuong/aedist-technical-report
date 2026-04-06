"""Generate census results LaTeX table from all_metrics.json.

Usage:
    python -m aedist.tabulate_census \\
        --input results/summary/all_metrics.json \\
        --output report/inputs/generated/tab_census.tex

Reads per-run metrics, groups by model (stripping -runN suffix),
computes medians, and emits a longtable sorted by F1 descending.
Local (Padme) models are marked with (L).
"""

import argparse
import json
import logging
from pathlib import Path

from .tabulate_utils import format_model_name, group_and_summarize

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LaTeX generation
# ---------------------------------------------------------------------------


_CENSUS_PREFIX = "sweep1_census/"


def _is_census(entry: dict) -> bool:
    return entry.get("label", "").startswith(_CENSUS_PREFIX)


def generate_census_table(metrics: list[dict]) -> str:
    """Generate a LaTeX longtable from per-run metrics."""
    rows = group_and_summarize(metrics, filter_fn=_is_census)

    lines = [
        "% Auto-generated — do not edit",
        "\\begin{longtable}[]{@{}lrrrr@{}}",
        "\\caption{Model census: single-shot F1 scores (median of 3 runs)}\\label{tab:census}\\\\",
        "\\toprule",
        "Model & F1 & Precision & Recall & Matched \\\\",
        "\\midrule",
        "\\endhead",
        "\\bottomrule",
        "\\endlastfoot",
    ]

    for row in rows:
        name = format_model_name(row["slug"])
        f1 = f"{row['f1'] * 100:.1f}\\%"
        prec = f"{row['precision'] * 100:.1f}\\%"
        recall = f"{row['coverage'] * 100:.1f}\\%"
        matched = f"{row['n_matched']}/{row['n_reference']}"
        lines.append(f"{name} & {f1} & {prec} & {recall} & {matched} \\\\")

    lines.append("\\end{longtable}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None):
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Generate census results LaTeX table",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", help="Path to all_metrics.json (legacy)")
    source.add_argument("--measurements", help="Path to measurements.jsonl")
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write tab_census.tex",
    )
    args = parser.parse_args(argv)

    output_path = Path(args.output)

    if args.measurements:
        from .measurements_adapter import load_metrics_from_measurements

        metrics = load_metrics_from_measurements(args.measurements)
    else:
        with open(args.input) as f:
            metrics = json.load(f)

    latex = generate_census_table(metrics)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(latex)
    log.info("Wrote %s (%d models)", output_path, len(latex.splitlines()) - 9)


if __name__ == "__main__":
    main()
