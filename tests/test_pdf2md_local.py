"""Tests for aedist.pdf2md_local — GROBID-based PDF conversion."""

from aedist.pdf2md_local import _table_to_html, _text, tei_to_markdown


SAMPLE_TEI = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title level="a" type="main">Test Document Title</title>
      </titleStmt>
      <publicationStmt><publisher/></publicationStmt>
      <sourceDesc><biblStruct><analytic>
        <title level="a" type="main">Test Document Title</title>
      </analytic><monogr><imprint/></monogr></biblStruct></sourceDesc>
    </fileDesc>
  </teiHeader>
  <text>
    <body>
      <div>
        <head n="1">Section One</head>
        <p>First paragraph of content.</p>
      </div>
      <div>
        <head n="1.1">Subsection</head>
        <p>More content here.</p>
      </div>
    </body>
    <figure type="table">
      <head>Table 1: Power Plants</head>
      <table>
        <row role="label">
          <cell>Name</cell>
          <cell>Capacity</cell>
        </row>
        <row>
          <cell>Pha Lai</cell>
          <cell>600 MW</cell>
        </row>
        <row>
          <cell>Ba Ria</cell>
          <cell>390 MW</cell>
        </row>
      </table>
    </figure>
  </text>
</TEI>"""


def test_tei_to_markdown_extracts_title():
    md = tei_to_markdown(SAMPLE_TEI)
    assert md.startswith("# Test Document Title")


def test_tei_to_markdown_extracts_sections():
    md = tei_to_markdown(SAMPLE_TEI)
    assert "## Section One" in md
    assert "### Subsection" in md


def test_tei_to_markdown_extracts_paragraphs():
    md = tei_to_markdown(SAMPLE_TEI)
    assert "First paragraph of content." in md
    assert "More content here." in md


def test_tei_to_markdown_extracts_tables():
    md = tei_to_markdown(SAMPLE_TEI)
    assert "<table>" in md
    assert "Pha Lai" in md
    assert "600 MW" in md
    assert "<caption>Table 1: Power Plants</caption>" in md


def test_table_to_html_header_row():
    """Label rows use <th> tags."""
    md = tei_to_markdown(SAMPLE_TEI)
    assert "<th>" in md
    assert "<th>Name</th>" in md


def test_tables_have_context_preamble():
    """Each table section includes a context breadcrumb."""
    md = tei_to_markdown(SAMPLE_TEI)
    assert "*Context:" in md
    assert "Test Document Title" in md.split("*Context:")[1]
    assert "Table 1: Power Plants" in md.split("*Context:")[1]


def test_tables_have_own_heading():
    """Each table gets its own ## heading."""
    md = tei_to_markdown(SAMPLE_TEI)
    assert "## Table 1: Power Plants" in md


def test_cli_has_grobid_url_flag():
    """CLI accepts --grobid-url flag."""
    source_path = __import__("pathlib").Path(__file__).parent.parent / "src" / "aedist" / "pdf2md_local.py"
    text = source_path.read_text()
    assert "--grobid-url" in text
    assert "localhost:8070" in text
