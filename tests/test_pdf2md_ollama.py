"""Tests for aedist.pdf2md_ollama — Ollama-based PDF-to-Markdown converter."""

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Module structure (source inspection — no Ollama required)
# ---------------------------------------------------------------------------


def _source():
    return (Path(__file__).parent.parent / "src" / "aedist" / "pdf2md_ollama.py").read_text()


def test_main_uses_argparse():
    text = _source()
    assert "ArgumentParser" in text
    assert "add_argument" in text


def test_no_print_calls():
    text = _source()
    lines = text.splitlines()
    for i, line in enumerate(lines, 1):
        stripped = line.lstrip()
        if stripped.startswith(("#", '"')):
            continue
        assert not re.match(r".*\bprint\s*\(", stripped), (
            f"Found print() call at line {i}: {line.strip()}"
        )


def test_uses_shared_utils():
    """Ollama converter imports from pdf2md_utils, not from other converters."""
    text = _source()
    assert "from .pdf2md_utils import" in text
    # No imports from sibling converters
    assert "from .pdf2md_openrouter" not in text
    assert "from .pdf2md_grobid" not in text


def test_function_named_pdf_to_markdown():
    """Main function follows the uniform interface name."""
    text = _source()
    assert "def pdf_to_markdown(" in text


def test_uses_shared_metadata_comment():
    """Ollama converter imports metadata_comment from utils."""
    text = _source()
    assert "metadata_comment" in text
    assert "def metadata_comment" not in text


def test_cli_has_model_flag():
    text = _source()
    assert "--model" in text


def test_cli_has_ollama_url_flag():
    text = _source()
    assert "--ollama-url" in text
    assert "localhost:11434" in text


def test_raises_on_empty_response():
    """_ollama_chat_vision raises ValueError on empty response, not silent."""
    text = _source()
    assert "raise ValueError" in text


# ---------------------------------------------------------------------------
# Functional tests (mock HTTP / external deps)
# ---------------------------------------------------------------------------

import json  # noqa: E402
from unittest.mock import MagicMock, patch  # noqa: E402

import pytest  # noqa: E402
from conftest import mock_urlopen  # noqa: E402

import aedist.pdf2md_ollama as _ollama_mod  # noqa: E402
from aedist.pdf2md_ollama import (  # noqa: E402
    DEFAULT_DPI,
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_URL,
    _ollama_chat_vision,
    main,
    pdf_to_markdown,
)


class TestConstants:
    def test_default_model(self):
        assert DEFAULT_MODEL == "gemma4:31b"

    def test_default_url(self):
        assert DEFAULT_OLLAMA_URL == "http://localhost:11434"

    def test_default_dpi(self):
        assert DEFAULT_DPI == 200


# ---------------------------------------------------------------------------
# _ollama_chat_vision
# ---------------------------------------------------------------------------


class TestOllamaChatVision:
    def test_returns_content(self, monkeypatch):
        body = {"message": {"content": "# Hello"}}
        cm = mock_urlopen(body)
        monkeypatch.setattr(_ollama_mod.urllib.request, "urlopen", MagicMock(return_value=cm))

        result = _ollama_chat_vision("gemma4:31b", [{"role": "user", "content": "hi"}])
        assert result == "# Hello"

    def test_raises_on_empty_content(self, monkeypatch):
        body = {"message": {"content": ""}}
        cm = mock_urlopen(body)
        monkeypatch.setattr(_ollama_mod.urllib.request, "urlopen", MagicMock(return_value=cm))

        with pytest.raises(ValueError, match="empty response"):
            _ollama_chat_vision("gemma4:31b", [{"role": "user", "content": "hi"}])

    def test_raises_on_missing_message(self, monkeypatch):
        body = {}
        cm = mock_urlopen(body)
        monkeypatch.setattr(_ollama_mod.urllib.request, "urlopen", MagicMock(return_value=cm))

        with pytest.raises(ValueError, match="empty response"):
            _ollama_chat_vision("gemma4:31b", [{"role": "user", "content": "hi"}])

    def test_sends_to_correct_url(self, monkeypatch):
        body = {"message": {"content": "ok"}}
        cm = mock_urlopen(body)
        mock_fn = MagicMock(return_value=cm)
        monkeypatch.setattr(_ollama_mod.urllib.request, "urlopen", mock_fn)

        _ollama_chat_vision("model", [{"role": "user", "content": "x"}], "http://myhost:1234")
        req = mock_fn.call_args[0][0]
        assert req.full_url == "http://myhost:1234/api/chat"

    def test_sends_model_in_payload(self, monkeypatch):
        body = {"message": {"content": "ok"}}
        cm = mock_urlopen(body)
        mock_fn = MagicMock(return_value=cm)
        monkeypatch.setattr(_ollama_mod.urllib.request, "urlopen", mock_fn)

        _ollama_chat_vision("mymodel", [{"role": "user", "content": "x"}])
        req = mock_fn.call_args[0][0]
        payload = json.loads(req.data)
        assert payload["model"] == "mymodel"
        assert payload["stream"] is False


