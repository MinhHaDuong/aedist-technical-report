"""Verify internal coherence of the fusion master table + sidecar pair.

Runs three families of checks:

1. Sidecar row coverage  — provenance JSON row count == master CSV row count,
   names aligned positionally.
2. Sidecar null parity   — every non-null field in master has a provenance
   entry; every null field has no provenance entry.
3. Delegated checks      — calls check_coherence() from aedist.coherence
   (row-level, cross-row, aggregate).

Usage::

    uv run python scripts/verify/coherence_table.py \\
        --master derived/fusion_proto/master.csv \\
        --provenance derived/fusion_proto/master_provenance.json

    uv run python scripts/verify/coherence_table.py \\
        --master derived/fusion_proto/master.csv \\
        --provenance derived/fusion_proto/master_provenance.json \\
        --output reports/coherence_table.txt
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# "Null" semantics for Plant fields
# ---------------------------------------------------------------------------

# Fields whose null sentinel is the UNKNOWN enum value (not Python None).
# All other FIELDS use None as the null sentinel.
_ENUM_FIELDS = {"fuel", "status"}

# Canonical FIELDS from prototype_v1_fusion (same order as FIELDS constant).
_FIELDS = ("fuel", "capacity_mwe", "status", "province", "cod")


def _field_is_null(plant_value: Any, field: str) -> bool:
    """Return True when the plant field carries no real information."""
    if field in _ENUM_FIELDS:
        # FuelType.UNKNOWN / PlantStatus.UNKNOWN ⟹ no information
        return str(plant_value).lower() == "unknown"
    return plant_value is None


# ---------------------------------------------------------------------------
# Sidecar checks
# ---------------------------------------------------------------------------


def check_sidecar_row_coverage(
    plants: list,
    provenance: list[dict],
) -> list[str]:
    """Verify provenance array length and name alignment.

    Returns a list of human-readable failure messages (empty = pass).
    """
    failures: list[str] = []

    if len(provenance) != len(plants):
        failures.append(
            f"row count mismatch: master has {len(plants)} rows, "
            f"provenance has {len(provenance)} entries"
        )
        return failures  # alignment check meaningless without equal lengths

    for i, (plant, prov) in enumerate(zip(plants, provenance)):
        if plant.name != prov.get("name"):
            failures.append(
                f"name mismatch at row {i}: master={plant.name!r}, provenance={prov.get('name')!r}"
            )

    return failures


def check_sidecar_null_parity(
    plants: list,
    provenance: list[dict],
) -> list[str]:
    """Verify that provenance entries exist iff the master field is non-null.

    Precondition: len(plants) == len(provenance) (call after coverage check).
    Returns a list of human-readable failure messages (empty = pass).
    """
    failures: list[str] = []

    for i, (plant, prov) in enumerate(zip(plants, provenance)):
        prov_fields: dict = prov.get("fields", {})
        for field in _FIELDS:
            plant_value = getattr(plant, field, None)
            is_null = _field_is_null(plant_value, field)
            has_prov = field in prov_fields

            if not is_null and not has_prov:
                failures.append(
                    f"row {i} ({plant.name!r}): field {field!r} is non-null "
                    f"(value={plant_value!r}) but has no provenance entry"
                )
            elif is_null and has_prov:
                failures.append(
                    f"row {i} ({plant.name!r}): field {field!r} is null "
                    f"but provenance entry exists (source={prov_fields[field].get('source')!r})"
                )

    return failures


# ---------------------------------------------------------------------------
# Main verification runner
# ---------------------------------------------------------------------------


def run_verification(
    master_path: Path,
    provenance_path: Path,
) -> tuple[bool, list[str]]:
    """Load files, run all checks, return (all_passed, report_lines)."""
    from aedist.coherence import check_coherence
    from aedist.evaluate import load_plants_csv

    lines: list[str] = []
    all_passed = True

    # Load master CSV as Plant list
    plants = load_plants_csv(master_path)
    lines.append(f"Master CSV:     {master_path}  ({len(plants)} rows)")

    # Load provenance JSON
    with provenance_path.open(encoding="utf-8") as fh:
        provenance: list[dict] = json.load(fh)
    lines.append(f"Provenance JSON:{provenance_path}  ({len(provenance)} entries)")
    lines.append("")

    # 1. Sidecar row coverage
    coverage_failures = check_sidecar_row_coverage(plants, provenance)
    if coverage_failures:
        all_passed = False
        lines.append("FAIL  sidecar_row_coverage")
        for msg in coverage_failures:
            lines.append(f"      {msg}")
    else:
        lines.append("PASS  sidecar_row_coverage")

    # 2. Sidecar null parity (only if coverage passed — otherwise alignment is broken)
    if not coverage_failures:
        parity_failures = check_sidecar_null_parity(plants, provenance)
        if parity_failures:
            all_passed = False
            lines.append("FAIL  sidecar_null_parity")
            for msg in parity_failures:
                lines.append(f"      {msg}")
        else:
            lines.append("PASS  sidecar_null_parity")
    else:
        lines.append("SKIP  sidecar_null_parity  (coverage check failed)")

    # 3. Delegated coherence checks
    issues = check_coherence(plants)
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]

    if errors:
        all_passed = False
        lines.append(f"FAIL  check_coherence  ({len(errors)} errors, {len(warnings)} warnings)")
        for issue in errors:
            lines.append(f"      [ERROR] {issue.check}: {issue.message}")
        for issue in warnings:
            lines.append(f"      [WARN]  {issue.check}: {issue.message}")
    elif warnings:
        lines.append(f"WARN  check_coherence  (0 errors, {len(warnings)} warnings)")
        for issue in warnings:
            lines.append(f"      [WARN]  {issue.check}: {issue.message}")
    else:
        lines.append("PASS  check_coherence")

    lines.append("")
    lines.append("RESULT: " + ("ALL CHECKS PASSED" if all_passed else "FAILURES FOUND"))

    return all_passed, lines


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify internal coherence of the fusion master table + sidecar."
    )
    parser.add_argument(
        "--master",
        type=Path,
        required=True,
        help="Path to master.csv (output of prototype_v1_fusion).",
    )
    parser.add_argument(
        "--provenance",
        type=Path,
        required=True,
        help="Path to master_provenance.json (sidecar produced alongside master.csv).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path for the text report (also printed to stdout).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    all_passed, report_lines = run_verification(args.master, args.provenance)
    report = "\n".join(report_lines) + "\n"

    print(report, end="")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
