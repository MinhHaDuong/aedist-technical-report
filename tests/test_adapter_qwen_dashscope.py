"""Unit tests for the Qwen3-Max DashScope adapter (ticket 0173).

Pure unit tests — no subprocess, no sleep, no network. Belong in
`make check-fast`. The live smoke is a separate one-shot driver invocation,
not a pytest test.

The fixture under ``tests/fixtures/qwen_dashscope_response.json`` is
deliberately **asymmetric**: ``usage.plugins.search.count == 3`` but
``output.search_info.search_results`` contains **5** distinct URLs. This
catches both "forgot len()" and "deduplicated wrong list" bugs in
``parse_response`` — a tautological "kwargs round-trip" assertion would
not.
"""

import json
from pathlib import Path

import pytest

from aedist.adapter_qwen_dashscope import (
    AGENT_FAMILY,
    DEFAULT_MODEL,
    build_request,
    parse_response,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "qwen_dashscope_response.json"


@pytest.fixture
def canned_response() -> dict:
    """Load the recorded DashScope response shape (verified 2026-05-20)."""
    return json.loads(FIXTURE_PATH.read_text())


@pytest.fixture
def price_card() -> dict:
    """Explicit price card so the test does not silently track default drift."""
    return {
        "model_id": DEFAULT_MODEL,
        "price_per_mtok_in": 1.2,
        "price_per_mtok_out": 6.0,
        "price_per_mtok_reasoning": 6.0,
        "price_per_web_search_call_usd": 0.010,
    }


# ---------------------------------------------------------------------------
# parse_response — the asymmetric, non-tautological assertion bundle
# ---------------------------------------------------------------------------


def test_parse_response_extracts_thinking_searches_and_citations(
    canned_response: dict, price_card: dict
) -> None:
    """The headline test from the raid plan.

    Fixture has ``search.count == 3`` and 5 distinct URLs in
    ``search_results``. Adapter records ``web_search_calls`` as a list of
    length ``count`` (per docstring), so ``len(record.web_search_calls)``
    must equal 3 — NOT 5 (the URL count) and NOT some boolean. Citations
    take the full 5-URL list.
    """
    record = parse_response(canned_response, model_meta=price_card)

    # --- search count (asymmetric: 3 searches, 5 URLs) ---
    assert record.web_search_calls is not None
    assert len(record.web_search_calls) == 3

    # --- citations (5 distinct URLs, flat across all searches) ---
    assert record.citations is not None
    assert len(record.citations) == 5
    urls = [c["url"] for c in record.citations]
    assert len(set(urls)) == 5  # no accidental dedup

    # --- reasoning_summary non-empty (thinking mode composed) ---
    assert record.reasoning_summary is not None
    assert len(record.reasoning_summary) > 0

    # --- agent_family contract ---
    assert record.agent_family == "qwen-direct"
    assert AGENT_FAMILY == "qwen-direct"  # belt-and-braces against drift

    # --- finish_reason surfaced from choices[0] ---
    assert record.finish_reason == "stop"

    # --- thinking_tokens surfaced from output_tokens_details.reasoning_tokens ---
    assert record.resource_use.thinking_tokens == 1900


def test_parse_response_cost_arithmetic_matches_fixture_price_card(
    canned_response: dict, price_card: dict
) -> None:
    """Cost arithmetic against the explicit fixture price card.

    Fixture: 42 input tokens, 2150 output tokens (incl. 1900 reasoning),
    3 web searches. Visible-output billing: 2150 − 1900 = 250 tokens at
    the output rate; reasoning at its own rate.

    Token cost  = 42·1.2/1e6 + 250·6.0/1e6 + 1900·6.0/1e6
                ≈ 5.04e−5 + 1.5e−3 + 1.14e−2
                ≈ 0.0129504
    Tool cost   = 3 × 0.010 = 0.030
    """
    record = parse_response(canned_response, model_meta=price_card)

    expected_token_cost = (
        42 * 1.2 / 1_000_000.0 + 250 * 6.0 / 1_000_000.0 + 1900 * 6.0 / 1_000_000.0
    )
    assert record.resource_use.cost_usd == pytest.approx(expected_token_cost, abs=1e-6)
    assert record.tool_calls_cost_usd == pytest.approx(0.030, abs=1e-6)

    # Cost breakdown bookkeeping — buckets present and sum to token cost.
    assert record.resource_use.cost_breakdown is not None
    bd = record.resource_use.cost_breakdown
    assert set(bd.keys()) == {"input", "output", "reasoning"}
    assert sum(bd.values()) == pytest.approx(expected_token_cost, abs=1e-6)


def test_parse_response_surfaces_token_counts(canned_response: dict, price_card: dict) -> None:
    """Token counts pass through from ``usage`` block unchanged."""
    record = parse_response(canned_response, model_meta=price_card)
    assert record.resource_use.tokens_in == 42
    assert record.resource_use.tokens_out == 2150


def test_parse_response_citation_entries_preserve_index_and_metadata(
    canned_response: dict, price_card: dict
) -> None:
    """Each citation carries url + title + site_name + server-assigned index."""
    record = parse_response(canned_response, model_meta=price_card)
    assert record.citations is not None
    first = record.citations[0]
    assert first["index"] == 1
    assert first["url"].startswith("https://mofcom.gov.cn/")
    assert first["site_name"] == "mofcom.gov.cn"
    assert "title" in first


# ---------------------------------------------------------------------------
# build_request — dry-run payload assertions
# ---------------------------------------------------------------------------


def test_build_request_contains_enable_search_and_thinking() -> None:
    payload = build_request("hello world", max_tokens=800)
    assert payload["enable_search"] is True
    assert payload["enable_thinking"] is True
    assert payload["model"] == DEFAULT_MODEL
    assert payload["max_tokens"] == 800


def test_build_request_contains_search_options_block() -> None:
    """The search_options block carries the three citation-shaping keys."""
    payload = build_request("hello", max_tokens=100)
    so = payload["search_options"]
    assert so["enable_source"] is True
    assert so["enable_citation"] is True
    assert so["citation_format"] == "[<number>]"


def test_build_request_omits_tools_key() -> None:
    """Negative assertion: ``tools=[...]`` would activate client-side function
    calling and break the server-side search contract (see adapter module
    docstring). The payload must never carry this key.
    """
    payload = build_request("hello", max_tokens=100)
    assert "tools" not in payload


def test_build_request_uses_user_role_message() -> None:
    payload = build_request("the prompt body", max_tokens=100)
    assert payload["messages"] == [{"role": "user", "content": "the prompt body"}]


def test_build_request_uses_message_result_format() -> None:
    """``result_format='message'`` is required for the choices[0].message
    shape that ``parse_response`` unpacks.
    """
    payload = build_request("hello", max_tokens=100)
    assert payload["result_format"] == "message"
