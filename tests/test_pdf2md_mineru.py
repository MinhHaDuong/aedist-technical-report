"""Tests for aedist.pdf2md_mineru — MinerU API container backend."""

import io
import zipfile
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


def test_extract_md_from_zip():
    from aedist.pdf2md_mineru import _extract_md_from_zip

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("output/result.md", "# Hello\n\nTable content here.")
    zip_bytes = buf.getvalue()

    md = _extract_md_from_zip(zip_bytes)
    assert "# Hello" in md
    assert "Table content" in md


def test_uses_metadata_comment():
    source = Path("src/aedist/pdf2md_mineru.py").read_text()
    assert "metadata_comment" in source


def test_uses_get_output_path():
    source = Path("src/aedist/pdf2md_mineru.py").read_text()
    assert "get_output_path" in source
