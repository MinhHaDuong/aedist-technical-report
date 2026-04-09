"""Variance decomposition of F1 scores via two-way ANOVA.

Computes eta-squared and omega-squared for model, method, interaction,
and residual effects on F1 variance.  Uses only stdlib — no scipy, no numpy.

The balanced design requires equal cell sizes.  The code automatically
finds the largest balanced sub-design from the available data by
searching over method subsets (tractable because the number of methods
is small).

Usage::

    from aedist.variance_decomposition import variance_decomposition
    result = variance_decomposition(records)
"""

from __future__ import annotations

import math
import random as _random
from collections import defaultdict
from itertools import combinations

from .schema import RunRecord
from .stats import bootstrap_ci

# ---------------------------------------------------------------------------
# F-distribution p-value (stdlib only, regularised incomplete beta)
# ---------------------------------------------------------------------------


def _log_beta(a: float, b: float) -> float:
    """Log of the Beta function via lgamma."""
    return math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)


def _betainc(x: float, a: float, b: float, n_iter: int = 200) -> float:
    """Regularised incomplete beta function I_x(a,b) via Lentz continued-fraction."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    if x > (a + 1.0) / (a + b + 2.0):
        return 1.0 - _betainc(1.0 - x, b, a, n_iter)
    prefix = math.exp(a * math.log(x) + b * math.log(1.0 - x) - _log_beta(a, b)) / a
    c = 1.0
    d = 1.0 - (a + b) * x / (a + 1.0)
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    result = d
    for m in range(1, n_iter + 1):
        numerator = m * (b - m) * x / ((a + 2 * m - 1) * (a + 2 * m))
        d = 1.0 + numerator * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + numerator / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        result *= d * c
        numerator = -(a + m) * (a + b + m) * x / ((a + 2 * m) * (a + 2 * m + 1))
        d = 1.0 + numerator * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + numerator / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        result *= delta
        if abs(delta - 1.0) < 1e-12:
            break
    return prefix * result


def _f_pvalue(f_stat: float, df1: int, df2: int) -> float:
    """Upper-tail p-value of the F-distribution, P(F > f_stat)."""
    if df1 <= 0 or df2 <= 0 or f_stat <= 0:
        return 1.0
    x = df2 / (df2 + df1 * f_stat)
    return _betainc(x, df2 / 2.0, df1 / 2.0)


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

    Returns dict with SS, df, eta-squared, MS, F, p, and omega-squared.
    """
    levels_a: set[str] = set()
    levels_b: set[str] = set()
    for a, b in data:
        levels_a.add(a)
        levels_b.add(b)
    a_levels = sorted(levels_a)
    b_levels = sorted(levels_b)
    a_count = len(a_levels)
    b_count = len(b_levels)

    cell_sizes = {k: len(v) for k, v in data.items()}
    n = next(iter(cell_sizes.values()))
    if not all(s == n for s in cell_sizes.values()):
        msg = f"Unbalanced design: cell sizes = {cell_sizes}"
        raise ValueError(msg)

    n_total = a_count * b_count * n
    all_values = [y for ys in data.values() for y in ys]
    grand_mean = _mean(all_values)

    row_means: dict[str, float] = {}
    for a in a_levels:
        row_means[a] = _mean([y for b in b_levels for y in data[(a, b)]])

    col_means: dict[str, float] = {}
    for b in b_levels:
        col_means[b] = _mean([y for a in a_levels for y in data[(a, b)]])

    cell_means: dict[tuple[str, str], float] = {}
    for a in a_levels:
        for b in b_levels:
            cell_means[(a, b)] = _mean(data[(a, b)])

    ss_a = b_count * n * sum((row_means[a] - grand_mean) ** 2 for a in a_levels)
    ss_b = a_count * n * sum((col_means[b] - grand_mean) ** 2 for b in b_levels)
    ss_ab = n * sum(
        (cell_means[(a, b)] - row_means[a] - col_means[b] + grand_mean) ** 2
        for a in a_levels for b in b_levels
    )
    ss_resid = sum(
        (y - cell_means[(a, b)]) ** 2
        for (a, b), ys in data.items() for y in ys
    )
    ss_total = sum((y - grand_mean) ** 2 for y in all_values)

    df_a = a_count - 1
    df_b = b_count - 1
    df_ab = df_a * df_b
    df_resid = n_total - a_count * b_count
    df_total = n_total - 1

    eta_sq_a = ss_a / ss_total if ss_total > 0 else 0.0
    eta_sq_b = ss_b / ss_total if ss_total > 0 else 0.0
    eta_sq_ab = ss_ab / ss_total if ss_total > 0 else 0.0
    eta_sq_resid = ss_resid / ss_total if ss_total > 0 else 0.0

    ms_a = ss_a / df_a if df_a > 0 else 0.0
    ms_b = ss_b / df_b if df_b > 0 else 0.0
    ms_ab = ss_ab / df_ab if df_ab > 0 else 0.0
    ms_resid = ss_resid / df_resid if df_resid > 0 else 0.0

    f_a = ms_a / ms_resid if ms_resid > 0 else 0.0
    f_b = ms_b / ms_resid if ms_resid > 0 else 0.0
    f_ab = ms_ab / ms_resid if ms_resid > 0 else 0.0

    p_a = _f_pvalue(f_a, df_a, df_resid)
    p_b = _f_pvalue(f_b, df_b, df_resid)
    p_ab = _f_pvalue(f_ab, df_ab, df_resid)

    denom = ss_total + ms_resid
    omega_sq_a = max(0.0, (ss_a - df_a * ms_resid) / denom) if denom > 0 else 0.0
    omega_sq_b = max(0.0, (ss_b - df_b * ms_resid) / denom) if denom > 0 else 0.0
    omega_sq_ab = max(0.0, (ss_ab - df_ab * ms_resid) / denom) if denom > 0 else 0.0

    return {
        "ss_a": ss_a, "ss_b": ss_b, "ss_ab": ss_ab, "ss_resid": ss_resid,
        "ss_total": ss_total,
        "df_a": df_a, "df_b": df_b, "df_ab": df_ab, "df_resid": df_resid,
        "df_total": df_total,
        "eta_sq_a": eta_sq_a, "eta_sq_b": eta_sq_b, "eta_sq_ab": eta_sq_ab,
        "eta_sq_resid": eta_sq_resid,
        "ms_a": ms_a, "ms_b": ms_b, "ms_ab": ms_ab, "ms_resid": ms_resid,
        "f_a": f_a, "f_b": f_b, "f_ab": f_ab,
        "p_a": p_a, "p_b": p_b, "p_ab": p_ab,
        "omega_sq_a": omega_sq_a, "omega_sq_b": omega_sq_b,
        "omega_sq_ab": omega_sq_ab,
    }


