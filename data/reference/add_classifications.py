#!/usr/bin/env python3
"""Add international energy classification columns to reference CSVs.

Adds four columns to gem_thermal.csv and vietnam_thermal_v1.csv:
  - ires_code:    IRES (International Recommendations for Energy Statistics)
                  commodity code for the primary fuel
  - ires_label:   Human-readable IRES commodity label
  - isic_code:    ISIC Rev. 4 activity code
  - pypsa_carrier: PyPSA-Earth technology carrier string

ISIC Rev 4: D3510 for all thermal plants. Dual-fuel (gas/oil) classified
by primary fuel (natural gas) per IRES multi-fuel guidelines. See FUEL_MAP
for the complete mapping.
"""

import csv
import sys
from pathlib import Path

# (ires_code, ires_label, pypsa_carrier) keyed by lowercase fuel string.
FUEL_MAP: dict[str, tuple[str, str, str]] = {
    "coal": ("0121", "Hard coal", "coal"),
    "gas": ("0311", "Natural gas", "CCGT"),
    "gas/oil": ("0311", "Natural gas", "CCGT"),
    "oil": ("0241", "Fuel oil", "oil"),
    "lng": ("0320", "Liquefied natural gas", "CCGT"),
    "imported lng": ("0320", "Liquefied natural gas", "CCGT"),
    "diesel": ("0244", "Gas/diesel oil", "oil"),
}

ISIC_CODE = "D3510"


def add_columns(input_path: Path, fuel_col: str) -> None:
    """Read CSV, add classification columns, overwrite in place."""
    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"{input_path} has no header row")
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    new_cols = ("ires_code", "ires_label", "isic_code", "pypsa_carrier")
    for col in new_cols:
        if col in fieldnames:
            fieldnames.remove(col)
    fieldnames.extend(new_cols)

    unmapped: set[str] = set()
    for row in rows:
        fuel = row[fuel_col].strip().lower()
        if fuel in FUEL_MAP:
            code, label, carrier = FUEL_MAP[fuel]
            row["ires_code"] = code
            row["ires_label"] = label
            row["pypsa_carrier"] = carrier
        else:
            row["ires_code"] = ""
            row["ires_label"] = ""
            row["pypsa_carrier"] = ""
            unmapped.add(fuel)

        row["isic_code"] = ISIC_CODE

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
