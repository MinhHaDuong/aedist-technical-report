"""Generate dataset figure placeholder for Exp2 outline.

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.
"""

import argparse
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def main(argv: list[str] | None = None):
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Generate Exp2 outline dataset figure placeholder")
    parser.add_argument("--output", required=True, help="Path to write fig_exp2_outline_dataset.tex")
    args = parser.parse_args(argv)

    tex = """% Auto-generated - Exp2 outline placeholder
\\begin{figure}[h]
\\centering
\\fbox{\\parbox{0.9\\linewidth}{\\centering Placeholder figure: Exp2 dataset coverage and quality availability by arm/model.}}
\\caption{Exp2 dataset overview (placeholder)}\\label{fig:exp2-outline-dataset}
\\end{figure}
"""
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(tex)
    log.info("Wrote %s", output)


if __name__ == "__main__":
    main()
