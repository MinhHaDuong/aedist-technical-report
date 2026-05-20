"""Shared scaffold for SOTA agent adapters.

This module defines the common Protocol, cost-cap utilities, and
dry-run formatter used by the four SOTA agent adapters under umbrella
0166:

- 0167 Anthropic Claude (web_search + adaptive thinking)
- 0168 OpenAI Responses (web_search + reasoning)
- 0169 Mistral Agents (web_search connector)
- 0173 Qwen DashScope (web_search in thinking mode)

Each adapter ships transport code only. Prompt content lives in
Phase A (ticket 0170). The Protocol is intentionally minimal —
retry/backoff/rate-limit primitives are deferred until the first
concrete adapter surfaces a real need.
"""

import json
from typing import Any, Protocol, runtime_checkable

from aedist.schema import RunRecord


class CostCapExceeded(Exception):  # noqa: N818 — name fixed by ticket 0180 spec
    """Raised when a pre-call cost estimate exceeds the configured cap."""

    pass


def estimate_call_cost(
    *,
    max_tokens: int,
    price_in: float,
    price_out: float,
    n_searches: int = 0,
    price_per_search: float = 0.0,
) -> float:
    """Conservative upper bound on the dollar cost of a single agent call.

    Upper bound — assumes ``max_tokens`` are billed at both the input and
    output rates (a deliberate double-count) and adds the per-search fee.
    """
    return max_tokens * (price_in + price_out) + n_searches * price_per_search


def enforce_cost_cap(estimated_usd: float, cap_usd: float = 10.0) -> None:
    """Raise ``CostCapExceeded`` if ``estimated_usd`` exceeds ``cap_usd``."""
    if estimated_usd > cap_usd:
        raise CostCapExceeded(f"estimated ${estimated_usd:.4f} exceeds cap ${cap_usd:.2f}")


def format_dry_run(payload: dict) -> str:
    """Return a deterministic pretty-printed JSON representation of ``payload``.

    Keys are sorted so dry-run diffs are stable across adapters.
    """
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)


@runtime_checkable
class AgentAdapter(Protocol):
    """Common surface for SOTA-agent adapters (tickets 0167/0168/0169/0173)."""

    def build_request(
        self,
        prompt: str,
        *,
        model: str,
        max_tokens: int,
        **opts: Any,
    ) -> dict:
        """Assemble the provider-specific request payload."""
        ...

    def parse_response(self, resp: Any, model_meta: dict) -> RunRecord:
        """Convert a provider response object into a canonical ``RunRecord``."""
        ...

    def run(
        self,
        prompt: str,
        *,
        dry_run: bool,
        **opts: Any,
    ) -> RunRecord:
        """Execute one agent call (or print the dry-run payload) and return a record."""
        ...
