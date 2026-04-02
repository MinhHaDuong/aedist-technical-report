"""Tests for aedist.query_web — web-augmented queries."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


def _make_mock_response(content="name,fuel\nPlant A,coal", prompt_tokens=100, completion_tokens=200):
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = content
    resp.choices[0].finish_reason = "stop"
    resp.usage.prompt_tokens = prompt_tokens
    resp.usage.completion_tokens = completion_tokens
    return resp


def _setup_files(tmp_path: Path) -> tuple[Path, Path, Path]:
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("List power plants in Vietnam.")

    models = tmp_path / "models.yaml"
    models.write_text(
        "- id: test/tiny-model\n"
        "  name: Tiny\n"
        "  price_per_mtok_in: 1.0\n"
        "  price_per_mtok_out: 2.0\n"
        "  context_window: 8000\n"
        "  country: US\n"
        "  architecture: dense\n"
        "  size_class: edge\n"
    )

    output = tmp_path / "out"
    return prompt, models, output


@patch("aedist.query_web.tavily_search")
@patch("aedist.harness.OpenAI")
def test_web_query_with_tavily(mock_openai_cls, mock_tavily, tmp_path):
    """When Tavily is available, search results are injected as context."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response()
    mock_openai_cls.return_value = mock_client

    mock_tavily.return_value = [
        {"title": "Vietnam Power Plants", "content": "Pha Lai, Ba Ria..."}
    ]

    prompt, models, output = _setup_files(tmp_path)

    with patch.dict("os.environ", {
        "OPENROUTER_API_KEY": "fake-key",
        "TAVILY_API_KEY": "fake-tavily",
    }):
        with patch.object(sys, "argv", [
            "query_web",
            "--prompt", str(prompt),
            "--models", str(models),
            "--output", str(output),
        ]):
            from aedist.query_web import main
            main()

    json_files = list(output.rglob("*.json"))
    assert len(json_files) == 1
    record = json.loads(json_files[0].read_text())
    assert "web_searches" in record
    assert len(record["web_searches"]) > 0


@patch("aedist.harness.OpenAI")
def test_web_query_skips_without_tavily_key(mock_openai_cls, tmp_path):
    """Without TAVILY_API_KEY, web-search models are skipped."""
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client

    prompt, models, output = _setup_files(tmp_path)

    env = {"OPENROUTER_API_KEY": "fake-key"}
    # Ensure TAVILY_API_KEY is NOT set
    with patch.dict("os.environ", env, clear=True):
        with patch.object(sys, "argv", [
            "query_web",
            "--prompt", str(prompt),
            "--models", str(models),
            "--output", str(output),
        ]):
            from aedist.query_web import main
            main()

    # No API calls — models skipped due to missing Tavily
    mock_client.chat.completions.create.assert_not_called()


@patch("aedist.query_web.tavily_search")
@patch("aedist.harness.OpenAI")
def test_web_query_output_metadata(mock_openai_cls, mock_tavily, tmp_path):
    """Output includes web_searches with query and results."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response()
    mock_openai_cls.return_value = mock_client

    mock_tavily.return_value = [
        {"title": "Source A", "content": "Data about plants"},
    ]

    prompt, models, output = _setup_files(tmp_path)

    with patch.dict("os.environ", {
        "OPENROUTER_API_KEY": "fake-key",
        "TAVILY_API_KEY": "fake-tavily",
    }):
        with patch.object(sys, "argv", [
            "query_web",
            "--prompt", str(prompt),
            "--models", str(models),
            "--output", str(output),
        ]):
            from aedist.query_web import main
            main()

    json_files = list(output.rglob("*.json"))
    record = json.loads(json_files[0].read_text())
    assert "web_searches" in record
    searches = record["web_searches"]
    assert len(searches) >= 1
    assert "query" in searches[0]
    assert "results" in searches[0]
