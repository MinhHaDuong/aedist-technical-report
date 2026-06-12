"""Tabulate the aggregation sweep results as a LaTeX table (+ manuscript macros).

Reads experiments/derived/aggregation_sweep.csv and writes a LaTeX table
suitable for inclusion in the manuscript. With ``--output-macros`` it also
emits the fusion-annex macros (best-union cell, single-run baseline from the
cross-eval CSV, intra-model and low-cost recipes — ticket 0531).

Usage:
    uv run python -m aedist.tabulate_aggregation_sweep \
        --input experiments/derived/aggregation_sweep.csv \
        --cross-eval experiments/derived/exp1_cross_eval.csv \
        --output report/inputs/generated/tab_aggregation_sweep.tex \
        --output-macros report/inputs/generated/macros_aggregation_sweep.tex

Tickets 0375, 0531.
"""

import argparse
import csv
import logging
from pathlib import Path

log = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).parent.parent.parent
_INPUT_CSV = _REPO_ROOT / "experiments" / "derived" / "aggregation_sweep.csv"
_OUTPUT_TEX = _REPO_ROOT / "report" / "inputs" / "generated" / "tab_aggregation_sweep.tex"

# Human-readable labels for diversity rules
_DIVERSITY_LABELS = {
    "intra_model": "Intra-model",
    "cross_model_low": "Cross-model low",
    "cross_model_high": "Cross-model high",
    "cross_model_mixed": "Cross-model mixed",
}

# Human-readable labels for merge methods
_METHOD_LABELS = {
    "union": "Union",
    "majority_2": "Majority ($k{=}2$)",
    "majority_3": "Majority ($k{=}3$)",
    "confidence_weighted": "Conf.-weighted",
}


def _safe_float(value: str) -> float | None:
    """Parse a float or return None for 'NA'."""
    if value == "NA" or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _fmt_cell(value: str, bold: bool = False) -> str:
    """Format a CSV cell value for LaTeX output."""
    if value == "NA" or value == "":
        return "---"
    try:
        f = float(value)
        formatted = f"{f:.3f}"
        return rf"\textbf{{{formatted}}}" if bold else formatted
    except ValueError:
        return value


def generate_latex(rows: list[dict]) -> str:
    """Generate a LaTeX booktabs table from the sweep rows."""
    # Find the best F1 cell
    best_f1 = max(
        (_safe_float(r["mean_f1"]) or 0.0 for r in rows),
        default=0.0,
    )

    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{Aggregation sweep results: mean F1 by merge method, pool size, and diversity rule.",
        r"    \emph{Intra-model}: all runs from one model, averaged over 14 models.",
        r"    \emph{Cross-model}: one run per model; low/high/mixed selects by per-run cost.",
        r"    Best cell in \textbf{bold}.}",
        r"\label{tab:aggregation-sweep}",
        r"\small",
        r"\begin{tabular}{llrrrr}",
        r"\toprule",
        r"Merge & Diversity rule & $n{=}2$ & $n{=}3$ & $n{=}4$ \\",
        r"\midrule",
    ]

    # Group rows by (merge_method, diversity_rule) → pool_size → row
    from collections import defaultdict

    grid: dict[tuple[str, str], dict[int, dict]] = defaultdict(dict)
    for r in rows:
        key = (r["merge_method"], r["diversity_rule"])
        pool_size = int(r["pool_size"])
        grid[key][pool_size] = r

    for method in ["union", "majority_2", "majority_3", "confidence_weighted"]:
        method_label = _METHOD_LABELS.get(method, method)
        first_row_for_method = True

        for diversity in ["intra_model", "cross_model_low", "cross_model_high", "cross_model_mixed"]:
            diversity_label = _DIVERSITY_LABELS.get(diversity, diversity)

            cells = []
            for pool_size in [2, 3, 4]:
                r = grid.get((method, diversity), {}).get(pool_size)
                if r is None:
                    cells.append("---")
                else:
                    f1 = _safe_float(r["mean_f1"])
                    is_best = f1 is not None and abs(f1 - best_f1) < 1e-6
                    cells.append(_fmt_cell(r["mean_f1"], bold=is_best))

            if first_row_for_method:
                lines.append(
                    rf"\multirow{{4}}{{*}}{{\rotatebox[origin=c]{{90}}{{{method_label}}}}} & "
                    rf"{diversity_label} & {' & '.join(cells)} \\"
                )
                first_row_for_method = False
            else:
                lines.append(rf" & {diversity_label} & {' & '.join(cells)} \\")

        # Separator between method groups (except after last)
        if method != "confidence_weighted":
            lines.append(r"\addlinespace[2pt]")

    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
        "",
    ]
    return "\n".join(lines)


