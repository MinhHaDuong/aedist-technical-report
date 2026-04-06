"""Tests for aedist.pdf2md_utils — shared PDF converter utilities."""

from aedist.pdf2md_utils import (
    CONVERTERS,
    PREV_PAGE_PLACEHOLDER,
    USER_PROMPT,
    Converter,
    clean_markdown,
    get_converter,
    get_output_path,
    metadata_comment,
)

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
# metadata_comment
# ---------------------------------------------------------------------------


class TestMetadataComment:
    def test_contains_all_fields(self, tmp_path):
        pdf = tmp_path / "doc.pdf"
        result = metadata_comment(
            pdf, backend="TestBack", model="test-model", argv=["test", "cmd"]
        )
        assert "Backend: TestBack" in result
        assert "Model: test-model" in result
        assert "Source: doc.pdf" in result
        assert "Command: python test cmd" in result
        assert "Date:" in result

    def test_is_html_comment(self, tmp_path):
        pdf = tmp_path / "doc.pdf"
        result = metadata_comment(pdf, backend="X", model="Y", argv=["z"])
        assert result.strip().startswith("<!--")
        assert result.strip().endswith("-->")


# ---------------------------------------------------------------------------
# USER_PROMPT placeholder safety
# ---------------------------------------------------------------------------


def test_user_prompt_handles_braces():
    """Markdown with literal {} must not crash the prompt substitution."""
    tricky = "style={color: red}"
    result = USER_PROMPT.replace(PREV_PAGE_PLACEHOLDER, tricky, 1)
    assert tricky in result


# ---------------------------------------------------------------------------
# Converter Protocol and registry
# ---------------------------------------------------------------------------


class TestConverterRegistry:
    def test_all_backends_registered(self):
        assert set(CONVERTERS) == {
            "grobid",
            "vision",
            "cloud",
            "cloud-doc",
            "mistral-ocr",
            "marker",
            "mineru",
        }

    def test_registered_backends_satisfy_protocol(self):
        for name, conv in CONVERTERS.items():
            assert isinstance(conv, Converter), f"{name} does not satisfy Converter"

    def test_get_converter_returns_entry(self):
        assert get_converter("grobid") is CONVERTERS["grobid"]

    def test_get_converter_unknown_raises(self):
        import pytest

        with pytest.raises(KeyError, match="Unknown converter 'bogus'"):
            get_converter("bogus")

    def test_custom_converter_satisfies_protocol(self):
        """A plain class with pdf_to_markdown is a valid Converter."""

        class Dummy:
            def pdf_to_markdown(self, pdf_path, **kwargs):
                return ""

        assert isinstance(Dummy(), Converter)
