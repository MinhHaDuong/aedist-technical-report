"""Internal coherence checks for extracted power plant data (v1: table-based).

Scope: one document, one table, one extraction. Does this table add
up? Are the rows self-consistent? Are there duplicates?

Explicitly OUT of scope for v1:
- Cross-document fusion (PDP7 vs PDP8, planned vs as-built)
- Temporal reconciliation across planning document versions
- Measurand ambiguity (nameplate vs net vs gross capacity)
- Knowledge graph / document knowledge store

These are v2+ concerns. See docs/quality-grounding.md for the
discussion of why.

Three levels, each with a clean entry point:

1. **Row-level** — each row is self-consistent (schema, business rules).
2. **Cross-row** — rows are consistent with each other (dedup).
3. **Aggregate** — the table is consistent with known control totals
   from the *same* document.

Each check returns a list of CoherenceIssue objects. The caller
decides severity — the checks report, they don't filter.

Design: expandable. Add new checks by appending to the relevant
function. Each check is a simple predicate on one or more rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .schema import FuelType, Plant, PlantStatus


class IssueLevel(StrEnum):
    ROW = "row"
    CROSS_ROW = "cross_row"
    AGGREGATE = "aggregate"


class IssueSeverity(StrEnum):
    ERROR = "error"  # Definitely wrong
    WARNING = "warning"  # Suspicious, needs review


@dataclass
class CoherenceIssue:
    """One coherence problem found in the data."""

    level: IssueLevel
    severity: IssueSeverity
    row_indices: list[int]  # Which rows are involved (0-indexed)
    check: str  # Machine-readable check name
    message: str  # Human-readable description


# ── Vietnamese provinces (63 provinces + 5 municipalities) ──────────
# Canonical names as used in the reference dataset.  Diacritics may
# vary in system outputs; the check normalises before comparing.

VIETNAM_PROVINCES: frozenset[str] = frozenset({
    # Municipalities
    "Hà Nội", "Hồ Chí Minh", "Hải Phòng", "Đà Nẵng", "Cần Thơ",
    # Northern
    "Hà Giang", "Cao Bằng", "Bắc Kạn", "Tuyên Quang", "Lào Cai",
    "Điện Biên", "Lai Châu", "Sơn La", "Yên Bái", "Hòa Bình",
    "Thái Nguyên", "Lạng Sơn", "Quảng Ninh", "Bắc Giang", "Phú Thọ",
    "Vĩnh Phúc", "Bắc Ninh", "Hải Dương", "Hưng Yên", "Thái Bình",
    "Hà Nam", "Nam Định", "Ninh Bình",
    # Central
    "Thanh Hóa", "Nghệ An", "Hà Tĩnh", "Quảng Bình", "Quảng Trị",
    "Thừa Thiên Huế", "Quảng Nam", "Quảng Ngãi", "Bình Định",
    "Phú Yên", "Khánh Hòa", "Ninh Thuận", "Bình Thuận",
    # Central Highlands
    "Kon Tum", "Gia Lai", "Đắk Lắk", "Đắk Nông", "Lâm Đồng",
    # Southern
    "Bình Phước", "Tây Ninh", "Bình Dương", "Đồng Nai",
    "Bà Rịa-Vũng Tàu", "Long An", "Tiền Giang", "Bến Tre",
    "Trà Vinh", "Vĩnh Long", "Đồng Tháp", "An Giang", "Kiên Giang",
    "Hậu Giang", "Sóc Trăng", "Bạc Liêu", "Cà Mau",
})

# Normalised lookup (lowercase, stripped diacritics not needed —
# we compare original strings case-insensitively).
_PROVINCES_LOWER: frozenset[str] = frozenset(p.lower() for p in VIETNAM_PROVINCES)

# Reference also uses some ASCII-only spellings
_PROVINCE_ALIASES: dict[str, str] = {
    "bac giang": "Bắc Giang",
    "hai duong": "Hải Dương",
    "lang son": "Lạng Sơn",
    "lao cai": "Lào Cai",
    "nam dinh": "Nam Định",
    "ninh binh": "Ninh Bình",
    "ninh thuan": "Ninh Thuận",
    "thai nguyen": "Thái Nguyên",
    "huế": "Thừa Thiên Huế",
    "hau giang": "Hậu Giang",
    "tra vinh": "Trà Vinh",
}


def _province_known(province: str | None) -> bool:
    """Return True if province matches a known Vietnamese province."""
    if province is None:
        return True  # Missing is not incoherent, just incomplete
    low = province.strip().lower()
    return low in _PROVINCES_LOWER or low in _PROVINCE_ALIASES


# Compatible fuel × technology pairs (extensible)
_VALID_FUEL_STATUS: set[tuple[FuelType, PlantStatus]] = set()  # all pairs valid for now


# ── Row-level checks ────────────────────────────────────────────────

def check_row_coherence(plants: list[Plant]) -> list[CoherenceIssue]:
    """Check each row independently for internal consistency.

    Current checks:
    - capacity must be positive (>0) if present
    - fuel must not be UNKNOWN
    - status must not be UNKNOWN
    - province must be a known Vietnamese province
    - retired plants should not have future commissioning dates
    """
    issues: list[CoherenceIssue] = []

    for i, p in enumerate(plants):
        # Capacity sanity
        if p.capacity_mwe is not None and p.capacity_mwe <= 0:
            issues.append(CoherenceIssue(
                level=IssueLevel.ROW,
                severity=IssueSeverity.ERROR,
                row_indices=[i],
                check="zero_or_negative_capacity",
                message=f"Plant '{p.name}' has capacity {p.capacity_mwe} MW",
            ))

        # Unknown fuel
        if p.fuel == FuelType.UNKNOWN:
            issues.append(CoherenceIssue(
                level=IssueLevel.ROW,
                severity=IssueSeverity.WARNING,
                row_indices=[i],
                check="unknown_fuel",
                message=f"Plant '{p.name}' has unknown fuel type",
            ))

        # Unknown status
        if p.status == PlantStatus.UNKNOWN:
            issues.append(CoherenceIssue(
                level=IssueLevel.ROW,
                severity=IssueSeverity.WARNING,
                row_indices=[i],
                check="unknown_status",
                message=f"Plant '{p.name}' has unknown status",
            ))

        # Province not recognised
        if not _province_known(p.province):
            issues.append(CoherenceIssue(
                level=IssueLevel.ROW,
                severity=IssueSeverity.WARNING,
                row_indices=[i],
                check="unknown_province",
                message=f"Plant '{p.name}' has unrecognised province '{p.province}'",
            ))

        # Retired plant with future COD
        if p.status == PlantStatus.RETIRED and p.cod is not None:
            try:
                year = int(p.cod[:4])
                if year > 2025:
                    issues.append(CoherenceIssue(
                        level=IssueLevel.ROW,
                        severity=IssueSeverity.ERROR,
                        row_indices=[i],
                        check="retired_future_cod",
                        message=f"Plant '{p.name}' is retired but has COD {p.cod}",
                    ))
            except (ValueError, IndexError):
                pass  # Unparseable COD is a different problem

    return issues


# ── Cross-row checks ────────────────────────────────────────────────

def check_cross_row_coherence(plants: list[Plant]) -> list[CoherenceIssue]:
    """Check rows against each other.

    Current checks:
    - Duplicate detection: same name + same province = likely duplicate
    """
    issues: list[CoherenceIssue] = []

    # Dedup: group by (normalised name, province)
    seen: dict[tuple[str, str | None], list[int]] = {}
    for i, p in enumerate(plants):
        key = (p.name.strip().lower(), (p.province or "").strip().lower() or None)
        seen.setdefault(key, []).append(i)

    for (name, province), indices in seen.items():
        if len(indices) > 1:
            issues.append(CoherenceIssue(
                level=IssueLevel.CROSS_ROW,
                severity=IssueSeverity.ERROR,
                row_indices=indices,
                check="duplicate_plant",
                message=(
                    f"Duplicate: '{name}' in province '{province}' "
                    f"appears {len(indices)} times (rows {indices})"
                ),
            ))

    return issues


# ── Aggregate checks (control totals) ──────────────────────────────

@dataclass
class ControlTotal:
    """A known aggregate constraint from a source document."""

    source: str  # e.g. "PDP8_Annex_III.2"
    fuel: FuelType | None = None  # None = all fuels
    status: PlantStatus | None = None  # None = all statuses
    province: str | None = None  # None = national
    total_mw: float = 0.0


def check_aggregate_coherence(
    plants: list[Plant],
    control_totals: list[ControlTotal],
    tolerance_pct: float = 5.0,
) -> list[CoherenceIssue]:
    """Check extracted data against known control totals.

    For each control total, filter plants by the specified dimensions
    (fuel, status, province), sum capacity, and compare.

    Args:
        plants: extracted plant list
        control_totals: known aggregates from source documents
        tolerance_pct: percentage deviation that triggers a warning
    """
    issues: list[CoherenceIssue] = []

    for ct in control_totals:
        filtered = plants
        if ct.fuel is not None:
            filtered = [p for p in filtered if p.fuel == ct.fuel]
        if ct.status is not None:
            filtered = [p for p in filtered if p.status == ct.status]
        if ct.province is not None:
            filtered = [
                p for p in filtered
                if p.province and p.province.strip().lower() == ct.province.strip().lower()
            ]

        total = sum(p.capacity_mwe or 0 for p in filtered)
        if ct.total_mw == 0:
            continue  # Can't check against zero

        deviation_pct = abs(total - ct.total_mw) / ct.total_mw * 100

        if deviation_pct > tolerance_pct:
            severity = IssueSeverity.ERROR if deviation_pct > 20 else IssueSeverity.WARNING
            issues.append(CoherenceIssue(
                level=IssueLevel.AGGREGATE,
                severity=severity,
                row_indices=[],  # Aggregate — no single row responsible
                check="control_total_deviation",
                message=(
                    f"Control total '{ct.source}'"
                    f"{f' fuel={ct.fuel}' if ct.fuel else ''}"
                    f"{f' status={ct.status}' if ct.status else ''}"
                    f"{f' province={ct.province}' if ct.province else ''}"
                    f": expected {ct.total_mw:.0f} MW, got {total:.0f} MW"
                    f" (deviation {deviation_pct:.1f}%)"
                ),
            ))

    return issues


# ── Main entry point ────────────────────────────────────────────────

def check_coherence(
    plants: list[Plant],
    control_totals: list[ControlTotal] | None = None,
) -> list[CoherenceIssue]:
    """Run all coherence checks and return combined issues.

    This is the main entry point. Callers can also call individual
    check functions directly for targeted use.
    """
    issues: list[CoherenceIssue] = []
    issues.extend(check_row_coherence(plants))
    issues.extend(check_cross_row_coherence(plants))
    if control_totals:
        issues.extend(check_aggregate_coherence(plants, control_totals))
    return issues
