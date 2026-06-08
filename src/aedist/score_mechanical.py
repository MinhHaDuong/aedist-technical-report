"""Mechanical scoring helpers for Exp2 outputs.

Pipeline phase: P2 (score & consolidate) — invoked by experiments/derived/score.mk.

Consumes canonical rows (from score_ingest), computes five scoring dimensions,
and appends one row to experiments/derived/sota_cross_eval.csv.
"""

import argparse
import csv
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from .config import VN_THERMAL_PLANTS_RELEASE_CSV
from .evaluate import load_plants_csv, plants_from_dicts
from .metrics import compute_metrics
from .reconcile import reconcile
from .score_ingest import RunLocator, ingest_run

log = logging.getLogger(__name__)

_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2}|2100)\b")
_SOURCE_DIVERSITY_CLIP = 20
_SOURCE_NOT_FOUND = frozenset({"not found", "n/a", "unknown", ""})
_CAPACITY_KEYS = ("capacity_mwe", "total_mwe", "total_mw", "capacity")

# Row-atomicity detector (ticket 0396, handoff §6).
# Reads ONLY the `name` field; technology-composition strings in other columns
# ("2 GT + 1 ST", "Coal + BFG") are never touched.
# Flag patterns: two plant identifiers joined in one name field.
_ATOMICITY_VIOLATION_RE = re.compile(
    r"\d\s*&\s*\d"  # "3 & 4", "1 & 2"
    r"|[ivxIVX]+\s*&\s*[ivxIVX]+"  # "I & II", "III & IV"
    r"|[ivxIVX0-9]\s*\+\s*[ivxIVX0-9]"  # "I+II", "1+2" (identifier join)
    r"|\d\s*và\s*\d"  # Vietnamese "1 và 2"
    r"|\d\s*[-–]\s*\d",  # "1-3", "1–3" (numbered range)
)

_ALLOWED_FUELS = {
    "coal",
    "gas",
    "natural gas",
    "local gas",
    "local natural gas",
    "lng",
    "imported lng",
    "imported gas",
    "oil",
    "unknown",
}

_ALLOWED_STATUSES = {
    # GEM canonical terms
    "announced",
    "pre-permit",
    "pre-permit development",
    "permitted",
    "construction",
    "operating",
    "shelved",
    "cancelled",
    "retired",
    # Accepted synonyms
    "operational",
    "under construction",
    "approved",
    "planned",
    "suspended",
    "commissioning",
    "decommissioned",
}

_CSV_COLUMNS = [
    "arm",
    "model",
    "run",
    "prompt_version",
    "reference",
    "n_rows",
    "accuracy_coverage",
    "accuracy_coverage_annotation",
    "accuracy_precision",
    "accuracy_precision_annotation",
    "accuracy_f1",
    "accuracy_f1_annotation",
    "accuracy_fuel",
    "accuracy_fuel_annotation",
    "accuracy_status",
    "accuracy_status_annotation",
    "accuracy_province",
    "accuracy_province_annotation",
    "coherence_vocab_adherence",
    "coherence_vocab_adherence_annotation",
    "coherence_status_vocab_adherence",
    "coherence_status_vocab_adherence_annotation",
    "coherence_capacity_nonnegative",
    "coherence_capacity_nonnegative_annotation",
    "coherence_row_atomicity",
    "coherence_row_atomicity_annotation",
    "coherence_capacity_plausible_for_level",
    "coherence_capacity_plausible_for_level_annotation",
    "coherence_level_consistent_with_name",
    "coherence_level_consistent_with_name_annotation",
    "provenance_source_presence",
    "provenance_source_presence_annotation",
    "provenance_high_conf_dual_source",
    "provenance_high_conf_dual_source_annotation",
    "provenance_source_diversity",
    "provenance_source_diversity_annotation",
    "provenance_source_spread",
    "provenance_source_spread_annotation",
    "temporality_asof_presence",
    "temporality_asof_presence_annotation",
    "temporality_plausible_range",
    "temporality_plausible_range_annotation",
    "temporality_cod_plausible",
    "temporality_cod_plausible_annotation",
    "field_completeness_core",
    "field_completeness_core_annotation",
    "field_completeness_capacity",
    "field_completeness_capacity_annotation",
]


@dataclass
class AccuracyScores:
    coverage: float | None
    precision: float | None
    f1: float | None
    fuel_accuracy: float | None
    status_accuracy: float | None
    province_accuracy: float | None
    annotation: str | None = None


