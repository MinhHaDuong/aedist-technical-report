"""Extract the Vietnam thermal-units reference list from the master ODS.

Reads the "Power plants" sheet of the imported `pipeline.ods` snapshot and
writes a curated CSV. This is the single, reproducible extraction step of the
reference pipeline (ticket 0420); it replaces the lost manual-export chain
(`pipeline.ods` -> hand export -> HDM.csv -> ...) that let the `ires_code`
zero-prefix coercion (0121 -> 121) slip through.

Since ticket 0439 the master carries a three-column address — `Complex |
Plant | Unit` (one denormalized table, dimension-path pattern). Parentage is
data, never an inference from name strings. Empty cells are declared
semantics: Unit empty means the row IS the plant (unknown split); Complex
empty means a standalone plant; Complex alone means a complex-grain row.
`name` (the attested designation) and `level` (the finest non-empty address
column, ticket 0401) are derived here.

Two invariants are non-negotiable:

1. **dtype=str throughout.** Every value is read as a string and stays a
   string. No numeric coercion, ever — leading zeros survive by construction.
2. **Hard validation, no tolerance.** A duplicate designation (modulo
   diacritics) or an address-shape violation aborts extraction with an
   actionable message. No CSV is written. Corrections belong in the master,
   not here. (Deeper conventions — grain exclusivity, controlled status
   vocabulary — are the 0416 contrat v2 layer.)

Run as a script (argparse) or import the validators for testing. Kept
self-contained (stdlib + pandas) so it runs via `python data/reference/
extract_ods.py` without package machinery.
"""

import argparse
import logging
import sys
import unicodedata
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Sheet and header layout of the master ODS, confirmed by inspection:
# row 0 = title, rows 1-3 = metadata/sub-headers, row 4 (0-indexed) = the
# actual column names.
SHEET_NAME = "Power plants"
HEADER_ROW = 4

# The three-column address (ticket 0439). Order matters: finest grain last.
ADDRESS_COLUMNS = ["Complex", "Plant", "Unit"]

# Source -> output column mapping. `name` and `level` are derived, not mapped.
COLUMN_MAP = {
    "Complex": "complex",
    "Plant": "plant",
    "Unit": "unit",
    "Province / Tỉnh": "province",
    "Asset type": "asset_type",
    "Capacity (MW)": "capacity_mwe",
    "Project stage": "status",
}

