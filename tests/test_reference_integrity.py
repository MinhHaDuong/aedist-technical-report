"""Reference integrity (ticket 0394): the _v1_fix1 reference files contain no
duplicate rows under diacritic folding, and ires_code keeps its 4-digit form.

Fold-uniqueness (lowercase + strip diacritics, NOT the matcher's clean_name)
catches every defect fixed by fix1: 'Duyen Hai 2' == 'Duyên Hải 2' (plant and
unit level), the two identical-name base/extension pairs (Dong Nai Formosa,
Ha Tinh Formosa), and the duplicated 'Quảng Trị 1 Unit 2' typo row. It is
deliberately blind to the 14 clean_name collisions among *distinct* plants
(gas/LNG successors merged by the cleaner's drops): the Exp2 FP/FN recounts
showed those cause neither FP nor FN, so the cleaner stays untouched
(documented non-finding, ticket 0394).
"""

import csv
import unicodedata
from collections import Counter
from pathlib import Path

DATA = Path(__file__).parent.parent / "data" / "reference"
PLANTS = DATA / "vietnam_thermal_v1_fix1.csv"
UNITS = DATA / "vietnam_thermal_units_v1_fix1.csv"


def fold(name: str) -> str:
    s = name.lower().strip().replace("đ", "d")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _fold_duplicates(path: Path, column: str) -> dict[str, int]:
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    counts = Counter(fold(r[column]) for r in rows)
    return {k: v for k, v in counts.items() if v > 1}


def test_plants_no_fold_duplicates():
    assert _fold_duplicates(PLANTS, "name") == {}


def test_units_no_fold_duplicates():
    assert _fold_duplicates(UNITS, "Name") == {}


def test_plants_ires_code_keeps_leading_zero():
    # A spreadsheet round-trip once coerced 0121 -> 121; guard the 4-digit form.
    rows = list(csv.DictReader(PLANTS.open(encoding="utf-8")))
    bad = [r["name"] for r in rows if not (len(r["ires_code"]) == 4 and r["ires_code"].isdigit())]
    assert bad == []


def test_plants_units_included_no_repeated_unit():
    # Quảng Trị 1 listed the same unit twice ("Unit 2, Unit 2") in v1.
    rows = list(csv.DictReader(PLANTS.open(encoding="utf-8")))
    bad = {}
    for r in rows:
        units = [u.strip() for u in r["units_included"].split(",") if u.strip()]
        dups = {u: c for u, c in Counter(units).items() if c > 1}
        if dups:
            bad[r["name"]] = dups
    assert bad == {}
