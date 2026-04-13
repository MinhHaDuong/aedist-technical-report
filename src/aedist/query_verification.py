"""Verification regimes on top configurations.

Applies 5 verification modes (unverified, tool, self, cross, web) to the
best outputs. Measures the evidence quality rubric (0-4) and the
precision-recall trade-off when filtering to verified-only plants.

Usage:
    python -m aedist.query_verification \
        --sweep verification --experiments experiments.toml \
        [--dry-run]
"""

import argparse
import csv
import json
import logging
import os
from pathlib import Path

import yaml

from .evaluate import load_plants_csv
from .harness import BudgetTracker
from .metrics import compute_metrics
from .reconcile import reconcile
from .schema import Method, MethodParams, ResourceUse, ResultSummary, RunRecord
from .verify import (
    _DEFAULT_REF,
    extract_csv_rows,
    extract_response_text,
    filter_by_score,
    verify_cross,
    verify_self,
    verify_tool,
    verify_unverified,
    verify_web,
    write_annotated_csv,
)

log = logging.getLogger(__name__)

# Web mode shares a Tavily cache across runs, so repeated runs produce
# identical results.  All three are deterministic: run once per config.
_DETERMINISTIC_MODES = {"unverified", "tool", "web"}

# Cost estimation constants (per million tokens, frontier model rates)
_COST_PER_MTOK_IN = 3.0
_COST_PER_MTOK_OUT = 15.0
_TAVILY_COST_PER_SEARCH = 0.005


def load_config(path: str | Path) -> dict:
    """Load verification YAML configuration."""
    with open(path) as f:
        return yaml.safe_load(f)


def _output_stem(model: str, mode: str, run: int) -> str:
    """Generate output filename stem: {model_short}-{mode}-run{n}."""
    short = model.split("/")[-1].replace(":", "-")
    return f"{short}-{mode}-run{run}"


_EMPTY_METRICS = {
    "n_plants": 0,
    "tp": 0,
    "fp": 0,
    "fn": 0,
    "f1": 0.0,
    "precision": 0.0,
    "coverage": 0.0,
    "fuel_accuracy": None,
    "status_accuracy": None,
    "province_accuracy": None,
}


def _evaluate_plants(system_plants: list, reference_path: Path, ref_plants_cache: dict) -> dict:
    """Evaluate system plants against reference, return metrics dict.

    Uses ref_plants_cache to avoid re-loading the reference CSV.
    Returns zeroed metrics for empty system output (e.g. no plants pass filter).
    """
    if not system_plants:
        return dict(_EMPTY_METRICS)

    ref_key = str(reference_path)
    if ref_key not in ref_plants_cache:
        ref_plants_cache[ref_key] = load_plants_csv(reference_path)
    ref_plants = ref_plants_cache[ref_key]

    entries = reconcile(ref_plants, system_plants)
    metrics = compute_metrics(entries)
    return {
        "n_plants": len(system_plants),
        "tp": metrics.n_matched,
        "fp": metrics.n_hallucinated,
        "fn": metrics.n_missed,
        "f1": round(metrics.f1, 4),
        "precision": round(metrics.precision, 4),
        "coverage": round(metrics.coverage, 4),
        "fuel_accuracy": round(metrics.fuel_accuracy, 4)
        if metrics.fuel_accuracy is not None
        else None,
        "status_accuracy": round(metrics.status_accuracy, 4)
        if metrics.status_accuracy is not None
        else None,
        "province_accuracy": round(metrics.province_accuracy, 4)
        if metrics.province_accuracy is not None
        else None,
    }


def _write_filtered_csv(annotated: list[dict], path: Path, min_score: int = 3) -> Path:
    """Write only plants with evidence_score >= min_score to CSV."""
    filtered = filter_by_score(annotated, min_score)
    if not filtered:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="") as f:
            if annotated:
                writer = csv.DictWriter(f, fieldnames=list(annotated[0].keys()))
                writer.writeheader()
        return path
    write_annotated_csv(filtered, path)
    return path


