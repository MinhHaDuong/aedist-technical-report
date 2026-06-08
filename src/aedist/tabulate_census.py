"""Generate census results LaTeX table from measurements.

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.

Reads per-run metrics, groups by model (stripping -runN suffix),
computes medians, and emits a longtable sorted by F1 descending.
Local (Padme) models are marked with (L).
"""

import argparse
import logging
from pathlib import Path

from .tabulate_utils import format_model_name, group_and_summarize_with_stats

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LaTeX generation
# ---------------------------------------------------------------------------


_CONVERGENCE_METHODS = {"direct", "direct+multiturn", "rag_livesearch", "rag"}

# Cohorts that share a convergence method but are NOT the pre-experiment census:
#   exp1_batch2     — Experiment 1 (its own figure/table)
#   derived         — P2 analysis artifacts (exp2_fp_* triage, cross-eval CSVs)
#   rag_consistency — synthetic multi-run aggregates (-union / -consolidated)
# Excluding these yields exactly the archive-sourced census cohort that the
# macros path (tabulate_census_macros --result-dir experiments/archive/outputs)
# selects, keeping the two census tabulators consistent.
_NON_CENSUS_PROMPT_VERSIONS = {"exp1_batch2", "derived", "rag_consistency"}


def _is_census(entry: dict) -> bool:
    return (
        entry.get("method") in _CONVERGENCE_METHODS
        and entry.get("prompt_version") not in _NON_CENSUS_PROMPT_VERSIONS
    )


def _format_f1(row: dict) -> str:
    """Format F1 as 'median ± std' when multiple runs exist, else plain value."""
    f1_pct = row["f1"] * 100
    if row["n_runs"] > 1:
        std_pct = row["f1_std"] * 100
        return f"{f1_pct:.1f} $\\pm$ {std_pct:.1f}\\%"
    return f"{f1_pct:.1f}\\%"


def generate_census_table(metrics: list[dict]) -> str:
    """Generate a LaTeX longtable from per-run metrics."""
    rows = group_and_summarize_with_stats(metrics, filter_fn=_is_census)

    lines = [
        "% Auto-generated — do not edit",
        "\\begin{longtable}[]{@{}lrrrr@{}}",
        "\\caption{Model census: single-shot F1 scores"
        " (median $\\pm$ std, 3 runs)}\\label{tab:census}\\\\",
        "\\toprule",
        "Model & F1 & Precision & Recall & Matched \\\\",
        "\\midrule",
        "\\endhead",
        "\\bottomrule",
        "\\endlastfoot",
    ]

    for row in rows:
        name = format_model_name(row["slug"])
        f1 = _format_f1(row)
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
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write tab_census.tex",
    )
    args = parser.parse_args(argv)

    output_path = Path(args.output)

    from .measurements import load_metrics

    metrics = load_metrics()

    latex = generate_census_table(metrics)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(latex)
    log.info("Wrote %s (%d models)", output_path, len(latex.splitlines()) - 9)


if __name__ == "__main__":
    main()
