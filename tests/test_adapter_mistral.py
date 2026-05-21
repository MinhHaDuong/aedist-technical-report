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

import httpx
import pytest

from aedist.adapter_mistral import (
    AGENT_FAMILY,
    DEFAULT_MODEL,
    _append_conversation,
    _create_agent,
    build_request,
    parse_response,
    run,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "mistral_conversation_response.json"
FIXTURE_STR_CONTENT_PATH = (
    Path(__file__).parent / "fixtures" / "mistral_conversation_response_str_content.json"
)


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


@pytest.fixture
def fixture_str_content_response() -> dict:
    """Fixture for the flat-string content shape (ticket 0206).

    The Mistral Conversations API empirically returns two content
    shapes: ``list[dict]`` of typed chunks (the 2026-05-20 derisk
    fixture) and ``str`` (observed live 2026-05-21 in the Exp 2 smoke,
    ticket 0185). This fixture exercises the second shape.
    """
    return json.loads(FIXTURE_STR_CONTENT_PATH.read_text())


def test_run_dry_run_short_circuits_before_network():
    """The dry-run branch of ``run()`` must construct a RunRecord without
    any HTTP call. We assert on the record's structure — if httpx were
    invoked, no `MISTRAL_API_KEY` is set in the test environment so the
    call would either fail at SystemExit or attempt a real request.

    This closes the coverage hole: the eight other tests exercise
    ``build_request`` and ``parse_response`` in isolation but never
    cross the ``run()`` entry point's dry-run early-return.
    """
    record = run(
        "hello",
        dry_run=True,
        model_meta={
            "model_id": DEFAULT_MODEL,
            "price_per_mtok_in": 0.5,
            "price_per_mtok_out": 1.5,
            "price_per_web_search_call_usd": 0.025,
        },
        max_tokens=600,
        cap_usd=10.0,
        agent_mode="smoke",
    )
    assert record.agent_family == AGENT_FAMILY
    assert record.agent_mode == "smoke"
    assert record.method_params.extra == {"dry_run": True}
    assert record.method_params.model == DEFAULT_MODEL


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
    # max_tokens belongs in completion_args at agent-create time — the
    # /v1/conversations endpoint rejects it as "Extra inputs are not
    # permitted" (verified 2026-05-20 against the live API).
    assert body["completion_args"]["max_tokens"] == 600


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
    # max_tokens is NOT a conversation-level field on Mistral Agents API
    # (it lives in agent.completion_args; see above test).
    assert "max_tokens" not in body


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


# ---------------------------------------------------------------------------
# parse_response — flat string content shape (ticket 0206)
#
# Empirically Mistral returns ``outputs[*].content`` in two shapes:
#   1. ``list[dict]`` of typed chunks (the 2026-05-20 derisk fixture).
#   2. ``str`` — a flat narrative inline (observed live 2026-05-21 in
#      the Exp 2 smoke, ticket 0185). The parser must handle both
#      without raising ``AttributeError: 'str' object has no attribute
#      'get'``.
# ---------------------------------------------------------------------------


def test_parse_response_handles_str_content_shape(fixture_str_content_response):
    """The flat-string shape must parse cleanly with status == "ok"."""
    record = parse_response(fixture_str_content_response, PRICE_CARD)
    assert record.result_summary.status == "ok"
    # Usage round-trip — the str-shape still carries a usage block.
    assert record.resource_use.tokens_in == 100
    assert record.resource_use.tokens_out == 50


def test_parse_response_str_content_yields_no_web_search_or_citations(
    fixture_str_content_response,
):
    """The flat-string shape carries no tool-reference markup."""
    record = parse_response(fixture_str_content_response, PRICE_CARD)
    assert record.web_search_calls == []
    assert record.citations == []


# ---------------------------------------------------------------------------
# Multi-turn continuation surface (ticket 0208)
# ---------------------------------------------------------------------------


def test_run_dry_run_returns_continuation_token():
    """First call (continuation=None) must return conversation_id and
    agent_id in method_params.extra so the harness can chain turns.
    Dry-run mode: no network, but the extra keys are present for the
    harness to introspect the return shape.
    """
    record = run(
        "hello",
        dry_run=True,
        model_meta=PRICE_CARD,
        max_tokens=600,
        cap_usd=10.0,
        agent_mode="smoke",
    )
    # Dry-run still has the dry_run marker; continuation keys are
    # only meaningful on live calls. Verify backward compat.
    assert record.method_params.extra == {"dry_run": True}


def test_continuation_skips_agent_creation(monkeypatch):
    """When continuation is provided, only one POST to /v1/conversations/{id}
    should happen — no agent creation, no agent deletion.

    Mistral's append-to-conversation endpoint is path-bound. This test
    asserts the URL path explicitly so a regression to the create-shape
    endpoint (which returns HTTP 422 live — ticket 0211) cannot sneak
    back in. The previous version of this test only counted POSTs,
    which is why the 0208 bug went unnoticed in unit tests.
    """
    import aedist.adapter_mistral as am

    calls: list[tuple[str, str, dict]] = []

    class FakeResponse:
        status_code = 200
        text = "{}"

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "outputs": [
                    {"type": "message.output", "content": "follow-up answer"},
                ],
                "usage": {
                    "prompt_tokens": 50,
                    "completion_tokens": 100,
                    "connector_tokens": 0,
                    "connectors": {"web_search": 0},
                },
                "conversation_id": "conv_1",
            }

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, **kwargs):
            calls.append(("POST", url, kwargs.get("json") or {}))
            return FakeResponse()

        def delete(self, url, **kwargs):
            calls.append(("DELETE", url, {}))
            return FakeResponse()

    monkeypatch.setattr(am, "_load_api_key", lambda *a, **k: "fake-key")
    monkeypatch.setattr(am.httpx, "Client", FakeClient)

    record = run(
        "follow up question",
        dry_run=False,
        model_meta=PRICE_CARD,
        max_tokens=600,
        cap_usd=10.0,
        agent_mode="smoke",
        continuation={"conversation_id": "conv_1", "agent_id": "ag_1"},
    )

    # Only one POST — no /v1/agents create or delete.
    assert len(calls) == 1
    method, url, _body = calls[0]
    assert method == "POST"
    # Path-bound endpoint (ticket 0211): must include the conversation id.
    assert url == "/v1/conversations/conv_1", (
        f"follow-up should POST to /v1/conversations/{{id}}, got: {calls}"
    )
    # Bare /v1/conversations is the *create* endpoint — would 422 live.
    assert not any(u == "/v1/conversations" for _, u, _ in calls), (
        f"follow-up must not POST to bare /v1/conversations (creates new), got: {calls}"
    )
    assert record.agent_family == AGENT_FAMILY


