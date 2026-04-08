"""Generate RAG comparison LaTeX table from measurements.jsonl.

Usage:
    python -m aedist.tabulate_comparaison \\
        --measurements measurements.jsonl \\
        --output report/inputs/generated/tab_comparaison.tex

Reads per-run metrics, finds models present in both census (sweep1) and RAG
(sweep_rag) sweeps, and emits a side-by-side comparison table showing how
RAG affects F1 for each model.
"""

import argparse
import logging
import statistics
from pathlib import Path

from .tabulate_utils import format_model_name, strip_label

log = logging.getLogger(__name__)

_CENSUS_PREFIX = "sweep1_census/"
_RAG_PREFIX = "sweep_rag/"


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def group_by_sweep(metrics: list[dict]) -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    """Split metrics into census and RAG groups, keyed by model slug."""
    census: dict[str, list[dict]] = {}
    rag: dict[str, list[dict]] = {}
    for entry in metrics:
        label = entry.get("label", "")
        slug = strip_label(label)
        if label.startswith(_CENSUS_PREFIX):
            census.setdefault(slug, []).append(entry)
        elif label.startswith(_RAG_PREFIX):
            rag.setdefault(slug, []).append(entry)
    return census, rag


# ---------------------------------------------------------------------------
# LaTeX generation
# ---------------------------------------------------------------------------


def generate_comparaison_table(metrics: list[dict]) -> tuple[str, int]:
    """Generate a LaTeX longtable comparing baseline vs. RAG F1.

    Returns (latex_string, number_of_models_compared).
    """
    census, rag = group_by_sweep(metrics)

    # Only include models present in both sweeps
    common_slugs = sorted(set(census) & set(rag))

    if not common_slugs:
        log.warning("No models found in both census and RAG sweeps — table will be empty.")

    rows = []
    for slug in common_slugs:
        f1_base = statistics.median(e["f1"] for e in census[slug])
        f1_rag = statistics.median(e["f1"] for e in rag[slug])
        cov_base = statistics.median(e["coverage"] for e in census[slug])
        cov_rag = statistics.median(e["coverage"] for e in rag[slug])
        delta = f1_rag - f1_base
        rows.append(
            {
                "slug": slug,
                "f1_base": f1_base,
                "f1_rag": f1_rag,
                "cov_base": cov_base,
                "cov_rag": cov_rag,
                "delta": delta,
            }
        )

    rows.sort(key=lambda r: r["f1_rag"], reverse=True)

    lines = [
        "% Auto-generated — do not edit",
        "\\begin{longtable}[]{@{}lrrrrr@{}}",
        "\\caption{RAG comparison: baseline vs.\\ wholesale RAG"
        " (median F1 of 3 runs)}\\label{tab:comparaison}\\\\",
        "\\toprule",
        "Model & F1 Base & F1 RAG & Recall Base & Recall RAG & $\\Delta$F1 \\\\",
        "\\midrule",
        "\\endhead",
        "\\bottomrule",
        "\\endlastfoot",
    ]

    for row in rows:
        name = format_model_name(row["slug"])
        f1b = f"{row['f1_base'] * 100:.1f}\\%"
        f1r = f"{row['f1_rag'] * 100:.1f}\\%"
        cb = f"{row['cov_base'] * 100:.1f}\\%"
        cr = f"{row['cov_rag'] * 100:.1f}\\%"
        sign = "+" if row["delta"] >= 0 else ""
        delta = f"{sign}{row['delta'] * 100:.1f}\\%"
        lines.append(f"{name} & {f1b} & {f1r} & {cb} & {cr} & {delta} \\\\")

    lines.append("\\end{longtable}")
    return "\n".join(lines) + "\n", len(common_slugs)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None):
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Generate RAG comparison LaTeX table",
    )
    parser.add_argument("--output", required=True, help="Path to write tab_comparaison.tex")
    args = parser.parse_args(argv)

    output_path = Path(args.output)

    from .measurements import load_metrics

    metrics = load_metrics()

    latex, n_compared = generate_comparaison_table(metrics)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(latex)
    log.info("Wrote %s (%d models compared)", output_path, n_compared)


if __name__ == "__main__":
    main()
