"""Convert PDF to Markdown via Mistral OCR API (direct, no LLM bottleneck).

Calls Mistral's /v1/ocr endpoint directly — a dedicated document parsing
service that returns page-by-page markdown with structured table extraction.
Unlike the OpenRouter file-parser plugin approach, there is no LLM output
token limit: all pages and all tables are returned.

Usage:
    python -m aedist.pdf2md_mistral_ocr input.pdf
    python -m aedist.pdf2md_mistral_ocr input.pdf --table-format html
    python -m aedist.pdf2md_mistral_ocr input.pdf --table-format markdown

Minh Ha-Duong, CNRS, 2025–
License CC-BY-SA
"""

import argparse
import base64
import json
import logging
import os
import sys
import urllib.request
from pathlib import Path

from .pdf2md_utils import get_output_path, metadata_comment

log = logging.getLogger(__name__)

MISTRAL_OCR_URL = "https://api.mistral.ai/v1/ocr"
DEFAULT_MODEL = "mistral-ocr-latest"
TABLE_FORMATS = ("html", "markdown")


def _ocr_request(pdf_path: Path, *, model: str, table_format: str) -> dict:
    """Send PDF to Mistral OCR API, return the raw JSON response."""
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise SystemExit("Set MISTRAL_API_KEY environment variable")

    pdf_bytes = pdf_path.read_bytes()
    b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
    data_url = f"data:application/pdf;base64,{b64_pdf}"

    payload = {
        "model": model,
        "document": {
            "type": "document_url",
            "document_url": data_url,
        },
        "table_format": table_format,
        "include_image_base64": False,
    }

    body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        MISTRAL_OCR_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    log.info(
        "Sending %s (%.1f MB) to Mistral OCR model=%s table_format=%s",
        pdf_path.name,
        len(pdf_bytes) / 1e6,
        model,
        table_format,
    )

    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _stitch_pages(ocr_result: dict) -> str:
    """Stitch per-page markdown into a single document.

    When table_format is set, table placeholders like [tbl-0.html](tbl-0.html)
    appear in the page markdown.  We inline the actual table content from the
    tables array so the output is self-contained.
    """
    pages = ocr_result.get("pages", [])
    parts = []

    for page in pages:
        md = page.get("markdown", "")

        # Inline table placeholders with actual content
        for tbl in page.get("tables", []):
            tbl_id = tbl.get("id", "")
            tbl_content = tbl.get("content", "")
            if tbl_id and tbl_content:
                # Replace both markdown link and bare reference forms
                md = md.replace(f"[{tbl_id}]({tbl_id})", tbl_content)
                md = md.replace(f"({tbl_id})", f"\n{tbl_content}\n")

        parts.append(f"<!-- PDF page {page.get('index', 0) + 1} -->\n{md}")

    return "\n\n".join(parts)


def pdf_to_markdown(
    pdf_path: Path,
    *,
    model: str = DEFAULT_MODEL,
    table_format: str = "html",
) -> str:
    """Convert a PDF to Markdown using Mistral OCR API."""
    result = _ocr_request(pdf_path, model=model, table_format=table_format)

    pages = result.get("pages", [])
    usage = result.get("usage_info", {})
    log.info(
        "Received %d pages, %d pages_processed",
        len(pages),
        usage.get("pages_processed", 0),
    )

    return _stitch_pages(result)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Convert PDF to Markdown via Mistral OCR API (direct)"
    )
    parser.add_argument("pdf", type=Path, help="Input PDF file")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output .md path (default: same name as PDF)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"OCR model (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--table-format",
        default="html",
        choices=TABLE_FORMATS,
        help="Table output format (default: html)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not args.pdf.exists():
        parser.error(f"File not found: {args.pdf}")
    if args.pdf.suffix.lower() != ".pdf":
        parser.error(f"Not a PDF: {args.pdf}")

    result = pdf_to_markdown(
        args.pdf,
        model=args.model,
        table_format=args.table_format,
    )

    output = get_output_path(args.pdf, args.output)
    actual_argv = sys.argv if argv is None else ["python", "-m", __spec__.name] + argv
    output.write_text(
        result
        + metadata_comment(
            args.pdf,
            backend="Mistral OCR (direct)",
            model=args.model,
            argv=actual_argv,
        ),
        encoding="utf-8",
    )
    log.info("Wrote %s", output)


if __name__ == "__main__":
    main()
