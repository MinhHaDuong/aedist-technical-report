"""Tests for the agent-mode RunRecord schema extension (ticket 0172).

The SOTA frontier-API experiment (umbrella 0166) adds new first-class
fields to RunRecord: agent identity (family/mode), spec freeze hashes,
tool-call traces (web searches + citations), reasoning trace, and an
extracted-table pointer. All additions are optional and default to
None so that the 330 pre-existing measurements.jsonl records parse
unchanged.

The metrics dict (ADR-7) projects list fields as counts so that
reporting can pivot on them without re-loading the raw record. Scalar
fields are omitted when None, matching the existing pattern in
``records_to_metrics``.
"""

from __future__ import annotations

import json

from aedist.measurements import records_to_metrics
from aedist.schema import (
    Method,
    MethodParams,
    ResourceUse,
    ResultSummary,
    RunRecord,
)

# ---------------------------------------------------------------------------
# Backward-compat fixture: real production record (measurements.jsonl line 32)
# Inlined verbatim to keep the test hermetic — no live-file dependency.
# ---------------------------------------------------------------------------

FIXTURE_LINE_32 = (
    '{"run_id": "61326a1572ec", "timestamp": "2026-04-10T17:59:04.846510Z", '
    '"method": "direct", "method_params": {"model": "deepseek/deepseek-v3.2", '
    '"temperature": null, "max_tokens": null, "prompt_version": "p1_base", '
    '"extra": {"size_class": "frontier", "country": "CN", "architecture": '
    '"moe", "provider": "DeepSeek", "context_window": 163840}}, '
    '"resource_use": {"wall_s": 79.067, "cost_usd": 0.0017366, '
    '"tokens_in": 418, "tokens_out": 4284}, "result_file": '
    '"experiments/outputs/ablation/direct/p1_base/deepseek-v3.2-run1.csv", '
    '"result_summary": {"status": "ok", "n_plants": 73, "tp": 73, "fp": 0, '
    '"fn": 90, "f1": 0.6186, "fuel_accuracy": 0.5616, "status_accuracy": '
    '0.4521, "province_accuracy": 0.6986}, "justification": null, '
    '"validation": {"ok": true, "category": "ok", "flags": []}}'
)


# ---------------------------------------------------------------------------
# First failing test (per plan: non-tautological, asymmetric lengths)
# ---------------------------------------------------------------------------


def test_records_to_metrics_projects_web_search_count_from_list_length():
    """Counts must come from ``len()`` of each list independently.

    Asymmetric lengths catch two classes of bug:
      * copy-pasted ``len(citations)`` written into both counters, and
      * a forgotten ``len(...)`` that would store the list itself.
    """
    record = RunRecord(
        method=Method.DIRECT,
        method_params=MethodParams(model="claude-opus-4-7"),
        web_search_calls=[
            {"query": "vietnam coal plants", "urls_returned": ["https://a"]},
            {"query": "vietnam gas plants", "urls_returned": ["https://b"]},
            {"query": "vietnam LNG plants", "urls_returned": ["https://c"]},
        ],
        citations=[
            {"url": "https://a", "snippet": None, "supports_claim": None},
            {"url": "https://b", "snippet": None, "supports_claim": None},
        ],
    )

    [m] = records_to_metrics([record])

    assert m["n_web_search_calls"] == 3
    assert m["n_citations"] == 2


# ---------------------------------------------------------------------------
# Backward-compat: a real pre-extension record still parses cleanly
# ---------------------------------------------------------------------------


def test_pre_extension_record_parses_with_new_fields_none():
    """Production record from before the schema extension must round-trip.

    The 330 measurements.jsonl records have no agent_* fields; loading
    them under the new schema must yield ``None`` for every new field
    and must preserve ``extra`` and ``validation`` payloads untouched.
    """
    record = RunRecord.from_jsonl_line(FIXTURE_LINE_32)

    # New top-level fields default to None.
    assert record.agent_family is None
    assert record.agent_mode is None
    assert record.synopsis_sha is None
    assert record.designed_prompt_sha is None
    assert record.web_search_calls is None
    assert record.citations is None
    assert record.parsed_table_path is None
    assert record.finish_reason is None
    assert record.retry_count is None
    assert record.error is None
    assert record.reasoning_summary is None
    assert record.tool_calls_cost_usd is None

    # New nested fields on ResourceUse default to None.
    assert record.resource_use.cost_breakdown is None
    assert record.resource_use.thinking_tokens is None

    # Existing payload preserved.
    assert record.method_params.extra is not None
    assert record.method_params.extra["architecture"] == "moe"
    assert record.method_params.extra["provider"] == "DeepSeek"
    assert record.validation == {"ok": True, "category": "ok", "flags": []}
    assert record.resource_use.cost_usd == 0.0017366
    assert record.resource_use.tokens_out == 4284


