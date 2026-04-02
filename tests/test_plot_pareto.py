"""Tests for aedist.plot_pareto — Pareto CSV from metrics JSON."""

import csv
import json

from aedist.plot_pareto import build_pareto_rows


SAMPLE_METRICS = [
    {"label": "sweep1_census/gpt-5.4-run1", "f1": 0.70},
    {"label": "sweep1_census/gpt-5.4-run2", "f1": 0.68},
    {"label": "sweep1_census/gpt-5.4-run3", "f1": 0.72},
    {"label": "sweep1_census/padme-qwen3.5-27b-run1", "f1": 0.50},
    {"label": "sweep1_census/padme-qwen3.5-27b-run2", "f1": 0.52},
    {"label": "sweep1_census/padme-qwen3.5-27b-run3", "f1": 0.48},
]


def test_build_pareto_rows():
    """Rows have model, f1, cost_usd, local columns."""
    rows = build_pareto_rows(SAMPLE_METRICS)
    assert len(rows) == 2
    assert all(set(r.keys()) == {"model", "f1", "cost_usd", "local"} for r in rows)


def test_cost_placeholder():
    """Cost is 0.0 as placeholder until query cost data is integrated."""
    rows = build_pareto_rows(SAMPLE_METRICS)
    for row in rows:
        assert row["cost_usd"] == 0.0


def test_local_flag():
    """Padme models flagged as local."""
    rows = build_pareto_rows(SAMPLE_METRICS)
    by_model = {r["model"]: r for r in rows}
    assert by_model["gpt-5.4"]["local"] == 0
    assert by_model["padme-qwen3.5-27b"]["local"] == 1


def test_main_writes_csv(tmp_path):
    """CLI writes well-formed CSV."""
    input_path = tmp_path / "all_metrics.json"
    input_path.write_text(json.dumps(SAMPLE_METRICS))
    output_path = tmp_path / "pareto.csv"

    from aedist.plot_pareto import main
    import sys

    sys.argv = [
        "plot_pareto",
        "--input", str(input_path),
        "--output", str(output_path),
    ]
    main()

    content = output_path.read_text()
    reader = csv.DictReader(content.splitlines())
    rows = list(reader)
    assert len(rows) == 2
    assert set(reader.fieldnames) == {"model", "f1", "cost_usd", "local"}
