"""Aggregation sweep for AEDIST self-ensembling experiments.

Generates all cells of the (merge_method × pool_size × diversity_rule) factorial
from committed per-run records in experiments/outputs/exp1_batch2/, with no new
API calls. Writes results to experiments/derived/aggregation_sweep.csv.

Usage:
    uv run python -m aedist.sweep_aggregations [--output PATH]

Ticket 0375.

Factorial design:
  merge_method: union, majority_2, majority_3, confidence_weighted
  pool_size: 2, 3, 4
  diversity_rule: intra_model, cross_model_low, cross_model_high, cross_model_mixed

Notes:
- intra_model: pool runs from the SAME model (only feasible when that model has ≥ pool_size runs).
  Averaged over all qualifying models to give a per-model-agnostic estimate.
- cross_model_low: one run each from the cheapest-cost models (distinct models)
- cross_model_high: one run each from the most-expensive models (distinct models)
- cross_model_mixed: alternate cheap and expensive models to fill the pool
- confidence_weighted threshold = 0.5 × pool_size (so at least half the runs must
  mention a plant with HIGH confidence, or more runs with lower confidence)
- Cells that are degenerate or unsupported are written with mean_f1=NA.
"""

import argparse
import csv
import itertools
import json
import logging
from collections import defaultdict
from pathlib import Path

from .aggregate_runs import (
    has_confidence_data,
    load_run_confidence,
    load_run_names,
    merge_confidence_weighted,
    merge_majority,
    merge_union,
)
from .config import VN_THERMAL_PLANTS_RELEASE_CSV
from .evaluate import load_plants_csv
from .metrics import compute_metrics
from .reconcile import reconcile

log = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).parent.parent.parent
_EXP1_BATCH2_DIR = _REPO_ROOT / "experiments" / "outputs" / "exp1_batch2"
_DERIVED_DIR = _REPO_ROOT / "experiments" / "derived"
_OUTPUT_CSV = _DERIVED_DIR / "aggregation_sweep.csv"

_MERGE_METHODS = ["union", "majority_2", "majority_3", "confidence_weighted"]
_POOL_SIZES = [2, 3, 4]
_DIVERSITY_RULES = ["intra_model", "cross_model_low", "cross_model_high", "cross_model_mixed"]

_OUTPUT_FIELDS = [
    "merge_method",
    "pool_size",
    "diversity_rule",
    "mean_f1",
    "mean_recall",
    "mean_precision",
    "mean_n_plants",
    "mean_cost_usd",
    "n_pools",
    "notes",
]


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------


def _load_model_runs(exp1_dir: Path) -> dict[str, list[Path]]:
    """Return {model_slug: [csv_path, ...]} sorted by run number."""
    result: dict[str, list[Path]] = defaultdict(list)
    for rec_path in sorted(exp1_dir.glob("*.record.json")):
        with open(rec_path, encoding="utf-8") as f:
            rec = json.load(f)
        result_file = rec.get("result_file", "")
        csv_rel = Path(result_file)
        # result_file is relative to repo root
        csv_path = _REPO_ROOT / csv_rel
        if not csv_path.exists():
            log.warning("Missing CSV: %s", csv_path)
            continue
        model_slug = rec_path.stem.rsplit("-run", 1)[0]
        result[model_slug].append(csv_path)
    return dict(result)


def _load_model_costs(exp1_dir: Path) -> dict[str, float]:
    """Return {model_slug: mean_cost_usd} over all runs."""
    costs: dict[str, list[float]] = defaultdict(list)
    for rec_path in sorted(exp1_dir.glob("*.record.json")):
        with open(rec_path, encoding="utf-8") as f:
            rec = json.load(f)
        model_slug = rec_path.stem.rsplit("-run", 1)[0]
        cost = rec.get("resource_use", {}).get("cost_usd", 0.0)
        costs[model_slug].append(cost)
    return {m: sum(c) / len(c) for m, c in costs.items()}


# ---------------------------------------------------------------------------
# Scoring helper
# ---------------------------------------------------------------------------


