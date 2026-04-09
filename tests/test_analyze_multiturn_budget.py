"""Tests for aedist.analyze_multiturn_budget — token budget extrapolation."""

import json

from aedist.analyze_multiturn_budget import (
    extrapolate_to_n_turns,
    load_multiturn_results,
    per_turn_token_usage,
)


def test_per_turn_token_usage_extracts_assistant_turns():
    record = {
        "turns": [
            {"role": "user", "content": "hi", "turn": 0},
            {
                "role": "assistant",
                "content": "resp",
                "turn": 0,
                "usage": {"prompt_tokens": 100, "completion_tokens": 200},
            },
            {"role": "user", "content": "more", "turn": 1},
            {
                "role": "assistant",
                "content": "resp2",
                "turn": 1,
                "usage": {"prompt_tokens": 400, "completion_tokens": 300},
            },
        ]
    }
    result = per_turn_token_usage(record)
    assert len(result) == 2
    assert result[0] == {"turn": 0, "prompt_tokens": 100, "completion_tokens": 200}
    assert result[1] == {"turn": 1, "prompt_tokens": 400, "completion_tokens": 300}


def test_per_turn_token_usage_handles_missing_usage():
    record = {
        "turns": [
            {"role": "assistant", "content": "x", "turn": 0},
        ]
    }
    result = per_turn_token_usage(record)
    assert result[0]["prompt_tokens"] == 0
    assert result[0]["completion_tokens"] == 0


def test_extrapolate_linear_growth():
    """Linear extrapolation with constant growth rate."""
    per_turn = [
        {"turn": 0, "prompt_tokens": 100, "completion_tokens": 200},
        {"turn": 1, "prompt_tokens": 400, "completion_tokens": 200},
        {"turn": 2, "prompt_tokens": 700, "completion_tokens": 200},
        {"turn": 3, "prompt_tokens": 1000, "completion_tokens": 200},
    ]
    # Growth: 300, 300, 300 → avg 300
    # Last prompt at turn 3: 1000
    # Project to turn 9 (n_turns=10): 1000 + (9-3)*300 = 2800
    proj = extrapolate_to_n_turns(per_turn, n_turns=10, context_window=5000)
    assert proj["observed_turns"] == 4
    assert proj["avg_growth_per_turn"] == 300
    assert proj["projected_prompt_at_n"] == 2800
    assert proj["limit_80pct"] == 4000
    assert proj["overflow"] is False
    assert abs(proj["projected_pct"] - 56.0) < 0.1


def test_extrapolate_overflow():
    """Detects overflow when projection exceeds 80% of context window."""
    per_turn = [
        {"turn": 0, "prompt_tokens": 1000, "completion_tokens": 500},
        {"turn": 1, "prompt_tokens": 5000, "completion_tokens": 500},
        {"turn": 2, "prompt_tokens": 9000, "completion_tokens": 500},
        {"turn": 3, "prompt_tokens": 13000, "completion_tokens": 500},
    ]
    # Growth: 4000 avg. Last: 13000. Project to turn 9: 13000 + 6*4000 = 37000
    # Context 40000 → limit 32000. 37000 > 32000 → overflow
    proj = extrapolate_to_n_turns(per_turn, n_turns=10, context_window=40000)
    assert proj["overflow"] is True
    assert proj["projected_prompt_at_n"] == 37000


def test_extrapolate_single_turn():
    """Single turn: no growth data, returns last prompt as projection."""
    per_turn = [
        {"turn": 0, "prompt_tokens": 500, "completion_tokens": 200},
    ]
    proj = extrapolate_to_n_turns(per_turn, n_turns=10, context_window=100000)
    assert proj["observed_turns"] == 1
    assert proj["avg_growth_per_turn"] == 0
    assert proj["projected_prompt_at_n"] == 500
    assert proj["overflow"] is False


def test_extrapolate_zero_context_window():
    """Zero context window: no overflow possible, pct is 0."""
    per_turn = [
        {"turn": 0, "prompt_tokens": 100, "completion_tokens": 50},
        {"turn": 1, "prompt_tokens": 200, "completion_tokens": 50},
    ]
    proj = extrapolate_to_n_turns(per_turn, n_turns=10, context_window=0)
    assert proj["overflow"] is False
    assert proj["projected_pct"] == 0


def test_load_multiturn_results_skips_derived_files(tmp_path):
    """load_multiturn_results only loads model-reply files, not derived files."""
    record = {"turns": [{"role": "assistant", "content": "x", "turn": 0}]}
    # Model reply (should be loaded)
    (tmp_path / "model-run1.json").write_text(json.dumps(record))
    # Derived files (should be skipped)
    (tmp_path / "tavily_cache.json").write_text(json.dumps({"query": "test"}))
    (tmp_path / "self_consistency_summary.json").write_text(json.dumps({"kappa": 0.8}))
    (tmp_path / "model-run1.record.json").write_text(json.dumps({"f1": 0.5}))

    results = load_multiturn_results(tmp_path)
    assert len(results) == 1
    assert results[0] == record
