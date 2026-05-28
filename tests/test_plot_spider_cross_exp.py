"""Tests for aedist.plot_spider_cross_exp — model-slug canonicalisation + aggregation."""

from aedist.plot_quality_spider_exp1 import SPIDER_AXES
from aedist.plot_spider_cross_exp import (
    _aggregate_condition,
    _canonical_model,
    _normalize_model_slug,
)


def test_normalize_model_slug_lowercases_and_dashes() -> None:
    assert _normalize_model_slug("GPT-5.5") == "gpt-5-5"
    assert _normalize_model_slug("Claude.Opus") == "claude-opus"


def test_canonical_model_matches_by_prefix() -> None:
    assert _canonical_model("claude-opus-4-6") == "claude-opus"
    assert _canonical_model("gpt-5.5-2026") == "gpt-5.5"
    assert _canonical_model("mistral-large-2512") == "mistral-large"


def test_canonical_model_unknown_is_none() -> None:
    assert _canonical_model("llama-3") is None


def test_aggregate_condition_medians_for_known_models_only() -> None:
    axis = SPIDER_AXES[0]
    rows = [
        {"model": "gpt-5.5-2026", axis: "0.4"},
        {"model": "gpt-5.5-2026", axis: "0.6"},
        {"model": "unknown-model", axis: "0.9"},  # ignored
    ]
    result = _aggregate_condition(rows)
    assert set(result) == {"gpt-5.5"}
    assert result["gpt-5.5"][axis] == 0.5
