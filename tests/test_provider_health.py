"""Tests for aedist.provider_health — failure classification state machine.

Covers three failure dispositions:

* ``HARD_STOP`` — credit exhausted / daily cap. Provider is dead for the
  remainder of the sweep; remaining cells get parked.
* ``SOFT_RETRY`` — transient rate limit / 503 / timeout. Backoff, retry,
  promote to HARD_STOP after N attempts.
* ``PERMANENT_SKIP`` — 403 region-locked, 404 model removed, Ollama
  connection refused. Cache in session, never retry.

All tests use fixtures or stubbed exceptions. No live API calls.
"""

import json
from types import SimpleNamespace

from aedist.provider_health import (
    Disposition,
    ProviderHealth,
    classify_exception,
    park_cell,
)

# ---------------------------------------------------------------------------
# Fixtures: synthetic exceptions that look like openai.APIError
# ---------------------------------------------------------------------------


def _make_api_error(
    status_code: int,
    *,
    error_type: str | None = None,
    code: int | str | None = None,
    message: str = "",
    metadata: dict | None = None,
):
    """Build a stub exception mimicking the relevant bits of openai.APIError.

    The real openai SDK surfaces provider errors via ``APIStatusError`` with
    a ``.status_code`` attribute and a ``.body`` dict carrying the upstream
    ``error`` object. OpenRouter puts its richer classification in
    ``error.code`` (a numeric HTTP-ish code) and ``error.metadata``.
    """

    body = {
        "error": {
            "message": message,
            "type": error_type,
            "code": code,
            "metadata": metadata or {},
        }
    }
    exc = SimpleNamespace(
        status_code=status_code,
        body=body,
        message=message,
        response=SimpleNamespace(status_code=status_code),
    )
    # openai.APIError is not raised directly here; classify_exception
    # duck-types on .status_code / .body, so any object works.
    return exc


# ---------------------------------------------------------------------------
# classify_exception: HTTP status mapping
# ---------------------------------------------------------------------------


def test_classify_402_is_hard_stop():
    exc = _make_api_error(402, message="Insufficient credits")
    assert classify_exception(exc).disposition is Disposition.HARD_STOP


def test_classify_openrouter_code_402_is_hard_stop():
    """OpenRouter sometimes wraps a 402 upstream inside an HTTP 200/4xx shell
    with the real code in ``error.code``. Catch that."""
    exc = _make_api_error(429, code=402, message="Upstream out of credit")
    assert classify_exception(exc).disposition is Disposition.HARD_STOP


def test_classify_429_quota_exceeded_is_hard_stop():
    exc = _make_api_error(429, error_type="quota_exceeded", message="daily quota reached")
    assert classify_exception(exc).disposition is Disposition.HARD_STOP


def test_classify_429_daily_cap_body_is_hard_stop():
    exc = _make_api_error(429, message="You reached your daily usage limit")
    assert classify_exception(exc).disposition is Disposition.HARD_STOP


def test_classify_429_short_window_is_soft_retry():
    exc = _make_api_error(429, error_type="rate_limit_exceeded", message="slow down, 3 per minute")
    assert classify_exception(exc).disposition is Disposition.SOFT_RETRY


def test_classify_503_is_soft_retry():
    exc = _make_api_error(503, message="service unavailable")
    assert classify_exception(exc).disposition is Disposition.SOFT_RETRY


def test_classify_403_is_permanent_skip():
    exc = _make_api_error(403, error_type="forbidden", message="region not supported")
    assert classify_exception(exc).disposition is Disposition.PERMANENT_SKIP


def test_classify_404_is_permanent_skip():
    exc = _make_api_error(404, message="model not found")
    assert classify_exception(exc).disposition is Disposition.PERMANENT_SKIP


def test_classify_ollama_connection_refused_is_permanent_skip():
    """Ollama returns ConnectionRefusedError from httpx when the daemon is
    down. Treat it as permanent-skip for the session; a separate health
    check can re-enable later."""
    exc = ConnectionRefusedError("connection refused")
    assert classify_exception(exc).disposition is Disposition.PERMANENT_SKIP


def test_classify_generic_timeout_is_soft_retry():
    exc = TimeoutError("read timed out")
    assert classify_exception(exc).disposition is Disposition.SOFT_RETRY


def test_classify_httpx_connect_error_is_soft_retry():
    """Genuine network hiccups from httpx bubble up as soft retries."""
    import httpx

    exc = httpx.ConnectError("connect failed")
    assert classify_exception(exc).disposition is Disposition.SOFT_RETRY


def test_unknown_exception_propagates():
    """A programming bug (RuntimeError, KeyError, etc.) must NOT be
    swallowed by the retry loop. Let it propagate so the real bug is
    visible instead of being masked as 'provider was capped'."""
    import pytest

    exc = RuntimeError("bug in dispatch code")
    with pytest.raises(RuntimeError, match="bug in dispatch code"):
        classify_exception(exc)


