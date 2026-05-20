"""Unit tests for the shared SOTA adapter scaffold (ticket 0180).

Pure unit tests — no subprocess, no sleep, no network. Belong in
`make check-fast`.
"""

from typing import Any

import pytest

from aedist.adapter_base import (
    AgentAdapter,
    CostCapExceeded,
    enforce_cost_cap,
    estimate_call_cost,
    format_dry_run,
)
from aedist.schema import RunRecord

# ---------------------------------------------------------------------------
# estimate_call_cost
# ---------------------------------------------------------------------------


def test_estimate_call_cost_no_searches():
    # Asymmetric numbers so swapping price_in/price_out would still pass,
    # but swapping max_tokens with a price would not.
    # 1000 * (0.003 + 0.015) = 18.0
    assert estimate_call_cost(max_tokens=1000, price_in=0.003, price_out=0.015) == pytest.approx(
        18.0
    )


def test_estimate_call_cost_search_only():
    # Token side zero, search side priced.
    # 7 * 0.025 = 0.175
    result = estimate_call_cost(
        max_tokens=0,
        price_in=0.0,
        price_out=0.0,
        n_searches=7,
        price_per_search=0.025,
    )
    assert result == pytest.approx(0.175)


def test_estimate_call_cost_mixed():
    # 500 * (0.001 + 0.004) + 3 * 0.01 = 2.5 + 0.03 = 2.53
    result = estimate_call_cost(
        max_tokens=500,
        price_in=0.001,
        price_out=0.004,
        n_searches=3,
        price_per_search=0.01,
    )
    assert result == pytest.approx(2.53)


def test_estimate_call_cost_asymmetric_arguments():
    # Verify operand order matters: swapping max_tokens and n_searches
    # would yield a different number. This catches accidental
    # operand-swap regressions.
    a = estimate_call_cost(
        max_tokens=100,
        price_in=0.01,
        price_out=0.02,
        n_searches=2,
        price_per_search=0.5,
    )
    b = estimate_call_cost(
        max_tokens=2,
        price_in=0.01,
        price_out=0.02,
        n_searches=100,
        price_per_search=0.5,
    )
    assert a != b
    # a = 100 * 0.03 + 2 * 0.5 = 3.0 + 1.0 = 4.0
    assert a == pytest.approx(4.0)
    # b = 2 * 0.03 + 100 * 0.5 = 0.06 + 50.0 = 50.06
    assert b == pytest.approx(50.06)


# ---------------------------------------------------------------------------
# enforce_cost_cap
# ---------------------------------------------------------------------------


def test_enforce_cost_cap_below_cap_returns_silently():
    # Should not raise.
    assert enforce_cost_cap(5.0, cap_usd=10.0) is None


def test_enforce_cost_cap_at_cap_returns_silently():
    # Equal is allowed (not greater than).
    assert enforce_cost_cap(10.0, cap_usd=10.0) is None


def test_enforce_cost_cap_above_cap_raises_with_both_numbers():
    with pytest.raises(CostCapExceeded) as excinfo:
        enforce_cost_cap(12.3456, cap_usd=10.0)
    msg = str(excinfo.value)
    # Both numbers must appear in the message so the operator can see
    # the estimate and the cap at a glance.
    assert "12.3456" in msg
    assert "10.00" in msg


def test_enforce_cost_cap_default_cap_is_ten():
    # Confirms the documented $10 default matches the synopsis budget.
    with pytest.raises(CostCapExceeded):
        enforce_cost_cap(10.01)


# ---------------------------------------------------------------------------
# format_dry_run
# ---------------------------------------------------------------------------


def test_format_dry_run_is_deterministic():
    payload = {"model": "claude-opus-4-7", "max_tokens": 1024, "tools": []}
    a = format_dry_run(payload)
    b = format_dry_run(payload)
    assert a == b


def test_format_dry_run_sorts_keys():
    # Different insertion orders must produce identical output.
    p1 = {"z": 1, "a": 2, "m": 3}
    p2 = {"a": 2, "m": 3, "z": 1}
    out1 = format_dry_run(p1)
    out2 = format_dry_run(p2)
    assert out1 == out2
    # And the order is alphabetical.
    assert out1.index('"a"') < out1.index('"m"') < out1.index('"z"')


def test_format_dry_run_preserves_unicode():
    payload = {"prompt": "Vietnam — coal plants"}
    out = format_dry_run(payload)
    # ensure_ascii=False keeps the em dash readable.
    assert "—" in out


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class _StubAdapter:
    """Minimal stub implementing the AgentAdapter Protocol."""

    def build_request(
        self,
        prompt: str,
        *,
        model: str,
        max_tokens: int,
        **opts: Any,
    ) -> dict:
        return {"prompt": prompt, "model": model, "max_tokens": max_tokens}

    def parse_response(self, resp: Any, model_meta: dict) -> RunRecord:
        return RunRecord(method="frontier", method_params={"model": "stub"})

    def run(self, prompt: str, *, dry_run: bool, **opts: Any) -> RunRecord:
        return RunRecord(method="frontier", method_params={"model": "stub"})


def test_stub_adapter_satisfies_protocol():
    stub = _StubAdapter()
    assert isinstance(stub, AgentAdapter)


def test_stub_adapter_methods_are_actually_callable():
    # @runtime_checkable only checks method presence, not signatures.
    # Exercise each method so a broken signature is caught here.
    stub = _StubAdapter()
    payload = stub.build_request("hello", model="m", max_tokens=10)
    assert payload["prompt"] == "hello"
    assert payload["model"] == "m"
    assert payload["max_tokens"] == 10

    record = stub.parse_response(resp=None, model_meta={})
    assert isinstance(record, RunRecord)

    record2 = stub.run("hello", dry_run=True)
    assert isinstance(record2, RunRecord)


def test_non_adapter_object_fails_protocol_check():
    class _NotAnAdapter:
        def build_request(self, *a, **k):
            return {}

        # missing parse_response and run

    assert not isinstance(_NotAnAdapter(), AgentAdapter)
