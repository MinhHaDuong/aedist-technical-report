"""Generate the Exp2 recognition matrix figures — one per arm (four total).

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.

Produces one boolean coverage heatmap per Exp2 arm (``naive``, ``optimised``,
``arm3``, ``arm4``).  Each figure uses the same layout as the Exp1 matrix
(ticket 0446): reference plants as columns ordered by status group then
capacity descending, model+run combinations as rows, with a false-positive
panel on the left.

Derivation routes through ``aedist.exp2_recognition`` (mart-layer loader) and
the shared renderer ``aedist.plot_exp1_matrix.render_recognition_matrix``.  No
intermediate CSV is emitted — consistency by common cause with the mart's stored
coverage metrics (DAG rule 0436: no P3→P3 side-output edges).

These are exploration artifacts (ticket 0449): wired into ``chart-figures`` but
not yet referenced by the manuscript.  Author placement decision is deferred.

Macro collision prevention: the four arm figures use arm-namespaced macro
prefixes (``ExpTwoNaiveMatrix``, etc.) so they can be \\input'd together without
duplicate-command errors, even though they are not yet in the manuscript.

Usage:
    uv run python -m aedist.plot_exp2_matrix \\
        --mart-jsonl experiments/derived/exp2_mart.jsonl \\
        --arm naive \\
        --output report/inputs/generated/fig_exp2_recognition_matrix_naive.pdf
"""

import argparse
import logging
from pathlib import Path

from .config import VN_THERMAL_PLANTS_RELEASE_CSV
from .exp2_recognition import load_exp2_recognition
from .plot_exp1_matrix import render_recognition_matrix

log = logging.getLogger(__name__)

# Arm → human-readable display name used in the super-title.
_ARM_DISPLAY: dict[str, str] = {
    "naive": "naive (arm 1)",
    "optimised": "optimised (arm 2)",
    "arm3": "arm 3",
    "arm4": "arm 4",
}

# Arm → LaTeX macro prefix (avoid duplicate-command collisions).
_ARM_MACRO_PREFIX: dict[str, str] = {
    "naive": "ExpTwoNaiveMatrix",
    "optimised": "ExpTwoOptMatrix",
    "arm3": "ExpTwoArmThreeMatrix",
    "arm4": "ExpTwoArmFourMatrix",
}


def write_pdf(
    mart_jsonl: Path,
    reference_path: Path,
    arm: str,
    output: Path,
    output_macros: Path | None = None,
    fp_top_n: int = 40,
    fp_seed: int = 42,
    cell_size: float = 0.11,
    ui_scale: float = 1.0,
    page_aspect: float = 1.7,
    lang: str = "en",
    repo_root: Path | None = None,
) -> None:
    """Render the Exp2 recognition matrix for one arm as a PDF (and optional macros).

    Args:
        mart_jsonl: Path to the Exp2 mart JSONL (P2 outcome).
        reference_path: Gold reference CSV.
        arm: One of ``naive``, ``optimised``, ``arm3``, ``arm4``.
        output: Output PDF path.
        output_macros: Optional ``.tex`` macros file (plant/run/FP counts).
        fp_top_n: Number of top false positives to show.
        fp_seed: Tie-breaking seed for FP selection.
        cell_size: Inches per column (controls figure width).
        ui_scale: Global font/size scale.
        page_aspect: Figure width/height ratio.
        lang: Band label language: ``en`` (default) or ``fr``.
        repo_root: Repository root for resolving mart artifact pointers;
            defaults to the current working directory.
    """
    resolved_root = repo_root if repo_root is not None else Path(".")
    data = load_exp2_recognition(
        mart_jsonl=mart_jsonl,
        reference_path=reference_path,
        repo_root=resolved_root,
        arm=arm,
    )
    if not data.cells:
        log.warning("No recognition data for arm=%r in mart %s — skipping", arm, mart_jsonl)
        return

    arm_label = _ARM_DISPLAY.get(arm, arm)
    suptitle = f"Which Vietnamese thermal assets does each model recognize? (Exp 2, {arm_label})"
    macros_prefix = _ARM_MACRO_PREFIX.get(arm, f"ExpTwo{arm.capitalize()}Matrix")

    render_recognition_matrix(
        data=data,
        output=output,
        output_macros=output_macros,
        fp_top_n=fp_top_n,
        fp_seed=fp_seed,
        cell_size=cell_size,
        ui_scale=ui_scale,
        page_aspect=page_aspect,
        lang=lang,
        suptitle=suptitle,
        macros_prefix=macros_prefix,
    )


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Generate an Exp2 recognition matrix figure for one arm (boolean heatmap)"
    )
    parser.add_argument(
        "--mart-jsonl",
        type=Path,
        default=Path("experiments/derived/exp2_mart.jsonl"),
        help="Exp2 mart JSONL (P2 outcome, default: experiments/derived/exp2_mart.jsonl)",
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=VN_THERMAL_PLANTS_RELEASE_CSV,
        help="Reference CSV (gold list); read at build time, no hardcoded count",
    )
    parser.add_argument(
        "--arm",
        required=True,
        choices=["naive", "optimised", "arm3", "arm4"],
        help="Exp2 arm to render",
    )
    parser.add_argument("--output", type=Path, required=True, help="Output PDF path")
    parser.add_argument(
        "--output-macros",
        type=Path,
        default=None,
        help="Optional .tex macros file (plant/run/FP counts, arm-namespaced)",
    )
    parser.add_argument("--fp-top-n", type=int, default=40, help="Top-N false positives to show")
    parser.add_argument(
        "--fp-seed", type=int, default=42, help="Seed for FP tie-breaking (rebuild-stable)"
    )
    parser.add_argument("--ui-scale", type=float, default=1.0, help="Global font/size scale")
    parser.add_argument(
        "--page-aspect",
        type=float,
        default=1.7,
        help="Figure width/height ratio; default matches a full landscape A4 page",
    )
    parser.add_argument(
        "--lang",
        choices=["en", "fr"],
        default="en",
        help="Band label language: en for the preprint (default), fr for the report annex",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root for resolving mart artifact pointers (default: cwd)",
    )
    args = parser.parse_args(argv)

    write_pdf(
        mart_jsonl=args.mart_jsonl,
        reference_path=args.reference,
        arm=args.arm,
        output=args.output,
        output_macros=args.output_macros,
        fp_top_n=args.fp_top_n,
        fp_seed=args.fp_seed,
        ui_scale=args.ui_scale,
        page_aspect=args.page_aspect,
        lang=args.lang,
        repo_root=args.repo_root,
    )


if __name__ == "__main__":
    main()
