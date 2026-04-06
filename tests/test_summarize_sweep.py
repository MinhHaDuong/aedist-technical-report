"""Tests for aedist.summarize_sweep."""

import csv
from pathlib import Path

from aedist.summarize_sweep import main


def _write_measurements(path: Path, entries: list[dict]) -> None:
    """Convert metrics dicts to measurements.jsonl."""
    from aedist.measurements_adapter import metrics_to_records
    from aedist.schema import RunRecord

    RunRecord.save_jsonl(metrics_to_records(entries), path)


def test_summarize_two_models(tmp_path, monkeypatch):
    """Two models, 2 runs each → sorted by median F1 descending."""
    meas = tmp_path / "measurements.jsonl"
    _write_measurements(meas, [
        {"label": "sweep1/alpha-run1", "f1": 0.6, "coverage": 0.7, "precision": 0.5, "fuel_accuracy": 0.8, "n_system": 10, "cost_usd": 0.01, "wall_seconds": 5.0},
        {"label": "sweep1/alpha-run2", "f1": 0.8, "coverage": 0.9, "precision": 0.7, "fuel_accuracy": 0.9, "n_system": 12, "cost_usd": 0.02, "wall_seconds": 6.0},
        {"label": "sweep1/beta-run1", "f1": 0.9, "coverage": 0.95, "precision": 0.85, "fuel_accuracy": 0.95, "n_system": 15, "cost_usd": 0.03, "wall_seconds": 3.0},
        {"label": "sweep1/beta-run2", "f1": 0.85, "coverage": 0.9, "precision": 0.8, "fuel_accuracy": 0.9, "n_system": 14, "cost_usd": 0.04, "wall_seconds": 4.0},
    ])

    out = tmp_path / "summary.csv"
    monkeypatch.setattr("sys.argv", [
        "summarize_sweep",
        "--measurements", str(meas),
        "--output", str(out),
    ])
    main()

    rows = list(csv.DictReader(out.open()))
    assert len(rows) == 2
    # beta has higher median F1 (0.875) than alpha (0.7) → beta first
    assert rows[0]["model"] == "beta"
    assert rows[1]["model"] == "alpha"
    assert float(rows[0]["median_f1"]) > float(rows[1]["median_f1"])


def test_summarize_empty_metrics(tmp_path, monkeypatch):
    """Empty metrics → empty CSV (header only)."""
    meas = tmp_path / "measurements.jsonl"
    _write_measurements(meas, [])
    out = tmp_path / "summary.csv"
    monkeypatch.setattr("sys.argv", [
        "summarize_sweep",
        "--measurements", str(meas),
        "--output", str(out),
    ])
    main()
    content = out.read_text().strip()
    # Empty metrics → no rows written (file may be empty or missing)
    assert content == "" or content.count("\n") == 0
