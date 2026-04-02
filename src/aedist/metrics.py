"""Metrics for evaluating AI-generated economic statistics.

Computes coverage (recall), precision, justification rate,
and error taxonomy from a reconciliation table.
"""

from collections import Counter
from dataclasses import dataclass, field

from .schema import MatchType, ReconciliationEntry


_MATCHED_TYPES = {
    MatchType.EXACT,
    MatchType.EXACT_CAPACITY_DIFF,
    MatchType.FUZZY,
    MatchType.FUZZY_CAPACITY_DIFF,
}


@dataclass
class BenchmarkMetrics:
    """Aggregate metrics for one evaluation run."""

    # Core metrics
    coverage: float = 0.0
    precision: float = 0.0
    f1: float = 0.0

    # Counts
    n_reference: int = 0
    n_system: int = 0
    n_matched: int = 0
    n_exact: int = 0
    n_fuzzy: int = 0
    n_missed: int = 0
    n_hallucinated: int = 0

    # Attribute accuracy (among matched entries)
    fuel_accuracy: float | None = None
    status_accuracy: float | None = None
    province_accuracy: float | None = None
    capacity_match_rate: float | None = None

    # Error taxonomy counts
    errors: dict[str, int] = field(default_factory=dict)

    # Justification (to be filled externally)
    justification_rate: float | None = None


def compute_metrics(entries: list[ReconciliationEntry]) -> BenchmarkMetrics:
    """Compute all benchmark metrics from a reconciliation table."""
    matched = [e for e in entries if e.match_type in _MATCHED_TYPES]
    missed = [e for e in entries if e.match_type == MatchType.REFERENCE_ONLY]
    hallucinated = [e for e in entries if e.match_type == MatchType.SYSTEM_ONLY]

    n_reference = len(matched) + len(missed)
    n_system = len(matched) + len(hallucinated)
    n_matched = len(matched)

    coverage = n_matched / n_reference if n_reference > 0 else 0.0
    precision = n_matched / n_system if n_system > 0 else 0.0
    f1 = (
        2 * coverage * precision / (coverage + precision)
        if (coverage + precision) > 0
        else 0.0
    )

    type_counts = Counter(e.match_type for e in matched)
    n_exact = type_counts.get(MatchType.EXACT, 0) + type_counts.get(MatchType.EXACT_CAPACITY_DIFF, 0)
    n_fuzzy = type_counts.get(MatchType.FUZZY, 0) + type_counts.get(MatchType.FUZZY_CAPACITY_DIFF, 0)

    def _accuracy(attr: str) -> float | None:
        checks = [getattr(e, attr) for e in matched if getattr(e, attr) is not None]
        return round(sum(checks) / len(checks), 4) if checks else None

    cap_ok = [e for e in matched if e.match_type in {MatchType.EXACT, MatchType.FUZZY}]

    errors = {
        "hallucinated_plant": len(hallucinated),
        "missed_plant": len(missed),
        "wrong_fuel": len([e for e in matched if e.fuel_match is False]),
        "wrong_status": len([e for e in matched if e.status_match is False]),
        "wrong_province": len([e for e in matched if e.province_match is False]),
        "capacity_mismatch": len([
            e for e in matched
            if e.match_type in {MatchType.EXACT_CAPACITY_DIFF, MatchType.FUZZY_CAPACITY_DIFF}
        ]),
    }

    return BenchmarkMetrics(
        coverage=round(coverage, 4),
        precision=round(precision, 4),
        f1=round(f1, 4),
        n_reference=n_reference,
        n_system=n_system,
        n_matched=n_matched,
        n_exact=n_exact,
        n_fuzzy=n_fuzzy,
        n_missed=len(missed),
        n_hallucinated=len(hallucinated),
        fuel_accuracy=_accuracy("fuel_match"),
        status_accuracy=_accuracy("status_match"),
        province_accuracy=_accuracy("province_match"),
        capacity_match_rate=round(len(cap_ok) / len(matched), 4) if matched else None,
        errors=errors,
    )


def format_metrics(m: BenchmarkMetrics) -> str:
    """Return a human-readable summary of metrics."""
    lines = [
        "=== Benchmark Metrics ===",
        f"Reference plants:    {m.n_reference}",
        f"System plants:       {m.n_system}",
        f"Matched:             {m.n_matched} (exact: {m.n_exact}, fuzzy: {m.n_fuzzy})",
        f"Missed:              {m.n_missed}",
        f"Hallucinated:        {m.n_hallucinated}",
        "",
        f"Coverage (recall):   {m.coverage:.1%}",
        f"Precision:           {m.precision:.1%}",
        f"F1:                  {m.f1:.1%}",
    ]
    for attr, label in [
        ("fuel_accuracy", "Fuel accuracy"),
        ("status_accuracy", "Status accuracy"),
        ("province_accuracy", "Province accuracy"),
        ("capacity_match_rate", "Capacity match rate"),
    ]:
        val = getattr(m, attr)
        if val is not None:
            lines.append(f"{label + ':':21s}{val:.1%}")
    if m.justification_rate is not None:
        lines.append(f"Justification rate:  {m.justification_rate:.1%}")
    lines.append("")
    lines.append("Error taxonomy:")
    for k, v in m.errors.items():
        lines.append(f"  {k}: {v}")
    return "\n".join(lines)
