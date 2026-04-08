"""Shared test fixtures for aedist tests."""

import tomllib
from pathlib import Path

import pytest
import yaml

EXPERIMENTS_DIR = Path(__file__).parent.parent / "experiments"


@pytest.fixture
def models():
    """Load the model registry."""
    with open(EXPERIMENTS_DIR / "models.yaml") as f:
        return yaml.safe_load(f)


@pytest.fixture
def experiments():
    """Load experiments.toml configuration."""
    with open(EXPERIMENTS_DIR / "experiments.toml", "rb") as f:
        return tomllib.load(f)


def write_measurements(path: Path, metrics: list[dict]) -> None:
    """Convert metrics dicts to measurements.jsonl for CLI tests."""
    from aedist.runner import _infer_method
    from aedist.schema import MethodParams, ResourceUse, ResultSummary, RunRecord

    records = []
    for entry in metrics:
        label = entry["label"]
        prompt_version, stem = label.rsplit("/", 1) if "/" in label else ("", label)
        tp = entry.get("n_matched", 0)
        fn = entry.get("n_missed", 0)
        fp = entry.get("n_hallucinated", 0)

        records.append(
            RunRecord(
                method=_infer_method(prompt_version),
                method_params=MethodParams(
                    model=stem,
                    prompt_version=prompt_version or None,
                ),
                resource_use=ResourceUse(
                    cost_usd=entry.get("cost_usd"),
                    wall_s=entry.get("wall_seconds"),
                ),
                result_file=f"{label}.csv",
                result_summary=ResultSummary(
                    n_plants=entry.get("n_system", tp + fp),
                    tp=tp,
                    fp=fp,
                    fn=fn,
                    f1=entry.get("f1"),
                    fuel_accuracy=entry.get("fuel_accuracy"),
                    status_accuracy=entry.get("status_accuracy"),
                    province_accuracy=entry.get("province_accuracy"),
                ),
            )
        )
    RunRecord.save_jsonl(records, path)


def patch_measurements_loader(monkeypatch, meas_path: Path) -> None:
    """Point aedist.measurements.load at a test measurements file."""
    import aedist.measurements as mmod

    monkeypatch.setattr(mmod, "_load_paths", lambda: {"measurements": str(meas_path)})
    monkeypatch.setattr(mmod, "_resolve", lambda p: Path(p))
