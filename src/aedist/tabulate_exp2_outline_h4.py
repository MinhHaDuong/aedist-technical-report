"""Generate H4 table placeholder for Exp2 outline."""

import argparse
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def main(argv: list[str] | None = None):
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Generate Exp2 H4 placeholder table")
    parser.add_argument("--output", required=True, help="Path to write tab_exp2_outline_h4.tex")
    args = parser.parse_args(argv)

    tex = """% Auto-generated - Exp2 outline placeholder
\\begin{table}[h]
\\centering
\\caption{H4 placeholder: naive bounce rate and Wilson upper bound}\\label{tab:exp2-outline-h4}
\\begin{tabular}{lll}
\\toprule
Agent & Bounce rate & Wilson upper bound \\\\
\\midrule
Qwen & <to fill> & <to fill> \\\\
GPT-5.5 & <to fill> & <to fill> \\\\
Mistral & <to fill> & <to fill> \\\\
Claude & <to fill> & <to fill> \\\\
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
