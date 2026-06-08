#!/usr/bin/env python3
"""Sweep matching similarity thresholds across reconciliation CSVs.

Reads existing reconciliation CSVs (which may contain a similarity_score
column) and for each threshold in [75, 80, 85, 88, 90, 92, 95], re-classifies
fuzzy matches below that threshold as unmatched. Computes TP/FP/FN/F1 from
the filtered entries -- no MILP re-run, pure post-hoc arithmetic.

Output: derived/matching_sensitivity.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import warnings
from collections import defaultdict
from itertools import combinations
from pathlib import Path

THRESHOLDS = [75, 80, 85, 88, 90, 92, 95]

# Match types that count as "matched" (true positives)
MATCHED_TYPES = {"exact", "exact_capacity_diff", "fuzzy", "fuzzy_capacity_diff"}
# Match types that are fuzzy (subject to threshold filtering)
FUZZY_TYPES = {"fuzzy", "fuzzy_capacity_diff"}


def _parse_float(val: str) -> float | None:
    """Parse a float from CSV string, returning None for empty/invalid."""
    if not val or val.strip() == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _parse_reconciliation_csv(path: Path) -> list[dict]:
    """Read a reconciliation CSV into a list of row dicts."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _parse_filename(path: Path) -> tuple[str, str, str]:
    """Extract (model, method, run) from reconciliation filename and parent dir.

    Expected pattern: reconciliation_{model}-run{N}.csv
    Parent directory name is the method (e.g., 'census', 'rag').
    """
    stem = path.stem  # e.g. reconciliation_gpt-5.4-run1
    name = stem.replace("reconciliation_", "")

    # Extract run number
    run_match = re.search(r"-run(\d+)$", name)
    if run_match:
        run = run_match.group(1)
        model = name[: run_match.start()]
    else:
        run = "1"
        model = name

    method = path.parent.name
    return model, method, run


def _compute_metrics_at_threshold(
    rows: list[dict], threshold: int
) -> dict[str, float | int]:
    """Compute metrics after filtering fuzzy matches below threshold.

    For each row:
    - If match_type is fuzzy and similarity_score < threshold:
      demote to unmatched (creates one FN + one FP instead of one TP).
    - Exact matches are never demoted.
    - reference_only = FN, system_only = FP, matched = TP.

    Returns dict with: f1, precision, coverage, n_matched, n_fuzzy_above, n_fuzzy_below
    """
    tp = 0
    fp = 0
    fn = 0
    n_fuzzy_above = 0
    n_fuzzy_below = 0

    for row in rows:
        mt = row.get("match_type", "")
        score = _parse_float(row.get("similarity_score", ""))

        if mt in FUZZY_TYPES and score is None:
            warnings.warn(
                f"Fuzzy row missing similarity_score: {row.get('reference_name', '?')} "
                f"-- threshold sweep will treat it as above every threshold (flat F1)",
                stacklevel=2,
            )

        if mt in FUZZY_TYPES and score is not None and score < threshold:
            # Demote: this fuzzy match is below the threshold
            # It becomes one missed reference (FN) + one hallucinated system (FP)
            fn += 1
            fp += 1
            n_fuzzy_below += 1
        elif mt in MATCHED_TYPES:
            tp += 1
            if mt in FUZZY_TYPES:
                n_fuzzy_above += 1
        elif mt == "reference_only":
            fn += 1
        elif mt == "system_only":
            fp += 1

    # Compute derived metrics
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    total_ref = tp + fn  # total reference entries
    coverage = tp / total_ref if total_ref > 0 else 0.0

    return {
        "f1": round(f1, 4),
        "precision": round(precision, 4),
        "coverage": round(coverage, 4),
        "n_matched": tp,
        "n_fuzzy_above": n_fuzzy_above,
        "n_fuzzy_below": n_fuzzy_below,
    }


