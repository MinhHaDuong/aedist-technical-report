"""Tests for aedist.harness — shared query utilities."""


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


def test_output_filename_with_prefix():
    assert output_filename("qwen3.5:122b", 1, prefix="padme") == "padme-qwen3.5-122b-run1.json"


def test_output_filename_colon_replaced():
    assert output_filename("mistral-small3.2", 3) == "mistral-small3.2-run3.json"


def test_should_skip_with_prefix(tmp_path):
    (tmp_path / "padme-qwen3.5-9b-run1.json").write_text("{}")
    assert should_skip(tmp_path, "qwen3.5:9b", 1, prefix="padme")
    assert not should_skip(tmp_path, "qwen3.5:9b", 1)  # no prefix → different file


def test_compute_cost_missing_pricing():
    """Models with no pricing fields (e.g. local Ollama) yield cost 0."""
    usage = {"prompt_tokens": 1000, "completion_tokens": 500}
    model = {"id": "qwen3.5:9b", "name": "Qwen local"}
    assert compute_cost(usage, model) == 0.0


def test_make_client_custom_base_url():
    """make_client with base_url doesn't require OPENROUTER_API_KEY."""
    from unittest.mock import patch
    with patch("aedist.harness.OpenAI") as mock_cls:
        from aedist.harness import make_client
        make_client(base_url="http://localhost:11434/v1")
        mock_cls.assert_called_once_with(
            base_url="http://localhost:11434/v1",
            api_key="ollama",
        )
