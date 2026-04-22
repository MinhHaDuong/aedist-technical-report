"""Tests for scripts/verify/coherence_table.py (ticket 0103).

All tests use synthetic fixtures — no LLM calls, no real data files.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the scripts/ tree importable without installing it as a package.
_SCRIPTS_ROOT = Path(__file__).parent.parent / "scripts"
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

from verify.coherence_table import (
    check_sidecar_null_parity,
    check_sidecar_row_coverage,
)

from aedist.coherence import check_coherence
from aedist.prototype_v1_fusion import MasterRecord, master_to_plants
from aedist.schema import FuelType, Plant, PlantStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _spec_stub(source_id="SRC", tier=2, year=2020):
    """Return a minimal FragmentSpec-like namespace (avoids importing FragmentSpec)."""
    from types import SimpleNamespace

    return SimpleNamespace(source_id=source_id, tier=tier, year=year)


def _prov_entry(name: str, **fields) -> dict:
    """Build a provenance dict entry in the shape save_provenance() produces."""
    return {"name": name, "fields": fields}


def _field_entry(value, source="SRC", tier=2, year=2020) -> dict:
    return {"value": value, "source": source, "tier": tier, "year": year}


# ---------------------------------------------------------------------------
# Test 1: adapter strips SourcedField wrappers
# ---------------------------------------------------------------------------


def test_adapter_strips_sourced_fields():
    """MasterRecord with SourcedField.value=100 → Plant.capacity_mwe=100."""
    spec = _spec_stub("PDP8-2023", tier=3, year=2023)
    rec = MasterRecord(name="Vinh Tan 1")
    rec.update_field("capacity_mwe", 1200.0, spec)
    rec.update_field("fuel", "coal", spec)
    rec.update_field("status", "operational", spec)

    plants = master_to_plants([rec])

    assert len(plants) == 1
    p = plants[0]
    assert p.name == "Vinh Tan 1"
    assert p.capacity_mwe == 1200.0
    assert p.fuel == FuelType.COAL
    assert p.status == PlantStatus.OPERATIONAL


# ---------------------------------------------------------------------------
# Test 2: sidecar row coverage mismatch is flagged
# ---------------------------------------------------------------------------


def test_sidecar_row_coverage_mismatch():
    """Provenance array has 12 entries but master has 10 rows → flagged."""
    plants = [Plant(name=f"Plant {i}", fuel=FuelType.COAL) for i in range(10)]
    provenance = [_prov_entry(f"Plant {i}") for i in range(12)]

    failures = check_sidecar_row_coverage(plants, provenance)

    assert failures, "expected at least one failure message"
    assert any("10" in f and "12" in f for f in failures), (
        "failure message should mention both counts"
    )


# ---------------------------------------------------------------------------
# Test 3: sidecar null parity violation is flagged
# ---------------------------------------------------------------------------


def test_sidecar_null_parity_violation():
    """Master row has capacity=None but provenance has source for it → fails."""
    plants = [Plant(name="Mong Duong 1", fuel=FuelType.COAL, capacity_mwe=None)]
    # Provenance claims a capacity entry even though master has None
    provenance = [
        _prov_entry(
            "Mong Duong 1",
            fuel=_field_entry("coal"),
            capacity_mwe=_field_entry(1080.0),  # spurious — plant has None
        )
    ]

    failures = check_sidecar_null_parity(plants, provenance)

    assert failures, "expected parity failure for null capacity with provenance entry"
    assert any("capacity_mwe" in f for f in failures)


# ---------------------------------------------------------------------------
# Test 4: existing coherence checks are delegated
# ---------------------------------------------------------------------------


def test_existing_checks_delegated():
    """master_to_plants + check_coherence catches unknown_fuel on master data."""
    spec = _spec_stub("SRC")
    rec = MasterRecord(name="Mystery Plant")
    rec.update_field("capacity_mwe", 500.0, spec)
    # fuel deliberately left unset → master_to_plants produces FuelType.UNKNOWN

    plants = master_to_plants([rec])
    assert plants[0].fuel == FuelType.UNKNOWN

    issues = check_coherence(plants)
    checks_fired = {i.check for i in issues}
    assert "unknown_fuel" in checks_fired, f"expected 'unknown_fuel' issue; got: {checks_fired}"
