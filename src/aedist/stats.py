"""Bootstrap confidence intervals and paired significance tests.

No external dependencies — uses only stdlib ``random``.  With n=3 runs
per condition the CIs are wide, but they make the uncertainty explicit
rather than hiding it behind point estimates.

Includes Benjamini-Hochberg FDR correction for multiple comparison
control (G6) and ANOVA assumption diagnostics (G7).
"""

from __future__ import annotations

import logging
import math
import random

log = logging.getLogger(__name__)


def bootstrap_ci(
    values: list[float],
    confidence: float = 0.95,
    n_bootstrap: int = 10_000,
    *,
    seed: int | None = None,
) -> tuple[float, float, float]:
    """Return (mean, ci_low, ci_high) via percentile bootstrap.

    Args:
        values: Observed sample values.
        confidence: Confidence level (default 0.95 for 95% CI).
        n_bootstrap: Number of bootstrap resamples.
        seed: Optional RNG seed for reproducibility.
    """
    if not values:
        return (0.0, 0.0, 0.0)
    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(rng.choices(values, k=n)) / n for _ in range(n_bootstrap))
    alpha = (1 - confidence) / 2
    lo = means[int(alpha * n_bootstrap)]
    hi = means[int((1 - alpha) * n_bootstrap) - 1]
    return (sum(values) / n, lo, hi)


def paired_bootstrap_test(
    a: list[float],
    b: list[float],
    n_bootstrap: int = 10_000,
    *,
    seed: int | None = None,
) -> float:
    """Return p-value for H0: mean(a) == mean(b) via paired bootstrap.

    Uses the difference-of-means test statistic.  Samples are paired
    element-wise (run 1 vs run 1, etc.), so ``len(a) == len(b)`` is
    required.

    Args:
        a: Observed values for condition A.
        b: Observed values for condition B.
        n_bootstrap: Number of bootstrap resamples.
        seed: Optional RNG seed for reproducibility.

    Returns:
        Two-sided p-value.
    """
    if len(a) != len(b):
        msg = f"Paired test requires equal-length samples (got {len(a)} vs {len(b)})"
        raise ValueError(msg)
    if not a:
        return 1.0

    rng = random.Random(seed)
    diffs = [ai - bi for ai, bi in zip(a, b, strict=True)]
    observed = abs(sum(diffs) / len(diffs))

    # Resample under H0 by randomly flipping signs of differences
    count = 0
    for _ in range(n_bootstrap):
        resampled = [d * rng.choice((-1, 1)) for d in diffs]
        if abs(sum(resampled) / len(resampled)) >= observed:
            count += 1

    return count / n_bootstrap


# ---------------------------------------------------------------------------
# Multiple comparison correction (G6)
# ---------------------------------------------------------------------------


def correct_pvalues(
    pvals: list[float | None],
    method: str = "fdr_bh",
) -> list[float | None]:
    """Apply multiple-comparison correction to a list of p-values.

    Supports Benjamini-Hochberg FDR (``fdr_bh``).  ``None`` entries
    (models with too few runs for a test) are passed through unchanged.

    The implementation is pure-Python (no scipy dependency).

    Args:
        pvals: Raw p-values.  ``None`` entries are preserved in place.
        method: Correction method.  Only ``'fdr_bh'`` is supported.

    Returns:
        List of adjusted p-values (same length, same positions).

    Raises:
        ValueError: If *method* is not supported.
    """
    if method != "fdr_bh":
        msg = f"Unsupported correction method: {method!r} (only 'fdr_bh' is supported)"
        raise ValueError(msg)

    # Separate indices with actual p-values from None entries
    indexed: list[tuple[int, float]] = [(i, p) for i, p in enumerate(pvals) if p is not None]
    if not indexed:
        return list(pvals)

    m = len(indexed)
    # Sort by p-value
    indexed.sort(key=lambda t: t[1])

    # Benjamini-Hochberg: adjusted_i = p_i * m / rank_i
    # Then enforce monotonicity from largest rank downward
    adjusted = [0.0] * m
    for rank_0based, (orig_idx, p) in enumerate(indexed):
        rank = rank_0based + 1  # 1-based rank
        adjusted[rank_0based] = p * m / rank

    # Enforce monotonicity: walking from largest rank to smallest,
    # each adjusted value must be <= the one after it (in rank order)
    for j in range(m - 2, -1, -1):
        adjusted[j] = min(adjusted[j], adjusted[j + 1])

    # Cap at 1.0
    adjusted = [min(a, 1.0) for a in adjusted]

    # Reconstruct output list preserving None positions
    result: list[float | None] = list(pvals)
    for k, (orig_idx, _p) in enumerate(indexed):
        result[orig_idx] = adjusted[k]

    return result


