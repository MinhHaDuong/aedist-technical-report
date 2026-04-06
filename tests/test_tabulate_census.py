"""Tests for aedist.tabulate_census — generate census results LaTeX table."""

import json

from aedist.tabulate_census import generate_census_table
from aedist.tabulate_utils import format_model_name, group_and_summarize, strip_label

# --- Fixtures ---

SAMPLE_METRICS = [
    {
        "label": "sweep1_census/gpt-5.4-run1",
        "coverage": 0.491,
        "precision": 1.0,
        "f1": 0.658,
        "n_reference": 163,
        "n_matched": 80,
    },
    {
        "label": "sweep1_census/gpt-5.4-run2",
        "coverage": 0.500,
        "precision": 0.980,
        "f1": 0.660,
        "n_reference": 163,
        "n_matched": 82,
    },
    {
        "label": "sweep1_census/gpt-5.4-run3",
        "coverage": 0.470,
        "precision": 0.990,
        "f1": 0.640,
        "n_reference": 163,
        "n_matched": 77,
    },
    {
        "label": "sweep1_census/padme-qwen3.5-122b-run1",
        "coverage": 0.300,
        "precision": 0.800,
        "f1": 0.436,
        "n_reference": 163,
        "n_matched": 49,
    },
    {
        "label": "sweep1_census/padme-qwen3.5-122b-run2",
        "coverage": 0.320,
        "precision": 0.850,
        "f1": 0.465,
        "n_reference": 163,
        "n_matched": 52,
    },
    {
        "label": "sweep1_census/padme-qwen3.5-122b-run3",
        "coverage": 0.310,
        "precision": 0.820,
        "f1": 0.450,
        "n_reference": 163,
        "n_matched": 51,
    },
]


# --- strip_label ---


def test_strip_label_basic():
    assert strip_label("sweep1_census/gpt-5.4-run1") == "gpt-5.4"


def test_strip_label_padme():
    assert strip_label("sweep1_census/padme-qwen3.5-122b-run1") == "padme-qwen3.5-122b"


def test_strip_label_multi_digit_run():
    assert strip_label("sweep1_census/claude-opus-4.6-run12") == "claude-opus-4.6"


def test_strip_label_no_dir():
    assert strip_label("gpt-5.4-run1") == "gpt-5.4"


def test_strip_label_deep_dir():
    assert strip_label("a/b/c/gpt-5.4-run3") == "gpt-5.4"


# --- format_model_name ---


def test_format_model_name_cloud():
    assert format_model_name("gpt-5.4") == "GPT-5.4"


def test_format_model_name_padme():
    assert format_model_name("padme-qwen3.5-122b") == "Qwen3.5-122b (L)"


def test_format_model_name_claude():
    assert format_model_name("claude-opus-4.6") == "Claude-Opus-4.6"


def test_format_model_name_deepseek():
    assert format_model_name("deepseek-v3.2") == "DeepSeek-V3.2"


# --- group_and_summarize ---


def test_group_and_summarize_median_f1():
    rows = group_and_summarize(SAMPLE_METRICS)
    gpt_row = next(r for r in rows if r["slug"] == "gpt-5.4")
    # Median of [0.640, 0.658, 0.660] = 0.658
    assert gpt_row["f1"] == 0.658


def test_group_and_summarize_median_precision():
    rows = group_and_summarize(SAMPLE_METRICS)
    gpt_row = next(r for r in rows if r["slug"] == "gpt-5.4")
    # Median of [0.980, 0.990, 1.0] = 0.990
    assert gpt_row["precision"] == 0.990


def test_group_and_summarize_median_coverage():
    rows = group_and_summarize(SAMPLE_METRICS)
    gpt_row = next(r for r in rows if r["slug"] == "gpt-5.4")
    # Median of [0.470, 0.491, 0.500] = 0.491
    assert gpt_row["coverage"] == 0.491


def test_group_and_summarize_median_matched():
    rows = group_and_summarize(SAMPLE_METRICS)
    gpt_row = next(r for r in rows if r["slug"] == "gpt-5.4")
    # Median of [77, 80, 82] = 80
    assert gpt_row["n_matched"] == 80


def test_group_and_summarize_n_reference():
    rows = group_and_summarize(SAMPLE_METRICS)
    gpt_row = next(r for r in rows if r["slug"] == "gpt-5.4")
    assert gpt_row["n_reference"] == 163


def test_group_and_summarize_sorted_by_f1_desc():
    rows = group_and_summarize(SAMPLE_METRICS)
    assert rows[0]["slug"] == "gpt-5.4"
    assert rows[1]["slug"] == "padme-qwen3.5-122b"


def test_group_and_summarize_local_detection():
    """Local (padme-*) models are detected via slug prefix by format_model_name."""
    rows = group_and_summarize(SAMPLE_METRICS)
    gpt_row = next(r for r in rows if r["slug"] == "gpt-5.4")
    padme_row = next(r for r in rows if r["slug"] == "padme-qwen3.5-122b")
    assert not gpt_row["slug"].startswith("padme-")
    assert padme_row["slug"].startswith("padme-")


def test_group_single_run():
    """Model with only one run should still produce a valid row."""
    data = [SAMPLE_METRICS[0]]  # only gpt-5.4-run1
    rows = group_and_summarize(data)
    assert len(rows) == 1
    assert rows[0]["f1"] == 0.658


# --- generate_census_table ---


def test_generate_census_table_structure():
    latex = generate_census_table(SAMPLE_METRICS)
    assert "\\begin{longtable}" in latex
    assert "\\end{longtable}" in latex
    assert "\\label{tab:census}" in latex
    assert "\\caption{" in latex


def test_generate_census_table_header():
    latex = generate_census_table(SAMPLE_METRICS)
    assert "Model" in latex
    assert "F1" in latex
    assert "Precision" in latex
    assert "Recall" in latex
    assert "Matched" in latex


def test_generate_census_table_autogenerated_comment():
    latex = generate_census_table(SAMPLE_METRICS)
    assert latex.startswith("% Auto-generated")


def test_generate_census_table_local_marker():
    latex = generate_census_table(SAMPLE_METRICS)
    assert "(L)" in latex


def test_generate_census_table_percentages():
    latex = generate_census_table(SAMPLE_METRICS)
    # GPT-5.4 F1=0.658 → 65.8%
    assert "65.8" in latex


def test_generate_census_table_matched_over_total():
    latex = generate_census_table(SAMPLE_METRICS)
    # GPT row: 80/163
    assert "80/163" in latex


# --- CLI integration via file ---


def test_main_writes_output(tmp_path):
    """main() reads input JSON and writes LaTeX output."""
    from aedist.tabulate_census import main

    input_file = tmp_path / "metrics.json"
    input_file.write_text(json.dumps(SAMPLE_METRICS))
    output_file = tmp_path / "tab_census.tex"

    main(["--input", str(input_file), "--output", str(output_file)])

    content = output_file.read_text()
    assert "\\begin{longtable}" in content
    assert "\\label{tab:census}" in content


def test_main_creates_parent_dirs(tmp_path):
    """main() creates parent directories if they don't exist."""
    from aedist.tabulate_census import main

    input_file = tmp_path / "metrics.json"
    input_file.write_text(json.dumps(SAMPLE_METRICS))
    output_file = tmp_path / "sub" / "dir" / "tab_census.tex"

    main(["--input", str(input_file), "--output", str(output_file)])

    assert output_file.exists()
