"""Score Exp1 flat CSV outputs across quality axes.

Pipeline phase: P2 (score & consolidate) — invoked by experiments/derived/score.mk.

Reads canonical CSV outputs from Exp1 batch runs, computes quality metrics
using score_mechanical helpers, and appends one row per run to a cross-eval CSV.
"""

import argparse
import csv
import logging
import re
from pathlib import Path

from .config import VN_THERMAL_PLANTS_RELEASE_CSV
from .score_mechanical import (
    score_accuracy,
    score_coherence,
    score_field_completeness,
    score_provenance,
    score_temporality,
)

log = logging.getLogger(__name__)

_FILENAME_RE = re.compile(r"^(?P<model>.+)-run(?P<run>\d+)\.csv$")
_CAPACITY_KEYS = ("capacity_mwe", "total_mwe", "total_mw", "capacity")
_SOURCE_DIVERSITY_CLIP = 20
_SOURCE_NOT_FOUND = frozenset({"not found", "n/a", "unknown", ""})
_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")

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
    "coherence_capacity_nonnegative",
    "coherence_capacity_nonnegative_annotation",
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


def _fmt(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.4f}"


def _parse_model_run(path: Path) -> tuple[str, int]:
    match = _FILENAME_RE.match(path.name)
    if not match:
        raise ValueError(f"unsupported filename format: {path.name}")
    return match.group("model"), int(match.group("run"))


def _load_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _as_float(token: str) -> float | None:
    value = token.strip().replace(",", "")
    if not value:
        return None
    try:
        return float(value)
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


def _source_diversity(rows: list[dict[str, str]]) -> tuple[float | None, str | None]:
    if not rows:
        return None, "no_rows"
    sources = {
        v
        for r in rows
        for v in [(r.get("source_1") or "").strip()]
        if v.lower() not in _SOURCE_NOT_FOUND
    }
    if not sources:
        return 0.0, "column_empty"
    return round(min(len(sources) / _SOURCE_DIVERSITY_CLIP, 1.0), 4), None


def _source_spread(rows: list[dict[str, str]]) -> tuple[float | None, str | None]:
    if not rows:
        return None, "no_rows"
    vals = [
        v
        for r in rows
        for v in [(r.get("source_1") or "").strip()]
        if v.lower() not in _SOURCE_NOT_FOUND
    ]
    if not vals:
        return 0.0, "column_empty"
    from collections import Counter

    top1_count = Counter(vals).most_common(1)[0][1]
    return round(1.0 - top1_count / len(vals), 4), None


def _cod_plausible(rows: list[dict[str, str]]) -> tuple[float | None, str | None]:
    if not rows:
        return None, "no_rows"
    cod_vals: list[str] = []
    years: list[int] = []
    for r in rows:
        cell = (r.get("cod") or "").strip()
        if not cell:
            continue
        cod_vals.append(cell)
        m = _YEAR_RE.search(cell)
        if m:
            years.append(int(m.group(1)))
    if not cod_vals:
        return None, "column_empty"
    if len(set(cod_vals)) <= 1:
        return 0.0, "all_identical"
    plausible = sum(1 for y in years if 1960 <= y <= 2035)
    return round(plausible / len(cod_vals), 4), None


def _append_rows(csv_path: Path, rows: list[dict[str, str]]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_CSV_COLUMNS)
        if needs_header:
            writer.writeheader()
        writer.writerows(rows)


def score_file(csv_path: Path, reference: Path, prompt_version: str) -> dict[str, str]:
    model, run = _parse_model_run(csv_path)
    rows = _load_rows(csv_path)

    accuracy = score_accuracy(rows, ref_path=reference)
    coherence = score_coherence(rows)
    provenance = score_provenance(rows)
    temporality = score_temporality(rows)
    completeness = score_field_completeness(rows)
    coherence_capacity, coherence_capacity_annotation = _capacity_nonnegative(rows)
    src_div, src_div_ann = _source_diversity(rows)
    src_spread, src_spread_ann = _source_spread(rows)
    cod_plaus, cod_plaus_ann = _cod_plausible(rows)

    return {
        "arm": "parametric",
        "model": model,
        "run": str(run),
        "prompt_version": prompt_version,
        "reference": reference.name,
        "n_rows": str(len(rows)),
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
        "coherence_capacity_nonnegative": _fmt(coherence_capacity),
        "coherence_capacity_nonnegative_annotation": coherence_capacity_annotation or "",
        "provenance_source_presence": _fmt(provenance.source_presence),
        "provenance_source_presence_annotation": provenance.source_presence_annotation or "",
        "provenance_high_conf_dual_source": _fmt(provenance.high_conf_dual_source),
        "provenance_high_conf_dual_source_annotation": provenance.high_conf_dual_source_annotation
        or "",
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


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Score Exp1 CSV runs on quality axes")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("experiments/outputs/exp1_batch2"),
        help="Directory containing {model}-run{N}.csv files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("experiments/derived/exp1_cross_eval.csv"),
        help="CSV to append one scored row per run",
    )
    parser.add_argument("--reference", type=Path, default=VN_THERMAL_PLANTS_RELEASE_CSV)
    parser.add_argument("--prompt-version", default="exp1")
    args = parser.parse_args(argv)

    files = sorted(args.input_dir.glob("*.csv"))
    if not files:
        raise SystemExit(f"no CSV files found under {args.input_dir}")

    out_rows: list[dict[str, str]] = []
    for csv_path in files:
        model, run = _parse_model_run(csv_path)
        row = score_file(csv_path, args.reference, args.prompt_version)
        out_rows.append(row)
        log.info("scored %s run=%d", model, run)

    _append_rows(args.output, out_rows)
    log.info("appended %d rows to %s", len(out_rows), args.output)


if __name__ == "__main__":
    main()
