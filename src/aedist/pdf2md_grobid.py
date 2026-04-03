"""Convert PDF to Markdown using local GROBID service.

Uses GROBID's TEI XML output and converts to structured Markdown,
preserving tables as HTML. No cloud API required.

Usage:
    python -m aedist.pdf2md_grobid input.pdf
    python -m aedist.pdf2md_grobid input.pdf --output output.md --grobid-url http://localhost:8070

Requires: GROBID running locally (e.g., podman start grobid).
"""

import argparse
import logging
import platform
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

log = logging.getLogger(__name__)

TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}
DEFAULT_GROBID_URL = "http://localhost:8070"


def grobid_process(pdf_path: Path, grobid_url: str = DEFAULT_GROBID_URL) -> str:
    """Send PDF to GROBID, return TEI XML string."""
    url = f"{grobid_url}/api/processFulltextDocument"

    # Build multipart form data
    boundary = "----GROBIDBoundary"
    pdf_bytes = pdf_path.read_bytes()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="input"; filename="{pdf_path.name}"\r\n'
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode() + pdf_bytes + (
        f"\r\n--{boundary}\r\n"
        f'Content-Disposition: form-data; name="consolidateHeader"\r\n\r\n'
        f"0\r\n"
        f"--{boundary}--\r\n"
    ).encode()

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return resp.read().decode("utf-8")


def _text(elem) -> str:
    """Extract all text from an element, including children."""
    return "".join(elem.itertext()).strip() if elem is not None else ""


def _table_to_html(table_elem) -> str:
    """Convert a TEI table element to HTML table."""
    head = table_elem.find("tei:head", TEI_NS)
    rows = table_elem.findall(".//tei:row", TEI_NS)
    if not rows:
        return ""

    parts = []
    if head is not None and head.text:
        parts.append(f"<caption>{head.text.strip()}</caption>")

    for row in rows:
        role = row.get("role", "")
        cells = row.findall("tei:cell", TEI_NS)
        tag = "th" if role == "label" else "td"
        cell_parts = []
        for cell in cells:
            text = _text(cell)
            cols = cell.get("cols")
            colspan = f' colspan="{cols}"' if cols else ""
            cell_parts.append(f"    <{tag}{colspan}>{text}</{tag}>")
        parts.append("  <tr>\n" + "\n".join(cell_parts) + "\n  </tr>")

    return "<table>\n" + "\n".join(parts) + "\n</table>"


def tei_to_markdown(tei_xml: str) -> str:
    """Convert TEI XML from GROBID to Markdown with HTML tables.

    Each table gets its own section with a context preamble showing
    where it sits in the document (title > section > table caption).
    This helps RAG systems understand the semantic context of each chunk.
    """
    root = ET.fromstring(tei_xml)

    # Extract title
    title_elem = root.find(".//tei:titleStmt/tei:title", TEI_NS)
    title = _text(title_elem) if title_elem is not None else "Untitled"

    parts = [f"# {title}\n"]

    # Extract body content, tracking section context for tables
    body = root.find(".//tei:body", TEI_NS)
    if body is None:
        return parts[0]

    current_section = ""
    emitted: set[int] = set()  # track by id() to avoid duplicates

    for div in body.findall(".//tei:div", TEI_NS):
        # Section heading
        head = div.find("tei:head", TEI_NS)
        if head is not None:
            level = head.get("n", "")
            depth = level.count(".") + 2 if level else 2
            depth = min(depth, 4)
            current_section = _text(head)
            parts.append(f"\n{'#' * depth} {current_section}\n")

        # Paragraphs
        for p in div.findall("tei:p", TEI_NS):
            text = _text(p)
            if text:
                parts.append(f"\n{text}\n")

        # Direct child tables only (not nested div tables)
        for fig in div.findall('tei:figure[@type="table"]', TEI_NS):
            if id(fig) not in emitted:
                _emit_table(fig, title, current_section, parts)
                emitted.add(id(fig))

    # Tables directly under body (not inside any div)
    for fig in body.findall('tei:figure[@type="table"]', TEI_NS):
        if id(fig) not in emitted:
            _emit_table(fig, title, current_section, parts)
            emitted.add(id(fig))

    # Tables outside body (some TEI variants put them under <text>)
    for fig in root.findall('.//tei:figure[@type="table"]', TEI_NS):
        if id(fig) not in emitted:
            _emit_table(fig, title, current_section, parts)
            emitted.add(id(fig))

    return "\n".join(parts)


def _emit_table(fig, doc_title: str, section: str, parts: list[str]):
    """Emit a table as its own headed section with context preamble."""
    head = fig.find("tei:head", TEI_NS)
    caption = _text(head) if head is not None else ""
    html = _table_to_html(fig)
    if not html:
        return

    # Build breadcrumb: Document > Section > Table
    breadcrumb_parts = [doc_title]
    if section:
        breadcrumb_parts.append(section)
    if caption:
        breadcrumb_parts.append(caption)
    breadcrumb = " > ".join(breadcrumb_parts)

    # Emit as own section
    heading = caption if caption else "Table"
    parts.append(f"\n## {heading}\n")
    parts.append(f"*Context: {breadcrumb}*\n")
    parts.append(f"\n{html}\n")


def metadata_comment(pdf_path: Path, argv: list[str]) -> str:
    """Conversion metadata appended as HTML comment."""
    return (
        f"\n\n<!-- Converted from PDF using:\n"
        f"Command: python {' '.join(argv)}\n"
        f"Date: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        f"Source: {pdf_path.name}\n"
        f"Platform: {platform.platform()}\n"
        f"Python: {platform.python_version()}\n"
        f"Backend: GROBID (local)\n"
        f"-->"
    )


def pdf_to_markdown_local(pdf_path: Path, *,
                          grobid_url: str = DEFAULT_GROBID_URL) -> str:
    """Convert a PDF to Markdown using local GROBID."""
    log.info("Sending %s to GROBID...", pdf_path.name)
    tei_xml = grobid_process(pdf_path, grobid_url)
    log.info("Converting TEI XML to Markdown...")
    return tei_to_markdown(tei_xml)


def get_output_path(pdf_path: Path, output_arg: Path | None) -> Path:
    """Determine output path: explicit arg > stem.md > stem_converted.md."""
    if output_arg:
        return output_arg
    candidate = pdf_path.with_suffix(".md")
    if candidate.exists():
        return pdf_path.with_name(pdf_path.stem + "_converted.md")
    return candidate


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Convert PDF to Markdown via local GROBID"
    )
    parser.add_argument("pdf", type=Path, help="Input PDF file")
    parser.add_argument("--output", "-o", type=Path, default=None,
                        help="Output .md path (default: same name as PDF)")
    parser.add_argument("--grobid-url", default=DEFAULT_GROBID_URL,
                        help=f"GROBID service URL (default: {DEFAULT_GROBID_URL})")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not args.pdf.exists():
        parser.error(f"File not found: {args.pdf}")
    if args.pdf.suffix.lower() != ".pdf":
        parser.error(f"Not a PDF: {args.pdf}")

    result = pdf_to_markdown_local(args.pdf, grobid_url=args.grobid_url)

    output = get_output_path(args.pdf, args.output)
    actual_argv = sys.argv if argv is None else ["python", "-m", "aedist.pdf2md_grobid"] + argv
    output.write_text(result + metadata_comment(args.pdf, actual_argv),
                      encoding="utf-8")
    log.info("Wrote %s", output)


if __name__ == "__main__":
    main()
