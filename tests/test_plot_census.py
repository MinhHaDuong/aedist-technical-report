"""Tests for aedist.plot_census — CSV bar-chart data from metrics JSON."""

import csv

from conftest import patch_measurements_loader, write_measurements

from aedist.plot_census import build_census_rows

SAMPLE_METRICS = [
    {"label": "census/gpt-5.4-run1", "f1": 0.70},
    {"label": "census/gpt-5.4-run2", "f1": 0.68},
    {"label": "census/gpt-5.4-run3", "f1": 0.72},
    {"label": "census/padme-qwen3.5-27b-run1", "f1": 0.50},
    {"label": "census/padme-qwen3.5-27b-run2", "f1": 0.52},
    {"label": "census/padme-qwen3.5-27b-run3", "f1": 0.48},
    {"label": "census/claude-4-run1", "f1": 0.65},
    {"label": "census/claude-4-run2", "f1": 0.63},
    {"label": "census/claude-4-run3", "f1": 0.67},
]


def test_build_census_rows():
    """Rows are sorted by f1 descending with correct local flag."""
    rows = build_census_rows(SAMPLE_METRICS)
    assert len(rows) == 3
    # Sorted by f1 descending
    assert rows[0]["model"] == "gpt-5.4"
    assert rows[1]["model"] == "claude-4"
    assert rows[2]["model"] == "padme-qwen3.5-27b"
    # F1 is median as decimal
    assert rows[0]["f1"] == 0.70
    assert rows[2]["f1"] == 0.50
    # Local flag
    assert rows[0]["local"] == 0
    assert rows[2]["local"] == 1


def test_slug_underscores_replaced_with_dashes():
    """Underscore in model slug is sanitised to dash (pgfplots safety)."""
    metrics_with_underscore = [
        {"label": "census/gpt-5.4_cross-run1", "f1": 0.80},
        {"label": "census/gpt-5.4_cross-run2", "f1": 0.78},
        {"label": "census/gpt-5.4_cross-run3", "f1": 0.82},
    ]
    rows = build_census_rows(metrics_with_underscore)
    assert len(rows) == 1
    assert "_" not in rows[0]["model"], "underscores must be replaced with dashes"
    assert rows[0]["model"] == "gpt-5.4-cross"


def test_output_is_sorted_descending():
    """First row has highest F1."""
    rows = build_census_rows(SAMPLE_METRICS)
    f1_values = [r["f1"] for r in rows]
    assert f1_values == sorted(f1_values, reverse=True)


def test_main_writes_csv(tmp_path, monkeypatch):
    """CLI writes well-formed CSV with header."""
    input_path = tmp_path / "measurements.jsonl"
    write_measurements(input_path, SAMPLE_METRICS)
    patch_measurements_loader(monkeypatch, input_path)
    output_path = tmp_path / "census_bars.csv"

    import sys

    from aedist.plot_census import main

    sys.argv = [
        "plot_census",
        "--output",
        str(output_path),
    ]
    main()

    content = output_path.read_text()
    reader = csv.DictReader(content.splitlines())
    rows = list(reader)
    assert len(rows) == 3
    assert set(reader.fieldnames) == {"model", "f1", "local"}
