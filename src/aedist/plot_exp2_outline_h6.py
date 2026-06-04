"""Generate H6 figure placeholder for Exp2 outline.

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.
"""

import argparse
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def main(argv: list[str] | None = None):
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Generate Exp2 H6 placeholder figure")
    parser.add_argument("--output", required=True, help="Path to write fig_exp2_outline_h6.tex")
    args = parser.parse_args(argv)

    tex = """% Auto-generated - Exp2 outline placeholder
\\begin{figure}[h]
\\centering
\\fbox{\\parbox{0.9\\linewidth}{\\centering Placeholder figure: rank-agreement scatter or heatmap between Phase C and mechanical metrics.}}
\\caption{H6 placeholder visualisation}\\label{fig:exp2-outline-h6}
\\end{figure}
"""
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(tex)
    log.info("Wrote %s", output)


if __name__ == "__main__":
    main()
