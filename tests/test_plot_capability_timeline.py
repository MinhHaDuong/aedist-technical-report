"""Tests for aedist.plot_capability_timeline.bucket_by_stage."""

from datetime import date

from aedist.plot_capability_timeline import bucket_by_stage


def test_shipped_rows_grouped_by_stage() -> None:
    rows = [
        {"stage": "1", "lab": "OpenAI", "date": "2022-11-30", "source_kind": ""},
        {"stage": "1", "lab": "Anthropic", "date": "2023-03-14", "source_kind": ""},
        {"stage": "5", "lab": "OpenAI", "date": "2024-09-12", "source_kind": ""},
    ]
    by_stage, missing = bucket_by_stage(rows)
    assert by_stage[1] == [("OpenAI", date(2022, 11, 30)), ("Anthropic", date(2023, 3, 14))]
    assert by_stage[5] == [("OpenAI", date(2024, 9, 12))]
    assert missing == {}


def test_blank_date_recorded_as_missing_with_source_kind() -> None:
    rows = [
        {"stage": "8", "lab": "Mistral", "date": "  ", "source_kind": "absent"},
        {"stage": "8", "lab": "Alibaba", "date": "", "source_kind": ""},  # defaults to TBD
    ]
    by_stage, missing = bucket_by_stage(rows)
    assert by_stage == {}
    assert missing[8]["absent"] == ["Mistral"]
    assert missing[8]["TBD"] == ["Alibaba"]


def test_unparseable_date_is_skipped() -> None:
    rows = [{"stage": "2", "lab": "OpenAI", "date": "soon", "source_kind": ""}]
    by_stage, missing = bucket_by_stage(rows)
    assert by_stage == {}
    assert missing == {}
