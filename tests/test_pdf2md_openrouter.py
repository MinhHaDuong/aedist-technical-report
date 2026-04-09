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