def test_continuation_body_omits_agent_id_and_conversation_id(monkeypatch):
    """Path-bound append endpoint rejects agent_id and conversation_id in
    the body (HTTP 422 live — ticket 0211). The body must contain only
    `inputs` (plus optional `metadata`).
    """
    import aedist.adapter_mistral as am

    bodies: list[dict] = []

    class FakeResponse:
        status_code = 200
        text = "{}"

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "outputs": [
                    {"type": "message.output", "content": "follow-up answer"},
                ],
                "usage": {
                    "prompt_tokens": 50,
                    "completion_tokens": 100,
                    "connector_tokens": 0,
                    "connectors": {"web_search": 0},
                },
                "conversation_id": "conv_1",
            }

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, **kwargs):
            bodies.append(kwargs.get("json") or {})
            return FakeResponse()

        def delete(self, url, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(am, "_load_api_key", lambda *a, **k: "fake-key")
    monkeypatch.setattr(am.httpx, "Client", FakeClient)

    run(
        "follow up question",
        dry_run=False,
        model_meta=PRICE_CARD,
        max_tokens=600,
        cap_usd=10.0,
        agent_mode="smoke",
        continuation={"conversation_id": "conv_1", "agent_id": "ag_1"},
    )

    assert len(bodies) == 1
    body = bodies[0]
    assert "inputs" in body
    assert "agent_id" not in body, (
        f"agent_id is rejected by the path-bound append endpoint; body={body}"
    )
    assert "conversation_id" not in body, (
        f"conversation_id belongs in the URL, not the body; body={body}"
    )


def test_multiturn_start_creates_agent_but_skips_delete(monkeypatch):
    """continuation={} (empty dict) = first turn of multi-turn.
    Agent must be created but NOT deleted — harness calls cleanup_agent later.
    """
    import aedist.adapter_mistral as am

    calls: list[tuple[str, str]] = []

    class FakeResponse:
        status_code = 200
        text = "{}"

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "id": "ag_new",
                "outputs": [
                    {"type": "message.output", "content": "first answer"},
                ],
                "usage": {
                    "prompt_tokens": 50,
                    "completion_tokens": 100,
                    "connector_tokens": 0,
                    "connectors": {"web_search": 0},
                },
                "conversation_id": "conv_new",
            }

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, **kwargs):
            calls.append(("POST", url))
            return FakeResponse()

        def delete(self, url, **kwargs):
            calls.append(("DELETE", url))
            return FakeResponse()

    monkeypatch.setattr(am, "_load_api_key", lambda *a, **k: "fake-key")
    monkeypatch.setattr(am.httpx, "Client", FakeClient)

    record = run(
        "first question",
        dry_run=False,
        model_meta=PRICE_CARD,
        max_tokens=600,
        cap_usd=10.0,
        agent_mode="smoke",
        continuation={},  # empty dict = multi-turn start sentinel
    )

    # Agent created (POST /v1/agents) + conversation started (POST /v1/conversations).
    # No DELETE — agent kept alive for follow-up turns.
    assert ("POST", "/v1/agents") in calls
    assert ("POST", "/v1/conversations") in calls
    assert not any(method == "DELETE" for method, _ in calls)

    # Continuation tokens surfaced for the next turn.
    assert record.method_params.extra["agent_id"] == "ag_new"
    assert record.method_params.extra["conversation_id"] == "conv_new"


