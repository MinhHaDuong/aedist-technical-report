"""Tests for aedist.query_rag — RAG wholesale experiments."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


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
    assert sorted(record["corpus_files"]) == ["doc1.md", "doc2.md"]
    assert isinstance(record["corpus_tokens"], int)
    assert record["corpus_tokens"] > 10  # both docs have real content


def _setup_modules(tmp_path: Path) -> Path:
    """Create a modules directory with base + persona + overview."""
    modules_dir = tmp_path / "modules"
    modules_dir.mkdir()
    (modules_dir / "base.txt").write_text("Base prompt text.")
    (modules_dir / "persona.txt").write_text("You are an expert.")
    (modules_dir / "overview.txt").write_text("Provide an overview.")
    return modules_dir


@patch("aedist.harness.OpenAI")
def test_rag_with_prompt_modules(mock_openai_cls, tmp_path):
    """query_rag accepts --prompt-modules and assembles prompt."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response()
    mock_openai_cls.return_value = mock_client

    _, corpus, models, output = _setup_files(tmp_path)
    modules_dir = _setup_modules(tmp_path)

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
        with patch.object(sys, "argv", [
            "query_rag",
            "--prompt-modules", "persona", "overview",
            "--modules-dir", str(modules_dir),
            "--corpus", str(corpus),
            "--strategy", "wholesale",
            "--models", str(models),
            "--output", str(output),
        ]):
            from aedist.query_rag import main
            main()

    # Verify: system message is corpus, user message is assembled prompt
    call_args = mock_client.chat.completions.create.call_args
    messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
    assert messages[0]["role"] == "system"
    assert "Pha Lai" in messages[0]["content"]  # corpus in system
    user_content = messages[1]["content"]
    # persona prepended before base, overview appended after base
    assert "You are an expert." in user_content
    assert "Base prompt text." in user_content
    assert "Provide an overview." in user_content
    assert user_content.index("You are an expert.") < user_content.index("Base prompt text.")


@patch("aedist.harness.OpenAI")
def test_rag_prompt_modules_metadata(mock_openai_cls, tmp_path):
    """Output JSON records assembled prompt when --prompt-modules used."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response()
    mock_openai_cls.return_value = mock_client

    _, corpus, models, output = _setup_files(tmp_path)
    modules_dir = _setup_modules(tmp_path)

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
        with patch.object(sys, "argv", [
            "query_rag",
            "--prompt-modules", "persona", "overview",
            "--modules-dir", str(modules_dir),
            "--corpus", str(corpus),
            "--models", str(models),
            "--output", str(output),
        ]):
            from aedist.query_rag import main
            main()

    json_files = list(output.rglob("*.json"))
    assert len(json_files) == 1
    record = json.loads(json_files[0].read_text())
    assert "You are an expert." in record["prompt"]
    assert "Base prompt text." in record["prompt"]
    assert record["sweep"] == "modules_persona_overview"


@patch("aedist.harness.OpenAI")
def test_rag_prompt_modules_dry_run(mock_openai_cls, tmp_path):
    """Dry run with --prompt-modules assembles prompt but makes no API calls."""
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client

    _, corpus, models, output = _setup_files(tmp_path)
    modules_dir = _setup_modules(tmp_path)

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
        with patch.object(sys, "argv", [
            "query_rag",
            "--prompt-modules", "persona",
            "--modules-dir", str(modules_dir),
            "--corpus", str(corpus),
            "--models", str(models),
            "--output", str(output),
            "--dry-run",
        ]):
            from aedist.query_rag import main
            main()

    mock_client.chat.completions.create.assert_not_called()


@patch("aedist.harness.OpenAI")
def test_rag_backwards_compat(mock_openai_cls, tmp_path):
    """Existing --prompt flag still works unchanged after adding --prompt-modules."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response()
    mock_openai_cls.return_value = mock_client

    prompt, corpus, models, output = _setup_files(tmp_path)

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
        with patch.object(sys, "argv", [
            "query_rag",
            "--prompt", str(prompt),
            "--corpus", str(corpus),
            "--models", str(models),
            "--output", str(output),
        ]):
            from aedist.query_rag import main
            main()

    call_args = mock_client.chat.completions.create.call_args
    messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
    assert messages[1]["content"] == "List power plants."

    json_files = list(output.rglob("*.json"))
    record = json.loads(json_files[0].read_text())
    assert record["prompt"] == "List power plants."


@patch("aedist.harness.OpenAI")
def test_rag_prompt_and_prompt_modules_mutually_exclusive(mock_openai_cls, tmp_path):
    """--prompt and --prompt-modules cannot be used together."""
    _, corpus, models, output = _setup_files(tmp_path)
    prompt = tmp_path / "prompt.txt"

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
        with patch.object(sys, "argv", [
            "query_rag",
            "--prompt", str(prompt),
            "--prompt-modules", "persona",
            "--corpus", str(corpus),
            "--models", str(models),
            "--output", str(output),
        ]):
            with pytest.raises(SystemExit):
                from aedist.query_rag import main
                main()
