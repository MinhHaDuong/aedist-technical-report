"""Aggregate the GEM unit-grain CSV up to plant grain.

Consumes `gem_units.csv` (the tracked GEM export, 308 units) and rolls unit
rows into plant rows, producing `gem_thermal.csv` (153 plants). This is the
single reproducible aggregation step for the GEM cross-check data (ticket 0429);
it replaces the lost `GEM.csv → GEM_aggregate.py` hand chain with an
argparse-driven input → output transform.

The GEM data model differs from the master's three-column address scheme: Phase
is embedded in the `Unit name` column (e.g. "Phase 1 Unit 2"), and Phase-name
appending is what creates unique plant keys for phase-split plants (e.g.
"An Khanh Phase 1" vs "An Khanh Phase 2"). This Phase-splitting logic is kept
exactly as the original, since changing it would alter the comparator output.

The tracked raw input is `gem_units.csv` — confirmed to reproduce `gem_thermal.csv`
(before classification columns) exactly. The full chain is:
  gem_units.csv → GEM_aggregate.py → add_classifications.py → gem_thermal.csv

One invariant, adapted from aggregate_units.py (ticket 0416):
- OUTPUT: the composite key (Name, Aggregated Units) must be unique. GEM's data
  model intentionally lists the same physical plant in multiple rows with different
  fuels or statuses; bare Name is not unique. The guard fires on truly duplicate
  rows (same Name AND same Aggregated Units) — a structural aggregation bug.

Run as a script (argparse) or import the helpers for testing. Self-contained
(stdlib + pandas) so it runs via `python data/reference/GEM_aggregate.py`.
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def validate_output_unique_plants(out: pd.DataFrame) -> None:
    """Refuse the plant table unless (Name, Aggregated Units) is a strict unique key.

    GEM's data model differs from the master's: the same physical plant can appear
    in multiple rows with different fuel types or statuses (e.g. Ba Ria: operating
    gas + cancelled gas). Name alone is not unique — that is intentional GEM
    behaviour, not a data error. The real unique key is (Name, Aggregated Units):
    the unit-name string encodes the physical configuration and disambiguates
    rows that share a plant name.

    A duplicate (Name, Aggregated Units) pair means the aggregation logic produced
    the same output row twice — a structural bug. The message lists the offending
    composites for diagnosis.
    """
    key_cols = ["Name", "Aggregated Units"]
    dup_mask = out.duplicated(subset=key_cols, keep=False)
    if dup_mask.any():
        dups = out.loc[dup_mask, key_cols].drop_duplicates()
        lines = [f"{r['Name']!r} / {r['Aggregated Units']!r}" for _, r in dups.iterrows()]
        raise ValueError(
            "(Name, Aggregated Units) must be unique — these rows appear more than once:\n  "
            + "\n  ".join(sorted(lines))
        )


def aggregate_table(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate GEM unit rows into plant rows.

    Phase-split logic: Phase is embedded in Unit name ("Phase 1 Unit 2").
    Phase info is appended to Plant name so that plants with distinct phases
    get distinct keys — this is what makes the plant name unique across
    phases of the same parent plant.

    Groupable units (Unit N, Phase N, Extension, CC N, plain digits) are
    summed by (Plant name, Province, Fuel, Status, Extension). Non-groupable
    rows (e.g. a unit whose name is already the plant designation) pass through.

    The uniqueness guard fires on the output before returning.
    """
    df = df.copy()
    # Extract Phase information (supports both Arabic and Roman numerals) from Unit name
    df["Phase"] = df["Unit name"].str.extract(r"(Phase [IVXLCDM0-9]+)")
    df["Extension"] = df["Unit name"].str.contains("Extension", case=False, na=False)

    # Append Phase name to Plant name (if Phase exists), ensuring a space is added
    df["Plant name"] = df["Plant name"] + df["Phase"].fillna("").apply(
        lambda x: f" {x}" if x else ""
    )

    # Identify rows that should be grouped:
    # - "Unit X"
    # - "Phase X"
    # - "Extension"
    # - "CCX"
    # - Plain numeric strings (^\d+$)
    df["Groupable"] = df["Unit name"].str.contains(
        r"(?:^\d+$|Unit \d+|Phase [IVXLCDM0-9]+|Extension|CC\d+)", case=False, na=False
    )

    # Separate groupable and non-groupable rows
    non_groupable = df[~df["Groupable"]].copy()
    non_groupable.rename(columns={"Unit name": "Aggregated Units"}, inplace=True)

    # Group groupable rows by Plant name, Province, Fuel, and Status
    groupable = df[df["Groupable"]]
    aggregated_groupable = (
        groupable.groupby(
            ["Plant name", "Province", "Fuel", "Status", "Extension"], dropna=False
        )
        .agg(
            {
                "Capacity": "sum",  # Sum the capacity numerically
                "Unit name": lambda x: ", ".join(x),  # List all units aggregated
            }
        )
        .reset_index()
    )

    # Drop the intermediate column
    aggregated_groupable.drop(columns=["Extension"], inplace=True)

    # Rename the "Unit name" column to "Aggregated Units" for clarity
    aggregated_groupable.rename(columns={"Unit name": "Aggregated Units"}, inplace=True)

    # Reorder the columns for groupable
    aggregated_groupable = aggregated_groupable[
        ["Plant name", "Province", "Fuel", "Capacity", "Status", "Aggregated Units"]
    ]

    # For non-groupable rows, select the same columns
    non_groupable = non_groupable[
        ["Plant name", "Province", "Fuel", "Capacity", "Status", "Aggregated Units"]
    ]

    # Combine groupable and non-groupable rows
    final_df = pd.concat([aggregated_groupable, non_groupable], ignore_index=True)

    # Rename the first column to "Name"
    final_df.rename(columns={"Plant name": "Name"}, inplace=True)

    # Sort the final DataFrame for better readability
    final_df = final_df.sort_values(by=["Name", "Province", "Status"]).reset_index(
        drop=True
    )

    validate_output_unique_plants(final_df)
    return final_df


def aggregate_file(input_path: Path, output_path: Path) -> pd.DataFrame:
    """Read the GEM unit CSV, aggregate to plants, and write the output CSV."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    logger.info("Reading %s", input_path)
    df = pd.read_csv(input_path)
    logger.info("Read %d unit rows, %d columns", len(df), len(df.columns))

    plants = aggregate_table(df)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plants.to_csv(output_path, index=False)
    logger.info("Wrote %d plant rows to %s", len(plants), output_path)
    return plants


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/reference/gem_units.csv"),
        help="Path to the GEM unit-grain CSV (default: %(default)s).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/reference/gem_thermal_aggregated.csv"),
        help="Path for the aggregated plant CSV (default: %(default)s). "
        "Run add_classifications.py afterwards to add classification columns "
        "(ires_code, ires_label, isic_code, pypsa_carrier) to produce gem_thermal.csv.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        aggregate_file(args.input, args.output)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Aggregation refused: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
