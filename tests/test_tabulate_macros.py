"""Tests for aedist.tabulate_macros — LaTeX macro generation from metrics JSON."""

from conftest import patch_measurements_loader, write_measurements

from aedist.tabulate_macros import generate_macros, load_and_summarize

SAMPLE_METRICS = [
    {"label": "census/gpt-5.4-run1", "f1": 0.70, "coverage": 0.8, "precision": 0.62},
    {"label": "census/gpt-5.4-run2", "f1": 0.68, "coverage": 0.78, "precision": 0.60},
    {"label": "census/gpt-5.4-run3", "f1": 0.72, "coverage": 0.82, "precision": 0.64},
    {"label": "census/claude-4-run1", "f1": 0.65, "coverage": 0.75, "precision": 0.58},
    {"label": "census/claude-4-run2", "f1": 0.63, "coverage": 0.73, "precision": 0.56},
    {"label": "census/claude-4-run3", "f1": 0.67, "coverage": 0.77, "precision": 0.60},
    {
        "label": "census/padme-qwen3.5-27b-run1",
        "f1": 0.50,
        "coverage": 0.60,
        "precision": 0.43,
    },
    {
        "label": "census/padme-qwen3.5-27b-run2",
        "f1": 0.52,
        "coverage": 0.62,
        "precision": 0.45,
    },
    {
        "label": "census/padme-qwen3.5-27b-run3",
        "f1": 0.48,
        "coverage": 0.58,
        "precision": 0.41,
    },
    {
        "label": "census/padme-mistral-small3.2-run1",
        "f1": 0.40,
        "coverage": 0.50,
        "precision": 0.33,
    },
    {
        "label": "census/padme-mistral-small3.2-run2",
        "f1": 0.42,
        "coverage": 0.52,
        "precision": 0.35,
    },
    {
        "label": "census/padme-mistral-small3.2-run3",
        "f1": 0.38,
        "coverage": 0.48,
        "precision": 0.31,
    },
]


def test_load_and_summarize():
    """Model slugs are extracted and median F1 computed per model."""
    summary = load_and_summarize(SAMPLE_METRICS)
    assert len(summary) == 4
    # gpt-5.4 median of [0.68, 0.70, 0.72] = 0.70
    assert summary["gpt-5.4"]["median_f1"] == 0.70
    # claude-4 median of [0.63, 0.65, 0.67] = 0.65
    assert summary["claude-4"]["median_f1"] == 0.65
    assert summary["padme-qwen3.5-27b"]["is_local"] is True
    assert summary["gpt-5.4"]["is_local"] is False


def test_generate_macros():
    """Output contains expected LaTeX newcommands."""
    summary = load_and_summarize(SAMPLE_METRICS)
    tex = generate_macros(summary)
    assert r"\newcommand{\NumModelsTested}" in tex
    assert r"\newcommand{\BestModelName}" in tex
    assert r"\newcommand{\BestModelFOne}" in tex
    assert r"\newcommand{\BestLocalName}" in tex
    assert r"\newcommand{\BestLocalFOne}" in tex
    # Best overall is gpt-5.4 with median F1 = 0.70
    assert "70.0" in tex
    # Best local is padme-qwen3.5-27b with median F1 = 0.50
    assert "50.0" in tex
    # 4 unique models
    assert "{4}" in tex


def test_slug_strips_run_and_dir():
    """Labels with directory prefix and -runN suffix produce clean slugs."""
    metrics = [
        {"label": "census/my-model-run1", "f1": 0.5},
        {"label": "census/my-model-run2", "f1": 0.6},
    ]
    summary = load_and_summarize(metrics)
    assert "my-model" in summary
    assert len(summary) == 1


def test_main_writes_file(tmp_path, monkeypatch):
    """CLI writes macros.tex from measurements."""
    input_path = tmp_path / "measurements.jsonl"
    write_measurements(input_path, SAMPLE_METRICS)
    patch_measurements_loader(monkeypatch, input_path)
    output_path = tmp_path / "macros.tex"

    import sys

    from aedist.tabulate_macros import main

    sys.argv = [
        "tabulate_macros",
        "--output",
        str(output_path),
    ]
    main()
    content = output_path.read_text()
    assert r"\newcommand" in content
