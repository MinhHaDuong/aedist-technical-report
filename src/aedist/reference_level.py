"""Derive and audit granularity levels for the v2 reference dataset.

The v2 unit-grain CSV (vietnam_thermal_units_v2.csv) carries three address
columns: complex, plant, unit.  The Level for each row is the finest non-empty
address column:

    unit set     → Level.UNIT
    plant set    → Level.PLANT    (unit empty)
    complex set  → Level.COMPLEX  (plant and unit empty)
    all empty    → Level.UNKNOWN

This derivation exactly reconstructs the pre-assigned `level` column
already present in the v2 CSV (verified: 100 % match across 258 rows).
The function is a cross-check and a forward-compatible path for new rows.

Taxonomy audit (tickets 0401 / 0402 gate):

Checks three capacity caps against the derived levels on the v2 reference:
  (a) every operating/constructing Plant row has capacity ≤ 1600 MW
  (b) every Unit row has capacity ≤ 1350 MW
  (c) Complex rows carry the highest capacities (> 3200 MW tail)

Audit passes when caps (a) and (b) hold; (c) is informational only.
If either cap is violated the audit returns a non-finding with diagnostics
and does not raise — the caller decides whether to treat as hard error.

Ticket 0401.
"""

import csv
import logging
from dataclasses import dataclass, field
from pathlib import Path

from .config import VN_THERMAL_UNITS_RELEASE_CSV
from .schema import Level

logger = logging.getLogger(__name__)

# Statuses in v2 unit CSV that map to "operational or constructing"
# (numeric-prefix vocab from extract_ods.py: "5 construction", "6 operating")
_OPERATIONAL_STATUSES = frozenset({"5 construction", "6 operating"})

# Capacity caps (MW) — domain knowledge, ticket 0401
_UNIT_CAP_MW = 1350.0       # world-record single shaft; VN alert above 700
_PLANT_OP_CAP_MW = 1600.0   # operating/constructing plant ceiling
_COMPLEX_FLOOR_MW = 3200.0  # complex threshold (informational)


def derive_level_from_address(
    complex_col: str,
    plant_col: str,
    unit_col: str,
) -> Level:
    """Return the Level for one row given its three address columns.

    Rule: finest non-empty address column wins.
    ``Block`` is not derivable from address columns alone (requires CCGT
    multi-shaft knowledge not currently in the reference); it remains
    available for model-emitted values (ticket 0402).
    """
    if unit_col.strip():
        return Level.UNIT
    if plant_col.strip():
        return Level.PLANT
    if complex_col.strip():
        return Level.COMPLEX
    return Level.UNKNOWN


def derive_reference_level(
    units_csv: Path | str | None = None,
) -> list[dict]:
    """Read the v2 unit CSV and return one dict per row with a derived level.

    Each dict contains: ``name``, ``derived_level``, ``recorded_level``,
    ``capacity_mwe`` (float or None), ``status``.

    ``derived_level`` is the Level derived from address columns;
    ``recorded_level`` is the string already in the CSV's ``level`` column
    (cross-check only — the caller should treat ``derived_level`` as
    authoritative for new work).

    Args:
        units_csv: Path to the unit-grain CSV.  Defaults to
            ``VN_THERMAL_UNITS_RELEASE_CSV``.
    """
    path = Path(units_csv) if units_csv is not None else VN_THERMAL_UNITS_RELEASE_CSV
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            cap_str = row.get("capacity_mwe", "").strip()
            try:
                cap = float(cap_str) if cap_str else None
            except ValueError:
                cap = None
                logger.warning("Non-numeric capacity %r for %r", cap_str, row.get("name"))

            derived = derive_level_from_address(
                row.get("complex", ""),
                row.get("plant", ""),
                row.get("unit", ""),
            )
            rows.append(
                {
                    "name": row.get("name", ""),
                    "derived_level": derived,
                    "recorded_level": row.get("level", ""),
                    "capacity_mwe": cap,
                    "status": row.get("status", ""),
                }
            )
    return rows


# ---------------------------------------------------------------------------
# Taxonomy audit
# ---------------------------------------------------------------------------


@dataclass
class AuditResult:
    """Result of the reference taxonomy audit.

    ``passed`` is True when all hard caps hold.
    ``unknown_count`` is the number of rows that could not be classified.
    ``violations`` lists (name, level, capacity_mwe, rule) for each cap breach.
    ``informational`` carries non-failing observations (e.g. complex-floor info).
    """

    passed: bool
    total: int
    level_counts: dict[str, int]
    unknown_count: int
    violations: list[tuple[str, str, float, str]] = field(default_factory=list)
    informational: list[str] = field(default_factory=list)


def audit_reference_taxonomy(
    units_csv: Path | str | None = None,
) -> AuditResult:
    """Run the taxonomy audit on the v2 reference.

    Checks:
      (a) operating/constructing Plant rows: capacity ≤ 1600 MW
      (b) Unit rows: capacity ≤ 1350 MW
      (c) informational: Complex rows carry capacities ≥ expected floor

    Returns an AuditResult.  Does not raise on cap violations; the caller
    controls failure behaviour (hard error vs. logged warning).
    """
    rows = derive_reference_level(units_csv)
    total = len(rows)

    level_counts: dict[str, int] = {}
    unknown_count = 0
    violations: list[tuple[str, str, float, str]] = []

    for r in rows:
        lv = r["derived_level"]
        lv_str = lv.value
        level_counts[lv_str] = level_counts.get(lv_str, 0) + 1
        if lv == Level.UNKNOWN:
            unknown_count += 1
            continue

        cap = r["capacity_mwe"]
        if cap is None:
            continue
        status = r["status"]

        # (a) operating/constructing Plants must stay under the ceiling
        if lv == Level.PLANT and status in _OPERATIONAL_STATUSES and cap > _PLANT_OP_CAP_MW:
            violations.append(
                (
                    r["name"],
                    lv_str,
                    cap,
                    f"Plant op/constr cap > {_PLANT_OP_CAP_MW} MW",
                )
            )

        # (b) Units must stay under world-record single-shaft ceiling
        if lv == Level.UNIT and cap > _UNIT_CAP_MW:
            violations.append(
                (r["name"], lv_str, cap, f"Unit cap > {_UNIT_CAP_MW} MW")
            )

    # (c) informational: max complex capacity
    complex_caps = [
        r["capacity_mwe"]
        for r in rows
        if r["derived_level"] == Level.COMPLEX and r["capacity_mwe"] is not None
    ]
    informational = []
    if complex_caps:
        max_complex = max(complex_caps)
        informational.append(
            f"Max Complex capacity: {max_complex:.0f} MW "
            f"(floor {_COMPLEX_FLOOR_MW:.0f} MW; "
            f"{'above' if max_complex >= _COMPLEX_FLOOR_MW else 'BELOW — check'} floor)"
        )

    passed = len(violations) == 0
    return AuditResult(
        passed=passed,
        total=total,
        level_counts=level_counts,
        unknown_count=unknown_count,
        violations=violations,
        informational=informational,
    )
