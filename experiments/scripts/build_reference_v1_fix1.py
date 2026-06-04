"""Build the ``_v1_fix1`` reference files from the frozen v1 (ticket 0394).

A *minimal integrity patch* over the plant-level and unit-level references.
Pure CSV text transform — every field is read and written verbatim, so codes
like ``ires_code`` ``0121`` keep their significant leading zero (hand-editing
v1 in a spreadsheet silently coerced ``0121`` -> ``121``; this script is the
fix).

Names are never invented: every ``name`` in the output is attested by the
primary sources (author's rule). ``Dong Nai Formosa`` and ``Ha Tinh Formosa
Plastics Steel Complex`` therefore each keep two same-name rows — distinct
unit groups of one named complex (operational base vs proposed expansion).
The integrity invariant is structural, not nominal: same-name rows must have
different ``status`` and disjoint ``units_included``
(see ``tests/test_reference_integrity.py``).

Integrity edits (author-adjudicated 2026-06-03/04, ticket 0394):

Plant level (``vietnam_thermal_v1.csv`` -> ``vietnam_thermal_v1_fix1.csv``):
  - DELETE the subset-duplicate ``Duyen Hai 2`` 600 MW (Unit 1) row; the
    ``Duyên Hải 2`` 1200 MW (Units 1+2) row subsumes it (overlapping units).
  - FIX the ``Quảng Trị 1`` units_included transcription error: the same unit
    was listed twice ("Unit 2, Unit 2"); upstream master has Units 1+2
    (1320 MW = 2 x 660, sibling plants all have Units 1+2).

Unit level (``vietnam_thermal_units_v1.csv`` -> ``vietnam_thermal_units_v1_fix1.csv``):
  - DELETE the romanization duplicate ``Duyen Hai 2 Unit 1`` (ASCII); the
    diacritic ``Duyên Hải 2 Unit 1`` row is the same physical unit.
  - RENAME the first of the two identical ``Quảng Trị 1 Unit 2`` rows to
    ``Quảng Trị 1 Unit 1`` (same transcription error as above; Unit 1 is the
    attested upstream designation, not an invention).

Scope: integrity only. The Exp2 FP/FN recounts showed reference hygiene
removes 0 FP and only the duplicate row's phantom FN; the cleaner-gate
(Famille B) and the name_ascii alias are deliberately NOT done (documented
non-finding, see ticket 0394). The defects originate in the unit->plant
aggregator (ticket 0416).
"""

import argparse
import csv
from pathlib import Path

PLANT_DELETE = [{"name": "Duyen Hai 2", "capacity_mwe": "600.0"}]
PLANT_FIELD_FIX = [
    {
        "match": {"name": "Quảng Trị 1"},
        "set": {"units_included": "Quảng Trị 1 Unit 1, Quảng Trị 1 Unit 2"},
    },
]

UNIT_DELETE = [{"Name": "Duyen Hai 2 Unit 1"}]
# First occurrence of the duplicated row gets the attested upstream name.
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
    return f"{dst}: {len(kept)} rows (deleted {deleted}, fixed {fixed})"


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
    return (
        f"{dst}: {len(kept)} rows (deleted {deleted}, fixed first-of-dup {len(UNIT_RENAME_FIRST)})"
    )


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