def verify_multi_cross(
    rows: list[dict],
    verifier_panel: list[str],
    subject: str = "thermal power plants in Vietnam",
) -> tuple[list[dict], dict]:
    """Multi-agent cross-verification: k verifiers score each row independently.

    Calls verify_cross() for each model in verifier_panel, collects per-row
    evidence scores, and computes the median across verifiers.

    Returns (annotated_rows, summary_dict) where:
      - Each row has evidence_score_v1..vN and evidence_score_median columns
      - evidence_score is set to the median for downstream filter_by_score compatibility
      - summary_dict contains per-verifier costs summed
    """
    import statistics as _statistics

    from .verify import DEFAULT_VERIFICATION_SUBJECT as _DVS  # noqa: F811

    if subject == "thermal power plants in Vietnam":
        subject = _DVS

    if not verifier_panel:
        # Empty panel: return rows unchanged with default scores
        annotated = []
        for row in rows:
            entry = dict(row)
            entry.setdefault("evidence_score", "1")
            annotated.append(entry)
        summary = {
            "mode": "multi_cross",
            "total_plants": len(annotated),
            "mean_evidence_score": 1.0 if annotated else 0.0,
            "score_distribution": {"0": 0, "1": len(annotated), "2": 0, "3": 0, "4": 0},
            "verifier_panel": [],
            "usage": {},
        }
        return annotated, summary

    # Collect per-verifier annotated results
    per_verifier_annotated: list[list[dict]] = []
    total_usage: dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0}

    for verifier_model in verifier_panel:
        v_annotated, v_summary = verify_cross(rows, verifier_model, subject)
        per_verifier_annotated.append(v_annotated)
        v_usage = v_summary.get("usage", {})
        total_usage["prompt_tokens"] += v_usage.get("prompt_tokens", 0) or 0
        total_usage["completion_tokens"] += v_usage.get("completion_tokens", 0) or 0

    # Merge: for each row, collect scores from each verifier, compute median
    annotated = []
    for row_idx, row in enumerate(rows):
        entry = dict(row)
        scores = []
        for v_idx, v_rows in enumerate(per_verifier_annotated, start=1):
            if row_idx < len(v_rows):
                score = int(v_rows[row_idx].get("evidence_score", 1))
            else:
                score = 1
            entry[f"evidence_score_v{v_idx}"] = str(score)
            scores.append(score)

        median_score = int(_statistics.median(scores))
        entry["evidence_score_median"] = str(median_score)
        entry["evidence_score"] = str(median_score)
        entry["verified"] = "True" if median_score >= 3 else "False"
        annotated.append(entry)

    # Build summary
    all_scores = [int(r["evidence_score"]) for r in annotated]
    total = len(annotated) or 1
    from collections import Counter as _Counter

    counts = _Counter(all_scores)
    summary = {
        "mode": "multi_cross",
        "total_plants": len(annotated),
        "mean_evidence_score": round(sum(all_scores) / total, 2),
        "score_distribution": {str(i): counts.get(i, 0) for i in range(5)},
        "verifier_panel": verifier_panel,
        "usage": total_usage,
    }
    return annotated, summary