# The sweep cell the manuscript quotes as "the best union recipe": three runs
# from the three most expensive models. Pinned to the same cell that
# tests/test_manuscript_derived_numbers.py::_sweep_cell pins, so the macros
# and the adherence guard can never quote different cells.
_BEST_UNION_CELL = ("union", "cross_model_high", 3)


def _cell(rows: list[dict], method: str, rule: str, pool: int) -> dict:
    """Return the sweep row for (merge_method, diversity_rule, pool_size)."""
    for r in rows:
        if (
            r["merge_method"] == method
            and r["diversity_rule"] == rule
            and r["pool_size"] == str(pool)
        ):
            return r
    raise ValueError(f"sweep cell {method}/{rule}/pool{pool} not found")


def generate_macros(rows: list[dict], xeval_rows: list[dict]) -> str:
    """Render the fusion-annex macros from the sweep CSV + Exp1 cross-eval CSV.

    The single-run baseline (mean / best recall, best F1) comes from
    ``exp1_cross_eval.csv`` — the same artifact the §4 run statistics use —
    while the pooled cells come from ``aggregation_sweep.csv``.
    """
    best = _cell(rows, *_BEST_UNION_CELL)
    best_recall = float(best["mean_recall"])
    intra3 = _cell(rows, "union", "intra_model", 3)
    low_recalls = [
        float(r["mean_recall"])
        for r in rows
        if r["merge_method"] == "union" and r["diversity_rule"] == "cross_model_low"
    ]

    cov_vals = [float(r["accuracy_coverage"]) for r in xeval_rows if r.get("accuracy_coverage")]
    f1_vals = [float(r["accuracy_f1"]) for r in xeval_rows if r.get("accuracy_f1")]
    single_mean_recall = sum(cov_vals) / len(cov_vals)

    lines = [
        "% Auto-generated by aedist.tabulate_aggregation_sweep — do not edit.",
        f"\\newcommand{{\\AggBestUnionRecall}}{{{best_recall:.3f}}}",
        f"\\newcommand{{\\AggBestUnionCost}}{{{float(best['mean_cost_usd']):.2f}}}",
        f"\\newcommand{{\\AggBestUnionCandidates}}{{{round(float(best['mean_n_plants']))}}}",
        f"\\newcommand{{\\AggBestUnionFOne}}{{{float(best['mean_f1']):.3f}}}",
        f"\\newcommand{{\\AggSingleRunMeanRecall}}{{{single_mean_recall:.3f}}}",
        f"\\newcommand{{\\AggUnionGainX}}{{{best_recall / single_mean_recall:.1f}}}",
        f"\\newcommand{{\\AggBestSingleRecall}}{{{max(cov_vals):.3f}}}",
        f"\\newcommand{{\\AggBestSingleFOne}}{{{max(f1_vals):.3f}}}",
        f"\\newcommand{{\\AggIntraPoolThreeRecall}}{{{float(intra3['mean_recall']):.3f}}}",
        f"\\newcommand{{\\AggIntraPoolThreeCost}}{{{float(intra3['mean_cost_usd']):.2f}}}",
        f"\\newcommand{{\\AggLowRecallMin}}{{{min(low_recalls):.2f}}}",
        f"\\newcommand{{\\AggLowRecallMax}}{{{max(low_recalls):.2f}}}",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Tabulate the aggregation sweep CSV as a LaTeX table."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=_INPUT_CSV,
        help="Path to aggregation_sweep.csv (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_OUTPUT_TEX,
        help="Path to write the LaTeX table (default: %(default)s)",
    )
    parser.add_argument(
        "--cross-eval",
        type=Path,
        default=_REPO_ROOT / "experiments" / "derived" / "exp1_cross_eval.csv",
        help="Exp1 cross-eval CSV (single-run baseline for the macros; default: %(default)s)",
    )
    parser.add_argument(
        "--output-macros",
        type=Path,
        default=None,
        help="Optional path to write the fusion-annex macros (ticket 0531)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    with open(args.input, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    log.info("Read %d rows from %s", len(rows), args.input)

    latex = generate_latex(rows)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(latex, encoding="utf-8")
    log.info("Wrote LaTeX table to %s", args.output)

    if args.output_macros is not None:
        with open(args.cross_eval, newline="", encoding="utf-8") as f:
            xeval_rows = list(csv.DictReader(f))
        args.output_macros.parent.mkdir(parents=True, exist_ok=True)
        args.output_macros.write_text(generate_macros(rows, xeval_rows), encoding="utf-8")
        log.info("Wrote macros to %s", args.output_macros)


if __name__ == "__main__":
    main()