# ---------------------------------------------------------------------------
# ANOVA assumption diagnostics (G7)
# ---------------------------------------------------------------------------


def _shapiro_wilk_w(x: list[float]) -> float | None:
    """Approximate normality W statistic inspired by Shapiro-Wilk.

    Uses Blom's expected order statistics as coefficients (not the true
    tabulated Shapiro-Wilk coefficients).  Suitable as a diagnostic flag
    for small samples (n <= 50) but should not be cited as a formal
    Shapiro-Wilk test.  Returns ``None`` if n < 3.
    """
    n = len(x)
    if n < 3:
        return None
    xs = sorted(x)
    mean = sum(xs) / n
    ss = sum((v - mean) ** 2 for v in xs)
    if ss == 0:
        return None

    # Approximate a-coefficients using Blom's formula for expected
    # normal order statistics: a_i ~ Phi^{-1}((i - 3/8)/(n + 1/4))
    # We use a rough inverse-normal approximation.
    def _inv_norm_approx(p: float) -> float:
        """Rational approximation to the inverse normal CDF (Abramowitz & Stegun 26.2.23)."""
        if p <= 0 or p >= 1:
            return 0.0
        if p > 0.5:
            return -_inv_norm_approx(1 - p)
        t = math.sqrt(-2 * math.log(p))
        # Coefficients for the rational approximation
        c0, c1, c2 = 2.515517, 0.802853, 0.010328
        d1, d2, d3 = 1.432788, 0.189269, 0.001308
        return -(t - (c0 + c1 * t + c2 * t * t) / (1 + d1 * t + d2 * t * t + d3 * t * t * t))

    a = [_inv_norm_approx((i + 1 - 0.375) / (n + 0.25)) for i in range(n)]
    a_ss = sum(ai * ai for ai in a)
    if a_ss == 0:
        return None

    # W = (sum(a_i * x_(i)))^2 / (sum(a_i^2) * SS)
    numerator = sum(ai * xi for ai, xi in zip(a, xs)) ** 2
    w = numerator / (a_ss * ss)
    return min(w, 1.0)


def _levene_statistic(groups: list[list[float]]) -> float | None:
    """Compute Levene's test statistic (mean-based) for homogeneity of variance.

    Returns ``None`` if fewer than 2 groups or any group has < 2 observations.
    """
    k = len(groups)
    if k < 2:
        return None
    if any(len(g) < 2 for g in groups):
        return None

    # Transform: z_ij = |x_ij - mean(x_j)|
    z_groups: list[list[float]] = []
    for g in groups:
        g_mean = sum(g) / len(g)
        z_groups.append([abs(v - g_mean) for v in g])

    all_z = [z for zg in z_groups for z in zg]
    n_total = len(all_z)
    z_grand = sum(all_z) / n_total

    z_means = [sum(zg) / len(zg) for zg in z_groups]

    # Between-group variability
    ss_between = sum(len(zg) * (zm - z_grand) ** 2 for zg, zm in zip(z_groups, z_means))
    # Within-group variability
    ss_within = sum(sum((z - zm) ** 2 for z in zg) for zg, zm in zip(z_groups, z_means))

    df_between = k - 1
    df_within = n_total - k

    if df_within <= 0 or ss_within == 0:
        return None

    w = (ss_between / df_between) / (ss_within / df_within)
    return w


