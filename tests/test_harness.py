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
            max_retries=1,
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
    assert "tools" not in kwargs


def test_web_search_model_gets_plugin():
    """Models with web_search=true get plugins in extra_body."""
    model = {"id": "test/web", "web_search": True}
    kwargs = build_api_kwargs(model, max_tokens=4096, temperature=0.7, enable_web_search=True)
    assert kwargs["temperature"] == 0.7
    assert kwargs["tools"][0]["type"] == "openrouter:web_search"
    assert kwargs["tools"][0]["parameters"]["max_total_results"] == 37


def test_web_search_with_temperature():
    """Models with web_search get both temperature and tools."""
    model = {"id": "test/both", "web_search": True}
    kwargs = build_api_kwargs(model, max_tokens=4096, temperature=0.0, enable_web_search=True)
    assert kwargs["temperature"] == 0.0
    assert kwargs["max_tokens"] == 4096
    assert kwargs["tools"][0]["type"] == "openrouter:web_search"
    assert kwargs["tools"][0]["parameters"]["max_total_results"] == 37


def test_web_search_false_no_plugin():
    """Explicit web_search=false produces no extra_body."""
    model = {"id": "test/no-web", "web_search": False}
    kwargs = build_api_kwargs(model, max_tokens=4096, temperature=0.5)
    assert "tools" not in kwargs


def test_no_think_sets_think_false():
    """no_think=True parameter adds think:false to extra_body."""
    model = {"id": "qwen3.6:35b"}
    kwargs = build_api_kwargs(model, temperature=0.0, no_think=True)
    assert kwargs.get("extra_body", {}).get("think") is False


def test_no_think_false_no_extra_body():
    """no_think absent or False does not add think key."""
    model = {"id": "some-model"}
    kwargs = build_api_kwargs(model, temperature=0.0)
    assert "think" not in kwargs.get("extra_body", {})


def test_reasoning_effort_per_model():
    """model.reasoning_effort surfaces as extra_body.reasoning.effort (ticket 0175)."""
    model = {"id": "openai/gpt-oss-120b", "reasoning_effort": "minimal"}
    kwargs = build_api_kwargs(model, temperature=0.0)
    assert kwargs["extra_body"]["reasoning"] == {"effort": "minimal"}


def test_reasoning_effort_absent_no_extra():
    """No reasoning_effort on the model leaves extra_body without a reasoning key."""
    model = {"id": "openai/gpt-5.5"}
    kwargs = build_api_kwargs(model, temperature=0.0)
    assert "reasoning" not in kwargs.get("extra_body", {})


# ---------------------------------------------------------------------------
# query_model — Ollama-branch wire-level plumbing (ticket 0139 regression)
# ---------------------------------------------------------------------------
#
# query_model dispatched OpenRouter-shape api_kwargs to query_ollama_native
# without translating them to Ollama's options payload. Result: temperature,
# seed, max_tokens, and no_think were silently dropped at the wire for any
# Ollama model_id (no slash). Tests below patch httpx.post and assert on
# the JSON body actually sent — mocking query_model itself would miss the
# bug, mocking query_ollama_native would miss the dispatcher translation.


def _make_ollama_http_mock(monkeypatch):
    """Patch httpx.post (imported lazily inside query_ollama_native) and capture call args."""
    from unittest.mock import MagicMock

    import httpx

    fake_response = MagicMock()
    fake_response.raise_for_status = MagicMock()
    fake_response.json = MagicMock(
        return_value={
            "message": {"content": "ok", "thinking": ""},
            "done_reason": "stop",
            "prompt_eval_count": 1,
            "eval_count": 1,
        }
    )
    mock_post = MagicMock(return_value=fake_response)
    monkeypatch.setattr(httpx, "post", mock_post)
    return mock_post


def test_query_model_ollama_plumbs_jobspec_params_to_options(monkeypatch):
    """JobSpec-declared params land in the Ollama options payload at the wire (0139)."""
    from aedist.harness import build_api_kwargs, query_model

    mock_post = _make_ollama_http_mock(monkeypatch)

    # Realistic flow: build_api_kwargs(no_think=True, seed=42, max_tokens=4096,
    # temperature=0.0) — exactly what sweep_regimes_direct_local declares.
    model = {"id": "qwen3.6:30b", "name": "qwen3.6:30b"}
    api_kwargs = build_api_kwargs(
        model,
        temperature=0.0,
        seed=42,
        max_tokens=4096,
        no_think=True,
    )
    # Dispatch through query_model with an Ollama-shaped model_id (no slash).
    query_model(
        client=None,  # unused on Ollama branch
        model_id="qwen3.6:30b",
        messages=[{"role": "user", "content": "hi"}],
        num_ctx=16384,
        ollama_base_url="http://localhost:11434/v1",
        **api_kwargs,
    )

    assert mock_post.call_count == 1
    sent = mock_post.call_args.kwargs["json"]
    assert sent["model"] == "qwen3.6:30b"
    options = sent["options"]
    assert options["num_ctx"] == 16384
    assert options["num_predict"] == 4096
    assert options["temperature"] == 0.0
    assert options["seed"] == 42
    assert options["think"] is False


