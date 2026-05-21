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
        prompt="prompts/prompt_extract.txt",
        models_file="models.yaml",
        repeat=3,
        budget_usd=10.0,
        output_dir="outputs/direct_extract",
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
            followups="prompts/prompt_followups.txt",
        )
        assert j.followups == "prompts/prompt_followups.txt"

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
            "prompt: prompts/prompt_extract.txt\n"
            "models: models.yaml\n"
            "repeat: 3\n"
            "budget_usd: 10\n"
            "output: outputs/direct_extract\n"
        )
        j = JobSpec.from_sweep_yaml(tmp_path / "sweep.yaml")
        assert j.mode == Method.SINGLE
        assert j.models_file == "models.yaml"
        assert j.output_dir == "outputs/direct_extract"

    def test_rag(self, tmp_path: Path):
        (tmp_path / "sweep.yaml").write_text(
            "mode: rag\n"
            "prompt: prompts/prompt_extract.txt\n"
            "corpus: data/rag_corpus\n"
            "strategy: wholesale\n"
            "models: models_sweep_rag.yaml\n"
            "repeat: 3\n"
            "budget_usd: 10\n"
            "output: outputs/rag_extract\n"
        )
        j = JobSpec.from_sweep_yaml(tmp_path / "sweep.yaml")
        assert j.mode == Method.RAG
        assert j.corpus == "data/rag_corpus"
        assert j.strategy == "wholesale"

    def test_multiturn(self, tmp_path: Path):
        (tmp_path / "sweep.yaml").write_text(
            "mode: multiturn\n"
            "prompt: prompts/prompt_extract.txt\n"
            "followups: prompts/prompt_followups.txt\n"
            "models: models_sweep_rag.yaml\n"
            "repeat: 3\n"
            "budget_usd: 10\n"
            "output: outputs/direct_multiturn\n"
        )
        j = JobSpec.from_sweep_yaml(tmp_path / "sweep.yaml")
        assert j.mode == Method.MULTITURN
        assert j.followups == "prompts/prompt_followups.txt"


class TestJobSpecPromptModules:
    def test_prompt_modules_field(self):
        j = _make_jobspec(prompt_modules=["persona", "overview"])
        assert j.prompt_modules == ["persona", "overview"]

    def test_prompt_modules_default_none(self):
        j = _make_jobspec()
        assert j.prompt_modules is None

    def test_prompt_modules_empty_list(self):
        j = _make_jobspec(prompt_modules=[])
        assert j.prompt_modules == []

    def test_prompt_modules_roundtrip_yaml(self):
        original = _make_jobspec(prompt_modules=["persona", "overview", "citation_columns"])
        restored = JobSpec.from_yaml(original.to_yaml())
        assert restored.prompt_modules == ["persona", "overview", "citation_columns"]

    def test_prompt_modules_none_excluded_from_yaml(self):
        j = _make_jobspec()
        yaml_str = j.to_yaml()
        assert "prompt_modules" not in yaml_str

    def test_prompt_modules_from_toml_section(self):
        section = {
            "mode": "single",
            "prompt_modules": ["persona", "overview"],
            "models": "models.yaml",
            "repeat": 2,
            "budget_usd": 5,
            "output": "outputs/ablation/test",
        }
        j = JobSpec.from_toml_section(section)
        assert j.prompt_modules == ["persona", "overview"]

    def test_prompt_modules_empty_from_toml_section(self):
        section = {
            "mode": "single",
            "prompt_modules": [],
            "models": "models.yaml",
            "repeat": 2,
            "budget_usd": 5,
            "output": "outputs/ablation/test",
        }
        j = JobSpec.from_toml_section(section)
        assert j.prompt_modules == []


class TestJobSpecForbidExtras:
    """Ticket 0139: extra='forbid' rejects unknown keys, accepts new fields."""

    def test_unknown_key_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            _make_jobspec(bogus_field=42)
        assert "bogus_field" in str(exc_info.value) or "Extra inputs" in str(exc_info.value)

    def test_seed_field(self):
        j = _make_jobspec(seed=42)
        assert j.seed == 42

    def test_provider_order_field(self):
        j = _make_jobspec(provider_order=["DeepSeek", "Alibaba"])
        assert j.provider_order == ["DeepSeek", "Alibaba"]

    def test_provider_order_default_none(self):
        j = _make_jobspec()
        assert j.provider_order is None

    def test_num_ctx_field(self):
        j = _make_jobspec(num_ctx=65536)
        assert j.num_ctx == 65536

    def test_num_ctx_default(self):
        j = _make_jobspec()
        assert j.num_ctx == 32768

    def test_max_tokens_field(self):
        j = _make_jobspec(max_tokens=8192)
        assert j.max_tokens == 8192

    def test_web_search_field(self):
        j = _make_jobspec(web_search=True)
        assert j.web_search is True

    def test_round_trip_new_fields(self):
        original = _make_jobspec(
            seed=42,
            provider_order=["DeepSeek"],
            num_ctx=16384,
            max_tokens=8192,
            web_search=True,
        )
        restored = JobSpec.from_yaml(original.to_yaml())
        assert restored == original


class TestJobSpecSweepRemap:
    """Ticket 0139: _remap_sweep_fields strips manager-owned and deprecated keys."""

    def test_model_set_stripped(self):
        """model_set is resolved by manager._filter_models_by_set, not JobSpec."""
        section = {
            "mode": "single",
            "prompt": "p.txt",
            "models": "models.yaml",
            "model_set": "modelset_journal",
            "repeat": 1,
            "output": "outputs/test",
        }
        j = JobSpec.from_toml_section(section)
        assert j.mode == Method.SINGLE

    def test_ollama_url_stripped(self):
        """ollama_url is a legacy sweep key; base URL comes from registry/worker."""
        section = {
            "mode": "single",
            "prompt": "p.txt",
            "models": "models.yaml",
            "ollama_url": "http://localhost:11434/v1",
            "repeat": 1,
            "output": "outputs/test",
        }
        j = JobSpec.from_toml_section(section)
        assert j.mode == Method.SINGLE

    def test_unknown_sweep_key_rejected(self):
        section = {
            "mode": "single",
            "prompt": "p.txt",
            "models": "models.yaml",
            "frobnicate": True,
            "repeat": 1,
            "output": "outputs/test",
        }
        with pytest.raises(ValidationError):
            JobSpec.from_toml_section(section)

    def test_canary_sweep_loads(self):
        """The live Exp 1 sweep (sweep_ablation_p1_direct_base) must load.

        This is the regression check for the forbid flip — if it ever fails,
        a new field was added to the canary sweep without being declared on
        JobSpec or stripped in _remap_sweep_fields.
        """
        section = {
            "mode": "single",
            "prompt_modules": [],
            "models": "models.yaml",
            "model_set": "modelset_ablation_journal",
            "repeat": 5,
            "temperature": 0.0,
            "seed": 42,
            "budget_usd": 15,
            "max_tokens": 32768,
            "system_instruction": "You have no web search capability.",
            "output": "outputs/ablation/direct/p1_base",
        }
        j = JobSpec.from_toml_section(section)
        assert j.mode == Method.SINGLE
        assert j.seed == 42
        assert j.max_tokens == 32768


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
