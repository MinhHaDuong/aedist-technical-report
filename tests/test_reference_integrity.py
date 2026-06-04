"""Reference integrity (ticket 0394): structural invariants of the _v1_fix1
reference files.

Names are source-attested and never invented (author's rule), so name
uniqueness is NOT the plant-level invariant. Same-name plant rows are
legitimate — distinct unit groups of one named complex (e.g. Dong Nai
Formosa: operational base vs proposed expansion) — provided they are
*structurally* distinct: pairwise different ``status`` and pairwise disjoint
``units_included``. That catches the real defects ('Duyen Hai 2' ==
'Duyên Hải 2': the same physical unit under two romanizations -> overlapping
units, same status; the duplicated 'Quảng Trị 1 Unit 2' typo row) while
passing the legitimate same-name pairs untouched.

Unit-level names must be fold-unique: one row per physical unit.

The 14 clean_name collisions among *distinct* plants (gas/LNG successors
merged by the cleaner's drops) are deliberately not tested: the Exp2 FP/FN
recounts showed they cause neither FP nor FN (documented non-finding,
ticket 0394).
"""

import csv
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

DATA = Path(__file__).parent.parent / "data" / "reference"
PLANTS = DATA / "vietnam_thermal_v1_fix1.csv"
UNITS = DATA / "vietnam_thermal_units_v1_fix1.csv"


def fold(name: str) -> str:
    s = name.lower().strip().replace("đ", "d")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _rows(path: Path) -> list[dict]:
    return list(csv.DictReader(path.open(encoding="utf-8")))


def _unit_set(row: dict) -> set[str]:
    return {fold(u.strip()) for u in row["units_included"].split(",") if u.strip()}


def test_units_no_fold_duplicates():
    counts = Counter(fold(r["Name"]) for r in _rows(UNITS))
    assert {k: v for k, v in counts.items() if v > 1} == {}


def test_plants_same_name_rows_structurally_distinct():
    groups = defaultdict(list)
    for r in _rows(PLANTS):
        groups[fold(r["name"])].append(r)
    violations = {}
    for key, members in groups.items():
        if len(members) < 2:
            continue
        statuses = [m["status"] for m in members]
        unit_sets = [_unit_set(m) for m in members]
        repeated_status = len(set(statuses)) != len(statuses)
        overlapping_units = any(
            unit_sets[i] & unit_sets[j]
            for i in range(len(members))
            for j in range(i + 1, len(members))
        )
        if repeated_status or overlapping_units:
            violations[key] = {"statuses": statuses, "overlapping_units": overlapping_units}
    assert violations == {}


def test_plants_ires_code_keeps_leading_zero():
    # A spreadsheet round-trip once coerced 0121 -> 121; guard the 4-digit form.
    rows = _rows(PLANTS)
    bad = [r["name"] for r in rows if not (len(r["ires_code"]) == 4 and r["ires_code"].isdigit())]
    assert bad == []


def test_plants_units_included_no_repeated_unit():
    # Quảng Trị 1 listed the same unit twice ("Unit 2, Unit 2") in v1.
    bad = {}
    for r in _rows(PLANTS):
        units = [u.strip() for u in r["units_included"].split(",") if u.strip()]
        dups = {u: c for u, c in Counter(units).items() if c > 1}
        if dups:
            bad[r["name"]] = dups
    assert bad == {}
