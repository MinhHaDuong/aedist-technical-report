"""Joint robustness summary combining variance decomposition and threshold sensitivity.

Produces a LaTeX-ready paragraph for the methodology section summarizing
how robust the measured F1 rankings are.

Usage::

    from aedist.analyze_robustness import analyze_robustness
    result = analyze_robustness(decomposition_result, threshold_sensitivity)
"""

from __future__ import annotations


def analyze_robustness(
    decomposition: dict,
    threshold_sensitivity: dict | None = None,
) -> dict:
    """Combine variance decomposition with threshold sensitivity into a summary.

    Args:
        decomposition: Output of ``variance_decomposition()``.
        threshold_sensitivity: Output of threshold sensitivity analysis
            (from ticket 0035), or None if not available.

    Returns:
        Dict with ``summary`` (LaTeX paragraph), ``n_unstable_pairs``,
        and ``measurement_dependent_rankings`` list.
    """
    eta_resid = decomposition.get("eta_sq_residual", 0.0)
    eta_model = decomposition.get("eta_sq_model", 0.0)
    eta_method = decomposition.get("eta_sq_method", 0.0)
    unstable_pairs = decomposition.get("unstable_pairs", [])
    n_unstable = len(unstable_pairs)

    # Build the LaTeX paragraph
    parts: list[str] = []

    if eta_resid < 0.10:
        parts.append(
            f"Run-to-run variance explains less than 10\\% of F1 differences "
            f"($\\eta^2_{{\\mathrm{{resid}}}} = {eta_resid:.2f}$), "
            f"indicating that rankings are stable across repetitions."
        )
    else:
        parts.append(
            f"Run-to-run noise accounts for {eta_resid * 100:.0f}\\% of F1 variance "
            f"($\\eta^2_{{\\mathrm{{resid}}}} = {eta_resid:.2f}$); "
            f"caution is warranted when interpreting small ranking differences."
        )

    parts.append(
        f"Method choice explains {eta_method * 100:.0f}\\% "
        f"($\\eta^2_{{\\mathrm{{method}}}} = {eta_method:.2f}$) "
        f"and model choice {eta_model * 100:.0f}\\% "
        f"($\\eta^2_{{\\mathrm{{model}}}} = {eta_model:.2f}$) of the total variance."
    )

    # Flag measurement-dependent rankings
    measurement_dependent: list[dict] = []

    if n_unstable > 0:
        pair_strs = [
            f"{p['model_a']} vs.\\ {p['model_b']} "
            f"($\\Delta$F1$={p['f1_diff']:.2f}$)"
            for p in unstable_pairs[:5]  # cap at 5 for readability
        ]
        parts.append(
            f"{n_unstable} model pair{'s' if n_unstable != 1 else ''} "
            f"show{'s' if n_unstable == 1 else ''} overlapping bootstrap confidence intervals "
            f"with mean F1 differences below 5~pp: {'; '.join(pair_strs)}."
        )

    # Cross-reference with threshold sensitivity if available
    if threshold_sensitivity is not None:
        flipped = threshold_sensitivity.get("rank_flips", [])
        for pair in unstable_pairs:
            for flip in flipped:
                if (
                    {pair["model_a"], pair["model_b"]}
                    == {flip.get("model_a", ""), flip.get("model_b", "")}
                ):
                    measurement_dependent.append({
                        "model_a": pair["model_a"],
                        "model_b": pair["model_b"],
                        "reason": "CI overlap + rank flip under threshold change",
                    })

        if measurement_dependent:
            parts.append(
                f"{len(measurement_dependent)} ranking{'s' if len(measurement_dependent) != 1 else ''} "
                f"{'are' if len(measurement_dependent) != 1 else 'is'} "
                f"measurement-dependent (overlapping CIs and rank reversal under "
                f"matching threshold perturbation)."
            )

    summary = " ".join(parts)

    return {
        "summary": summary,
        "n_unstable_pairs": n_unstable,
        "measurement_dependent_rankings": measurement_dependent,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """Generate robustness summary from variance decomposition output."""
    import argparse
    import json
    import logging
    from pathlib import Path

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    log = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Generate robustness summary")
    parser.add_argument(
        "--decomposition",
        default="derived/variance_decomposition.json",
        help="Path to variance decomposition JSON",
    )
    parser.add_argument(
        "--threshold-sensitivity",
        default=None,
        help="Path to threshold sensitivity JSON (from ticket 0035)",
    )
    parser.add_argument(
        "--output",
        default="derived/robustness_summary.json",
        help="Path to write output JSON",
    )
    args = parser.parse_args(argv)

    decomp_path = Path(args.decomposition)
    decomposition = json.loads(decomp_path.read_text())

    threshold_sensitivity = None
    if args.threshold_sensitivity:
        ts_path = Path(args.threshold_sensitivity)
        if ts_path.exists():
            threshold_sensitivity = json.loads(ts_path.read_text())

    result = analyze_robustness(decomposition, threshold_sensitivity)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n")
    log.info("Wrote %s", output_path)


if __name__ == "__main__":
    main()
