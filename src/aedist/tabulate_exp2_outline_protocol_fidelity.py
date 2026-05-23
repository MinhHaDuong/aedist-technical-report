"""Generate protocol-fidelity table placeholder for Exp2 outline."""

import argparse
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def main(argv: list[str] | None = None):
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Generate Exp2 protocol-fidelity placeholder")
    parser.add_argument("--output", required=True, help="Path to write tab_exp2_outline_protocol_fidelity.tex")
    args = parser.parse_args(argv)

    tex = """% Auto-generated - Exp2 outline placeholder
\\begin{table}[h]
\\centering
\\caption{Exp2 protocol-fidelity matrix (placeholder)}\\label{tab:exp2-outline-protocol-fidelity}
\\begin{tabular}{lll}
\\toprule
Commitment & Status & Evidence path \\\\
\\midrule
Two-arm design (N=5/model/arm) & <to fill> & <to fill> \\\\
Operational metrics tabulated & <to fill> & <to fill> \\\\
Quality metrics integrated & <to fill> & <to fill> \\\\
Compliance audit integrated & <to fill> & <to fill> \\\\
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