def test_query_model_ollama_no_think_false_omits_think(monkeypatch):
    """no_think=False (build_api_kwargs default) leaves think absent — proves we don't hardcode."""
    from aedist.harness import build_api_kwargs, query_model

    mock_post = _make_ollama_http_mock(monkeypatch)

    model = {"id": "qwen3.6:30b", "name": "qwen3.6:30b"}
    api_kwargs = build_api_kwargs(
        model,
        temperature=0.7,
        seed=42,
        no_think=False,  # explicit default — extra_body should be absent
    )
    query_model(
        client=None,
        model_id="qwen3.6:30b",
        messages=[{"role": "user", "content": "hi"}],
        num_ctx=32768,
        **api_kwargs,
    )

    options = mock_post.call_args.kwargs["json"]["options"]
    assert "think" not in options
    assert options["temperature"] == 0.7
    assert options["seed"] == 42
    # max_tokens absent → num_predict absent
    assert "num_predict" not in options


def test_query_model_ollama_drops_openrouter_only_keys(monkeypatch):
    """provider_order + reasoning_effort + tools are OpenRouter-only — must not reach Ollama wire."""
    from aedist.harness import build_api_kwargs, query_model

    mock_post = _make_ollama_http_mock(monkeypatch)

    # A pathological config: OpenRouter-only knobs on an Ollama model.
    # Should be silently dropped (no Ollama analogue), not error.
    model = {
        "id": "qwen3.6:30b",
        "name": "qwen3.6:30b",
        "web_search": True,
        "reasoning_effort": "minimal",
    }
    api_kwargs = build_api_kwargs(
        model,
        temperature=0.0,
        seed=42,
        provider_order=["DeepSeek"],
        enable_web_search=True,
        no_think=True,
    )
    query_model(
        client=None,
        model_id="qwen3.6:30b",
        messages=[{"role": "user", "content": "hi"}],
        **api_kwargs,
    )

    sent = mock_post.call_args.kwargs["json"]
    # Ollama JSON body has model/messages/options/stream — nothing else.
    assert set(sent.keys()) == {"model", "messages", "options", "stream"}
    options = sent["options"]
    assert options["temperature"] == 0.0
    assert options["seed"] == 42
    assert options["think"] is False
    # OpenRouter-only knobs not present anywhere in the wire payload.
    assert "provider" not in options
    assert "reasoning" not in options
    assert "tools" not in sent


def test_query_model_ollama_local_sweep_jobspec_end_to_end(monkeypatch, tmp_path):
    """End-to-end: build_api_kwargs from a `sweep_regimes_direct_local`-shaped JobSpec
    reaches the Ollama wire with no_think honoured (0139)."""
    from aedist.harness import build_api_kwargs, query_model
    from aedist.schema import JobSpec, Method, WorkerPool

    mock_post = _make_ollama_http_mock(monkeypatch)

    # Shape mirrors sweep_regimes_direct_local in experiments.toml:
    # temperature=0.0, seed=42, no_think=true, max_tokens set, num_ctx set.
    job = JobSpec(
        models_file=str(tmp_path / "models.yaml"),
        mode=Method.SINGLE,
        prompt=str(tmp_path / "prompt.txt"),
        output_dir=str(tmp_path / "out"),
        worker_pool=WorkerPool.PADME,
        run_number=1,
        temperature=0.0,
        seed=42,
        max_tokens=4096,
        num_ctx=16384,
        no_think=True,
    )
    model_entry = {"id": "qwen3.6:30b", "name": "qwen3.6:30b"}
    api_kwargs = build_api_kwargs(
        model_entry,
        temperature=job.temperature,
        max_tokens=job.max_tokens,
        seed=job.seed,
        provider_order=job.provider_order,
        enable_web_search=job.web_search,
        no_think=job.no_think,
    )
    query_model(
        client=None,
        model_id=model_entry["name"],
        messages=[{"role": "user", "content": "test"}],
        num_ctx=job.num_ctx,
        ollama_base_url="http://localhost:11434/v1",
        **api_kwargs,
    )

    options = mock_post.call_args.kwargs["json"]["options"]
    assert options["temperature"] == 0.0
    assert options["seed"] == 42
    assert options["num_predict"] == 4096
    assert options["num_ctx"] == 16384
    assert options["think"] is False, (
        "no_think=true on local sweep must reach the Ollama wire — "
        "regression for ticket 0139 silent-drop"
    )


