"""Tests for aedist.pdf2md_mistral_ocr — direct Mistral OCR API converter."""

import re
from pathlib import Path

from aedist.pdf2md_mistral_ocr import DEFAULT_MODEL, TABLE_FORMATS, _stitch_pages

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_default_model(self):
        assert "ocr" in DEFAULT_MODEL

    def test_table_formats(self):
        assert "html" in TABLE_FORMATS
        assert "markdown" in TABLE_FORMATS


# ---------------------------------------------------------------------------
# _stitch_pages
# ---------------------------------------------------------------------------


class TestStitchPages:
    def test_empty_result(self):
        assert _stitch_pages({"pages": []}) == ""

    def test_single_page(self):
        result = {"pages": [{"index": 0, "markdown": "Hello world", "tables": []}]}
        out = _stitch_pages(result)
        assert "<!-- PDF page 1 -->" in out
        assert "Hello world" in out

    def test_page_numbering(self):
        result = {
            "pages": [
                {"index": 0, "markdown": "p1", "tables": []},
                {"index": 1, "markdown": "p2", "tables": []},
            ]
        }
        out = _stitch_pages(result)
        assert "<!-- PDF page 1 -->" in out
        assert "<!-- PDF page 2 -->" in out

    def test_table_placeholder_inlined(self):
        result = {
            "pages": [
                {
                    "index": 0,
                    "markdown": "Before [tbl-0.html](tbl-0.html) after",
                    "tables": [
                        {"id": "tbl-0.html", "content": "<table><tr><td>data</td></tr></table>"}
                    ],
                }
            ]
        }
        out = _stitch_pages(result)
        assert "<table>" in out
        assert "[tbl-0.html]" not in out

    def test_missing_tables_key(self):
        """Pages without tables key should not crash."""
        result = {"pages": [{"index": 0, "markdown": "text"}]}
        out = _stitch_pages(result)
        assert "text" in out


# ---------------------------------------------------------------------------
# Argparse and code quality (source inspection)
# ---------------------------------------------------------------------------

SRC = Path(__file__).resolve().parent.parent / "src" / "aedist" / "pdf2md_mistral_ocr.py"


def test_main_uses_argparse():
    text = SRC.read_text()
    assert "ArgumentParser" in text
    assert "add_argument" in text


def test_has_table_format_flag():
    text = SRC.read_text()
    assert "--table-format" in text


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
    text = SRC.read_text()
    assert "def pdf_to_markdown(" in text


def test_uses_stdlib_urllib():
    """Uses stdlib urllib.request, not openai SDK — direct API call."""
    text = SRC.read_text()
    assert "urllib.request" in text


def test_calls_mistral_ocr_endpoint():
    text = SRC.read_text()
    assert "/v1/ocr" in text
    assert "mistral.ai" in text


# ---------------------------------------------------------------------------
# Functional tests (mock HTTP)
# ---------------------------------------------------------------------------

import io
import json
from unittest.mock import MagicMock, patch

import pytest

from aedist.pdf2md_mistral_ocr import (
    MISTRAL_OCR_URL,
    _ocr_request,
    main,
    pdf_to_markdown,
)


def _mock_urlopen(response_body):
    """Return a context-manager mock for urllib.request.urlopen."""
    resp_bytes = json.dumps(response_body).encode("utf-8")
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=io.BytesIO(resp_bytes))
    cm.__exit__ = MagicMock(return_value=False)
    return cm


# ---------------------------------------------------------------------------
# _stitch_pages (additional edge cases)
# ---------------------------------------------------------------------------


class TestStitchPagesExtra:
    def test_bare_parenthetical_table_ref(self):
        """Test the (tbl-id) replacement form."""
        result = {
            "pages": [
                {
                    "index": 0,
                    "markdown": "See table (tbl-0.html) for details",
                    "tables": [
                        {"id": "tbl-0.html", "content": "<table><tr><td>X</td></tr></table>"}
                    ],
                }
            ]
        }
        out = _stitch_pages(result)
        assert "<table>" in out
        assert "(tbl-0.html)" not in out

    def test_multiple_tables_on_one_page(self):
        result = {
            "pages": [
                {
                    "index": 0,
                    "markdown": "[tbl-0.html](tbl-0.html) and [tbl-1.html](tbl-1.html)",
                    "tables": [
                        {"id": "tbl-0.html", "content": "<table>A</table>"},
                        {"id": "tbl-1.html", "content": "<table>B</table>"},
                    ],
                }
            ]
        }
        out = _stitch_pages(result)
        assert "<table>A</table>" in out
        assert "<table>B</table>" in out
        assert "[tbl-0.html]" not in out
        assert "[tbl-1.html]" not in out

    def test_table_with_empty_id_skipped(self):
        result = {
            "pages": [
                {
                    "index": 0,
                    "markdown": "text here",
                    "tables": [{"id": "", "content": "should not appear as replacement"}],
                }
            ]
        }
        out = _stitch_pages(result)
        assert "text here" in out

    def test_table_with_empty_content_skipped(self):
        result = {
            "pages": [
                {
                    "index": 0,
                    "markdown": "[tbl-0.html](tbl-0.html)",
                    "tables": [{"id": "tbl-0.html", "content": ""}],
                }
            ]
        }
        out = _stitch_pages(result)
        # Placeholder remains because content is empty
        assert "[tbl-0.html]" in out

    def test_missing_index_defaults_to_zero(self):
        result = {"pages": [{"markdown": "no index"}]}
        out = _stitch_pages(result)
        assert "<!-- PDF page 1 -->" in out

    def test_multi_page_separator(self):
        result = {
            "pages": [
                {"index": 0, "markdown": "p1"},
                {"index": 1, "markdown": "p2"},
                {"index": 2, "markdown": "p3"},
            ]
        }
        out = _stitch_pages(result)
        # Pages are separated by double newlines
        assert "\n\n" in out
        assert out.count("<!-- PDF page") == 3


