"""Tests for mechanical scoring helpers."""

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


def test_ingested_rows_mark_confidence_metric_column_missing(tmp_path) -> None:
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
    assert result.high_conf_dual_source_annotation == "column_missing"


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

    assert result.asof_presence is None
    assert result.asof_presence_annotation == "column_missing"
    assert result.plausible_range is None
    assert result.plausible_range_annotation == "column_missing"
