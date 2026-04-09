"""Tests for aedist.pdf2md_marker — Marker API container backend."""

from pathlib import Path


def test_module_has_pdf_to_markdown():
    source = (Path(__file__).parent.parent / "src" / "aedist" / "pdf2md_marker.py").read_text()
    assert "def pdf_to_markdown(" in source


def test_module_has_argparse():
    source = (Path(__file__).parent.parent / "src" / "aedist" / "pdf2md_marker.py").read_text()
    assert "ArgumentParser" in source


def test_module_uses_stdlib_http():
    source = (Path(__file__).parent.parent / "src" / "aedist" / "pdf2md_marker.py").read_text()
    assert "urllib.request" in source


def test_conforms_to_converter_protocol():
    from aedist.pdf2md_utils import Converter, get_converter

    converter = get_converter("marker")
    assert isinstance(converter, Converter)


def test_default_url():
    from aedist.pdf2md_marker import DEFAULT_MARKER_URL

    assert "localhost" in DEFAULT_MARKER_URL
    assert "8001" in DEFAULT_MARKER_URL


def test_uses_metadata_comment():
    source = (Path(__file__).parent.parent / "src" / "aedist" / "pdf2md_marker.py").read_text()
    assert "metadata_comment" in source


def test_uses_get_output_path():
    source = (Path(__file__).parent.parent / "src" / "aedist" / "pdf2md_marker.py").read_text()
    assert "get_output_path" in source


# ---------------------------------------------------------------------------
# Functional tests (mock HTTP)
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock, patch

import pytest

import aedist.pdf2md_marker as _marker_mod
from aedist.pdf2md_marker import (
    DEFAULT_MARKER_URL,
    main,
    marker_convert,
    pdf_to_markdown,
)
from conftest import mock_urlopen


# ---------------------------------------------------------------------------
# marker_convert
# ---------------------------------------------------------------------------


class TestMarkerConvert:
    def test_returns_markdown_from_dict(self, tmp_path, monkeypatch):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake content")

        body = {"markdown": "# Converted Document\n\nParagraph."}
        cm = mock_urlopen(body)
        monkeypatch.setattr(_marker_mod.urllib.request, "urlopen", MagicMock(return_value=cm))

        result = marker_convert(fake_pdf)
        assert result == "# Converted Document\n\nParagraph."

    def test_returns_markdown_from_list(self, tmp_path, monkeypatch):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        body = [{"markdown": "# From list"}]
        cm = mock_urlopen(body)
        monkeypatch.setattr(_marker_mod.urllib.request, "urlopen", MagicMock(return_value=cm))

        result = marker_convert(fake_pdf)
        assert result == "# From list"

    def test_empty_list_returns_empty(self, tmp_path, monkeypatch):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        body = []
        cm = mock_urlopen(body)
        monkeypatch.setattr(_marker_mod.urllib.request, "urlopen", MagicMock(return_value=cm))

        result = marker_convert(fake_pdf)
        assert result == ""

    def test_falls_back_to_text_key(self, tmp_path, monkeypatch):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        body = {"text": "fallback text"}
        cm = mock_urlopen(body)
        monkeypatch.setattr(_marker_mod.urllib.request, "urlopen", MagicMock(return_value=cm))

        result = marker_convert(fake_pdf)
        assert result == "fallback text"

    def test_custom_url(self, tmp_path, monkeypatch):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        body = {"markdown": "ok"}
        cm = mock_urlopen(body)
        urlopen_mock = MagicMock(return_value=cm)
        monkeypatch.setattr(_marker_mod.urllib.request, "urlopen", urlopen_mock)

        marker_convert(fake_pdf, "http://custom:9999")
        req = urlopen_mock.call_args[0][0]
        assert req.full_url == "http://custom:9999/convert"

    def test_sends_multipart_with_pdf_filename(self, tmp_path, monkeypatch):
        fake_pdf = tmp_path / "myfile.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        body = {"markdown": "ok"}
        cm = mock_urlopen(body)
        urlopen_mock = MagicMock(return_value=cm)
        monkeypatch.setattr(_marker_mod.urllib.request, "urlopen", urlopen_mock)

        marker_convert(fake_pdf)
        req = urlopen_mock.call_args[0][0]
        assert b"myfile.pdf" in req.data
        assert "multipart/form-data" in req.get_header("Content-type")


# ---------------------------------------------------------------------------
# pdf_to_markdown (thin wrapper)
# ---------------------------------------------------------------------------


class TestPdfToMarkdown:
    def test_delegates_to_marker_convert(self, tmp_path, monkeypatch):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        with patch("aedist.pdf2md_marker.marker_convert", return_value="# Done") as mock:
            result = pdf_to_markdown(fake_pdf, marker_url="http://x:1")

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

        with patch("aedist.pdf2md_marker.pdf_to_markdown", return_value="# Marker result"):
            main([str(fake_pdf), "--output", str(out)])

        assert out.exists()
        text = out.read_text()
        assert "# Marker result" in text
        assert "Converted from PDF" in text
        assert "Marker" in text

    def test_default_output_path(self, tmp_path):
        fake_pdf = tmp_path / "report.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        with patch("aedist.pdf2md_marker.pdf_to_markdown", return_value="md"):
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

    def test_custom_marker_url(self, tmp_path):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")
        out = tmp_path / "out.md"

        with patch(
            "aedist.pdf2md_marker.pdf_to_markdown", return_value="ok"
        ) as mock:
            main([str(fake_pdf), "--output", str(out), "--marker-url", "http://other:5000"])

        mock.assert_called_once_with(fake_pdf, marker_url="http://other:5000")
