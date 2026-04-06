"""Sweep 4: Verification regimes on top Sweep 2 configurations.

Applies 5 verification modes (unverified, tool, self, cross, web) to the
best Sweep 2 outputs. Measures the evidence quality rubric (0-4) and the
precision-recall trade-off when filtering to verified-only plants.

Usage:
    python -m aedist.query_verification \
        --config experiments/sweeps/sweep4_verification.yaml \
        [--dry-run]
"""

import argparse
import csv
import json
import logging
import os
from pathlib import Path

import yaml

from .harness import BudgetTracker
from .metrics import compute_metrics
from .reconcile import reconcile
from .runner import load_plants_csv
from .schema import Method, MethodParams, ResourceUse, ResultSummary, RunRecord
from .verify import (
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

_DEFAULT_REF = (
    Path(__file__).parent.parent.parent / "data" / "reference" / "vietnam_thermal_v1.csv"
)

# Deterministic modes: run once regardless of repeat setting
_DETERMINISTIC_MODES = {"unverified", "tool"}


def load_config(path: str | Path) -> dict:
    """Load sweep 4 YAML configuration."""
    with open(path) as f:
        return yaml.safe_load(f)


def _output_stem(model: str, mode: str, run: int) -> str:
    """Generate output filename stem: {model_short}-{mode}-run{n}."""
    short = model.split("/")[-1].replace(":", "-")
    return f"{short}-{mode}-run{run}"


def _evaluate_csv(csv_path: Path, reference_path: Path) -> dict:
    """Evaluate a CSV against reference, return metrics dict."""
    system_plants = load_plants_csv(csv_path)
    ref_plants = load_plants_csv(reference_path)
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
        # Write empty CSV with headers
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="") as f:
            if annotated:
                writer = csv.DictWriter(f, fieldnames=list(annotated[0].keys()))
                writer.writeheader()
        return path
    write_annotated_csv(filtered, path)
    return path


def run_condition(
    base_config: dict,
    mode: str,
    run: int,
    output_dir: Path,
    reference_path: Path,
    cross_verifier: str | None = None,
    tavily_key: str | None = None,
) -> RunRecord | None:
    """Run one verification condition and return a RunRecord."""
    model = base_config["model"]
    method = base_config["method"]
    result_file = base_config["result_file"]

    stem = _output_stem(model, mode, run)
    csv_path = output_dir / f"{stem}.csv"
    filtered_path = output_dir / f"{stem}_filtered.csv"

    # Skip if already done
    if csv_path.exists():
        log.info("Skip %s (cached)", stem)
        return None

    # Load base output
    result_path = Path(result_file)
    if not result_path.is_absolute():
        # Resolve relative to experiments/ directory
        result_path = Path(__file__).parent.parent.parent / "experiments" / result_path
    record = json.loads(result_path.read_text())
    response_text = extract_response_text(record)
    if not response_text:
        log.warning("No response text in %s", result_file)
        return None

    rows = extract_csv_rows(response_text)
    if not rows:
        log.warning("No CSV data in %s", result_file)
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
    elif mode == "web":
        if not tavily_key:
            log.error("TAVILY_API_KEY not set, skipping web mode")
            return None
        cache_path = output_dir / "tavily_cache.json"
        annotated, summary = verify_web(rows, tavily_key, cache_path)
        verification_cost = summary.get("searches_performed", 0) * 0.005
    else:
        log.error("Unknown mode: %s", mode)
        return None

    # Write annotated CSV (full output)
    write_annotated_csv(annotated, csv_path)

    # Write filtered CSV (evidence_score >= 3)
    _write_filtered_csv(annotated, filtered_path)

    # Evaluate both full and filtered outputs
    full_metrics = _evaluate_csv(csv_path, reference_path)
    filtered_metrics = _evaluate_csv(filtered_path, reference_path)

    # Build RunRecord
    return RunRecord(
        method=Method(method),
        method_params=MethodParams(
            model=model,
            prompt_version="sweep4_verification",
            extra={
                "verification_mode": mode,
                "base_result_file": result_file,
                "cross_verifier": cross_verifier if mode == "cross" else None,
            },
        ),
        resource_use=ResourceUse(cost_usd=verification_cost),
        result_file=str(csv_path.relative_to(Path(__file__).parent.parent.parent)),
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
    # Rough estimate: $3/Mtok in, $15/Mtok out (frontier model rates)
    prompt_tokens = usage.get("prompt_tokens", 0) or 0
    completion_tokens = usage.get("completion_tokens", 0) or 0
    return (prompt_tokens * 3 + completion_tokens * 15) / 1_000_000


def main():
    parser = argparse.ArgumentParser(
        description="Sweep 4: Verification regimes on top Sweep 2 configs"
    )
    parser.add_argument("--config", required=True, help="Path to sweep4 YAML config")
    parser.add_argument("--dry-run", action="store_true", help="List conditions without running")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    config = load_config(args.config)
    base_configs = config["base_configs"]
    modes = config["verification_modes"]
    repeat = config.get("repeat", 3)
    budget_usd = config.get("budget_usd")
    output_dir = Path(config.get("output", "outputs/sweep4_verification"))
    cross_verifier = config.get("cross_verifier")
    ref_path_str = config.get("reference")
    reference_path = Path(ref_path_str) if ref_path_str else _DEFAULT_REF

    tavily_key = os.environ.get("TAVILY_API_KEY")

    # Enumerate conditions
    conditions = []
    for base in base_configs:
        for mode in modes:
            runs = 1 if mode in _DETERMINISTIC_MODES else repeat
            for run in range(1, runs + 1):
                conditions.append((base, mode, run))

    if args.dry_run:
        log.info("Sweep 4: %d conditions", len(conditions))
        for base, mode, run in conditions:
            log.info(
                "  %s + %s + %s run %d",
                base["method"],
                base["model"],
                mode,
                run,
            )
        estimated_llm_calls = sum(1 for _, m, _ in conditions if m in ("self", "cross"))
        estimated_tavily_searches = sum(150 for _, m, _ in conditions if m == "web")
        log.info(
            "Estimated: %d LLM calls, ~%d Tavily searches",
            estimated_llm_calls,
            estimated_tavily_searches,
        )
        return

    # Run conditions
    budget = BudgetTracker(budget_usd)
    measurements_path = Path(__file__).parent.parent.parent / "measurements.jsonl"
    records: list[RunRecord] = []

    for base, mode, run in conditions:
        if not budget.check_or_warn():
            break

        run_record = run_condition(
            base_config=base,
            mode=mode,
            run=run,
            output_dir=output_dir,
            reference_path=reference_path,
            cross_verifier=cross_verifier,
            tavily_key=tavily_key,
        )
        if run_record:
            records.append(run_record)
            cost = run_record.resource_use.cost_usd or 0
            budget.add(cost)

            # Append to measurements.jsonl
            with open(measurements_path, "a") as f:
                f.write(run_record.to_jsonl_line() + "\n")

            jscore = run_record.justification or {}
            log.info(
                "  Done: F1=%.4f, mean_evidence=%.2f, cost=$%.4f",
                run_record.result_summary.f1 or 0,
                jscore.get("mean_evidence_score", 0),
                cost,
            )

    log.info(
        "Sweep 4 complete. %d records. Total cost: $%.4f",
        len(records),
        budget.total_cost,
    )


if __name__ == "__main__":
    main()