# ---------------------------------------------------------------------------
# _ocr_request
# ---------------------------------------------------------------------------


class TestOcrRequest:
    def test_returns_json(self, tmp_path, monkeypatch):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        monkeypatch.setenv("MISTRAL_API_KEY", "test-key-123")

        body = {"pages": [{"index": 0, "markdown": "content", "tables": []}]}
        cm = _mock_urlopen(body)
        monkeypatch.setattr("urllib.request.urlopen", MagicMock(return_value=cm))

        result = _ocr_request(fake_pdf, model="mistral-ocr-latest", table_format="html")
        assert result["pages"][0]["markdown"] == "content"

    def test_raises_without_api_key(self, tmp_path, monkeypatch):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        monkeypatch.delenv("MISTRAL_API_KEY", raising=False)

        with pytest.raises(SystemExit, match="MISTRAL_API_KEY"):
            _ocr_request(fake_pdf, model="mistral-ocr-latest", table_format="html")

    def test_sends_correct_headers(self, tmp_path, monkeypatch):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        monkeypatch.setenv("MISTRAL_API_KEY", "sk-my-key")

        body = {"pages": []}
        cm = _mock_urlopen(body)
        mock_urlopen = MagicMock(return_value=cm)
        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

        _ocr_request(fake_pdf, model="mistral-ocr-latest", table_format="html")

        req = mock_urlopen.call_args[0][0]
        assert req.full_url == MISTRAL_OCR_URL
        assert req.get_header("Authorization") == "Bearer sk-my-key"
        assert req.get_header("Content-type") == "application/json"

    def test_sends_correct_payload(self, tmp_path, monkeypatch):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        monkeypatch.setenv("MISTRAL_API_KEY", "sk-key")

        body = {"pages": []}
        cm = _mock_urlopen(body)
        mock_urlopen = MagicMock(return_value=cm)
        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

        _ocr_request(fake_pdf, model="my-model", table_format="markdown")

        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data)
        assert payload["model"] == "my-model"
        assert payload["table_format"] == "markdown"
        assert payload["include_image_base64"] is False
        assert payload["document"]["type"] == "document_url"
        assert payload["document"]["document_url"].startswith("data:application/pdf;base64,")


# ---------------------------------------------------------------------------
# pdf_to_markdown
# ---------------------------------------------------------------------------


class TestPdfToMarkdownFunctional:
    def test_full_pipeline(self, tmp_path, monkeypatch):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        monkeypatch.setenv("MISTRAL_API_KEY", "sk-key")

        ocr_result = {
            "pages": [
                {"index": 0, "markdown": "# Title", "tables": []},
                {"index": 1, "markdown": "Body text", "tables": []},
            ],
            "usage_info": {"pages_processed": 2},
        }

        with patch("aedist.pdf2md_mistral_ocr._ocr_request", return_value=ocr_result):
            result = pdf_to_markdown(fake_pdf)

        assert "<!-- PDF page 1 -->" in result
        assert "<!-- PDF page 2 -->" in result
        assert "# Title" in result
        assert "Body text" in result

    def test_passes_model_and_table_format(self, tmp_path, monkeypatch):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        monkeypatch.setenv("MISTRAL_API_KEY", "sk-key")

        ocr_result = {"pages": [], "usage_info": {"pages_processed": 0}}

        with patch(
            "aedist.pdf2md_mistral_ocr._ocr_request", return_value=ocr_result
        ) as mock:
            pdf_to_markdown(fake_pdf, model="custom-model", table_format="markdown")

        mock.assert_called_once_with(
            fake_pdf, model="custom-model", table_format="markdown"
        )


# ---------------------------------------------------------------------------
# main (CLI)
# ---------------------------------------------------------------------------


class TestMain:
    def test_writes_output_file(self, tmp_path):
        fake_pdf = tmp_path / "input.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")
        out = tmp_path / "output.md"

        with patch("aedist.pdf2md_mistral_ocr.pdf_to_markdown", return_value="# OCR result"):
            main([str(fake_pdf), "--output", str(out)])

        assert out.exists()
        text = out.read_text()
        assert "# OCR result" in text
        assert "Converted from PDF" in text
        assert "Mistral OCR" in text

    def test_default_output_path(self, tmp_path):
        fake_pdf = tmp_path / "report.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        with patch("aedist.pdf2md_mistral_ocr.pdf_to_markdown", return_value="md"):
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
            "aedist.pdf2md_mistral_ocr.pdf_to_markdown", return_value="ok"
        ) as mock:
            main([
                str(fake_pdf), "--output", str(out),
                "--model", "custom-ocr",
                "--table-format", "markdown",
            ])

        mock.assert_called_once_with(
            fake_pdf,
            model="custom-ocr",
            table_format="markdown",
        )

    def test_metadata_in_output(self, tmp_path):
        fake_pdf = tmp_path / "meta.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")
        out = tmp_path / "meta.md"

        with patch("aedist.pdf2md_mistral_ocr.pdf_to_markdown", return_value="content"):
            main([str(fake_pdf), "--output", str(out)])

        text = out.read_text()
        assert "Backend: Mistral OCR (direct)" in text
