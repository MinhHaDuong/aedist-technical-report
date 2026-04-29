"""Tests for aedist.plot_regimes_scatter — regimes scatter plot."""

from conftest import patch_measurements_loader, write_measurements

from aedist.plot_regimes_scatter import load_regimes_data

SAMPLE_METRICS = [
    {"label": "census/gpt-5.4", "n_matched": 80, "n_hallucinated": 2, "n_missed": 83},
    {"label": "census/gpt-5.4", "n_matched": 85, "n_hallucinated": 1, "n_missed": 78},
    {"label": "followups/gpt-5.4", "n_matched": 90, "n_hallucinated": 3, "n_missed": 73},
    {"label": "rag/gpt-5.4", "n_matched": 150, "n_hallucinated": 5, "n_missed": 13},
    {
        "label": "census/gemini-2.5-flash-lite",
        "n_matched": 60,
        "n_hallucinated": 0,
        "n_missed": 103,
    },
    {"label": "rag/gemini-2.5-flash-lite", "n_matched": 155, "n_hallucinated": 2, "n_missed": 8},
    # Non-target model — should be excluded
    {"label": "census/qwen3", "n_matched": 100, "n_hallucinated": 0, "n_missed": 63},
    # Union artifact — should be excluded
    {"label": "rag/gpt-5.4-union", "n_matched": 160, "n_hallucinated": 1, "n_missed": 3},
]


def test_load_filters_to_target_models(tmp_path, monkeypatch):
    input_path = tmp_path / "measurements.jsonl"
    write_measurements(input_path, SAMPLE_METRICS)
    patch_measurements_loader(monkeypatch, input_path)

    data = load_regimes_data()
    models = {model for model, _ in data}
    assert "qwen3" not in models
    assert "gpt-5.4" in models


def test_load_excludes_synthetic(tmp_path, monkeypatch):
    input_path = tmp_path / "measurements.jsonl"
    write_measurements(input_path, SAMPLE_METRICS)
    patch_measurements_loader(monkeypatch, input_path)

    data = load_regimes_data()
    for (model, _method), tp_list in data.items():
        assert not model.endswith("-union"), f"synthetic {model} not filtered"


def test_load_returns_tp_counts(tmp_path, monkeypatch):
    input_path = tmp_path / "measurements.jsonl"
    write_measurements(input_path, SAMPLE_METRICS)
    patch_measurements_loader(monkeypatch, input_path)

    data = load_regimes_data()
    for tp_list in data.values():
        assert all(isinstance(v, int) and v >= 0 for v in tp_list)


def test_write_pdf(tmp_path, monkeypatch):
    input_path = tmp_path / "measurements.jsonl"
    write_measurements(input_path, SAMPLE_METRICS)
    patch_measurements_loader(monkeypatch, input_path)

    data = load_regimes_data()
    output = tmp_path / "fig_regimes_scatter.pdf"

    from aedist.plot_regimes_scatter import write_pdf

    write_pdf(data, output)
    assert output.exists()
    assert output.stat().st_size > 0
