"""Ticket 0544 — validate the rapidfuzz partial_ratio matcher threshold.

The LP matcher (``matching/lp.py``) accepts a fuzzy match when
``fuzz.partial_ratio(name_a, name_b) >= 90``. On phase-named plants
(Vũng Áng 1 vs Vũng Áng 2) partial_ratio is structurally high across phases,
so the raw threshold is exposed to cross-phase false matches. The LP also
carries a unit-number veto (lp.py:203–208): when both names have digit tokens
and they differ, the pair's cost is set above the leave-unmatched cost, making
cross-phase assignment structurally impossible.

This script measures, on the adopted reference, three layers of that exposure:

1. **Structural false-match set** — all pairs of distinct reference plants with
   ``partial_ratio >= threshold`` (raw exposure of the threshold itself).
2. **Veto-blocked subset** — pairs the unit-number veto excludes; the
   complement is the **residual exposure** the LP could actually pick.
3. **Realised rate** — from the committed threshold sweep
   (``experiments/derived/matching_sensitivity.csv``): mean F1 and total
   ``n_fuzzy_below`` per threshold in {85, 90, 95}.

Outputs (cited by the source-concordance caveat in the manuscript):
  - report/inputs/generated/tab_phase_collisions.csv
  - report/inputs/generated/macros_phase_collisions.tex
"""

import argparse
import csv
import logging
from pathlib import Path

from rapidfuzz import fuzz, process

from aedist.config import VN_THERMAL_PLANTS_RELEASE_CSV
from aedist.evaluate import load_plants_csv
from aedist.matching.lp import ambiguous_phase_bases, digit_veto
from aedist.reconcile import plants_to_dataframe

log = logging.getLogger(__name__)

THRESHOLDS = (85, 90, 95)

DEFAULT_SENSITIVITY_CSV = Path("experiments/derived/matching_sensitivity.csv")
DEFAULT_OUTPUT_CSV = Path("report/inputs/generated/tab_phase_collisions.csv")
DEFAULT_OUTPUT_MACROS = Path("report/inputs/generated/macros_phase_collisions.tex")


def _veto_blocked(name_a: str, name_b: str, ambiguous: frozenset[str]) -> bool:
    """True when the LP unit-number veto fires for this pair.

    Reuses the LP's own ``digit_veto`` (ticket 0551): both names carry
    differing digit-token sets, or exactly one side carries digits, the
    digit-stripped names are near-identical, and the base is phase-ambiguous.
    """
    return digit_veto(name_a, name_b, ambiguous)


def reference_names_clean(reference: Path = VN_THERMAL_PLANTS_RELEASE_CSV) -> list[str]:
    """Distinct matcher-side cleaned names of the reference plants.

    Uses the exact pipeline the matcher sees: ``load_plants_csv`` →
    ``plants_to_dataframe`` (cleaner + single-unit suffix stripping), so the
    measured exposure is the matcher's, not a re-implementation's.
    """
    df = plants_to_dataframe(load_plants_csv(reference))
    return sorted(set(df["name_clean"].astype(str)))


def structural_false_matches(
    threshold: int = 90, reference: Path = VN_THERMAL_PLANTS_RELEASE_CSV
) -> dict[tuple[str, str], tuple[float, bool]]:
    """Pairs of distinct reference plants with partial_ratio >= threshold.

    Returns ``{(name_a, name_b): (partial_ratio, veto_blocked)}`` with names
    in sorted order; the score is the cdist one used for selection.
    """
    names = reference_names_clean(reference)
    ambiguous = ambiguous_phase_bases(names)
    scores = process.cdist(names, names, scorer=fuzz.partial_ratio)
    pairs: dict[tuple[str, str], tuple[float, bool]] = {}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if scores[i][j] >= threshold:
                pairs[(names[i], names[j])] = (
                    float(scores[i][j]),
                    _veto_blocked(names[i], names[j], ambiguous),
                )
    return pairs


