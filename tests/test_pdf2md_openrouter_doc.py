"""Tests for aedist.pdf2md_openrouter_doc — OpenRouter document-level converter."""

import re
from pathlib import Path

from aedist.pdf2md_openrouter_doc import DEFAULT_ENGINE, ENGINES, EXTRACT_PROMPT

# ---------------------------------------------------------------------------
# Constants and configuration
# ---------------------------------------------------------------------------


class TestConstants:
    def test_default_engine_is_valid(self):
        assert DEFAULT_ENGINE in ENGINES

    def test_engines_tuple(self):
        assert "mistral-ocr" in ENGINES
        assert "cloudflare-ai" in ENGINES

    def test_prompt_mentions_tables(self):
        assert "table" in EXTRACT_PROMPT.lower()

    def test_prompt_mentions_vietnamese(self):
        assert "Vietnamese" in EXTRACT_PROMPT


# ---------------------------------------------------------------------------
# Argparse and code quality (source inspection)
# ---------------------------------------------------------------------------

SRC = Path(__file__).resolve().parent.parent / "src" / "aedist" / "pdf2md_openrouter_doc.py"


def test_main_uses_argparse():
    text = SRC.read_text()
    assert "ArgumentParser" in text
    assert "add_argument" in text


def test_has_engine_flag():
    text = SRC.read_text()
    assert "--engine" in text


def test_has_model_flag():
    text = SRC.read_text()
    assert "--model" in text


def test_no_print_calls():
    text = SRC.read_text()
    lines = text.splitlines()
    for i, line in enumerate(lines, 1):
        stripped = line.lstrip()
        if stripped.startswith(("#", '"')):
            continue
        assert not re.match(r".*\bprint\s*\(", stripped), (
            f"Found print() call at line {i}: {line.strip()}"
        )


def test_uses_metadata_comment():
    text = SRC.read_text()
    assert "metadata_comment" in text


def test_uses_get_output_path():
    text = SRC.read_text()
    assert "get_output_path" in text


def test_converter_protocol_compliance():
    """Module exposes pdf_to_markdown with pdf_path as first arg."""
    text = SRC.read_text()
    assert "def pdf_to_markdown(" in text


def test_uses_openai_client():
    """Uses OpenAI SDK for OpenRouter-compatible API."""
    text = SRC.read_text()
    assert "from openai import OpenAI" in text


def test_uses_plugins_extra_body():
    """Sends file-parser plugin via extra_body."""
    text = SRC.read_text()
    assert "file-parser" in text
    assert "extra_body" in text


def test_uses_file_content_type():
    """Must use type 'file' (not 'image_url') for PDF data URLs."""
    text = SRC.read_text()
    assert '"type": "file"' in text or "'type': 'file'" in text
    assert "file_data" in text


# ---------------------------------------------------------------------------
# Functional tests (mock OpenAI client)
# ---------------------------------------------------------------------------

from types import SimpleNamespace  # noqa: E402
from unittest.mock import MagicMock, patch  # noqa: E402

import pytest  # noqa: E402

from aedist.pdf2md_openrouter_doc import (  # noqa: E402
    main,
    pdf_to_markdown,
)


def _fake_response(content):
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


# ---------------------------------------------------------------------------
# pdf_to_markdown
# ---------------------------------------------------------------------------


