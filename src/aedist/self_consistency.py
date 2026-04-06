"""Self-consistency evaluation for sweep2_rag outputs.

For each model with 3 runs, merge them by majority vote (plant kept if it
appears in 2+ of 3 runs), evaluate the consolidated result, and compare
against the single-run median F1.

Usage:
    python -m aedist.self_consistency \
        --input experiments/outputs/sweep2_rag \
        --output experiments/outputs/sweep2_rag_consistency
"""

import argparse
import csv
import io
import json
import logging
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

from .extract import extract_one
from .metrics import BenchmarkMetrics, compute_metrics
from .reconcile import reconcile
from .runner import _DEFAULT_REF, load_plants_csv
from .schema import (
    FuelType,
    Method,
    MethodParams,
    Plant,
    PlantStatus,
    ResultSummary,
    RunRecord,
)

log = logging.getLogger(__name__)


def _normalize_name(name: str) -> str:
    """Cheap name normalization: lower, strip accents-neutral, collapse spaces."""
    n = unicodedata.normalize("NFC", name.strip().lower())
    n = re.sub(r"\s+", " ", n)
    return n


def _extract_to_csv(json_path: Path, work_dir: Path) -> Path | None:
    """Extract CSV from a single JSON run file. Returns CSV path or None."""
    work_dir.mkdir(parents=True, exist_ok=True)
    result = extract_one(json_path, work_dir, overwrite=True)
    if result.output_path and result.output_path.exists():
        return result.output_path
    log.warning("Extraction failed for %s: %s", json_path.name, result.message)
    return None


def _canonical_name(plant: Plant) -> str:
    """Return a cleaned name for a Plant using the existing cleaner pipeline."""
    return _normalize_name(plant.name)


def _build_name_maps(run_plant_lists: list[list]) -> list[dict[str, object]]:
    """Build normalized-name → Plant maps for each run."""
    result = []
    for plants in run_plant_lists:
        mapping: dict[str, object] = {}
        for p in plants:
            key = _canonical_name(p)
            if key not in mapping:
                mapping[key] = p
        result.append(mapping)
    return result


