#!/usr/bin/env python3
"""Add international energy classification columns to reference CSVs.

Adds four columns to gem_thermal.csv and vietnam_thermal_v1.csv:
  - ires_code:    IRES (International Recommendations for Energy Statistics)
                  commodity code for the primary fuel
  - ires_label:   Human-readable IRES commodity label
  - isic_code:    ISIC Rev. 4 activity code
  - pypsa_carrier: PyPSA-Earth technology carrier string

Mapping reference
-----------------
| Fuel     | IRES code | IRES label              | PyPSA carrier |
|----------|-----------|-------------------------|---------------|
| Coal     | 0121      | Hard coal (anthracite,   | coal          |
|          |           | bituminous, sub-bit.)    |               |
| gas      | 0311      | Natural gas              | CCGT          |
| gas/oil  | 0311      | Natural gas (primary)    | CCGT          |
| oil      | 0241      | Fuel oil                 | oil           |
| LNG      | 0320      | Liquefied natural gas    | CCGT          |
| diesel   | 0244      | Gas/diesel oil           | oil           |

ISIC Rev 4: D3510 — Electric power generation, transmission and distribution
(same for all thermal plants).

gas/oil dual-fuel plants are classified by primary fuel (natural gas) per
IRES guidelines for multi-fuel plants.
"""

import csv
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Mapping tables
# ---------------------------------------------------------------------------

# Keys are lowercase fuel strings as they appear in the CSVs.
IRES_MAP: dict[str, tuple[str, str]] = {
    "coal": ("0121", "Hard coal"),
    "gas": ("0311", "Natural gas"),
    "gas/oil": ("0311", "Natural gas"),  # dual-fuel, primary = gas
    "oil": ("0241", "Fuel oil"),
    "lng": ("0320", "Liquefied natural gas"),
    "imported lng": ("0320", "Liquefied natural gas"),
    "diesel": ("0244", "Gas/diesel oil"),
}

PYPSA_MAP: dict[str, str] = {
    "coal": "coal",
    "gas": "CCGT",
    "gas/oil": "CCGT",
    "oil": "oil",
    "lng": "CCGT",
    "imported lng": "CCGT",
    "diesel": "oil",
}

ISIC_CODE = "D3510"  # Electric power generation


def add_columns(input_path: Path, fuel_col: str) -> None:
    """Read CSV, add classification columns, overwrite in place."""
    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"{input_path} has no header row")
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    # Remove old classification columns if re-running
    for col in ("ires_code", "ires_label", "isic_code", "pypsa_carrier"):
        if col in fieldnames:
            fieldnames.remove(col)

    # Append new columns
    fieldnames.extend(["ires_code", "ires_label", "isic_code", "pypsa_carrier"])

    unmapped: set[str] = set()
    for row in rows:
        fuel = row[fuel_col].strip().lower()
        if fuel in IRES_MAP:
            code, label = IRES_MAP[fuel]
            row["ires_code"] = code
            row["ires_label"] = label
        else:
            row["ires_code"] = ""
            row["ires_label"] = ""
            unmapped.add(fuel)

        row["isic_code"] = ISIC_CODE
        row["pypsa_carrier"] = PYPSA_MAP.get(fuel, "")

    if unmapped:
        print(f"WARNING: unmapped fuels in {input_path.name}: {unmapped}", file=sys.stderr)

    with open(input_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    mapped_count = sum(1 for r in rows if r["ires_code"])
    print(f"{input_path.name}: {mapped_count}/{len(rows)} plants mapped")


def main() -> None:
    here = Path(__file__).parent

    gem_path = here / "gem_thermal.csv"
    vtv_path = here / "vietnam_thermal_v1.csv"

    if gem_path.exists():
        add_columns(gem_path, fuel_col="Fuel")

    if vtv_path.exists():
        add_columns(vtv_path, fuel_col="fuel")


if __name__ == "__main__":
    main()