class TestPdfToMarkdown:
    def test_returns_content(self, tmp_path, monkeypatch):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-key")

        resp = _fake_response("# Document content\n\nParagraph.")
        mock_client = MagicMock()
        mock_client.chat.completions.create = MagicMock(return_value=resp)

        with patch("aedist.pdf2md_openrouter_doc.OpenAI", return_value=mock_client):
            result = pdf_to_markdown(fake_pdf)

        assert "# Document content" in result
        assert "Paragraph." in result

    def test_raises_without_api_key(self, tmp_path, monkeypatch):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

        with pytest.raises(SystemExit, match="OPENROUTER_API_KEY"):
            pdf_to_markdown(fake_pdf)

    def test_empty_choices_raises(self, tmp_path, monkeypatch):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")

        resp = SimpleNamespace(choices=[])
        mock_client = MagicMock()
        mock_client.chat.completions.create = MagicMock(return_value=resp)

        with patch("aedist.pdf2md_openrouter_doc.OpenAI", return_value=mock_client):
            with pytest.raises(ValueError, match="empty choices"):
                pdf_to_markdown(fake_pdf)

    def test_empty_content_raises(self, tmp_path, monkeypatch):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")

        resp = _fake_response("")
        mock_client = MagicMock()
        mock_client.chat.completions.create = MagicMock(return_value=resp)

        with patch("aedist.pdf2md_openrouter_doc.OpenAI", return_value=mock_client):
            with pytest.raises(ValueError, match="empty content"):
                pdf_to_markdown(fake_pdf)

    def test_passes_engine_and_model(self, tmp_path, monkeypatch):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")

        resp = _fake_response("ok")
        mock_client = MagicMock()
        mock_client.chat.completions.create = MagicMock(return_value=resp)

        with patch("aedist.pdf2md_openrouter_doc.OpenAI", return_value=mock_client):
            pdf_to_markdown(
                fake_pdf,
                engine="cloudflare-ai",
                model="openai/gpt-4o",
                max_tokens=1024,
            )

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "openai/gpt-4o"
        assert call_kwargs["max_tokens"] == 1024
        extra = call_kwargs["extra_body"]
        assert extra["plugins"][0]["pdf"]["engine"] == "cloudflare-ai"

    def test_creates_client_with_openrouter_base_url(self, tmp_path, monkeypatch):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-my-key")

        resp = _fake_response("ok")
        mock_client = MagicMock()
        mock_client.chat.completions.create = MagicMock(return_value=resp)

        with patch("aedist.pdf2md_openrouter_doc.OpenAI", return_value=mock_client) as mock_cls:
            pdf_to_markdown(fake_pdf)

        call_kwargs = mock_cls.call_args[1]
        assert "openrouter.ai" in call_kwargs["base_url"]
        assert call_kwargs["api_key"] == "sk-my-key"


# ---------------------------------------------------------------------------
# main (CLI)
# ---------------------------------------------------------------------------


class TestMain:
    def test_writes_output_file(self, tmp_path, monkeypatch):
        fake_pdf = tmp_path / "input.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")
        out = tmp_path / "output.md"

        with patch("aedist.pdf2md_openrouter_doc.pdf_to_markdown", return_value="# Doc"):
            main([str(fake_pdf), "--output", str(out)])

        assert out.exists()
        text = out.read_text()
        assert "# Doc" in text
        assert "Converted from PDF" in text

    def test_default_output_path(self, tmp_path):
        fake_pdf = tmp_path / "report.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        with patch("aedist.pdf2md_openrouter_doc.pdf_to_markdown", return_value="md"):
            main([str(fake_pdf)])

        assert (tmp_path / "report.md").exists()

    def test_file_not_found(self, tmp_path):
        with pytest.raises(SystemExit):
            main([str(tmp_path / "nonexistent.pdf")])

    def test_not_a_pdf(self, tmp_path):
        txt = tmp_path / "file.txt"
        txt.write_text("hello")
        with pytest.raises(SystemExit):
            main([str(txt)])

    def test_custom_args_forwarded(self, tmp_path):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")
        out = tmp_path / "out.md"

        with patch("aedist.pdf2md_openrouter_doc.pdf_to_markdown", return_value="ok") as mock:
            main(
                [
                    str(fake_pdf),
                    "--output",
                    str(out),
                    "--engine",
                    "cloudflare-ai",
                    "--model",
                    "openai/gpt-4o",
                    "--max-tokens",
                    "2048",
                ]
            )

        mock.assert_called_once_with(
            fake_pdf,
            engine="cloudflare-ai",
            model="openai/gpt-4o",
            max_tokens=2048,
        )

    def test_metadata_mentions_engine(self, tmp_path):
        fake_pdf = tmp_path / "m.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")
        out = tmp_path / "m.md"

        with patch("aedist.pdf2md_openrouter_doc.pdf_to_markdown", return_value="c"):
            main([str(fake_pdf), "--output", str(out), "--engine", "mistral-ocr"])

        text = out.read_text()
        assert "OpenRouter/mistral-ocr" in text
