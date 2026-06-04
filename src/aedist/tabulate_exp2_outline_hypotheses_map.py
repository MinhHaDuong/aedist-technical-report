"""Generate hypotheses-to-tests mapping table placeholder for Exp2 outline.

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.
"""

import argparse
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def main(argv: list[str] | None = None):
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Generate Exp2 outline hypotheses map placeholder")
    parser.add_argument("--output", required=True, help="Path to write tab_exp2_outline_hypotheses_map.tex")
    args = parser.parse_args(argv)

    tex = """% Auto-generated - Exp2 outline placeholder
\\begin{table}[h]
\\centering
\\caption{Exp2 hypotheses and planned tests (placeholder)}\\label{tab:exp2-outline-hypotheses-map}
\\begin{tabular}{llll}
\\toprule
Hypothesis & Metric & Test & Effect size \\\\
\\midrule
H1 & Per-row F1 & Mann-Whitney U & Rank-biserial r \\\\
H2 & Per-row F1 rank diff. & Friedman & Kendall W \\\\
H3 & Provenance delta & Paired Wilcoxon & Matched-pair d \\\\
H4 & Bounce rate & Wilson upper bound & N/A \\\\
H5 & Wiki citation rate & Wilson upper bound & N/A \\\\
H6 & Rank agreement & Spearman rho & Rho value \\\\
\\bottomrule
\\end{tabular}
\\end{table}
"""
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(tex)
    log.info("Wrote %s", output)


if __name__ == "__main__":
    main()