def _load_pool_rows(pool: list[Path]) -> dict[str, dict[str, str]]:
    """Build a {name → row_dict} map from a pool of CSV paths.

    For each unique plant name, keep the row from the first run that mentioned
    it (preserving fuel, status, capacity, province for meaningful LP scoring).
    """
    seen: dict[str, dict[str, str]] = {}
    for csv_path in pool:
        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                name = row.get("name", "").strip()
                if name and name not in seen:
                    seen[name] = row
    return seen


def _score_pool_merged(
    selected_names: list[str],
    pool_rows: dict[str, dict[str, str]],
) -> tuple[float, float, float]:
    """Score a set of selected plant names using full row data from the pool.

    Uses the first-occurrence row data (fuel, status, capacity) for LP scoring
    so the matcher has meaningful signals. Returns (f1, recall, precision).
    """
    if not selected_names:
        return 0.0, 0.0, 0.0
    reference = load_plants_csv(VN_THERMAL_PLANTS_RELEASE_CSV)
    # Build a temporary CSV with full row data for the selected names.
    rows = [pool_rows[n] for n in selected_names if n in pool_rows]
    if not rows:
        return 0.0, 0.0, 0.0
    # plants_from_dicts handles CSV parsing + enum projection.
    from .evaluate import plants_from_dicts

    system = plants_from_dicts(rows)
    entries = reconcile(reference, system)
    metrics = compute_metrics(entries)
    return metrics.f1, metrics.coverage, metrics.precision


# ---------------------------------------------------------------------------
# Pool generation helpers
# ---------------------------------------------------------------------------


def _intra_model_pools(model_runs: dict[str, list[Path]], pool_size: int) -> list[list[Path]]:
    """Generate all pools of `pool_size` runs from the same model.

    For each model that has ≥ pool_size runs, take the first pool_size runs
    (deterministic). Returns one pool per qualifying model.
    """
    pools = []
    for _model, runs in sorted(model_runs.items()):
        if len(runs) >= pool_size:
            pools.append(runs[:pool_size])
    return pools


def _rank_models_by_cost(model_costs: dict[str, float], ascending: bool = True) -> list[str]:
    """Return model slugs sorted by mean cost (ascending or descending)."""
    return sorted(model_costs, key=lambda m: model_costs[m], reverse=not ascending)


def _cross_model_low_pool(model_runs: dict[str, list[Path]], model_costs: dict[str, float], pool_size: int) -> list[Path]:
    """One run per model, selecting the cheapest-cost models."""
    ranked = _rank_models_by_cost(model_costs, ascending=True)
    pool = []
    for m in ranked:
        if m in model_runs and model_runs[m]:
            pool.append(model_runs[m][0])  # First run of each model
            if len(pool) == pool_size:
                break
    return pool if len(pool) == pool_size else []


def _cross_model_high_pool(model_runs: dict[str, list[Path]], model_costs: dict[str, float], pool_size: int) -> list[Path]:
    """One run per model, selecting the most expensive models."""
    ranked = _rank_models_by_cost(model_costs, ascending=False)
    pool = []
    for m in ranked:
        if m in model_runs and model_runs[m]:
            pool.append(model_runs[m][0])
            if len(pool) == pool_size:
                break
    return pool if len(pool) == pool_size else []


def _cross_model_mixed_pool(model_runs: dict[str, list[Path]], model_costs: dict[str, float], pool_size: int) -> list[Path]:
    """Alternate between cheap and expensive models."""
    cheap = _rank_models_by_cost(model_costs, ascending=True)
    expensive = _rank_models_by_cost(model_costs, ascending=False)
    pool: list[Path] = []
    seen_models: set[str] = set()

    cheap_iter = iter(cheap)
    exp_iter = iter(expensive)
    use_cheap = True
    while len(pool) < pool_size:
        try:
            m = next(cheap_iter if use_cheap else exp_iter)
        except StopIteration:
            break
        if m not in seen_models and m in model_runs and model_runs[m]:
            pool.append(model_runs[m][0])
            seen_models.add(m)
        use_cheap = not use_cheap

    return pool if len(pool) == pool_size else []


