"""Within-model screen validation: do vetoed runs have lower accuracy within model?

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.

The internal-coherence screen (docs/internal-coherence-screen.md) vetoes runs
on two reference-free criteria derived from within-run capacity/status
variability:

    VETO if cap_distinct <= 4 OR status_distinct <= 1

where cap_distinct = number of distinct capacity values in the run output,
status_distinct = number of distinct status values.

A tautological concern: "weak models are weak on everything — of course
vetoed runs (from weak models) have lower F1." This script tests whether
the screen discriminates good from bad runs of the **same model**,
removing the across-model confound.

Method:
    For each model, compute cap_distinct and status_distinct from the raw
    exp1_batch2 CSV outputs. Pair with reference-based F1 from the cross-eval
    CSV. Report:
    1. Model-stratified Kendall tau of cap_distinct vs F1 (concordant−discordant
       pairs counted only within each model's 5 runs, summed across 14 models).
    2. Binary within-model mean F1 gap (vetoed vs surviving) for models that
       have both vetoed and surviving runs.

The across-model confound is illustrated by comparing the pooled gap
(tautological, inflated) to the within-model binary gap.

Usage:
    uv run python -m aedist.screen_validation_within_model \\
        --exp1-dir experiments/outputs/exp1_batch2 \\
        --cross-eval experiments/derived/exp1_cross_eval.csv \\
        --output report/inputs/generated/tab_screen_validation_within_model.csv
"""

import argparse
import csv
import logging
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

_CAP_KEYS = ("capacity_mwe", "total_mwe", "total_mw", "capacity")

# In-sample threshold from docs/internal-coherence-screen.md.
_CAP_DISTINCT_VETO = 4
_STATUS_DISTINCT_VETO = 1


@dataclass
class WithinModelAccuracyGap:
    """Result of the within-model accuracy gap analysis.

    Attributes:
        is_within_model: True — strata are (model,) not pooled.
        vetoed_mean_f1: Pooled mean F1 of vetoed runs (mixed models only;
            still carries cross-model confound — use per_model_binary_gap
            for the confound-free estimate).
        surviving_mean_f1: Pooled mean F1 of surviving runs (mixed models only).
        n_mixed_models: Number of models with both vetoed and surviving runs.
        per_model_binary_gap: Mean of per-model (surviving_mean − vetoed_mean)
            gaps over mixed models — the true within-model estimate without
            cross-model confound.
        stratified_kendall_tau_cap: Model-stratified Kendall tau,
            cap_distinct vs F1 (counts concordant/discordant pairs only
            within each model).
        stratified_kendall_tau_status: Same for status_distinct vs F1.
        tau_cap_concordant: Number of concordant pairs for cap_distinct tau.
        tau_cap_discordant: Number of discordant pairs for cap_distinct tau.
        tau_status_concordant: Number of concordant pairs for status_distinct tau.
        tau_status_discordant: Number of discordant pairs for status_distinct tau.
        n_models_positive_cap: Models with positive within-model Spearman
            rho(cap_distinct, F1).
        n_models_total: Total models with >= 2 scoreable runs.
        pooled_vetoed_mean_f1: Across-model pooled mean F1 of vetoed runs
            (tautological baseline; included to quantify the confound removed).
        pooled_surviving_mean_f1: Across-model pooled mean F1 of surviving runs.
    """

    is_within_model: bool
    vetoed_mean_f1: float | None
    surviving_mean_f1: float | None
    n_mixed_models: int
    per_model_binary_gap: float | None
    stratified_kendall_tau_cap: float
    stratified_kendall_tau_status: float
    tau_cap_concordant: int
    tau_cap_discordant: int
    tau_status_concordant: int
    tau_status_discordant: int
    n_models_positive_cap: int
    n_models_total: int
    pooled_vetoed_mean_f1: float
    pooled_surviving_mean_f1: float


def _load_f1(cross_eval: Path) -> dict[tuple[str, int], float | None]:
    """Load per-run F1 scores from the cross-eval CSV."""
    f1_map: dict[tuple[str, int], float | None] = {}
    with cross_eval.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            key = (row["model"], int(row["run"]))
            raw = row.get("accuracy_f1", "").strip()
            f1_map[key] = float(raw) if raw else None
    return f1_map


