"""Mistral Agents API adapter with the built-in web_search connector.

Ticket: 0169 (umbrella 0166, SOTA frontier-API experiment).

HTTP shape verified directly against the live Mistral API on 2026-05-20
(see tickets/0169-adapter-mistral-agents-websearch.erg log entry):

- POST /v1/agents          create     -> returns {"id": "ag_..."}
- POST /v1/conversations   invoke     -> returns {outputs[], usage{...}}
- DELETE /v1/agents/{id}   cleanup    -> HTTP 204

Docs: https://docs.mistral.ai/agents/connectors/websearch/  (verified
2026-05-20). The Agents + Conversations endpoints are still flagged
beta on the docs site; re-verify shape if implementation lands more
than ~30 days from the verification date above.

Persistent-agent strategy: this adapter creates and deletes the agent
inline in :func:`run` (one create + one invoke + one delete per call).
Phase-B suites that issue many calls against the same agent config
should hoist creation up the call stack — but that caching layer is a
Phase-B concern (raid plan §0169) and is intentionally NOT implemented
here.

Pricing notes:

- ``usage.connector_tokens`` is a *separately billed* token bucket — it
  must NOT be folded into ``tokens_in``/``tokens_out``. We surface its
  dollar value via :attr:`RunRecord.tool_calls_cost_usd` and break it
  out in ``ResourceUse.cost_breakdown`` under the ``connector`` key.
- ``usage.connectors.web_search`` is a count of executed search calls
  and matches ``len(outputs[type=tool.execution])`` in a healthy
  response (the test asserts this invariant).
"""

import json
import logging
import os
import random
import time
from pathlib import Path
from typing import Any

import httpx

from aedist.adapter_base import enforce_cost_cap, estimate_call_cost, format_dry_run
from aedist.schema import MethodParams, ResourceUse, ResultSummary, RunRecord

log = logging.getLogger(__name__)

AGENT_FAMILY = "mistral-direct"
DEFAULT_MODEL = "mistral-large-2512"
API_BASE = "https://api.mistral.ai"
API_DOCS_VERIFIED = "2026-05-20"
KEY_PATH = Path.home() / ".config" / "keys" / "mistral.env"
TOKENS_PER_MTOK = 1_000_000


# ---------------------------------------------------------------------------
# Key loading
# ---------------------------------------------------------------------------


def _load_api_key(path: Path = KEY_PATH) -> str:
    """Read ``MISTRAL_API_KEY`` from ``~/.config/keys/mistral.env``.

    Falls back to the environment variable of the same name so callers
    can override in tests. Raises ``SystemExit`` if neither is set.
    """
    if path.exists():
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("MISTRAL_API_KEY="):
                value = line.split("=", 1)[1].strip()
                # Strip surrounding quotes if present.
                if value and value[0] in {'"', "'"} and value[-1] == value[0]:
                    value = value[1:-1]
                if value:
                    return value
    env = os.environ.get("MISTRAL_API_KEY")
    if env:
        return env
    raise SystemExit(f"MISTRAL_API_KEY not found in {path} or environment")


# ---------------------------------------------------------------------------
# Request assembly (Protocol surface: build_request)
# ---------------------------------------------------------------------------


def build_request(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 600,
    **opts: Any,
) -> dict:
    """Assemble the two-step request bodies for create-agent + invoke.

    The Mistral Agents API requires two POSTs per call (create the agent
    instance, then start a conversation against it). Returning both
    bodies in a single dict keeps the dry-run output complete and lets
    callers inspect exactly what will be sent. ``opts`` is reserved for
    future per-call settings (e.g. ``temperature``); unknown keys are
    ignored so the adapter remains forward-compatible with raid-plan
    callers that pass extra metadata.

    Note on ``max_tokens``: empirically (2026-05-20 derisk) the
    ``POST /v1/conversations`` endpoint *rejects* ``max_tokens`` with
    HTTP 422 ("Extra inputs are not permitted"). It must be set at
    agent-create time (``completion_args.max_tokens``) rather than per
    conversation. We therefore push the cap into the agent body and
    leave the conversation body free of it.
    """
    del opts  # reserved for future overrides; intentionally unused
    agent_body = {
        "model": model,
        "name": "aedist-sota-agent",
        "description": "AEDIST SOTA experiment agent with web_search connector.",
        "tools": [{"type": "web_search"}],
        "completion_args": {"max_tokens": max_tokens},
    }
    conversation_body = {
        "agent_id": "<assigned-after-agent-create>",
        "inputs": [{"role": "user", "content": prompt}],
    }
    return {
        "agent_create": {"method": "POST", "path": "/v1/agents", "body": agent_body},
        "conversation_start": {
            "method": "POST",
            "path": "/v1/conversations",
            "body": conversation_body,
        },
        "agent_delete": {"method": "DELETE", "path": "/v1/agents/{agent_id}"},
    }


