"""Tests for mechanical scoring helpers."""

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
    assert score_provenance([]).annotation == "no_rows"
    assert score_temporality([]).annotation == "no_rows"
    assert score_field_completeness([]).annotation == "no_rows"
