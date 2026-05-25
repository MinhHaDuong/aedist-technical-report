"""Score Exp1 flat CSV outputs across quality axes.

Reads canonical CSV outputs from Exp1 batch runs, computes quality metrics
using score_mechanical helpers, and appends one row per run to a cross-eval CSV.
"""

import argparse
import csv
import logging
import re
from pathlib import Path

from .evaluate import _DEFAULT_REF
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

_CSV_COLUMNS = [
    "arm",
    "model",
    "run",
    "prompt_version",
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
    "temporality_asof_presence",
    "temporality_asof_presence_annotation",
    "temporality_plausible_range",
    "temporality_plausible_range_annotation",
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

    return {
        "arm": "parametric",
        "model": model,
        "run": str(run),
        "prompt_version": prompt_version,
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
        "temporality_asof_presence": _fmt(temporality.asof_presence),
        "temporality_asof_presence_annotation": temporality.asof_presence_annotation or "",
        "temporality_plausible_range": _fmt(temporality.plausible_range),
        "temporality_plausible_range_annotation": temporality.plausible_range_annotation or "",
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
    parser.add_argument("--reference", type=Path, default=_DEFAULT_REF)
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
