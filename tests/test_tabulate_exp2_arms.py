"""Tests for aedist.tabulate_exp2_arms (reads from CSV intermediate)."""

import csv
import json

import pytest

from aedist.tabulate_exp2_arms import (
    _is_truncated,
    _load_runs,
    _run_is_truncated,
    generate_latex,
    main,
    summarize_arms,
)


def _write_json(path, payload):
    path.write_text(json.dumps(payload))


def _write_csv(path, rows, fieldnames):
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


_FIELDS = [
    "arm",
    "agent",
    "model",
    "run",
    "classification",
    "narrative_chars",
    "inventory_rows",
    "cost_usd",
    "wall_s",
    "turns",
]


# --- _is_truncated -----------------------------------------------------------


def test_is_truncated_when_finish_reason_length():
    assert _is_truncated(
        {"finish_reason": "length", "usage": {"completion_tokens": 8000}, "max_tokens": 8192}
    )


def test_is_truncated_when_completion_hits_max_tokens():
    assert _is_truncated(
        {"finish_reason": "stop", "usage": {"completion_tokens": 8192}, "max_tokens": 8192}
    )


def test_is_not_truncated_when_completion_below_cap():
    assert not _is_truncated(
        {"finish_reason": "stop", "usage": {"completion_tokens": 5000}, "max_tokens": 8192}
    )


# --- _run_is_truncated -------------------------------------------------------


def test_run_is_truncated_reads_raw_json(tmp_path):
    _write_json(
        tmp_path / "qwen_run01.raw.json",
        {"finish_reason": "length", "usage": {"completion_tokens": 8192}, "max_tokens": 8192},
    )
    assert _run_is_truncated(tmp_path, "qwen", 1)


def test_run_is_not_truncated_when_raw_missing(tmp_path):
    assert not _run_is_truncated(tmp_path, "qwen", 99)


# --- _load_runs --------------------------------------------------------------


def test_load_runs_parses_types(tmp_path):
    csv_path = tmp_path / "runs.csv"
    _write_csv(
        csv_path,
        [
            {
                "arm": "naive",
                "agent": "qwen",
                "model": "qwen3-max",
                "run": "1",
                "classification": "report",
                "narrative_chars": "5000",
                "inventory_rows": "23",
                "cost_usd": "0.05",
                "wall_s": "120.0",
                "turns": "1",
            },
            {
                "arm": "optimised",
                "agent": "mistral",
                "model": "mistral-large",
                "run": "2",
                "classification": "no_report",
                "narrative_chars": "200",
                "inventory_rows": "None",
                "cost_usd": "0.01",
                "wall_s": "10.0",
                "turns": "3",
            },
        ],
        _FIELDS,
    )

    rows = _load_runs(csv_path)
    assert len(rows) == 2
    assert rows[0]["run"] == 1
    assert rows[0]["inventory_rows"] == 23
    assert rows[1]["inventory_rows"] is None
    assert rows[1]["turns"] == 3


# --- summarize_arms ----------------------------------------------------------


def test_summarize_arms_report_rate(tmp_path):
    naive_dir = tmp_path / "naive"
    optimised_dir = tmp_path / "optimised"
    naive_dir.mkdir()
    optimised_dir.mkdir()

    runs = [
        {
            "arm": "naive",
            "agent": "qwen",
            "model": "qwen3-max",
            "run": 1,
            "classification": "report",
            "narrative_chars": 5000,
            "inventory_rows": 20,
            "cost_usd": 0.10,
            "wall_s": 100.0,
            "turns": 1,
        },
        {
            "arm": "naive",
            "agent": "qwen",
            "model": "qwen3-max",
            "run": 2,
            "classification": "no_report",
            "narrative_chars": 100,
            "inventory_rows": 0,
            "cost_usd": 0.02,
            "wall_s": 20.0,
            "turns": 1,
        },
    ]

    summary = summarize_arms(runs, naive_dir, optimised_dir)
    assert len(summary) == 1
    row = summary[0]
    assert row["report_rate"] == pytest.approx(0.5)
    assert row["median_cost_usd"] == pytest.approx(0.06)
    assert row["n_runs"] == 2


def test_summarize_arms_truncation_from_raw(tmp_path):
    naive_dir = tmp_path / "naive"
    naive_dir.mkdir()
    _write_json(
        naive_dir / "qwen_run01.raw.json",
        {"finish_reason": "length", "usage": {"completion_tokens": 8192}, "max_tokens": 8192},
    )

    runs = [
        {
            "arm": "naive",
            "agent": "qwen",
            "model": "qwen3-max",
            "run": 1,
            "classification": "report",
            "narrative_chars": 5000,
            "inventory_rows": 20,
            "cost_usd": 0.10,
            "wall_s": 100.0,
            "turns": 1,
        },
    ]

    summary = summarize_arms(runs, naive_dir, tmp_path / "optimised")
    assert summary[0]["trunc_rate"] == pytest.approx(1.0)


# --- generate_latex ----------------------------------------------------------


def test_generate_latex_contains_required_structure():
    summary = [
        {
            "arm": "naive",
            "model": "qwen3-max-2026-01-23",
            "n_runs": 5,
            "report_rate": 0.8,
            "trunc_rate": 0.0,
            "median_turns": 1.0,
            "median_cost_usd": 0.05,
            "median_wall_s": 120.0,
        },
        {
            "arm": "optimised",
            "model": "qwen3-max-2026-01-23",
            "n_runs": 5,
            "report_rate": 1.0,
            "trunc_rate": 0.0,
            "median_turns": 2.5,
            "median_cost_usd": 0.20,
            "median_wall_s": 300.0,
        },
    ]
    latex = generate_latex(summary)
    assert "\\label{tab:exp2-arms}" in latex
    assert "Report (\\%)" in latex
    assert "Naive" in latex
    assert "Optimised" in latex


# --- main --------------------------------------------------------------------


def test_main_writes_output(tmp_path):
    naive_dir = tmp_path / "naive"
    optimised_dir = tmp_path / "optimised"
    naive_dir.mkdir()
    optimised_dir.mkdir()

    csv_path = tmp_path / "runs.csv"
    _write_csv(
        csv_path,
        [
            {
                "arm": "naive",
                "agent": "qwen",
                "model": "qwen3-max",
                "run": "1",
                "classification": "report",
                "narrative_chars": "5000",
                "inventory_rows": "23",
                "cost_usd": "0.05",
                "wall_s": "120.0",
                "turns": "1",
            },
        ],
        _FIELDS,
    )

    out = tmp_path / "tab_exp2_arms.tex"
    main(
        [
            "--input",
            str(csv_path),
            "--output",
            str(out),
            "--naive-dir",
            str(naive_dir),
            "--optimised-dir",
            str(optimised_dir),
        ]
    )

    content = out.read_text()
    assert "\\begin{longtable}" in content
    assert "\\label{tab:exp2-arms}" in content
