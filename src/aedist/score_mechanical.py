"""Mechanical scoring helpers for Exp2 outputs.

Consumes canonical rows (from score_ingest), computes five scoring dimensions,
and appends one row to experiments/derived/sota_cross_eval.csv.
"""

import argparse
import csv
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from .evaluate import _DEFAULT_REF, load_plants_csv, plants_from_dicts
from .metrics import compute_metrics
from .reconcile import reconcile
from .score_ingest import RunLocator, ingest_run

log = logging.getLogger(__name__)

_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2}|2100)\b")
_CAPACITY_KEYS = ("capacity_mwe", "total_mwe", "total_mw", "capacity")

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

_CSV_COLUMNS = [
    "arm",
    "model",
    "run",
    "prompt_version",
    "n_rows",
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
    "coherence_capacity_nonnegative",
    "coherence_capacity_nonnegative_annotation",
    "provenance_source_presence",
    "provenance_source_presence_annotation",
    "provenance_high_conf_dual_source",
    "provenance_high_conf_dual_source_annotation",
    "temporality_asof_presence",
    "temporality_asof_presence_annotation",
    "temporality_plausible_range",
    "temporality_plausible_range_annotation",
    "field_completeness_core",
    "field_completeness_core_annotation",
    "field_completeness_capacity",
    "field_completeness_capacity_annotation",
]


@dataclass
class AccuracyScores:
    f1: float | None
    fuel_accuracy: float | None
    status_accuracy: float | None
    province_accuracy: float | None
    annotation: str | None = None


@dataclass
class CoherenceScores:
    vocab_adherence: float | None
    capacity_nonnegative: float | None
    annotation: str | None = None


@dataclass
class ProvenanceScores:
    source_presence: float | None
    high_conf_dual_source: float | None
    annotation: str | None = None


@dataclass
class TemporalityScores:
    asof_presence: float | None
    plausible_range: float | None
    annotation: str | None = None


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


def _pick_asof_cell(row: dict[str, str]) -> str:
    return _first_nonempty(row, ("status_as_of", "as_of", "date_as_of", "freshness_date"))


def score_accuracy(rows: list[dict[str, str]], ref_path: Path | None) -> AccuracyScores:
    if not rows:
        return AccuracyScores(None, None, None, None, annotation="no_rows")
    if ref_path is None:
        return AccuracyScores(None, None, None, None, annotation="reference_missing")

    reference = load_plants_csv(ref_path)
    system = plants_from_dicts(rows)
    metrics = compute_metrics(reconcile(reference, system))
    return AccuracyScores(
        f1=metrics.f1,
        fuel_accuracy=metrics.fuel_accuracy,
        status_accuracy=metrics.status_accuracy,
        province_accuracy=metrics.province_accuracy,
        annotation=None,
    )


def score_coherence(rows: list[dict[str, str]]) -> CoherenceScores:
    if not rows:
        return CoherenceScores(None, None, annotation="no_rows")

    valid_vocab = 0
    nonnegative = 0
    for row in rows:
        fuel = (row.get("fuel") or "").strip().lower()
        if fuel in _ALLOWED_FUELS:
            valid_vocab += 1

        cap = _as_float(_first_nonempty(row, _CAPACITY_KEYS))
        if cap is not None and cap >= 0:
            nonnegative += 1

    return CoherenceScores(
        vocab_adherence=_fraction(valid_vocab, len(rows)),
        capacity_nonnegative=_fraction(nonnegative, len(rows)),
        annotation=None,
    )


def score_provenance(rows: list[dict[str, str]]) -> ProvenanceScores:
    if not rows:
        return ProvenanceScores(None, None, annotation="no_rows")

    with_sources = 0
    high_rows = 0
    high_rows_with_dual = 0

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

    high_dual = _fraction(high_rows_with_dual, high_rows)
    if high_rows == 0:
        annotation = "column_missing_or_no_high_confidence"
    else:
        annotation = None

    return ProvenanceScores(
        source_presence=_fraction(with_sources, len(rows)),
        high_conf_dual_source=high_dual,
        annotation=annotation,
    )


def score_temporality(rows: list[dict[str, str]]) -> TemporalityScores:
    if not rows:
        return TemporalityScores(None, None, annotation="no_rows")

    with_asof = 0
    plausible = 0
    for row in rows:
        cell = _pick_asof_cell(row)
        if not cell:
            continue
        with_asof += 1
        match = _YEAR_RE.search(cell)
        if not match:
            continue
        year = int(match.group(1))
        if 1980 <= year <= 2100:
            plausible += 1

    plausible_rate = _fraction(plausible, with_asof)
    if with_asof == 0:
        annotation = "column_missing_or_empty"
    else:
        annotation = None

    return TemporalityScores(
        asof_presence=_fraction(with_asof, len(rows)),
        plausible_range=plausible_rate,
        annotation=annotation,
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
    parser.add_argument("--arm", required=True, choices=["naive", "optimised"])
    parser.add_argument("--model", required=True)
    parser.add_argument("--run", required=True, type=int)
    parser.add_argument("--prompt-version", default="exp2")
    parser.add_argument("--reference", type=Path, default=_DEFAULT_REF)
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
    args = parser.parse_args(argv)

    locator = RunLocator(arm=args.arm, model=args.model, run=args.run)
    ingested = ingest_run(locator, naive_dir=args.naive_dir, optimised_dir=args.optimised_dir)

    accuracy = score_accuracy(ingested.rows, ref_path=args.reference)
    coherence = score_coherence(ingested.rows)
    provenance = score_provenance(ingested.rows)
    temporality = score_temporality(ingested.rows)
    completeness = score_field_completeness(ingested.rows)

    out_row = {
        "arm": args.arm,
        "model": args.model,
        "run": str(args.run),
        "prompt_version": args.prompt_version,
        "n_rows": str(len(ingested.rows)),
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
        "coherence_capacity_nonnegative": _fmt(coherence.capacity_nonnegative),
        "coherence_capacity_nonnegative_annotation": coherence.annotation or "",
        "provenance_source_presence": _fmt(provenance.source_presence),
        "provenance_source_presence_annotation": provenance.annotation or "",
        "provenance_high_conf_dual_source": _fmt(provenance.high_conf_dual_source),
        "provenance_high_conf_dual_source_annotation": provenance.annotation or "",
        "temporality_asof_presence": _fmt(temporality.asof_presence),
        "temporality_asof_presence_annotation": temporality.annotation or "",
        "temporality_plausible_range": _fmt(temporality.plausible_range),
        "temporality_plausible_range_annotation": temporality.annotation or "",
        "field_completeness_core": _fmt(completeness.core_fields),
        "field_completeness_core_annotation": completeness.annotation or "",
        "field_completeness_capacity": _fmt(completeness.capacity_present),
        "field_completeness_capacity_annotation": completeness.annotation or "",
    }
    _append_row(args.output_csv, out_row)
    log.info("Appended one row to %s", args.output_csv)


if __name__ == "__main__":
    main()
