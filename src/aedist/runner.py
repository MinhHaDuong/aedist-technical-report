"""Command-line runner for the aedist benchmark.

Usage:
    aedist evaluate <system_csv> [--reference <ref_csv>]
    aedist evaluate-all [--output-dir <dir>]
"""

import argparse
import csv
import json
import logging
import sys
from pathlib import Path

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


def _metrics_to_runrecord(
    metrics: BenchmarkMetrics,
    label: str,
    csv_file: Path,
) -> "RunRecord":
    """Build a RunRecord from evaluation metrics."""
    from .schema import Method, MethodParams, ResultSummary, RunRecord

    sweep_name = csv_file.parent.name
    method = Method.SINGLE
    if "multiturn" in sweep_name:
        method = Method.MULTITURN
    elif "rag" in sweep_name:
        method = Method.RAG
    elif "web" in sweep_name:
        method = Method.WEB

    return RunRecord(
        method=method,
        method_params=MethodParams(
            model=label.rsplit("/", 1)[-1],
            prompt_version=sweep_name,
        ),
        result_file=str(csv_file),
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

    measurements_path = Path(args.measurements_output) if args.measurements_output else None

    reference = load_plants_csv(ref_path)
    new_metrics = []
    new_records: list = []

    for csv_file in sorted(outputs_dir.rglob("*.csv")):
        system = load_plants_csv(csv_file)
        if not system:
            continue
        entries = reconcile(reference, system)
        metrics = compute_metrics(entries)
        label = f"{csv_file.parent.name}/{csv_file.stem}"
        new_metrics.append({"label": label, **_metrics_to_dict(metrics)})
        new_records.append(_metrics_to_runrecord(metrics, label, csv_file))
        log.info(
            "%s  cov=%.1f%%  prec=%.1f%%  F1=%.1f%%  (%d/%d)",
            label.ljust(50),
            metrics.coverage * 100,
            metrics.precision * 100,
            metrics.f1 * 100,
            metrics.n_matched,
            metrics.n_reference,
        )

    # Merge with existing metrics (preserve data from other sweeps)
    summary_path = result_dir / "all_metrics.json"
    existing: list[dict] = []
    if summary_path.exists():
        try:
            existing = json.loads(summary_path.read_text())
        except (json.JSONDecodeError, OSError):
            log.warning("Could not read existing %s, starting fresh", summary_path)

    # Build set of new labels for replacement
    new_labels = {m["label"] for m in new_metrics}
    # Keep existing entries whose labels are not being replaced
    merged = [m for m in existing if m["label"] not in new_labels]
    merged.extend(new_metrics)

    with open(summary_path, "w") as f:
        json.dump(merged, f, indent=2)
    log.info("Summary: %s (%d entries, %d new)", summary_path, len(merged), len(new_metrics))

    # Write measurements.jsonl if requested
    if measurements_path and new_records:
        from .schema import RunRecord

        existing_records = []
        if measurements_path.exists():
            existing_records = RunRecord.load_jsonl(measurements_path)
        # Replace records with matching labels
        existing_labels = {
            f"{r.method_params.prompt_version}/{Path(r.result_file).stem}" for r in new_records
        }
        kept = [
            r
            for r in existing_records
            if f"{r.method_params.prompt_version}/{Path(r.result_file).stem}"
            not in existing_labels
        ]
        kept.extend(new_records)
        RunRecord.save_jsonl(kept, measurements_path)
        log.info(
            "Measurements: %s (%d entries, %d new)",
            measurements_path,
            len(kept),
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
