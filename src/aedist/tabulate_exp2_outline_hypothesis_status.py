"""Generate synthesis hypothesis-status table placeholder for Exp2 outline."""

import argparse
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def main(argv: list[str] | None = None):
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Generate Exp2 hypothesis-status placeholder table")
    parser.add_argument("--output", required=True, help="Path to write tab_exp2_outline_hypothesis_status.tex")
    args = parser.parse_args(argv)

    tex = """% Auto-generated - Exp2 outline placeholder
\\begin{table}[h]
\\centering
\\caption{Exp2 synthesis: hypothesis status (placeholder)}\\label{tab:exp2-outline-hypothesis-status}
\\begin{tabular}{lll}
\\toprule
Hypothesis & Status & Evidence pointer \\\\
\\midrule
H1 & <to fill> & <to fill> \\\\
H2 & <to fill> & <to fill> \\\\
H3 & <to fill> & <to fill> \\\\
H4 & <to fill> & <to fill> \\\\
H5 & <to fill> & <to fill> \\\\
H6 & <to fill> & <to fill> \\\\
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
