"""Canonical JSON schema for the Exp2 mart.

The mart stores structured analysis records and immutable artifact pointers.
It deliberately rejects verbatim chat payload fields.
"""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

_MART_SCHEMA_NAME = "exp2_mart"
# v2 (ticket 0431): Exp2ScoreMartRecord carries ``reference`` — the release
# filename of the dataset the accuracy metrics were computed against.
_MART_SCHEMA_VERSION = 2
_SHA256_PATTERN = r"^[0-9a-f]{64}$"


class ArtifactPointer(BaseModel):
    """Pointer to an immutable artifact in the repository."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(..., min_length=1, description="Repo-relative artifact path.")
    sha256: str = Field(..., pattern=_SHA256_PATTERN, description="SHA-256 digest.")

    @model_validator(mode="after")
    def _validate_path(self) -> "ArtifactPointer":
        candidate = Path(self.path)
        if candidate.is_absolute():
            raise ValueError("artifact paths must be repo-relative")
        if ".." in candidate.parts:
            raise ValueError("artifact paths must not traverse upward")
        return self


class MetricValue(BaseModel):
    """A metric value with its annotation code."""

    model_config = ConfigDict(extra="forbid")

    value: float | None = Field(default=None, ge=0.0, le=1.0)
    annotation: str = ""


class AccuracyMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    coverage: MetricValue = Field(default_factory=MetricValue)
    precision: MetricValue = Field(default_factory=MetricValue)
    f1: MetricValue = Field(default_factory=MetricValue)
    fuel: MetricValue = Field(default_factory=MetricValue)
    status: MetricValue = Field(default_factory=MetricValue)
    province: MetricValue = Field(default_factory=MetricValue)


class CoherenceMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vocab_adherence: MetricValue = Field(default_factory=MetricValue)
    status_vocab_adherence: MetricValue = Field(default_factory=MetricValue)
    capacity_nonnegative: MetricValue = Field(default_factory=MetricValue)


class ProvenanceMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_presence: MetricValue = Field(default_factory=MetricValue)
    high_conf_dual_source: MetricValue = Field(default_factory=MetricValue)
    n_rows_with_source: int | None = Field(default=None, ge=0)
    n_confidence_high: int | None = Field(default=None, ge=0)
    has_confidence_column: bool | None = Field(default=None)


class TemporalityMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asof_presence: MetricValue = Field(default_factory=MetricValue)
    plausible_range: MetricValue = Field(default_factory=MetricValue)


class FieldCompletenessMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    core: MetricValue = Field(default_factory=MetricValue)
    capacity: MetricValue = Field(default_factory=MetricValue)


class ScoreSummary(BaseModel):
    """Grouped mechanical-score payload matching the scorer contract."""

    model_config = ConfigDict(extra="forbid")

    n_rows: int = Field(..., ge=0)
    accuracy: AccuracyMetrics = Field(default_factory=AccuracyMetrics)
    coherence: CoherenceMetrics = Field(default_factory=CoherenceMetrics)
    provenance: ProvenanceMetrics = Field(default_factory=ProvenanceMetrics)
    temporality: TemporalityMetrics = Field(default_factory=TemporalityMetrics)
    field_completeness: FieldCompletenessMetrics = Field(default_factory=FieldCompletenessMetrics)


class RunSummary(BaseModel):
    """Run-level summary for one Exp2 output."""

    model_config = ConfigDict(extra="forbid")

    n_rows: int = Field(..., ge=0)
    classification: str | None = Field(default=None)
    class_trace: list[str] | None = Field(default=None)
    turns: int | None = Field(default=None, ge=0)
    tokens_in: int | None = Field(default=None, ge=0)
    tokens_out: int | None = Field(default=None, ge=0)
    wall_s: float | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    classifier_cost_usd: float | None = Field(default=None, ge=0)
    narrative_chars: int | None = Field(default=None, ge=0)
    n_bib_entries: int | None = Field(default=None, ge=0)


class ProbeSummary(BaseModel):
    """Turn/probe-level summary for one Exp2 probe artifact."""

    model_config = ConfigDict(extra="forbid")

    turn: int = Field(..., ge=1)
    probe_label: str | None = Field(default=None)
    rows: int | None = Field(default=None, ge=0)


class Exp2MartBase(BaseModel):
    """Common mart fields shared by all Exp2 record types."""

    model_config = ConfigDict(extra="forbid")

    mart_schema: Literal["exp2_mart"] = _MART_SCHEMA_NAME
    mart_schema_version: Literal[2] = _MART_SCHEMA_VERSION
    record_kind: Literal["run", "probe", "score"]
    record_id: str = Field(..., min_length=1)
    parent_record_id: str | None = Field(default=None)
    arm: Literal["naive", "optimised", "arm3", "arm4"]
    agent: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    run: int = Field(..., ge=1)
    prompt_version: str | None = Field(default=None)
    result_file: ArtifactPointer | None = Field(default=None)
    parsed_table_file: ArtifactPointer | None = Field(default=None)
    probe_file: ArtifactPointer | None = Field(default=None)


class Exp2RunMartRecord(Exp2MartBase):
    """Run-level mart record."""

    record_kind: Literal["run"] = "run"
    run_summary: RunSummary
    result_file: ArtifactPointer
    narrative_file: ArtifactPointer | None = Field(default=None)
    bib_file: ArtifactPointer | None = Field(default=None)
    compliance_file: ArtifactPointer | None = Field(default=None)


class Exp2ProbeMartRecord(Exp2MartBase):
    """Turn/probe-level mart record."""

    record_kind: Literal["probe"] = "probe"
    probe_summary: ProbeSummary
    probe_file: ArtifactPointer


class Exp2ScoreMartRecord(Exp2MartBase):
    """Mechanical score mart record."""

    record_kind: Literal["score"] = "score"
    score_summary: ScoreSummary
    result_file: ArtifactPointer
    # Reference release filename (e.g. the VN thermal v1 CSV) the accuracy
    # metrics were scored against; None on legacy rows scored before 0431.
    reference: str | None = Field(
        default=None,
        description=(
            "Release filename of the reference dataset the accuracy metrics "
            "were computed against (ticket 0431). None on legacy score rows "
            "scored before the reference was stamped."
        ),
    )


Exp2MartRecord = Exp2RunMartRecord | Exp2ProbeMartRecord | Exp2ScoreMartRecord
