"""Tests for scripts/audit_arm34_cache.py (ticket 0369)."""

import json
from pathlib import Path

from scripts.audit_arm34_cache import aggregate, collect_rows, usage_from_raw


def test_usage_anthropic_shape():
    u = usage_from_raw({"usage": {"input_tokens": 100, "cache_read_input_tokens": 30,
                                  "cache_creation_input_tokens": 20, "output_tokens": 5}})
    assert u == {"input": 100, "cache_read": 30, "cache_write": 20, "output": 5}


def test_usage_openai_shape():
    u = usage_from_raw({"usage": {"input_tokens": 100,
                                  "input_tokens_details": {"cached_tokens": 40},
                                  "output_tokens": 5}})
    assert u["cache_read"] == 40


def test_usage_mistral_shape():
    u = usage_from_raw({"usage": {"prompt_tokens": 70, "completion_tokens": 7}})
    assert u == {"input": 70, "cache_read": 0, "cache_write": 0, "output": 7}


def test_usage_missing_returns_none():
    assert usage_from_raw({}) is None
    assert usage_from_raw({"usage": {"weird": 1}}) is None


def test_collect_and_aggregate(tmp_path: Path):
    arm4 = tmp_path / "arm4" / "run01" / "anthropic_run01"
    arm4.mkdir(parents=True)
    (arm4 / "anthropic_turn_01.raw.json").write_text(json.dumps(
        {"usage": {"input_tokens": 1000, "cache_read_input_tokens": 0,
                   "cache_creation_input_tokens": 0, "output_tokens": 10}}) + "\n")
    (arm4 / "anthropic_turn_02.raw.json").write_text(json.dumps(
        {"usage": {"input_tokens": 100, "cache_read_input_tokens": 900,
                   "cache_creation_input_tokens": 0, "output_tokens": 10}}) + "\n")
    arm3 = tmp_path / "arm3" / "run01"
    arm3.mkdir(parents=True)
    (arm3 / "anthropic-direct-m-run1.json").write_text(json.dumps(
        {"response": {"usage": {"input_tokens": 500, "cache_read_input_tokens": 0,
                                "cache_creation_input_tokens": 0,
                                "output_tokens": 1}}}) + "\n")

    rows = collect_rows(tmp_path / "arm3", tmp_path / "arm4")
    assert len(rows) == 3
    agg = {(a["arm"], a["agent"]): a for a in aggregate(rows)}
    assert agg[(4, "anthropic")]["n_calls"] == 2
    assert agg[(4, "anthropic")]["cache_hit_rate"] == round(900 / 2000, 4)
    assert agg[(3, "anthropic")]["input_tokens"] == 500