@dataclass
class CoherenceScores:
    vocab_adherence: float | None
    status_vocab_adherence: float | None
    row_atomicity: float | None
    capacity_plausible_for_level: float | None = None
    capacity_plausible_for_level_annotation: str | None = None
    level_consistent_with_name: float | None = None
    level_consistent_with_name_annotation: str | None = None
    annotation: str | None = None


@dataclass
class VariabilityScores:
    """Run-level internal-coherence screen (ticket 0453).

    Counts distinct non-empty values in the capacity and status columns.
    The VETO flag signals a degenerate run: capacity has ≤4 distinct values
    OR status has ≤1 distinct value.

    Note: ``status_as_of`` variability is intentionally NOT a criterion.
    Strong models stamp the run date on every row (asof_distinct=1 is the
    norm for top performers such as claude-sonnet-4.6), so a variability
    requirement on status-as-of would produce false rejections.
    """

    capacity_distinct: int
    status_distinct: int
    veto: bool  # cap_distinct <= 4 OR status_distinct <= 1


@dataclass
class ProvenanceScores:
    source_presence: float | None
    source_presence_annotation: str | None
    high_conf_dual_source: float | None
    high_conf_dual_source_annotation: str | None


@dataclass
class TemporalityScores:
    asof_presence: float | None
    asof_presence_annotation: str | None
    plausible_range: float | None
    plausible_range_annotation: str | None


@dataclass
class FieldCompletenessScores:
    core_fields: float | None
    capacity_present: float | None
    annotation: str | None = None


def _fraction(num: int, den: int) -> float | None:
    if den <= 0:
        return None
    return round(num / den, 4)


def _first_nonempty(row: dict[str, str], keys: tuple[str, ...]) -> str:
    for key in keys:
        raw = row.get(key)
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    return ""


def _as_float(value: str) -> float | None:
    token = value.strip().replace(",", "")
    if not token:
        return None
    try:
        return float(token)
    except ValueError:
        return None


def _capacity_nonnegative(rows: list[dict[str, str]]) -> tuple[float | None, str | None]:
    if not rows:
        return None, "no_rows"

    seen = 0
    nonnegative = 0
    for row in rows:
        token = ""
        for key in _CAPACITY_KEYS:
            raw = row.get(key)
            if raw is not None and str(raw).strip():
                token = str(raw)
                break
        if not token:
            continue
        parsed = _as_float(token)
        if parsed is None:
            continue
        seen += 1
        if parsed >= 0:
            nonnegative += 1

    if seen == 0:
        return None, "column_missing"
    return round(nonnegative / seen, 4), None


def _pick_asof_cell(row: dict[str, str]) -> str:
    return _first_nonempty(row, ("status_as_of", "as_of", "date_as_of", "freshness_date"))


def score_source_diversity(rows: list[dict[str, str]]) -> tuple[float | None, str | None]:
    if not rows:
        return None, "no_rows"
    sources = {
        v.strip()
        for r in rows
        for v in [(r.get("source_1") or "").strip()]
        if v.strip().lower() not in _SOURCE_NOT_FOUND
    }
    if not sources:
        return 0.0, "column_empty"
    return round(min(len(sources) / _SOURCE_DIVERSITY_CLIP, 1.0), 4), None


def score_source_spread(rows: list[dict[str, str]]) -> tuple[float | None, str | None]:
    if not rows:
        return None, "no_rows"
    from collections import Counter

    vals = [
        v
        for r in rows
        for v in [(r.get("source_1") or "").strip()]
        if v.lower() not in _SOURCE_NOT_FOUND
    ]
    if not vals:
        return 0.0, "column_empty"
    top1_count = Counter(vals).most_common(1)[0][1]
    return round(1.0 - top1_count / len(vals), 4), None


def score_cod_plausible(rows: list[dict[str, str]]) -> tuple[float | None, str | None]:
    if not rows:
        return None, "no_rows"
    cod_vals = [(r.get("cod") or "").strip() for r in rows if (r.get("cod") or "").strip()]
    if not cod_vals:
        return None, "column_empty"
    if len(set(cod_vals)) <= 1:
        return 0.0, "all_identical"
    years = []
    for v in cod_vals:
        m = _YEAR_RE.search(v)
        if m:
            years.append(int(m.group(1)))
    plausible = sum(1 for y in years if 1960 <= y <= 2035)
    return round(plausible / len(cod_vals), 4), None