def sensitivity_summary(sensitivity_csv: Path) -> dict[int, dict[str, float]]:
    """Per-threshold mean F1 and total n_fuzzy_below from the committed sweep."""
    with sensitivity_csv.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    out: dict[int, dict[str, float]] = {}
    for t in THRESHOLDS:
        at_t = [r for r in rows if int(r["threshold"]) == t]
        assert at_t, f"no rows at threshold {t} in {sensitivity_csv}"
        f1s = [float(r["f1"]) for r in at_t]
        out[t] = {
            "mean_f1": sum(f1s) / len(f1s),
            "n_fuzzy_below": sum(int(r["n_fuzzy_below"]) for r in at_t),
            "n_runs": len(at_t),
        }
    return out


def write_csv(
    by_threshold: dict[int, dict[tuple[str, str], tuple[float, bool]]], output: Path
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["name_a", "name_b", "partial_ratio", "threshold", "veto_blocked"])
        for t in THRESHOLDS:
            for (a, b), (score, blocked) in sorted(by_threshold[t].items()):
                w.writerow([a, b, round(score, 1), t, blocked])
    log.info("Wrote phase-collision pairs to %s", output)


def write_macros(
    by_threshold: dict[int, dict[tuple[str, str], tuple[float, bool]]],
    sens: dict[int, dict[str, float]],
    output: Path,
) -> None:
    pairs_90 = by_threshold[90]
    n_blocked_90 = sum(1 for _, blocked in pairs_90.values() if blocked)
    f1_drop = sens[90]["mean_f1"] - sens[95]["mean_f1"]
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "% Auto-generated by aedist.analyze_matcher_phase_collisions — do not edit.",
        f"\\newcommand{{\\PhaseCollisionPairsNinety}}{{{len(pairs_90)}}}",
        f"\\newcommand{{\\PhaseCollisionVetoBlockedNinety}}{{{n_blocked_90}}}",
        f"\\newcommand{{\\PhaseCollisionResidualNinety}}{{{len(pairs_90) - n_blocked_90}}}",
        f"\\newcommand{{\\PhaseCollisionPairsEightyFive}}{{{len(by_threshold[85])}}}",
        f"\\newcommand{{\\PhaseCollisionPairsNinetyFive}}{{{len(by_threshold[95])}}}",
        f"\\newcommand{{\\RealisedFuzzyBelowNinety}}{{{int(sens[90]['n_fuzzy_below'])}}}",
        "% Mean-F1 drop from threshold 90 to 95, averaged over the "
        f"{int(sens[90]['n_runs'])} runs at each threshold in "
        "matching_sensitivity.csv; not yet cited in the manuscript — "
        "defined for future citation.",
        f"\\newcommand{{\\ThresholdSensFOneDropNinetyFive}}{{{f1_drop:.3f}}}",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("Wrote phase-collision macros to %s", output)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Measure the structural cross-phase false-match exposure of the "
        "partial_ratio matcher threshold on the reference (ticket 0544)"
    )
    parser.add_argument("--reference", type=Path, default=VN_THERMAL_PLANTS_RELEASE_CSV)
    parser.add_argument("--sensitivity", type=Path, default=DEFAULT_SENSITIVITY_CSV)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--output-macros", type=Path, default=DEFAULT_OUTPUT_MACROS)
    args = parser.parse_args(argv)

    by_threshold = {
        t: structural_false_matches(threshold=t, reference=args.reference)
        for t in THRESHOLDS
    }
    sens = sensitivity_summary(args.sensitivity)

    write_csv(by_threshold, args.output_csv)
    write_macros(by_threshold, sens, args.output_macros)

    for t in THRESHOLDS:
        pairs = by_threshold[t]
        n_blocked = sum(1 for _, blocked in pairs.values() if blocked)
        log.info(
            "t=%d: %d structural pairs (%d veto-blocked, %d residual); "
            "mean_f1=%.4f, n_fuzzy_below=%d over %d runs",
            t,
            len(pairs),
            n_blocked,
            len(pairs) - n_blocked,
            sens[t]["mean_f1"],
            int(sens[t]["n_fuzzy_below"]),
            int(sens[t]["n_runs"]),
        )


if __name__ == "__main__":
    main()
