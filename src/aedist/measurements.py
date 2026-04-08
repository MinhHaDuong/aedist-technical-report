"""Measurements loader — sole read interface for benchmark results.

All reporting scripts import ``load()`` instead of reading files directly.
The path to the measurements cache is read from ``experiments.toml [paths]``.

Usage::

    from aedist.measurements import load

    records = load()                    # all records
    records = load(method="rag")        # filtered by method
    records = load(method="frontier")   # qualitative results
"""

import tomllib
from pathlib import Path

from .schema import Method, RunRecord

# experiments.toml lives at the repo root under experiments/.
_EXPERIMENTS_TOML = Path(__file__).parent.parent.parent / "experiments" / "experiments.toml"


def _load_paths() -> dict[str, str]:
    """Read [paths] section from experiments.toml."""
    with open(_EXPERIMENTS_TOML, "rb") as f:
        config = tomllib.load(f)
    return config.get("paths", {})


def _resolve(rel_path: str) -> Path:
    """Resolve a path relative to the repo root."""
    repo_root = Path(__file__).parent.parent.parent
    return repo_root / rel_path


def load(method: str | None = None) -> list[RunRecord]:
    """Load measurements, optionally filtered by method.

    Reads the cache file declared in ``experiments.toml [paths].measurements``.
    Returns an empty list if the file does not exist yet (run ``make measurements``).
    """
    paths = _load_paths()
    measurements_path = _resolve(paths.get("measurements", "measurements.jsonl"))
    if not measurements_path.exists():
        return []
    records = RunRecord.load_jsonl(measurements_path)
    if method:
        m = Method(method)
        records = [r for r in records if r.method == m]
    return records


def measurements_path() -> Path:
    """Return the resolved path to the measurements file."""
    paths = _load_paths()
    return _resolve(paths.get("measurements", "measurements.jsonl"))


def records_to_metrics(records: list[RunRecord]) -> list[dict]:
    """Convert RunRecord rows to the reporting dict format.

    Produces dicts with keys: label, f1, coverage, precision, n_reference,
    n_system, n_matched, n_missed, n_hallucinated, fuel_accuracy,
    status_accuracy, province_accuracy, cost_usd, wall_seconds.
    """
    result = []
    for r in records:
        s = r.result_summary
        tp = s.tp or 0
        fp = s.fp or 0
        fn = s.fn or 0

        n_reference = tp + fn
        n_system = tp + fp

        coverage = round(tp / n_reference, 4) if n_reference > 0 else 0.0
        precision = round(tp / n_system, 4) if n_system > 0 else 0.0

        prompt_version = r.method_params.prompt_version or ""
        stem = Path(r.result_file).stem if r.result_file else r.run_id
        label = f"{prompt_version}/{stem}" if prompt_version else stem

        d: dict = {
            "label": label,
            "coverage": coverage,
            "precision": precision,
            "f1": s.f1 if s.f1 is not None else 0.0,
            "n_reference": n_reference,
            "n_system": n_system,
            "n_matched": tp,
            "n_missed": fn,
            "n_hallucinated": fp,
            "fuel_accuracy": s.fuel_accuracy,
            "status_accuracy": s.status_accuracy,
            "province_accuracy": s.province_accuracy,
        }

        if r.resource_use.cost_usd is not None:
            d["cost_usd"] = r.resource_use.cost_usd
        if r.resource_use.wall_s is not None:
            d["wall_seconds"] = r.resource_use.wall_s

        result.append(d)
    return result


def load_metrics(method: str | None = None) -> list[dict]:
    """Load measurements and convert to reporting dict format.

    Convenience wrapper: ``load()`` + ``records_to_metrics()``.
    """
    return records_to_metrics(load(method))