# Closed status vocabulary (master Conventions sheet, ratified 2026-06-05):
# a single ordinal ladder, rungs 7-8 reserved for future extension. Any value
# outside this list is a data-entry error — hard stop, no silent coercion.
STATUS_VOCABULARY = (
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

# Project stage (master, fine grain) -> v1-compatible reference status.
# The master keeps the fine grain; the pipe owns the derivation (same doctrine
# as Fuel, 0439 convention 4). "4 permitted -> planned" reads "planned" as
# *inscribed in the plan / authorized* (PDP reading) — if "planned" ever came
# to mean ready-to-build, that row must be revisited. NOT wired to extraction
# output: v2 carries the raw stage; consumers project at 0413 adoption time.
V1_STATUS_BY_STAGE = {
    "0 exploring": "proposed",
    "1 announced": "proposed",
    "2 proposed": "proposed",
    "3 added to PDP": "planned",
    "4 permitted": "planned",
    "5 construction": "constructing",
    "6 operating": "operational",
    "9 cancelled": "cancelled",
    "10 retired": "retired",
}
assert set(V1_STATUS_BY_STAGE) == set(STATUS_VOCABULARY)


def derive_v1_status(stage: str) -> str:
    """Project a master stage onto the 6-status v1 vocabulary.

    Exhaustive table lookup — an unknown stage raises KeyError loudly (never
    a .get default): silently mapping a typo would corrupt scoring downstream.
    """
    return V1_STATUS_BY_STAGE[stage]


def _fold(name: str) -> str:
    """Normalise a name for diacritics-insensitive, case-insensitive comparison.

    NFKD decomposes accented characters into base + combining marks; dropping
    the combining marks strips the diacritics. casefold() makes it
    case-insensitive. So "Duyên Hải" and "Duyen Hai" fold to the same key.
    """
    decomposed = unicodedata.normalize("NFKD", name)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return stripped.strip().casefold()


def _cell(value) -> str:
    """A trimmed string cell; NaN and whitespace-only become empty."""
    return value.strip() if isinstance(value, str) else ""


def derive_name(row: pd.Series) -> str:
    """The attested designation: Plant + Unit concatenated, or the bare grain.

    The 0439 split never invents names — Plant and Unit always concatenate
    back to the designation the sources attest. A complex-grain row's
    designation is the Complex itself.
    """
    complex_, plant, unit = (_cell(row[c]) for c in ADDRESS_COLUMNS)
    if unit:
        return f"{plant} {unit}"
    return plant or complex_


def derive_level(row: pd.Series) -> str:
    """The finest non-empty address column (Level as derivation, ticket 0401)."""
    complex_, plant, unit = (_cell(row[c]) for c in ADDRESS_COLUMNS)
    if unit:
        return "unit"
    if plant:
        return "plant"
    if complex_:
        return "complex"
    return ""


def validate_address_shape(df: pd.DataFrame) -> None:
    """Every row needs an address, and a Unit needs its Plant.

    A row with a Unit but no Plant is an unfinished 0439 split (parentage
    would be an inference again); a row with no address at all carries data
    that nothing can reference. Both are master-file errors.
    """
    offenders = []
    for idx, row in df.iterrows():
        complex_, plant, unit = (_cell(row[c]) for c in ADDRESS_COLUMNS)
        if unit and not plant:
            offenders.append(f"row {idx + HEADER_ROW + 2}: Unit={unit!r} without a Plant")
        elif not (complex_ or plant):
            offenders.append(f"row {idx + HEADER_ROW + 2}: no address (all three columns empty)")
    if offenders:
        raise ValueError(
            "Address-shape violations in the master ODS — fix them in the "
            "master, then re-import:\n  " + "\n  ".join(offenders)
        )


def validate_no_duplicate_names(df: pd.DataFrame) -> None:
    """Abort if any derived designation appears more than once, modulo diacritics.

    Two designations that differ only by diacritical marks or case are the
    same asset recorded twice — a master-file data error. The message lists
    the offending *original* surface forms so the author can find and fix
    them in the master.
    """
    names = df.apply(derive_name, axis=1)
    names = names[names != ""]
    folded = names.map(_fold)
    duplicated_mask = folded.duplicated(keep=False)
    if not duplicated_mask.any():
        return
    offenders = sorted(set(names[duplicated_mask]))
    raise ValueError(
        "Duplicate designations (modulo diacritics) in the master ODS — "
        "fix them in the master, then re-import. Offending names:\n  " + "\n  ".join(offenders)
    )


def validate_status_vocabulary(df: pd.DataFrame) -> None:
    """Abort on any Project stage outside the closed 9-label vocabulary.

    The ladder is closed by convention (master Conventions sheet): an unknown
    value is a data-entry error in the master, never something to coerce or
    pass through. The message lists each offending value with its rows.
    """
    allowed = set(STATUS_VOCABULARY)
    offenders: dict[str, list[int]] = {}
    for idx, value in df["Project stage"].items():
        stage = _cell(value)
        if stage not in allowed:
            offenders.setdefault(stage or "<empty>", []).append(idx + HEADER_ROW + 2)
    if offenders:
        detail = "\n  ".join(f"{v!r} (rows {r})" for v, r in sorted(offenders.items()))
        raise ValueError(
            "Project stage values outside the closed vocabulary — fix them in "
            "the master (Conventions sheet lists the 9 valid labels), then "
            "re-import:\n  " + detail
        )


def validate_capacity_numeric(df: pd.DataFrame) -> None:
    """Abort if any Capacity cell is non-empty and non-numeric.

    A spreadsheet error value (e.g. ``Err:510``, ``#VALUE!``, ``#REF!``) is
    corruption leaked from a formula cell, not data — writing it to the CSV
    would silently break downstream numeric aggregation (the capacity sum in
    aggregate_units.py). Empty is allowed (legitimately unknown capacity for
    planned plants). The message names the offending spreadsheet row and the
    bad value so the author can fix the master.

    Ticket 0442: Err:510 leaked through extraction into the CSV; the failure
    surfaced only downstream in aggregate_units.py's capacity guard (0416).
    Per the layered-guards doctrine, extraction is the primary catch.
    """
    offenders = []
    for idx, value in df["Capacity (MW)"].items():
        cell = _cell(value)
        if not cell:
            continue
        try:
            float(cell)
        except ValueError:
            offenders.append(
                f"row {idx + HEADER_ROW + 2}: {cell!r}"
            )
    if offenders:
        raise ValueError(
            "Non-numeric capacity cells in the master ODS — a spreadsheet "
            "formula error (e.g. Err:510, #VALUE!, #REF!) leaked through. "
            "Fix the formula in the master, then re-import:\n  "
            + "\n  ".join(offenders)
        )


def validate_input(df: pd.DataFrame) -> None:
    """Run every input validator. Hard stop on the first failure.

    New invariants are added by extending this function (no rule registry —
    YAGNI). Shape first: duplicate detection relies on well-formed addresses.
    """
    validate_address_shape(df)
    validate_no_duplicate_names(df)
    validate_status_vocabulary(df)
    validate_capacity_numeric(df)


def read_ods(path: Path) -> pd.DataFrame:
    """Read the Power plants sheet as all-string data (no coercion)."""
    return pd.read_excel(
        path,
        engine="odf",
        sheet_name=SHEET_NAME,
        header=HEADER_ROW,
        dtype=str,
    )


def select_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Project to the curated output columns, deriving `name` and `level`.

    Missing mapped columns raise rather than silently emitting NaN. `name`
    leads the output for continuity with the v1 schema; the address columns
    follow so downstream consumers (0416 contrat v2) get parentage as data.
    """
    missing = [src for src in COLUMN_MAP if src not in df.columns]
    if missing:
        raise ValueError(
            f"Expected columns absent from the ODS sheet {SHEET_NAME!r}: {missing}. "
            "Has the master layout changed? Check the header row."
        )
    out = df[list(COLUMN_MAP)].rename(columns=COLUMN_MAP)
    out.insert(0, "name", df.apply(derive_name, axis=1))
    out["level"] = df.apply(derive_level, axis=1)
    return out


def extract(input_path: Path, output_path: Path) -> pd.DataFrame:
    """Read, validate, project, and write the reference CSV.

    Validation runs on the raw DataFrame before any transformation, so a bad
    input file aborts extraction before a partial CSV can be written.
    """
    logger.info("Reading %s (sheet=%r, header=%d, dtype=str)", input_path, SHEET_NAME, HEADER_ROW)
    raw = read_ods(input_path)
    logger.info("Read %d rows, %d columns", len(raw), len(raw.columns))

    validate_input(raw)

    out = select_columns(raw)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    logger.info("Wrote %d rows to %s", len(out), output_path)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/reference/raw/pipeline+extensions-as-plants-2026-06-05.ods"),
        help="Path to the master ODS snapshot (default: %(default)s). "
        "Non-authoritative fallback for standalone runs; the acquire.mk DAG "
        "overrides this with config.VN_THERMAL_MASTER_SNAPSHOT_ODS.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/reference/vietnam_thermal_units_v2.csv"),
        help="Path for the extracted CSV (default: %(default)s).",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        extract(args.input, args.output)
    except ValueError as exc:
        logger.error("Extraction refused: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
