"""Generate variance decomposition LaTeX table.

Reads the output of ``variance_decomposition()`` and produces a longtable
showing SS, df, and eta-squared for each ANOVA source.

Usage::

    python -m aedist.tabulate_variance \\
        --input derived/variance_decomposition.json \\
        --output report/inputs/generated/tab_variance.tex
"""

from __future__ import annotations


def generate_variance_table(decomposition: dict) -> str:
    """Generate a LaTeX longtable from variance decomposition results.

    Args:
        decomposition: Dict with ``anova`` sub-dict containing SS, df, and
            top-level ``eta_sq_*`` values.

    Returns:
        LaTeX string for the ANOVA table.
    """
    anova = decomposition.get("anova", {})

    rows = [
        ("Model", anova.get("ss_a", 0), anova.get("df_a", 0), decomposition.get("eta_sq_model", 0)),
        (
            "Method",
            anova.get("ss_b", 0),
            anova.get("df_b", 0),
            decomposition.get("eta_sq_method", 0),
        ),
        (
            "Model $\\times$ Method",
            anova.get("ss_ab", 0),
            anova.get("df_ab", 0),
            decomposition.get("eta_sq_interaction", 0),
        ),
        (
            "Residual",
            anova.get("ss_resid", 0),
            anova.get("df_resid", 0),
            decomposition.get("eta_sq_residual", 0),
        ),
    ]

    lines = [
        "% Auto-generated — do not edit",
        "\\begin{longtable}[]{@{}lrrr@{}}",
        "\\caption{Variance decomposition of F1 scores "
        "(two-way ANOVA, model $\\times$ method)}\\label{tab:variance}\\\\",
        "\\toprule",
        "Source & SS & df & $\\eta^2$ \\\\",
        "\\midrule",
        "\\endhead",
        "\\bottomrule",
        "\\endlastfoot",
    ]

    for source, ss, df, eta in rows:
        lines.append(f"{source} & {ss:.4f} & {df} & {eta:.2f} \\\\")

    # Total row
    ss_total = anova.get("ss_total", 0)
    df_total = anova.get("df_total", 0)
    lines.append(f"\\midrule")
    lines.append(f"Total & {ss_total:.4f} & {df_total} & 1.00 \\\\")

    lines.append("\\end{longtable}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """Read variance decomposition JSON and write LaTeX table."""
    import argparse
    import json
    import logging
    from pathlib import Path

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    log = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Generate variance decomposition LaTeX table")
    parser.add_argument(
        "--input",
        default="derived/variance_decomposition.json",
        help="Path to variance decomposition JSON",
    )
    parser.add_argument(
        "--output",
        default="report/inputs/generated/tab_variance.tex",
        help="Path to write LaTeX table",
    )
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    decomposition = json.loads(input_path.read_text())

    latex = generate_variance_table(decomposition)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(latex)
    log.info("Wrote %s", output_path)


if __name__ == "__main__":
    main()
