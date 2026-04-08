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
    from aedist.measurements_adapter import metrics_to_records
    from aedist.schema import RunRecord

    RunRecord.save_jsonl(metrics_to_records(metrics), path)
