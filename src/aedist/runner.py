"""Command-line runner for the aedist benchmark.

Usage:
    aedist evaluate <system_csv> [--reference <ref_csv>]
    aedist evaluate-all [--output-dir <dir>]
"""

import argparse
import csv
import json
import logging
import re
import sys
from pathlib import Path

from pydantic import ValidationError

from .metrics import BenchmarkMetrics, compute_metrics, format_metrics
from .reconcile import reconcile
from .schema import (
    FuelType,
    Plant,
    PlantStatus,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

_FUEL_MAP = {
    "coal": FuelType.COAL,
    "gas": FuelType.GAS,
    "natural gas": FuelType.GAS,
    "local gas": FuelType.GAS,
    "local natural gas": FuelType.GAS,
    "lng": FuelType.IMPORTED_LNG,
    "imported lng": FuelType.IMPORTED_LNG,
    "imported gas": FuelType.IMPORTED_LNG,
    "oil": FuelType.OIL,
}

_STATUS_MAP = {
    "operational": PlantStatus.OPERATIONAL,
    "operating": PlantStatus.OPERATIONAL,
    "retired": PlantStatus.RETIRED,
    "constructing": PlantStatus.CONSTRUCTING,
    "construction": PlantStatus.CONSTRUCTING,
    "under construction": PlantStatus.CONSTRUCTING,
    "planned": PlantStatus.PLANNED,
    "proposed": PlantStatus.PROPOSED,
    "announced": PlantStatus.PROPOSED,
    "cancelled": PlantStatus.CANCELLED,
    "canceled": PlantStatus.CANCELLED,
    "shelved": PlantStatus.CANCELLED,
}


def _get(row: dict, col_map: dict, candidates: list[str]) -> str | None:
    for c in candidates:
        orig = col_map.get(c)
        if orig and row.get(orig):
            return row[orig]
    return None


def load_plants_csv(path: Path) -> list[Plant]:
    """Load a CSV file into a list of Plant objects."""
    plants: list[Plant] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return plants
        col_map = {c.strip().lower().replace(" ", "_"): c for c in reader.fieldnames}
        for row in reader:
            name = _get(row, col_map, ["name", "plant_name", "plant"])
            if not name:
                continue
            fuel_raw = _get(row, col_map, ["fuel", "fuel_type"])
            status_raw = _get(row, col_map, ["status", "construction_stage", "stage"])
            cod = _get(row, col_map, ["cod", "connection_date", "date"])
            province = _get(row, col_map, ["province", "location"])
            cap_raw = _get(row, col_map, ["capacity_mwe", "capacity", "generation_capacity"])

            fuel = (
                _FUEL_MAP.get(fuel_raw.strip().lower(), FuelType.UNKNOWN)
                if fuel_raw
                else FuelType.UNKNOWN
            )
            status = (
                _STATUS_MAP.get(status_raw.strip().lower(), PlantStatus.UNKNOWN)
                if status_raw
                else PlantStatus.UNKNOWN
            )

            cap = None
            if cap_raw:
                try:
                    cap = float(cap_raw.strip().replace(",", ""))
                except ValueError:
                    cap = None

            source_ref = _get(row, col_map, ["source_ref"])

            try:
                plants.append(
                    Plant(
                        name=name.strip(),
                        fuel=fuel,
                        status=status,
                        cod=cod.strip() if cod else None,
                        province=province.strip() if province else None,
                        capacity_mwe=cap,
                        source_ref=source_ref.strip() if source_ref else None,
                    )
                )
            except (ValueError, ValidationError):
                continue
    return plants


# ---------------------------------------------------------------------------
# Default reference path
# ---------------------------------------------------------------------------

_DEFAULT_REF = (
    Path(__file__).parent.parent.parent / "data" / "reference" / "vietnam_thermal_v1.csv"
)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def cmd_evaluate(args: argparse.Namespace) -> None:
    """Evaluate a single system output against the reference."""
    system_path = Path(args.system_csv)
    ref_path = Path(args.reference) if args.reference else _DEFAULT_REF

    reference = load_plants_csv(ref_path)
    system = load_plants_csv(system_path)

    log.info("Reference: %d plants from %s", len(reference), ref_path.name)
    log.info("System:    %d plants from %s", len(system), system_path.name)

    entries = reconcile(reference, system)
    metrics = compute_metrics(entries)
    log.info(format_metrics(metrics))

    if args.output:
        out = Path(args.output)
        recon_path = out / f"reconciliation_{system_path.stem}.csv"
        _save_reconciliation_csv(entries, recon_path)
        metrics_path = out / f"metrics_{system_path.stem}.json"
        _save_metrics_json(metrics, system_path.name, metrics_path)
        log.info("Saved: %s, %s", recon_path, metrics_path)


def _strip_run_suffix(name: str) -> str:
    """Remove -runN suffix from a model label: 'claude-opus-4.6-run1' → 'claude-opus-4.6'."""
    return re.sub(r"-run\d+$", "", name)


def _infer_method(dir_name: str) -> "Method":
    """Infer Method enum from output subdirectory name."""
    from .schema import Method

    if "multiturn" in dir_name:
        return Method.MULTITURN
    if "rag" in dir_name and "sourced" not in dir_name:
        return Method.RAG
    if "web" in dir_name:
        return Method.WEB
    if "decomposed" in dir_name:
        return Method.DECOMPOSED
    if "sourced" in dir_name:
        return Method.SOURCED
    if "frontier" in dir_name:
        return Method.FRONTIER
    if "verification" in dir_name:
        return Method.VERIFICATION
    return Method.SINGLE


def _backfill_resource_use(record: "RunRecord", json_path: Path) -> None:
    """Populate resource_use and model metadata from a companion JSON file."""
    from .schema import ResourceUse

    raw = json.loads(json_path.read_text(encoding="utf-8"))
    usage = raw.get("usage") or {}
    record.resource_use = ResourceUse(
        wall_s=raw.get("wall_seconds") or raw.get("total_wall_seconds"),
        cost_usd=raw.get("cost_usd") or raw.get("total_cost_usd"),
        tokens_in=usage.get("prompt_tokens"),
        tokens_out=usage.get("completion_tokens"),
    )
    record.method_params.model = raw.get("model", record.method_params.model)
    record.method_params.extra = raw.get("model_metadata")


def _metrics_to_runrecord(
    metrics: BenchmarkMetrics,
    label: str,
    result_file: str,
) -> "RunRecord":
    """Build a RunRecord from evaluation metrics.

    *result_file* should be a relative path (e.g. experiments/outputs/...).
    """
    from .schema import MethodParams, ResultSummary, RunRecord

    condition = label.split("/")[0] if "/" in label else ""
    stem = label.rsplit("/", 1)[-1]
    method = _infer_method(condition)

    return RunRecord(
        method=method,
        method_params=MethodParams(
            model=_strip_run_suffix(stem),
            prompt_version=condition,
        ),
        result_file=result_file,
        result_summary=ResultSummary(
            n_plants=metrics.n_system,
            tp=metrics.n_matched,
            fp=metrics.n_hallucinated,
            fn=metrics.n_missed,
            f1=metrics.f1,
            fuel_accuracy=metrics.fuel_accuracy,
            status_accuracy=metrics.status_accuracy,
            province_accuracy=metrics.province_accuracy,
        ),
    )


def cmd_evaluate_all(args: argparse.Namespace) -> None:
    """Evaluate all CSV files in the outputs directory."""
    outputs_dir = Path(args.outputs_dir) if args.outputs_dir else Path("outputs")
    ref_path = Path(args.reference) if args.reference else _DEFAULT_REF
    result_dir = Path(args.output) if args.output else Path("results/summary")
    result_dir.mkdir(parents=True, exist_ok=True)

    measurements_path = (
        Path(args.measurements_output)
        if args.measurements_output
        else result_dir / "measurements.jsonl"
    )

    # Compute project root for relative paths in RunRecords.
    # Walk up from measurements_path to find the repo root (contains pyproject.toml).
    project_root = measurements_path.resolve().parent
    for _ in range(10):
        if (project_root / "pyproject.toml").exists():
            break
        project_root = project_root.parent

    reference = load_plants_csv(ref_path)
    new_records: list = []

    evaluated_jsons: set[Path] = set()

    # Walk only immediate subdirs of outputs_dir — no recursion into
    # _extracted/ or legacy dirs (llm_direct, rag_curated, etc.)
    subdirs = sorted(p for p in outputs_dir.iterdir() if p.is_dir() and not p.name.startswith("_"))
    for subdir in subdirs:
        for csv_file in sorted(subdir.glob("*.csv")):
            system = load_plants_csv(csv_file)
            if not system:
                continue
            entries = reconcile(reference, system)
            metrics = compute_metrics(entries)
            label = f"{csv_file.parent.name}/{csv_file.stem}"
            try:
                rel_path = str(csv_file.resolve().relative_to(project_root))
            except ValueError:
                rel_path = str(csv_file)
            record = _metrics_to_runrecord(metrics, label, rel_path)
            # Backfill resource_use from companion JSON
            json_companion = csv_file.with_suffix(".json")
            if json_companion.exists():
                _backfill_resource_use(record, json_companion)
                evaluated_jsons.add(json_companion.resolve())
            new_records.append(record)
            log.info(
                "%s  cov=%.1f%%  prec=%.1f%%  F1=%.1f%%  (%d/%d)  $%.4f",
                label.ljust(50),
                metrics.coverage * 100,
                metrics.precision * 100,
                metrics.f1 * 100,
                metrics.n_matched,
                metrics.n_reference,
                record.resource_use.cost_usd or 0,
            )

    # Second pass: qualitative results (JSONs with no companion CSV)
    from .schema import MethodParams, ResultSummary, RunRecord

    for subdir in subdirs:
        for json_file in sorted(subdir.glob("*-run*.json")):
            if json_file.resolve() in evaluated_jsons:
                continue
            try:
                raw = json.loads(json_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                log.warning("Skipping unreadable JSON: %s", json_file)
                continue
            if "model" not in raw:
                continue
            dir_name = json_file.parent.name
            try:
                rel_path = str(json_file.resolve().relative_to(project_root))
            except ValueError:
                rel_path = str(json_file)
            record = RunRecord(
                method=_infer_method(dir_name),
                method_params=MethodParams(
                    model=raw["model"],
                    prompt_version=dir_name,
                ),
                result_file=rel_path,
                result_summary=ResultSummary(status="qualitative"),
            )
            _backfill_resource_use(record, json_file)
            new_records.append(record)
            log.info(
                "%s/%s  qualitative  $%.4f",
                dir_name,
                json_file.stem,
                record.resource_use.cost_usd or 0,
            )

    # Write measurements.jsonl (full rebuild — no merge with existing)
    if new_records:
        RunRecord.save_jsonl(new_records, measurements_path)
        log.info(
            "Measurements: %s (%d entries)",
            measurements_path,
            len(new_records),
        )


def _save_reconciliation_csv(entries: list, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "match_type",
                "reference_name",
                "system_name",
                "reference_province",
                "system_province",
                "reference_fuel",
                "system_fuel",
                "reference_capacity_mwe",
                "system_capacity_mwe",
                "capacity_diff_pct",
                "fuel_match",
                "status_match",
                "province_match",
                "reference_source_ref",
                "system_source_ref",
            ]
        )
        for e in entries:
            w.writerow(
                [
                    e.match_type.value,
                    e.reference_name,
                    e.system_name,
                    e.reference_province,
                    e.system_province,
                    e.reference_fuel,
                    e.system_fuel,
                    e.reference_capacity_mwe,
                    e.system_capacity_mwe,
                    e.capacity_diff_pct,
                    e.fuel_match,
                    e.status_match,
                    e.province_match,
                    e.reference_source_ref,
                    e.system_source_ref,
                ]
            )


def _metrics_to_dict(m: BenchmarkMetrics) -> dict:
    return {
        "coverage": m.coverage,
        "precision": m.precision,
        "f1": m.f1,
        "n_reference": m.n_reference,
        "n_system": m.n_system,
        "n_matched": m.n_matched,
        "n_exact": m.n_exact,
        "n_fuzzy": m.n_fuzzy,
        "n_missed": m.n_missed,
        "n_hallucinated": m.n_hallucinated,
        "fuel_accuracy": m.fuel_accuracy,
        "status_accuracy": m.status_accuracy,
        "province_accuracy": m.province_accuracy,
        "errors": m.errors,
    }


def _save_metrics_json(m: BenchmarkMetrics, label: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump({"label": label, **_metrics_to_dict(m)}, f, indent=2)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(prog="aedist", description="AEDIST benchmark tools")
    sub = parser.add_subparsers(dest="command")

    p_eval = sub.add_parser("evaluate", help="Evaluate one system output")
    p_eval.add_argument("system_csv", help="Path to system output CSV")
    p_eval.add_argument("--reference", help="Path to reference CSV")
    p_eval.add_argument("--output", help="Directory for reconciliation & metrics output")

    p_all = sub.add_parser("evaluate-all", help="Evaluate all outputs")
    p_all.add_argument("--outputs-dir", help="Directory containing system outputs")
    p_all.add_argument("--reference", help="Path to reference CSV")
    p_all.add_argument("--output", help="Directory for summary output")
    p_all.add_argument(
        "--measurements-output", help="Path to measurements.jsonl (also writes RunRecords)"
    )

    args = parser.parse_args()
    if args.command == "evaluate":
        cmd_evaluate(args)
    elif args.command == "evaluate-all":
        cmd_evaluate_all(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