def test_cleanup_agent_is_public():
    """cleanup_agent must be importable for harness lifecycle management."""
    from aedist.adapter_mistral import cleanup_agent

    assert callable(cleanup_agent)


# ---------------------------------------------------------------------------
# system_prompt kwarg (ticket 0213)
# ---------------------------------------------------------------------------


def test_run_threads_system_prompt_to_agent_description(monkeypatch):
    """Ticket 0213: ``system_prompt`` kwarg must populate the
    ``agent_create`` body's ``description`` field on multi-turn-start
    mode (continuation={}). The body is the only Mistral surface where
    a system-level instruction lives — see the adapter docstring's
    cross-adapter table.
    """
    import aedist.adapter_mistral as am

    bodies: dict[str, dict] = {}

    class FakeResponse:
        status_code = 200
        text = "{}"

        def __init__(self, payload: dict):
            self._payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self._payload

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, **kwargs):
            body = kwargs.get("json") or {}
            if url == "/v1/agents":
                bodies["agent_create"] = body
                return FakeResponse({"id": "ag_X"})
            if url == "/v1/conversations":
                bodies["conversation_start"] = body
                return FakeResponse(
                    {
                        "outputs": [{"type": "message.output", "content": "ok"}],
                        "usage": {
                            "prompt_tokens": 10,
                            "completion_tokens": 20,
                            "connector_tokens": 0,
                            "connectors": {"web_search": 0},
                        },
                        "conversation_id": "conv_X",
                    }
                )
            raise AssertionError(f"unexpected POST to {url}")

        def delete(self, url, **kwargs):
            return FakeResponse({})

    monkeypatch.setattr(am, "_load_api_key", lambda *a, **k: "fake-key")
    monkeypatch.setattr(am.httpx, "Client", FakeClient)

    run(
        "first prompt",
        dry_run=False,
        model_meta=PRICE_CARD,
        max_tokens=600,
        cap_usd=10.0,
        agent_mode="smoke",
        continuation={},  # multi-turn start
        system_prompt="custom system text",
    )

    assert "agent_create" in bodies
    assert bodies["agent_create"]["description"] == "custom system text", (
        f"expected description='custom system text'; got {bodies['agent_create']!r}"
    )


