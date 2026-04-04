"""Tests for aedist.migrate_to_measurements — sweep result migration."""

import json

from aedist.migrate_to_measurements import migrate_query_json, migrate_sweep
from aedist.schema import Method, RunRecord


def _make_query_json(tmp_path, name="model-a-run1.json", **overrides):
    """Create a minimal query output JSON and return its path."""
    record = {
        "model": "openai/gpt-4o",
        "date": "2026-03-15",
        "run": 1,
        "prompt": "List all thermal power plants...",
        "response": "name,fuel,status\nPlant A,coal,operational",
        "finish_reason": "stop",
        "usage": {"prompt_tokens": 100, "completion_tokens": 200},
        "wall_seconds": 5.3,
        "cost_usd": 0.0012,
        "model_metadata": {"size_class": "large", "provider": "openai"},
    }
    record.update(overrides)
    path = tmp_path / name
    path.write_text(json.dumps(record))
    return path


def _make_metrics_json(tmp_path):
    """Create a minimal all_metrics.json and return its path."""
    metrics = [
        {
            "label": "sweep1_census/model-a-run1",
            "coverage": 0.85,
            "precision": 0.90,
            "f1": 0.87,
            "n_reference": 163,
            "n_system": 140,
            "n_matched": 130,
            "n_exact": 100,
            "n_fuzzy": 30,
            "n_missed": 33,
            "n_hallucinated": 10,
        }
    ]
    path = tmp_path / "all_metrics.json"
    path.write_text(json.dumps(metrics))
    return path


class TestMigrateQueryJson:
    def test_basic_conversion(self, tmp_path):
        json_path = _make_query_json(tmp_path)
        rec = migrate_query_json(json_path, Method.SINGLE, "sweep1_census")

        assert isinstance(rec, RunRecord)
        assert rec.method == Method.SINGLE
        assert rec.method_params.model == "openai/gpt-4o"
        assert rec.method_params.prompt_version == "sweep1_census"
        assert rec.resource_use.wall_s == 5.3
        assert rec.resource_use.cost_usd == 0.0012
        assert rec.resource_use.tokens_in == 100
        assert rec.resource_use.tokens_out == 200
        assert rec.result_summary.status == "ok"

    def test_with_metrics(self, tmp_path):
        json_path = _make_query_json(tmp_path)
        metrics_path = _make_metrics_json(tmp_path)
        from aedist.migrate_to_measurements import _load_metrics_index
        index = _load_metrics_index(metrics_path)

        rec = migrate_query_json(json_path, Method.SINGLE, "sweep1_census", index)
        assert rec.result_summary.f1 == 0.87
        assert rec.result_summary.tp == 130
        assert rec.result_summary.fp == 10
        assert rec.result_summary.fn == 33
        assert rec.result_summary.n_plants == 140

    def test_empty_response(self, tmp_path):
        json_path = _make_query_json(tmp_path, response="")
        rec = migrate_query_json(json_path, Method.SINGLE, "sweep1_census")
        assert rec.result_summary.status == "empty"

    def test_model_metadata_preserved(self, tmp_path):
        json_path = _make_query_json(tmp_path)
        rec = migrate_query_json(json_path, Method.SINGLE, "sweep1_census")
        assert rec.method_params.extra == {"size_class": "large", "provider": "openai"}

    def test_result_file_recorded(self, tmp_path):
        json_path = _make_query_json(tmp_path)
        rec = migrate_query_json(json_path, Method.SINGLE, "sweep1_census")
        assert rec.result_file == str(json_path)


class TestMigrateSweep:
    def test_migrates_all_files(self, tmp_path):
        for i in range(3):
            _make_query_json(tmp_path, name=f"model-a-run{i+1}.json", run=i + 1)
        records = migrate_sweep(tmp_path, Method.SINGLE, "sweep1_census")
        assert len(records) == 3

    def test_skips_bad_files(self, tmp_path):
        _make_query_json(tmp_path)
        (tmp_path / "bad-run1.json").write_text("not valid json {{{")
        records = migrate_sweep(tmp_path, Method.SINGLE, "sweep1_census")
        assert len(records) == 1

    def test_ignores_non_run_json(self, tmp_path):
        _make_query_json(tmp_path)
        (tmp_path / "manifest.json").write_text("{}")
        records = migrate_sweep(tmp_path, Method.SINGLE, "sweep1_census")
        assert len(records) == 1

    def test_round_trip(self, tmp_path):
        _make_query_json(tmp_path)
        records = migrate_sweep(tmp_path, Method.SINGLE, "sweep1_census")
        out = tmp_path / "measurements.jsonl"
        RunRecord.save_jsonl(records, out)
        loaded = RunRecord.load_jsonl(out)
        assert len(loaded) == 1
        assert loaded[0].method == Method.SINGLE
        assert loaded[0].method_params.model == "openai/gpt-4o"
