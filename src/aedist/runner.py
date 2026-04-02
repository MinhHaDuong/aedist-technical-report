"""Command-line runner for the aedist benchmark.

Usage:
    aedist evaluate <system_csv> [--reference <ref_csv>]
    aedist evaluate-all [--output-dir <dir>]
"""

import argparse
import csv
import json
import sys
from pathlib import Path

from .metrics import BenchmarkMetrics, compute_metrics, format_metrics
from .reconcile import reconcile
from .schema import FuelType, Plant, PlantStatus


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

            fuel = _FUEL_MAP.get(fuel_raw.strip().lower(), FuelType.UNKNOWN) if fuel_raw else FuelType.UNKNOWN
            status = _STATUS_MAP.get(status_raw.strip().lower(), PlantStatus.UNKNOWN) if status_raw else PlantStatus.UNKNOWN

            cap = None
            if cap_raw:
                try:
                    cap = float(cap_raw.strip().replace(",", ""))
                except ValueError:
                    cap = None

            plants.append(Plant(
                name=name.strip(),
                fuel=fuel,
                status=status,
                cod=cod.strip() if cod else None,
                province=province.strip() if province else None,
                capacity_mwe=cap,
            ))
    return plants


# ---------------------------------------------------------------------------
# Default reference path
# ---------------------------------------------------------------------------

_DEFAULT_REF = Path(__file__).parent.parent.parent / "data" / "reference" / "vietnam_thermal_v1.csv"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_evaluate(args: argparse.Namespace) -> None:
    """Evaluate a single system output against the reference."""
    system_path = Path(args.system_csv)
    ref_path = Path(args.reference) if args.reference else _DEFAULT_REF

    reference = load_plants_csv(ref_path)
    system = load_plants_csv(system_path)

    print(f"Reference: {len(reference)} plants from {ref_path.name}")
    print(f"System:    {len(system)} plants from {system_path.name}")
    print()

    entries = reconcile(reference, system)
    metrics = compute_metrics(entries)
    print(format_metrics(metrics))

    if args.output:
        out = Path(args.output)
        # Save reconciliation table
        recon_path = out / f"reconciliation_{system_path.stem}.csv"
        _save_reconciliation_csv(entries, recon_path)
        # Save metrics
        metrics_path = out / f"metrics_{system_path.stem}.json"
        _save_metrics_json(metrics, system_path.name, metrics_path)
        print(f"\nSaved: {recon_path}, {metrics_path}")


def cmd_evaluate_all(args: argparse.Namespace) -> None:
    """Evaluate all CSV files in the outputs directory."""
    outputs_dir = Path(args.outputs_dir) if args.outputs_dir else Path("outputs")
    ref_path = Path(args.reference) if args.reference else _DEFAULT_REF
    result_dir = Path(args.output) if args.output else Path("results/summary")
    result_dir.mkdir(parents=True, exist_ok=True)

    reference = load_plants_csv(ref_path)
    all_metrics = []

    for csv_file in sorted(outputs_dir.rglob("*.csv")):
        system = load_plants_csv(csv_file)
        if not system:
            continue
        entries = reconcile(reference, system)
        metrics = compute_metrics(entries)
        label = f"{csv_file.parent.name}/{csv_file.stem}"
        all_metrics.append({"label": label, **_metrics_to_dict(metrics)})
        print(f"{label:50s}  cov={metrics.coverage:.1%}  prec={metrics.precision:.1%}  F1={metrics.f1:.1%}  ({metrics.n_matched}/{metrics.n_reference})")

    summary_path = result_dir / "all_metrics.json"
    with open(summary_path, "w") as f:
        json.dump(all_metrics, f, indent=2)
    print(f"\nSummary: {summary_path}")


def _save_reconciliation_csv(entries: list, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "match_type", "reference_name", "system_name",
            "reference_province", "system_province",
            "reference_fuel", "system_fuel",
            "reference_capacity_mwe", "system_capacity_mwe",
            "capacity_diff_pct", "fuel_match", "status_match", "province_match",
        ])
        for e in entries:
            w.writerow([
                e.match_type.value, e.reference_name, e.system_name,
                e.reference_province, e.system_province,
                e.reference_fuel, e.system_fuel,
                e.reference_capacity_mwe, e.system_capacity_mwe,
                e.capacity_diff_pct, e.fuel_match, e.status_match, e.province_match,
            ])


def _metrics_to_dict(m: BenchmarkMetrics) -> dict:
    return {
        "coverage": m.coverage, "precision": m.precision, "f1": m.f1,
        "n_reference": m.n_reference, "n_system": m.n_system,
        "n_matched": m.n_matched, "n_exact": m.n_exact, "n_fuzzy": m.n_fuzzy,
        "n_missed": m.n_missed, "n_hallucinated": m.n_hallucinated,
        "fuel_accuracy": m.fuel_accuracy, "status_accuracy": m.status_accuracy,
        "province_accuracy": m.province_accuracy,
        "errors": m.errors,
    }


def _save_metrics_json(m: BenchmarkMetrics, label: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump({"label": label, **_metrics_to_dict(m)}, f, indent=2)


def main() -> None:
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