# ---------------------------------------------------------------------------
# OpenRouter upstream provider attribution
# ---------------------------------------------------------------------------


def test_classify_extracts_openrouter_upstream_provider():
    exc = _make_api_error(
        402,
        code=402,
        message="Insufficient credits",
        metadata={"provider_name": "DeepInfra"},
    )
    verdict = classify_exception(exc)
    assert verdict.upstream_provider == "DeepInfra"


# ---------------------------------------------------------------------------
# ProviderHealth session state
# ---------------------------------------------------------------------------


def test_health_blocks_model_after_hard_stop():
    health = ProviderHealth()
    exc = _make_api_error(402)
    health.record_failure("openrouter", "deepseek/deepseek-chat", exc)
    assert health.is_blocked("openrouter", "deepseek/deepseek-chat")


def test_health_blocks_whole_provider_after_hard_stop_family():
    """A hard_stop should block every model under that router for the
    remainder of the session (credit exhaustion is router-wide)."""
    health = ProviderHealth()
    exc = _make_api_error(402)
    health.record_failure("openrouter", "deepseek/deepseek-chat", exc)
    assert health.is_blocked("openrouter", "moonshot/kimi-k2")


def test_health_permanent_skip_only_blocks_one_model():
    """PERMANENT_SKIP must NOT take down the whole provider — 403 on one
    region-locked model should not stop Kimi from running on the same
    router."""
    health = ProviderHealth()
    exc = _make_api_error(403)
    health.record_failure("openrouter", "anthropic/claude-region-x", exc)
    assert health.is_blocked("openrouter", "anthropic/claude-region-x")
    assert not health.is_blocked("openrouter", "moonshot/kimi-k2")


def test_health_soft_retry_does_not_block_immediately():
    health = ProviderHealth()
    exc = _make_api_error(503)
    health.record_failure("openrouter", "deepseek/deepseek-chat", exc)
    assert not health.is_blocked("openrouter", "deepseek/deepseek-chat")


def test_health_soft_retry_promotes_after_n_attempts():
    """After N=3 soft retries, the failing cell should be blocked."""
    health = ProviderHealth(soft_retry_limit=3)
    exc = _make_api_error(503)
    for _ in range(3):
        health.record_failure("openrouter", "deepseek/deepseek-chat", exc)
    assert health.is_blocked("openrouter", "deepseek/deepseek-chat")


def test_soft_retry_promotion_scopes_to_model():
    """A flaky single model must not take down every other model on the
    same router. Soft-retry promotion is model-scoped; only genuine
    router-wide errors (402 credit) hard-stop the whole router."""
    health = ProviderHealth(soft_retry_limit=3)
    exc = _make_api_error(503)
    for _ in range(3):
        health.record_failure("openrouter", "deepseek/deepseek-chat", exc)
    # The flaky model is blocked...
    assert health.is_blocked("openrouter", "deepseek/deepseek-chat")
    # ...but other models on the same router remain runnable.
    assert not health.is_blocked("openrouter", "moonshot/kimi-k2")
    assert not health.is_blocked("openrouter", "anthropic/claude-sonnet")


def test_hard_stop_on_account_credit_blocks_whole_router():
    """A 402 payment-required error is account-wide: the whole router
    must be blocked, not just the model that happened to trigger it."""
    health = ProviderHealth()
    exc = _make_api_error(402, message="Insufficient credits")
    health.record_failure("openrouter", "deepseek/deepseek-chat", exc)
    assert health.is_blocked("openrouter", "deepseek/deepseek-chat")
    assert health.is_blocked("openrouter", "moonshot/kimi-k2")
    assert health.is_blocked("openrouter", "anthropic/claude-sonnet")


def test_health_success_resets_soft_retry_counter():
    health = ProviderHealth(soft_retry_limit=3)
    exc = _make_api_error(503)
    health.record_failure("openrouter", "deepseek/deepseek-chat", exc)
    health.record_failure("openrouter", "deepseek/deepseek-chat", exc)
    health.record_success("openrouter", "deepseek/deepseek-chat")
    # Two more failures should not yet promote.
    health.record_failure("openrouter", "deepseek/deepseek-chat", exc)
    health.record_failure("openrouter", "deepseek/deepseek-chat", exc)
    assert not health.is_blocked("openrouter", "deepseek/deepseek-chat")


def test_health_block_reason_is_readable():
    health = ProviderHealth()
    exc = _make_api_error(402, message="out of credit")
    health.record_failure("openrouter", "deepseek/deepseek-chat", exc)
    reason = health.block_reason("openrouter", "deepseek/deepseek-chat")
    assert reason is not None
    assert "hard_stop" in reason.lower() or "402" in reason


# ---------------------------------------------------------------------------
# parked.jsonl writer
# ---------------------------------------------------------------------------