def score_variability(rows: list[dict[str, str]]) -> VariabilityScores:
    """Compute within-run capacity and status variability (ticket 0453).

    Returns distinct-value counts plus the run-level VETO flag.

    Spearman(cap_distinct, F1) ≈ 0.90 over Exp1 batch2 (70 runs).
    The VETO rule ``cap_distinct <= 4 OR status_distinct <= 1`` was
    calibrated in-sample on those 70 runs and is an existence proof,
    not a cross-validated detector.
    """
    if not rows:
        return VariabilityScores(capacity_distinct=0, status_distinct=0, veto=True)

    cap_vals: set[str] = set()
    for row in rows:
        for key in _CAPACITY_KEYS:
            v = (row.get(key) or "").strip()
            if v:
                cap_vals.add(v)
                break

    status_vals = {
        (row.get("status") or "").strip().lower()
        for row in rows
        if (row.get("status") or "").strip()
    }

    cap_distinct = len(cap_vals)
    status_distinct = len(status_vals)
    veto = cap_distinct <= 4 or status_distinct <= 1
    return VariabilityScores(
        capacity_distinct=cap_distinct,
        status_distinct=status_distinct,
        veto=veto,
    )


def model_reliability_grade(
    scored_runs: list[dict[str, str]],
) -> dict[str, dict[str, float | int | bool]]:
    """Aggregate run-level VETO flags to a model-level source-reliability grade.

    Implements the NATO STANAG 2511 Level-2 ("source reliability") grade from
    ticket 0453.  A model version that produces 5/5 incoherent runs is
    disqualified as a source altogether.

    Args:
        scored_runs: rows from exp1_cross_eval.csv, each containing
            ``model``, ``coherence_run_veto`` ("1"/"0"), and optionally
            ``prompt_version``.

    Returns:
        Dict keyed by ``(model, prompt_version)`` with fields:
        - ``n_total``: number of runs considered
        - ``n_vetoed``: runs where coherence_run_veto == "1"
        - ``veto_fraction``: n_vetoed / n_total
        - ``disqualified``: True if n_vetoed == n_total (5/5 rule)
    """
    from collections import defaultdict

    groups: dict[tuple[str, str], list[bool]] = defaultdict(list)
    for row in scored_runs:
        model = row.get("model", "")
        pv = row.get("prompt_version", "")
        veto = row.get("coherence_run_veto", "0") == "1"
        groups[(model, pv)].append(veto)

    result = {}
    for (model, pv), vetoes in groups.items():
        n_total = len(vetoes)
        n_vetoed = sum(vetoes)
        result[(model, pv)] = {
            "n_total": n_total,
            "n_vetoed": n_vetoed,
            "veto_fraction": round(n_vetoed / n_total, 4) if n_total > 0 else 0.0,
            "disqualified": n_vetoed == n_total and n_total > 0,
        }
    return result


def score_accuracy(rows: list[dict[str, str]], ref_path: Path | None) -> AccuracyScores:
    if not rows:
        return AccuracyScores(None, None, None, None, None, None, annotation="no_rows")
    if ref_path is None:
        return AccuracyScores(None, None, None, None, None, None, annotation="reference_missing")

    reference = load_plants_csv(ref_path)
    system = plants_from_dicts(rows)
    metrics = compute_metrics(reconcile(reference, system))
    return AccuracyScores(
        f1=metrics.f1,
        coverage=metrics.coverage,
        precision=metrics.precision,
        fuel_accuracy=metrics.fuel_accuracy,
        status_accuracy=metrics.status_accuracy,
        province_accuracy=metrics.province_accuracy,
        annotation=None,
    )


def score_coherence(rows: list[dict[str, str]]) -> CoherenceScores:
    # Local import to avoid a circular dependency:
    # score_coherence_level imports _ATOMICITY_VIOLATION_RE, _CAPACITY_KEYS,
    # and _as_float from this module at the top level.
    from .score_coherence_level import (
        score_capacity_plausible_for_level,
        score_level_consistent_with_name,
    )

    if not rows:
        return CoherenceScores(None, None, None, annotation="no_rows")

    valid_fuel = 0
    valid_status = 0
    atomic_rows = 0
    for row in rows:
        fuel = (row.get("fuel") or "").strip().lower()
        if fuel in _ALLOWED_FUELS:
            valid_fuel += 1

        status = (row.get("status") or "").strip().lower()
        if status in _ALLOWED_STATUSES:
            valid_status += 1

        name = (row.get("name") or "").strip()
        if not _ATOMICITY_VIOLATION_RE.search(name):
            atomic_rows += 1

    cap_plaus, cap_plaus_ann = score_capacity_plausible_for_level(rows)
    level_name, level_name_ann = score_level_consistent_with_name(rows)

    return CoherenceScores(
        vocab_adherence=_fraction(valid_fuel, len(rows)),
        status_vocab_adherence=_fraction(valid_status, len(rows)),
        row_atomicity=_fraction(atomic_rows, len(rows)),
        capacity_plausible_for_level=cap_plaus,
        capacity_plausible_for_level_annotation=cap_plaus_ann,
        level_consistent_with_name=level_name,
        level_consistent_with_name_annotation=level_name_ann,
        annotation=None,
    )


