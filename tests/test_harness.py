"""Tests for aedist.harness — shared query utilities."""

from pathlib import Path

from aedist.harness import (
    BudgetTracker,
    compute_cost,
    model_metadata,
    output_filename,
    should_skip,
)


def test_compute_cost_basic():
    """Cost computed from token counts and pricing."""
    usage = {"prompt_tokens": 1000, "completion_tokens": 500}
    model = {"price_per_mtok_in": 2.0, "price_per_mtok_out": 6.0}
    cost = compute_cost(usage, model)
    # (1000 * 2.0 + 500 * 6.0) / 1_000_000 = 5000 / 1_000_000 = 0.005
    assert abs(cost - 0.005) < 1e-9


def test_compute_cost_zero_tokens():
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    model = {"price_per_mtok_in": 2.0, "price_per_mtok_out": 6.0}
    assert compute_cost(usage, model) == 0.0


def test_model_metadata_extracts_keys():
    model = {
        "id": "test/m",
        "name": "Test",
        "size_class": "frontier",
        "country": "US",
        "architecture": "dense",
        "provider": "Acme",
        "context_window": 8000,
        "price_per_mtok_in": 1.0,
    }
    meta = model_metadata(model)
    assert meta == {
        "size_class": "frontier",
        "country": "US",
        "architecture": "dense",
        "provider": "Acme",
        "context_window": 8000,
    }


def test_output_filename():
    assert output_filename("anthropic/claude-sonnet-4.6", 2) == "claude-sonnet-4.6-run2.json"


def test_budget_tracker_no_budget():
    bt = BudgetTracker(budget_usd=None)
    bt.add(1000.0)
    assert not bt.exceeded
    assert bt.check_or_warn()


def test_budget_tracker_exceeded():
    bt = BudgetTracker(budget_usd=1.0)
    bt.add(0.5)
    assert not bt.exceeded
    bt.add(0.6)
    assert bt.exceeded
    assert not bt.check_or_warn()


def test_should_skip_false(tmp_path):
    assert not should_skip(tmp_path, "test/model", 1)


def test_should_skip_true(tmp_path):
    (tmp_path / "model-run1.json").write_text("{}")
    assert should_skip(tmp_path, "test/model", 1)
