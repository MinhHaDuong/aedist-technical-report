"""Tests for aedist.pdf2md_ollama — Ollama-based PDF-to-Markdown converter."""

import re
from pathlib import Path

import pytest


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
        if stripped.startswith("#") or stripped.startswith('"'):
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
    assert 'raise ValueError' in text
