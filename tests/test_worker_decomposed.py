"""Tests for Worker._execute_decomposed — corpus guard + happy path."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aedist.schema import JobSpec
from aedist.worker import Worker


def _make_worker(tmp_path) -> Worker:
    return Worker("test-worker", jobs_root=tmp_path / "jobs")


def _job(corpus: str | None, models_file: str) -> JobSpec:
    return JobSpec(
        mode="rag",
        models_file=models_file,
        corpus=corpus,
        budget_usd=5.0,
        output_dir="out",
        prompt="prompt.txt",
    )


def test_missing_corpus_dir_raises_value_error(tmp_path) -> None:
    worker = _make_worker(tmp_path)
    job = _job(corpus=None, models_file=str(tmp_path / "models.yaml"))
    with pytest.raises(ValueError, match="valid corpus directory"):
        worker._execute_decomposed(
            client=None,
            model_id="m",
            model_entry={},
            prompt="p",
            output_dir=tmp_path / "out",
            run=1,
            pool_label="",
            job=job,
        )


def test_query_failure_raises_runtime_error(tmp_path, monkeypatch) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "doc.md").write_text("content", encoding="utf-8")

    monkeypatch.setattr("aedist.worker.load_corpus", lambda d: ("corpus text", ["doc.md"]))
    monkeypatch.setattr("aedist.worker.query_decomposed", lambda *a, **k: None)

    worker = _make_worker(tmp_path)
    job = _job(corpus=str(corpus), models_file=str(tmp_path / "models.yaml"))
    with pytest.raises(RuntimeError, match="Decomposed query failed"):
        worker._execute_decomposed(
            client=None,
            model_id="m",
            model_entry={},
            prompt="p",
            output_dir=tmp_path / "out",
            run=2,
            pool_label="",
            job=job,
        )


def test_happy_path_writes_json_and_returns_metrics(tmp_path, monkeypatch) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "doc.md").write_text("content", encoding="utf-8")

    monkeypatch.setattr("aedist.worker.load_corpus", lambda d: ("corpus text", ["doc.md"]))
    monkeypatch.setattr(
        "aedist.worker.query_decomposed",
        lambda *a, **k: {
            "merged_csv": "name,fuel\nPha Lai,coal\n",
            "total_usage": {"prompt_tokens": 100, "completion_tokens": 40},
            "total_wall_seconds": 12.5,
            "total_cost_usd": 0.07,
            "n_merged_plants": 1,
        },
    )

    worker = _make_worker(tmp_path)
    output_dir = tmp_path / "out"
    job = _job(corpus=str(corpus), models_file=str(tmp_path / "models.yaml"))
    result = worker._execute_decomposed(
        client=None,
        model_id="deepseek-v3.2",
        model_entry={"provider": "deepseek"},
        prompt="p",
        output_dir=output_dir,
        run=3,
        pool_label="",
        job=job,
        api_kwargs={"temperature": 0.0},
    )

    assert result["wall_seconds"] == 12.5
    assert result["cost_usd"] == 0.07
    assert result["tokens_in"] == 100
    assert result["tokens_out"] == 40

    saved = json.loads(Path(result["result_file"]).read_text(encoding="utf-8"))
    assert saved["strategy"] == "decomposed"
    assert saved["response"] == "name,fuel\nPha Lai,coal\n"
    assert saved["corpus_files"] == ["doc.md"]
    assert saved["n_merged_plants"] == 1