# ---------------------------------------------------------------------------
# Cost computation
# ---------------------------------------------------------------------------


def _compute_costs(usage: dict, price_card: dict) -> tuple[float, float, dict]:
    """Compute (token_cost_usd, connector_cost_usd, cost_breakdown).

    Token cost is the standard input/output split. Connector cost comes
    from ``usage.connector_tokens`` at the registry's
    ``price_per_connector_mtok`` rate when present; if the registry
    instead carries a flat ``price_per_web_search_call_usd``, fall back
    to ``usage.connectors.web_search`` × that flat price. This lets the
    pricing card evolve as Mistral clarifies billing without changing
    adapter logic.
    """
    p_in = float(price_card.get("price_per_mtok_in", 0.0))
    p_out = float(price_card.get("price_per_mtok_out", 0.0))
    tokens_in = int(usage.get("prompt_tokens", 0) or 0)
    tokens_out = int(usage.get("completion_tokens", 0) or 0)
    input_cost = tokens_in * p_in / TOKENS_PER_MTOK
    output_cost = tokens_out * p_out / TOKENS_PER_MTOK
    token_cost = input_cost + output_cost

    connector_tokens = int(usage.get("connector_tokens", 0) or 0)
    n_searches = int((usage.get("connectors") or {}).get("web_search", 0) or 0)
    p_conn_mtok = price_card.get("price_per_connector_mtok")
    p_per_call = price_card.get("price_per_web_search_call_usd")
    if p_conn_mtok is not None:
        connector_cost = connector_tokens * float(p_conn_mtok) / TOKENS_PER_MTOK
    elif p_per_call is not None:
        connector_cost = n_searches * float(p_per_call)
    else:
        connector_cost = 0.0

    breakdown = {"input": input_cost, "output": output_cost}
    if connector_cost > 0:
        breakdown["connector"] = connector_cost
    return token_cost, connector_cost, breakdown


# ---------------------------------------------------------------------------
# Response parsing (Protocol surface: parse_response)
# ---------------------------------------------------------------------------


def parse_response(
    resp: dict,
    model_meta: dict,
    *,
    wall_s: float | None = None,
    agent_mode: str = "smoke",
    prompt: str = "",
) -> RunRecord:
    """Convert a Mistral conversations response into a :class:`RunRecord`.

    Walks ``resp["outputs"]`` exactly once:

    - ``type == "tool.execution"`` with ``name == "web_search"`` → one
      entry in :attr:`RunRecord.web_search_calls`. The search query is
      parsed from the JSON-encoded ``arguments`` string.
    - ``type == "message.output"`` → ``content`` is empirically one of
      two shapes:
        * ``list[dict]`` of typed chunks (2026-05-20 derisk fixture) —
          iterate; ``type == "text"`` chunks join the narrative,
          ``type == "tool_reference"`` chunks become citations.
        * ``str`` — a flat narrative inline (observed live 2026-05-21
          in the Exp 2 smoke, ticket 0185 / fix 0206). The whole string
          is the narrative; no tool-reference markup is carried.
    """
    web_search_calls: list[dict] = []
    citations: list[dict] = []
    narrative_chunks: list[str] = []

    for item in resp.get("outputs", []):
        kind = item.get("type")
        if kind == "tool.execution" and item.get("name") == "web_search":
            query = _extract_query(item.get("arguments"))
            web_search_calls.append({"query": query, "urls_returned": []})
        elif kind == "message.output":
            content = item.get("content")
            # Flat-string shape (ticket 0206) — whole string is the
            # narrative; nothing else to extract.
            if isinstance(content, str):
                narrative_chunks.append(content)
                continue
            for chunk in content or []:
                ctype = chunk.get("type")
                if ctype == "text":
                    narrative_chunks.append(chunk.get("text", ""))
                elif ctype == "tool_reference":
                    citations.append(
                        {
                            "url": chunk.get("url", ""),
                            "snippet": chunk.get("description"),
                            "supports_claim": None,
                            "title": chunk.get("title"),
                        }
                    )

    narrative = "".join(narrative_chunks).strip()
    usage = resp.get("usage", {}) or {}
    token_cost, connector_cost, breakdown = _compute_costs(usage, model_meta)

    record = RunRecord(
        method="frontier",
        method_params=MethodParams(
            model=model_meta.get("model_id", DEFAULT_MODEL),
            max_tokens=usage.get("completion_tokens"),
            extra={"prompt_preview": prompt[:200] if prompt else None},
        ),
        resource_use=ResourceUse(
            wall_s=wall_s,
            cost_usd=token_cost,
            tokens_in=usage.get("prompt_tokens"),
            tokens_out=usage.get("completion_tokens"),
            cost_breakdown=breakdown,
        ),
        result_summary=ResultSummary(status="ok" if narrative else "empty"),
        agent_family=AGENT_FAMILY,
        agent_mode=agent_mode,
        web_search_calls=web_search_calls,
        citations=citations,
        tool_calls_cost_usd=connector_cost,
        finish_reason=resp.get("finish_reason", "stop"),
    )
    return record


