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
