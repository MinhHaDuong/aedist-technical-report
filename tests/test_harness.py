"""Tests for aedist.harness — shared query utilities."""

from aedist.harness import (
    BudgetTracker,
    build_api_kwargs,
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


def test_estimate_tokens():
    from aedist.harness import estimate_tokens

    # 20 chars / 4 chars_per_token = 5
    assert estimate_tokens("a" * 20) == 5
    assert estimate_tokens("") == 0


def test_estimate_messages_tokens():
    from aedist.harness import estimate_messages_tokens

    messages = [
        {"role": "user", "content": "a" * 40},  # 10 tokens
        {"role": "assistant", "content": "b" * 80},  # 20 tokens
    ]
    assert estimate_messages_tokens(messages) == 30


def test_estimate_messages_tokens_missing_content():
    from aedist.harness import estimate_messages_tokens

    messages = [{"role": "user"}]
    assert estimate_messages_tokens(messages) == 0


def test_iter_model_replies_filters_derived_files(tmp_path):
    """iter_model_replies returns only canonical model-reply files."""
    from aedist.harness import iter_model_replies

    # Model replies (should be returned)
    (tmp_path / "deepseek-v3.2-run1.json").write_text("{}")
    (tmp_path / "deepseek-v3.2-run2.json").write_text("{}")
    (tmp_path / "padme-qwen3.5-122b-run1.json").write_text("{}")

    # Derived files (should be excluded)
    (tmp_path / "deepseek-v3.2-run1.record.json").write_text("{}")
    (tmp_path / "deepseek-v3.2-run1.eval.json").write_text("{}")
    (tmp_path / "tavily_cache.json").write_text("{}")
    (tmp_path / "self_consistency_summary.json").write_text("{}")
    (tmp_path / "deepseek-v3.2-run1_summary.json").write_text("{}")

    result = [f.name for f in iter_model_replies(tmp_path)]
    assert result == [
        "deepseek-v3.2-run1.json",
        "deepseek-v3.2-run2.json",
        "padme-qwen3.5-122b-run1.json",
    ]


# ---------------------------------------------------------------------------
# build_api_kwargs — capability-driven API parameter construction
# ---------------------------------------------------------------------------


def test_no_capabilities_unchanged():
    """Models without flags get standard params (backward compat)."""
    model = {"id": "test/plain", "name": "Plain"}
    kwargs = build_api_kwargs(model, max_tokens=4096, temperature=0.7)
    assert kwargs == {"max_tokens": 4096, "temperature": 0.7}
    assert "extra_body" not in kwargs


def test_reasoning_model_skips_temperature():
    """Models with reasoning=true don't get temperature param."""
    model = {"id": "openai/o3", "reasoning": True}
    kwargs = build_api_kwargs(model, max_tokens=4096, temperature=0.7)
    assert "temperature" not in kwargs
    assert kwargs["max_tokens"] == 4096


def test_web_search_model_gets_plugin():
    """Models with web_search=true get plugins in extra_body."""
    model = {"id": "test/web", "web_search": True}
    kwargs = build_api_kwargs(model, max_tokens=4096, temperature=0.7)
    assert kwargs["temperature"] == 0.7
    assert kwargs["extra_body"] == {"plugins": [{"id": "web"}]}


def test_both_capabilities():
    """Model with both reasoning and web_search gets correct params."""
    model = {"id": "test/both", "reasoning": True, "web_search": True}
    kwargs = build_api_kwargs(model, max_tokens=4096, temperature=0.0)
    assert "temperature" not in kwargs
    assert kwargs["max_tokens"] == 4096
    assert kwargs["extra_body"] == {"plugins": [{"id": "web"}]}


def test_web_search_false_no_plugin():
    """Explicit web_search=false produces no extra_body."""
    model = {"id": "test/no-web", "web_search": False}
    kwargs = build_api_kwargs(model, max_tokens=4096, temperature=0.5)
    assert "extra_body" not in kwargs


def test_reasoning_false_keeps_temperature():
    """Explicit reasoning=false keeps temperature."""
    model = {"id": "test/no-reason", "reasoning": False}
    kwargs = build_api_kwargs(model, max_tokens=4096, temperature=0.3)
    assert kwargs["temperature"] == 0.3
