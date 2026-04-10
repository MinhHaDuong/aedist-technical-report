"""Canonical schema for power plant entries and run records.

This module defines the data model used both for the expert reference dataset
and for system outputs. All evaluation is performed on normalized instances
of these models.

RunRecord is the unified representation of a single benchmark run,
forming the measurements table (the single source of truth for all results).
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml
from pydantic import BaseModel, Field


class FuelType(StrEnum):
    COAL = "coal"
    GAS = "gas"
    IMPORTED_LNG = "imported lng"
    OIL = "oil"
    UNKNOWN = "unknown"


class PlantStatus(StrEnum):
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
    source_ref: str | None = Field(
        default=None,
        description="Primary source document reference, e.g. 'Decision 1509/QĐ-BCT, Annexe II.1'.",
    )


class SourceType(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    HALLUCINATED = "hallucinated"
    NONE = "none"


class SourcedPlant(Plant):
    """Plant entry with provenance information, for system outputs."""

    sources: list[str] = Field(default_factory=list)
    source_types: list[SourceType] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_score: int = Field(
        default=0,
        ge=0,
        le=4,
        description=(
            "Evidence quality rubric: 0=hallucinated sources, 1=no sources, "
            "2=one secondary, 3=one primary, 4=two+ independent primary."
        ),
    )


class MatchType(StrEnum):
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
    reference_source_ref: str | None = None
    system_source_ref: str | None = None
    similarity_score: float | None = None
    notes: str = ""


# ---------------------------------------------------------------------------
# RunRecord — measurements table
# ---------------------------------------------------------------------------


class Method(StrEnum):
    SINGLE = "single"
    MULTITURN = "multiturn"
    RAG = "rag"
    WEB = "web"
    DECOMPOSED = "decomposed"
    SOURCED = "sourced"
    FRONTIER = "frontier"
    VERIFICATION = "verification"


class MethodParams(BaseModel):
    """Method-specific parameters captured at run time."""

    model: str = Field(..., description="Model identifier (e.g. openai/gpt-4o).")
    temperature: float | None = None
    max_tokens: int | None = None
    prompt_version: str | None = Field(default=None, description="Prompt template identifier.")
    extra: dict | None = Field(default=None, description="Arbitrary method-specific parameters.")


class ResourceUse(BaseModel):
    """Resource consumption for one run."""

    wall_s: float | None = Field(default=None, ge=0, description="Wall-clock seconds.")
    cost_usd: float | None = Field(default=None, ge=0, description="API cost in USD.")
    tokens_in: int | None = Field(default=None, ge=0)
    tokens_out: int | None = Field(default=None, ge=0)


class ResultSummary(BaseModel):
    """Compact evaluation result for one run."""

    status: str = Field(default="ok", description="Run outcome: ok | refusal | error | empty | qualitative")
    n_plants: int | None = Field(default=None, ge=0)
    tp: int | None = Field(default=None, ge=0, description="True positives (matched).")
    fp: int | None = Field(default=None, ge=0, description="False positives (hallucinated).")
    fn: int | None = Field(default=None, ge=0, description="False negatives (missed).")
    f1: float | None = Field(default=None, ge=0.0, le=1.0)
    fuel_accuracy: float | None = Field(default=None, ge=0.0, le=1.0)
    status_accuracy: float | None = Field(default=None, ge=0.0, le=1.0)
    province_accuracy: float | None = Field(default=None, ge=0.0, le=1.0)


class RunRecord(BaseModel):
    """One row in the measurements table.

    Each RunRecord captures a single benchmark run end-to-end:
    what method was used, what resources it consumed, and what
    it scored.
    """

    run_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC time the run completed.",
    )
    method: Method
    method_params: MethodParams
    resource_use: ResourceUse = Field(default_factory=ResourceUse)
    result_file: str | None = Field(
        default=None, description="Path to the raw result file (relative to repo root)."
    )
    result_summary: ResultSummary = Field(default_factory=ResultSummary)
    justification: dict | None = Field(
        default=None, description="Optional justification metadata."
    )

    # -- serialization helpers ------------------------------------------------

    def to_jsonl_line(self) -> str:
        """Serialize to a single JSON-lines string (no trailing newline)."""
        return self.model_dump_json()

    @classmethod
    def from_jsonl_line(cls, line: str) -> RunRecord:
        """Deserialize from a single JSON-lines string."""
        return cls.model_validate_json(line)

    @classmethod
    def load_jsonl(cls, path: str | Path) -> list[RunRecord]:
        """Load all records from a JSON-lines file."""
        records = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(cls.from_jsonl_line(line))
        return records

    @classmethod
    def save_jsonl(cls, records: list[RunRecord], path: str | Path) -> None:
        """Write records to a JSON-lines file."""
        with open(path, "w") as f:
            for r in records:
                f.write(r.to_jsonl_line() + "\n")


# ---------------------------------------------------------------------------
# JobSpec / LeaseInfo — worker job board
# ---------------------------------------------------------------------------


class WorkerPool(StrEnum):
    OPENROUTER = "openrouter"
    PADME = "padme"


class JobSpec(BaseModel):
    """Specification for a single benchmark job dispatched to a worker.

    Mirrors the sweep YAML configs with additional per-job fields
    for scheduling and resource management.
    """

    job_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    priority: int = Field(default=0, description="Higher value = higher priority.")
    mode: Method
    prompt: str = Field(default="", description="Path to prompt file (unused when prompt_modules is set).")
    models_file: str = Field(..., description="Path to models YAML file.")
    model_filter: str | None = Field(
        default=None, description="Glob or regex to select a subset of models."
    )
    corpus: str | None = Field(
        default=None, description="Path to RAG corpus directory (rag mode)."
    )
    followups: str | None = Field(
        default=None, description="Path to followups file (multiturn mode)."
    )
    strategy: str | None = Field(
        default=None, description="RAG retrieval strategy (e.g. wholesale)."
    )
    prompt_modules: list[str] | None = Field(
        default=None,
        description="Module names for assemble_prompt(). Mutually exclusive with prompt file.",
    )
    modules_dir: str | None = Field(
        default=None,
        description="Directory containing prompt module text files (default: experiments/prompts/modules/).",
    )
    repeat: int = Field(default=3, ge=1)
    run_number: int = Field(default=1, ge=1, description="Which run this job represents (1-indexed).")
    budget_usd: float = Field(default=10.0, ge=0)
    output_dir: str = Field(..., description="Output directory for results.")
    timeout_seconds: int = Field(default=600, ge=0)
    estimated_duration: float | None = Field(
        default=None, ge=0, description="Estimated wall-clock seconds."
    )
    worker_pool: WorkerPool = WorkerPool.OPENROUTER

    # -- YAML serialization ---------------------------------------------------

    def to_yaml(self) -> str:
        """Serialize to YAML string."""
        return yaml.dump(
            self.model_dump(mode="json", exclude_none=True),
            default_flow_style=False,
            sort_keys=False,
        )

    @classmethod
    def from_yaml(cls, text: str) -> JobSpec:
        """Deserialize from a YAML string."""
        data: dict[str, Any] = yaml.safe_load(text)
        return cls.model_validate(data)

    @staticmethod
    def _remap_sweep_fields(data: dict[str, Any]) -> dict[str, Any]:
        """Remap sweep-config field names to JobSpec field names."""
        if "models" in data and "models_file" not in data:
            data["models_file"] = data.pop("models")
        if "output" in data and "output_dir" not in data:
            data["output_dir"] = data.pop("output")
        return data

    @classmethod
    def from_sweep_yaml(cls, path: str | Path) -> JobSpec:
        """Load a JobSpec from an existing sweep config YAML."""
        with open(path) as f:
            data: dict[str, Any] = yaml.safe_load(f)
        return cls.model_validate(cls._remap_sweep_fields(data))

    @classmethod
    def from_toml_section(cls, section: dict[str, Any]) -> JobSpec:
        """Load a JobSpec from a [sweeps.*] section of experiments.toml."""
        return cls.model_validate(cls._remap_sweep_fields(dict(section)))


class LeaseInfo(BaseModel):
    """Tracks an exclusive claim on a job by a worker."""

    job_id: str
    worker_id: str
    start_time: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
    expiry_time: datetime = Field(
        ..., description="UTC time after which the lease expires and the job can be reclaimed."
    )
