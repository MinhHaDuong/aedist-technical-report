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
    """Minimal well-formed record with a non-empty CSV response.

    The response body is >200 chars so it does not trip the
    content-length-based ``voluntary_short_stop`` soft flag.
    """
    rec = {
        "model": "anthropic/claude-opus-4.6",
        "response": (
            "```csv\nName,Fuel,Province,Capacity MW,Status,Operator\n"
            "Pha Lai,Coal,Hai Duong,1040,Operating,EVN\n"
            "Uong Bi,Coal,Quang Ninh,630,Operating,EVN\n"
            "Quang Ninh,Coal,Quang Ninh,1200,Operating,EVN\n"
            "Vung Ang,Coal,Ha Tinh,1200,Operating,EVN\n"
            "Mong Duong,Coal,Quang Ninh,1080,Operating,AES\n"
            "```"
        ),
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
    def test_short_stop_flagged_by_short_content(self):
        """Voluntary-short-stop is content-length-based, not token-count-based.

        Ollama counts internal/reasoning tokens in completion_tokens, so the
        canonical degenerate RAG run (``rag/qwen3.5-2b-run2.json``) reports
        17k completion tokens with a 94-char CSV-header-only response. The
        soft flag must fire on the content body, not the token count.
        """
        rec = _clean_record(
            response="```csv\nName, Fuel Type, Capacity MW, Operator\n```",
            finish_reason="stop",
            usage={"prompt_tokens": 100, "completion_tokens": 17182},
        )
        result = validate_run(rec)
        assert result.category == "ok"
        assert result.ok is True
        assert "voluntary_short_stop" in result.flags

    def test_long_content_high_tokens_not_flagged(self):
        """A long response with many tokens is not a short stop."""
        rec = _clean_record(
            response="```csv\nName,Fuel\n" + ("Plant,Coal\n" * 50) + "```",
            finish_reason="stop",
            usage={"prompt_tokens": 100, "completion_tokens": 2000},
        )
        result = validate_run(rec)
        assert "voluntary_short_stop" not in result.flags

    def test_short_stop_real_fixture(self):
        """Regression fixture: a real RAG-style degenerate run.

        Shaped to mirror ``experiments/outputs/rag/qwen3.5-2b-run2.json``:
        ``stop`` finish, 17k Ollama completion_tokens, 94-char CSV shell.
        The synthetic shape stands in for the real file, which is not in
        the current corpus snapshot but is the exact scenario this branch
        was written to catch.
        """
        rec = {
            "model": "ollama/qwen3.5:2b",
            "response": "```csv\nName, Fuel Type, Capacity MW, Province, Status, Operator\n```",
            "finish_reason": "stop",
            "usage": {"prompt_tokens": 63000, "completion_tokens": 17182},
            "model_metadata": {"context_window": 131072},
        }
        result = validate_run(rec)
        assert result.category == "ok"
        assert "voluntary_short_stop" in result.flags


class TestMultiturnContent:
    """W2: Multiturn records store content in ``turns``, not ``response``."""

    def test_multiturn_with_assistant_content_not_empty(self):
        rec = {
            "model": "anthropic/claude-opus-4.6",
            "model_metadata": {"context_window": 200000},
            "turns": [
                {"role": "user", "content": "List thermal plants", "turn": 1},
                {
                    "role": "assistant",
                    "content": "```csv\nName,Fuel\nPha Lai,Coal\nUong Bi,Coal\n```",
                    "turn": 1,
                },
            ],
            "usage": {"prompt_tokens": 500, "completion_tokens": 800},
            "finish_reason": "stop",
        }
        result = validate_run(rec)
        assert result.category == "ok"
        assert result.ok is True

    def test_multiturn_with_empty_assistant_is_empty(self):
        rec = {
            "model": "anthropic/claude-opus-4.6",
            "model_metadata": {"context_window": 200000},
            "turns": [
                {"role": "user", "content": "List thermal plants", "turn": 1},
                {"role": "assistant", "content": "", "turn": 1},
            ],
            "usage": {"prompt_tokens": 500, "completion_tokens": 0},
            "finish_reason": "stop",
        }
        result = validate_run(rec)
        assert result.category == "empty"


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
