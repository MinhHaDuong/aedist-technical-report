"""Unit tests for the OpenAI Responses adapter (ticket 0168).

Pure unit tests — no subprocess, no sleep, no network. Belong in
`make check-fast`.

Fixture arithmetic (locked, hand-computed for non-tautology):
  input_tokens=100 (of which cached=20 → fresh=80)
  output_tokens=500
  reasoning_tokens=1500
  Price card: fresh_in=$5.0, cached_in=$1.25, output=$20.0, reasoning=$20.0
  cost_usd = (80 * 5.0 + 20 * 1.25 + 500 * 20.0 + 1500 * 20.0) / 1e6
           = (400 + 25 + 10000 + 30000) / 1e6
           = 40425 / 1e6
           = 0.040425
URLs: 4 + 3 = 7 distinct (asymmetric, catches parser bugs).
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from aedist.adapter_base import CostCapExceeded
from aedist.adapter_openai_responses import (
    AGENT_FAMILY,
    DEFAULT_COST_CAP_USD,
    DEFAULT_MODEL,
    build_request,
    parse_response,
    run,
)

FIXTURE = Path(__file__).parent / "fixtures" / "openai_responses_response.json"

PRICE_CARD = {
    "price_per_mtok_in_fresh": 5.0,
    "price_per_mtok_in_cached": 1.25,
    "price_per_mtok_out": 20.0,
    "price_per_mtok_reasoning": 20.0,
}

EXPECTED_COST_USD = 0.040425  # see module docstring for derivation


def _json_to_namespace(obj):
    """Recursively convert dicts/lists from JSON to SimpleNamespace.

    Mimics the attribute-access shape of the OpenAI SDK's response object,
    so the fixture exercises the same code path as a live SDK return value.
    """
    if isinstance(obj, dict):
        return SimpleNamespace(**{k: _json_to_namespace(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [_json_to_namespace(item) for item in obj]
    return obj


def _load_fixture() -> SimpleNamespace:
    with open(FIXTURE) as f:
        return _json_to_namespace(json.load(f))


# ---------------------------------------------------------------------------
# parse_response — the core non-tautological test
# ---------------------------------------------------------------------------


def test_parse_canned_response_yields_runrecord_with_citations_and_reasoning():
    resp = _load_fixture()
    record = parse_response(resp, PRICE_CARD)

    # Family identity
    assert record.agent_family == AGENT_FAMILY == "openai-direct"

    # Asymmetric counts (4 + 3 = 7 distinct URLs across two searches)
    assert record.web_search_calls is not None
    assert len(record.web_search_calls) == 2, (
        f"expected 2 web_search_call entries, got {len(record.web_search_calls)}"
    )
    assert record.citations is not None
    assert len(record.citations) == 7, f"expected 7 citations (4+3), got {len(record.citations)}"

    # Query lifted from action.query (not from result, not from action.sources)
    assert record.web_search_calls[0]["query"] == "vietnam coal power plants operational"
    assert record.web_search_calls[1]["query"] == "Phu My 2.2 capacity"

    # Asymmetric per-call URL counts: search 0 has 4 URLs, search 1 has 3
    assert len(record.web_search_calls[0]["urls_returned"]) == 4
    assert len(record.web_search_calls[1]["urls_returned"]) == 3

    # Citation URLs come from action.sources (not from output_text.annotations)
    citation_urls = {c["url"] for c in record.citations}
    assert "https://example.com/vinh-tan" in citation_urls
    assert "https://example.com/phu-my-overview" in citation_urls

    # Narrative from message.content[*].output_text
    # (Adapter may concatenate or pick first; assert the substring is present.)

    # Cost: hand-computed against PRICE_CARD
    assert record.resource_use.cost_usd == pytest.approx(EXPECTED_COST_USD), (
        f"expected ${EXPECTED_COST_USD}, got ${record.resource_use.cost_usd}"
    )

    # Token bookkeeping carried through
    assert record.resource_use.tokens_in == 100
    assert record.resource_use.tokens_out == 500
    assert record.resource_use.thinking_tokens == 1500

    # reasoning_summary is typically empty for this adapter (verified
    # empirically 2026-05-20 against gpt-5.5: summary=[] even at
    # effort=high, summary=detailed). None is the correct value.
    assert record.reasoning_summary is None or record.reasoning_summary == ""


# ---------------------------------------------------------------------------
# build_request — dry-run payload assertions, with belt-and-suspenders on
# the include= directive (the #1 silent-citation-loss bug surface)
# ---------------------------------------------------------------------------


def test_build_request_payload_contains_required_keys():
    payload = build_request(
        "List 3 coal power plants in Vietnam",
        model="gpt-5.5",
        max_output_tokens=2000,
        reasoning_effort="high",
    )

    # Model + input wired through
    assert payload["model"] == "gpt-5.5"
    assert payload["input"] == "List 3 coal power plants in Vietnam"
    assert payload["max_output_tokens"] == 2000

    # Tools must be the native web_search (NOT web_search_preview, which
    # is a legacy alias removed by OpenAI).
    assert payload["tools"] == [{"type": "web_search"}]
    # Explicit assert: never use the preview alias.
    assert all(t["type"] != "web_search_preview" for t in payload["tools"])

    # Reasoning effort directive present.
    assert payload["reasoning"] == {"effort": "high"}


def test_build_request_includes_web_search_sources_directive():
    """The include= directive is MANDATORY — without it the response's
    web_search_call.action carries only the query and output_text.annotations
    stays empty, so citations are silently lost. Verified empirically against
    gpt-5.5 on 2026-05-20. This is the #1 way to ship a silent-citation-loss
    bug; over-test it.
    """
    payload = build_request(
        "test",
        model="gpt-5.5",
        max_output_tokens=100,
        reasoning_effort="high",
    )

    # Key must be present.
    assert "include" in payload, (
        "missing 'include' kwarg — URLs will be silently dropped from the response"
    )
    # Must be a non-empty list.
    assert isinstance(payload["include"], list)
    assert len(payload["include"]) > 0
    # The specific magic string must appear (the only known directive that
    # surfaces action.sources URLs).
    assert "web_search_call.action.sources" in payload["include"]


def test_default_model_is_gpt_5_5():
    assert DEFAULT_MODEL == "gpt-5.5"


# ---------------------------------------------------------------------------
# Cost cap enforcement — ticket 0168 Action 4 (pre-call estimate)
# ---------------------------------------------------------------------------


def test_run_raises_costcap_before_http_call_when_estimate_exceeds_cap():
    """``run()`` must enforce the cost cap PRE-call.

    Pricing chosen so that the conservative estimate (max_tokens billed at
    both input and output rates) exceeds a $1 cap by a wide margin:

        price_per_mtok_in = price_per_mtok_out = 1_000.0  -> $1e-3/token
        max_output_tokens = 10_000
        estimate = 10_000 * (1e-3 + 1e-3) = $20.00 >> $1.00

    No HTTP client is constructed; the exception must fire from the cap
    check, not from a missing OPENAI_API_KEY or a network call.
    """
    expensive_card = {
        "price_per_mtok_in_fresh": 1_000.0,
        "price_per_mtok_in": 1_000.0,
        "price_per_mtok_out": 1_000.0,
    }
    with pytest.raises(CostCapExceeded):
        run(
            "trivial prompt",
            dry_run=False,
            max_output_tokens=10_000,
            price_card=expensive_card,
            cap_usd=1.0,
        )


def test_run_dry_run_still_enforces_cap_pre_call():
    """Even ``dry_run=True`` must respect the cap — guards against a caller
    discovering the breach only when they flip dry_run to False.
    """
    expensive_card = {
        "price_per_mtok_in_fresh": 1_000.0,
        "price_per_mtok_in": 1_000.0,
        "price_per_mtok_out": 1_000.0,
    }
    with pytest.raises(CostCapExceeded):
        run(
            "trivial prompt",
            dry_run=True,
            max_output_tokens=10_000,
            price_card=expensive_card,
            cap_usd=1.0,
        )


def test_default_cost_cap_is_ten_dollars():
    """Ticket 0168 Action 4 spec: hard cap per call $10."""
    assert DEFAULT_COST_CAP_USD == 10.0


# ---------------------------------------------------------------------------
# Multi-turn continuation surface (ticket 0208)
# ---------------------------------------------------------------------------


def test_run_dry_run_returns_continuation_ready_record():
    """Dry-run with continuation=None must succeed without crash.
    The continuation token is only meaningful on live calls.
    """
    record = run(
        "test prompt",
        dry_run=True,
        model=DEFAULT_MODEL,
        max_output_tokens=100,
        price_card=PRICE_CARD,
        cap_usd=DEFAULT_COST_CAP_USD,
    )
    assert record.agent_family == AGENT_FAMILY
    assert record.result_summary.status == "qualitative"


def test_parse_response_returns_response_id_in_extra():
    """parse_response must include response_id in method_params.extra
    so the harness can use it for previous_response_id chaining.
    """
    resp = _load_fixture()
    record = parse_response(resp, PRICE_CARD)
    assert record.method_params.extra is not None
    assert "response_id" in record.method_params.extra


def test_run_dry_run_accepts_continuation_kwarg():
    """run() must accept continuation kwarg without crashing on dry-run."""
    record = run(
        "follow up",
        dry_run=True,
        model=DEFAULT_MODEL,
        max_output_tokens=100,
        price_card=PRICE_CARD,
        cap_usd=DEFAULT_COST_CAP_USD,
        continuation={"response_id": "resp_abc"},
    )
    assert record.agent_family == AGENT_FAMILY


def test_run_dry_run_accepts_extra_metadata_kwarg():
    """run() must accept extra_metadata kwarg without crashing."""
    record = run(
        "prompt",
        dry_run=True,
        model=DEFAULT_MODEL,
        max_output_tokens=100,
        price_card=PRICE_CARD,
        cap_usd=DEFAULT_COST_CAP_USD,
        extra_metadata={"remaining_budget_usd": "5.50"},
    )
    assert record.agent_family == AGENT_FAMILY