def score_provenance(rows: list[dict[str, str]]) -> ProvenanceScores:
    if not rows:
        return ProvenanceScores(None, "no_rows", None, "no_rows")

    with_sources = 0
    high_rows = 0
    high_rows_with_dual = 0
    has_confidence_column = any("confidence" in row for row in rows)

    for row in rows:
        source_1 = (row.get("source_1") or "").strip()
        source_2 = (row.get("source_2") or "").strip()
        if source_1 or source_2:
            with_sources += 1

        confidence = (row.get("confidence") or "").strip().upper()
        if confidence == "HIGH":
            high_rows += 1
            if source_1 and source_2:
                high_rows_with_dual += 1

    if not has_confidence_column:
        high_dual = None
        high_annotation = "column_missing"
    elif high_rows == 0:
        high_dual = None
        high_annotation = "no_high_confidence"
    else:
        high_dual = _fraction(high_rows_with_dual, high_rows)
        high_annotation = None

    return ProvenanceScores(
        source_presence=_fraction(with_sources, len(rows)),
        source_presence_annotation=None,
        high_conf_dual_source=high_dual,
        high_conf_dual_source_annotation=high_annotation,
    )


def score_temporality(rows: list[dict[str, str]]) -> TemporalityScores:
    if not rows:
        return TemporalityScores(None, "no_rows", None, "no_rows")

    asof_keys = ("status_as_of", "as_of", "date_as_of", "freshness_date")
    has_asof_column = any(any(k in row for k in asof_keys) for row in rows)
    if not has_asof_column:
        return TemporalityScores(None, "column_missing", None, "column_missing")

    with_asof = 0
    plausible = 0
    years_found: list[int] = []
    for row in rows:
        cell = _pick_asof_cell(row)
        if not cell:
            continue
        with_asof += 1
        match = _YEAR_RE.search(cell)
        if not match:
            continue
        year = int(match.group(1))
        years_found.append(year)
        if 1980 <= year <= 2100:
            plausible += 1

    if with_asof == 0:
        plausible_rate = None
        plausible_annotation = "column_empty"
    elif len(years_found) >= 2 and len(set(years_found)) == 1:
        # All cells carry the same year — likely the run date stamped on every row.
        plausible_rate = 0.0
        plausible_annotation = "all_identical"
    else:
        plausible_rate = _fraction(plausible, with_asof)
        plausible_annotation = None

    return TemporalityScores(
        asof_presence=_fraction(with_asof, len(rows)),
        asof_presence_annotation=None,
        plausible_range=plausible_rate,
        plausible_range_annotation=plausible_annotation,
    )


def score_field_completeness(rows: list[dict[str, str]]) -> FieldCompletenessScores:
    if not rows:
        return FieldCompletenessScores(None, None, annotation="no_rows")

    core_cols = ("name", "fuel", "status", "cod", "province")
    present_cells = 0
    capacity_present = 0
    for row in rows:
        for col in core_cols:
            if (row.get(col) or "").strip():
                present_cells += 1
        if _first_nonempty(row, _CAPACITY_KEYS):
            capacity_present += 1

    return FieldCompletenessScores(
        core_fields=_fraction(present_cells, len(rows) * len(core_cols)),
        capacity_present=_fraction(capacity_present, len(rows)),
        annotation=None,
    )


def _fmt(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.4f}"


