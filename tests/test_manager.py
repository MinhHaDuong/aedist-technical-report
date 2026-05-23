"""Tests for the experiment manager fan-out logic."""

import re
from pathlib import Path

import yaml

from aedist.manager import generate
from aedist.schema import JobSpec, Method


def _write_sweep(tmp_path: Path, repeat: int = 2) -> Path:
    """Write a minimal sweep YAML and model registry, return sweep path."""
    models = [
        {"name": "provider/model-a", "display_name": "Model A"},
        {"name": "provider/model-b", "display_name": "Model B"},
        {"name": "provider/model-c", "display_name": "Model C"},
    ]
    models_path = tmp_path / "models.yaml"
    models_path.write_text(yaml.dump(models))

    sweep_path = tmp_path / "sweep.yaml"
    sweep_path.write_text(
        f"mode: single\n"
        f"prompt: prompts/prompt.txt\n"
        f"models: {models_path}\n"
        f"repeat: {repeat}\n"
        f"budget_usd: 5\n"
        f"output: outputs/test\n"
    )
    return sweep_path


def test_fanout_count(tmp_path: Path):
    """N models x R repeats = N*R job files."""
    sweep_path = _write_sweep(tmp_path, repeat=2)
    jobs_root = tmp_path / "jobs"

    generated, skipped = generate(str(sweep_path), jobs_root)

    assert generated == 6  # 3 models x 2 runs
    assert skipped == 0
    assert len(list((jobs_root / "pending").iterdir())) == 6


def test_idempotency(tmp_path: Path):
    """Running generate twice produces no duplicates."""
    sweep_path = _write_sweep(tmp_path, repeat=2)
    jobs_root = tmp_path / "jobs"

    gen1, skip1 = generate(str(sweep_path), jobs_root)
    gen2, skip2 = generate(str(sweep_path), jobs_root)

    assert gen1 == 6
    assert skip1 == 0
    assert gen2 == 0
    assert skip2 == 6
    assert len(list((jobs_root / "pending").iterdir())) == 6


def test_filename_format(tmp_path: Path):
    """Files match {priority:03d}-{job_id}.yaml pattern."""
    sweep_path = _write_sweep(tmp_path, repeat=1)
    jobs_root = tmp_path / "jobs"
    generate(str(sweep_path), jobs_root)

    pattern = re.compile(r"^\d{3}-[0-9a-f]{12}\.yaml$")
    for f in (jobs_root / "pending").iterdir():
        assert pattern.match(f.name), f"Bad filename: {f.name}"


def test_jobspec_content(tmp_path: Path):
    """Each generated JobSpec has correct model_filter, repeat=1, and mode."""
    sweep_path = _write_sweep(tmp_path, repeat=1)
    jobs_root = tmp_path / "jobs"
    generate(str(sweep_path), jobs_root)

    model_ids_seen = set()
    for f in sorted((jobs_root / "pending").iterdir()):
        spec = JobSpec.from_yaml(f.read_text())
        assert spec.repeat == 1
        assert spec.mode == Method.SINGLE
        assert spec.model_filter is not None
        model_ids_seen.add(spec.model_filter)

    assert model_ids_seen == {
        "provider/model-a",
        "provider/model-b",
        "provider/model-c",
    }


def test_dirs_created(tmp_path: Path):
    """generate creates jobs/{pending,running,done,failed} directories."""
    sweep_path = _write_sweep(tmp_path, repeat=1)
    jobs_root = tmp_path / "jobs"
    generate(str(sweep_path), jobs_root)

    for subdir in ("pending", "running", "done", "failed"):
        assert (jobs_root / subdir).is_dir()


def test_prompt_modules_propagated_to_jobs(tmp_path: Path):
    """Sweep with prompt_modules propagates to each generated job."""
    models = [{"name": "provider/model-a", "display_name": "Model A"}]
    models_path = tmp_path / "models.yaml"
    models_path.write_text(yaml.dump(models))

    sweep_config = {
        "mode": "single",
        "prompt_modules": ["persona", "overview"],
        "models": str(models_path),
        "repeat": 1,
        "budget_usd": 5,
        "output": "outputs/ablation/test",
    }
    jobs_root = tmp_path / "jobs"
    generated, _ = generate(
        jobs_root=jobs_root,
        sweep_config=sweep_config,
        sweep_name="ablation_test",
    )
    assert generated == 1

    job_file = next((jobs_root / "pending").iterdir())
    spec = JobSpec.from_yaml(job_file.read_text())
    assert spec.prompt_modules == ["persona", "overview"]


def test_prompt_modules_empty_list_propagated(tmp_path: Path):
    """Sweep with empty prompt_modules list propagates correctly."""
    models = [{"name": "provider/model-a", "display_name": "Model A"}]
    models_path = tmp_path / "models.yaml"
    models_path.write_text(yaml.dump(models))

    sweep_config = {
        "mode": "single",
        "prompt_modules": [],
        "models": str(models_path),
        "repeat": 1,
        "budget_usd": 5,
        "output": "outputs/ablation/test",
    }
    jobs_root = tmp_path / "jobs"
    generated, _ = generate(
        jobs_root=jobs_root,
        sweep_config=sweep_config,
        sweep_name="ablation_base",
    )
    assert generated == 1

    job_file = next((jobs_root / "pending").iterdir())
    spec = JobSpec.from_yaml(job_file.read_text())
    assert spec.prompt_modules == []


