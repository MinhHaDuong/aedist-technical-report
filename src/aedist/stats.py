"""Bootstrap confidence intervals and paired significance tests.

No external dependencies — uses only stdlib ``random``.  With n=3 runs
per condition the CIs are wide, but they make the uncertainty explicit
rather than hiding it behind point estimates.
"""

import random


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
    means = sorted(
        sum(rng.choices(values, k=n)) / n for _ in range(n_bootstrap)
    )
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
