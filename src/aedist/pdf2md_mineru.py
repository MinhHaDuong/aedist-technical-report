"""Convert PDF to Markdown using MinerU API container.

Uses the mineru-api container for layout-aware PDF conversion with
cross-page table merging. No Python deps beyond stdlib.

Usage:
    python -m aedist.pdf2md_mineru input.pdf
    python -m aedist.pdf2md_mineru input.pdf --output output.md --mineru-url http://localhost:8010

Requires: mineru-api container running locally.
    podman run -d --name mineru-api --gpus all -p 8010:8000 jianjungki/mineru-api
"""

import argparse
import io
import json
import logging
import sys
import urllib.request
import zipfile
from pathlib import Path

from .pdf2md_utils import get_output_path, metadata_comment

log = logging.getLogger(__name__)

DEFAULT_MINERU_URL = "http://localhost:8010"


def mineru_convert(pdf_path: Path, mineru_url: str = DEFAULT_MINERU_URL) -> str:
    """Send PDF to MinerU API, return markdown string.

    MinerU returns a ZIP containing markdown and images.
    We extract just the markdown content.
    """
    url = f"{mineru_url}/api/parse"

    boundary = "----MinerUBoundary"
    pdf_bytes = pdf_path.read_bytes()

    body = (
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{pdf_path.name}"\r\n'
            f"Content-Type: application/pdf\r\n\r\n"
        ).encode()
        + pdf_bytes
        + (
            f"\r\n--{boundary}\r\n"
            f'Content-Disposition: form-data; name="return_md"\r\n\r\n'
            f"true\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="table_enable"\r\n\r\n'
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
        content_type = resp.headers.get("Content-Type", "")
        raw = resp.read()

    # MinerU may return ZIP or JSON depending on version
    if "zip" in content_type or raw[:4] == b"PK\x03\x04":
        return _extract_md_from_zip(raw)

    # JSON response
    result = json.loads(raw.decode("utf-8"))
    if "content" in result:
        return result["content"]
    if "markdown" in result:
        return result["markdown"]
    if "md_content" in result:
        return result["md_content"]
    # Return whatever text we got
    return json.dumps(result, indent=2, ensure_ascii=False)


def _extract_md_from_zip(zip_bytes: bytes) -> str:
    """Extract markdown content from MinerU ZIP response."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        md_files = [n for n in zf.namelist() if n.endswith(".md")]
        if not md_files:
            raise ValueError(f"No .md files in ZIP (contents: {zf.namelist()[:10]})")
        # Take the first (usually only) markdown file
        return zf.read(md_files[0]).decode("utf-8")


def pdf_to_markdown(pdf_path: Path, *, mineru_url: str = DEFAULT_MINERU_URL) -> str:
    """Convert a PDF to Markdown using MinerU API container."""
    log.info("Sending %s to MinerU...", pdf_path.name)
    return mineru_convert(pdf_path, mineru_url)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Convert PDF to Markdown via MinerU API container"
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
        "--mineru-url",
        default=DEFAULT_MINERU_URL,
        help=f"MinerU API URL (default: {DEFAULT_MINERU_URL})",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not args.pdf.exists():
        parser.error(f"File not found: {args.pdf}")
    if args.pdf.suffix.lower() != ".pdf":
        parser.error(f"Not a PDF: {args.pdf}")

    result = pdf_to_markdown(args.pdf, mineru_url=args.mineru_url)

    output = get_output_path(args.pdf, args.output)
    actual_argv = sys.argv if argv is None else ["python", "-m", __spec__.name] + argv
    output.write_text(
        result + metadata_comment(args.pdf, backend="MinerU", model="n/a", argv=actual_argv),
        encoding="utf-8",
    )
    log.info("Wrote %s", output)


if __name__ == "__main__":
    main()
