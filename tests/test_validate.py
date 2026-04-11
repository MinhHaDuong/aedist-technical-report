"""Tests for the run validation layer (ticket 0072).

validate_run() operates on the raw dict loaded from an
``experiments/outputs/<condition>/<model>-runN.json`` file and returns a
ValidationResult describing whether the run is a clean observation of the
method x model cell.

Category precedence (first failing check wins):
    provider_error > empty > truncated_output > truncated_input > ok

Soft flags (e.g. ``voluntary_short_stop``) are added to ``flags`` but do
not set ``category`` away from ``ok``.
"""

from __future__ import annotations

from aedist.validate import ValidationResult, validate_run


def _clean_record(**overrides) -> dict:
    """Minimal well-formed record with a non-empty CSV response."""
    rec = {
        "model": "anthropic/claude-opus-4.6",
        "response": "```csv\nName,Fuel\nPha Lai,Coal\n```",
        "finish_reason": "stop",
        "usage": {"prompt_tokens": 63, "completion_tokens": 2000},
        "wall_seconds": 40.7,
        "cost_usd": 0.06,
        "model_metadata": {"context_window": 200000},
    }
    rec.update(overrides)
    return rec


class TestCleanRun:
    def test_clean_run_is_ok(self):
        result = validate_run(_clean_record())
        assert isinstance(result, ValidationResult)
        assert result.ok is True
        assert result.category == "ok"
        assert result.flags == []


class TestEmptyContent:
    def test_empty_response_is_empty_category(self):
        """Ticket 0041 shape: HTTP 200, stop, tokens reported, but response=''."""
        rec = _clean_record(
            response="",
            usage={"prompt_tokens": 63, "completion_tokens": 20258},
            finish_reason="stop",
        )
        result = validate_run(rec)
        assert result.ok is False
        assert result.category == "empty"
        assert "empty_content" in result.flags

    def test_whitespace_only_is_empty(self):
        rec = _clean_record(response="   \n\t\n  ")
        result = validate_run(rec)
        assert result.category == "empty"


class TestTruncatedOutput:
    def test_finish_reason_length_is_truncated_output(self):
        rec = _clean_record(finish_reason="length")
        result = validate_run(rec)
        assert result.ok is False
        assert result.category == "truncated_output"
        assert "finish_reason_length" in result.flags

    def test_content_filter_is_truncated_output(self):
        rec = _clean_record(finish_reason="content_filter")
        assert validate_run(rec).category == "truncated_output"

    def test_error_finish_reason_is_truncated_output(self):
        rec = _clean_record(finish_reason="error")
        assert validate_run(rec).category == "truncated_output"


class TestTruncatedInput:
    def test_prompt_over_90pct_ctx_is_truncated_input(self):
        rec = _clean_record(
            usage={"prompt_tokens": 190_000, "completion_tokens": 100},
            model_metadata={"context_window": 200_000},
        )
        result = validate_run(rec)
        assert result.ok is False
        assert result.category == "truncated_input"
        assert "prompt_over_ctx_threshold" in result.flags

    def test_prompt_under_90pct_is_ok(self):
        rec = _clean_record(
            usage={"prompt_tokens": 179_000, "completion_tokens": 100},
            model_metadata={"context_window": 200_000},
        )
        assert validate_run(rec).category == "ok"

    def test_missing_ctx_window_skips_input_check(self):
        rec = _clean_record(
            usage={"prompt_tokens": 190_000, "completion_tokens": 100},
            model_metadata={},
        )
        # Without context_window we cannot judge — do not fail the run.
        assert validate_run(rec).category == "ok"


class TestProviderError:
    def test_openrouter_error_body_on_200(self):
        """OpenRouter sometimes returns {"error": {...}} on HTTP 200."""
        rec = _clean_record(
            response="",
            error={"message": "rate limited", "code": 429},
        )
        result = validate_run(rec)
        assert result.ok is False
        assert result.category == "provider_error"
        assert "provider_error_body" in result.flags

    def test_provider_error_takes_precedence_over_empty(self):
        rec = _clean_record(response="", error={"message": "x"})
        assert validate_run(rec).category == "provider_error"


class TestSoftWarnings:
    def test_short_stop_flagged_but_still_ok(self):
        """RAG voluntary-short-stop: stop finish with <500 completion tokens.

        Surfaces the signal without corrupting data the decomposition fix already
        addresses.
        """
        rec = _clean_record(
            response="```csv\nName\nA\n```",
            finish_reason="stop",
            usage={"prompt_tokens": 100, "completion_tokens": 120},
        )
        result = validate_run(rec)
        assert result.category == "ok"
        assert result.ok is True
        assert "voluntary_short_stop" in result.flags


class TestSerialization:
    def test_result_is_jsonable(self):
        result = validate_run(_clean_record())
        d = result.to_dict()
        assert d["ok"] is True
        assert d["category"] == "ok"
        assert d["flags"] == []

    def test_rehydrate_from_dict(self):
        d = {"ok": False, "category": "empty", "flags": ["empty_content"]}
        result = ValidationResult.from_dict(d)
        assert result.category == "empty"
        assert result.flags == ["empty_content"]