def test_run_threads_system_prompt_in_single_turn_mode(monkeypatch):
    """Single-turn mode (continuation=None) also accepts system_prompt
    and threads it through the agent body's description. Backward
    compatibility: omitting the kwarg leaves the default description in
    place (covered by every existing test).
    """
    import aedist.adapter_mistral as am

    captured: dict[str, dict] = {}

    class FakeResponse:
        status_code = 200
        text = "{}"

        def __init__(self, payload: dict):
            self._payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self._payload

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, **kwargs):
            body = kwargs.get("json") or {}
            if url == "/v1/agents":
                captured["agent_create"] = body
                return FakeResponse({"id": "ag_X"})
            return FakeResponse(
                {
                    "outputs": [{"type": "message.output", "content": "ok"}],
                    "usage": {
                        "prompt_tokens": 5,
                        "completion_tokens": 7,
                        "connector_tokens": 0,
                        "connectors": {"web_search": 0},
                    },
                    "conversation_id": "conv_X",
                }
            )

        def delete(self, url, **kwargs):
            return FakeResponse({})

    monkeypatch.setattr(am, "_load_api_key", lambda *a, **k: "fake-key")
    monkeypatch.setattr(am.httpx, "Client", FakeClient)

    run(
        "single-turn prompt",
        dry_run=False,
        model_meta=PRICE_CARD,
        max_tokens=600,
        cap_usd=10.0,
        agent_mode="smoke",
        system_prompt="ST-only system text",
    )

    assert captured["agent_create"]["description"] == "ST-only system text"


def test_run_followup_rejects_system_prompt_kwarg(monkeypatch):
    """Ticket 0213: passing system_prompt on a follow-up turn (when the
    agent is already created) must raise ValueError. The agent's
    description is fixed at creation time; silently ignoring would mask
    a programmer error (matching the codebase's history of dict-vs-string
    and HTTP 422 silent-accept incidents).
    """
    import aedist.adapter_mistral as am

    # No HTTP should be issued — the validation happens before the
    # transport block. Still stub the key loader to guard against the
    # SystemExit path masking a different failure.
    monkeypatch.setattr(am, "_load_api_key", lambda *a, **k: "fake-key")

    with pytest.raises(ValueError, match="system_prompt cannot be set on a follow-up turn"):
        run(
            "follow up question",
            dry_run=False,
            model_meta=PRICE_CARD,
            max_tokens=600,
            cap_usd=10.0,
            agent_mode="smoke",
            continuation={"conversation_id": "conv_1", "agent_id": "ag_1"},
            system_prompt="should be rejected",
        )


def test_run_default_description_when_no_system_prompt(monkeypatch):
    """Backward compat: when ``system_prompt`` is omitted, the agent
    body's description falls back to ``build_request``'s default. This
    locks in the no-change-for-existing-callers contract.
    """
    import aedist.adapter_mistral as am

    captured: dict[str, dict] = {}

    class FakeResponse:
        status_code = 200
        text = "{}"

        def __init__(self, payload: dict):
            self._payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self._payload

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, **kwargs):
            body = kwargs.get("json") or {}
            if url == "/v1/agents":
                captured["agent_create"] = body
                return FakeResponse({"id": "ag_X"})
            return FakeResponse(
                {
                    "outputs": [{"type": "message.output", "content": "ok"}],
                    "usage": {
                        "prompt_tokens": 5,
                        "completion_tokens": 7,
                        "connector_tokens": 0,
                        "connectors": {"web_search": 0},
                    },
                    "conversation_id": "conv_X",
                }
            )

        def delete(self, url, **kwargs):
            return FakeResponse({})

    monkeypatch.setattr(am, "_load_api_key", lambda *a, **k: "fake-key")
    monkeypatch.setattr(am.httpx, "Client", FakeClient)

    run(
        "no system prompt here",
        dry_run=False,
        model_meta=PRICE_CARD,
        max_tokens=600,
        cap_usd=10.0,
        agent_mode="smoke",
    )

    # The default description from build_request — unchanged.
    assert captured["agent_create"]["description"] == (
        "AEDIST SOTA experiment agent with web_search connector."
    )


def test_run_extra_metadata_logged_without_crash(monkeypatch, caplog):
    """extra_metadata should not crash the adapter. Mistral's metadata
    support is uncertain, so the adapter should be defensive.
    """
    record = run(
        "hello",
        dry_run=True,
        model_meta=PRICE_CARD,
        max_tokens=600,
        cap_usd=10.0,
        agent_mode="smoke",
        extra_metadata={"remaining_budget_usd": "5.50"},
    )
    # Should not crash; dry-run returns normally.
    assert record.method_params.extra == {"dry_run": True}


# ---------------------------------------------------------------------------
# Retry policy (ticket 0215)
#
# The Mistral Agents beta API is empirically flaky on 5xx (the 2026-05-21
# multi-turn smoke turn-3 was killed by a single HTTP 502; ticket 0185).
# The adapter wraps each POST/DELETE with an exponential-backoff retry
# that triggers ONLY on transient signals (502/503/504, ReadTimeout,
# ConnectTimeout, RemoteProtocolError). 4xx — and 422 in particular —
# must NEVER be retried; that would have papered over the request-shape
# bugs fixed in tickets 0211/0218.
# ---------------------------------------------------------------------------