# ---------------------------------------------------------------------------
# Unstable pair detection
# ---------------------------------------------------------------------------


def _find_unstable_pairs(
    records: list[RunRecord], threshold_pp: float = 5.0, seed: int = 42,
) -> list[dict]:
    """Find model pairs where mean F1 differs by <threshold_pp and CIs overlap."""
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
            ci_overlap = lo_a <= hi_b and lo_b <= hi_a
            if f1_diff < threshold_pp / 100 and ci_overlap:
                unstable.append({
                    "model_a": m_a, "model_b": m_b,
                    "f1_diff": round(f1_diff, 4), "ci_overlap": True,
                })
    return unstable


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def variance_decomposition(records: list[RunRecord], *, seed: int = 42) -> dict:
    """Run two-way ANOVA (model x method) on F1 scores from RunRecords."""
    ok_records = [
        r for r in records
        if r.result_summary.status == "ok" and r.result_summary.f1 is not None
    ]
    n_total_ok = len(ok_records)

    cells: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in ok_records:
        cells[(r.method_params.model, r.method)].append(r.result_summary.f1)

    if not cells:
        return {
            "n_records": 0, "n_records_excluded": len(records), "n_groups": 0,
            "models_included": [], "methods_included": [],
            "eta_sq_model": 0.0, "eta_sq_method": 0.0,
            "eta_sq_interaction": 0.0, "eta_sq_residual": 0.0,
            "omega_sq_model": 0.0, "omega_sq_method": 0.0,
            "omega_sq_interaction": 0.0, "anova": {}, "unstable_pairs": [],
        }

    min_reps = min(len(v) for v in cells.values())
    if min_reps < 2:
        cells = {k: v for k, v in cells.items() if len(v) >= 2}
        min_reps = min(len(v) for v in cells.values()) if cells else 0

    if min_reps < 2:
        return {
            "n_records": n_total_ok,
            "n_records_excluded": len(records) - n_total_ok, "n_groups": 0,
            "models_included": [], "methods_included": [],
            "eta_sq_model": 0.0, "eta_sq_method": 0.0,
            "eta_sq_interaction": 0.0, "eta_sq_residual": 0.0,
            "omega_sq_model": 0.0, "omega_sq_method": 0.0,
            "omega_sq_interaction": 0.0, "anova": {},
            "unstable_pairs": _find_unstable_pairs(ok_records, seed=seed),
        }

    rng = _random.Random(seed)
    balanced: dict[tuple[str, str], list[float]] = {
        k: (rng.sample(v, min_reps) if len(v) > min_reps else list(v))
        for k, v in cells.items()
    }

    models_in_cells: dict[str, set[str]] = defaultdict(set)
    for m, method in balanced:
        models_in_cells[m].add(method)
    unique_methods = sorted({method for _, method in balanced})

    best_score = 0
    all_models: set[str] = set()
    all_methods: set[str] = set()

    for size in range(len(unique_methods), 1, -1):
        for method_combo in combinations(unique_methods, size):
            method_set = set(method_combo)
            eligible = {m for m, ms in models_in_cells.items() if ms >= method_set}
            score = len(eligible) * len(method_set)
            if len(eligible) >= 2 and score > best_score:
                best_score = score
                all_models = eligible
                all_methods = method_set
        if best_score > 0 and (size - 1) * len(models_in_cells) <= best_score:
            break

    if best_score == 0:
        for method in unique_methods:
            eligible = {m for m, ms in models_in_cells.items() if method in ms}
            if len(eligible) >= 2 and len(eligible) > best_score:
                best_score = len(eligible)
                all_models = eligible
                all_methods = {method}

    anova_data: dict[tuple[str, str], list[float]] = {
        (m, method): v for (m, method), v in balanced.items()
        if m in all_models and method in all_methods
    }
    n_groups = len(anova_data)
    n_used = sum(len(v) for v in anova_data.values())
    n_excluded = len(records) - n_used

    if len(all_models) < 2:
        return {
            "n_records": n_total_ok, "n_records_excluded": n_excluded,
            "n_groups": n_groups,
            "models_included": sorted(all_models),
            "methods_included": sorted(all_methods),
            "eta_sq_model": 0.0, "eta_sq_method": 0.0,
            "eta_sq_interaction": 0.0,
            "eta_sq_residual": 1.0 if n_groups > 0 else 0.0,
            "omega_sq_model": 0.0, "omega_sq_method": 0.0,
            "omega_sq_interaction": 0.0, "anova": {},
            "unstable_pairs": _find_unstable_pairs(ok_records, seed=seed),
        }

    if len(all_methods) < 2:
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
            "n_records": n_total_ok, "n_records_excluded": n_excluded,
            "n_groups": n_groups,
            "models_included": sorted(all_models),
            "methods_included": sorted(all_methods),
            "eta_sq_model": round(eta_model, 4), "eta_sq_method": 0.0,
            "eta_sq_interaction": 0.0,
            "eta_sq_residual": round(eta_resid, 4),
            "omega_sq_model": 0.0, "omega_sq_method": 0.0,
            "omega_sq_interaction": 0.0, "anova": {},
            "unstable_pairs": _find_unstable_pairs(ok_records, seed=seed),
        }

    anova = two_way_anova(anova_data)
    return {
        "n_records": n_total_ok, "n_records_excluded": n_excluded,
        "n_groups": n_groups,
        "models_included": sorted(all_models),
        "methods_included": sorted(all_methods),
        "eta_sq_model": round(anova["eta_sq_a"], 4),
        "eta_sq_method": round(anova["eta_sq_b"], 4),
        "eta_sq_interaction": round(anova["eta_sq_ab"], 4),
        "eta_sq_residual": round(anova["eta_sq_resid"], 4),
        "omega_sq_model": round(anova["omega_sq_a"], 4),
        "omega_sq_method": round(anova["omega_sq_b"], 4),
        "omega_sq_interaction": round(anova["omega_sq_ab"], 4),
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
    import json
    import logging
    from pathlib import Path

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    log = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Variance decomposition of F1 scores")
    parser.add_argument("--output", required=True, help="Path to write output JSON")
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
