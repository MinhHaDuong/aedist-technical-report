"""Tests for aedist.pdf2md_openrouter — OpenRouter PDF-to-Markdown converter."""

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from aedist.pdf2md_openrouter import process_model_response

# ---------------------------------------------------------------------------
# process_model_response
# ---------------------------------------------------------------------------

class TestProcessModelResponse:
    def test_returns_cleaned_content_with_page_comment(self):
        resp = _fake_response("```markdown\n# Title\n```")
        result = process_model_response(resp, 0)
        assert result.startswith("<!-- PDF page 1 -->")
        assert "# Title" in result
        assert "```" not in result

    def test_page_numbering_is_one_based(self):
        resp = _fake_response("text")
        result = process_model_response(resp, 4)
        assert "<!-- PDF page 5 -->" in result

    def test_empty_choices_raises(self):
        resp = SimpleNamespace(choices=[])
        with pytest.raises(ValueError, match="choices"):
            process_model_response(resp, 0)

    def test_missing_message_raises(self):
        choice = SimpleNamespace(message=None)
        resp = SimpleNamespace(choices=[choice])
        with pytest.raises(ValueError, match="Unexpected"):
            process_model_response(resp, 0)

    def test_none_content_raises(self):
        message = SimpleNamespace(content=None)
        choice = SimpleNamespace(message=message)
        resp = SimpleNamespace(choices=[choice])
        with pytest.raises(ValueError, match="Unexpected"):
            process_model_response(resp, 0)


def _fake_response(content):
    """Build a minimal object matching the OpenAI response shape."""
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


# ---------------------------------------------------------------------------
# Argparse and code quality (source inspection)
# ---------------------------------------------------------------------------

def test_main_uses_argparse():
    source = Path(__file__).resolve().parent.parent / "src" / "aedist" / "pdf2md_openrouter.py"
    text = source.read_text()
    assert "ArgumentParser" in text
    assert "add_argument" in text


def test_no_print_calls():
    source = Path(__file__).resolve().parent.parent / "src" / "aedist" / "pdf2md_openrouter.py"
    text = source.read_text()
    lines = text.splitlines()
    for i, line in enumerate(lines, 1):
        stripped = line.lstrip()
        if stripped.startswith(("#", '"')):
            continue
        assert not re.match(r".*\bprint\s*\(", stripped), (
            f"Found print() call at line {i}: {line.strip()}"
        )


# ---------------------------------------------------------------------------
# Functional tests (mock OpenAI client & pdf2image)
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock, patch

from aedist.pdf2md_openrouter import DEFAULT_DPI, main, pdf_to_markdown


class TestDefaultDpi:
    def test_value(self):
        assert DEFAULT_DPI == 300


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

        resp1 = _fake_response("# Page 1")
        resp2 = _fake_response("# Page 2")

        mock_client = MagicMock()
        mock_client.chat.completions.create = MagicMock(side_effect=[resp1, resp2])

        with patch("aedist.pdf2md_openrouter.OpenAI", return_value=mock_client):
            result = pdf_to_markdown(fake_pdf)

        assert "<!-- PDF page 1 -->" in result
        assert "<!-- PDF page 2 -->" in result
        assert "Page 1" in result
        assert "Page 2" in result

    def test_single_page(self, monkeypatch, tmp_path):
        fake_image = MagicMock()
        fake_image.save = MagicMock(side_effect=lambda f, fmt: f.write(b"\xff\xd8fake"))

        self._install_pdf2image_mock(monkeypatch, [fake_image])

        fake_pdf = tmp_path / "single.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        resp = _fake_response("Only content")
        mock_client = MagicMock()
        mock_client.chat.completions.create = MagicMock(return_value=resp)

        with patch("aedist.pdf2md_openrouter.OpenAI", return_value=mock_client):
            result = pdf_to_markdown(fake_pdf)

        assert "<!-- PDF page 1 -->" in result
        assert "Only content" in result

    def test_passes_model_and_max_tokens(self, monkeypatch, tmp_path):
        fake_image = MagicMock()
        fake_image.save = MagicMock(side_effect=lambda f, fmt: f.write(b"\xff\xd8fake"))

        self._install_pdf2image_mock(monkeypatch, [fake_image])

        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        resp = _fake_response("ok")
        mock_client = MagicMock()
        mock_client.chat.completions.create = MagicMock(return_value=resp)

        with patch("aedist.pdf2md_openrouter.OpenAI", return_value=mock_client):
            pdf_to_markdown(fake_pdf, model="claude-3", max_tokens=8192)

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "claude-3"
        assert call_kwargs["max_tokens"] == 8192


# ---------------------------------------------------------------------------
# main (CLI)
# ---------------------------------------------------------------------------


class TestMain:
    def test_writes_output_file(self, tmp_path):
        fake_pdf = tmp_path / "input.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")
        out = tmp_path / "output.md"

        with patch("aedist.pdf2md_openrouter.pdf_to_markdown", return_value="# Result"):
            main([str(fake_pdf), "--output", str(out)])

        assert out.exists()
        text = out.read_text()
        assert "# Result" in text
        assert "Converted from PDF" in text
        assert "OpenRouter" in text

    def test_default_output_path(self, tmp_path):
        fake_pdf = tmp_path / "report.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        with patch("aedist.pdf2md_openrouter.pdf_to_markdown", return_value="md"):
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

        with patch(
            "aedist.pdf2md_openrouter.pdf_to_markdown", return_value="ok"
        ) as mock:
            main([
                str(fake_pdf), "--output", str(out),
                "--model", "gpt-4-turbo",
                "--dpi", "150",
                "--max-tokens", "2048",
            ])

        mock.assert_called_once_with(
            fake_pdf,
            model="gpt-4-turbo",
            dpi=150,
            max_tokens=2048,
        )

    def test_metadata_mentions_model(self, tmp_path):
        fake_pdf = tmp_path / "m.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")
        out = tmp_path / "m.md"

        with patch("aedist.pdf2md_openrouter.pdf_to_markdown", return_value="c"):
            main([str(fake_pdf), "--output", str(out), "--model", "gpt-4o"])

        text = out.read_text()
        assert "Model: gpt-4o" in text
