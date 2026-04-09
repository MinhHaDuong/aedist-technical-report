"""Generate RAG comparison LaTeX table from measurements.jsonl.

Usage:
    python -m aedist.tabulate_comparaison \\
        --measurements measurements.jsonl \\
        --output report/inputs/generated/tab_comparaison.tex

Reads per-run metrics, finds models present in both census and RAG
conditions, and emits a side-by-side comparison table showing how
RAG affects F1 for each model.
"""

import argparse
import logging
import statistics
from pathlib import Path

from .stats import bootstrap_ci, paired_bootstrap_test
from .tabulate_utils import format_model_name, strip_label

log = logging.getLogger(__name__)

_CENSUS_PREFIX = "census/"
_RAG_PREFIX = "rag/"


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def group_by_sweep(metrics: list[dict]) -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    """Split metrics into census and RAG conditions, keyed by model slug."""
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

    # Only include models present in both conditions
    common_slugs = sorted(set(census) & set(rag))

    if not common_slugs:
        log.warning("No models found in both census and RAG conditions — table will be empty.")

    rows = []
    for slug in common_slugs:
        f1_base_vals = [e["f1"] for e in census[slug]]
        f1_rag_vals = [e["f1"] for e in rag[slug]]
        f1_base = statistics.median(f1_base_vals)
        f1_rag = statistics.median(f1_rag_vals)
        cov_base = statistics.median(e["coverage"] for e in census[slug])
        cov_rag = statistics.median(e["coverage"] for e in rag[slug])
        delta = f1_rag - f1_base

        # Paired significance test (requires equal-length samples)
        if len(f1_base_vals) == len(f1_rag_vals) and len(f1_base_vals) > 1:
            p_value = paired_bootstrap_test(f1_rag_vals, f1_base_vals, seed=42)
        else:
            p_value = None

        # Bootstrap CI for RAG F1 (used for unstable pair detection)
        _, ci_lo, ci_hi = bootstrap_ci(f1_rag_vals, seed=42)

        rows.append(
            {
                "slug": slug,
                "f1_base": f1_base,
                "f1_rag": f1_rag,
                "f1_rag_ci_lo": ci_lo,
                "f1_rag_ci_hi": ci_hi,
                "cov_base": cov_base,
                "cov_rag": cov_rag,
                "delta": delta,
                "p_value": p_value,
                "not_robust": False,
            }
        )

    rows.sort(key=lambda r: r["f1_rag"], reverse=True)

    # Flag unstable pairs: RAG F1 differs by <5pp and CIs overlap
    for i, row_a in enumerate(rows):
        for row_b in rows[i + 1 :]:
            f1_diff = abs(row_a["f1_rag"] - row_b["f1_rag"])
            ci_overlap = (
                row_a["f1_rag_ci_lo"] <= row_b["f1_rag_ci_hi"]
                and row_b["f1_rag_ci_lo"] <= row_a["f1_rag_ci_hi"]
            )
            if f1_diff < 0.05 and ci_overlap:
                row_a["not_robust"] = True
                row_b["not_robust"] = True

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

        # Significance markers (LaTeX superscript)
        p = row.get("p_value")
        if p is not None and p < 0.01:
            delta += "$^{**}$"
        elif p is not None and p < 0.05:
            delta += "$^{*}$"

        # Unstable ranking flag
        if row.get("not_robust"):
            delta += " \\textsuperscript{\\textdagger}"

        lines.append(f"{name} & {f1b} & {f1r} & {cb} & {cr} & {delta} \\\\")

    lines.append("\\end{longtable}")

    # Add footnote if any rows are flagged as not robust
    has_unstable = any(r.get("not_robust") for r in rows)
    if has_unstable:
        lines.append(
            "\\noindent{\\footnotesize \\textsuperscript{\\textdagger}"
            "Not robust: RAG F1 difference $<$5~pp with overlapping bootstrap CIs.}"
        )

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