# ---------------------------------------------------------------------------
# Merge helpers
# ---------------------------------------------------------------------------


def _apply_merge(
    pool: list[Path],
    merge_method: str,
    pool_size: int,
) -> list[str] | None:
    """Apply a merge method to a pool of CSV paths.

    Returns:
        list of aggregated plant names, or None if N/A (e.g. no confidence data).
    """
    run_names = [load_run_names(p) for p in pool]

    if merge_method == "union":
        return merge_union(run_names)

    if merge_method == "majority_2":
        return merge_majority(run_names, k=2)

    if merge_method == "majority_3":
        return merge_majority(run_names, k=3)

    if merge_method == "confidence_weighted":
        conf_maps = [load_run_confidence(p) for p in pool]
        if not has_confidence_data(conf_maps):
            return None  # N/A: no confidence data
        threshold = 0.5 * pool_size
        return merge_confidence_weighted(conf_maps, threshold=threshold)

    raise ValueError(f"Unknown merge_method: {merge_method}")


# ---------------------------------------------------------------------------
# Sweep
# ---------------------------------------------------------------------------


def run_sweep(exp1_dir: Path = _EXP1_BATCH2_DIR) -> list[dict]:
    """Execute the full factorial sweep. Returns list of result dicts."""
    model_runs = _load_model_runs(exp1_dir)
    model_costs = _load_model_costs(exp1_dir)
    log.info("Loaded %d models, %d total runs", len(model_runs), sum(len(v) for v in model_runs.values()))

    rows = []

    for merge_method, pool_size, diversity_rule in itertools.product(
        _MERGE_METHODS, _POOL_SIZES, _DIVERSITY_RULES
    ):
        # Generate pools for this (pool_size, diversity_rule) combination
        if diversity_rule == "intra_model":
            pools = _intra_model_pools(model_runs, pool_size)
        elif diversity_rule == "cross_model_low":
            pool = _cross_model_low_pool(model_runs, model_costs, pool_size)
            pools = [pool] if pool else []
        elif diversity_rule == "cross_model_high":
            pool = _cross_model_high_pool(model_runs, model_costs, pool_size)
            pools = [pool] if pool else []
        elif diversity_rule == "cross_model_mixed":
            pool = _cross_model_mixed_pool(model_runs, model_costs, pool_size)
            pools = [pool] if pool else []
        else:
            raise ValueError(f"Unknown diversity_rule: {diversity_rule}")

        if not pools:
            row = {
                "merge_method": merge_method,
                "pool_size": pool_size,
                "diversity_rule": diversity_rule,
                "mean_f1": "NA",
                "mean_recall": "NA",
                "mean_precision": "NA",
                "mean_n_plants": "NA",
                "mean_cost_usd": "NA",
                "n_pools": 0,
                "notes": "no qualifying pools",
            }
            rows.append(row)
            continue

        # Evaluate each pool
        f1_vals: list[float] = []
        recall_vals: list[float] = []
        precision_vals: list[float] = []
        n_plants_vals: list[int] = []
        cost_vals: list[float] = []
        na_count = 0

        for pool in pools:
            merged = _apply_merge(pool, merge_method, pool_size)
            if merged is None:
                na_count += 1
                continue

            # Use full row data (fuel, status, capacity) for accurate LP scoring.
            pool_rows = _load_pool_rows(pool)
            f1, recall, precision = _score_pool_merged(merged, pool_rows)
            f1_vals.append(f1)
            recall_vals.append(recall)
            precision_vals.append(precision)
            n_plants_vals.append(len(merged))

            # Cost = sum of individual run costs
            pool_cost = sum(
                _get_run_cost(exp1_dir, p) for p in pool
            )
            cost_vals.append(pool_cost)

        n_evaluated = len(f1_vals)
        notes = ""
        if na_count:
            notes = f"{na_count} pool(s) N/A (no confidence data)"

        if n_evaluated == 0:
            row = {
                "merge_method": merge_method,
                "pool_size": pool_size,
                "diversity_rule": diversity_rule,
                "mean_f1": "NA",
                "mean_recall": "NA",
                "mean_precision": "NA",
                "mean_n_plants": "NA",
                "mean_cost_usd": "NA",
                "n_pools": len(pools),
                "notes": notes or "all pools N/A",
            }
        else:
            row = {
                "merge_method": merge_method,
                "pool_size": pool_size,
                "diversity_rule": diversity_rule,
                "mean_f1": round(sum(f1_vals) / n_evaluated, 4),
                "mean_recall": round(sum(recall_vals) / n_evaluated, 4),
                "mean_precision": round(sum(precision_vals) / n_evaluated, 4),
                "mean_n_plants": round(sum(n_plants_vals) / n_evaluated, 1),
                "mean_cost_usd": round(sum(cost_vals) / n_evaluated, 4),
                "n_pools": n_evaluated,
                "notes": notes,
            }
        rows.append(row)
        log.info(
            "%s / %s / pool=%d: f1=%s, n_pools=%d",
            merge_method,
            diversity_rule,
            pool_size,
            row["mean_f1"],
            row["n_pools"],
        )

    return rows


