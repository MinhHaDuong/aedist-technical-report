"""Tests for JobSpec and LeaseInfo schema and YAML round-trip."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from aedist.schema import (
    JobSpec,
    LeaseInfo,
    Method,
    WorkerPool,
)


def _make_jobspec(**overrides) -> JobSpec:
    defaults = dict(
        job_id="job_aaa111",
        mode=Method.SINGLE,
        prompt="prompts/prompt_structured.txt",
        models_file="models.yaml",
        repeat=3,
        budget_usd=10.0,
        output_dir="outputs/census",
    )
    defaults.update(overrides)
    return JobSpec(**defaults)


class TestJobSpecConstruction:
    def test_all_fields(self):
        j = _make_jobspec()
        assert j.job_id == "job_aaa111"
        assert j.mode == Method.SINGLE
        assert j.repeat == 3
        assert j.worker_pool == WorkerPool.OPENROUTER

    def test_defaults(self):
        j = JobSpec(
            mode=Method.RAG,
            prompt="prompts/p.txt",
            models_file="models.yaml",
            output_dir="out/",
        )
        assert len(j.job_id) == 12
        assert j.priority == 0
        assert j.timeout_seconds == 600
        assert j.corpus is None

    def test_rag_fields(self):
        j = _make_jobspec(
            mode=Method.RAG,
            corpus="data/rag_corpus",
            strategy="wholesale",
        )
        assert j.corpus == "data/rag_corpus"
        assert j.strategy == "wholesale"

    def test_multiturn_fields(self):
        j = _make_jobspec(
            mode=Method.MULTITURN,
            followups="prompts/followups.txt",
        )
        assert j.followups == "prompts/followups.txt"

    def test_invalid_mode_rejected(self):
        with pytest.raises(ValidationError):
            _make_jobspec(mode="bogus")


class TestJobSpecYamlRoundTrip:
    def test_round_trip(self):
        original = _make_jobspec()
        yaml_str = original.to_yaml()
        restored = JobSpec.from_yaml(yaml_str)
        assert restored == original

    def test_round_trip_with_optional_fields(self):
        original = _make_jobspec(
            mode=Method.RAG,
            corpus="data/rag_corpus",
            strategy="wholesale",
            model_filter="*gpt*",
            estimated_duration=120.0,
            worker_pool=WorkerPool.PADME,
        )
        restored = JobSpec.from_yaml(original.to_yaml())
        assert restored == original

    def test_none_fields_excluded_from_yaml(self):
        j = _make_jobspec()
        yaml_str = j.to_yaml()
        assert "corpus" not in yaml_str
        assert "followups" not in yaml_str


class TestFromSweepYaml:
    def test_census(self, tmp_path: Path):
        (tmp_path / "sweep.yaml").write_text(
            "mode: single\n"
            "prompt: prompts/prompt_structured.txt\n"
            "models: models.yaml\n"
            "repeat: 3\n"
            "budget_usd: 10\n"
            "output: outputs/census\n"
        )
        j = JobSpec.from_sweep_yaml(tmp_path / "sweep.yaml")
        assert j.mode == Method.SINGLE
        assert j.models_file == "models.yaml"
        assert j.output_dir == "outputs/census"

    def test_rag(self, tmp_path: Path):
        (tmp_path / "sweep.yaml").write_text(
            "mode: rag\n"
            "prompt: prompts/prompt_structured.txt\n"
            "corpus: data/rag_corpus\n"
            "strategy: wholesale\n"
            "models: models_sweep_rag.yaml\n"
            "repeat: 3\n"
            "budget_usd: 10\n"
            "output: outputs/rag\n"
        )
        j = JobSpec.from_sweep_yaml(tmp_path / "sweep.yaml")
        assert j.mode == Method.RAG
        assert j.corpus == "data/rag_corpus"
        assert j.strategy == "wholesale"

    def test_multiturn(self, tmp_path: Path):
        (tmp_path / "sweep.yaml").write_text(
            "mode: multiturn\n"
            "prompt: prompts/prompt_structured.txt\n"
            "followups: prompts/followups.txt\n"
            "models: models_sweep_rag.yaml\n"
            "repeat: 3\n"
            "budget_usd: 10\n"
            "output: outputs/multiturn\n"
        )
        j = JobSpec.from_sweep_yaml(tmp_path / "sweep.yaml")
        assert j.mode == Method.MULTITURN
        assert j.followups == "prompts/followups.txt"


class TestLeaseInfo:
    def test_construction(self):
        now = datetime.now(UTC)
        lease = LeaseInfo(
            job_id="job_001",
            worker_id="worker-padme-1",
            start_time=now,
            expiry_time=now + timedelta(minutes=30),
        )
        assert lease.job_id == "job_001"
        assert lease.expiry_time > lease.start_time

    def test_start_time_defaults_to_now(self):
        lease = LeaseInfo(
            job_id="job_002",
            worker_id="worker-or-1",
            expiry_time=datetime(2026, 12, 31, tzinfo=UTC),
        )
        assert lease.start_time.tzinfo is not None

    def test_expiry_required(self):
        with pytest.raises(ValidationError):
            LeaseInfo(job_id="job_003", worker_id="w1")
