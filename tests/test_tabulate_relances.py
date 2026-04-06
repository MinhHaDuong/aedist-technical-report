"""Tests for aedist.tabulate_relances — generate multi-turn relances LaTeX table."""

import json

from aedist.tabulate_relances import (
    _generate_per_turn_table,
    _generate_summary_table,
    generate_relances_table,
    group_by_model_and_turn,
    main,
)

# --- Fixtures ---

# Per-turn entries (with "turn" field) for two models, 3 runs each, turns 0-2.
SAMPLE_PER_TURN_METRICS = [
    # gpt-5.4 run1
    {"label": "sweep2_multiturn/gpt-5.4-run1", "turn": 0, "f1": 0.40, "precision": 0.90, "coverage": 0.30, "n_reference": 163, "n_matched": 49},
    {"label": "sweep2_multiturn/gpt-5.4-run1", "turn": 1, "f1": 0.55, "precision": 0.92, "coverage": 0.45, "n_reference": 163, "n_matched": 73},
    {"label": "sweep2_multiturn/gpt-5.4-run1", "turn": 2, "f1": 0.65, "precision": 0.95, "coverage": 0.50, "n_reference": 163, "n_matched": 82},
    # gpt-5.4 run2
    {"label": "sweep2_multiturn/gpt-5.4-run2", "turn": 0, "f1": 0.42, "precision": 0.91, "coverage": 0.32, "n_reference": 163, "n_matched": 52},
    {"label": "sweep2_multiturn/gpt-5.4-run2", "turn": 1, "f1": 0.57, "precision": 0.93, "coverage": 0.47, "n_reference": 163, "n_matched": 77},
    {"label": "sweep2_multiturn/gpt-5.4-run2", "turn": 2, "f1": 0.67, "precision": 0.96, "coverage": 0.52, "n_reference": 163, "n_matched": 85},
    # gpt-5.4 run3
    {"label": "sweep2_multiturn/gpt-5.4-run3", "turn": 0, "f1": 0.38, "precision": 0.89, "coverage": 0.28, "n_reference": 163, "n_matched": 46},
    {"label": "sweep2_multiturn/gpt-5.4-run3", "turn": 1, "f1": 0.53, "precision": 0.91, "coverage": 0.43, "n_reference": 163, "n_matched": 70},
    {"label": "sweep2_multiturn/gpt-5.4-run3", "turn": 2, "f1": 0.63, "precision": 0.94, "coverage": 0.48, "n_reference": 163, "n_matched": 78},
    # padme-qwen3.5-122b run1
    {"label": "sweep2_multiturn/padme-qwen3.5-122b-run1", "turn": 0, "f1": 0.20, "precision": 0.80, "coverage": 0.15, "n_reference": 163, "n_matched": 24},
    {"label": "sweep2_multiturn/padme-qwen3.5-122b-run1", "turn": 1, "f1": 0.30, "precision": 0.82, "coverage": 0.22, "n_reference": 163, "n_matched": 36},
    {"label": "sweep2_multiturn/padme-qwen3.5-122b-run1", "turn": 2, "f1": 0.38, "precision": 0.85, "coverage": 0.28, "n_reference": 163, "n_matched": 46},
    # padme-qwen3.5-122b run2
    {"label": "sweep2_multiturn/padme-qwen3.5-122b-run2", "turn": 0, "f1": 0.22, "precision": 0.81, "coverage": 0.17, "n_reference": 163, "n_matched": 28},
    {"label": "sweep2_multiturn/padme-qwen3.5-122b-run2", "turn": 1, "f1": 0.32, "precision": 0.83, "coverage": 0.24, "n_reference": 163, "n_matched": 39},
    {"label": "sweep2_multiturn/padme-qwen3.5-122b-run2", "turn": 2, "f1": 0.40, "precision": 0.86, "coverage": 0.30, "n_reference": 163, "n_matched": 49},
    # padme-qwen3.5-122b run3
    {"label": "sweep2_multiturn/padme-qwen3.5-122b-run3", "turn": 0, "f1": 0.18, "precision": 0.79, "coverage": 0.13, "n_reference": 163, "n_matched": 21},
    {"label": "sweep2_multiturn/padme-qwen3.5-122b-run3", "turn": 1, "f1": 0.28, "precision": 0.81, "coverage": 0.20, "n_reference": 163, "n_matched": 33},
    {"label": "sweep2_multiturn/padme-qwen3.5-122b-run3", "turn": 2, "f1": 0.36, "precision": 0.84, "coverage": 0.26, "n_reference": 163, "n_matched": 43},
]