def _get_run_cost(exp1_dir: Path, csv_path: Path) -> float:
    """Look up cost for a CSV path by reading the corresponding record.json."""
    # csv_path is absolute; record.json has the same stem + ".record.json"
    stem = csv_path.stem  # e.g. "claude-haiku-4.5-run1"
    rec_path = exp1_dir / f"{stem}.record.json"
    if rec_path.exists():
        with open(rec_path, encoding="utf-8") as f:
            rec = json.load(f)
        return rec.get("resource_use", {}).get("cost_usd", 0.0)
    return 0.0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Sweep run-aggregation methods over exp1_batch2 data."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_OUTPUT_CSV,
        help="Path to write the aggregation_sweep.csv (default: %(default)s)",
    )
    parser.add_argument(
        "--exp1-dir",
        type=Path,
        default=_EXP1_BATCH2_DIR,
        help="Directory of exp1_batch2 record.json and CSV files (default: %(default)s)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    rows = run_sweep(args.exp1_dir)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    log.info("Wrote %d rows to %s", len(rows), args.output)
    _print_summary(rows)


def _print_summary(rows: list[dict]) -> None:
    """Print a brief human-readable summary of the best aggregation recipes."""
    numeric_rows = [r for r in rows if r["mean_f1"] != "NA"]
    if not numeric_rows:
        print("No numeric results to summarize.")
        return

    best = max(numeric_rows, key=lambda r: float(r["mean_f1"]))
    print("\n=== Aggregation Sweep Summary ===")
    print(f"Total cells: {len(rows)}, evaluated: {len(numeric_rows)}, N/A: {len(rows) - len(numeric_rows)}")
    print("\nBest recipe:")
    print(f"  merge_method:  {best['merge_method']}")
    print(f"  pool_size:     {best['pool_size']}")
    print(f"  diversity_rule: {best['diversity_rule']}")
    print(f"  mean_f1:       {best['mean_f1']}")
    print(f"  mean_recall:   {best['mean_recall']}")
    print(f"  mean_precision: {best['mean_precision']}")
    print(f"  mean_n_plants: {best['mean_n_plants']}")
    print(f"  mean_cost_usd: {best['mean_cost_usd']}")
    print(f"  n_pools:       {best['n_pools']}")

    # Also show the top-5
    top5 = sorted(numeric_rows, key=lambda r: float(r["mean_f1"]), reverse=True)[:5]
    print("\nTop-5 by F1:")
    for i, r in enumerate(top5, 1):
        print(
            f"  {i}. {r['merge_method']:25s} pool={r['pool_size']} {r['diversity_rule']:20s}"
            f"  F1={r['mean_f1']:.4f}  recall={r['mean_recall']:.4f}  cost={r['mean_cost_usd']:.4f}"
        )


if __name__ == "__main__":
    main()