def test_park_cell_writes_jsonl_record(tmp_path):
    park_cell(
        tmp_path,
        sweep_id="ablation_rag_p1",
        model_id="deepseek/deepseek-chat",
        run=2,
        prompt_hash="abc123",
        prompt_path="experiments/prompts/rag_v2.txt",
        reason="hard_stop: 402 insufficient credits",
    )
    parked_file = tmp_path / "parked.jsonl"
    assert parked_file.exists()
    records = [json.loads(line) for line in parked_file.read_text().splitlines()]
    assert len(records) == 1
    rec = records[0]
    assert rec["sweep_id"] == "ablation_rag_p1"
    assert rec["model_id"] == "deepseek/deepseek-chat"
    assert rec["run"] == 2
    assert rec["prompt_hash"] == "abc123"
    assert rec["prompt_path"] == "experiments/prompts/rag_v2.txt"
    assert "hard_stop" in rec["reason"]
    assert "parked_at" in rec


def test_park_cell_full_sha256_digest_and_path_for_drift_detection(tmp_path):
    """A parked record must carry the full 64-char SHA-256 of the prompt
    and the source path that was hashed. The resume path uses the pair
    to tell 'same prompt, resume safe' from 'prompt edited, stop and
    ask'. Truncated hashes collide; missing paths leave the resumer
    with no reference point."""
    import hashlib

    prompt_text = "Estimate Vietnam 2050 emissions under BAU."
    full_digest = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
    assert len(full_digest) == 64

    park_cell(
        tmp_path,
        sweep_id="s",
        model_id="m",
        run=1,
        prompt_hash=full_digest,
        prompt_path="prompts/vn_2050.txt",
        reason="hard_stop",
    )
    rec = json.loads((tmp_path / "parked.jsonl").read_text().splitlines()[0])
    assert rec["prompt_hash"] == full_digest
    assert len(rec["prompt_hash"]) == 64
    assert rec["prompt_path"] == "prompts/vn_2050.txt"


def test_park_cell_prompt_path_none_for_in_memory_prompts(tmp_path):
    """When the prompt is assembled from modules in memory there is no
    single source file. ``prompt_path`` must be stored as JSON null —
    never a fabricated path."""
    park_cell(
        tmp_path,
        sweep_id="s",
        model_id="m",
        run=1,
        prompt_hash="a" * 64,
        reason="hard_stop",
    )
    rec = json.loads((tmp_path / "parked.jsonl").read_text().splitlines()[0])
    assert "prompt_path" in rec
    assert rec["prompt_path"] is None


def test_park_cell_appends(tmp_path):
    park_cell(
        tmp_path,
        sweep_id="s",
        model_id="m1",
        run=1,
        prompt_hash="h",
        reason="hard_stop",
    )
    park_cell(
        tmp_path,
        sweep_id="s",
        model_id="m2",
        run=1,
        prompt_hash="h",
        reason="permanent_skip",
    )
    lines = (tmp_path / "parked.jsonl").read_text().splitlines()
    assert len(lines) == 2


# ---------------------------------------------------------------------------
# Integration sketch: sweep loop consults health before dispatch
# ---------------------------------------------------------------------------


def test_sweep_parks_remaining_cells_after_hard_stop(tmp_path):
    """Simulate the sweep loop contract: when one cell hard-stops, the
    remaining cells under the same provider are parked without dispatch."""

    health = ProviderHealth()
    models = [
        {"id": "deepseek/deepseek-chat", "router": "openrouter"},
        {"id": "deepseek/deepseek-chat", "router": "openrouter"},
        {"id": "deepseek/deepseek-chat", "router": "openrouter"},
    ]
    dispatches = 0
    parks: list[tuple[str, int]] = []

    class PaymentRequiredError(Exception):
        def __init__(self):
            super().__init__("402")
            self.status_code = 402
            self.body = {"error": {"code": 402, "message": "insufficient"}}

    # Pretend the first call raises 402.
    def fake_dispatch(model, run):
        nonlocal dispatches
        dispatches += 1
        raise PaymentRequiredError()

    for run, model in enumerate(models, start=1):
        if health.is_blocked(model["router"], model["id"]):
            park_cell(
                tmp_path,
                sweep_id="t",
                model_id=model["id"],
                run=run,
                prompt_hash="h",
                reason=health.block_reason(model["router"], model["id"]) or "blocked",
            )
            parks.append((model["id"], run))
            continue
        try:
            fake_dispatch(model, run)
        except Exception as exc:
            health.record_failure(model["router"], model["id"], exc)
            park_cell(
                tmp_path,
                sweep_id="t",
                model_id=model["id"],
                run=run,
                prompt_hash="h",
                reason=health.block_reason(model["router"], model["id"]) or "failed",
            )
            parks.append((model["id"], run))

    assert dispatches == 1  # only the first one tried
    assert len(parks) == 3  # all three parked
    parked_lines = (tmp_path / "parked.jsonl").read_text().splitlines()
    assert len(parked_lines) == 3
