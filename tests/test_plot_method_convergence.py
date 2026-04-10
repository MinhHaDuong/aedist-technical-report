"""Tests for aedist.plot_method_convergence — strip plot CSV data."""

import csv

from conftest import patch_measurements_loader, write_measurements

from aedist.plot_method_convergence import load_convergence_data

# Sample data: 2 models × 2 methods × 2 runs each
SAMPLE_METRICS = [
    {
        "label": "census/modelA-run1",
        "f1": 0.70,
        "n_matched": 100,
        "n_hallucinated": 5,
        "n_missed": 63,
    },
    {
        "label": "census/modelA-run2",
        "f1": 0.72,
        "n_matched": 105,
        "n_hallucinated": 3,
        "n_missed": 58,
    },
    {
        "label": "census/modelB-run1",
        "f1": 0.50,
        "n_matched": 70,
        "n_hallucinated": 0,
        "n_missed": 93,
    },
    {
        "label": "rag/modelA-run1",
        "f1": 0.90,
        "n_matched": 150,
        "n_hallucinated": 10,
        "n_missed": 13,
    },
    {
        "label": "rag/modelA-run2",
        "f1": 0.88,
        "n_matched": 145,
        "n_hallucinated": 8,
        "n_missed": 18,
    },
    {
        "label": "rag/modelB-run1",
        "f1": 0.85,
        "n_matched": 140,
        "n_hallucinated": 2,
        "n_missed": 23,
    },
    # union artifact — should be excluded
    {
        "label": "rag/modelA-union",
        "f1": 0.95,
        "n_matched": 155,
        "n_hallucinated": 1,
        "n_missed": 8,
    },
]


def test_load_excludes_artifacts(tmp_path, monkeypatch):
    """Union/consolidated artifacts are excluded from convergence data."""
    input_path = tmp_path / "measurements.jsonl"
    write_measurements(input_path, SAMPLE_METRICS)
    patch_measurements_loader(monkeypatch, input_path)

    rows = load_convergence_data()
    models = {r["model"] for r in rows}
    assert "modelA-union" not in models


def test_load_returns_tp_fp(tmp_path, monkeypatch):
    """Each row has integer tp and fp counts."""
    input_path = tmp_path / "measurements.jsonl"
    write_measurements(input_path, SAMPLE_METRICS)
    patch_measurements_loader(monkeypatch, input_path)

    rows = load_convergence_data()
    for r in rows:
        assert isinstance(r["tp"], int)
        assert isinstance(r["fp"], int)
        assert r["tp"] >= 0
        assert r["fp"] >= 0


def test_load_has_correct_methods(tmp_path, monkeypatch):
    """Only included methods appear in output."""
    input_path = tmp_path / "measurements.jsonl"
    write_measurements(input_path, SAMPLE_METRICS)
    patch_measurements_loader(monkeypatch, input_path)

    rows = load_convergence_data()
    methods = {r["method"] for r in rows}
    # census maps to "single", rag stays "rag"
    assert methods <= {"single", "rag", "multiturn", "web", "decomposed"}


def test_main_writes_csv(tmp_path, monkeypatch):
    """CLI writes well-formed CSV with expected columns."""
    input_path = tmp_path / "measurements.jsonl"
    write_measurements(input_path, SAMPLE_METRICS)
    patch_measurements_loader(monkeypatch, input_path)
    output_path = tmp_path / "method_convergence.csv"

    import sys

    from aedist.plot_method_convergence import main

    sys.argv = ["plot_method_convergence", "--output", str(output_path)]
    main()

    content = output_path.read_text()
    reader = csv.DictReader(content.splitlines())
    rows = list(reader)
    assert len(rows) > 0
    assert set(reader.fieldnames) == {"method", "model", "tp", "fp", "fn"}
