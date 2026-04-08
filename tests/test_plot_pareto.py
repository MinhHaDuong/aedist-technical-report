"""Tests for aedist.plot_pareto — Pareto CSV from metrics JSON."""

import csv

from conftest import patch_measurements_loader, write_measurements

from aedist.plot_pareto import build_pareto_rows, load_costs

SAMPLE_METRICS = [
    {"label": "census/gpt-5.4-run1", "f1": 0.70},
    {"label": "census/gpt-5.4-run2", "f1": 0.68},
    {"label": "census/gpt-5.4-run3", "f1": 0.72},
    {"label": "census/padme-qwen3.5-27b-run1", "f1": 0.50},
    {"label": "census/padme-qwen3.5-27b-run2", "f1": 0.52},
    {"label": "census/padme-qwen3.5-27b-run3", "f1": 0.48},
]

SUMMARY_CSV = """\
model,n_runs,median_f1,median_coverage,median_precision,median_fuel_accuracy,median_n_plants,total_cost_usd,median_latency_s
gpt-5.4,3,0.7000,0.8000,0.9000,0.5000,10,0.045000,2.5
padme-qwen3.5-27b,3,0.5000,0.6000,0.7000,0.4000,8,0.000000,5.0
"""


def test_build_pareto_rows():
    """Rows have model, f1, cost_usd, local columns."""
    rows = build_pareto_rows(SAMPLE_METRICS)
    assert len(rows) == 2
    assert all(set(r.keys()) == {"model", "f1", "cost_usd", "local"} for r in rows)


def test_cost_without_csv():
    """Cost defaults to 0.0 when no cost data provided."""
    rows = build_pareto_rows(SAMPLE_METRICS)
    for row in rows:
        assert row["cost_usd"] == 0.0


def test_cost_from_csv(tmp_path):
    """Cost is per-run (total_cost / n_runs) when CSV provided."""
    csv_path = tmp_path / "summary.csv"
    csv_path.write_text(SUMMARY_CSV)
    costs = load_costs(csv_path)
    rows = build_pareto_rows(SAMPLE_METRICS, costs)
    by_model = {r["model"]: r for r in rows}
    assert by_model["gpt-5.4"]["cost_usd"] == 0.015  # 0.045 / 3
    assert by_model["padme-qwen3.5-27b"]["cost_usd"] == 0.0


def test_local_flag():
    """Padme models flagged as local."""
    rows = build_pareto_rows(SAMPLE_METRICS)
    by_model = {r["model"]: r for r in rows}
    assert by_model["gpt-5.4"]["local"] == 0
    assert by_model["padme-qwen3.5-27b"]["local"] == 1


def test_main_writes_csv(tmp_path, monkeypatch):
    """CLI writes well-formed CSV with cost data."""
    input_path = tmp_path / "measurements.jsonl"
    write_measurements(input_path, SAMPLE_METRICS)
    patch_measurements_loader(monkeypatch, input_path)
    costs_path = tmp_path / "summary.csv"
    costs_path.write_text(SUMMARY_CSV)
    output_path = tmp_path / "pareto.csv"

    import sys

    from aedist.plot_pareto import main

    sys.argv = [
        "plot_pareto",
        "--costs",
        str(costs_path),
        "--output",
        str(output_path),
    ]
    main()

    content = output_path.read_text()
    reader = csv.DictReader(content.splitlines())
    rows = list(reader)
    assert len(rows) == 2
    assert set(reader.fieldnames) == {"model", "f1", "cost_usd", "local"}
    by_model = {r["model"]: r for r in rows}
    assert float(by_model["gpt-5.4"]["cost_usd"]) == 0.015


def test_main_without_costs(tmp_path, monkeypatch):
    """CLI works without --costs."""
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
