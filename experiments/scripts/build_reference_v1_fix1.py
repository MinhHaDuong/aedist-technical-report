"""Build the ``_v1_fix1`` reference files from the frozen v1 (ticket 0394).

A *minimal integrity patch* over the plant-level and unit-level references.
Pure CSV text transform — every field is read and written verbatim, so codes
like ``ires_code`` ``0121`` keep their significant leading zero (hand-editing
v1 in a spreadsheet silently coerced ``0121`` -> ``121``; this script is the
fix).

Integrity edits (human-adjudicated 2026-06-03/04, ticket 0394):

Plant level (``vietnam_thermal_v1.csv`` -> ``vietnam_thermal_v1_fix1.csv``):
  - DELETE the subset-duplicate ``Duyen Hai 2`` 600 MW (Unit 1) row; the
    ``Duyên Hải 2`` 1200 MW (Units 1+2) row subsumes it (overlapping units).
  - RENAME the *proposed* extension row of two identical-name base/extension
    pairs, adopting the reference's own ``extension`` convention (cf.
    ``Duyen Hai 3 Extension``, ``Vinh Tan 4 extension``):
      ``Dong Nai Formosa`` (proposed, Unit 3)               -> ``Dong Nai Formosa extension``
      ``Ha Tinh Formosa Plastics Steel Complex`` (proposed) -> ``... extension``
  - FIX the ``Quảng Trị 1`` units_included typo: the same unit was listed
    twice ("Unit 2, Unit 2"); 1320 MW = 2 x 660 and sibling plants all have
    "Unit 1, Unit 2".

Unit level (``vietnam_thermal_units_v1.csv`` -> ``vietnam_thermal_units_v1_fix1.csv``):
  - DELETE the romanization duplicate ``Duyen Hai 2 Unit 1`` (ASCII); the
    diacritic ``Duyên Hải 2 Unit 1`` row is the same physical unit.
  - RENAME the first of the two identical ``Quảng Trị 1 Unit 2`` rows to
    ``Quảng Trị 1 Unit 1`` (same data-entry typo as above).

Scope: integrity only. The Exp2 FP/FN recounts showed reference hygiene
removes 0 FP and only the duplicate row's ~80 phantom FN; the cleaner-gate
(Famille B) and the name_ascii alias are deliberately NOT done (documented
non-finding, see ticket 0394). DNF/HTF need no unit-level change (distinct
unit numbers -> no collision).
"""

import argparse
import csv
from pathlib import Path

PLANT_DELETE = [{"name": "Duyen Hai 2", "capacity_mwe": "600.0"}]
PLANT_RENAME = [
    {
        "match": {"name": "Dong Nai Formosa", "status": "proposed"},
        "new_name": "Dong Nai Formosa extension",
    },
    {
        "match": {"name": "Ha Tinh Formosa Plastics Steel Complex", "status": "proposed"},
        "new_name": "Ha Tinh Formosa Plastics Steel Complex extension",
    },
]
PLANT_FIELD_FIX = [
    {
        "match": {"name": "Quảng Trị 1"},
        "set": {"units_included": "Quảng Trị 1 Unit 1, Quảng Trị 1 Unit 2"},
    },
]

UNIT_DELETE = [{"Name": "Duyen Hai 2 Unit 1"}]
# First occurrence of the duplicated row gets the corrected name.
UNIT_RENAME_FIRST = [
    {
        "match": {"Name": "Quảng Trị 1 Unit 2"},
        "new_name": "Quảng Trị 1 Unit 1",
        "expect_matches": 2,
    },
]


def _matches(row: dict, crit: dict) -> bool:
    return all(row.get(k) == v for k, v in crit.items())


def _read(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames is not None, f"{path} has no header"
        return list(reader.fieldnames), list(reader)


def _write(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def build_plants(src: Path, dst: Path) -> str:
    fieldnames, rows = _read(src)

    kept = [r for r in rows if not any(_matches(r, d) for d in PLANT_DELETE)]
    deleted = len(rows) - len(kept)
    assert deleted == len(PLANT_DELETE), f"expected {len(PLANT_DELETE)} deletion(s), got {deleted}"

    renamed = 0
    for r in kept:
        for spec in PLANT_RENAME:
            if _matches(r, spec["match"]):
                r["name"] = spec["new_name"]
                renamed += 1
    assert renamed == len(PLANT_RENAME), f"expected {len(PLANT_RENAME)} rename(s), got {renamed}"

    fixed = 0
    for r in kept:
        for spec in PLANT_FIELD_FIX:
            if _matches(r, spec["match"]):
                r.update(spec["set"])
                fixed += 1
    assert fixed == len(PLANT_FIELD_FIX), (
        f"expected {len(PLANT_FIELD_FIX)} field fix(es), got {fixed}"
    )

    _write(dst, fieldnames, kept)
    return f"{dst}: {len(kept)} rows (deleted {deleted}, renamed {renamed}, fixed {fixed})"


def build_units(src: Path, dst: Path) -> str:
    fieldnames, rows = _read(src)

    kept = [r for r in rows if not any(_matches(r, d) for d in UNIT_DELETE)]
    deleted = len(rows) - len(kept)
    assert deleted == len(UNIT_DELETE), f"expected {len(UNIT_DELETE)} deletion(s), got {deleted}"

    for spec in UNIT_RENAME_FIRST:
        hits = [r for r in kept if _matches(r, spec["match"])]
        assert len(hits) == spec["expect_matches"], (
            f"expected {spec['expect_matches']} rows matching {spec['match']}, got {len(hits)}"
        )
        hits[0]["Name"] = spec["new_name"]

    _write(dst, fieldnames, kept)
    return f"{dst}: {len(kept)} rows (deleted {deleted}, renamed first-of-dup {len(UNIT_RENAME_FIRST)})"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--input-plants", type=Path, default=Path("data/reference/vietnam_thermal_v1.csv")
    )
    ap.add_argument(
        "--input-units", type=Path, default=Path("data/reference/vietnam_thermal_units_v1.csv")
    )
    ap.add_argument(
        "--output-plants", type=Path, default=Path("data/reference/vietnam_thermal_v1_fix1.csv")
    )
    ap.add_argument(
        "--output-units",
        type=Path,
        default=Path("data/reference/vietnam_thermal_units_v1_fix1.csv"),
    )
    args = ap.parse_args()

    print(build_plants(args.input_plants, args.output_plants))
    print(build_units(args.input_units, args.output_units))


if __name__ == "__main__":
    main()
