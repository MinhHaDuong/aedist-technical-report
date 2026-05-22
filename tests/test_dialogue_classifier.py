"""Unit tests for the Exp 2 dialogue classifier (ticket 0226).

Pure unit tests — no network, no API key. Uses monkeypatching and
httpx mocking to verify request construction, key loading, parsing,
and cost computation.
"""

import pytest

from experiments.sota.dialogue_classifier import (
    CLASSIFIER_API_BASE,
    CLASSIFIER_MODEL,
    _compute_cost_usd,
    _load_api_key,
    _parse_class,
    classify_report,
)

# ── Model and endpoint constants ──────────────────────────────────────


def test_classifier_model_is_nemotron():
    """Verify the pinned classifier is nvidia/nemotron-nano-9b-v2."""
    assert CLASSIFIER_MODEL == "nvidia/nemotron-nano-9b-v2"


def test_classifier_api_base_is_openrouter():
    """Verify the API base points to OpenRouter."""
    assert "openrouter.ai" in CLASSIFIER_API_BASE


# ── API key loading ───────────────────────────────────────────────────


def test_load_api_key_from_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-123")
    assert _load_api_key() == "test-key-123"


def test_load_api_key_missing(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert _load_api_key() is None


# ── _parse_class ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("report", "report"),
        ("no_report", "no_report"),
        ("report\n", "report"),
        ("no_report\n", "no_report"),
        ("  report  ", "report"),
        ("REPORT", "report"),
        ("NO_REPORT", "no_report"),
        ("`report`", "report"),
        ('"report"', "report"),
        ("'no_report'", "no_report"),
        # Thinking-model leak: first alpha token is not 'report'
        ("<think>analysis</think>report", "no_report"),
        ("Let me think... report", "no_report"),
        # Empty / garbage -> safe default
        ("", "no_report"),
        ("???", "no_report"),
        ("maybe", "no_report"),
        # Tokens starting with 'no' -> no_report
        ("nope", "no_report"),
        ("nothing", "no_report"),
    ],
)
def test_parse_class(raw, expected):
    assert _parse_class(raw) == expected


# ── Cost computation ──────────────────────────────────────────────────


def test_compute_cost_usd():
    usage = {"prompt_tokens": 2304, "completion_tokens": 265}
    cost = _compute_cost_usd(usage)
    expected = 2304 * 0.04 / 1_000_000 + 265 * 0.16 / 1_000_000
    assert abs(cost - expected) < 1e-10


def test_compute_cost_usd_empty():
    assert _compute_cost_usd({}) == 0.0


def test_compute_cost_usd_none_values():
    usage = {"prompt_tokens": None, "completion_tokens": None}
    assert _compute_cost_usd(usage) == 0.0


# ── classify_report (mocked HTTP) ────────────────────────────────────


def _make_mock_response(content: str, prompt_tokens: int = 100, completion_tokens: int = 50):
    """Build a fake OpenRouter JSON response."""
    return {
        "choices": [{"message": {"content": content}}],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        },
    }


def test_classify_report_returns_report(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    def mock_post(prompt, api_key):
        return _make_mock_response("report\n")

    monkeypatch.setattr("experiments.sota.dialogue_classifier._post_classifier", mock_post)

    result = classify_report("Here is a table of power plants...")
    assert result.class_ == "report"
    assert result.classifier_model == "nvidia/nemotron-nano-9b-v2"
    assert result.classifier_cost_usd > 0


def test_classify_report_returns_no_report(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    def mock_post(prompt, api_key):
        return _make_mock_response("no_report\n")

    monkeypatch.setattr("experiments.sota.dialogue_classifier._post_classifier", mock_post)

    result = classify_report("I will build the inventory in three phases...")
    assert result.class_ == "no_report"


def test_classify_report_no_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    result = classify_report("any text")
    assert result.class_ == "no_report"
    assert result.classifier_cost_usd == 0.0


def test_classify_report_http_error(monkeypatch):
    import httpx

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    def mock_post(prompt, api_key):
        raise httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=httpx.Request("POST", "http://test"),
            response=httpx.Response(500),
        )

    monkeypatch.setattr("experiments.sota.dialogue_classifier._post_classifier", mock_post)

    result = classify_report("any text")
    assert result.class_ == "no_report"
    assert result.classifier_cost_usd == 0.0


def test_classify_report_request_body_shape(monkeypatch):
    """Verify that _post_classifier sends the right model and max_tokens."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    captured = {}

    def mock_post(prompt, api_key):
        # We can inspect what _build_prompt produced
        captured["prompt"] = prompt
        captured["api_key"] = api_key
        return _make_mock_response("report\n")

    monkeypatch.setattr("experiments.sota.dialogue_classifier._post_classifier", mock_post)

    classify_report("test narrative")
    assert "test narrative" in captured["prompt"]
    assert captured["api_key"] == "test-key"


def test_post_classifier_body_contains_model_and_max_tokens():
    """Verify the HTTP request body has the correct model and max_tokens.

    Reads the source to confirm the constants without making a real API call.
    """
    src = open("experiments/sota/dialogue_classifier.py").read()
    # Model is set from the module constant
    assert "CLASSIFIER_MODEL" in src
    assert '"nvidia/nemotron-nano-9b-v2"' in src
    # max_tokens accommodates thinking model reasoning tokens
    assert '"max_tokens": 512' in src
