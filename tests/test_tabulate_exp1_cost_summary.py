"""Tests for aedist.tabulate_exp1_cost_summary."""

from aedist.tabulate_exp1_cost_summary import aggregate_per_model, generate_table_tex


def test_exp1_cost_summary_includes_wall_time_column():
    tex = generate_table_tex(
        [
            {
                "model": "x/m",
                "n_ok": 5,
                "n_refused": 0,
                "n_other": 0,
                "tokens_in_total": 1000,
                "tokens_out_total": 500,
                "cost_usd_total": 0.01,
                "median_wall_s": 12.3,
            }
        ]
    )

    assert "wall (s)" in tex
    assert "12.3" in tex
    assert "\\textbf{Total}" in tex
    assert "& --- \\\\" in tex


def test_aggregate_per_model_uses_median_wall_time():
    records = [
        {
            "result_file": "experiments/outputs/ablation/direct/p1_base/qwen/run01.json",
            "method_params": {"model": "qwen/test"},
            "resource_use": {"tokens_in": 10, "tokens_out": 20, "cost_usd": 0.1, "wall_s": 10},
            "result_summary": {"status": "ok"},
        },
        {
            "result_file": "experiments/outputs/ablation/direct/p1_base/qwen/run02.json",
            "method_params": {"model": "qwen/test"},
            "resource_use": {"tokens_in": 11, "tokens_out": 21, "cost_usd": 0.2, "wall_s": 100},
            "result_summary": {"status": "ok"},
        },
        {
            "result_file": "experiments/outputs/ablation/direct/p1_base/qwen/run03.json",
            "method_params": {"model": "qwen/test"},
            "resource_use": {"tokens_in": 12, "tokens_out": 22, "cost_usd": 0.3, "wall_s": 1000},
            "result_summary": {"status": "ok"},
        },
    ]

    rows = aggregate_per_model(records)
    assert len(rows) == 1
    assert rows[0]["median_wall_s"] == 100


def test_aggregate_per_model_ignores_nonstring_result_file():
    rows = aggregate_per_model(
        [
            {
                "result_file": None,
                "method_params": {"model": "qwen/test"},
                "resource_use": {"tokens_in": 10, "tokens_out": 20, "cost_usd": 0.1, "wall_s": 10},
                "result_summary": {"status": "ok"},
            }
        ]
    )

    assert rows == []