# ---------------------------------------------------------------------------
# pdf_to_markdown
# ---------------------------------------------------------------------------


class TestPdfToMarkdown:
    def _install_pdf2image_mock(self, monkeypatch, images):
        """Inject a fake pdf2image module into sys.modules so the lazy import works."""
        import sys
        import types

        fake_mod = types.ModuleType("pdf2image")
        fake_mod.convert_from_path = MagicMock(return_value=images)
        monkeypatch.setitem(sys.modules, "pdf2image", fake_mod)
        return fake_mod

    def test_converts_pages(self, monkeypatch, tmp_path):
        fake_image = MagicMock()
        fake_image.save = MagicMock(side_effect=lambda f, fmt: f.write(b"\xff\xd8fake"))

        self._install_pdf2image_mock(monkeypatch, [fake_image, fake_image])

        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        with patch(
            "aedist.pdf2md_ollama._ollama_chat_vision",
            side_effect=["# Page 1 content", "# Page 2 content"],
        ):
            result = pdf_to_markdown(fake_pdf)

        assert "<!-- PDF page 1 -->" in result
        assert "<!-- PDF page 2 -->" in result
        assert "Page 1 content" in result
        assert "Page 2 content" in result

    def test_single_page(self, monkeypatch, tmp_path):
        fake_image = MagicMock()
        fake_image.save = MagicMock(side_effect=lambda f, fmt: f.write(b"\xff\xd8fake"))

        self._install_pdf2image_mock(monkeypatch, [fake_image])

        fake_pdf = tmp_path / "single.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        with patch(
            "aedist.pdf2md_ollama._ollama_chat_vision",
            return_value="Only page",
        ):
            result = pdf_to_markdown(fake_pdf)

        assert "<!-- PDF page 1 -->" in result
        assert "Only page" in result
        # Only 1 page, so no page 2
        assert "page 2" not in result


# ---------------------------------------------------------------------------
# main (CLI)
# ---------------------------------------------------------------------------


class TestMain:
    def test_writes_output_file(self, tmp_path):
        fake_pdf = tmp_path / "input.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")
        out_path = tmp_path / "output.md"

        with patch(
            "aedist.pdf2md_ollama.pdf_to_markdown",
            return_value="# Converted",
        ):
            main([str(fake_pdf), "--output", str(out_path)])

        assert out_path.exists()
        text = out_path.read_text()
        assert "# Converted" in text

    def test_default_output_path(self, tmp_path):
        fake_pdf = tmp_path / "doc.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        with patch(
            "aedist.pdf2md_ollama.pdf_to_markdown",
            return_value="# Result",
        ):
            main([str(fake_pdf)])

        expected = tmp_path / "doc.md"
        assert expected.exists()
        assert "# Result" in expected.read_text()

    def test_file_not_found(self, tmp_path):
        missing = tmp_path / "nope.pdf"
        with pytest.raises(SystemExit):
            main([str(missing)])

    def test_not_a_pdf(self, tmp_path):
        txt = tmp_path / "file.txt"
        txt.write_text("hello")
        with pytest.raises(SystemExit):
            main([str(txt)])

    def test_custom_model_and_dpi(self, tmp_path):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")
        out = tmp_path / "out.md"

        with patch(
            "aedist.pdf2md_ollama.pdf_to_markdown",
            return_value="ok",
        ) as mock_p2m:
            main(
                [
                    str(fake_pdf),
                    "--output",
                    str(out),
                    "--model",
                    "llava:13b",
                    "--dpi",
                    "150",
                    "--ollama-url",
                    "http://other:9999",
                ]
            )

        mock_p2m.assert_called_once_with(
            fake_pdf,
            model="llava:13b",
            dpi=150,
            ollama_url="http://other:9999",
        )

    def test_metadata_in_output(self, tmp_path):
        fake_pdf = tmp_path / "meta.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")
        out = tmp_path / "meta.md"

        with patch(
            "aedist.pdf2md_ollama.pdf_to_markdown",
            return_value="content",
        ):
            main([str(fake_pdf), "--output", str(out)])

        text = out.read_text()
        assert "Converted from PDF" in text
        assert "Ollama" in text
