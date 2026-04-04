"""Experiment manager: fan out sweep YAML into per-model job files.

Reads a sweep YAML config, loads the model registry, and creates one
JobSpec file per (model, run) combination in ``jobs/pending/``.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from .harness import load_models
from .schema import JobSpec

_JOB_SUBDIRS = ("pending", "running", "done", "failed")


def _deterministic_job_id(sweep_path: str, model_id: str, run: int) -> str:
    """Generate a stable 12-char hex job ID from (sweep, model, run)."""
    key = f"{sweep_path}:{model_id}:{run}"
    return hashlib.sha256(key.encode()).hexdigest()[:12]


def _existing_job_ids(jobs_root: Path) -> set[str]:
    """Scan all job subdirectories for existing job IDs."""
    ids: set[str] = set()
    for subdir in _JOB_SUBDIRS:
        d = jobs_root / subdir
        if not d.is_dir():
            continue
        for f in d.iterdir():
            if f.suffix == ".yaml" and f.is_file():
                stem = f.stem
                parts = stem.split("-", 1)
                if len(parts) == 2:
                    ids.add(parts[1])
    return ids


def _ensure_dirs(jobs_root: Path) -> None:
    """Create jobs/ directory structure."""
    for subdir in _JOB_SUBDIRS:
        (jobs_root / subdir).mkdir(parents=True, exist_ok=True)


def generate(sweep_path: str, jobs_root: Path | None = None) -> tuple[int, int]:
    """Fan out a sweep config into individual job files.

    Returns (generated_count, skipped_count).
    """
    sweep = Path(sweep_path)
    parent_spec = JobSpec.from_sweep_yaml(sweep)

    models = load_models(parent_spec.models_file)

    if jobs_root is None:
        jobs_root = Path("jobs")
    _ensure_dirs(jobs_root)

    existing = _existing_job_ids(jobs_root)
    sweep_key = str(sweep)

    generated = 0
    skipped = 0

    for model in models:
        model_id = model["id"]
        for run in range(1, parent_spec.repeat + 1):
            job_id = _deterministic_job_id(sweep_key, model_id, run)

            if job_id in existing:
                skipped += 1
                continue

            job = JobSpec(
                job_id=job_id,
                priority=parent_spec.priority,
                mode=parent_spec.mode,
                prompt=parent_spec.prompt,
                models_file=parent_spec.models_file,
                model_filter=model_id,
                corpus=parent_spec.corpus,
                followups=parent_spec.followups,
                strategy=parent_spec.strategy,
                repeat=1,
                budget_usd=parent_spec.budget_usd,
                output_dir=parent_spec.output_dir,
                timeout_seconds=parent_spec.timeout_seconds,
                worker_pool=parent_spec.worker_pool,
            )

            filename = f"{job.priority:03d}-{job_id}.yaml"
            (jobs_root / "pending" / filename).write_text(job.to_yaml())
            existing.add(job_id)
            generated += 1

    return generated, skipped


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="aedist.manager",
        description="Experiment manager — fan out sweep configs into jobs.",
    )
    sub = parser.add_subparsers(dest="command")

    gen = sub.add_parser("generate", help="Generate job files from a sweep YAML.")
    gen.add_argument("sweep_yaml", help="Path to sweep YAML config.")
    gen.add_argument(
        "--jobs-dir",
        default="jobs",
        help="Root directory for job files (default: jobs/).",
    )

    args = parser.parse_args()
    if args.command == "generate":
        generated, skipped = generate(args.sweep_yaml, Path(args.jobs_dir))
        print(f"Generated {generated} jobs, skipped {skipped} existing")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