def test_model_set_filters_registry(tmp_path: Path):
    """sweep_config with model_set restricts fan-out to that set's model_ids.

    Regression: prior to this fix, the manager iterated all models in
    models.yaml and silently ignored ``model_set`` (the field isn't on
    JobSpec, and pydantic's default extra='ignore' dropped it). Ticket 0175
    repointed the journal sweep to a 16-model set; ticket 0177 hit the bug
    by generating 315 jobs (63 models × 5 reps) instead of 80.
    """
    models = [
        {"name": "provider/model-a", "display_name": "Model A"},
        {"name": "provider/model-b", "display_name": "Model B"},
        {"name": "provider/model-c", "display_name": "Model C"},
    ]
    models_path = tmp_path / "models.yaml"
    models_path.write_text(yaml.dump(models))

    experiments_path = tmp_path / "experiments.toml"
    experiments_path.write_text(
        '[sets.set_two]\nmodel_ids = ["provider/model-a", "provider/model-c"]\n'
    )

    sweep_config = {
        "mode": "single",
        "prompt_modules": [],
        "models": str(models_path),
        "model_set": "set_two",
        "repeat": 2,
        "budget_usd": 5,
        "seed": 42,
        "max_tokens": 8192,
        "output": "outputs/ablation/test",
    }
    jobs_root = tmp_path / "jobs"
    generated, _ = generate(
        jobs_root=jobs_root,
        sweep_config=sweep_config,
        sweep_name="ablation_set_filter",
        experiments_path=experiments_path,
    )
    assert generated == 4  # 2 models in set × 2 reps

    filters = set()
    for job_file in (jobs_root / "pending").iterdir():
        spec = JobSpec.from_yaml(job_file.read_text())
        filters.add(spec.model_filter)
        assert spec.seed == 42
        assert spec.max_tokens == 8192
    assert filters == {"provider/model-a", "provider/model-c"}


def test_fanout_forwards_all_jobspec_fields(tmp_path: Path):
    """Ticket 0139 regression guard: ``manager.generate`` must propagate
    every JobSpec field from the parent spec to the per-job spec, except
    the four fields that legitimately differ per job (``job_id``,
    ``model_filter``, ``repeat``, ``run_number``).

    Prior to ticket 0139, the per-job ``JobSpec(...)`` call hand-listed
    fields. That hand-list silently dropped any new JobSpec field added
    later (the original silent-drop bug for ``seed``). This test reads
    the parent spec via ``model_dump`` and compares against the child;
    when a new field is added to JobSpec, this test fails until the
    manager forwards it.
    """
    models = [
        {"name": "provider/model-a", "display_name": "Model A"},
    ]
    models_path = tmp_path / "models.yaml"
    models_path.write_text(yaml.dump(models))

    sweep_path = tmp_path / "sweep.yaml"
    sweep_path.write_text(
        f"mode: single\n"
        f"prompt: prompts/prompt.txt\n"
        f"models: {models_path}\n"
        f"repeat: 1\n"
        f"budget_usd: 5\n"
        f"seed: 42\n"
        f"max_tokens: 8192\n"
        f"web_search: true\n"
        f"no_think: true\n"
        f"provider_order: [DeepSeek, Alibaba]\n"
        f"num_ctx: 65536\n"
        f"temperature: 0.5\n"
        f"system_instruction: 'no web search'\n"
        f"evidence_pack_manifest: experiments/evidence_packs/all18tables.yaml\n"
        f"output: outputs/test\n"
    )
    jobs_root = tmp_path / "jobs"

    generate(str(sweep_path), jobs_root)

    parent = JobSpec.from_sweep_yaml(sweep_path)
    job_files = list((jobs_root / "pending").iterdir())
    assert len(job_files) == 1
    child = JobSpec.from_yaml(job_files[0].read_text())

    per_job_overrides = {"job_id", "model_filter", "repeat", "run_number"}
    parent_dump = parent.model_dump()
    child_dump = child.model_dump()
    for field, expected in parent_dump.items():
        if field in per_job_overrides:
            continue
        assert child_dump[field] == expected, (
            f"manager.generate dropped JobSpec field {field!r}: "
            f"parent={expected!r}, child={child_dump[field]!r}"
        )
    # Spot-check the 0139 batch explicitly.
    assert child.seed == 42
    assert child.max_tokens == 8192
    assert child.web_search is True
    assert child.no_think is True
    assert child.provider_order == ["DeepSeek", "Alibaba"]
    assert child.num_ctx == 65536
    assert child.evidence_pack_manifest == "experiments/evidence_packs/all18tables.yaml"


def test_idempotency_across_dirs(tmp_path: Path):
    """Jobs already in running/done/failed are skipped."""
    sweep_path = _write_sweep(tmp_path, repeat=1)
    jobs_root = tmp_path / "jobs"

    # First run creates 3 jobs
    generate(str(sweep_path), jobs_root)
    files = sorted((jobs_root / "pending").iterdir())
    assert len(files) == 3

    # Move one to "done" (keeps pending filename format)
    moved = files[0]
    moved.rename(jobs_root / "done" / moved.name)

    # Move another to "running" with lease format (as Worker.acquire does)
    moved2 = files[1]
    job_id = moved2.stem.split("-", 1)[1]
    moved2.rename(jobs_root / "running" / f"{job_id}-lease-20260404T120000Z.yaml")

    # Second run should still skip all 3
    gen, skipped = generate(str(sweep_path), jobs_root)
    assert gen == 0
    assert skipped == 3