def run_condition(
    rows: list[dict],
    base_config: dict,
    mode: str,
    run: int,
    output_dir: Path,
    reference_path: Path,
    ref_plants_cache: dict,
    cross_verifier: str | None = None,
    tavily_key: str | None = None,
    verifier_panel: list[str] | None = None,
) -> RunRecord | None:
    """Run one verification condition and return a RunRecord.

    Takes pre-extracted rows to avoid re-reading the base output file.
    """
    model = base_config["model"]
    method = base_config["method"]
    result_file = base_config["result_file"]

    stem = _output_stem(model, mode, run)
    csv_path = output_dir / f"{stem}.csv"
    filtered_path = output_dir / f"{stem}_filtered.csv"

    if csv_path.exists():
        log.info("Skip %s (cached)", stem)
        return None

    log.info("Running %s (mode=%s, run=%d, %d plants)...", stem, mode, run, len(rows))

    # Apply verification mode
    verification_cost = 0.0
    if mode == "unverified":
        annotated, summary = verify_unverified(rows)
    elif mode == "tool":
        annotated, summary = verify_tool(rows, reference_path)
    elif mode == "self":
        annotated, summary = verify_self(rows, model)
        verification_cost = _estimate_llm_cost(summary)
    elif mode == "cross":
        if not cross_verifier:
            log.error("No cross_verifier configured")
            return None
        annotated, summary = verify_cross(rows, cross_verifier)
        verification_cost = _estimate_llm_cost(summary)
    elif mode == "multi_cross":
        if not verifier_panel:
            log.error("No verifier_panel configured for multi_cross mode")
            return None
        annotated, summary = verify_multi_cross(rows, verifier_panel)
        verification_cost = _estimate_llm_cost(summary)
    elif mode == "web":
        if not tavily_key:
            log.error("TAVILY_API_KEY not set, skipping web mode")
            return None
        cache_path = output_dir / "tavily_cache.json"
        annotated, summary = verify_web(rows, tavily_key, cache_path)
        verification_cost = summary.get("searches_performed", 0) * _TAVILY_COST_PER_SEARCH
    else:
        log.error("Unknown mode: %s", mode)
        return None

    # Write annotated CSV (full output)
    write_annotated_csv(annotated, csv_path)

    # Write filtered CSV (evidence_score >= 3)
    _write_filtered_csv(annotated, filtered_path)

    # Evaluate in-memory via written CSVs (load_plants_csv needs a file)
    full_metrics = _evaluate_plants(load_plants_csv(csv_path), reference_path, ref_plants_cache)
    filtered_metrics = _evaluate_plants(
        load_plants_csv(filtered_path), reference_path, ref_plants_cache
    )

    repo_root = Path(__file__).parent.parent.parent
    try:
        result_file_path = str(csv_path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        result_file_path = str(csv_path)
    return RunRecord(
        method=Method(method),
        method_params=MethodParams(
            model=model,
            prompt_version="verification",
            extra={
                "verification_mode": mode,
                "base_result_file": result_file,
                "cross_verifier": cross_verifier if mode == "cross" else None,
                "verifier_panel": verifier_panel if mode == "multi_cross" else None,
            },
        ),
        resource_use=ResourceUse(cost_usd=verification_cost),
        result_file=result_file_path,
        result_summary=ResultSummary(
            status="ok",
            n_plants=full_metrics["n_plants"],
            tp=full_metrics["tp"],
            fp=full_metrics["fp"],
            fn=full_metrics["fn"],
            f1=full_metrics["f1"],
            fuel_accuracy=full_metrics.get("fuel_accuracy"),
            status_accuracy=full_metrics.get("status_accuracy"),
            province_accuracy=full_metrics.get("province_accuracy"),
        ),
        justification={
            "verification_mode": mode,
            "mean_evidence_score": summary.get("mean_evidence_score"),
            "score_distribution": summary.get("score_distribution"),
            "verification_cost_usd": verification_cost,
            "filtered_metrics": filtered_metrics,
        },
    )


def _estimate_llm_cost(summary: dict) -> float:
    """Estimate LLM verification cost from usage data."""
    usage = summary.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens", 0) or 0
    completion_tokens = usage.get("completion_tokens", 0) or 0
    return (prompt_tokens * _COST_PER_MTOK_IN + completion_tokens * _COST_PER_MTOK_OUT) / 1_000_000


def main():
    parser = argparse.ArgumentParser(description="Verification regimes on top configurations")
    parser.add_argument("--config", help="Path to verification YAML config (legacy)")
    parser.add_argument("--sweep", help="Sweep name from experiments.toml")
    parser.add_argument(
        "--experiments",
        default="experiments.toml",
        help="Path to experiments.toml",
    )
    parser.add_argument("--dry-run", action="store_true", help="List conditions without running")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.sweep:
        from .harness import load_experiments

        exp = load_experiments(args.experiments)
        config = dict(exp["sweeps"][args.sweep])
    elif args.config:
        config = load_config(args.config)
    else:
        parser.error("Provide --config or --sweep")
    base_configs = config["base_configs"]
    modes = config["verification_modes"]
    repeat = config.get("repeat", 3)
    budget_usd = config.get("budget_usd")
    output_dir = Path(config.get("output", "derived/verification"))
    cross_verifier = config.get("cross_verifier")
    verifier_panel = config.get("verifier_panel")
    ref_path_str = config.get("reference")
    reference_path = Path(ref_path_str) if ref_path_str else _DEFAULT_REF

    tavily_key = os.environ.get("TAVILY_API_KEY")

    # Enumerate conditions
    conditions = [
        (base, mode, run)
        for base in base_configs
        for mode in modes
        for run in range(1, (1 if mode in _DETERMINISTIC_MODES else repeat) + 1)
    ]

    if args.dry_run:
        log.info("Verification: %d conditions", len(conditions))
        for base, mode, run in conditions:
            log.info(
                "  %s + %s + %s run %d",
                base["method"],
                base["model"],
                mode,
                run,
            )
        n_panel = len(verifier_panel) if verifier_panel else 0
        estimated_llm_calls = sum(
            n_panel if m == "multi_cross" else (1 if m in ("self", "cross") else 0)
            for _, m, _ in conditions
        )
        estimated_tavily_searches = sum(150 for _, m, _ in conditions if m == "web")
        log.info(
            "Estimated: %d LLM calls, ~%d Tavily searches",
            estimated_llm_calls,
            estimated_tavily_searches,
        )
        return

    # Pre-load base outputs (avoid re-reading per condition)
    base_rows: dict[str, list[dict]] = {}
    for base in base_configs:
        result_file = base["result_file"]
        result_path = Path(result_file)
        if not result_path.is_absolute():
            result_path = Path(__file__).parent.parent.parent / "experiments" / result_path
        record = json.loads(result_path.read_text())
        response_text = extract_response_text(record)
        if not response_text:
            log.warning("No response text in %s, skipping", result_file)
            continue
        rows = extract_csv_rows(response_text)
        if not rows:
            log.warning("No CSV data in %s, skipping", result_file)
            continue
        base_rows[result_file] = rows
        log.info("Loaded %d plants from %s", len(rows), result_file)

    # Run conditions
    budget = BudgetTracker(budget_usd)
    measurements_path = Path(__file__).parent.parent.parent / "measurements.jsonl"
    records: list[RunRecord] = []
    ref_plants_cache: dict = {}

    with open(measurements_path, "a") as mf:
        for base, mode, run in conditions:
            if not budget.check_or_warn():
                break

            rows = base_rows.get(base["result_file"])
            if not rows:
                continue

            run_record = run_condition(
                rows=rows,
                base_config=base,
                mode=mode,
                run=run,
                output_dir=output_dir,
                reference_path=reference_path,
                ref_plants_cache=ref_plants_cache,
                cross_verifier=cross_verifier,
                tavily_key=tavily_key,
                verifier_panel=verifier_panel,
            )
            if run_record:
                records.append(run_record)
                cost = run_record.resource_use.cost_usd or 0
                budget.add(cost)

                mf.write(run_record.to_jsonl_line() + "\n")
                mf.flush()

                jscore = run_record.justification or {}
                log.info(
                    "  Done: F1=%.4f, mean_evidence=%.2f, cost=$%.4f",
                    run_record.result_summary.f1 or 0,
                    jscore.get("mean_evidence_score", 0),
                    cost,
                )

    log.info(
        "Verification complete. %d records. Total cost: $%.4f",
        len(records),
        budget.total_cost,
    )


if __name__ == "__main__":
    main()