def _load_raw_runs(exp1_dir: Path, f1_map: dict[tuple[str, int], float | None]) -> list[dict]:
    """Compute cap_distinct and status_distinct from raw run CSVs."""
    runs = []
    for csv_path in sorted(exp1_dir.glob("*-run*.csv")):
        stem = csv_path.stem
        if stem.startswith("reconciliation_"):
            continue
        parts = stem.rsplit("-run", 1)
        if len(parts) != 2:
            continue
        model, run_str = parts
        try:
            run = int(run_str)
        except ValueError:
            continue

        with csv_path.open(newline="", encoding="utf-8") as fh:
            row_list = list(csv.DictReader(fh))

        # Distinct capacity values
        capacities = []
        for r in row_list:
            for k in _CAP_KEYS:
                v = (r.get(k) or "").strip()
                if v:
                    capacities.append(v)
                    break
        cap_distinct = len(set(capacities))

        # Distinct status values
        statuses = [s for r in row_list if (s := (r.get("status") or "").strip())]
        status_distinct = len(set(statuses))

        vetoed = cap_distinct <= _CAP_DISTINCT_VETO or status_distinct <= _STATUS_DISTINCT_VETO
        f1 = f1_map.get((model, run))

        runs.append(
            {
                "model": model,
                "run": run,
                "n_rows": len(row_list),
                "cap_distinct": cap_distinct,
                "status_distinct": status_distinct,
                "vetoed": vetoed,
                "f1": f1,
            }
        )

    return runs


def _spearman(xs: list[float], ys: list[float]) -> float | None:
    """Spearman rank correlation of two lists."""
    n = len(xs)
    if n < 2:
        return None

    def rank(arr: list[float]) -> list[float]:
        sorted_pairs = sorted(enumerate(arr), key=lambda x: x[1])
        ranks = [0.0] * n
        for i, (orig_idx, _) in enumerate(sorted_pairs):
            ranks[orig_idx] = float(i + 1)
        return ranks

    rx = rank(xs)
    ry = rank(ys)
    d2 = sum((x - y) ** 2 for x, y in zip(rx, ry, strict=True))
    return 1.0 - 6.0 * d2 / (n * (n**2 - 1))


def _stratified_kendall_tau(
    model_groups: dict[str, list[dict]], key: str
) -> tuple[float, int, int]:
    """Model-stratified Kendall tau of `key` vs F1.

    Concordant/discordant pairs are counted only within each model's runs,
    then summed across models. This removes the across-model confound.

    Returns (tau, concordant_total, discordant_total).
    """
    concordant = 0
    discordant = 0
    for model_runs in model_groups.values():
        valid = [(r[key], r["f1"]) for r in model_runs if r["f1"] is not None]
        n = len(valid)
        for i in range(n):
            for j in range(i + 1, n):
                xi, yi = valid[i]
                xj, yj = valid[j]
                prod = (xi - xj) * (yi - yj)
                if prod > 0:
                    concordant += 1
                elif prod < 0:
                    discordant += 1
    total = concordant + discordant
    tau = (concordant - discordant) / total if total > 0 else 0.0
    return tau, concordant, discordant