def sweep_thresholds(
    recon_root: Path,
    output_path: Path,
) -> dict:
    """Run the threshold sweep over all reconciliation CSVs under recon_root.

    Writes two files:
    - output_path: matching_sensitivity.csv (per-model, per-threshold metrics)
    - output_path.parent / matching_stability.json (rank flips, slopes, stable core)

    Args:
        recon_root: Root directory containing reconciliation CSVs (searched recursively).
        output_path: Path to write matching_sensitivity.csv.

    Returns:
        Stability analysis dict with keys: rank_flips, slopes, stable_core.
    """
    # Find all reconciliation CSVs
    recon_files = sorted(recon_root.rglob("reconciliation_*.csv"))
    if not recon_files:
        raise FileNotFoundError(f"No reconciliation CSVs found under {recon_root}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    for recon_path in recon_files:
        model, method, run = _parse_filename(recon_path)
        rows = _parse_reconciliation_csv(recon_path)

        for threshold in THRESHOLDS:
            metrics = _compute_metrics_at_threshold(rows, threshold)
            results.append({
                "model": model,
                "method": method,
                "run": run,
                "threshold": threshold,
                **metrics,
            })

    # Write output CSV
    fieldnames = [
        "model", "method", "run", "threshold",
        "f1", "precision", "coverage",
        "n_matched", "n_fuzzy_above", "n_fuzzy_below",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    # Stability analysis
    stability = _compute_stability(results)

    # Write stability JSON
    stability_path = output_path.parent / "matching_stability.json"
    with open(stability_path, "w", encoding="utf-8") as f:
        json.dump(stability, f, indent=2)
        f.write("\n")

    # Print summary
    _print_stability_summary(stability)

    return stability


def _compute_stability(results: list[dict]) -> dict:
    """Compute rank stability, per-model F1 slopes, and stable core.

    Returns dict with:
    - rank_flips: list of {method, model_1, model_2} where rankings invert
    - slopes: list of {method, model, f1_slope} (F1 change per threshold unit)
    - stable_core: list of models whose rankings never flip
    """
    # Group by (method, model) -> {threshold: [f1 values across runs]}
    method_model_f1: dict[str, dict[str, dict[int, list[float]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )

    for r in results:
        t = int(r["threshold"])
        if 75 <= t <= 95:
            method_model_f1[r["method"]][r["model"]][t].append(float(r["f1"]))

    # Rank flips
    flips: list[dict[str, str]] = []
    for method, models in method_model_f1.items():
        model_names = sorted(models.keys())
        for m1, m2 in combinations(model_names, 2):
            m1_means = {t: sum(vs) / len(vs) for t, vs in models[m1].items()}
            m2_means = {t: sum(vs) / len(vs) for t, vs in models[m2].items()}

            common_thresholds = sorted(set(m1_means) & set(m2_means))
            if len(common_thresholds) < 2:
                continue

            signs = []
            for t in common_thresholds:
                diff = m1_means[t] - m2_means[t]
                signs.append(1 if diff > 0 else (-1 if diff < 0 else 0))

            nonzero = [s for s in signs if s != 0]
            if len(set(nonzero)) > 1:
                flips.append({"method": method, "model_1": m1, "model_2": m2})

    # Per-model slopes (linear regression of mean F1 vs threshold)
    slopes: list[dict] = []
    for method, models in method_model_f1.items():
        for model, threshold_f1s in models.items():
            mean_f1s = {t: sum(vs) / len(vs) for t, vs in threshold_f1s.items()}
            thresholds = sorted(mean_f1s.keys())
            if len(thresholds) < 2:
                slopes.append({
                    "method": method,
                    "model": model,
                    "f1_slope": 0.0,
                })
                continue

            # Simple linear regression: slope = cov(x,y) / var(x)
            xs = [float(t) for t in thresholds]
            ys = [mean_f1s[t] for t in thresholds]
            x_mean = sum(xs) / len(xs)
            y_mean = sum(ys) / len(ys)
            cov_xy = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys, strict=True))
            var_x = sum((x - x_mean) ** 2 for x in xs)
            slope = round(cov_xy / var_x, 6) if var_x > 0 else 0.0
            slopes.append({
                "method": method,
                "model": model,
                "f1_slope": slope,
            })

    # Stable core: models not involved in any rank flip
    all_models = set()
    for models in method_model_f1.values():
        all_models.update(models.keys())

    flipping_models = set()
    for f in flips:
        flipping_models.add(f["model_1"])
        flipping_models.add(f["model_2"])

    stable_core = sorted(all_models - flipping_models)

    return {
        "rank_flips": flips,
        "slopes": slopes,
        "stable_core": stable_core,
    }


def _print_stability_summary(stability: dict) -> None:
    """Print a human-readable summary of stability analysis."""
    flips = stability["rank_flips"]
    slopes = stability["slopes"]
    stable_core = stability["stable_core"]

    if flips:
        print(f"\nRank flips detected ({len(flips)} model pairs):")
        for f in flips[:10]:
            print(f"  {f['method']}: {f['model_1']} vs {f['model_2']}")
    else:
        print("\nNo rank flips detected across thresholds [75, 95].")

    if slopes:
        print("\nF1 sensitivity (slope per threshold unit):")
        sorted_slopes = sorted(slopes, key=lambda s: abs(s["f1_slope"]), reverse=True)
        for s in sorted_slopes[:10]:
            print(f"  {s['method']}/{s['model']}: {s['f1_slope']:+.6f}")

    if stable_core:
        print(f"\nStable core ({len(stable_core)} models): {', '.join(stable_core)}")
    else:
        print("\nNo models in stable core (all involved in rank flips).")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Sweep matching thresholds across reconciliation CSVs"
    )
    parser.add_argument(
        "--recon-root",
        type=Path,
        default=Path("experiments/outputs"),
        help="Root directory containing reconciliation CSVs",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("derived/matching_sensitivity.csv"),
        help="Output CSV path",
    )
    args = parser.parse_args()

    sweep_thresholds(recon_root=args.recon_root, output_path=args.output)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