def check_anova_assumptions(
    residuals: list[float],
    groups: list[list[float]] | None = None,
) -> dict[str, dict]:
    """Run ANOVA assumption diagnostics and return results.

    Checks:
    - **Normality** (Shapiro-Wilk on residuals, requires n >= 3)
    - **Homoscedasticity** (Levene's test on groups, requires groups)

    Args:
        residuals: ANOVA residuals (observed - cell mean).
        groups: Optional list of per-cell value lists for Levene's test.

    Returns:
        Dict mapping test name to ``{statistic, p_value, passed, note}``.
        When sample is too small, *statistic* and *p_value* are ``None``
        and *note* explains why.
    """
    result: dict[str, dict] = {}

    # --- Normality (Shapiro-Wilk) ---
    n = len(residuals)
    if n < 3:
        result["shapiro_wilk"] = {
            "statistic": None,
            "p_value": None,
            "passed": None,
            "note": f"Sample too small for Shapiro-Wilk (n={n}, need >= 3).",
        }
    else:
        w = _shapiro_wilk_w(residuals)
        if w is None:
            result["shapiro_wilk"] = {
                "statistic": None,
                "p_value": None,
                "passed": None,
                "note": "Shapiro-Wilk W could not be computed (zero variance).",
            }
        else:
            # We compute W but cannot compute an exact p-value without
            # distribution tables.  Use a conservative heuristic:
            # W > 0.9 suggests approximate normality for small samples.
            p_approx = None  # No closed-form p without tables
            passed = w > 0.9
            note = (
                f"W={w:.4f}. "
                + (
                    "W > 0.9 suggests approximate normality. "
                    if passed
                    else "W <= 0.9 suggests non-normality. "
                )
                + f"Caution: with n={n}, Shapiro-Wilk has very low power."
            )
            result["shapiro_wilk"] = {
                "statistic": round(w, 4),
                "p_value": p_approx,
                "passed": passed,
                "note": note,
            }

    # --- Homoscedasticity (Levene's test) ---
    if groups is None or len(groups) < 2:
        result["levene"] = {
            "statistic": None,
            "p_value": None,
            "passed": None,
            "note": "No group data provided for Levene's test."
            if groups is None
            else f"Need >= 2 groups for Levene's test (got {len(groups)}).",
        }
    elif any(len(g) < 2 for g in groups):
        small = [i for i, g in enumerate(groups) if len(g) < 2]
        result["levene"] = {
            "statistic": None,
            "p_value": None,
            "passed": None,
            "note": f"Some groups have < 2 observations (groups {small}); Levene's test not applicable.",
        }
    else:
        w = _levene_statistic(groups)
        if w is None:
            result["levene"] = {
                "statistic": None,
                "p_value": None,
                "passed": None,
                "note": "Levene's statistic could not be computed.",
            }
        else:
            # Without F-distribution tables we use a heuristic:
            # W < 2.0 generally suggests acceptable homogeneity for
            # small balanced designs.
            k = len(groups)
            n_total = sum(len(g) for g in groups)
            passed = w < 2.0
            note = (
                f"W={w:.4f} (k={k} groups, N={n_total}). "
                + (
                    "W < 2.0 suggests acceptable variance homogeneity. "
                    if passed
                    else "W >= 2.0 suggests possible heteroscedasticity. "
                )
                + "Caution: with small cell sizes, Levene's test has low power."
            )
            result["levene"] = {
                "statistic": round(w, 4),
                "p_value": None,  # No exact p without F-distribution tables
                "passed": passed,
                "note": note,
            }

    return result