def _extract_query(arguments: Any) -> str:
    """Best-effort extraction of the search query from tool-call arguments.

    Mistral returns ``arguments`` as a JSON-encoded string with a
    ``query`` key. Be tolerant — accept either the encoded string or a
    pre-parsed dict, and never raise on malformed input (the response
    is a record of what the model did, not a contract we enforce).
    """
    if arguments is None:
        return ""
    if isinstance(arguments, dict):
        return str(arguments.get("query", ""))
    if isinstance(arguments, str):
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError:
            return arguments
        if isinstance(parsed, dict):
            return str(parsed.get("query", ""))
        return str(parsed)
    return str(arguments)


# ---------------------------------------------------------------------------
# HTTP transport
# ---------------------------------------------------------------------------

# Retry policy for transient gateway / network failures on the Mistral
# Agents beta API (ticket 0215). The 2026-05-21 multi-turn smoke
# (ticket 0185) was killed by a single HTTP 502 from
# POST /v1/conversations/{id}; that endpoint is empirically flaky.
#
# Policy: max 3 retries, exponential backoff 1s/2s/4s with ±10% jitter.
# Retry only on transient signals — never on 4xx (a 4xx is a request
# bug, not a server hiccup; retrying would have papered over the 422
# bugs fixed in tickets 0211/0218).
RETRYABLE_STATUSES = frozenset({502, 503, 504})
RETRYABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    httpx.ReadTimeout,
    httpx.ConnectTimeout,
    httpx.RemoteProtocolError,
)
MAX_RETRIES = 3
BACKOFF_BASE_S = 1.0


def _sleep_with_backoff(attempt: int) -> None:
    """Sleep for ``BACKOFF_BASE_S * 2**attempt`` seconds, ±10% jitter.

    ``attempt`` is the zero-indexed retry number (0 → ~1s, 1 → ~2s,
    2 → ~4s). Extracted so tests can monkeypatch ``time.sleep`` to a
    no-op and still cover the retry control flow.
    """
    delay = BACKOFF_BASE_S * (2**attempt) * (1.0 + random.uniform(-0.1, 0.1))
    time.sleep(delay)


