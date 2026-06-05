"""Extract the Vietnam thermal-units reference list from the master ODS.

Reads the "Power plants" sheet of the imported `pipeline.ods` snapshot and
writes a curated CSV. This is the single, reproducible extraction step of the
reference pipeline (ticket 0420); it replaces the lost manual-export chain
(`pipeline.ods` -> hand export -> HDM.csv -> ...) that let the `ires_code`
zero-prefix coercion (0121 -> 121) slip through.

Two invariants are non-negotiable:

1. **dtype=str throughout.** Every value is read as a string and stays a
   string. No numeric coercion, ever — leading zeros survive by construction.
2. **Hard validation, no tolerance.** A duplicate name (modulo diacritics) or
   a Level/name inconsistency aborts extraction with an actionable message.
   No CSV is written. Corrections belong in the master, not here.

The `Level` column does not yet exist in the tracked ODS; it is forthcoming in
the master. It passes through untouched when present and is a graceful no-op
when absent.

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
# actual column names. 250 data rows.
SHEET_NAME = "Power plants"
HEADER_ROW = 4

# Source -> output column mapping. `Level` is added conditionally (passthrough).
COLUMN_MAP = {
    "Project name": "name",
    "Province / Tỉnh": "province",
    "Asset type": "asset_type",
    "Capacity (MW)": "capacity_mwe",
    "Project stage": "status",
}

# Level values that denote a unit-level (as opposed to plant-level) record.
UNIT_LEVEL_VALUES = {"unit", "unité", "unite"}


def _fold(name: str) -> str:
    """Normalise a name for diacritics-insensitive, case-insensitive comparison.

    NFKD decomposes accented characters into base + combining marks; dropping
    the combining marks strips the diacritics. casefold() makes it
    case-insensitive. So "Duyên Hải" and "Duyen Hai" fold to the same key.
    """
    decomposed = unicodedata.normalize("NFKD", name)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return stripped.strip().casefold()


def validate_no_duplicate_names(df: pd.DataFrame) -> None:
    """Abort if any Project name appears more than once, modulo diacritics.

    Two names that differ only by diacritical marks or case are the same unit
    recorded twice — a master-file data error. The message lists the offending
    *original* surface forms so the author can find and fix them in the master.
    """
    names = df["Project name"].dropna().astype(str)
    folded = names.map(_fold)
    duplicated_mask = folded.duplicated(keep=False)
    if not duplicated_mask.any():
        return
    offenders = sorted(set(names[duplicated_mask]))
    raise ValueError(
        "Duplicate project names (modulo diacritics) in the master ODS — "
        "fix them in the master, then re-import. Offending names:\n  " + "\n  ".join(offenders)
    )


def validate_unit_level_consistency(df: pd.DataFrame) -> None:
    """If a Level column is present, a 'Unit' name must have a unit-level Level.

    No-op when the Level column is absent (it is forthcoming in the master).
    The message lists every name that contains "Unit" but is not marked as a
    unit-level record.
    """
    if "Level" not in df.columns:
        return
    offenders = []
    for name, level in zip(df["Project name"], df["Level"], strict=False):
        if not isinstance(name, str) or "unit" not in name.casefold():
            continue
        level_norm = level.strip().casefold() if isinstance(level, str) else ""
        if level_norm not in UNIT_LEVEL_VALUES:
            offenders.append(f"{name!r} (Level={level!r})")
    if offenders:
        raise ValueError(
            "Names containing 'Unit' must have a unit-level Level — fix in the "
            "master, then re-import. Inconsistent entries:\n  " + "\n  ".join(offenders)
        )


def validate_input(df: pd.DataFrame) -> None:
    """Run every input validator. Hard stop on the first failure.

    New invariants are added by extending this function (no rule registry —
    YAGNI). The two named validators below are the current invariant set.
    """
    validate_no_duplicate_names(df)
    validate_unit_level_consistency(df)


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
    """Project to the curated output columns, renaming to snake_case.

    `Level` passes through (renamed to `level`) when present; omitted when
    absent. Missing mapped columns raise rather than silently emitting NaN.
    """
    missing = [src for src in COLUMN_MAP if src not in df.columns]
    if missing:
        raise ValueError(
            f"Expected columns absent from the ODS sheet {SHEET_NAME!r}: {missing}. "
            "Has the master layout changed? Check the header row."
        )
    column_map = dict(COLUMN_MAP)
    if "Level" in df.columns:
        column_map["Level"] = "level"
    return df[list(column_map)].rename(columns=column_map)


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
        default=Path("data/reference/raw/pipeline-2026-05-26.ods"),
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
