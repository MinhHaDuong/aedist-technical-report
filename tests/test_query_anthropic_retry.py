"""Tests for aedist.query_anthropic._call_with_retry — backoff + error paths.

Pure unit tests: no network, no real SDK call. Backoff sleeps are patched out.
"""

from __future__ import annotations

import anthropic
import httpx
import pytest

from aedist.query_anthropic import _MAX_RETRIES, _call_with_retry

_REQ = httpx.Request("POST", "https://api.anthropic.com/v1/messages")


def _rate_limit() -> anthropic.RateLimitError:
    return anthropic.RateLimitError("rate limited", response=httpx.Response(429, request=_REQ), body=None)


def _status(code: int) -> anthropic.APIStatusError:
    return anthropic.APIStatusError("status", response=httpx.Response(code, request=_REQ), body=None)


def _conn() -> anthropic.APIConnectionError:
    return anthropic.APIConnectionError(message="conn dropped", request=_REQ)


class _FakeMessages:
    def __init__(self, effects):
        self._effects = list(effects)
        self.create_calls = 0

    def create(self, **kwargs):
        self.create_calls += 1
        effect = self._effects.pop(0)
        if isinstance(effect, Exception):
            raise effect
        return effect


class _FakeClient:
    def __init__(self, effects):
        self.messages = _FakeMessages(effects)


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr("aedist.query_anthropic._sleep_with_backoff", lambda attempt: None)


# NOTE: "retry-then-success" and "4xx-not-retried" with the real SDK's
# exception types are already covered in test_adapter_anthropic.py via fake
# exception classes. These tests target the previously-uncovered branches —
# retry exhaustion, connection-error retry, and the streaming fallback —
# using the *real* anthropic exception types end-to-end.


def test_rate_limit_exhaustion_raises_after_max_retries() -> None:
    client = _FakeClient([_rate_limit() for _ in range(_MAX_RETRIES + 1)])
    with pytest.raises(anthropic.RateLimitError):
        _call_with_retry(client, {})
    assert client.messages.create_calls == _MAX_RETRIES + 1


def test_5xx_retried_then_raises_on_exhaustion() -> None:
    client = _FakeClient([_status(503) for _ in range(_MAX_RETRIES + 1)])
    with pytest.raises(anthropic.APIStatusError):
        _call_with_retry(client, {})
    assert client.messages.create_calls == _MAX_RETRIES + 1


def test_connection_error_retried_then_succeeds() -> None:
    sentinel = object()
    client = _FakeClient([_conn(), sentinel])
    assert _call_with_retry(client, {}) is sentinel
    assert client.messages.create_calls == 2


class _Stream:
    def __init__(self, final):
        self._final = final

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self._final


def test_streaming_fallback_on_max_tokens_value_error() -> None:
    sentinel = object()

    class _StreamingClient:
        class messages:  # noqa: N801 - mimic SDK attribute shape
            create_calls = 0

            @classmethod
            def create(cls, **kwargs):
                cls.create_calls += 1
                raise ValueError("Streaming is required for long requests")

            @staticmethod
            def stream(**kwargs):
                return _Stream(sentinel)

    client = _StreamingClient()
    assert _call_with_retry(client, {}) is sentinel
    assert client.messages.create_calls == 1