def within_model_accuracy_gap(rows: list[dict]) -> WithinModelAccuracyGap:
    """Compute the within-model accuracy gap between vetoed and surviving runs.

    Parameters
    ----------
    rows:
        List of dicts with keys: model, run, cap_distinct, status_distinct,
        vetoed (bool), f1 (float | None).

    Returns
    -------
    WithinModelAccuracyGap with is_within_model=True (strata are model-level).
    """
    from collections import defaultdict

    model_groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        model_groups[r["model"]].append(r)

    # Binary within-model gap (only models with both vetoed and surviving runs).
    # Compute per-model gaps first, then average — this is the confound-free estimate.
    # Pooling across models (extend) would still carry cross-model signal because
    # high-quality models tend to have both higher F1 and more surviving runs.
    within_vetoed_f1: list[float] = []
    within_surv_f1: list[float] = []
    per_model_gaps: list[float] = []
    n_mixed = 0

    for model_runs in model_groups.values():
        vetoed_runs = [r for r in model_runs if r["vetoed"] and r["f1"] is not None]
        surv_runs = [r for r in model_runs if not r["vetoed"] and r["f1"] is not None]
        if vetoed_runs and surv_runs:
            v_mean = sum(r["f1"] for r in vetoed_runs) / len(vetoed_runs)  # type: ignore[operator]
            s_mean = sum(r["f1"] for r in surv_runs) / len(surv_runs)  # type: ignore[operator]
            within_vetoed_f1.extend(r["f1"] for r in vetoed_runs)
            within_surv_f1.extend(r["f1"] for r in surv_runs)
            per_model_gaps.append(s_mean - v_mean)
            n_mixed += 1

    vetoed_mean = sum(within_vetoed_f1) / len(within_vetoed_f1) if within_vetoed_f1 else None
    surv_mean = sum(within_surv_f1) / len(within_surv_f1) if within_surv_f1 else None
    per_model_gap = sum(per_model_gaps) / len(per_model_gaps) if per_model_gaps else None

    # Model-stratified Kendall tau
    tau_cap, conc_cap, disc_cap = _stratified_kendall_tau(model_groups, "cap_distinct")
    tau_status, conc_status, disc_status = _stratified_kendall_tau(model_groups, "status_distinct")

    log.debug("Stratified tau(cap_distinct, F1): %.3f (%d C, %d D)", tau_cap, conc_cap, disc_cap)

    # Per-model Spearman direction count
    n_pos = 0
    n_tot = 0
    for model_runs in model_groups.values():
        valid = [(r["cap_distinct"], r["f1"]) for r in model_runs if r["f1"] is not None]
        if len(valid) < 2:
            continue
        xs, ys = zip(*valid, strict=False)  # valid has guaranteed >= 2 items from the check above
        rho = _spearman(list(xs), list(ys))
        if rho is not None:
            n_tot += 1
            if rho > 0:
                n_pos += 1

    # Pooled (across-model, tautological baseline)
    all_vetoed = [r["f1"] for r in rows if r["vetoed"] and r["f1"] is not None]
    all_surv = [r["f1"] for r in rows if not r["vetoed"] and r["f1"] is not None]
    pooled_v = sum(all_vetoed) / len(all_vetoed) if all_vetoed else 0.0
    pooled_s = sum(all_surv) / len(all_surv) if all_surv else 0.0

    return WithinModelAccuracyGap(
        is_within_model=True,
        vetoed_mean_f1=vetoed_mean,
        surviving_mean_f1=surv_mean,
        n_mixed_models=n_mixed,
        per_model_binary_gap=per_model_gap,
        stratified_kendall_tau_cap=tau_cap,
        stratified_kendall_tau_status=tau_status,
        tau_cap_concordant=conc_cap,
        tau_cap_discordant=disc_cap,
        tau_status_concordant=conc_status,
        tau_status_discordant=disc_status,
        n_models_positive_cap=n_pos,
        n_models_total=n_tot,
        pooled_vetoed_mean_f1=pooled_v,
        pooled_surviving_mean_f1=pooled_s,
    )


