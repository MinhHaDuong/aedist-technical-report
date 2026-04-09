"""Tests for RunRecord schema and JSONL round-trip."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from aedist.schema import (
    Method,
    MethodParams,
    ResourceUse,
    ResultSummary,
    RunRecord,
)


def _make_record(**overrides) -> RunRecord:
    """Build a RunRecord with sensible defaults, overridden by kwargs."""
    defaults = dict(
        run_id="abc123def456",
        timestamp=datetime(2026, 4, 4, 12, 0, 0, tzinfo=UTC),
        method=Method.SINGLE,
        method_params=MethodParams(
            model="openai/gpt-4o",
            temperature=0.0,
            max_tokens=4096,
            prompt_version="census_v1",
        ),
        resource_use=ResourceUse(
            wall_s=12.5,
            cost_usd=0.03,
            tokens_in=1500,
            tokens_out=3200,
        ),
        result_file="experiments/outputs/census/gpt-4o-run1.json",
        result_summary=ResultSummary(
            status="ok",
            n_plants=120,
            tp=100,
            fp=20,
            fn=64,
            f1=0.704,
        ),
        justification={"source": "self-reported"},
    )
    defaults.update(overrides)
    return RunRecord(**defaults)


class TestRunRecordConstruction:
    def test_all_fields_set(self):
        r = _make_record()
        assert r.run_id == "abc123def456"
        assert r.method == Method.SINGLE
        assert r.method_params.model == "openai/gpt-4o"
        assert r.resource_use.wall_s == 12.5
        assert r.result_summary.f1 == pytest.approx(0.704)

    def test_defaults(self):
        r = RunRecord(
            method=Method.RAG,
            method_params=MethodParams(model="anthropic/claude-sonnet-4-20250514"),
        )
        assert len(r.run_id) == 12
        assert r.run_id.isalnum()  # hex chars only, not arbitrary
        assert r.resource_use.wall_s is None
        assert r.result_summary.status == "ok"
        assert r.justification is None

    def test_method_enum_values(self):
        for m in ("single", "multiturn", "rag", "web"):
            r = RunRecord(
                method=m,
                method_params=MethodParams(model="test/model"),
            )
            assert r.method == m

    def test_invalid_method_rejected(self):
        with pytest.raises(ValidationError):
            RunRecord(
                method="invalid",
                method_params=MethodParams(model="test/model"),
            )


class TestRoundTrip:
    def test_jsonl_line_round_trip(self):
        original = _make_record()
        line = original.to_jsonl_line()
        restored = RunRecord.from_jsonl_line(line)
        assert restored == original

    def test_jsonl_line_is_single_line(self):
        line = _make_record().to_jsonl_line()
        assert "\n" not in line

    def test_round_trip_with_none_fields(self):
        original = RunRecord(
            method=Method.WEB,
            method_params=MethodParams(model="google/gemini-2.0-flash"),
        )
        restored = RunRecord.from_jsonl_line(original.to_jsonl_line())
        assert restored == original

    def test_round_trip_with_extra_params(self):
        original = _make_record(
            method_params=MethodParams(
                model="meta/llama-3-70b",
                extra={"top_k": 40, "repetition_penalty": 1.1},
            ),
        )
        restored = RunRecord.from_jsonl_line(original.to_jsonl_line())
        assert restored.method_params.extra["top_k"] == 40


class TestJsonlFile:
    def test_save_and_load(self, tmp_path: Path):
        records = [
            _make_record(run_id="run_001"),
            _make_record(run_id="run_002", method=Method.MULTITURN),
            _make_record(run_id="run_003", method=Method.RAG),
        ]
        path = tmp_path / "measurements.jsonl"
        RunRecord.save_jsonl(records, path)
        loaded = RunRecord.load_jsonl(path)
        assert loaded == records

    def test_load_skips_blank_lines(self, tmp_path: Path):
        path = tmp_path / "sparse.jsonl"
        r = _make_record()
        with open(path, "w") as f:
            f.write(r.to_jsonl_line() + "\n")
            f.write("\n")
            f.write(r.to_jsonl_line() + "\n")
        loaded = RunRecord.load_jsonl(path)
        assert len(loaded) == 2
