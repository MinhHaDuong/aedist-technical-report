"""Generate H1 table placeholder for Exp2 outline."""

import argparse
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def main(argv: list[str] | None = None):
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Generate Exp2 H1 placeholder table")
    parser.add_argument("--output", required=True, help="Path to write tab_exp2_outline_h1.tex")
    args = parser.parse_args(argv)

    tex = """% Auto-generated - Exp2 outline placeholder
\\begin{table}[h]
\\centering
\\caption{H1 placeholder: per-row F1 by arm}\\label{tab:exp2-outline-h1}
\\begin{tabular}{lll}
\\toprule
Arm & Median F1 & IQR \\\\
\\midrule
Naive & <to fill> & <to fill> \\\\
Optimized & <to fill> & <to fill> \\\\
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
