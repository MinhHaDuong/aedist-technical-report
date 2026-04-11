"""Tests for _classify_orphan and cmd_assemble in aedist.evaluate."""

from aedist.evaluate import _classify_orphan


class TestClassifyOrphan:
    """Classify JSON-only results (no CSV companion) by status."""

    def test_prose_only_is_refusal(self):
        raw = {"model": "test", "response": "I am unable to provide this information."}
        assert _classify_orphan(raw) == "refusal"

    def test_pipe_table_is_error(self):
        raw = {
            "model": "test",
            "response": "Here is the data:\n\n| Name | Fuel |\n|---|---|\n| Pha Lai | Coal |\n",
        }
        assert _classify_orphan(raw) == "error"

    def test_fenced_csv_is_error(self):
        raw = {
            "model": "test",
            "response": "```csv\nName,Fuel\nPha Lai,Coal\n```",
        }
        assert _classify_orphan(raw) == "error"

    def test_empty_response_is_empty(self):
        raw = {"model": "test", "response": ""}
        assert _classify_orphan(raw) == "empty"

    def test_missing_response_is_empty(self):
        raw = {"model": "test"}
        assert _classify_orphan(raw) == "empty"

    def test_whitespace_only_is_empty(self):
        raw = {"model": "test", "response": "   \n  "}
        assert _classify_orphan(raw) == "empty"

    def test_multiturn_prose_is_refusal(self):
        raw = {
            "model": "test",
            "turns": [
                {"role": "user", "content": "List thermal plants"},
                {"role": "assistant", "content": "I'm sorry, I cannot produce that table."},
            ],
        }
        assert _classify_orphan(raw) == "refusal"

    def test_multiturn_with_table_is_error(self):
        raw = {
            "model": "test",
            "turns": [
                {"role": "user", "content": "List thermal plants"},
                {"role": "assistant", "content": "| Name | Fuel |\n|---|---|\n| Pha Lai | Coal |"},
            ],
        }
        assert _classify_orphan(raw) == "error"

    def test_multiturn_empty_assistant_is_empty(self):
        raw = {
            "model": "test",
            "turns": [
                {"role": "user", "content": "List thermal plants"},
                {"role": "assistant", "content": ""},
            ],
        }
        assert _classify_orphan(raw) == "empty"

    def test_inline_csv_without_fencing_is_refusal(self):
        """Inline CSV (no fenced block or pipe table) is treated as refusal.

        The fallback_extract_inline_csv heuristic is too aggressive for
        classification — comma-separated phrases in refusal prose trigger
        false positives, so we only use strong table signals.
        """
        raw = {
            "model": "test",
            "response": "Name,Fuel,Status\nPha Lai,Coal,Operating\nUong Bi,Coal,Operating\n",
        }
        assert _classify_orphan(raw) == "refusal"