def test_pre_extension_record_metrics_omits_absent_agent_fields():
    """metrics dict must not surface keys for fields the record did not carry."""
    record = RunRecord.from_jsonl_line(FIXTURE_LINE_32)
    [m] = records_to_metrics([record])

    # All agent-mode keys absent from a non-agent record.
    for key in (
        "agent_family",
        "agent_mode",
        "synopsis_sha",
        "designed_prompt_sha",
        "n_web_search_calls",
        "n_citations",
        "parsed_table_path",
        "finish_reason",
        "retry_count",
        "error",
        "reasoning_summary",
        "thinking_tokens",
        "cost_breakdown",
        "tool_calls_cost_usd",
    ):
        assert key not in m, f"{key!r} leaked into metrics for a non-agent record"


# ---------------------------------------------------------------------------
# Round-trip: a new agent-mode record serialises and deserialises losslessly
# ---------------------------------------------------------------------------


def test_agent_mode_record_round_trips_through_jsonl():
    """Every new field must survive ``to_jsonl_line`` → ``from_jsonl_line``."""
    original = RunRecord(
        method=Method.DIRECT,
        method_params=MethodParams(model="claude-opus-4-7"),
        resource_use=ResourceUse(
            wall_s=12.3,
            cost_usd=0.19,
            tokens_in=200,
            tokens_out=600,
            cost_breakdown={"input": 0.003, "output": 0.045, "reasoning": 0.142},
            thinking_tokens=1500,
        ),
        result_summary=ResultSummary(status="ok"),
        agent_family="anthropic-direct",
        agent_mode="phase_b_run",
        synopsis_sha="a" * 40,
        designed_prompt_sha="b" * 64,
        web_search_calls=[
            {"query": "phu my 2.2", "urls_returned": ["https://example/1"]},
            {"query": "vinh tan", "urls_returned": ["https://example/2"]},
        ],
        citations=[
            {"url": "https://example/1", "snippet": "...", "supports_claim": True},
            {"url": "https://example/2", "snippet": None, "supports_claim": None},
            {"url": "https://example/3", "snippet": "third", "supports_claim": False},
        ],
        parsed_table_path="experiments/outputs/sota_smoke/anthropic_run1.csv",
        finish_reason="stop",
        retry_count=0,
        error=None,
        reasoning_summary="Considered Vietnamese coal fleet from EVN annual report.",
        tool_calls_cost_usd=0.020,
    )

    restored = RunRecord.from_jsonl_line(original.to_jsonl_line())

    assert restored.agent_family == "anthropic-direct"
    assert restored.agent_mode == "phase_b_run"
    assert restored.synopsis_sha == "a" * 40
    assert restored.designed_prompt_sha == "b" * 64
    assert restored.web_search_calls == original.web_search_calls
    assert restored.citations == original.citations
    assert restored.parsed_table_path == original.parsed_table_path
    assert restored.finish_reason == "stop"
    assert restored.retry_count == 0
    assert restored.error is None
    assert restored.reasoning_summary == original.reasoning_summary
    assert restored.tool_calls_cost_usd == 0.020
    assert restored.resource_use.cost_breakdown == {
        "input": 0.003,
        "output": 0.045,
        "reasoning": 0.142,
    }
    assert restored.resource_use.thinking_tokens == 1500


# ---------------------------------------------------------------------------
# records_to_metrics surfaces every new column when present
# ---------------------------------------------------------------------------


