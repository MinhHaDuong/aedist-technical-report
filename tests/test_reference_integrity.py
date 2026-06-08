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


# Plants explicitly required by ticket 0395 exit criteria.
# Keys: normalised fragment that must appear in at least one reference row's
# ``name`` field (case-insensitive substring match).
_REQUIRED_PLANTS = [
    "Kiên Lương 1",
    "Kiên Lương 2",
    "Kiên Lương 3",
    "Kim Sơn",
    "Yên Hưng",
    "Rạng Đông",
]


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