class TestAssembleValidation:
    """cmd_assemble attaches validate_run() results to each RunRecord."""

    def _write_raw_json(self, path, payload):
        import json as _json

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_json.dumps(payload), encoding="utf-8")

    def _write_record(self, path, result_file):
        from aedist.schema import Method, MethodParams, RunRecord

        rec = RunRecord(
            method=Method.SINGLE,
            method_params=MethodParams(model="test/model"),
            result_file=str(result_file),
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rec.model_dump_json(indent=2, exclude_none=True), encoding="utf-8")

    def test_assemble_attaches_ok_validation_for_clean_run(self, tmp_path, monkeypatch):
        import argparse

        from aedist.evaluate import cmd_assemble
        from aedist.schema import RunRecord

        monkeypatch.chdir(tmp_path)
        raw_path = tmp_path / "experiments" / "outputs" / "census" / "ok-run1.json"
        self._write_raw_json(
            raw_path,
            {
                "model": "test/model",
                "response": "```csv\nName,Fuel\nPha Lai,Coal\n```",
                "finish_reason": "stop",
                "usage": {"prompt_tokens": 50, "completion_tokens": 800},
                "model_metadata": {"context_window": 128000},
            },
        )
        rec_path = tmp_path / "ok-run1.record.json"
        self._write_record(rec_path, raw_path.relative_to(tmp_path))

        out = tmp_path / "measurements.jsonl"
        cmd_assemble(argparse.Namespace(record_files=[str(rec_path)], output=str(out)))

        records = RunRecord.load_jsonl(out)
        assert len(records) == 1
        assert records[0].validation is not None
        assert records[0].validation["category"] == "ok"
        assert records[0].validation["ok"] is True

    def test_assemble_flags_empty_response_run(self, tmp_path, monkeypatch):
        import argparse

        from aedist.evaluate import cmd_assemble
        from aedist.schema import RunRecord

        monkeypatch.chdir(tmp_path)
        raw_path = tmp_path / "experiments" / "outputs" / "rag" / "gemma-run1.json"
        self._write_raw_json(
            raw_path,
            {
                "model": "ollama/gemma",
                "response": "",
                "finish_reason": "stop",
                "usage": {"prompt_tokens": 100, "completion_tokens": 20000},
                "model_metadata": {"context_window": 128000},
            },
        )
        rec_path = tmp_path / "gemma-run1.record.json"
        self._write_record(rec_path, raw_path.relative_to(tmp_path))

        out = tmp_path / "measurements.jsonl"
        cmd_assemble(argparse.Namespace(record_files=[str(rec_path)], output=str(out)))

        records = RunRecord.load_jsonl(out)
        assert records[0].validation["category"] == "empty"
        assert records[0].validation["ok"] is False
        assert "empty_content" in records[0].validation["flags"]

    def test_assemble_missing_raw_json_leaves_validation_none(self, tmp_path, monkeypatch):
        """If the companion raw JSON is missing, validation is skipped, not crashed."""
        import argparse
        from pathlib import Path

        from aedist.evaluate import cmd_assemble
        from aedist.schema import RunRecord

        monkeypatch.chdir(tmp_path)
        rec_path = tmp_path / "orphan.record.json"
        self._write_record(rec_path, Path("experiments/outputs/gone/missing-run1.json"))

        out = tmp_path / "measurements.jsonl"
        cmd_assemble(argparse.Namespace(record_files=[str(rec_path)], output=str(out)))

        records = RunRecord.load_jsonl(out)
        assert records[0].validation is None

    def test_assemble_derives_raw_json_from_csv_result_file(self, tmp_path, monkeypatch):
        """Regression (ticket 0072 B1): real records store ``result_file`` as the
        CSV companion path, not the raw JSON. The validator must derive the
        raw JSON path from the CSV stem. Prior to this fix, every CSV-backed
        record silently got ``validation=None``.

        Uses a real fixture pair from experiments/outputs/rag/ so that any
        drift between fixture shape and validator expectations is caught.
        """
        import argparse
        import json as _json
        import shutil
        from pathlib import Path

        from aedist.evaluate import cmd_assemble
        from aedist.schema import RunRecord

        repo_root = Path(__file__).resolve().parent.parent
        src_raw = repo_root / "experiments/outputs/rag/deepseek-v3.2-run1.json"
        src_rec = repo_root / "experiments/outputs/rag/deepseek-v3.2-run1.record.json"
        assert src_raw.exists(), f"fixture missing: {src_raw}"
        assert src_rec.exists(), f"fixture missing: {src_rec}"

        monkeypatch.chdir(tmp_path)
        dst_dir = tmp_path / "experiments" / "outputs" / "rag"
        dst_dir.mkdir(parents=True)
        shutil.copy(src_raw, dst_dir / "deepseek-v3.2-run1.json")

        # Load the real record and keep its CSV result_file as-is: this is
        # exactly the shape the real corpus has.
        record_data = _json.loads(src_rec.read_text(encoding="utf-8"))
        assert record_data["result_file"].endswith(".csv"), (
            "fixture must have CSV result_file to exercise the regression"
        )
        rec_path = tmp_path / "deepseek-v3.2-run1.record.json"
        rec_path.write_text(_json.dumps(record_data), encoding="utf-8")

        out = tmp_path / "measurements.jsonl"
        cmd_assemble(argparse.Namespace(record_files=[str(rec_path)], output=str(out)))

        records = RunRecord.load_jsonl(out)
        assert len(records) == 1
        # The fix must attach a validation; it must not be None.
        assert records[0].validation is not None, (
            "validation should be attached when the raw JSON exists alongside "
            "the CSV companion (derived from result_file stem)"
        )
        assert records[0].validation["category"] in {
            "ok",
            "empty",
            "truncated_output",
            "truncated_input",
            "provider_error",
        }
