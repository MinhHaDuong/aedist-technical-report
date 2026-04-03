"""Tests for aedist.summarize_sweep."""

import csv
import json
from pathlib import Path

from aedist.summarize_sweep import main


def _make_metrics(tmp_path: Path, entries: list[dict]) -> Path:
    p = tmp_path / "all_metrics.json"
    p.write_text(json.dumps(entries))
    return p


def _make_query(tmp_path: Path, name: str, cost: float, wall: float) -> None:
    d = tmp_path / "queries"
    d.mkdir(exist_ok=True)
    (d / f"{name}.json").write_text(json.dumps({
        "model": name,
        "cost_usd": cost,
        "wall_seconds": wall,
    }))


def test_summarize_two_models(tmp_path, monkeypatch):
    """Two models, 2 runs each → sorted by median F1 descending."""
    metrics = _make_metrics(tmp_path, [
        {"label": "sweep1/alpha-run1", "f1": 0.6, "coverage": 0.7, "precision": 0.5, "fuel_accuracy": 0.8, "n_system": 10},
        {"label": "sweep1/alpha-run2", "f1": 0.8, "coverage": 0.9, "precision": 0.7, "fuel_accuracy": 0.9, "n_system": 12},
        {"label": "sweep1/beta-run1", "f1": 0.9, "coverage": 0.95, "precision": 0.85, "fuel_accuracy": 0.95, "n_system": 15},
        {"label": "sweep1/beta-run2", "f1": 0.85, "coverage": 0.9, "precision": 0.8, "fuel_accuracy": 0.9, "n_system": 14},
    ])
    queries = tmp_path / "queries"
    queries.mkdir()
    for name, cost, wall in [("alpha-run1", 0.01, 5.0), ("alpha-run2", 0.02, 6.0),
                              ("beta-run1", 0.03, 3.0), ("beta-run2", 0.04, 4.0)]:
        (queries / f"{name}.json").write_text(json.dumps({
            "model": name, "cost_usd": cost, "wall_seconds": wall,
        }))

    out = tmp_path / "summary.csv"
    monkeypatch.setattr("sys.argv", [
        "summarize_sweep",
        "--metrics", str(metrics),
        "--queries", str(queries),
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
    metrics = _make_metrics(tmp_path, [])
    queries = tmp_path / "queries"
    queries.mkdir()
    out = tmp_path / "summary.csv"
    monkeypatch.setattr("sys.argv", [
        "summarize_sweep",
        "--metrics", str(metrics),
        "--queries", str(queries),
        "--output", str(out),
    ])
    main()
    content = out.read_text().strip()
    # Empty metrics → no rows written (file may be empty or missing)
    assert content == "" or content.count("\n") == 0
