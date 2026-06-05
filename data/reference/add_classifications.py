#!/usr/bin/env python3
"""Add international energy classification columns to a reference CSV.

Adds four columns, keyed on the CSV's fuel column:
  - ires_code:    IRES (International Recommendations for Energy Statistics)
                  commodity code for the primary fuel
  - ires_label:   Human-readable IRES commodity label
  - isic_code:    ISIC Rev. 4 activity code (D3510 for all thermal plants)
  - pypsa_carrier: PyPSA-Earth technology carrier string

ISIC Rev 4: D3510 for all thermal plants. Dual-fuel (gas/oil) classified by
primary fuel (natural gas) per IRES multi-fuel guidelines. See FUEL_MAP for the
complete mapping.

Ticket 0416 rewrote this from an in-place mutator (which classified both
gem_thermal.csv and the v1 reference) into an argparse input -> output
transform, so it slots into the acquire.mk reference pipe (extract -> aggregate
-> classify) without mutating its input. All I/O is text: ires_code is the
zero-prefixed string "0121", and writing it back as text is what stops the
0121 -> 121 coercion that motivated the v2 pipeline (ticket 0420).
"""

import argparse
import csv
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

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

NEW_COLUMNS = ("ires_code", "ires_label", "isic_code", "pypsa_carrier")


def add_columns(input_path: Path, output_path: Path, fuel_col: str) -> None:
    """Read a CSV, add classification columns, and write to a distinct output.

    The input is never mutated. Unmapped fuels get blank IRES fields (and a
    warning) rather than aborting — a missing classification is a data gap, not
    a structural error.
    """
    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"{input_path} has no header row")
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    if fuel_col not in fieldnames:
        raise ValueError(f"{input_path} has no {fuel_col!r} column (columns: {fieldnames})")

    for col in NEW_COLUMNS:
        if col in fieldnames:
            fieldnames.remove(col)
    fieldnames.extend(NEW_COLUMNS)

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
        logger.warning("Unmapped fuels in %s: %s", input_path.name, sorted(unmapped))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    mapped_count = sum(1 for r in rows if r["ires_code"])
    logger.info("%s -> %s: %d/%d rows classified", input_path.name, output_path.name, mapped_count, len(rows))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/reference/vietnam_thermal_plants_v2.csv"),
        help="Path to the plant CSV to classify (default: %(default)s).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/reference/vietnam_thermal_plants_v2_classified.csv"),
        help="Path for the classified CSV (default: %(default)s). Distinct from "
        "--input: this step is a transform, never an in-place mutation.",
    )
    parser.add_argument(
        "--fuel-col",
        default="fuel",
        help="Name of the fuel column to classify on (default: %(default)s).",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        add_columns(args.input, args.output, fuel_col=args.fuel_col)
    except ValueError as exc:
        logger.error("Classification refused: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
