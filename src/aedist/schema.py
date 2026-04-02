"""Canonical schema for power plant entries.

This module defines the data model used both for the expert reference dataset
and for system outputs. All evaluation is performed on normalized instances
of these models.
"""

from enum import Enum

from pydantic import BaseModel, Field


class FuelType(str, Enum):
    COAL = "coal"
    GAS = "gas"
    IMPORTED_LNG = "imported lng"
    OIL = "oil"
    UNKNOWN = "unknown"


class PlantStatus(str, Enum):
    RETIRED = "retired"
    OPERATIONAL = "operational"
    CONSTRUCTING = "constructing"
    PLANNED = "planned"
    PROPOSED = "proposed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class Plant(BaseModel):
    """A single power plant entry in canonical form.

    One row = one plant (not unit, not complex).  See ADR-4.
    """

    name: str = Field(..., description="Canonical plant name.")
    fuel: FuelType = Field(default=FuelType.UNKNOWN)
    status: PlantStatus = Field(default=PlantStatus.UNKNOWN)
    cod: str | None = Field(default=None, description="Connection date (year or YYYY-MM-DD).")
    province: str | None = Field(default=None)
    capacity_mwe: float | None = Field(default=None, ge=0)


class SourcedPlant(Plant):
    """Plant entry with provenance information, for system outputs."""

    sources: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class MatchType(str, Enum):
    EXACT = "exact"
    EXACT_CAPACITY_DIFF = "exact_capacity_diff"
    FUZZY = "fuzzy"
    FUZZY_CAPACITY_DIFF = "fuzzy_capacity_diff"
    SYSTEM_ONLY = "system_only"
    REFERENCE_ONLY = "reference_only"


class ReconciliationEntry(BaseModel):
    """One row in the reconciliation table."""

    reference_name: str | None = None
    system_name: str | None = None
    reference_province: str | None = None
    system_province: str | None = None
    reference_fuel: str | None = None
    system_fuel: str | None = None
    reference_capacity_mwe: float | None = None
    system_capacity_mwe: float | None = None
    capacity_diff_pct: float | None = None
    match_type: MatchType = MatchType.REFERENCE_ONLY
    fuel_match: bool | None = None
    status_match: bool | None = None
    province_match: bool | None = None
    notes: str = ""
