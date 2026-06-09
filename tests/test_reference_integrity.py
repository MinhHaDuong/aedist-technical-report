"""Reference integrity checks for ticket-0395 additions.

Asserts:
1. Each high-confidence plant named in ticket 0395 resolves to exactly one
   reference row (presence check).
2. No added plant has capacity_mwe < 30 MWe (scope guard).
3. The reference has no plant rows with capacity_mwe < 30 MWe at all
   (blanket 30-MWe floor, not just the 0395 additions).
"""

import csv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_CSV = ROOT / "data" / "reference" / "vietnam_thermal_plants_v2_classified.csv"


def _load_reference() -> list[dict]:
    with REFERENCE_CSV.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


# Plants explicitly required by ticket 0395 exit criteria, as amended by the
# ticket 0497 boundary correction: Kim Sơn and Rạng Đông were E542 PL9.2
# *potential sites* (candidate locations, not projects) and were removed
# (see _REMOVED_POTENTIAL_SITES below). Yên Hưng (PDP7 planned project) and the
# Kiên Lương trio remain required.
# Keys: normalised fragment that must appear in at least one reference row's
# ``name`` field (case-insensitive substring match).
_REQUIRED_PLANTS = [
    "Kiên Lương 1",
    "Kiên Lương 2",
    "Kiên Lương 3",
    "Yên Hưng",
]

# E542 PL9.2 potential sites removed by ticket 0497 — must NOT appear as a
# counted reference row (recorded as aliases in PROVENANCE.md instead).
_REMOVED_POTENTIAL_SITES = ["Kim Sơn", "Rạng Đông", "Phú Thọ"]


@pytest.mark.parametrize("plant_name", _REQUIRED_PLANTS)
def test_required_plant_present(plant_name: str) -> None:
    """Each high-confidence plant from ticket 0395 is in the reference."""
    rows = _load_reference()
    matches = [r for r in rows if plant_name.lower() in r["name"].lower()]
    assert len(matches) == 1, (
        f"Expected exactly 1 reference row for '{plant_name}', "
        f"found {len(matches)}: {[r['name'] for r in matches]}"
    )


@pytest.mark.parametrize("plant_name", _REQUIRED_PLANTS)
def test_required_plant_capacity_at_least_30_mwe(plant_name: str) -> None:
    """No ticket-0395 addition is below the 30-MWe scope threshold."""
    rows = _load_reference()
    matches = [r for r in rows if plant_name.lower() in r["name"].lower()]
    assert matches, f"Plant '{plant_name}' not found in reference (run test_required_plant_present first)"
    for row in matches:
        cap_str = row["capacity_mwe"]
        if cap_str:
            cap = float(cap_str)
            assert cap >= 30, (
                f"Plant '{row['name']}' has capacity {cap} MWe < 30 MWe scope threshold"
            )


@pytest.mark.parametrize("plant_name", _REMOVED_POTENTIAL_SITES)
def test_removed_potential_site_absent(plant_name: str) -> None:
    """The E542 PL9.2 potential sites (ticket 0497) are not counted reference rows.

    Exact-name match: "Rạng Đông" (diacritics) is the removed potential site;
    the unrelated "Rang Dong cogeneration" (100 MW captive cogen, ASCII) stays.
    """
    rows = _load_reference()
    exact = [r for r in rows if r["name"].strip() == plant_name]
    assert not exact, (
        f"Removed potential site '{plant_name}' is still a counted reference row: "
        f"{[r['name'] for r in exact]}"
    )


def test_no_reference_row_below_30_mwe() -> None:
    """No reference plant row has a non-zero capacity below 30 MWe."""
    rows = _load_reference()
    violations = [
        r for r in rows
        if r["capacity_mwe"] and float(r["capacity_mwe"]) > 0 and float(r["capacity_mwe"]) < 30
    ]
    assert not violations, (
        f"Found {len(violations)} reference plants below 30 MWe: "
        + ", ".join(f"{r['name']} ({r['capacity_mwe']} MW)" for r in violations)
    )
