"""Tests for aedist.pdf2md_marker — Marker API container backend."""

from pathlib import Path


def test_module_has_pdf_to_markdown():
    source = Path("src/aedist/pdf2md_marker.py").read_text()
    assert "def pdf_to_markdown(" in source


def test_module_has_argparse():
    source = Path("src/aedist/pdf2md_marker.py").read_text()
    assert "ArgumentParser" in source


def test_module_uses_stdlib_http():
    source = Path("src/aedist/pdf2md_marker.py").read_text()
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
    source = Path("src/aedist/pdf2md_marker.py").read_text()
    assert "metadata_comment" in source


def test_uses_get_output_path():
    source = Path("src/aedist/pdf2md_marker.py").read_text()
    assert "get_output_path" in source
