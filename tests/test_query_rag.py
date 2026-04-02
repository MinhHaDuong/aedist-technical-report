"""Tests for aedist.query_rag — RAG wholesale experiments."""

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


def _setup_files(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("List power plants.")

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "doc1.md").write_text("# Vietnam Coal\nPha Lai is a coal plant in Hai Duong.\n")
    (corpus / "doc2.md").write_text("# Vietnam Gas\nBa Ria is a gas plant.\n")

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
    return prompt, corpus, models, output


@patch("aedist.harness.OpenAI")
def test_rag_wholesale_concatenates_corpus(mock_openai_cls, tmp_path):
    """Wholesale strategy concatenates all .md files as system message."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response()
    mock_openai_cls.return_value = mock_client

    prompt, corpus, models, output = _setup_files(tmp_path)

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
        with patch.object(sys, "argv", [
            "query_rag",
            "--prompt", str(prompt),
            "--corpus", str(corpus),
            "--strategy", "wholesale",
            "--models", str(models),
            "--output", str(output),
        ]):
            from aedist.query_rag import main
            main()

    # Check that system message was sent with corpus content
    call_args = mock_client.chat.completions.create.call_args
    messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
    assert messages[0]["role"] == "system"
    assert "Pha Lai" in messages[0]["content"]
    assert "Ba Ria" in messages[0]["content"]


@patch("aedist.harness.OpenAI")
def test_rag_context_window_guard(mock_openai_cls, tmp_path):
    """Models with small context windows are skipped when corpus is too large."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response()
    mock_openai_cls.return_value = mock_client

    prompt, corpus, models, output = _setup_files(tmp_path)

    # Rewrite models.yaml with tiny context window
    models.write_text(
        "- id: test/tiny-ctx\n"
        "  name: TinyCtx\n"
        "  price_per_mtok_in: 1.0\n"
        "  price_per_mtok_out: 2.0\n"
        "  context_window: 10\n"  # 10 tokens — way too small
        "  country: US\n"
        "  architecture: dense\n"
        "  size_class: edge\n"
    )

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
        with patch.object(sys, "argv", [
            "query_rag",
            "--prompt", str(prompt),
            "--corpus", str(corpus),
            "--strategy", "wholesale",
            "--models", str(models),
            "--output", str(output),
        ]):
            from aedist.query_rag import main
            main()

    # Should not have called the API (model skipped)
    mock_client.chat.completions.create.assert_not_called()
    json_files = list(output.rglob("*.json"))
    assert len(json_files) == 0


@patch("aedist.harness.OpenAI")
def test_rag_output_metadata(mock_openai_cls, tmp_path):
    """Output JSON includes strategy, corpus_files, corpus_tokens."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response()
    mock_openai_cls.return_value = mock_client

    prompt, corpus, models, output = _setup_files(tmp_path)

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
        with patch.object(sys, "argv", [
            "query_rag",
            "--prompt", str(prompt),
            "--corpus", str(corpus),
            "--strategy", "wholesale",
            "--models", str(models),
            "--output", str(output),
        ]):
            from aedist.query_rag import main
            main()

    json_files = list(output.rglob("*.json"))
    assert len(json_files) == 1
    record = json.loads(json_files[0].read_text())
    assert record["strategy"] == "wholesale"
    assert "corpus_files" in record
    assert len(record["corpus_files"]) == 2
    assert "corpus_tokens" in record
    assert record["corpus_tokens"] > 0