def test_records_to_metrics_surfaces_all_new_fields_when_present():
    """Per ADR-7: every new field flows through the metrics dict."""
    record = RunRecord(
        method=Method.DIRECT,
        method_params=MethodParams(model="gpt-5.5"),
        resource_use=ResourceUse(
            cost_breakdown={"input": 0.001, "output": 0.05, "reasoning": 0.12},
            thinking_tokens=2048,
        ),
        agent_family="openai-direct",
        agent_mode="phase_b_run",
        synopsis_sha="deadbeef" * 5,
        designed_prompt_sha="cafebabe" * 8,
        web_search_calls=[{"query": "q1", "urls_returned": []}],
        citations=[
            {"url": "u1", "snippet": None, "supports_claim": None},
            {"url": "u2", "snippet": None, "supports_claim": None},
        ],
        parsed_table_path="experiments/outputs/sota_smoke/openai.csv",
        finish_reason="stop",
        retry_count=1,
        error=None,
        reasoning_summary="Brief plan.",
        tool_calls_cost_usd=0.030,
    )

    [m] = records_to_metrics([record])

    assert m["agent_family"] == "openai-direct"
    assert m["agent_mode"] == "phase_b_run"
    assert m["synopsis_sha"] == "deadbeef" * 5
    assert m["designed_prompt_sha"] == "cafebabe" * 8
    assert m["n_web_search_calls"] == 1
    assert m["n_citations"] == 2
    assert m["parsed_table_path"] == "experiments/outputs/sota_smoke/openai.csv"
    assert m["finish_reason"] == "stop"
    assert m["retry_count"] == 1
    assert m["reasoning_summary"] == "Brief plan."
    assert m["thinking_tokens"] == 2048
    assert m["cost_breakdown"] == {"input": 0.001, "output": 0.05, "reasoning": 0.12}
    assert m["tool_calls_cost_usd"] == 0.030
    # error is None — keep omit-when-None contract.
    assert "error" not in m


def test_records_to_metrics_includes_error_when_set():
    """``error`` participates in the omit-when-None contract symmetrically."""
    record = RunRecord(
        method=Method.DIRECT,
        method_params=MethodParams(model="gpt-5.5"),
        agent_family="openai-direct",
        agent_mode="phase_b_run",
        error="rate_limit_exceeded",
        retry_count=3,
    )
    [m] = records_to_metrics([record])
    assert m["error"] == "rate_limit_exceeded"
    assert m["retry_count"] == 3


def test_records_to_metrics_projects_verification_scalars_from_justification():
    """Per ADR-7: verification scalars in justification flow through metrics."""
    record = RunRecord(
        method=Method.DIRECT,
        method_params=MethodParams(model="gpt-5.5"),
        justification={
            "verification_mode": "source_grounding",
            "mean_evidence_score": 0.82,
            "verification_cost_usd": 0.0123,
            # nested structures must NOT be projected
            "score_distribution": {"high": 10, "low": 2},
            "filtered_metrics": {"f1": 0.7},
        },
    )
    [m] = records_to_metrics([record])
    assert m["verification_mode"] == "source_grounding"
    assert m["mean_evidence_score"] == 0.82
    assert m["verification_cost_usd"] == 0.0123
    assert "score_distribution" not in m
    assert "filtered_metrics" not in m


def test_records_to_metrics_omits_verification_scalars_when_no_justification():
    """Omit-when-absent: no justification dict means no verification columns.

    Also covers the adapter's {"output_text": ...} shape, which carries no
    verification scalars and must not leak narrative text into metrics."""
    record = RunRecord(
        method=Method.DIRECT,
        method_params=MethodParams(model="gpt-5.5"),
        justification={"output_text": "some narrative"},
    )
    [m] = records_to_metrics([record])
    assert "verification_mode" not in m
    assert "mean_evidence_score" not in m
    assert "verification_cost_usd" not in m
    assert "output_text" not in m


def test_fixture_line_32_is_byte_identical_to_source():
    """Sanity: the inlined fixture is valid JSON and has the expected run_id.

    Catches accidental edits to FIXTURE_LINE_32 during refactors.
    """
    payload = json.loads(FIXTURE_LINE_32)
    assert payload["run_id"] == "61326a1572ec"
    assert payload["method_params"]["extra"]["architecture"] == "moe"
