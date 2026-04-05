"""Tests for the experiment manager fan-out logic."""

import re
from pathlib import Path

import yaml

from aedist.manager import generate
from aedist.schema import JobSpec, Method


def _write_sweep(tmp_path: Path, repeat: int = 2) -> Path:
    """Write a minimal sweep YAML and model registry, return sweep path."""
    models = [
        {"id": "provider/model-a", "name": "Model A"},
        {"id": "provider/model-b", "name": "Model B"},
        {"id": "provider/model-c", "name": "Model C"},
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
