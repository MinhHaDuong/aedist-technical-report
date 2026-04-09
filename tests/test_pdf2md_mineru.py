"""Tests for aedist.pdf2md_mineru — MinerU API container backend."""

from pathlib import Path


def test_module_has_pdf_to_markdown():
    source = Path("src/aedist/pdf2md_mineru.py").read_text()
    assert "def pdf_to_markdown(" in source


def test_module_has_argparse():
    source = Path("src/aedist/pdf2md_mineru.py").read_text()
    assert "ArgumentParser" in source


def test_module_uses_stdlib_http():
    source = Path("src/aedist/pdf2md_mineru.py").read_text()
    assert "urllib.request" in source


def test_conforms_to_converter_protocol():
    from aedist.pdf2md_utils import Converter, get_converter

    converter = get_converter("mineru")
    assert isinstance(converter, Converter)


def test_default_url():
    from aedist.pdf2md_mineru import DEFAULT_MINERU_URL

    assert "localhost" in DEFAULT_MINERU_URL
    assert "8010" in DEFAULT_MINERU_URL


def test_endpoint_is_file_parse():
    source = Path("src/aedist/pdf2md_mineru.py").read_text()
    assert "file_parse" in source


def test_sends_table_enable():
    source = Path("src/aedist/pdf2md_mineru.py").read_text()
    assert "table_enable" in source


def test_uses_pipeline_backend():
    source = Path("src/aedist/pdf2md_mineru.py").read_text()
    assert '"pipeline"' in source


def test_uses_latin_lang():
    source = Path("src/aedist/pdf2md_mineru.py").read_text()
    assert '"latin"' in source


def test_uses_metadata_comment():
    source = Path("src/aedist/pdf2md_mineru.py").read_text()
    assert "metadata_comment" in source


def test_uses_get_output_path():
    source = Path("src/aedist/pdf2md_mineru.py").read_text()
    assert "get_output_path" in source


# ---------------------------------------------------------------------------
# Functional tests (mock HTTP)
# ---------------------------------------------------------------------------

import io
import json
from unittest.mock import MagicMock, patch

import pytest

from aedist.pdf2md_mineru import (
    DEFAULT_MINERU_URL,
    main,
    mineru_convert,
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
# mineru_convert
# ---------------------------------------------------------------------------


class TestMineruConvert:
    def test_returns_md_content(self, tmp_path, monkeypatch):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        body = {"results": {"test.pdf": {"md_content": "# MinerU output"}}}
        cm = _mock_urlopen(body)
        monkeypatch.setattr("urllib.request.urlopen", MagicMock(return_value=cm))

        result = mineru_convert(fake_pdf)
        assert result == "# MinerU output"

    def test_raises_on_unexpected_response(self, tmp_path, monkeypatch):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        body = {"status": "error", "message": "fail"}
        cm = _mock_urlopen(body)
        monkeypatch.setattr("urllib.request.urlopen", MagicMock(return_value=cm))

        with pytest.raises(ValueError, match="Unexpected MinerU response"):
            mineru_convert(fake_pdf)

    def test_sends_to_correct_url(self, tmp_path, monkeypatch):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        body = {"results": {"test.pdf": {"md_content": "ok"}}}
        cm = _mock_urlopen(body)
        mock_urlopen = MagicMock(return_value=cm)
        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

        mineru_convert(fake_pdf, "http://myhost:7777")
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "http://myhost:7777/file_parse"

    def test_sends_multipart_with_pdf_bytes(self, tmp_path, monkeypatch):
        fake_pdf = tmp_path / "data.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 real content here")

        body = {"results": {"data.pdf": {"md_content": "ok"}}}
        cm = _mock_urlopen(body)
        mock_urlopen = MagicMock(return_value=cm)
        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

        mineru_convert(fake_pdf)
        req = mock_urlopen.call_args[0][0]
        assert b"data.pdf" in req.data
        assert b"%PDF-1.4 real content here" in req.data
        assert "multipart/form-data" in req.get_header("Content-type")

    def test_logs_timing_when_timestamps_present(self, tmp_path, monkeypatch):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        body = {
            "results": {"test.pdf": {"md_content": "ok"}},
            "created_at": "2026-01-01T00:00:00",
            "completed_at": "2026-01-01T00:00:05",
            "backend": "pipeline",
        }
        cm = _mock_urlopen(body)
        monkeypatch.setattr("urllib.request.urlopen", MagicMock(return_value=cm))

        # Should not raise even with timing info
        result = mineru_convert(fake_pdf)
        assert result == "ok"


# ---------------------------------------------------------------------------
# pdf_to_markdown (thin wrapper)
# ---------------------------------------------------------------------------


class TestPdfToMarkdown:
    def test_delegates_to_mineru_convert(self, tmp_path):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        with patch("aedist.pdf2md_mineru.mineru_convert", return_value="# Done") as mock:
            result = pdf_to_markdown(fake_pdf, mineru_url="http://x:1")

        mock.assert_called_once_with(fake_pdf, "http://x:1")
        assert result == "# Done"


# ---------------------------------------------------------------------------
# main (CLI)
# ---------------------------------------------------------------------------


class TestMain:
    def test_writes_output_file(self, tmp_path):
        fake_pdf = tmp_path / "input.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")
        out = tmp_path / "output.md"

        with patch("aedist.pdf2md_mineru.pdf_to_markdown", return_value="# MinerU"):
            main([str(fake_pdf), "--output", str(out)])

        assert out.exists()
        text = out.read_text()
        assert "# MinerU" in text
        assert "Converted from PDF" in text
        assert "MinerU" in text

    def test_default_output_path(self, tmp_path):
        fake_pdf = tmp_path / "report.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        with patch("aedist.pdf2md_mineru.pdf_to_markdown", return_value="md"):
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

    def test_custom_mineru_url(self, tmp_path):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")
        out = tmp_path / "out.md"

        with patch(
            "aedist.pdf2md_mineru.pdf_to_markdown", return_value="ok"
        ) as mock:
            main([str(fake_pdf), "--output", str(out), "--mineru-url", "http://other:5000"])

        mock.assert_called_once_with(fake_pdf, mineru_url="http://other:5000")

    def test_metadata_in_output(self, tmp_path):
        fake_pdf = tmp_path / "meta.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")
        out = tmp_path / "meta.md"

        with patch("aedist.pdf2md_mineru.pdf_to_markdown", return_value="content"):
            main([str(fake_pdf), "--output", str(out)])

        text = out.read_text()
        assert "Backend: MinerU" in text
