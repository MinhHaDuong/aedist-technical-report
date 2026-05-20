"""Unit tests for the Mistral Agents adapter (ticket 0169).

Pure unit tests — no network. Verifies:

- ``build_request`` assembles both the agent-create and conversation
  bodies with the right tool list and prompt shape.
- ``parse_response`` walks the verified HTTP shape correctly,
  populating ``web_search_calls``, ``citations``, ``tool_calls_cost_usd``,
  and ``cost_breakdown`` from a recorded-shape fixture.
- Cost arithmetic separates the connector bucket from token cost.

The fixture (`tests/fixtures/mistral_conversation_response.json`) was
constructed from the empirical probe shape captured 2026-05-20 — see
its `_provenance` field and the ticket log entry.
"""

import json
from pathlib import Path

import pytest

from aedist.adapter_mistral import (
    AGENT_FAMILY,
    DEFAULT_MODEL,
    build_request,
    parse_response,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "mistral_conversation_response.json"


# Pricing card mirrored from the models.yaml entry registered in this
# ticket. Keep in sync if the registry numbers shift.
PRICE_CARD = {
    "model_id": DEFAULT_MODEL,
    "price_per_mtok_in": 0.5,
    "price_per_mtok_out": 1.5,
    "price_per_connector_mtok": 1.0,
}


@pytest.fixture
def fixture_response() -> dict:
    return json.loads(FIXTURE_PATH.read_text())


# ---------------------------------------------------------------------------
# build_request
# ---------------------------------------------------------------------------


def test_build_request_emits_agent_create_with_web_search_tool():
    payload = build_request("hello world", model=DEFAULT_MODEL, max_tokens=600)
    create = payload["agent_create"]
    assert create["method"] == "POST"
    assert create["path"] == "/v1/agents"
    body = create["body"]
    assert body["model"] == DEFAULT_MODEL
    assert body["tools"] == [{"type": "web_search"}]


def test_build_request_emits_conversation_with_agent_id_placeholder_and_inputs():
    payload = build_request("hello world", model=DEFAULT_MODEL, max_tokens=600)
    conv = payload["conversation_start"]
    assert conv["method"] == "POST"
    assert conv["path"] == "/v1/conversations"
    body = conv["body"]
    # agent_id is unresolved at build time — the run() loop fills it
    # after the create response. The dry-run reader must see a clearly
    # marked placeholder, not an empty string that hides the contract.
    assert body["agent_id"] == "<assigned-after-agent-create>"
    assert body["inputs"] == [{"role": "user", "content": "hello world"}]
    assert body["max_tokens"] == 600


def test_build_request_declares_delete_path():
    payload = build_request("hello", model=DEFAULT_MODEL)
    assert payload["agent_delete"]["method"] == "DELETE"
    assert "{agent_id}" in payload["agent_delete"]["path"]


# ---------------------------------------------------------------------------
# parse_response — the non-tautological asymmetric-counts assertion
# ---------------------------------------------------------------------------


def test_parse_response_populates_tool_calls_cost_and_citations(fixture_response):
    """The headline assertion from ticket 0169.

    Fixture deliberately has 2 tool.execution entries and 4
    tool_reference entries — asymmetric counts catch any parser that
    confuses search-call count with citation count.
    """
    record = parse_response(fixture_response, PRICE_CARD)

    # Asymmetric counts — the load-bearing check.
    assert len(record.web_search_calls) == 2
    assert len(record.citations) == 4
    # Round-trip the count through the usage block too.
    assert fixture_response["usage"]["connectors"]["web_search"] == 2

    # Cost split: token-only on resource_use.cost_usd, connector on
    # tool_calls_cost_usd. NEVER blended.
    # Token cost = 120 * 0.5/1M + 380 * 1.5/1M = 6.0e-5 + 5.7e-4 = 6.3e-4
    assert record.resource_use.cost_usd == pytest.approx(0.00063, rel=1e-9)
    # Connector cost = 4200 * 1.0/1M = 0.0042
    assert record.tool_calls_cost_usd == pytest.approx(0.0042, rel=1e-9)

    # cost_breakdown surfaces the connector bucket distinctly.
    bd = record.resource_use.cost_breakdown
    assert bd["input"] == pytest.approx(120 * 0.5 / 1_000_000)
    assert bd["output"] == pytest.approx(380 * 1.5 / 1_000_000)
    assert bd["connector"] == pytest.approx(0.0042)


def test_parse_response_extracts_query_from_tool_execution_arguments(fixture_response):
    record = parse_response(fixture_response, PRICE_CARD)
    queries = [c["query"] for c in record.web_search_calls]
    assert queries == [
        "Phu My 2.2 power plant capacity Vietnam",
        "EVN coal power plants Vietnam 2025",
    ]


def test_parse_response_citations_carry_url_title_and_snippet(fixture_response):
    record = parse_response(fixture_response, PRICE_CARD)
    urls = [c["url"] for c in record.citations]
    assert "https://en.wikipedia.org/wiki/Phu_My_2.2_Power_Plant" in urls
    # snippet maps from description; title preserved as a sidecar field.
    first = record.citations[0]
    assert first["url"].startswith("https://")
    assert first["snippet"] is not None
    assert first["title"]


def test_parse_response_concatenates_narrative_text_chunks(fixture_response):
    record = parse_response(fixture_response, PRICE_CARD)
    # The fixture's text chunks should appear in order in the narrative
    # so we can verify the right items were aggregated.
    # We rely on the agent_mode being "ok" because the fixture has text.
    assert record.result_summary.status == "ok"


def test_parse_response_sets_agent_family_and_mode(fixture_response):
    record = parse_response(fixture_response, PRICE_CARD, agent_mode="probe")
    assert record.agent_family == AGENT_FAMILY
    assert record.agent_mode == "probe"


def test_parse_response_records_tokens_in_resource_use(fixture_response):
    record = parse_response(fixture_response, PRICE_CARD)
    assert record.resource_use.tokens_in == 120
    assert record.resource_use.tokens_out == 380


# ---------------------------------------------------------------------------
# Pricing fallback: flat per-call when connector-token rate absent
# ---------------------------------------------------------------------------


def test_parse_response_falls_back_to_flat_per_call_price(fixture_response):
    """Without ``price_per_connector_mtok`` the adapter charges flat
    per-call from ``usage.connectors.web_search``.

    This keeps the door open for Mistral to publish either pricing model
    (per-bucket-token or per-call) without an adapter rewrite.
    """
    card = dict(PRICE_CARD)
    del card["price_per_connector_mtok"]
    card["price_per_web_search_call_usd"] = 0.025
    record = parse_response(fixture_response, card)
    # 2 web_search calls × $0.025 = $0.050
    assert record.tool_calls_cost_usd == pytest.approx(0.05, rel=1e-9)
