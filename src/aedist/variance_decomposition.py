"""Variance decomposition of F1 scores via two-way ANOVA.

Computes eta-squared for model, method, interaction, and residual
effects on F1 variance.  Uses only stdlib — no scipy, no numpy.

The balanced design requires equal cell sizes.  For the main analysis
this is 5 models x 4 methods x 3 replicates = 60 records (the
``decomposed`` method is excluded because deepseek lacks it).

Usage::

    from aedist.variance_decomposition import variance_decomposition
    result = variance_decomposition(records)
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .schema import RunRecord
from .stats import bootstrap_ci


# ---------------------------------------------------------------------------
# Two-way ANOVA (balanced, fixed effects, stdlib only)
# ---------------------------------------------------------------------------


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def two_way_anova(
    data: dict[tuple[str, str], list[float]],
) -> dict[str, float]:
    """Compute Type-I sums of squares for a balanced two-way design.

    *data* maps ``(factor_a, factor_b) -> [y values]``.  All cells must
    have the same number of replicates.

    Returns dict with keys: ss_a, ss_b, ss_ab, ss_resid, ss_total,
    df_a, df_b, df_ab, df_resid, df_total, eta_sq_a, eta_sq_b,
    eta_sq_ab, eta_sq_resid.
    """
    # Discover factor levels
    levels_a: set[str] = set()
    levels_b: set[str] = set()
    for a, b in data:
        levels_a.add(a)
        levels_b.add(b)
    a_levels = sorted(levels_a)
    b_levels = sorted(levels_b)

    a_count = len(a_levels)
    b_count = len(b_levels)

    # Cell sizes — must be balanced
    cell_sizes = {k: len(v) for k, v in data.items()}
    n = next(iter(cell_sizes.values()))
    if not all(s == n for s in cell_sizes.values()):
        msg = f"Unbalanced design: cell sizes = {cell_sizes}"
        raise ValueError(msg)

    N = a_count * b_count * n  # total observations

    # Grand mean
    all_values = [y for ys in data.values() for y in ys]
    grand_mean = _mean(all_values)

    # Row (factor A) means
    row_means: dict[str, float] = {}
    for a in a_levels:
        vals = [y for b in b_levels for y in data[(a, b)]]
        row_means[a] = _mean(vals)

    # Column (factor B) means
    col_means: dict[str, float] = {}
    for b in b_levels:
        vals = [y for a in a_levels for y in data[(a, b)]]
        col_means[b] = _mean(vals)

    # Cell means
    cell_means: dict[tuple[str, str], float] = {}
    for a in a_levels:
        for b in b_levels:
            cell_means[(a, b)] = _mean(data[(a, b)])

    # Sums of squares
    ss_a = b_count * n * sum((row_means[a] - grand_mean) ** 2 for a in a_levels)
    ss_b = a_count * n * sum((col_means[b] - grand_mean) ** 2 for b in b_levels)

    ss_ab = n * sum(
        (cell_means[(a, b)] - row_means[a] - col_means[b] + grand_mean) ** 2
        for a in a_levels
        for b in b_levels
    )

    ss_resid = sum(
        (y - cell_means[(a, b)]) ** 2
        for (a, b), ys in data.items()
        for y in ys
    )

    ss_total = sum((y - grand_mean) ** 2 for y in all_values)

    # Degrees of freedom
    df_a = a_count - 1
    df_b = b_count - 1
    df_ab = df_a * df_b
    df_resid = N - a_count * b_count
    df_total = N - 1

    # Eta-squared (proportion of total variance)
    eta_sq_a = ss_a / ss_total if ss_total > 0 else 0.0
    eta_sq_b = ss_b / ss_total if ss_total > 0 else 0.0
    eta_sq_ab = ss_ab / ss_total if ss_total > 0 else 0.0
    eta_sq_resid = ss_resid / ss_total if ss_total > 0 else 0.0

    return {
        "ss_a": ss_a,
        "ss_b": ss_b,
        "ss_ab": ss_ab,
        "ss_resid": ss_resid,
        "ss_total": ss_total,
        "df_a": df_a,
        "df_b": df_b,
        "df_ab": df_ab,
        "df_resid": df_resid,
        "df_total": df_total,
        "eta_sq_a": eta_sq_a,
        "eta_sq_b": eta_sq_b,
        "eta_sq_ab": eta_sq_ab,
        "eta_sq_resid": eta_sq_resid,
    }


# ---------------------------------------------------------------------------
# Unstable pair detection
# ---------------------------------------------------------------------------


def _find_unstable_pairs(
    records: list[RunRecord],
    threshold_pp: float = 5.0,
    seed: int = 42,
) -> list[dict]:
    """Find model pairs where mean F1 differs by <threshold_pp and CIs overlap."""
    # Group F1 values by model (across all methods)
    model_f1s: dict[str, list[float]] = defaultdict(list)
    for r in records:
        f1 = r.result_summary.f1
        if f1 is not None:
            model_f1s[r.method_params.model].append(f1)

    models = sorted(model_f1s.keys())
    unstable = []

    for i, m_a in enumerate(models):
        mean_a, lo_a, hi_a = bootstrap_ci(model_f1s[m_a], seed=seed)
        for m_b in models[i + 1 :]:
            mean_b, lo_b, hi_b = bootstrap_ci(model_f1s[m_b], seed=seed)

            f1_diff = abs(mean_a - mean_b)
            # CIs overlap if the lower bound of one is below the upper of the other
            ci_overlap = lo_a <= hi_b and lo_b <= hi_a

            if f1_diff < threshold_pp / 100 and ci_overlap:
                unstable.append({
                    "model_a": m_a,
                    "model_b": m_b,
                    "f1_diff": round(f1_diff, 4),
                    "ci_overlap": True,
                })

    return unstable


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def variance_decomposition(
    records: list[RunRecord],
    *,
    seed: int = 42,
) -> dict:
    """Run two-way ANOVA (model x method) on F1 scores from RunRecords.

    Filters to status=="ok" with non-null F1.  Groups by (model, method),
    keeping only cells with 3+ observations.  Then builds the largest
    balanced sub-design and runs the ANOVA.

    Returns a dict with eta-squared components and unstable pairs.
    """
    # Filter to ok records with F1
    ok_records = [
        r
        for r in records
        if r.result_summary.status == "ok" and r.result_summary.f1 is not None
    ]

    # Group by (model, method)
    cells: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in ok_records:
        key = (r.method_params.model, r.method)
        cells[key].append(r.result_summary.f1)

    # Find the minimum cell size across non-empty cells
    if not cells:
        return {
            "n_records": 0,
            "n_groups": 0,
            "eta_sq_model": 0.0,
            "eta_sq_method": 0.0,
            "eta_sq_interaction": 0.0,
            "eta_sq_residual": 0.0,
            "anova": {},
            "unstable_pairs": [],
        }

    # For a balanced design: find the largest balanced sub-design
    # First, find cells with enough replicates (>= min_reps)
    min_reps = min(len(v) for v in cells.values())
    if min_reps < 2:
        # Try keeping only cells with >= 2 replicates
        cells = {k: v for k, v in cells.items() if len(v) >= 2}
        if cells:
            min_reps = min(len(v) for v in cells.values())
        else:
            min_reps = 0

    if min_reps < 2:
        return {
            "n_records": len(ok_records),
            "n_groups": 0,
            "eta_sq_model": 0.0,
            "eta_sq_method": 0.0,
            "eta_sq_interaction": 0.0,
            "eta_sq_residual": 0.0,
            "anova": {},
            "unstable_pairs": _find_unstable_pairs(ok_records, seed=seed),
        }

    # Truncate all cells to min_reps for balance
    balanced: dict[tuple[str, str], list[float]] = {
        k: v[:min_reps] for k, v in cells.items()
    }

    # Find models and methods that form a complete cross
    models_in_cells: dict[str, set[str]] = defaultdict(set)
    methods_in_cells: dict[str, set[str]] = defaultdict(set)
    for m, method in balanced:
        models_in_cells[m].add(method)
        methods_in_cells[method].add(m)

    # Keep only models that appear in all methods and methods that appear in all models
    # Iteratively prune until stable
    all_methods = set(methods_in_cells.keys())
    all_models = set(models_in_cells.keys())

    changed = True
    while changed:
        changed = False
        new_models = {m for m in all_models if models_in_cells[m] >= all_methods}
        new_methods = {method for method in all_methods if methods_in_cells[method] >= all_models}
        if new_models != all_models or new_methods != all_methods:
            all_models = new_models
            all_methods = new_methods
            changed = True
            # Rebuild membership
            models_in_cells = defaultdict(set)
            methods_in_cells = defaultdict(set)
            for (m, method), v in balanced.items():
                if m in all_models and method in all_methods:
                    models_in_cells[m].add(method)
                    methods_in_cells[method].add(m)

    # Build the balanced data for ANOVA
    anova_data: dict[tuple[str, str], list[float]] = {}
    for (m, method), v in balanced.items():
        if m in all_models and method in all_methods:
            anova_data[(m, method)] = v

    n_groups = len(anova_data)

    if len(all_models) < 2 and len(all_methods) < 2:
        # Not enough factors for any ANOVA
        return {
            "n_records": len(ok_records),
            "n_groups": n_groups,
            "eta_sq_model": 0.0,
            "eta_sq_method": 0.0,
            "eta_sq_interaction": 0.0,
            "eta_sq_residual": 1.0 if n_groups > 0 else 0.0,
            "anova": {},
            "unstable_pairs": _find_unstable_pairs(ok_records, seed=seed),
        }

    if len(all_methods) < 2:
        # One-way ANOVA on model factor only
        all_values = [y for v in anova_data.values() for y in v]
        grand_mean = _mean(all_values)
        model_groups: dict[str, list[float]] = defaultdict(list)
        for (m, _method), v in anova_data.items():
            model_groups[m].extend(v)
        ss_model = sum(
            len(vals) * (_mean(vals) - grand_mean) ** 2
            for vals in model_groups.values()
        )
        ss_total = sum((y - grand_mean) ** 2 for y in all_values)
        ss_resid = ss_total - ss_model
        eta_model = ss_model / ss_total if ss_total > 0 else 0.0
        eta_resid = ss_resid / ss_total if ss_total > 0 else 0.0
        return {
            "n_records": len(ok_records),
            "n_groups": n_groups,
            "eta_sq_model": round(eta_model, 4),
            "eta_sq_method": 0.0,
            "eta_sq_interaction": 0.0,
            "eta_sq_residual": round(eta_resid, 4),
            "anova": {},
            "unstable_pairs": _find_unstable_pairs(ok_records, seed=seed),
        }

    if len(all_models) < 2:
        # One-way ANOVA on method factor only
        all_values = [y for v in anova_data.values() for y in v]
        grand_mean = _mean(all_values)
        method_groups: dict[str, list[float]] = defaultdict(list)
        for (_m, method), v in anova_data.items():
            method_groups[method].extend(v)
        ss_method = sum(
            len(vals) * (_mean(vals) - grand_mean) ** 2
            for vals in method_groups.values()
        )
        ss_total = sum((y - grand_mean) ** 2 for y in all_values)
        ss_resid = ss_total - ss_method
        eta_method = ss_method / ss_total if ss_total > 0 else 0.0
        eta_resid = ss_resid / ss_total if ss_total > 0 else 0.0
        return {
            "n_records": len(ok_records),
            "n_groups": n_groups,
            "eta_sq_model": 0.0,
            "eta_sq_method": round(eta_method, 4),
            "eta_sq_interaction": 0.0,
            "eta_sq_residual": round(eta_resid, 4),
            "anova": {},
            "unstable_pairs": _find_unstable_pairs(ok_records, seed=seed),
        }

    anova = two_way_anova(anova_data)

    return {
        "n_records": len(ok_records),
        "n_groups": n_groups,
        "eta_sq_model": round(anova["eta_sq_a"], 4),
        "eta_sq_method": round(anova["eta_sq_b"], 4),
        "eta_sq_interaction": round(anova["eta_sq_ab"], 4),
        "eta_sq_residual": round(anova["eta_sq_resid"], 4),
        "anova": {
            k: round(v, 6) if isinstance(v, float) else v for k, v in anova.items()
        },
        "unstable_pairs": _find_unstable_pairs(ok_records, seed=seed),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """Run variance decomposition on measurements.jsonl and write output."""
    import argparse
    import logging

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    log = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Variance decomposition of F1 scores")
    parser.add_argument(
        "--output",
        default="derived/variance_decomposition.json",
        help="Path to write output JSON",
    )
    args = parser.parse_args(argv)

    from .measurements import load

    records = load()
    result = variance_decomposition(records)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n")
    log.info("Wrote %s (%d records, %d groups)", output_path, result["n_records"], result["n_groups"])


if __name__ == "__main__":
    main()
