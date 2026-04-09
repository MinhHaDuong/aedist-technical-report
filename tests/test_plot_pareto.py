"""Tests for aedist.plot_pareto — Pareto CSV from metrics JSON."""

import csv

from conftest import patch_measurements_loader, write_measurements

from aedist.plot_pareto import build_pareto_rows

SAMPLE_METRICS = [
    {"label": "census/gpt-5.4-run1", "f1": 0.70},
    {"label": "census/gpt-5.4-run2", "f1": 0.68},
    {"label": "census/gpt-5.4-run3", "f1": 0.72},
    {"label": "census/padme-qwen3.5-27b-run1", "f1": 0.50},
    {"label": "census/padme-qwen3.5-27b-run2", "f1": 0.52},
    {"label": "census/padme-qwen3.5-27b-run3", "f1": 0.48},
]


def test_build_pareto_rows():
    """Rows have correct models with median f1 and local flag."""
    rows = build_pareto_rows(SAMPLE_METRICS)
    assert len(rows) == 2
    assert all(set(r.keys()) == {"model", "f1", "cost_usd", "local"} for r in rows)
    by_model = {r["model"]: r for r in rows}
    assert by_model["gpt-5.4"]["f1"] == 0.70  # median of [0.68, 0.70, 0.72]
    assert by_model["gpt-5.4"]["local"] == 0
    assert by_model["padme-qwen3.5-27b"]["f1"] == 0.50  # median of [0.48, 0.50, 0.52]
    assert by_model["padme-qwen3.5-27b"]["local"] == 1


def test_cost_without_explicit_data():
    """Cost defaults to 0.0 when no cost data in metrics."""
    rows = build_pareto_rows(SAMPLE_METRICS)
    for row in rows:
        assert row["cost_usd"] == 0.0


def test_local_flag():
    """Padme models flagged as local."""
    rows = build_pareto_rows(SAMPLE_METRICS)
    by_model = {r["model"]: r for r in rows}
    assert by_model["gpt-5.4"]["local"] == 0
    assert by_model["padme-qwen3.5-27b"]["local"] == 1


def test_main_writes_csv(tmp_path, monkeypatch):
    """CLI writes well-formed CSV."""
    input_path = tmp_path / "measurements.jsonl"
    write_measurements(input_path, SAMPLE_METRICS)
    patch_measurements_loader(monkeypatch, input_path)
    output_path = tmp_path / "pareto.csv"

    import sys

    from aedist.plot_pareto import main

    sys.argv = [
        "plot_pareto",
        "--output",
        str(output_path),
    ]
    main()

    content = output_path.read_text()
    reader = csv.DictReader(content.splitlines())
    rows = list(reader)
    assert len(rows) == 2
    assert set(reader.fieldnames) == {"model", "f1", "cost_usd", "local"}