# ---------------------------------------------------------------------------
# query_single_turn timeout propagation (ticket 0183)
# ---------------------------------------------------------------------------


def test_query_single_turn_forwards_timeout_kwarg():
    """A ``timeout=`` kwarg given to query_single_turn reaches the OpenAI call.

    Worker.execute() injects ``api_kwargs["timeout"] = job.timeout_seconds`` so
    that httpx can interrupt wedged network reads. This test pins the contract:
    if the kwarg silently disappears on the way down, the wedge-fix is dead.
    """
    from unittest.mock import MagicMock

    from aedist.harness import query_single_turn

    client = MagicMock()
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content="ok"), finish_reason="stop")]
    response.usage = MagicMock(prompt_tokens=1, completion_tokens=1)
    client.chat.completions.create.return_value = response

    query_single_turn(client, "test/m", [{"role": "user", "content": "hi"}], timeout=42.0)
    call_kwargs = client.chat.completions.create.call_args.kwargs
    assert call_kwargs["timeout"] == 42.0


def test_query_single_turn_surfaces_api_timeout_error():
    """APITimeoutError from the OpenAI client propagates unwrapped to the caller.

    The worker's exception handler relies on this: an unswallowed timeout moves
    the job from running/ to failed/ and frees the worker for the next job.
    Wrapping or hiding the exception would re-create the wedge this ticket
    fixes.
    """
    from unittest.mock import MagicMock

    import httpx
    import openai
    import pytest

    from aedist.harness import query_single_turn

    client = MagicMock()
    request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    client.chat.completions.create.side_effect = openai.APITimeoutError(request)

    with pytest.raises(openai.APITimeoutError):
        query_single_turn(
            client,
            "test/m",
            [{"role": "user", "content": "hi"}],
            timeout=1.0,
        )


def test_query_single_turn_preserves_reasoning_tokens():
    """``usage`` dict round-trips ``completion_tokens_details.reasoning_tokens``.

    OpenRouter populates this field for reasoning-capable models (gpt-oss-*,
    qwen3-max-thinking, deepseek-v4-pro, etc.). The harness must hand the
    full dict to the worker so Annex A / records_to_metrics can surface
    actual reasoning intensity rather than relying on registry metadata.
    Ticket 0195.
    """
    from unittest.mock import MagicMock

    from aedist.harness import query_single_turn

    client = MagicMock()
    usage = MagicMock()
    usage.model_dump.return_value = {
        "prompt_tokens": 88,
        "completion_tokens": 159,
        "completion_tokens_details": {"reasoning_tokens": 94, "audio_tokens": 0},
        "prompt_tokens_details": {"cached_tokens": 0},
    }
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content="ok"), finish_reason="stop")]
    response.usage = usage
    client.chat.completions.create.return_value = response

    result = query_single_turn(client, "test/m", [{"role": "user", "content": "hi"}])

    assert result["usage"]["prompt_tokens"] == 88
    assert result["usage"]["completion_tokens"] == 159
    assert result["usage"]["completion_tokens_details"]["reasoning_tokens"] == 94
    assert result["usage"]["prompt_tokens_details"]["cached_tokens"] == 0


def test_query_single_turn_handles_missing_usage():
    """If the provider returns no usage block, return ``{}`` rather than crash."""
    from unittest.mock import MagicMock

    from aedist.harness import query_single_turn

    client = MagicMock()
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content="ok"), finish_reason="stop")]
    response.usage = None
    client.chat.completions.create.return_value = response

    result = query_single_turn(client, "test/m", [{"role": "user", "content": "hi"}])
    assert result["usage"] == {}


def test_query_single_turn_raises_on_null_content():
    """query_single_turn raises RuntimeError when content is None (ticket 0217).

    Providers like deepseek-v4-pro can return HTTP 200 with message.content=None.
    This must not silently propagate to callers — a RuntimeError with the model
    ID is raised immediately so callers get a diagnostic, not an AttributeError
    or corrupt data.
    """
    from unittest.mock import MagicMock

    import pytest

    from aedist.harness import query_single_turn

    client = MagicMock()
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=None), finish_reason="stop")]
    response.usage = MagicMock(model_dump=MagicMock(return_value={}))
    client.chat.completions.create.return_value = response

    with pytest.raises(RuntimeError, match="null-content-model"):
        query_single_turn(client, "null-content-model", [{"role": "user", "content": "hi"}])


def test_make_client_default_sets_max_retries():
    """make_client() (OpenRouter default) pins max_retries=1 on the OpenAI client."""
    import os
    from unittest.mock import patch

    with (
        patch("aedist.harness.OpenAI") as mock_cls,
        patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}),
    ):
        from aedist.harness import make_client

        make_client()
        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["max_retries"] == 1
        assert call_kwargs["base_url"] == "https://openrouter.ai/api/v1"
