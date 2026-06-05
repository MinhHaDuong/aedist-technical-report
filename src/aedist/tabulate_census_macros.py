"""Write the census macros (.tex) from measurements.jsonl.

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.

Table half of the census artifacts: it emits only the ``macros_census.tex``
LaTeX include (``\\NumCensusModels``, ``\\CensusTPMin`` …). Before ticket 0436
these macros were harvested as a side-output of ``plot_method_convergence``,
which was invoked purely to dump them while discarding its PDF to a sentinel
path — a figure script run only to produce a table side-output. This module
imports the shared derivation (:func:`aedist.plot_method_convergence.load_convergence_data`
and :func:`aedist.plot_method_convergence._build_macros`) and emits the macros
directly, so no figure script is invoked to harvest a table.

The macro counts (\\NumCensusModels, \\CensusTP*/\\CensusFP* …) are computed over
the records selected by ``--prompt-version`` / ``--result-dir`` — the same set
``plot_method_convergence._build_macros`` saw. ``load_convergence_data`` already
restricts to the four convergence methods (``direct``, ``direct+multiturn``,
``rag_livesearch``, ``rag``); the historical ``--methods direct`` flag only
narrowed the *figure's* method bands, never the macro counts, so it is not
replayed here.

Usage::

    uv run python -m aedist.tabulate_census_macros \\
        --output report/inputs/generated/macros_census.tex \\
        --prompt-version census
"""

import argparse
import logging
from pathlib import Path

from .plot_method_convergence import _build_macros, load_convergence_data

log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Write the census macros (.tex) from measurements.jsonl",
    )
    parser.add_argument("--output", required=True, help="Path to write macros_census.tex")
    parser.add_argument(
        "--prompt-version",
        default=None,
        help="Filter to a single prompt_version (e.g. census, p1_base)",
    )
    parser.add_argument(
        "--result-dir",
        default=None,
        help="Only include records whose result_file starts with this prefix",
    )
    parser.add_argument(
        "--exclude-models",
        default=None,
        help="Comma-separated normalized model names to exclude",
    )
    args = parser.parse_args()

    excluded_models = None
    if args.exclude_models:
        excluded_models = {m.strip() for m in args.exclude_models.split(",") if m.strip()}

    rows = load_convergence_data(
        prompt_version=args.prompt_version,
        result_dir=args.result_dir,
        excluded_models=excluded_models,
    )

    tex = _build_macros(
        rows,
        prompt_version=args.prompt_version,
        result_dir=args.result_dir,
        excluded_models=excluded_models,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(tex)
    log.info("Wrote %s", output_path)


if __name__ == "__main__":
    main()