# Summary entries (no "turn" field) for fallback table.
SAMPLE_SUMMARY_METRICS = [
    {"label": "sweep2_multiturn/gpt-5.4-run1", "f1": 0.658, "precision": 1.0, "coverage": 0.491, "n_reference": 163, "n_matched": 80},
    {"label": "sweep2_multiturn/gpt-5.4-run2", "f1": 0.660, "precision": 0.980, "coverage": 0.500, "n_reference": 163, "n_matched": 82},
    {"label": "sweep2_multiturn/gpt-5.4-run3", "f1": 0.640, "precision": 0.990, "coverage": 0.470, "n_reference": 163, "n_matched": 77},
    {"label": "sweep2_multiturn/padme-qwen3.5-122b-run1", "f1": 0.436, "precision": 0.800, "coverage": 0.300, "n_reference": 163, "n_matched": 49},
    {"label": "sweep2_multiturn/padme-qwen3.5-122b-run2", "f1": 0.465, "precision": 0.850, "coverage": 0.320, "n_reference": 163, "n_matched": 52},
    {"label": "sweep2_multiturn/padme-qwen3.5-122b-run3", "f1": 0.450, "precision": 0.820, "coverage": 0.310, "n_reference": 163, "n_matched": 51},
]


# --- generate_relances_table: no multiturn entries ---


def test_generate_relances_table_no_multiturn_entries():
    """When no sweep2_multiturn entries exist, returns empty summary table."""
    non_mt = [
        {"label": "sweep1_census/gpt-5.4-run1", "f1": 0.65, "precision": 1.0, "coverage": 0.49, "n_reference": 163, "n_matched": 80},
    ]
    latex = generate_relances_table(non_mt)
    assert "\\begin{longtable}" in latex
    assert "\\end{longtable}" in latex
    assert "\\label{tab:relances}" in latex
    # Table should have no data rows (only boilerplate)
    lines = latex.splitlines()
    data_lines = [l for l in lines if "\\\\" in l and "toprule" not in l and "midrule" not in l and "endhead" not in l and "bottomrule" not in l and "endlastfoot" not in l and "caption" not in l and "Model &" not in l]
    assert len(data_lines) == 0


def test_generate_relances_table_empty_list():
    """Empty metrics list produces a valid (empty) table."""
    latex = generate_relances_table([])
    assert "\\begin{longtable}" in latex
    assert "\\end{longtable}" in latex


# --- _generate_per_turn_table ---


def test_generate_per_turn_table_structure():
    latex = _generate_per_turn_table(SAMPLE_PER_TURN_METRICS)
    assert "\\begin{longtable}" in latex
    assert "\\end{longtable}" in latex
    assert "\\label{tab:relances}" in latex
    assert "\\caption{" in latex


def test_generate_per_turn_table_turn_headers():
    """Per-turn table has Prompt header and Relance headers."""
    latex = _generate_per_turn_table(SAMPLE_PER_TURN_METRICS)
    assert "Prompt" in latex
    assert "Relance 1" in latex
    assert "Relance 2" in latex


def test_generate_per_turn_table_matched_format():
    """Each cell shows matched/reference counts."""
    latex = _generate_per_turn_table(SAMPLE_PER_TURN_METRICS)
    # GPT-5.4 turn 0: median of [46, 49, 52] = 49, ref=163
    assert "49/163" in latex


def test_generate_per_turn_table_autogenerated_comment():
    latex = _generate_per_turn_table(SAMPLE_PER_TURN_METRICS)
    assert latex.startswith("% Auto-generated")


def test_generate_per_turn_table_model_names():
    latex = _generate_per_turn_table(SAMPLE_PER_TURN_METRICS)
    assert "GPT-5.4" in latex
    assert "(L)" in latex


def test_generate_per_turn_table_sorted_by_final_turn_f1():
    """Models sorted by final-turn F1 descending (GPT before padme)."""
    latex = _generate_per_turn_table(SAMPLE_PER_TURN_METRICS)
    lines = latex.splitlines()
    data_lines = [l for l in lines if "\\\\" in l and "toprule" not in l and "midrule" not in l and "endhead" not in l and "bottomrule" not in l and "endlastfoot" not in l and "caption" not in l and "Model &" not in l]
    gpt_line = next((i for i, l in enumerate(data_lines) if "GPT-5.4" in l), None)
    padme_line = next((i for i, l in enumerate(data_lines) if "(L)" in l), None)
    assert gpt_line is not None and padme_line is not None
    assert gpt_line < padme_line


# --- _generate_summary_table ---


def test_generate_summary_table_structure():
    latex = _generate_summary_table(SAMPLE_SUMMARY_METRICS)
    assert "\\begin{longtable}" in latex
    assert "\\end{longtable}" in latex
    assert "\\label{tab:relances}" in latex


