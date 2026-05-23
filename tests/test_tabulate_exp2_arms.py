"""Tests for aedist.tabulate_exp2_arms."""

import json

import pytest

from aedist.tabulate_exp2_arms import (
    _is_truncated,
    generate_exp2_arms_table,
    main,
    summarize_arm,
)


def _write_json(path, payload):
    path.write_text(json.dumps(payload))


def test_is_truncated_when_finish_reason_length():
    payload = {
        "finish_reason": "length",
        "usage": {"completion_tokens": 8000},
        "max_tokens": 8192,
    }
    assert _is_truncated(payload)


def test_is_truncated_when_completion_hits_max_tokens():
    payload = {
        "finish_reason": "stop",
        "usage": {"completion_tokens": 8192},
        "max_tokens": 8192,
    }
    assert _is_truncated(payload)


def test_is_not_truncated_when_completion_below_cap():
    payload = {
        "finish_reason": "stop",
        "usage": {"completion_tokens": 5000},
        "max_tokens": 8192,
    }
    assert not _is_truncated(payload)


def test_summarize_arm_uses_raw_truncation(tmp_path):
    arm_dir = tmp_path / "naive"
    arm_dir.mkdir()

    _write_json(
        arm_dir / "qwen_run01.raw.json",
        {
            "finish_reason": "length",
            "usage": {"completion_tokens": 8192},
            "max_tokens": 8192,
        },
    )
    _write_json(
        arm_dir / "qwen_run02.raw.json",
        {
            "finish_reason": "stop",
            "usage": {"completion_tokens": 4000},
            "max_tokens": 8192,
        },
    )

    rows = summarize_arm(
        [
            {
                "agent": "qwen",
                "run": 1,
                "model": "qwen3-max-2026-01-23",
                "classification": "report",
                "cost_usd": 0.10,
                "wall_s": 100.0,
            },
            {
                "agent": "qwen",
                "run": 2,
                "model": "qwen3-max-2026-01-23",
                "classification": "no_report",
                "cost_usd": 0.20,
                "wall_s": 200.0,
            },
        ],
        arm_dir,
        "Naive",
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["report_rate"] == 0.5
    assert row["trunc_rate"] == 0.5
    assert row["median_cost_usd"] == pytest.approx(0.15)
    assert row["median_wall_s"] == 150.0


def test_generate_exp2_arms_table_contains_expected_columns(tmp_path):
    naive_dir = tmp_path / "naive"
    optimized_dir = tmp_path / "optimized"
    naive_dir.mkdir()
    optimized_dir.mkdir()

    _write_json(
        naive_dir / "qwen_run01.raw.json",
        {
            "finish_reason": "length",
            "usage": {"completion_tokens": 8192},
            "max_tokens": 8192,
        },
    )
    _write_json(
        optimized_dir / "qwen_run01.raw.json",
        {
            "finish_reason": "stop",
            "usage": {"completion_tokens": 5000},
            "max_tokens": 8192,
        },
    )

    latex = generate_exp2_arms_table(
        [
            {
                "agent": "qwen",
                "run": 1,
                "model": "qwen3-max-2026-01-23",
                "classification": "report",
                "cost_usd": 0.11,
                "wall_s": 111.0,
            }
        ],
        [
            {
                "agent": "qwen",
                "run": 1,
                "model": "qwen3-max-2026-01-23",
                "classification": "report",
                "total_cost_usd": 0.22,
                "wall_s": 222.0,
                "turns": 2,
            }
        ],
        naive_dir,
        optimized_dir,
    )

    assert "\\label{tab:exp2-arms}" in latex
    assert "Report (\\%)" in latex
    assert "Truncated (\\%)" in latex
    assert "Naive" in latex
    assert "Optimized" in latex


def test_main_writes_output(tmp_path):
    naive_dir = tmp_path / "naive"
    optimized_dir = tmp_path / "optimized"
    naive_dir.mkdir()
    optimized_dir.mkdir()

    _write_json(
        naive_dir / "qwen_run01.raw.json",
        {
            "finish_reason": "length",
            "usage": {"completion_tokens": 8192},
            "max_tokens": 8192,
        },
    )
    _write_json(
        optimized_dir / "qwen_run01.raw.json",
        {
            "finish_reason": "stop",
            "usage": {"completion_tokens": 6000},
            "max_tokens": 8192,
        },
    )

    naive_summary = tmp_path / "naive_summary.json"
    optimized_summary = tmp_path / "optimized_summary.json"
    output_file = tmp_path / "generated" / "tab_exp2_arms.tex"

    _write_json(
        naive_summary,
        [
            {
                "agent": "qwen",
                "run": 1,
                "model": "qwen3-max-2026-01-23",
                "classification": "report",
                "cost_usd": 0.11,
                "wall_s": 111.0,
            }
        ],
    )
    _write_json(
        optimized_summary,
        [
            {
                "agent": "qwen",
                "run": 1,
                "model": "qwen3-max-2026-01-23",
                "classification": "report",
                "total_cost_usd": 0.22,
                "wall_s": 222.0,
                "turns": 2,
            }
        ],
    )

    main(
        [
            "--output",
            str(output_file),
            "--naive-summary",
            str(naive_summary),
            "--optimized-summary",
            str(optimized_summary),
            "--naive-dir",
            str(naive_dir),
            "--optimized-dir",
            str(optimized_dir),
        ]
    )

    content = output_file.read_text()
    assert "\\begin{longtable}" in content
    assert "\\label{tab:exp2-arms}" in content