def _request_with_retry(
    method: str,
    client: httpx.Client,
    url: str,
    **kwargs: Any,
) -> httpx.Response:
    """Issue an HTTP request with the transient-failure retry policy.

    Wraps ``client.post``/``client.delete``. Retries on the statuses in
    :data:`RETRYABLE_STATUSES` and on the exceptions in
    :data:`RETRYABLE_EXCEPTIONS`. On 4xx (or any other non-retryable
    status), raises immediately via ``raise_for_status``. Logs every
    retry attempt with the URL and the reason so post-mortems are
    tractable. On exhaustion, raises the final status's
    ``HTTPStatusError`` (or re-raises the final exception).
    """
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):  # 1 initial + up to MAX_RETRIES
        try:
            resp = getattr(client, method)(url, **kwargs)
        except RETRYABLE_EXCEPTIONS as exc:
            last_exc = exc
            if attempt < MAX_RETRIES:
                log.warning(
                    "Mistral %s %s transient failure (%s); retry %d/%d",
                    method.upper(),
                    url,
                    type(exc).__name__,
                    attempt + 1,
                    MAX_RETRIES,
                )
                _sleep_with_backoff(attempt)
                continue
            raise
        if resp.status_code not in RETRYABLE_STATUSES:
            return resp
        if attempt < MAX_RETRIES:
            log.warning(
                "Mistral %s %s returned HTTP %d; retry %d/%d",
                method.upper(),
                url,
                resp.status_code,
                attempt + 1,
                MAX_RETRIES,
            )
            _sleep_with_backoff(attempt)
            continue
        # Out of retries — surface the final response as an HTTPStatusError.
        resp.raise_for_status()
        return resp  # unreachable; for type-checker peace of mind
    # Loop exited without return — only possible if MAX_RETRIES < 0.
    assert last_exc is not None
    raise last_exc


def _create_agent(client: httpx.Client, body: dict) -> str:
    """POST /v1/agents — returns the new agent_id (``ag_*``)."""
    resp = _request_with_retry("post", client, "/v1/agents", json=body, timeout=60.0)
    resp.raise_for_status()
    data = resp.json()
    agent_id = data.get("id")
    if not agent_id:
        raise RuntimeError(f"Mistral /v1/agents response missing 'id': {data!r}")
    return agent_id


def _start_conversation(client: httpx.Client, body: dict) -> dict:
    """POST /v1/conversations — returns the parsed response body."""
    resp = _request_with_retry("post", client, "/v1/conversations", json=body, timeout=600.0)
    resp.raise_for_status()
    return resp.json()


def _append_conversation(client: httpx.Client, conversation_id: str, body: dict) -> dict:
    """POST /v1/conversations/{id} — append a turn to an existing conversation.

    Path-bound append endpoint (Mistral Agents beta API, verified
    2026-05-21). The agent is implied by the conversation; ``agent_id``
    and ``conversation_id`` MUST NOT appear in ``body`` (HTTP 422
    otherwise — see tickets 0211/0218).
    """
    resp = _request_with_retry(
        "post",
        client,
        f"/v1/conversations/{conversation_id}",
        json=body,
        timeout=600.0,
    )
    resp.raise_for_status()
    return resp.json()


def _delete_agent(client: httpx.Client, agent_id: str) -> None:
    """DELETE /v1/agents/{id} — silent on success, logs warnings on failure.

    Cleanup must never raise to the caller — a failed delete is a
    hygiene issue, not a result failure. Orphans can be swept later via
    the Mistral console. The retry wrapper may raise ``HTTPStatusError``
    on exhaustion; ``httpx.HTTPError`` covers that subclass plus all
    transport exceptions so the contract holds.
    """
    try:
        resp = _request_with_retry("delete", client, f"/v1/agents/{agent_id}", timeout=30.0)
        if resp.status_code not in (200, 204):
            log.warning(
                "Mistral DELETE /v1/agents/%s returned HTTP %s: %s",
                agent_id,
                resp.status_code,
                resp.text[:200],
            )
    except httpx.HTTPError as exc:
        log.warning("Mistral DELETE /v1/agents/%s failed: %s", agent_id, exc)


def cleanup_agent(agent_id: str, *, api_key: str | None = None) -> None:
    """Public lifecycle cleanup: delete a Mistral agent by ID.

    The Exp 2 harness (ticket 0207) calls this at session end after
    multi-turn conversations. Accepts an optional ``api_key`` override;
    falls back to the standard key-loading path.
    """
    key = api_key or _load_api_key()
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(base_url=API_BASE, headers=headers) as client:
        _delete_agent(client, agent_id)


# ---------------------------------------------------------------------------
# Entry point (Protocol surface: run)
# ---------------------------------------------------------------------------


