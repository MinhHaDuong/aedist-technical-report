"""Tests for mechanical scoring helpers."""

import pytest

from aedist.score_ingest import RunLocator, ingest_run
from aedist.score_mechanical import (
    score_coherence,
    score_field_completeness,
    score_provenance,
    score_temporality,
)


def test_coal_and_ccgt_lowers_vocab_adherence() -> None:
    rows = [
        {"name": "A", "fuel": "coal", "capacity_mwe": "600"},
        {"name": "B", "fuel": "CCGT", "capacity_mwe": "450"},
    ]
    result = score_coherence(rows)
    assert result.vocab_adherence == 0.5


def test_status_vocab_adherence_rejects_noncanonical() -> None:
    rows = [
        {"name": "A", "fuel": "coal", "status": "Operating"},
        {"name": "B", "fuel": "coal", "status": "Under Constr."},
    ]
    result = score_coherence(rows)
    assert result.status_vocab_adherence == 0.5


def test_high_confidence_missing_source2_lowers_dual_source_metric() -> None:
    rows = [
        {
            "name": "A",
            "source_1": "Decision 1195/QD-TTg",
            "source_2": "",
            "confidence": "HIGH",
        }
    ]
    result = score_provenance(rows)
    assert result.high_conf_dual_source == 0.0


def test_temporality_1979_fails_and_1980_passes_plausible_range() -> None:
    rows = [
        {"name": "A", "status_as_of": "as-of 1979"},
        {"name": "B", "status_as_of": "as-of 1980"},
    ]
    result = score_temporality(rows)
    assert result.plausible_range == 0.5


def test_temporality_all_identical_years_scores_zero() -> None:
    rows = [
        {"name": "A", "status_as_of": "as-of 2025"},
        {"name": "B", "status_as_of": "2025"},
        {"name": "C", "status_as_of": "checked 2025"},
    ]
    result = score_temporality(rows)
    assert result.plausible_range == 0.0
    assert result.plausible_range_annotation == "all_identical"


def test_empty_total_mwe_counted_absent() -> None:
    rows = [{"name": "A", "fuel": "coal", "total_mwe": ""}]
    result = score_field_completeness(rows)
    assert result.capacity_present == 0.0


def test_empty_table_has_no_division_by_zero() -> None:
    assert score_coherence([]).annotation == "no_rows"
    assert score_provenance([]).source_presence_annotation == "no_rows"
    assert score_provenance([]).high_conf_dual_source_annotation == "no_rows"
    assert score_temporality([]).asof_presence_annotation == "no_rows"
    assert score_temporality([]).plausible_range_annotation == "no_rows"
    assert score_field_completeness([]).annotation == "no_rows"


def _write_json(path, payload) -> None:
    import json

    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_md(path, content) -> None:
    path.write_text(content, encoding="utf-8")


def test_ingested_rows_mark_confidence_metric_no_high_confidence(tmp_path) -> None:
    naive_dir = tmp_path / "naive"
    optimised_dir = tmp_path / "optimised"
    naive_dir.mkdir()
    optimised_dir.mkdir()

    _write_json(naive_dir / "openai_run01.json", {"model": "gpt-5.5", "run": 1})
    _write_md(
        naive_dir / "openai_run01.md",
        "| Name | Fuel | Capacity | Status | COD | Province | Source 1 | Source 2 |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
        "| Pha Lai | Coal | 440 | Operating | 1983 | Hai Duong | EVN report | MOIT |\n",
    )

    ingested = ingest_run(
        RunLocator(arm="naive", model="gpt-5.5", run=1),
        naive_dir=naive_dir,
        optimised_dir=optimised_dir,
    )
    result = score_provenance(ingested.rows)

    assert result.source_presence == 1.0
    assert result.source_presence_annotation is None
    assert result.high_conf_dual_source is None
    assert result.high_conf_dual_source_annotation == "no_high_confidence"


def test_ingested_rows_mark_temporality_metrics_column_missing(tmp_path) -> None:
    naive_dir = tmp_path / "naive"
    optimised_dir = tmp_path / "optimised"
    naive_dir.mkdir()
    optimised_dir.mkdir()

    _write_json(naive_dir / "openai_run01.json", {"model": "gpt-5.5", "run": 1})
    _write_md(
        naive_dir / "openai_run01.md",
        "| Name | Fuel | Capacity | Status | COD | Province |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| Pha Lai | Coal | 440 | Operating | 1983 | Hai Duong |\n",
    )

    ingested = ingest_run(
        RunLocator(arm="naive", model="gpt-5.5", run=1),
        naive_dir=naive_dir,
        optimised_dir=optimised_dir,
    )
    result = score_temporality(ingested.rows)

    assert result.asof_presence == 0.0
    assert result.asof_presence_annotation is None
    assert result.plausible_range is None
    assert result.plausible_range_annotation == "column_empty"


def test_ingested_rows_compute_high_conf_dual_source_when_present(tmp_path) -> None:
    naive_dir = tmp_path / "naive"
    optimised_dir = tmp_path / "optimised"
    naive_dir.mkdir()
    optimised_dir.mkdir()

    _write_json(naive_dir / "openai_run01.json", {"model": "gpt-5.5", "run": 1})
    _write_md(
        naive_dir / "openai_run01.md",
        "| Name | Fuel | Capacity | Status | Status as-of-date | COD | Province | Confidence | Source 1 | Source 2 |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
        "| Pha Lai | Coal | 440 | Operating | 2024 est. | 1983 | Hai Duong | HIGH | EVN report | MOIT |\n",
    )

    ingested = ingest_run(
        RunLocator(arm="naive", model="gpt-5.5", run=1),
        naive_dir=naive_dir,
        optimised_dir=optimised_dir,
    )
    prov = score_provenance(ingested.rows)
    temp = score_temporality(ingested.rows)

    assert prov.high_conf_dual_source == 1.0
    assert prov.high_conf_dual_source_annotation is None
    assert temp.asof_presence == 1.0
    assert temp.asof_presence_annotation is None
    assert temp.plausible_range == 1.0
    assert temp.plausible_range_annotation is None


@pytest.mark.adherence
def test_score_mechanical_columns_match_sota_cross_eval_header() -> None:
    import csv
    from pathlib import Path

    from aedist.score_mechanical import _CSV_COLUMNS

    csv_path = Path(__file__).parent.parent / "experiments" / "derived" / "sota_cross_eval.csv"
    with csv_path.open(newline="", encoding="utf-8") as fh:
        header = next(csv.reader(fh))
    assert header == _CSV_COLUMNS, (
        f"_CSV_COLUMNS in score_mechanical.py does not match sota_cross_eval.csv header.\n"
        f"Scorer has: {_CSV_COLUMNS}\nCSV has: {header}"
    )
