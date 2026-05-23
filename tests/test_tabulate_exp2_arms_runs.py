"""Tests for aedist.tabulate_exp2_arms_runs."""

import csv
import json

from aedist.tabulate_exp2_arms_runs import (
    _count_md_table_rows,
    _load_arm_runs,
    build_runs_csv,
    main,
)


def _write_json(path, payload):
    path.write_text(json.dumps(payload))


def _write_md(path, content):
    path.write_text(content)


# --- _count_md_table_rows ----------------------------------------------------


def test_count_md_table_rows_basic(tmp_path):
    md = tmp_path / "report.md"
    _write_md(
        md,
        "| Plant | Capacity |\n| --- | --- |\n| Vinh Tan 1 | 1200 |\n| Vinh Tan 2 | 600 |\n",
    )
    assert _count_md_table_rows(md) == 2


def test_count_md_table_rows_missing_file(tmp_path):
    assert _count_md_table_rows(tmp_path / "missing.md") == 0


def test_count_md_table_rows_no_table(tmp_path):
    md = tmp_path / "report.md"
    _write_md(md, "This report has no tables.\nJust prose.\n")
    assert _count_md_table_rows(md) == 0


# --- _load_arm_runs ----------------------------------------------------------


def test_load_arm_runs_naive_uses_md_for_inventory_rows(tmp_path):
    _write_json(
        tmp_path / "anthropic_run01.json",
        {
            "agent": "anthropic",
            "run": 1,
            "model": "claude-opus-4-6",
            "classification": "report",
            "narrative_chars": 14000,
            "wall_s": 300.0,
            "cost_usd": 0.90,
            "classifier_cost_usd": 0.0,
        },
    )
    _write_md(
        tmp_path / "anthropic_run01.md",
        "| Plant | Capacity |\n| --- | --- |\n| A | 1 |\n| B | 2 |\n| C | 3 |\n",
    )

    rows = _load_arm_runs(tmp_path, "naive")
    assert len(rows) == 1
    row = rows[0]
    assert row["arm"] == "naive"
    assert row["inventory_rows"] == 3
    assert row["turns"] == 1


def test_load_arm_runs_optimised_uses_json_for_inventory_rows(tmp_path):
    _write_json(
        tmp_path / "mistral_run02.json",
        {
            "agent": "mistral",
            "run": 2,
            "model": "mistral-large-2512",
            "arm": "optimised",
            "classification": "report",
            "narrative_chars": 18000,
            "inventory_rows": 50,
            "turns": 2,
            "wall_s": 160.0,
            "total_cost_usd": 0.29,
            "classifier_cost_usd": 0.0,
        },
    )

    rows = _load_arm_runs(tmp_path, "optimised")
    assert len(rows) == 1
    row = rows[0]
    assert row["inventory_rows"] == 50
    assert row["turns"] == 2


def test_load_arm_runs_skips_summary_json(tmp_path):
    _write_json(tmp_path / "summary.json", [{"agent": "x"}])
    _write_json(tmp_path / "summary_20260522T2342Z.json", [{"agent": "y"}])
    rows = _load_arm_runs(tmp_path, "naive")
    assert rows == []


def test_load_arm_runs_uses_brerun1_not_phase_b_full(tmp_path):
    """Canonical optimised dir is sota_exp2_brerun1, not sota_exp2_phase_b_full."""
    from aedist.tabulate_exp2_arms_runs import _DEFAULT_OPTIMISED_DIR

    assert "brerun1" in str(_DEFAULT_OPTIMISED_DIR)
    assert "phase_b_full" not in str(_DEFAULT_OPTIMISED_DIR)


# --- build_runs_csv ----------------------------------------------------------


def test_build_runs_csv_both_arms(tmp_path):
    naive_dir = tmp_path / "naive"
    optimised_dir = tmp_path / "optimised"
    naive_dir.mkdir()
    optimised_dir.mkdir()

    _write_json(
        naive_dir / "qwen_run01.json",
        {
            "agent": "qwen",
            "run": 1,
            "model": "qwen3-max",
            "classification": "report",
            "narrative_chars": 20000,
            "wall_s": 200.0,
            "cost_usd": 0.04,
        },
    )
    _write_md(naive_dir / "qwen_run01.md", "| A | B |\n| - | - |\n| x | y |\n")

    _write_json(
        optimised_dir / "qwen_run01.json",
        {
            "agent": "qwen",
            "run": 1,
            "model": "qwen3-max",
            "arm": "optimised",
            "classification": "report",
            "narrative_chars": 8000,
            "inventory_rows": 31,
            "turns": 3,
            "wall_s": 180.0,
            "total_cost_usd": 0.19,
        },
    )

    rows = build_runs_csv(naive_dir, optimised_dir)
    assert len(rows) == 2
    arms = {r["arm"] for r in rows}
    assert arms == {"naive", "optimised"}
    naive_row = next(r for r in rows if r["arm"] == "naive")
    assert naive_row["inventory_rows"] == 1
    optimised_row = next(r for r in rows if r["arm"] == "optimised")
    assert optimised_row["inventory_rows"] == 31


# --- main --------------------------------------------------------------------


def test_main_writes_csv(tmp_path):
    naive_dir = tmp_path / "naive"
    optimised_dir = tmp_path / "optimised"
    naive_dir.mkdir()
    optimised_dir.mkdir()

    _write_json(
        naive_dir / "anthropic_run01.json",
        {
            "agent": "anthropic",
            "run": 1,
            "model": "claude-opus-4-6",
            "classification": "report",
            "narrative_chars": 14000,
            "wall_s": 300.0,
            "cost_usd": 0.90,
        },
    )
    _write_md(naive_dir / "anthropic_run01.md", "| P | C |\n| - | - |\n| A | 1 |\n")

    out = tmp_path / "runs.csv"
    main(
        [
            "--output",
            str(out),
            "--naive-dir",
            str(naive_dir),
            "--optimised-dir",
            str(optimised_dir),
        ]
    )

    with out.open() as fh:
        rows = list(csv.DictReader(fh))

    assert len(rows) == 1
    assert rows[0]["arm"] == "naive"
    assert rows[0]["inventory_rows"] == "1"
    assert rows[0]["classification"] == "report"