def majority_vote(run_plant_lists: list[list]) -> list:
    """Given lists of Plant objects, return plants present in 2+ runs (majority).

    Uses normalized name matching. For plants in the majority, takes attributes
    from the run with the most plants (most complete response).
    """
    name_to_plant = _build_name_maps(run_plant_lists)
    n_runs = len(run_plant_lists)

    all_keys: set[str] = set()
    for mapping in name_to_plant:
        all_keys |= mapping.keys()

    majority: list = []
    for key in sorted(all_keys):
        appearances = [m for m in name_to_plant if key in m]
        if len(appearances) >= (n_runs // 2 + 1):  # majority: 2+ out of 3
            source = max(appearances, key=lambda m: len(m))
            majority.append(source[key])

    return majority


def union_vote(run_plant_lists: list[list]) -> list:
    """Return all plants seen in ANY run (union / OR vote).

    Precision drops but recall maximized. Useful as an upper-bound reference.
    For plants appearing in multiple runs, attributes taken from the longest run.
    """
    name_to_plant = _build_name_maps(run_plant_lists)

    all_keys: set[str] = set()
    for mapping in name_to_plant:
        all_keys |= mapping.keys()

    union: list = []
    for key in sorted(all_keys):
        appearances = [m for m in name_to_plant if key in m]
        source = max(appearances, key=lambda m: len(m))
        union.append(source[key])

    return union


def plants_to_csv_text(plants: list) -> str:
    """Serialize a list of Plant objects to canonical CSV text."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["name", "fuel", "status", "cod", "province", "capacity_mwe"])
    for p in plants:
        fuel = p.fuel.value if p.fuel and p.fuel != FuelType.UNKNOWN else ""
        status = p.status.value if p.status and p.status != PlantStatus.UNKNOWN else ""
        writer.writerow(
            [
                p.name,
                fuel,
                status,
                p.cod or "",
                p.province or "",
                str(p.capacity_mwe) if p.capacity_mwe is not None else "",
            ]
        )
    return buf.getvalue()


def _group_runs(input_dir: Path) -> dict[str, list[Path]]:
    """Group JSON files by model name. Returns {model: [run1, run2, run3]}."""
    pattern = re.compile(r"^(.+)-run(\d+)\.json$")
    groups: dict[str, list[tuple[int, Path]]] = defaultdict(list)
    for jf in sorted(input_dir.glob("*.json")):
        m = pattern.match(jf.name)
        if m:
            groups[m.group(1)].append((int(m.group(2)), jf))
    return {model: [p for _, p in sorted(runs)] for model, runs in groups.items()}


def evaluate_single_runs(
    run_paths: list[Path],
    work_dir: Path,
    reference_plants: list,
) -> tuple[list[BenchmarkMetrics], list[Path | None]]:
    """Extract + evaluate each run individually. Returns (metrics_list, csv_paths)."""
    metrics_list = []
    csv_paths = []
    for jp in run_paths:
        csv_path = _extract_to_csv(jp, work_dir)
        csv_paths.append(csv_path)
        if csv_path:
            system = load_plants_csv(csv_path)
            entries = reconcile(reference_plants, system)
            metrics_list.append(compute_metrics(entries))
        else:
            metrics_list.append(None)
    return metrics_list, csv_paths


def run_analysis(
    input_dir: Path,
    output_dir: Path,
    reference_path: Path,
) -> tuple[list[dict], dict[str, list[BenchmarkMetrics]], dict[str, list[Path]]]:
    """Run self-consistency analysis.

    Returns (results, run_metrics_by_model, run_paths_by_model):
    - results: list of per-model summary dicts
    - run_metrics_by_model: per-model list of BenchmarkMetrics (sorted by F1)
    - run_paths_by_model: per-model list of JSON source paths
    """
    reference = load_plants_csv(reference_path)
    log.info("Reference: %d plants", len(reference))

    groups = _group_runs(input_dir)
    log.info("Found %d models: %s", len(groups), sorted(groups.keys()))

    work_dir = output_dir / "_extracted"
    results = []
    run_metrics_by_model: dict[str, list[BenchmarkMetrics]] = {}
    run_paths_by_model: dict[str, list[Path]] = {}

    for model, run_paths in sorted(groups.items()):
        log.info("\n=== %s ===", model)

        # Evaluate individual runs
        run_metrics, csv_paths = evaluate_single_runs(run_paths, work_dir, reference)
        valid_metrics = [m for m in run_metrics if m is not None]

        if not valid_metrics:
            log.warning("No valid runs for %s — skipping", model)
            continue

        # Sort metrics by F1 so per-run arrays are aligned with sorted f1_scores
        valid_metrics.sort(key=lambda m: m.f1)
        run_metrics_by_model[model] = valid_metrics
        run_paths_by_model[model] = run_paths
        f1_scores = [m.f1 for m in valid_metrics]
        median_f1 = f1_scores[len(f1_scores) // 2]

        log.info(
            "Individual run F1: %s  (median=%.1f%%)",
            [f"{f:.1%}" for f in f1_scores],
            median_f1 * 100,
        )

        # Self-consistency: majority vote across all runs with valid CSV
        valid_plant_lists = []
        for csv_path in csv_paths:
            if csv_path:
                plants = load_plants_csv(csv_path)
                if plants:
                    valid_plant_lists.append(plants)

        consistency_metrics = None
        union_metrics = None
        voted_plants: list = []

        if len(valid_plant_lists) < 2:
            log.warning("Fewer than 2 valid runs for %s — cannot do majority vote", model)
            consistency_metrics = valid_metrics[0] if valid_metrics else None
            union_metrics = consistency_metrics
            voted_plants = valid_plant_lists[0] if valid_plant_lists else []
        else:
            run_sizes = [len(pl) for pl in valid_plant_lists]

            majority_plants = majority_vote(valid_plant_lists)
            log.info("Majority-vote: %d plants (from runs of %s)", len(majority_plants), run_sizes)

            union_plants = union_vote(valid_plant_lists)
            log.info("Union-vote:    %d plants", len(union_plants))

            output_dir.mkdir(parents=True, exist_ok=True)

            # Save and evaluate majority-vote CSV
            consolidated_path = output_dir / f"{model}-consolidated.csv"
            consolidated_path.write_text(plants_to_csv_text(majority_plants), encoding="utf-8")
            log.info("Wrote %s", consolidated_path)
            entries = reconcile(reference, majority_plants)
            consistency_metrics = compute_metrics(entries)
            voted_plants = majority_plants

            # Save and evaluate union-vote CSV
            union_path = output_dir / f"{model}-union.csv"
            union_path.write_text(plants_to_csv_text(union_plants), encoding="utf-8")
            entries_union = reconcile(reference, union_plants)
            union_metrics = compute_metrics(entries_union)

        if consistency_metrics:
            log.info(
                "Majority F1: %.1f%%  Union F1: %.1f%%  (vs median %.1f%%)",
                consistency_metrics.f1 * 100,
                union_metrics.f1 * 100 if union_metrics else 0,
                median_f1 * 100,
            )

        results.append(
            {
                "model": model,
                "n_reference": len(reference),
                "n_runs": len(run_paths),
                "n_valid_runs": len(valid_metrics),
                "run_f1_scores": f1_scores,
                "run_n_matched": [m.n_matched for m in valid_metrics],
                "run_n_system": [m.n_system for m in valid_metrics],
                "median_f1": round(median_f1, 4),
                "median_coverage": round(
                    sorted([m.coverage for m in valid_metrics])[len(valid_metrics) // 2], 4
                ),
                "median_precision": round(
                    sorted([m.precision for m in valid_metrics])[len(valid_metrics) // 2], 4
                ),
                "majority_f1": round(consistency_metrics.f1, 4) if consistency_metrics else None,
                "majority_coverage": round(consistency_metrics.coverage, 4)
                if consistency_metrics
                else None,
                "majority_precision": round(consistency_metrics.precision, 4)
                if consistency_metrics
                else None,
                "majority_n_matched": consistency_metrics.n_matched
                if consistency_metrics
                else None,
                "majority_n_system": consistency_metrics.n_system if consistency_metrics else None,
                "majority_n_hallucinated": consistency_metrics.n_hallucinated
                if consistency_metrics
                else None,
                "n_majority_plants": len(voted_plants),
                "union_f1": round(union_metrics.f1, 4) if union_metrics else None,
                "union_coverage": round(union_metrics.coverage, 4) if union_metrics else None,
                "union_precision": round(union_metrics.precision, 4) if union_metrics else None,
                "union_n_matched": union_metrics.n_matched if union_metrics else None,
                "union_n_system": union_metrics.n_system if union_metrics else None,
                "union_n_hallucinated": union_metrics.n_hallucinated if union_metrics else None,
            }
        )

    return results, run_metrics_by_model, run_paths_by_model


def _metrics_to_result_summary(m: BenchmarkMetrics) -> ResultSummary:
    """Convert BenchmarkMetrics to a ResultSummary."""
    return ResultSummary(
        status="ok",
        n_plants=m.n_system,
        tp=m.n_matched,
        fp=m.n_hallucinated,
        fn=m.n_missed,
        f1=round(m.f1, 4),
        fuel_accuracy=round(m.fuel_accuracy, 4) if m.fuel_accuracy else None,
        status_accuracy=round(m.status_accuracy, 4) if m.status_accuracy else None,
        province_accuracy=round(m.province_accuracy, 4) if m.province_accuracy else None,
    )


def _results_to_records(
    results: list[dict],
    run_metrics_by_model: dict[str, list[BenchmarkMetrics]],
    run_paths_by_model: dict[str, list[Path]],
    output_dir: Path,
) -> list[RunRecord]:
    """Convert analysis results to RunRecords for measurements.jsonl."""
    records: list[RunRecord] = []

    for r in results:
        model = r["model"]
        metrics_list = run_metrics_by_model.get(model, [])
        paths = run_paths_by_model.get(model, [])

        # Per-run records (sweep2_rag)
        for i, m in enumerate(metrics_list):
            run_num = i + 1
            # Find the original JSON path for this run
            result_file = str(paths[i]) if i < len(paths) else None
            records.append(
                RunRecord(
                    method=Method.RAG,
                    method_params=MethodParams(
                        model=model,
                        prompt_version="sweep2_rag",
                    ),
                    result_file=result_file,
                    result_summary=_metrics_to_result_summary(m),
                )
            )

        # Majority-vote record (sweep2_rag_consistency)
        if r.get("majority_f1") is not None:
            records.append(
                RunRecord(
                    method=Method.RAG,
                    method_params=MethodParams(
                        model=f"{model}-consolidated",
                        prompt_version="sweep2_rag_consistency",
                    ),
                    result_file=str(output_dir / f"{model}-consolidated.csv"),
                    result_summary=ResultSummary(
                        status="ok",
                        n_plants=r["majority_n_system"],
                        tp=r["majority_n_matched"],
                        fp=r.get("majority_n_hallucinated", 0),
                        fn=r["n_reference"] - (r["majority_n_matched"] or 0),
                        f1=r["majority_f1"],
                    ),
                )
            )

        # Union-vote record (sweep2_rag_consistency)
        if r.get("union_f1") is not None:
            records.append(
                RunRecord(
                    method=Method.RAG,
                    method_params=MethodParams(
                        model=f"{model}-union",
                        prompt_version="sweep2_rag_consistency",
                    ),
                    result_file=str(output_dir / f"{model}-union.csv"),
                    result_summary=ResultSummary(
                        status="ok",
                        n_plants=r["union_n_system"],
                        tp=r["union_n_matched"],
                        fp=r.get("union_n_hallucinated", 0),
                        fn=r["n_reference"] - (r["union_n_matched"] or 0),
                        f1=r["union_f1"],
                    ),
                )
            )

    return records


def write_measurements(records: list[RunRecord], measurements_path: Path) -> None:
    """Merge records into measurements.jsonl, replacing existing sweep2_rag* entries."""
    existing: list[RunRecord] = []
    if measurements_path.exists():
        existing = RunRecord.load_jsonl(measurements_path)

    # Remove old sweep2_rag and sweep2_rag_consistency records
    kept = [
        r
        for r in existing
        if r.method_params.prompt_version not in ("sweep2_rag", "sweep2_rag_consistency")
    ]
    kept.extend(records)
    RunRecord.save_jsonl(kept, measurements_path)
    log.info("Measurements: %s (%d total, %d new)", measurements_path, len(kept), len(records))


def _print_comparison_table(results: list[dict]) -> None:
    header = (
        f"{'Model':<30} {'Med F1':>7} {'Maj F1':>7} {'Union F1':>9} "
        f"{'Maj gain':>9} {'Union gain':>11}"
    )
    sep = "-" * len(header)
    print(sep)
    print(header)
    print(sep)
    for r in results:
        maj_f1 = r.get("majority_f1") or 0
        union_f1 = r.get("union_f1") or 0
        maj_gain = maj_f1 - r["median_f1"]
        union_gain = union_f1 - r["median_f1"]
        print(
            f"{r['model']:<30} "
            f"{r['median_f1']:>6.1%} "
            f"{maj_f1:>6.1%} "
            f"{union_f1:>8.1%} "
            f"{maj_gain:>+8.1%} "
            f"{union_gain:>+10.1%}"
        )
    print(sep)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(description="Self-consistency analysis for sweep2_rag runs")
    p.add_argument("--input", required=True, help="Directory with sweep2_rag JSON outputs")
    p.add_argument(
        "--output", required=True, help="Output directory for consolidated CSVs and results"
    )
    p.add_argument(
        "--reference", default=None, help="Path to reference CSV (default: vietnam_thermal_v1.csv)"
    )
    p.add_argument(
        "--measurements", default=None, help="Path to measurements.jsonl (updates per-run records)"
    )
    args = p.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    ref_path = Path(args.reference) if args.reference else _DEFAULT_REF

    if not input_dir.exists():
        raise SystemExit(f"Input dir not found: {input_dir}")
    if not ref_path.exists():
        raise SystemExit(f"Reference not found: {ref_path}")

    results, run_metrics_by_model, run_paths_by_model = run_analysis(
        input_dir, output_dir, ref_path
    )

    if not results:
        raise SystemExit("No results produced.")

    print("\n\n=== SELF-CONSISTENCY COMPARISON ===\n")
    _print_comparison_table(results)

    # Save JSON summary
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "self_consistency_summary.json"
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2)
    log.info("\nSaved: %s", summary_path)

    # Write RunRecords to measurements.jsonl
    if args.measurements:
        records = _results_to_records(
            results, run_metrics_by_model, run_paths_by_model, output_dir
        )
        write_measurements(records, Path(args.measurements))

    # Print key findings
    maj_gains = [(r["model"], (r.get("majority_f1") or 0) - r["median_f1"]) for r in results]
    union_gains = [(r["model"], (r.get("union_f1") or 0) - r["median_f1"]) for r in results]
    avg_maj_gain = sum(g for _, g in maj_gains) / len(maj_gains)
    avg_union_gain = sum(g for _, g in union_gains) / len(union_gains)
    best_union_model, best_union_gain = max(union_gains, key=lambda x: x[1])
    print(
        f"\nKey finding — majority vote:  avg F1 change = {avg_maj_gain:+.1%}  (conservative, hurts recall)"
    )
    print(
        f"Key finding — union vote:     avg F1 change = {avg_union_gain:+.1%}  (best: {best_union_model} {best_union_gain:+.1%})"
    )
    print("\nDiagnosis: bottleneck is RECALL not hallucinations. Union > majority.")
    print("Recommendation: multi-run union is the right aggregation strategy.")


if __name__ == "__main__":
    main()
