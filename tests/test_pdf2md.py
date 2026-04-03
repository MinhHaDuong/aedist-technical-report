"""Tests for aedist.pdf2md — PDF-to-Markdown converter."""

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from aedist.pdf2md import clean_markdown, get_output_path, process_model_response

# ---------------------------------------------------------------------------
# clean_markdown
# ---------------------------------------------------------------------------

class TestCleanMarkdown:
    def test_strips_markdown_fence(self):
        raw = "```markdown\n# Hello\n```"
        assert clean_markdown(raw) == "# Hello"

    def test_strips_html_fence(self):
        raw = "```html\n<table></table>\n```"
        assert clean_markdown(raw) == "<table></table>"

    def test_strips_bare_fence(self):
        raw = "```\nsome text\n```"
        assert clean_markdown(raw) == "some text"

    def test_normalises_tr_indent(self):
        raw = "      <tr><td>x</td></tr>"
        assert clean_markdown(raw) == "  <tr><td>x</td></tr>"

    def test_normalises_td_indent(self):
        raw = "  <td>val</td>"
        assert clean_markdown(raw) == "    <td>val</td>"

    def test_normalises_th_indent(self):
        raw = " <th>Header</th>"
        assert clean_markdown(raw) == "    <th>Header</th>"

    def test_strips_trailing_whitespace(self):
        raw = "line one   \nline two  "
        assert clean_markdown(raw) == "line one\nline two"

    def test_passthrough_plain_text(self):
        raw = "Just plain text"
        assert clean_markdown(raw) == "Just plain text"


# ---------------------------------------------------------------------------
# process_model_response
# ---------------------------------------------------------------------------

def _fake_response(content):
    """Build a minimal object matching the OpenAI response shape."""
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


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


# ---------------------------------------------------------------------------
# get_output_path
# ---------------------------------------------------------------------------

class TestGetOutputPath:
    def test_explicit_output_wins(self, tmp_path):
        explicit = tmp_path / "custom.md"
        result = get_output_path(tmp_path / "doc.pdf", explicit)
        assert result == explicit

    def test_default_swaps_suffix(self, tmp_path):
        pdf = tmp_path / "doc.pdf"
        result = get_output_path(pdf, None)
        assert result == tmp_path / "doc.md"

    def test_fallback_when_md_exists(self, tmp_path):
        pdf = tmp_path / "doc.pdf"
        (tmp_path / "doc.md").write_text("existing")
        result = get_output_path(pdf, None)
        assert result == tmp_path / "doc_converted.md"


# ---------------------------------------------------------------------------
# Argparse presence (source inspection)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# USER_PROMPT placeholder safety
# ---------------------------------------------------------------------------

def test_user_prompt_handles_braces():
    """Markdown with literal {} must not crash the prompt substitution."""
    from aedist.pdf2md import _PREV_PAGE_PLACEHOLDER, USER_PROMPT
    tricky = "style={color: red}"
    result = USER_PROMPT.replace(_PREV_PAGE_PLACEHOLDER, tricky, 1)
    assert tricky in result


# ---------------------------------------------------------------------------
# Argparse presence (source inspection)
# ---------------------------------------------------------------------------

def test_main_uses_argparse():
    source = Path(__file__).resolve().parent.parent / "src" / "aedist" / "pdf2md.py"
    text = source.read_text()
    assert "ArgumentParser" in text
    assert "add_argument" in text


# ---------------------------------------------------------------------------
# No print() calls (should use logging)
# ---------------------------------------------------------------------------

def test_no_print_calls():
    source = Path(__file__).resolve().parent.parent / "src" / "aedist" / "pdf2md.py"
    text = source.read_text()
    # Match print( but not inside strings or comments
    lines = text.splitlines()
    for i, line in enumerate(lines, 1):
        stripped = line.lstrip()
        if stripped.startswith("#") or stripped.startswith('"'):
            continue
        assert not re.match(r".*\bprint\s*\(", stripped), (
            f"Found print() call at line {i}: {line.strip()}"
        )
