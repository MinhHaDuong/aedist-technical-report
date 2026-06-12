"""Unit tests for the Anthropic Claude adapter (ticket 0167).

Pure unit tests — no subprocess, no network, no SDK call. Belong in
``make check-fast``. The fixture lives at ``tests/fixtures/anthropic_response.json``
and mimics the shape verified live on 2026-05-20 against ``claude-opus-4-6``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aedist.query_anthropic import (
    AGENT_FAMILY,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MAX_USES,
    DEFAULT_MODEL,
    DEFAULT_PRICE_PER_WEB_SEARCH_USD,
    _compute_anthropic_cost,
    _parse_anthropic_response,
    assemble_request,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "anthropic_response.json"


@pytest.fixture
def anthropic_fixture() -> dict:
    """Load the recorded ``messages.create`` response shape."""
    return json.loads(FIXTURE_PATH.read_text())


@pytest.fixture
def price_card() -> dict:
    """Published Anthropic Claude Opus 4.6 token prices + web_search surcharge."""
    return {
        "family": AGENT_FAMILY,
        "route": AGENT_FAMILY,
        "model_id": DEFAULT_MODEL,
        "price_per_mtok_in": 5.0,
        "price_per_mtok_out": 25.0,
        "price_per_mtok_cache_read": 0.50,
        "price_per_mtok_cache_write": 10.0,
        "price_per_web_search": DEFAULT_PRICE_PER_WEB_SEARCH_USD,
    }


# ---------------------------------------------------------------------------
# Parsing — the *first failing test* from raid plan §0167
# ---------------------------------------------------------------------------


def test_parse_response_extracts_citations_and_search_calls(anthropic_fixture):
    """End-to-end parse: thinking + server_tool_use + result + text+citation."""
    parsed = _parse_anthropic_response(anthropic_fixture)

    # One search call (the single server_tool_use block).
    assert len(parsed["web_search_calls"]) == 1
    call = parsed["web_search_calls"][0]
    assert call["query"].startswith("Vietnam operational coal")
    # urls_returned is stitched from the matching web_search_tool_result by id.
    assert len(call["urls_returned"]) == 2
    assert any("evn.com.vn" in u for u in call["urls_returned"])

    # One inline citation on the text block (richer signal than result URLs).
    assert len(parsed["citations"]) == 1
    cit = parsed["citations"][0]
    assert "evn.com.vn" in cit["url"]
    assert cit["snippet"] is not None and "Vinh Tan" in cit["snippet"]

    # Narrative non-empty.
    assert parsed["text"]
    assert "Vietnam" in parsed["text"]

    # n_searches from usage.server_tool_use.web_search_requests (authoritative).
    assert parsed["n_searches"] == 1

    # Thinking captured as reasoning_summary.
    assert parsed["reasoning_summary"] is not None
    assert "search" in parsed["reasoning_summary"].lower()

    # Token usage carried through.
    assert parsed["tokens_in"] == 12000
    assert parsed["tokens_out"] == 600

    # finish_reason wired from stop_reason.
    assert parsed["finish_reason"] == "end_turn"


# ---------------------------------------------------------------------------
# Cost arithmetic
# ---------------------------------------------------------------------------


def test_compute_cost_against_hand_arithmetic(anthropic_fixture, price_card):
    """Hand-computed cost matches the adapter's breakdown.

    Hand math:
      input   = 12000 / 1e6 * $5.00  = $0.060
      output  =   600 / 1e6 * $25.00 = $0.015
      cache   = 0
      search  = 1 * $0.010           = $0.010
      ---------------------------------------
      total                          = $0.085
    """
    usage = anthropic_fixture["usage"]
    cost = _compute_anthropic_cost(usage, price_card, n_searches=1)

    assert cost["input"] == pytest.approx(0.060, abs=1e-9)
    assert cost["output"] == pytest.approx(0.015, abs=1e-9)
    assert cost["cache_read"] == pytest.approx(0.0, abs=1e-9)
    assert cost["cache_write"] == pytest.approx(0.0, abs=1e-9)
    assert cost["web_search"] == pytest.approx(0.010, abs=1e-9)
    assert cost["total"] == pytest.approx(0.085, abs=1e-9)


def test_compute_cost_asymmetric_arguments_catches_swaps(price_card):
    """Swapping input_tokens and output_tokens must change the answer.

    Catches the classic "I priced output at input rate" bug.
    """
    a = _compute_anthropic_cost(
        {"input_tokens": 1000, "output_tokens": 100}, price_card, n_searches=0
    )
    b = _compute_anthropic_cost(
        {"input_tokens": 100, "output_tokens": 1000}, price_card, n_searches=0
    )
    # a = 1000*5 + 100*25 = 5000 + 2500 = 7500 / 1e6 = 0.0075
    # b = 100*5 + 1000*25 = 500 + 25000 = 25500 / 1e6 = 0.0255
    assert a["total"] == pytest.approx(0.0075)
    assert b["total"] == pytest.approx(0.0255)
    assert a["total"] != b["total"]


# ---------------------------------------------------------------------------
# Dry-run payload assembly
# ---------------------------------------------------------------------------


def test_assemble_request_contains_model_websearch_and_thinking():
    payload = assemble_request(
        "Hello, world.",
        DEFAULT_MODEL,
        max_tokens=DEFAULT_MAX_TOKENS,
        max_uses=DEFAULT_MAX_USES,
    )

    assert payload["model"] == DEFAULT_MODEL
    assert payload["max_tokens"] == DEFAULT_MAX_TOKENS
    assert payload["messages"] == [{"role": "user", "content": "Hello, world."}]

    # Adaptive thinking — NOT manual {enabled, budget_tokens}.
    assert payload["thinking"] == {"type": "adaptive", "display": "summarized"}

    # web_search tool entry must be present, well-typed, with max_uses wired.
    [tool] = payload["tools"]
    assert tool["type"] == "web_search_20250305"
    assert tool["name"] == "web_search"
    assert tool["max_uses"] == DEFAULT_MAX_USES

    # tool_choice must be "auto" (or none). Live API rejects forced tool use.
    assert payload["tool_choice"] == {"type": "auto"}


def test_assemble_request_default_model_pinned_to_4_6():
    """Ticket 0167 decision (2026-05-20): pin claude-opus-4-6, not 4.7."""
    payload = assemble_request("ping")
    assert payload["model"] == "claude-opus-4-6"


# ---------------------------------------------------------------------------
# Empty / degenerate inputs
# ---------------------------------------------------------------------------


def test_parse_empty_content_returns_empty_lists():
    parsed = _parse_anthropic_response({"content": [], "usage": {}, "stop_reason": "stop"})
    assert parsed["text"] == ""
    assert parsed["citations"] == []
    assert parsed["web_search_calls"] == []
    assert parsed["n_searches"] == 0
    assert parsed["reasoning_summary"] is None


def test_parse_handles_multiple_text_blocks_with_citations():
    """Citations from several text blocks accumulate in order."""
    resp = {
        "content": [
            {
                "type": "text",
                "text": "Para 1. ",
                "citations": [
                    {"type": "web_search_result_location", "url": "https://a", "cited_text": "x"}
                ],
            },
            {
                "type": "text",
                "text": "Para 2.",
                "citations": [
                    {"type": "web_search_result_location", "url": "https://b", "cited_text": "y"}
                ],
            },
        ],
        "usage": {"input_tokens": 1, "output_tokens": 1},
        "stop_reason": "end_turn",
    }
    parsed = _parse_anthropic_response(resp)
    assert parsed["text"] == "Para 1. Para 2."
    assert [c["url"] for c in parsed["citations"]] == ["https://a", "https://b"]


def test_parse_stitches_tool_use_to_result_by_id():
    """server_tool_use and web_search_tool_result are paired by tool_use_id."""
    resp = {
        "content": [
            {
                "type": "server_tool_use",
                "id": "T1",
                "name": "web_search",
                "input": {"query": "q1"},
            },
            {
                "type": "server_tool_use",
                "id": "T2",
                "name": "web_search",
                "input": {"query": "q2"},
            },
            {
                "type": "web_search_tool_result",
                "tool_use_id": "T2",
                "content": [{"type": "web_search_result", "url": "https://second"}],
            },
            {
                "type": "web_search_tool_result",
                "tool_use_id": "T1",
                "content": [{"type": "web_search_result", "url": "https://first"}],
            },
        ],
        "usage": {
            "input_tokens": 1,
            "output_tokens": 1,
            "server_tool_use": {"web_search_requests": 2},
        },
        "stop_reason": "end_turn",
    }
    parsed = _parse_anthropic_response(resp)
    # Order follows server_tool_use appearance, not result appearance.
    assert [c["query"] for c in parsed["web_search_calls"]] == ["q1", "q2"]
    assert parsed["web_search_calls"][0]["urls_returned"] == ["https://first"]
    assert parsed["web_search_calls"][1]["urls_returned"] == ["https://second"]
    assert parsed["n_searches"] == 2


# ---------------------------------------------------------------------------
# Multi-turn continuation surface (ticket 0208)
# ---------------------------------------------------------------------------


def test_dispatch_accepts_continuation_kwarg(anthropic_fixture, price_card, tmp_path):
    """dispatch() must accept continuation kwarg on dry-run without crash."""
    from aedist.query_anthropic import dispatch

    payload = assemble_request("hello", DEFAULT_MODEL, max_tokens=DEFAULT_MAX_TOKENS)
    result = dispatch(
        payload,
        price_card,
        dry_run=True,
        output_dir=tmp_path,
        continuation={"messages": [{"role": "user", "content": "q1"}]},
    )
    # Dry-run returns None record.
    assert result["run_record"] is None


def test_dispatch_accepts_extra_metadata_kwarg(price_card, tmp_path):
    """dispatch() must accept extra_metadata kwarg on dry-run without crash."""
    from aedist.query_anthropic import dispatch

    payload = assemble_request("hello", DEFAULT_MODEL, max_tokens=DEFAULT_MAX_TOKENS)
    result = dispatch(
        payload,
        price_card,
        dry_run=True,
        output_dir=tmp_path,
        extra_metadata={"remaining_budget_usd": "5.50"},
    )
    assert result["run_record"] is None


def test_record_from_parsed_includes_messages_in_extra():
    """_record_from_parsed must include messages in method_params.extra
    when provided, so the harness can chain multi-turn conversations.
    """
    from aedist.query_anthropic import _record_from_parsed

    parsed = {
        "text": "answer text",
        "web_search_calls": [],
        "citations": [],
        "reasoning_summary": None,
        "finish_reason": "end_turn",
    }
    record = _record_from_parsed(
        parsed,
        model=DEFAULT_MODEL,
        cost_breakdown={"total": 0.01, "input": 0.005, "output": 0.005},
        tokens_in=100,
        tokens_out=50,
        wall_s=1.0,
        thinking_tokens=None,
        agent_mode="smoke",
        run_number=1,
        messages_for_continuation=[
            {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "answer text"},
        ],
    )
    assert record.method_params.extra is not None
    assert "messages" in record.method_params.extra
    msgs = record.method_params.extra["messages"]
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"


# ── Retry policy (ticket 0244) ──────────────────────────────────────


@pytest.fixture()
def _no_sleep_anthropic(monkeypatch):
    monkeypatch.setattr("aedist.query_anthropic.time.sleep", lambda _: None)


class _FakeRateLimitError(Exception):
    pass


class _FakeAPIStatusError(Exception):
    def __init__(self, status_code):
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}")


class _FakeAPIConnectionError(Exception):
    pass


def _patch_anthropic_exceptions(monkeypatch):
    import types

    fake_anthropic = types.ModuleType("anthropic")
    fake_anthropic.RateLimitError = _FakeRateLimitError
    fake_anthropic.APIStatusError = _FakeAPIStatusError
    fake_anthropic.APIConnectionError = _FakeAPIConnectionError
    monkeypatch.setitem(__import__("sys").modules, "anthropic", fake_anthropic)


def test_anthropic_retry_succeeds_after_429(_no_sleep_anthropic, monkeypatch):
    """429 twice then success → result returned, 3 attempts total."""
    _patch_anthropic_exceptions(monkeypatch)
    from aedist.query_anthropic import _call_with_retry

    call_count = 0

    class FakeClient:
        class messages:  # noqa: N801
            @staticmethod
            def create(**kwargs):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    raise _FakeRateLimitError("rate limited")
                return {"result": "ok"}

    result = _call_with_retry(FakeClient(), {"model": "test"})
    assert result == {"result": "ok"}
    assert call_count == 3


def test_anthropic_retry_exhausts_on_429(_no_sleep_anthropic, monkeypatch):
    """429 × 4 → raises after exhausting retries."""
    _patch_anthropic_exceptions(monkeypatch)
    from aedist.query_anthropic import _call_with_retry

    class FakeClient:
        class messages:  # noqa: N801
            @staticmethod
            def create(**kwargs):
                raise _FakeRateLimitError("rate limited")

    with pytest.raises(_FakeRateLimitError):
        _call_with_retry(FakeClient(), {"model": "test"})


def test_anthropic_retry_skips_4xx(_no_sleep_anthropic, monkeypatch):
    """Non-429 4xx raises immediately — no retry."""
    _patch_anthropic_exceptions(monkeypatch)
    from aedist.query_anthropic import _call_with_retry

    call_count = 0

    class FakeClient:
        class messages:  # noqa: N801
            @staticmethod
            def create(**kwargs):
                nonlocal call_count
                call_count += 1
                raise _FakeAPIStatusError(422)

    with pytest.raises(_FakeAPIStatusError):
        _call_with_retry(FakeClient(), {"model": "test"})
    assert call_count == 1, "4xx must not trigger any retry"


def test_anthropic_retry_retries_500(_no_sleep_anthropic, monkeypatch):
    """500 once then success → retried."""
    _patch_anthropic_exceptions(monkeypatch)
    from aedist.query_anthropic import _call_with_retry

    call_count = 0

    class FakeClient:
        class messages:  # noqa: N801
            @staticmethod
            def create(**kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise _FakeAPIStatusError(502)
                return {"result": "ok"}

    result = _call_with_retry(FakeClient(), {"model": "test"})
    assert result == {"result": "ok"}
    assert call_count == 2


def test_parse_empty_payload_does_not_raise():
    """A response with no content block parses to empty text / no citations."""
    parsed = _parse_anthropic_response({})
    assert parsed["text"] == ""
    assert parsed["citations"] == []
    assert parsed["web_search_calls"] == []


def test_parse_truncated_payload_keeps_partial_text():
    """A truncated stream (text block, max_tokens stop) still yields its text."""
    resp = {
        "content": [{"type": "text", "text": "partial answer"}],
        "stop_reason": "max_tokens",
    }
    parsed = _parse_anthropic_response(resp)
    assert parsed["text"] == "partial answer"
    assert parsed["finish_reason"] == "max_tokens"
    assert parsed["citations"] == []
