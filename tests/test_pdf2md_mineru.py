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
