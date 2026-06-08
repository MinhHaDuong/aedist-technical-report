"""Level-conditioned capacity coherence predicates (ticket 0402).

Two per-row predicates that check internal self-consistency of a model-emitted
power-plant row given the level it declared:

``capacity_plausible_for_level``
    Is the capacity within the plausible range for the declared level?
    Uses declared Level as authoritative — capacity does NOT cleanly
    partition Plant from Complex (see reference_level.py docstring and
    audit_reference_taxonomy informational findings).

``level_consistent_with_name``
    Does the declared level match the structural evidence in the name?
    Three name-pattern rules (each a necessary but not sufficient condition):

    R1 — Merge-marker names (0396 regex) cannot be Level.UNIT.
         "Nhơn Trạch 3 & 4" with level=Unit is incoherent.
    R2 — Bare-site names (no trailing number, no merge marker) cannot be
         Level.UNIT or Level.PLANT.  "Cà Mau" with level=Plant is incoherent.
    R3 — Site+number names imply Level.PLANT (not Unit).
         "Vinh Tan 2" with level=Unit is incoherent.
         (Unit names carry an explicit unit token: "Vinh Tan 2 Unit 1".)

    A row passes when NONE of the violation rules fire.

Capacity caps by Level (declared level is authoritative):
    Unit    — ≤ 1350 MW  (world-record single shaft; VN: 300–660 MW)
    Block   — > 1300 MW (multi-shaft CCGT assembly; no hard upper cap)
    Plant   — ≤ 3200 MW  (covers operating ≤ 1600 MW and planned LNG ≤ 3200 MW)
    Complex — no upper cap (power-centre, can exceed 6000 MW)
    Unknown — skip (not scoreable)

Lower bound (≥ 30 MWe) is a task-scope check handled by the external composite
(0397) — not re-checked here.

Ticket 0402.
"""

import re

from .schema import Level
from .score_mechanical import _ATOMICITY_VIOLATION_RE, _CAPACITY_KEYS, _as_float

# ---------------------------------------------------------------------------
# Capacity caps per Level — domain knowledge (ticket 0401 / 0402)
# ---------------------------------------------------------------------------

# Upper capacity caps (MW).  Complex and Block have no hard upper cap.
_UNIT_CAP_MW = 1350.0    # world-record single shaft
_PLANT_CAP_MW = 3200.0   # covers both operating (≤ 1600) and planned LNG (≤ 3200)
_BLOCK_MIN_MW = 1300.0   # CCGT block lower end; no upper cap

# ---------------------------------------------------------------------------
# Name-pattern helpers (ticket 0402, R2 / R3)
# ---------------------------------------------------------------------------

# R3: "Site + number" pattern — a number immediately follows the site name.
# Matches names like "Vinh Tan 2", "Cẩm Phả 1", "Phả Lại 3", "LNG Hải Phòng 1".
# Excludes explicit unit tokens ("Unit 1", "Tổ máy 1") — those are R1 territory.
_SITE_NUMBER_RE = re.compile(
    r"\b\d+\s*$"                  # trailing digit(s) at end
    r"|"
    r"\b\d+\s+(?:unit|tổ máy|tm)\b",  # digit followed by explicit unit token
    re.IGNORECASE,
)

# Unit-token pattern — explicit unit identifier in the name.
# When present, the name describes a Unit, not a Plant.
_UNIT_TOKEN_RE = re.compile(
    r"\b(?:unit|tổ máy|tm)\s*\d+",
    re.IGNORECASE,
)

# R2: bare-site name — no trailing number, no merge marker, no unit token.
# We check this by exclusion: a name is a bare-site if none of the
# above patterns match.
def _is_bare_site(name: str) -> bool:
    """Return True if the name looks like a bare site (Complex-grain)."""
    stripped = name.strip()
    if not stripped:
        return False
    if _ATOMICITY_VIOLATION_RE.search(stripped):
        return False   # merge-marker names are handled by R1, not R2
    if _UNIT_TOKEN_RE.search(stripped):
        return False   # explicit unit token → Unit grain
    if re.search(r"\d", stripped):
        return False   # any digit → not bare site
    return True


def _has_trailing_number(name: str) -> bool:
    """Return True if name ends with a number (Site+number pattern, R3)."""
    # Allow Roman numerals and ASCII digits.
    # The pattern must not match names with explicit unit tokens (those are Unit-grain).
    stripped = name.strip()
    if _UNIT_TOKEN_RE.search(stripped):
        return False  # "Vinh Tan 2 Unit 1" is a Unit, not a Plant
    return bool(re.search(r"\b(?:[IVXivx]+|\d+)\s*$", stripped))


