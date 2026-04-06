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
        if stripped.startswith("#") or stripped.startswith('"'):
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
