"""Shared test fixtures for aedist tests."""

from pathlib import Path


def write_measurements(path: Path, metrics: list[dict]) -> None:
    """Convert metrics dicts to measurements.jsonl for CLI tests."""
    from aedist.measurements_adapter import metrics_to_records
    from aedist.schema import RunRecord

    RunRecord.save_jsonl(metrics_to_records(metrics), path)