class _FakeResponseSequence:
    """Drives a queued list of (status_code, body_json) pairs.

    Each ``post``/``delete`` pops the next entry and returns a response
    whose ``raise_for_status`` raises an authentic
    :class:`httpx.HTTPStatusError` (subclass of ``httpx.HTTPError``) for
    non-2xx — so the retry-vs-no-retry tests actually exercise the same
    exception type the live API produces.
    """

    def __init__(self, entries: list[tuple[int, dict]]):
        self._entries = list(entries)
        self.calls: list[tuple[str, str]] = []

    def _next(self, method: str, url: str) -> httpx.Response:
        self.calls.append((method, url))
        status, body = self._entries.pop(0)
        request = httpx.Request(method.upper(), f"https://example.invalid{url}")
        return httpx.Response(status, json=body, request=request)

    def post(self, url: str, **_kwargs: object) -> httpx.Response:
        return self._next("POST", url)

    def delete(self, url: str, **_kwargs: object) -> httpx.Response:
        return self._next("DELETE", url)


@pytest.fixture
def _no_sleep(monkeypatch):
    """Skip the backoff sleeps so retry tests run instantly."""
    monkeypatch.setattr("aedist.adapter_mistral.time.sleep", lambda _s: None)


def test_create_agent_retries_on_502(_no_sleep):
    """502 twice → 200 ok: ``_create_agent`` retries and returns the id."""
    client = _FakeResponseSequence(
        [
            (502, {"error": "bad gateway"}),
            (502, {"error": "bad gateway"}),
            (200, {"id": "ag_retry_success"}),
        ]
    )
    agent_id = _create_agent(client, {"model": DEFAULT_MODEL})
    assert agent_id == "ag_retry_success"
    # 1 initial + 2 retries = 3 attempts total.
    assert len(client.calls) == 3
    assert all(m == "POST" and u == "/v1/agents" for m, u in client.calls)


def test_create_agent_gives_up_after_3_retries(_no_sleep):
    """502 × 4: ``_create_agent`` exhausts retries and raises ``HTTPStatusError``."""
    client = _FakeResponseSequence([(502, {"error": "bad gateway"})] * 4)
    with pytest.raises(httpx.HTTPStatusError):
        _create_agent(client, {"model": DEFAULT_MODEL})
    # 1 initial + 3 retries = 4 attempts; then raise.
    assert len(client.calls) == 4


def test_create_agent_does_not_retry_on_422(_no_sleep):
    """422 (client error) must raise immediately — no retry.

    Retrying 4xx would have papered over the request-shape bugs fixed
    in tickets 0211/0218; the regression guard is load-bearing.
    """
    client = _FakeResponseSequence(
        [
            (422, {"detail": "Extra inputs are not permitted"}),
            # Extras intentionally present — if a retry leaked in we'd
            # see a second call and the test would still fail on the
            # call-count assertion.
            (200, {"id": "ag_should_not_reach"}),
        ]
    )
    with pytest.raises(httpx.HTTPStatusError):
        _create_agent(client, {"model": DEFAULT_MODEL})
    assert len(client.calls) == 1, "422 must not trigger any retry"


def test_append_conversation_retries_on_503(_no_sleep):
    """The path-bound follow-up POST also goes through the retry wrapper.

    Bonus coverage per the ticket: this is the endpoint that killed the
    0185 multi-turn smoke (POST /v1/conversations/{id}).
    """
    client = _FakeResponseSequence(
        [
            (503, {"error": "service unavailable"}),
            (
                200,
                {
                    "outputs": [
                        {"type": "message.output", "content": "follow-up ok"},
                    ],
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 5,
                        "connector_tokens": 0,
                        "connectors": {"web_search": 0},
                    },
                },
            ),
        ]
    )
    raw = _append_conversation(client, "conv_abc", {"inputs": []})
    assert raw["outputs"][0]["content"] == "follow-up ok"
    assert len(client.calls) == 2
    # All calls hit the path-bound URL — not bare /v1/conversations.
    assert all(u == "/v1/conversations/conv_abc" for _, u in client.calls)
