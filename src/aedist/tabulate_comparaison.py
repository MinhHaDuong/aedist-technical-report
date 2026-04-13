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

from .stats import correct_pvalues, paired_bootstrap_test
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


def _load_unstable_slugs(variance_path: Path | None) -> set[str]:
    """Load unstable model slugs from variance decomposition JSON.

    Returns a set of model slugs (provider prefix stripped) that appear
    in at least one unstable pair.
    """
    if variance_path is None or not variance_path.exists():
        return set()
    import json

    data = json.loads(variance_path.read_text())
    slugs: set[str] = set()
    for pair in data.get("unstable_pairs", []):
        for key in ("model_a", "model_b"):
            full_id = pair.get(key, "")
            # Strip provider prefix: "openai/gpt-5.4" -> "gpt-5.4"
            slug = full_id.split("/", 1)[-1] if "/" in full_id else full_id
            slugs.add(slug)
    return slugs


def generate_comparaison_table(
    metrics: list[dict], *, variance_path: Path | None = None,
) -> tuple[str, int]:
    """Generate a LaTeX longtable comparing baseline vs. RAG F1.

    Returns (latex_string, number_of_models_compared).
    """
    unstable_slugs = _load_unstable_slugs(variance_path)
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

        rows.append(
            {
                "slug": slug,
                "f1_base": f1_base,
                "f1_rag": f1_rag,
                "cov_base": cov_base,
                "cov_rag": cov_rag,
                "delta": delta,
                "p_value": p_value,
            }
        )

    # Apply Benjamini-Hochberg FDR correction across all comparisons (G6)
    raw_pvals = [r["p_value"] for r in rows]
    adjusted_pvals = correct_pvalues(raw_pvals, method="fdr_bh")
    for row, adj_p in zip(rows, adjusted_pvals):
        row["p_value_raw"] = row["p_value"]
        row["p_value"] = adj_p  # significance markers now use FDR-adjusted values

    n_corrected = sum(1 for p in raw_pvals if p is not None)
    if n_corrected > 1:
        log.info("Applied Benjamini-Hochberg FDR correction to %d p-values.", n_corrected)

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

    # Determine which rows get daggers, then check discriminating power
    dagger_slugs = {row["slug"] for row in rows if row["slug"] in unstable_slugs}
    all_flagged = len(dagger_slugs) == len(rows) and len(rows) > 0

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

        # Unstable pair marker — only when some rows are NOT flagged
        if not all_flagged and row["slug"] in dagger_slugs:
            f1r += "$\\dagger$"

        lines.append(f"{name} & {f1b} & {f1r} & {cb} & {cr} & {delta} \\\\")

    dagger_note = (
        "Unstable ranking: $<$5\\,pp from nearest neighbour"
        " with overlapping bootstrap 95\\% CIs."
    )
    if dagger_slugs:
        lines.append("\\midrule")
        if all_flagged:
            # All rows flagged — table-level note without per-row daggers
            lines.append(
                "\\multicolumn{6}{l}{\\footnotesize "
                "All inter-model differences are $<$5\\,pp"
                " with overlapping bootstrap 95\\% CIs.} \\\\"
            )
        else:
            lines.append(
                "\\multicolumn{6}{l}{\\footnotesize $\\dagger$ "
                + dagger_note
                + "} \\\\"
            )
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
    parser.add_argument(
        "--variance-json",
        default=None,
        help="Path to variance_decomposition.json for unstable pair flagging",
    )
    args = parser.parse_args(argv)

    output_path = Path(args.output)
    variance_path = Path(args.variance_json) if args.variance_json else None

    from .measurements import load_metrics

    metrics = load_metrics()

    latex, n_compared = generate_comparaison_table(metrics, variance_path=variance_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(latex)
    log.info("Wrote %s (%d models compared)", output_path, n_compared)


if __name__ == "__main__":
    main()
