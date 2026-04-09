"""Tests for aedist.build_corpus — RAG corpus builder."""

from pathlib import Path

from aedist.build_corpus import (
    parse_reference_titles,
    select_by_reference,
    split_into_sections,
)


def test_split_by_page_markers():
    """split_into_sections separates on <!-- PDF page N --> markers."""
    md = (
        "<!-- PDF page 1 -->\n"
        "# Document Title\n"
        "Some intro text.\n"
        "\n"
        "<!-- PDF page 2 -->\n"
        "## Section A\n"
        "Content of section A.\n"
    )
    sections = split_into_sections(md)
    assert len(sections) == 2
    assert sections[0]["page"] == 1
    assert "Document Title" in sections[0]["text"]
    assert sections[1]["page"] == 2
    assert "Section A" in sections[1]["text"]


def test_split_preserves_table_content():
    """Sections containing HTML tables are kept intact within a page."""
    md = (
        "<!-- PDF page 5 -->\n"
        "## Annex I\n"
        "<table>\n"
        "  <tr><td>Plant A</td><td>Coal</td></tr>\n"
        "  <tr><td>Plant B</td><td>Gas</td></tr>\n"
        "</table>\n"
    )
    sections = split_into_sections(md)
    assert len(sections) >= 1
    table_sections = [s for s in sections if "<table>" in s["text"]]
    assert len(table_sections) == 1
    assert "Plant A" in table_sections[0]["text"]
    assert "Plant B" in table_sections[0]["text"]


def test_split_extracts_headings():
    """Headings are extracted into the section metadata."""
    md = (
        "<!-- PDF page 3 -->\n"
        "## Danh mục các dự án điện\n"
        "Some content here.\n"
    )
    sections = split_into_sections(md)
    heading_sections = [s for s in sections if s["heading"]]
    assert len(heading_sections) >= 1
    assert "Danh mục các dự án điện" in heading_sections[0]["heading"]


def test_split_empty_input():
    """Empty input yields no sections."""
    assert split_into_sections("") == []
    assert split_into_sections("   \n\n  ") == []


def test_split_no_page_markers():
    """Content without page markers still produces sections."""
    md = "## Some heading\nSome content.\n\n## Another heading\nMore content.\n"
    sections = split_into_sections(md)
    assert len(sections) >= 1
    assert all(s["page"] is None for s in sections)


def test_parse_reference_titles(tmp_path):
    """parse_reference_titles extracts titles from LaTeX-style README."""
    readme = tmp_path / "README.md"
    readme.write_text(
        "# Resources\n\n"
        r"Author (2024) \emph{Quyết định 1682/QĐ-TTg Phê duyệt}. Report." "\n\n"
        "Author (2023) `From aspiration to reality for PDP8'. News.\n"
    )
    titles = parse_reference_titles(readme)
    assert len(titles) == 2
    assert "Quyết định 1682/QĐ-TTg Phê duyệt" in titles
    assert "From aspiration to reality for PDP8" in titles


def test_select_by_reference_filters():
    """select_by_reference keeps items matching reference titles."""
    items = [
        {"key": "A", "title": "Quyết định 1682/QĐ-TTg Phê duyệt bổ sung",
         "attachment_key": "A1"},
        {"key": "B", "title": "Unrelated document about cooking",
         "attachment_key": "B1"},
        {"key": "C", "title": "PDP8 implementation plan report",
         "attachment_key": "C1"},
    ]
    ref_titles = [
        "Quyết định 1682/QĐ-TTg Phê duyệt bổ sung, cập nhật Kế hoạch",
    ]
    selected = select_by_reference(items, ref_titles, threshold=60)
    keys = [s["key"] for s in selected]
    assert "A" in keys
    assert "B" not in keys


def test_select_by_reference_empty_refs():
    """With no reference titles, nothing is selected."""
    items = [{"key": "A", "title": "Some doc", "attachment_key": "A1"}]
    selected = select_by_reference(items, [], threshold=60)
    assert len(selected) == 0


def test_score_system_prompt_exists():
    """The scoring system prompt is defined and non-empty."""
    from aedist.build_corpus import SCORE_SYSTEM
    assert "thermal power" in SCORE_SYSTEM.lower()
    assert "score" in SCORE_SYSTEM.lower()


def test_cli_argparse_has_required_args():
    """CLI has --query/--items, --output, --ollama-url flags."""
    source = Path(__file__).parent.parent / "src" / "aedist" / "build_corpus.py"
    text = source.read_text()
    assert "--query" in text
    assert "--items" in text
    assert "--output" in text
    assert "--ollama-url" in text
    assert "--dry-run" in text
    assert "--scorer-model" in text
    assert "--reference" in text
    assert "--converter" in text
