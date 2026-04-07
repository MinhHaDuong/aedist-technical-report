"""Convert PDF to Markdown using Marker API container.

Uses the marker-api container for layout-aware PDF conversion with
table structure preservation. No Python deps beyond stdlib.

Usage:
    python -m aedist.pdf2md_marker input.pdf
    python -m aedist.pdf2md_marker input.pdf --output output.md --marker-url http://localhost:8001

Requires: marker-api container running locally.
    podman run -d --name marker-api --device nvidia.com/gpu=all -p 8001:8000 savatar101/marker-api
"""

import argparse
import json
import logging
import sys
import urllib.request
from pathlib import Path

from .pdf2md_utils import get_output_path, metadata_comment

log = logging.getLogger(__name__)

DEFAULT_MARKER_URL = "http://localhost:8001"


def marker_convert(pdf_path: Path, marker_url: str = DEFAULT_MARKER_URL) -> str:
    """Send PDF to Marker API, return markdown string."""
    url = f"{marker_url}/convert"

    boundary = "----MarkerBoundary"
    pdf_bytes = pdf_path.read_bytes()

    body = (
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="pdf_file"; filename="{pdf_path.name}"\r\n'
            f"Content-Type: application/pdf\r\n\r\n"
        ).encode()
        + pdf_bytes
        + (
            f"\r\n--{boundary}\r\n"
            f'Content-Disposition: form-data; name="force_ocr"\r\n\r\n'
            f"true\r\n"
            f"--{boundary}--\r\n"
        ).encode()
    )

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    # Marker returns a list of documents; take the first
    if isinstance(result, list):
        result = result[0] if result else {}
    return result.get("markdown", result.get("text", ""))


def pdf_to_markdown(pdf_path: Path, *, marker_url: str = DEFAULT_MARKER_URL) -> str:
    """Convert a PDF to Markdown using Marker API container."""
    log.info("Sending %s to Marker...", pdf_path.name)
    return marker_convert(pdf_path, marker_url)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Convert PDF to Markdown via Marker API container"
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
        "--marker-url",
        default=DEFAULT_MARKER_URL,
        help=f"Marker API URL (default: {DEFAULT_MARKER_URL})",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not args.pdf.exists():
        parser.error(f"File not found: {args.pdf}")
    if args.pdf.suffix.lower() != ".pdf":
        parser.error(f"Not a PDF: {args.pdf}")

    result = pdf_to_markdown(args.pdf, marker_url=args.marker_url)

    output = get_output_path(args.pdf, args.output)
    actual_argv = sys.argv if argv is None else ["python", "-m", __spec__.name] + argv
    output.write_text(
        result + metadata_comment(args.pdf, backend="Marker", model="n/a", argv=actual_argv),
        encoding="utf-8",
    )
    log.info("Wrote %s", output)


if __name__ == "__main__":
    main()