def run_analysis(exp1_dir: Path, cross_eval: Path, output: Path) -> WithinModelAccuracyGap:
    """Run the full within-model accuracy gap analysis and write a summary CSV."""
    f1_map = _load_f1(cross_eval)
    runs = _load_raw_runs(exp1_dir, f1_map)
    log.info("Loaded %d runs from %s", len(runs), exp1_dir)

    result = within_model_accuracy_gap(runs)

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "metric",
                "value",
                "note",
            ],
        )
        writer.writeheader()
        writer.writerows(
            [
                {
                    "metric": "stratified_kendall_tau_cap_distinct",
                    "value": f"{result.stratified_kendall_tau_cap:.3f}",
                    "note": "Model-stratified Kendall tau, cap_distinct vs F1 "
                    "(pairs counted within model only)",
                },
                {
                    "metric": "tau_cap_concordant",
                    "value": str(result.tau_cap_concordant),
                    "note": "Concordant pairs for cap_distinct tau",
                },
                {
                    "metric": "tau_cap_discordant",
                    "value": str(result.tau_cap_discordant),
                    "note": "Discordant pairs for cap_distinct tau",
                },
                {
                    "metric": "stratified_kendall_tau_status_distinct",
                    "value": f"{result.stratified_kendall_tau_status:.3f}",
                    "note": "Model-stratified Kendall tau, status_distinct vs F1",
                },
                {
                    "metric": "tau_status_concordant",
                    "value": str(result.tau_status_concordant),
                    "note": "Concordant pairs for status_distinct tau",
                },
                {
                    "metric": "tau_status_discordant",
                    "value": str(result.tau_status_discordant),
                    "note": "Discordant pairs for status_distinct tau",
                },
                {
                    "metric": "n_models_positive_cap_spearman",
                    "value": f"{result.n_models_positive_cap}/{result.n_models_total}",
                    "note": "Models with positive within-model Spearman(cap_distinct, F1)",
                },
                {
                    "metric": "n_mixed_models",
                    "value": str(result.n_mixed_models),
                    "note": "Models with both vetoed and surviving runs",
                },
                {
                    "metric": "per_model_binary_gap",
                    "value": f"{result.per_model_binary_gap:.3f}" if result.per_model_binary_gap is not None else "",
                    "note": "Mean of per-model (surviving - vetoed) F1 gaps — confound-free within-model estimate",
                },
                {
                    "metric": "within_model_vetoed_mean_f1",
                    "value": f"{result.vetoed_mean_f1:.3f}" if result.vetoed_mean_f1 is not None else "",
                    "note": "Pooled mean F1 of vetoed runs across mixed models (residual cross-model confound)",
                },
                {
                    "metric": "within_model_surviving_mean_f1",
                    "value": f"{result.surviving_mean_f1:.3f}" if result.surviving_mean_f1 is not None else "",
                    "note": "Pooled mean F1 of surviving runs across mixed models (residual cross-model confound)",
                },
                {
                    "metric": "pooled_vetoed_mean_f1",
                    "value": f"{result.pooled_vetoed_mean_f1:.3f}",
                    "note": "Pooled across-model mean F1 of vetoed runs (tautological baseline)",
                },
                {
                    "metric": "pooled_surviving_mean_f1",
                    "value": f"{result.pooled_surviving_mean_f1:.3f}",
                    "note": "Pooled across-model mean F1 of surviving runs (tautological baseline)",
                },
            ]
        )
    log.info("Wrote summary to %s", output)
    return result


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Within-model screen validation: vetoed vs surviving run F1"
    )
    parser.add_argument(
        "--exp1-dir",
        type=Path,
        default=Path("experiments/outputs/exp1_batch2"),
        help="Directory containing raw {model}-run{N}.csv files",
    )
    parser.add_argument(
        "--cross-eval",
        type=Path,
        default=Path("experiments/derived/exp1_cross_eval.csv"),
        help="Exp1 cross-eval CSV (provides reference-based F1 per run)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("report/inputs/generated/tab_screen_validation_within_model.csv"),
        help="Output summary CSV",
    )
    args = parser.parse_args(argv)

    result = run_analysis(args.exp1_dir, args.cross_eval, args.output)

    # Log the headline numbers
    log.info(
        "Model-stratified Kendall tau(cap_distinct, F1) = %.3f",
        result.stratified_kendall_tau_cap,
    )
    log.info(
        "Model-stratified Kendall tau(status_distinct, F1) = %.3f",
        result.stratified_kendall_tau_status,
    )
    log.info(
        "Positive within-model Spearman(cap_distinct, F1): %d/%d models",
        result.n_models_positive_cap,
        result.n_models_total,
    )
    log.info(
        "Mixed models binary gap: vetoed=%.3f, surviving=%.3f (n_mixed=%d) | per-model avg gap=%.3f",
        result.vetoed_mean_f1 or 0,
        result.surviving_mean_f1 or 0,
        result.n_mixed_models,
        result.per_model_binary_gap or 0,
    )
    log.info(
        "Pooled gap (tautological): vetoed=%.3f, surviving=%.3f",
        result.pooled_vetoed_mean_f1,
        result.pooled_surviving_mean_f1,
    )


if __name__ == "__main__":
    main()
