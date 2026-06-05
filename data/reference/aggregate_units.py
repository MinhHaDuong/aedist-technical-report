"""Aggregate the unit-grain reference CSV up to plant grain.

Consumes the CSV produced by `extract_ods.py` (ticket 0420) and rolls unit
rows into plant rows. Replaces the lost `HDM_aggregate.py`, whose
`normalize_plant_name` parsed "X Unit N" off the name string to find the
parent — a forbidden name synthesis (author doctrine, ticket 0416).

Under the three-column address contract (ticket 0439) parentage is DATA: a
unit row names its parent in the `plant` column, so grouping is a pure
`groupby(plant)`. No name string is parsed anywhere. The output plant name is
the `plant` cell verbatim (or `complex` for complex-grain rows) — never
invented.

Grain handling (contrat v2, ticket 0416):
  - unit-grain rows (Unit non-empty) aggregate into their Plant;
  - plant-grain rows (Plant set, Unit empty) pass through as plants;
  - complex-grain rows (Complex set, Plant empty) pass through keyed on the
    Complex cell — the 19 LNG complexes not yet split into named plants.

Two invariants, mirroring extract_ods.py:

1. **All-text I/O.** Every cell is read and written as a string; the one
   numeric op is the explicit capacity sum (parse -> add -> render), so a
   leading-zero `ires_code` can never be coerced (the 0121 -> 121 defect).
2. **Hard validation, no tolerance.**
   - INPUT: a duplicated unit row (same designation twice) aborts — the
     "Quảng Trị 1 Unit 2" x2 case must fail, never sum 660+660. Redundant
     with extract_ods by design (defense in depth).
   - OUTPUT: a repeated plant name (the key is unique), a unit repeated in
     one plant's Units Included, or a unit landing in two groups is a refusal
     listing the offending groups, for resolution in the master.

Status legitimately VARIES across units of one plant (units commission and
retire in phases — Dong Nai Formosa operating+announced, Uong Bi I
operating+retired), so it is collapsed (operating wins; else the most-advanced
pre-operating stage), never asserted constant. Province and asset_type are
plant-invariant and asserted constant — a violation is a master error.

Run as a script (argparse) or import the helpers for testing. Self-contained
(stdlib + pandas) so it runs via `python data/reference/aggregate_units.py`
without package machinery.
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# asset_type (master, fine grain) -> v1 fuel label. The pipe owns the fuel
# derivation (contrat v2, ticket 0416; same doctrine as the status projection
# in extract_ods). An unknown asset_type raises KeyError loudly — a new asset
# class must be mapped deliberately, never emit a blank fuel.
ASSET_TYPE_TO_FUEL: dict[str, str] = {
    "Coal power plant": "coal",
    "Coal cogen plant": "coal",
    "Gas power plant": "gas",
    "Gas/Oil power plant": "gas/oil",
}

# Ordinal status ladder (master Conventions sheet, ticket 0439). Index = rung.
# Mirrors extract_ods.STATUS_VOCABULARY; kept local so the aggregator stays
# importable without the extractor. The status projected onto v1 vocabulary is
# the consumer's job at adoption (0413); v2 carries the raw stage.
STATUS_LADDER = (
    "0 exploring",
    "1 announced",
    "2 proposed",
    "3 added to PDP",
    "4 permitted",
    "5 construction",
    "6 operating",
    "9 cancelled",
    "10 retired",
)
OPERATING = "6 operating"

# Plant-invariant columns: every unit of a plant must agree on these. A
# disagreement is a master data error, not something to collapse silently.
INVARIANT_COLUMNS = ("province", "asset_type")


def derive_fuel(asset_type: str) -> str:
    """Map a master asset_type onto the v1 fuel label.

    Exhaustive lookup — an unmapped asset_type raises KeyError (never a .get
    default): silently emitting a blank fuel would break add_classifications
    downstream and corrupt scoring.
    """
    return ASSET_TYPE_TO_FUEL[asset_type]


def plant_key(row: pd.Series) -> str:
    """The plant-level identity of a row: its `plant` cell, or `complex` for a
    complex-grain row (plant empty). Pure data lookup — no name parsing."""
    plant = (row["plant"] or "").strip()
    if plant:
        return plant
    return (row["complex"] or "").strip()


def collapse_status(statuses: list[str]) -> str:
    """Collapse the per-unit statuses of a plant into one plant status.

    Units of one plant commission and retire in phases, so status genuinely
    varies. A naive numeric max is wrong (retired=10 outranks operating=6, yet
    a plant with one operating unit operates). Rule: if ANY unit is operating,
    the plant is operating; otherwise the most-advanced pre-operating stage
    (highest ladder rung below operating, falling back to the highest rung if
    all are post-operating — cancelled/retired only).
    """
    if OPERATING in statuses:
        return OPERATING
    operating_rung = STATUS_LADDER.index(OPERATING)
    rung = {s: STATUS_LADDER.index(s) for s in statuses}
    pre = [s for s in statuses if rung[s] < operating_rung]
    pool = pre or statuses
    return max(pool, key=lambda s: rung[s])


def validate_input_no_duplicate_units(df: pd.DataFrame) -> None:
    """Abort if any designation (`name`) appears more than once in the input.

    A duplicated unit row would be summed into a doubled plant capacity (the
    "Quảng Trị 1 Unit 2" x2 -> 1320 defect). The message lists each offending
    designation so the author can fix the master and re-import.
    """
    names = df["name"]
    duplicated = names[names.duplicated(keep=False)]
    if duplicated.empty:
        return
    offenders = sorted(set(duplicated))
    raise ValueError(
        "Duplicated unit rows in the input CSV — a duplicate would double the "
        "plant capacity. Fix the master and re-import. Offending designations:"
        "\n  " + "\n  ".join(offenders)
    )


def validate_capacity_numeric(df: pd.DataFrame) -> None:
    """Abort if any capacity cell is non-empty and non-numeric.

    A spreadsheet error value (e.g. `Err:510`, a leaked circular-reference /
    formula error) is corruption, not data — summing around it would silently
    understate the plant. Empty is allowed (legitimately-unknown capacity,
    summed as 0). The message names the offending rows for a master fix.
    """
    offenders = []
    for name, value in zip(df["name"], df["capacity_mwe"], strict=True):
        cell = value.strip()
        if not cell:
            continue
        try:
            float(cell)
        except ValueError:
            offenders.append(f"{name!r}: capacity={cell!r}")
    if offenders:
        raise ValueError(
            "Non-numeric capacity cells in the input — a spreadsheet formula "
            "error (e.g. Err:510) leaked into the master. Fix the formula in "
            "the master and re-import:\n  " + "\n  ".join(offenders)
        )


def validate_output_unique_plants(out: pd.DataFrame) -> None:
    """Refuse the plant table unless the plant name is a strict unique key.

    Three structural faults, each listing the offending groups for resolution
    in the master:
      - a plant name appearing twice (the key is not unique);
      - a unit repeated within one plant's `units_included`;
      - a unit appearing in two different plants' `units_included`.
    """
    dup_names = sorted(set(out["name"][out["name"].duplicated(keep=False)]))
    if dup_names:
        raise ValueError(
            "Plant name is the unique key but these appear more than once — "
            "resolve in the master:\n  " + "\n  ".join(dup_names)
        )

    seen: dict[str, str] = {}
    repeated_within: list[str] = []
    across: list[str] = []
    for _, row in out.iterrows():
        units = [u.strip() for u in row["units_included"].split(",") if u.strip()]
        local_seen: set[str] = set()
        for unit in units:
            if unit in local_seen:
                repeated_within.append(f"{unit!r} (plant {row['name']!r})")
            local_seen.add(unit)
            if unit in seen and seen[unit] != row["name"]:
                across.append(f"{unit!r} (plants {seen[unit]!r} and {row['name']!r})")
            seen[unit] = row["name"]

    if repeated_within:
        raise ValueError(
            "Units repeated within one plant's Units Included — resolve in the "
            "master:\n  " + "\n  ".join(sorted(set(repeated_within)))
        )
    if across:
        raise ValueError(
            "Units appearing in two plant groups — resolve in the master:\n  "
            + "\n  ".join(sorted(set(across)))
        )


def _assert_invariant_columns(key: str, group: pd.DataFrame) -> None:
    """Every unit of a plant must agree on the plant-invariant columns."""
    for col in INVARIANT_COLUMNS:
        values = sorted(set(group[col]))
        if len(values) > 1:
            raise ValueError(
                f"Plant {key!r} has units disagreeing on {col!r}: {values}. "
                "A plant cannot span two values — resolve in the master."
            )


def aggregate(df: pd.DataFrame) -> pd.DataFrame:
    """Roll unit-grain rows up to plant grain.

    Validates the input, groups by the data-carried plant key (never a parsed
    name), sums capacity as an explicit numeric op, collapses status, derives
    fuel from asset_type, and validates the output before returning.
    """
    df = df.fillna("").astype(str)
    validate_input_no_duplicate_units(df)
    validate_capacity_numeric(df)

    df = df.copy()
    df["_key"] = df.apply(plant_key, axis=1)

    records = []
    for key, group in df.groupby("_key", sort=True):
        _assert_invariant_columns(key, group)
        capacity = sum(int(float(c)) for c in group["capacity_mwe"] if c.strip())
        units_included = ", ".join(sorted(group["name"]))
        records.append(
            {
                "name": key,
                "province": group["province"].iloc[0],
                "fuel": derive_fuel(group["asset_type"].iloc[0]),
                "capacity_mwe": str(capacity),
                "status": collapse_status(list(group["status"])),
                "units_included": units_included,
                # The output is plant-grain by construction: every row is a
                # plant, whether rolled up from units or passed through from a
                # plant-/complex-grain input row.
                "level": "plant",
            }
        )

    out = pd.DataFrame.from_records(records)
    validate_output_unique_plants(out)
    return out


def aggregate_file(input_path: Path, output_path: Path) -> pd.DataFrame:
    """Read the unit CSV (all text), aggregate to plants, and write the CSV."""
    logger.info("Reading %s (dtype=str)", input_path)
    units = pd.read_csv(input_path, dtype=str).fillna("")
    logger.info("Read %d unit rows", len(units))

    plants = aggregate(units)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plants.to_csv(output_path, index=False)
    logger.info("Wrote %d plant rows to %s", len(plants), output_path)
    return plants


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/reference/vietnam_thermal_units_v2.csv"),
        help="Path to the unit-grain CSV from extract_ods.py (default: %(default)s).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/reference/vietnam_thermal_plants_v2.csv"),
        help="Path for the aggregated plant CSV (default: %(default)s).",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        aggregate_file(args.input, args.output)
    except ValueError as exc:
        logger.error("Aggregation refused: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