def run(
    prompt: str,
    *,
    dry_run: bool,
    model_meta: dict | None = None,
    max_tokens: int = 600,
    cap_usd: float = 10.0,
    agent_mode: str = "smoke",
    output_path: Path | None = None,
    continuation: dict | None = None,
    extra_metadata: dict | None = None,
    system_prompt: str | None = None,
    **opts: Any,
) -> RunRecord:
    """Execute one Mistral Agents call (or print the dry-run payload).

    Three lifecycle modes controlled by ``continuation``:

    1. ``continuation=None`` — **single-turn** (backward-compatible
       default): create agent -> invoke conversation -> delete agent.
       The delete runs in ``finally`` so no orphan ``ag_*`` is left.

    2. ``continuation={}`` (empty dict) — **first turn of multi-turn**:
       create agent -> invoke conversation -> **skip delete**. Returns
       ``agent_id`` + ``conversation_id`` in ``method_params.extra``.
       The harness must call :func:`cleanup_agent` at session end.

    3. ``continuation={"agent_id": ..., "conversation_id": ...}`` —
       **follow-up turn**: skip agent creation, send follow-up message
       to existing conversation. No create, no delete.

    ``extra_metadata`` behaviour differs by turn:

    - **Turn 1 (create + invoke):** attached as a body-level ``metadata``
      key on the ``POST /v1/conversations`` request.
    - **Follow-up turns:** the append endpoint (``POST /v1/conversations/{id}``)
      returns HTTP 422 when a ``metadata`` key is present in the body
      (confirmed empirically, ticket 0247). Instead the budget signal is
      prepended as a ``[metadata] key=value; ...`` line inside the user
      message content, matching the Qwen DashScope fallback pattern.

    ``system_prompt`` (ticket 0213) installs a designed system-level
    instruction on the Mistral agent at create time by overriding the
    default ``agent.description``. Only meaningful in modes 1 and 2 —
    the follow-up mode reuses an already-created agent, so passing
    ``system_prompt`` alongside ``continuation['agent_id']`` raises
    ``ValueError`` (fail-fast matching this codebase's history of
    dict-vs-string and HTTP 422 silent-accept incidents).

    **System-prompt surface across SOTA adapters** (for future extension
    by 0214 etc. — keep this table in sync when adding new adapters):

    +----------------+--------------------------------------------------+
    | Adapter        | Where the system prompt lives                    |
    +================+==================================================+
    | Mistral Agents | ``POST /v1/agents`` body ``description`` field   |
    +----------------+--------------------------------------------------+
    | Anthropic      | ``messages.create`` ``system`` parameter         |
    +----------------+--------------------------------------------------+
    | OpenAI         | ``instructions`` parameter on                    |
    | Responses      | ``responses.create``                             |
    +----------------+--------------------------------------------------+
    | Qwen           | ``messages[0]`` with ``role: "system"``          |
    | DashScope      |                                                  |
    +----------------+--------------------------------------------------+

    ``model_meta`` is the registry entry for the chosen model (see
    ``experiments/models.yaml``). When omitted, a minimal default is
    used so the dry-run path is still usable for ad-hoc smokes.
    """
    del opts  # reserved for forward-compat
    # Fail-fast: system_prompt cannot be set on a follow-up turn (agent
    # is already created with its description fixed). Ticket 0213.
    is_followup_call = (
        continuation is not None and continuation.get("agent_id") and system_prompt is not None
    )
    if is_followup_call:
        raise ValueError(
            "system_prompt cannot be set on a follow-up turn: the Mistral agent "
            "is already created and its description is fixed. Pass system_prompt "
            "only on the first turn (continuation=None or continuation={})."
        )
    meta = model_meta or {"model_id": DEFAULT_MODEL}
    payload = build_request(
        prompt, model=meta.get("model_id", DEFAULT_MODEL), max_tokens=max_tokens
    )
    if system_prompt is not None:
        payload["agent_create"]["body"]["description"] = system_prompt

    # Conservative cost cap — assume worst-case token usage and a few
    # connector calls. enforce_cost_cap raises CostCapExceeded if over.
    estimate = estimate_call_cost(
        max_tokens=max_tokens,
        price_in=float(meta.get("price_per_mtok_in", 0.0)) / TOKENS_PER_MTOK,
        price_out=float(meta.get("price_per_mtok_out", 0.0)) / TOKENS_PER_MTOK,
        n_searches=5,
        price_per_search=float(meta.get("price_per_web_search_call_usd", 0.02) or 0.02),
    )
    enforce_cost_cap(estimate, cap_usd=cap_usd)

    if dry_run:
        log.info("Mistral dry-run payload:\n%s", format_dry_run(payload))
        return RunRecord(
            method="frontier",
            method_params=MethodParams(
                model=meta.get("model_id", DEFAULT_MODEL),
                max_tokens=max_tokens,
                extra={"dry_run": True},
            ),
            agent_family=AGENT_FAMILY,
            agent_mode=agent_mode,
            result_summary=ResultSummary(status="qualitative"),
        )

    api_key = _load_api_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    t0 = time.monotonic()

    # Determine lifecycle mode from continuation shape.
    is_followup = continuation is not None and continuation.get("agent_id")
    is_multiturn_start = continuation is not None and not continuation.get("agent_id")
    agent_id: str | None = None

    def _attach_metadata(body: dict[str, Any]) -> None:
        if extra_metadata is not None:
            try:
                body["metadata"] = extra_metadata
            except Exception:
                log.warning("Failed to attach extra_metadata to Mistral conversation body")

    if is_followup:
        # Mode 3: follow-up turn — reuse existing agent and conversation.
        # Mistral's append-to-conversation endpoint is path-bound:
        # POST /v1/conversations/{conversation_id} with body {"inputs": [...]}.
        # The agent is implied by the existing conversation; agent_id and
        # conversation_id MUST NOT appear in the body (HTTP 422 otherwise).
        # Docs verified 2026-05-21:
        # https://docs.mistral.ai/api/endpoint/beta/conversations
        conversation_id = continuation.get("conversation_id")
        if not conversation_id:
            raise ValueError(
                "Mistral follow-up turn requires continuation['conversation_id']; "
                f"got {continuation!r}"
            )
        # Mistral's append endpoint returns HTTP 422 with a body-level
        # ``metadata`` key (confirmed ticket 0247). Preserve the budget
        # signal by prepending a machine-parseable line into the message
        # text — matching the Qwen DashScope fallback pattern.
        user_content = prompt
        if extra_metadata is not None:
            meta_text = "; ".join(f"{k}={v}" for k, v in extra_metadata.items())
            user_content = f"[metadata] {meta_text}\n{prompt}"
            log.info(
                "Mistral follow-up: extra_metadata prepended to user content "
                "(body-level metadata key causes HTTP 422 on append endpoint)"
            )
        conv_body: dict[str, Any] = {
            "inputs": [{"role": "user", "content": user_content}],
        }
        with httpx.Client(base_url=API_BASE, headers=headers) as client:
            raw = _append_conversation(client, conversation_id, conv_body)
        agent_id = continuation["agent_id"]
    else:
        # Mode 1 or 2: create agent + invoke.
        with httpx.Client(base_url=API_BASE, headers=headers) as client:
            try:
                agent_id = _create_agent(client, payload["agent_create"]["body"])
                conv_body = dict(payload["conversation_start"]["body"])
                conv_body["agent_id"] = agent_id
                _attach_metadata(conv_body)
                raw = _start_conversation(client, conv_body)
            except BaseException:
                # On failure, always clean up the agent (if created).
                if agent_id is not None:
                    _delete_agent(client, agent_id)
                raise
            # Mode 1 (single-turn): delete immediately.
            # Mode 2 (multi-turn start): keep alive.
            if not is_multiturn_start and agent_id is not None:
                _delete_agent(client, agent_id)

    wall_s = round(time.monotonic() - t0, 3)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Persist the raw response — never lose the source of truth.
        output_path.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n")
        log.info("Saved Mistral raw response to %s", output_path)

    record = parse_response(raw, meta, wall_s=wall_s, agent_mode=agent_mode, prompt=prompt)

    # Surface continuation tokens for multi-turn chaining.
    if record.method_params.extra is None:
        record.method_params.extra = {}
    # The path-bound append endpoint does not echo conversation_id in
    # its response (the caller already knew it — it was in the URL).
    # Fall back to the value we sent so >2-turn chains stay robust.
    followup_conv_id = continuation.get("conversation_id") if continuation else None
    record.method_params.extra["conversation_id"] = raw.get("conversation_id") or followup_conv_id
    if agent_id is not None:
        record.method_params.extra["agent_id"] = agent_id

    return record
