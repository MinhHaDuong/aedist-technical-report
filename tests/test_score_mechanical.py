"""Tests for mechanical scoring helpers."""

import pytest

from aedist.score_ingest import RunLocator, ingest_run
from aedist.score_mechanical import (
    _capacity_nonnegative,
    score_accuracy,
    score_cod_plausible,
    score_coherence,
    score_field_completeness,
    score_provenance,
    score_source_diversity,
    score_source_spread,
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


def test_capacity_nonnegative_all_valid() -> None:
    rows = [
        {"capacity_mwe": "600"},
        {"capacity_mwe": "1,200"},
    ]
    score, annotation = _capacity_nonnegative(rows)
    assert score == 1.0
    assert annotation is None


def test_capacity_nonnegative_flags_negative() -> None:
    rows = [
        {"capacity_mwe": "600"},
        {"capacity_mwe": "-50"},
    ]
    score, annotation = _capacity_nonnegative(rows)
    assert score == 0.5
    assert annotation is None


def test_capacity_nonnegative_ignores_unparseable_and_empty() -> None:
    rows = [
        {"capacity_mwe": "600"},
        {"capacity_mwe": "n/a"},  # unparseable -> not counted
        {"capacity_mwe": ""},  # empty -> skipped
    ]
    score, annotation = _capacity_nonnegative(rows)
    assert score == 1.0
    assert annotation is None


def test_capacity_nonnegative_no_rows() -> None:
    assert _capacity_nonnegative([]) == (None, "no_rows")


def test_capacity_nonnegative_column_missing() -> None:
    score, annotation = _capacity_nonnegative([{"name": "A"}, {"name": "B"}])
    assert score is None
    assert annotation == "column_missing"


def test_source_diversity_counts_distinct_sources() -> None:
    rows = [
        {"source_1": "Decision 1195/QD-TTg"},
        {"source_1": "EVN 2024"},
        {"source_1": "Decision 1195/QD-TTg"},  # duplicate
    ]
    score, annotation = score_source_diversity(rows)
    # 2 distinct sources / clip(20)
    assert score == round(2 / 20, 4)
    assert annotation is None


def test_source_diversity_ignores_not_found_sentinels() -> None:
    rows = [
        {"source_1": "Not found"},
        {"source_1": "N/A"},
        {"source_1": "unknown"},
        {"source_1": ""},
    ]
    score, annotation = score_source_diversity(rows)
    assert score == 0.0
    assert annotation == "column_empty"


def test_source_diversity_clips_at_one() -> None:
    rows = [{"source_1": f"src-{i}"} for i in range(50)]
    score, annotation = score_source_diversity(rows)
    assert score == 1.0
    assert annotation is None


def test_source_diversity_no_rows() -> None:
    assert score_source_diversity([]) == (None, "no_rows")


def test_source_spread_uniform_sources_high_spread() -> None:
    rows = [
        {"source_1": "A"},
        {"source_1": "B"},
        {"source_1": "C"},
        {"source_1": "D"},
    ]
    score, annotation = score_source_spread(rows)
    # most-common appears 1/4 of the time -> 1 - 0.25
    assert score == 0.75
    assert annotation is None


def test_source_spread_single_dominant_source_zero() -> None:
    rows = [{"source_1": "A"} for _ in range(5)]
    score, annotation = score_source_spread(rows)
    assert score == 0.0
    assert annotation is None


def test_source_spread_only_sentinels_is_column_empty() -> None:
    rows = [{"source_1": "not found"}, {"source_1": ""}]
    score, annotation = score_source_spread(rows)
    assert score == 0.0
    assert annotation == "column_empty"


def test_source_spread_no_rows() -> None:
    assert score_source_spread([]) == (None, "no_rows")


def test_cod_plausible_mixed_years() -> None:
    rows = [
        {"cod": "1983"},
        {"cod": "commissioned 2010"},
        {"cod": "1950"},  # parses, implausible (<1960)
        {"cod": "TBD"},  # no parseable year — counts toward denominator, not plausible
    ]
    score, annotation = score_cod_plausible(rows)
    # Denominator is len(cod_vals)=4 (all non-empty), not len(parsed years)=3:
    # 2 plausible (1983, 2010) of 4 -> 0.5. A `plausible/len(years)` bug would give 2/3.
    assert score == round(2 / 4, 4)
    assert annotation is None


def test_cod_plausible_all_identical_scores_zero() -> None:
    rows = [{"cod": "2024"}, {"cod": "2024"}, {"cod": "2024"}]
    score, annotation = score_cod_plausible(rows)
    assert score == 0.0
    assert annotation == "all_identical"


def test_cod_plausible_column_empty() -> None:
    score, annotation = score_cod_plausible([{"cod": ""}, {"name": "A"}])
    assert score is None
    assert annotation == "column_empty"


def test_cod_plausible_no_rows() -> None:
    assert score_cod_plausible([]) == (None, "no_rows")


def test_accuracy_no_rows() -> None:
    result = score_accuracy([], ref_path=None)
    assert result.f1 is None
    assert result.annotation == "no_rows"


def test_accuracy_reference_missing() -> None:
    rows = [{"name": "A", "fuel": "coal"}]
    result = score_accuracy(rows, ref_path=None)
    assert result.f1 is None
    assert result.annotation == "reference_missing"


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