# ---------------------------------------------------------------------------
# Per-row predicates
# ---------------------------------------------------------------------------


def capacity_plausible_for_level(
    level: str | Level,
    fuel: str,
    capacity_mwe: float | None,
) -> bool | None:
    """Return True / False / None for capacity plausibility given the declared level.

    Args:
        level:        The Level declared by the model (string or Level enum).
        fuel:         Fuel type string (for future fuel-conditional caps; unused now).
        capacity_mwe: Numeric capacity in MW, or None if absent.

    Returns:
        True  — capacity is plausible for the declared level.
        False — capacity violates the cap for the declared level.
        None  — cannot score (level=Unknown, or capacity absent).
    """
    if capacity_mwe is None:
        return None

    # Normalise level
    try:
        lv = Level(str(level).lower())
    except ValueError:
        return None

    if lv == Level.UNKNOWN:
        return None

    if lv == Level.UNIT:
        return capacity_mwe <= _UNIT_CAP_MW

    if lv == Level.PLANT:
        return capacity_mwe <= _PLANT_CAP_MW

    if lv == Level.BLOCK:
        # CCGT blocks are above the single-shaft threshold; no upper cap
        return capacity_mwe >= _BLOCK_MIN_MW

    # Level.COMPLEX — no upper cap; any positive capacity is plausible
    return capacity_mwe > 0


def level_consistent_with_name(name: str, level: str | Level) -> bool | None:
    """Return True / False / None for level-name structural consistency.

    Applies three name-pattern rules (see module docstring R1/R2/R3).

    Args:
        name:  The plant name as emitted by the model.
        level: The Level declared by the model.

    Returns:
        True  — no rule fires; level is structurally consistent with the name.
        False — at least one violation rule fires.
        None  — cannot score (empty name or level=Unknown).
    """
    stripped = name.strip()
    if not stripped:
        return None

    try:
        lv = Level(str(level).lower())
    except ValueError:
        return None

    if lv == Level.UNKNOWN:
        return None

    # R1 — merge-marker names cannot be Unit
    if lv == Level.UNIT and _ATOMICITY_VIOLATION_RE.search(stripped):
        return False

    # R2 — bare-site names cannot be Unit or Plant
    if lv in (Level.UNIT, Level.PLANT) and _is_bare_site(stripped):
        return False

    # R3 — Site+number names imply Plant, not Unit
    # (A Unit name carries an explicit unit token; a bare Site+number is Plant)
    if lv == Level.UNIT and _has_trailing_number(stripped):
        return False

    return True


# ---------------------------------------------------------------------------
# Run-level scoring functions (fraction of rows passing)
# ---------------------------------------------------------------------------


def score_capacity_plausible_for_level(
    rows: list[dict[str, str]],
) -> tuple[float | None, str | None]:
    """Return (fraction, annotation) for capacity-plausibility-for-level.

    Scores only rows where both level and capacity are available.
    Returns (None, "column_missing") if no scoreable row is found.
    """
    if not rows:
        return None, "no_rows"

    seen = 0
    plausible = 0
    for row in rows:
        level_str = (row.get("level") or "").strip()
        if not level_str:
            continue
        cap_str = ""
        for key in _CAPACITY_KEYS:
            raw = row.get(key)
            if raw is not None and str(raw).strip():
                cap_str = str(raw)
                break
        cap = _as_float(cap_str)
        fuel = (row.get("fuel") or "").strip().lower()

        verdict = capacity_plausible_for_level(level_str, fuel, cap)
        if verdict is None:
            continue
        seen += 1
        if verdict:
            plausible += 1

    if seen == 0:
        return None, "column_missing"
    frac = round(plausible / seen, 4)
    return frac, None


def score_level_consistent_with_name(
    rows: list[dict[str, str]],
) -> tuple[float | None, str | None]:
    """Return (fraction, annotation) for level-name structural consistency.

    Scores only rows where both name and level are available.
    Returns (None, "column_missing") if no scoreable row is found.
    """
    if not rows:
        return None, "no_rows"

    seen = 0
    consistent = 0
    for row in rows:
        name = (row.get("name") or "").strip()
        level_str = (row.get("level") or "").strip()
        if not name or not level_str:
            continue
        verdict = level_consistent_with_name(name, level_str)
        if verdict is None:
            continue
        seen += 1
        if verdict:
            consistent += 1

    if seen == 0:
        return None, "column_missing"
    frac = round(consistent / seen, 4)
    return frac, None