def _append_row(csv_path: Path, row: dict[str, str]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not csv_path.exists()
    with csv_path.open("a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_CSV_COLUMNS)
        if needs_header:
            writer.writeheader()
        writer.writerow(row)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Compute mechanical scores for one Exp2 run")
    parser.add_argument("--arm", required=True, choices=["naive", "optimised", "arm3", "arm4"])
    parser.add_argument("--model", required=True)
    parser.add_argument("--run", required=True, type=int)
    parser.add_argument("--prompt-version", default="exp2")
    parser.add_argument("--reference", type=Path, default=VN_THERMAL_PLANTS_RELEASE_CSV)
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("experiments/derived/sota_cross_eval.csv"),
    )
    parser.add_argument(
        "--naive-dir",
        type=Path,
        default=Path("experiments/outputs/sota_exp2_naive_arm"),
    )
    parser.add_argument(
        "--optimised-dir",
        type=Path,
        default=Path("experiments/outputs/sota_exp2_brerun1"),
    )
    parser.add_argument(
        "--arm3-dir",
        type=Path,
        default=Path("experiments/derived/arm3_flat"),
    )
    parser.add_argument(
        "--arm4-dir",
        type=Path,
        default=Path("experiments/derived/arm4_flat"),
    )
    args = parser.parse_args(argv)

    locator = RunLocator(arm=args.arm, model=args.model, run=args.run)
    ingested = ingest_run(
        locator,
        naive_dir=args.naive_dir,
        optimised_dir=args.optimised_dir,
        arm3_dir=args.arm3_dir,
        arm4_dir=args.arm4_dir,
    )

    accuracy = score_accuracy(ingested.rows, ref_path=args.reference)
    coherence = score_coherence(ingested.rows)
    coherence_capacity, coherence_capacity_annotation = _capacity_nonnegative(ingested.rows)
    provenance = score_provenance(ingested.rows)
    temporality = score_temporality(ingested.rows)
    completeness = score_field_completeness(ingested.rows)
    src_div, src_div_ann = score_source_diversity(ingested.rows)
    src_spread, src_spread_ann = score_source_spread(ingested.rows)
    cod_plaus, cod_plaus_ann = score_cod_plausible(ingested.rows)

    out_row = {
        "arm": args.arm,
        "model": args.model,
        "run": str(args.run),
        "prompt_version": args.prompt_version,
        "reference": args.reference.name,
        "n_rows": str(len(ingested.rows)),
        "accuracy_coverage": _fmt(accuracy.coverage),
        "accuracy_coverage_annotation": accuracy.annotation or "",
        "accuracy_precision": _fmt(accuracy.precision),
        "accuracy_precision_annotation": accuracy.annotation or "",
        "accuracy_f1": _fmt(accuracy.f1),
        "accuracy_f1_annotation": accuracy.annotation or "",
        "accuracy_fuel": _fmt(accuracy.fuel_accuracy),
        "accuracy_fuel_annotation": accuracy.annotation or "",
        "accuracy_status": _fmt(accuracy.status_accuracy),
        "accuracy_status_annotation": accuracy.annotation or "",
        "accuracy_province": _fmt(accuracy.province_accuracy),
        "accuracy_province_annotation": accuracy.annotation or "",
        "coherence_vocab_adherence": _fmt(coherence.vocab_adherence),
        "coherence_vocab_adherence_annotation": coherence.annotation or "",
        "coherence_status_vocab_adherence": _fmt(coherence.status_vocab_adherence),
        "coherence_status_vocab_adherence_annotation": coherence.annotation or "",
        "coherence_capacity_nonnegative": _fmt(coherence_capacity),
        "coherence_capacity_nonnegative_annotation": coherence_capacity_annotation or "",
        "coherence_row_atomicity": _fmt(coherence.row_atomicity),
        "coherence_row_atomicity_annotation": coherence.annotation or "",
        "provenance_source_presence": _fmt(provenance.source_presence),
        "provenance_source_presence_annotation": provenance.source_presence_annotation or "",
        "provenance_high_conf_dual_source": _fmt(provenance.high_conf_dual_source),
        "provenance_high_conf_dual_source_annotation": (
            provenance.high_conf_dual_source_annotation or ""
        ),
        "provenance_source_diversity": _fmt(src_div),
        "provenance_source_diversity_annotation": src_div_ann or "",
        "provenance_source_spread": _fmt(src_spread),
        "provenance_source_spread_annotation": src_spread_ann or "",
        "temporality_asof_presence": _fmt(temporality.asof_presence),
        "temporality_asof_presence_annotation": temporality.asof_presence_annotation or "",
        "temporality_plausible_range": _fmt(temporality.plausible_range),
        "temporality_plausible_range_annotation": temporality.plausible_range_annotation or "",
        "temporality_cod_plausible": _fmt(cod_plaus),
        "temporality_cod_plausible_annotation": cod_plaus_ann or "",
        "field_completeness_core": _fmt(completeness.core_fields),
        "field_completeness_core_annotation": completeness.annotation or "",
        "field_completeness_capacity": _fmt(completeness.capacity_present),
        "field_completeness_capacity_annotation": completeness.annotation or "",
    }
    _append_row(args.output_csv, out_row)
    log.info("Appended one row to %s", args.output_csv)


if __name__ == "__main__":
    main()
