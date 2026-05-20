"""Experiment manager: fan out sweep config into per-model job files.

Reads a sweep config (from experiments.toml or a YAML file), loads the
model registry, and creates one JobSpec file per (model, run) combination
in ``jobs/pending/``.
"""

import argparse
import hashlib
from pathlib import Path

from .harness import load_experiments, load_models
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
                # pending/done/failed: {priority:03d}-{job_id}
                parts = stem.split("-", 1)
                if len(parts) == 2 and parts[0].isdigit():
                    ids.add(parts[1])
                # running: {job_id}-lease-{expiry}
                elif "-lease-" in stem:
                    ids.add(stem.split("-lease-")[0])
    return ids


def _ensure_dirs(jobs_root: Path) -> None:
    """Create jobs/ directory structure."""
    for subdir in _JOB_SUBDIRS:
        (jobs_root / subdir).mkdir(parents=True, exist_ok=True)


def _filter_models_by_set(
    models: list[dict],
    model_set: str,
    experiments_path: str | Path,
) -> list[dict]:
    """Restrict the model registry to ids listed in ``[sets.<model_set>]``.

    Resolves ``model_set`` against ``[sets]`` in ``experiments.toml`` and
    returns only the registry entries whose ``name`` is in the allowed set.
    Raises KeyError if the named set does not exist.
    """
    experiments = load_experiments(experiments_path)
    sets = experiments.get("sets", {})
    if model_set not in sets:
        raise KeyError(f"Unknown model_set {model_set!r}; available: {sorted(sets)}")
    allowed = set(sets[model_set].get("model_ids", []))
    filtered = [m for m in models if m["name"] in allowed]
    missing = allowed - {m["name"] for m in filtered}
    if missing:
        raise KeyError(f"model_set {model_set!r} references unknown model ids: {sorted(missing)}")
    return filtered


def generate(
    sweep_path: str | None = None,
    jobs_root: Path | None = None,
    *,
    sweep_config: dict | None = None,
    sweep_name: str | None = None,
    experiments_path: str | Path = "experiments.toml",
) -> tuple[int, int]:
    """Fan out a sweep config into individual job files.

    Provide either *sweep_path* (YAML file) or *sweep_config* (dict from TOML).
    When using *sweep_config*, pass *sweep_name* for deterministic job IDs.
    If the sweep config sets ``model_set``, the model registry is filtered
    to that named set in *experiments_path* before fan-out.
    Returns (generated_count, skipped_count).
    """
    if sweep_config is not None:
        parent_spec = JobSpec.from_toml_section(sweep_config)
        sweep_key = sweep_name or "toml"
        model_set = sweep_config.get("model_set")
    elif sweep_path is not None:
        sweep = Path(sweep_path)
        parent_spec = JobSpec.from_sweep_yaml(sweep)
        sweep_key = str(sweep)
        model_set = None
    else:
        raise ValueError("Provide sweep_path or sweep_config")

    models = load_models(parent_spec.models_file)
    if model_set:
        models = _filter_models_by_set(models, model_set, experiments_path)

    if jobs_root is None:
        jobs_root = Path("jobs")
    _ensure_dirs(jobs_root)

    existing = _existing_job_ids(jobs_root)

    generated = 0
    skipped = 0

    for model in models:
        model_name = model["name"]
        for run in range(1, parent_spec.repeat + 1):
            job_id = _deterministic_job_id(sweep_key, model_name, run)

            if job_id in existing:
                skipped += 1
                continue

            job = JobSpec(
                job_id=job_id,
                priority=parent_spec.priority,
                mode=parent_spec.mode,
                prompt=parent_spec.prompt,
                models_file=parent_spec.models_file,
                model_filter=model_name,
                corpus=parent_spec.corpus,
                followups=parent_spec.followups,
                strategy=parent_spec.strategy,
                prompt_modules=parent_spec.prompt_modules,
                modules_dir=parent_spec.modules_dir,
                repeat=1,
                run_number=run,
                budget_usd=parent_spec.budget_usd,
                temperature=parent_spec.temperature,
                seed=parent_spec.seed,
                max_tokens=parent_spec.max_tokens,
                web_search=parent_spec.web_search,
                no_think=parent_spec.no_think,
                system_instruction=parent_spec.system_instruction,
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

    gen = sub.add_parser("generate", help="Generate job files from a sweep config.")
    gen.add_argument("sweep_yaml", nargs="?", help="Path to sweep YAML config (legacy).")
    gen.add_argument("--sweep", help="Sweep name from experiments.toml.")
    gen.add_argument(
        "--experiments",
        default="experiments.toml",
        help="Path to experiments.toml (default: experiments.toml).",
    )
    gen.add_argument(
        "--jobs-dir",
        default="jobs",
        help="Root directory for job files (default: jobs/).",
    )

    args = parser.parse_args()
    if args.command == "generate":
        if args.sweep:
            config = load_experiments(args.experiments)
            section = config["sweeps"][args.sweep]
            generated, skipped = generate(
                jobs_root=Path(args.jobs_dir),
                sweep_config=section,
                sweep_name=args.sweep,
                experiments_path=args.experiments,
            )
        elif args.sweep_yaml:
            generated, skipped = generate(args.sweep_yaml, Path(args.jobs_dir))
        else:
            parser.error("Provide sweep_yaml or --sweep NAME")
            return
        print(f"Generated {generated} jobs, skipped {skipped} existing")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
