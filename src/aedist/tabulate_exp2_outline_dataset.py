"""Generate dataset descriptive table placeholder for Exp2 outline."""

import argparse
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def main(argv: list[str] | None = None):
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Generate Exp2 outline dataset table placeholder")
    parser.add_argument("--output", required=True, help="Path to write tab_exp2_outline_dataset.tex")
    args = parser.parse_args(argv)

    tex = """% Auto-generated - Exp2 outline placeholder
\\begin{table}[h]
\\centering
\\caption{Exp2 dataset descriptive statistics (placeholder)}\\label{tab:exp2-outline-dataset}
\\begin{tabular}{lll}
\\toprule
Metric & Arm & Value \\\\
\\midrule
Run count & Naive & <to fill> \\\\
Run count & Optimized & <to fill> \\\\
Median cost (USD) & Naive & <to fill> \\\\
Median cost (USD) & Optimized & <to fill> \\\\
Median turns & Naive & <to fill> \\\\
Median turns & Optimized & <to fill> \\\\
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