def test_generate_summary_table_headers():
    latex = _generate_summary_table(SAMPLE_SUMMARY_METRICS)
    assert "Model" in latex
    assert "F1" in latex
    assert "Precision" in latex
    assert "Recall" in latex
    assert "Matched" in latex


def test_generate_summary_table_percentages():
    latex = _generate_summary_table(SAMPLE_SUMMARY_METRICS)
    # GPT-5.4 F1 median of [0.640, 0.658, 0.660] = 0.658 -> 65.8%
    assert "65.8" in latex


def test_generate_summary_table_matched_over_total():
    latex = _generate_summary_table(SAMPLE_SUMMARY_METRICS)
    # GPT median matched [77, 80, 82] = 80
    assert "80/163" in latex


def test_generate_summary_table_used_when_no_turn_field():
    """generate_relances_table dispatches to summary when turn field absent."""
    latex = generate_relances_table(SAMPLE_SUMMARY_METRICS)
    assert "F1" in latex
    assert "Precision" in latex
    assert "Prompt" not in latex


# --- group_by_model_and_turn ---


def test_group_by_model_and_turn_skips_entries_without_turn():
    mixed = [
        {"label": "sweep2_multiturn/gpt-5.4-run1", "f1": 0.65, "n_reference": 163, "n_matched": 80},
        {"label": "sweep2_multiturn/gpt-5.4-run1", "turn": 0, "f1": 0.40, "n_reference": 163, "n_matched": 49},
    ]
    grouped = group_by_model_and_turn(mixed)
    assert "gpt-5.4" in grouped
    # Only the entry with turn=0 should be present
    assert 0 in grouped["gpt-5.4"]
    total_entries = sum(len(v) for turns in grouped.values() for v in turns.values())
    assert total_entries == 1


def test_group_by_model_and_turn_empty_input():
    grouped = group_by_model_and_turn([])
    assert grouped == {}


def test_group_by_model_and_turn_all_without_turn():
    entries = [
        {"label": "sweep2_multiturn/gpt-5.4-run1", "f1": 0.65, "n_reference": 163, "n_matched": 80},
        {"label": "sweep2_multiturn/gpt-5.4-run2", "f1": 0.66, "n_reference": 163, "n_matched": 82},
    ]
    grouped = group_by_model_and_turn(entries)
    assert grouped == {}


def test_group_by_model_and_turn_groups_correctly():
    grouped = group_by_model_and_turn(SAMPLE_PER_TURN_METRICS)
    assert "gpt-5.4" in grouped
    assert "padme-qwen3.5-122b" in grouped
    # 3 runs per turn
    assert len(grouped["gpt-5.4"][0]) == 3
    assert len(grouped["gpt-5.4"][1]) == 3
    assert len(grouped["gpt-5.4"][2]) == 3


# --- Single-run models ---


def test_single_run_per_turn_table():
    """Model with only one run should still produce valid per-turn output."""
    single_run = [e for e in SAMPLE_PER_TURN_METRICS if e["label"] == "sweep2_multiturn/gpt-5.4-run1"]
    latex = _generate_per_turn_table(single_run)
    assert "\\begin{longtable}" in latex
    assert "GPT-5.4" in latex
    assert "49/163" in latex


def test_single_run_summary_table():
    """Model with only one run should still produce valid summary output."""
    data = [SAMPLE_SUMMARY_METRICS[0]]
    latex = _generate_summary_table(data)
    assert "\\begin{longtable}" in latex
    assert "GPT-5.4" in latex


# --- CLI integration ---


def _write_measurements(path, metrics):
    from aedist.measurements_adapter import metrics_to_records
    from aedist.schema import RunRecord

    RunRecord.save_jsonl(metrics_to_records(metrics), path)


def test_main_writes_output(tmp_path):
    """main() reads measurements.jsonl and writes LaTeX output."""
    input_file = tmp_path / "measurements.jsonl"
    _write_measurements(input_file, SAMPLE_PER_TURN_METRICS)
    output_file = tmp_path / "tab_relances.tex"

    main(["--measurements", str(input_file), "--output", str(output_file)])

    content = output_file.read_text()
    assert "\\begin{longtable}" in content
    assert "\\label{tab:relances}" in content


def test_main_creates_parent_dirs(tmp_path):
    """main() creates parent directories if they don't exist."""
    input_file = tmp_path / "measurements.jsonl"
    _write_measurements(input_file, SAMPLE_SUMMARY_METRICS)
    output_file = tmp_path / "sub" / "dir" / "tab_relances.tex"

    main(["--measurements", str(input_file), "--output", str(output_file)])

    assert output_file.exists()
