"""Convert PDF to Markdown using MinerU v3.x API container.

Uses the official MinerU container (opendatalab/MinerU) for layout-aware
PDF conversion with GPU-accelerated table recognition. No Python deps
beyond stdlib.

Usage:
    python -m aedist.pdf2md_mineru input.pdf
    python -m aedist.pdf2md_mineru input.pdf --output output.md --mineru-url http://localhost:8010

Requires: MinerU v3.x container running locally.
    podman run -d --name mineru-api --gpus all -p 8010:8000 mineru:latest mineru-api --host 0.0.0.0 --port 8000
"""

import argparse
import json
import logging
import sys
import urllib.request
from pathlib import Path

from .pdf2md_utils import get_output_path, metadata_comment

log = logging.getLogger(__name__)

DEFAULT_MINERU_URL = "http://localhost:8010"


def mineru_convert(pdf_path: Path, mineru_url: str = DEFAULT_MINERU_URL) -> str:
    """Send PDF to MinerU v3.x API (POST /file_parse), return markdown."""
    url = f"{mineru_url}/file_parse"

    boundary = "----MinerUBoundary"
    pdf_bytes = pdf_path.read_bytes()

    chunks = [
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="files"; filename="{pdf_path.name}"\r\n'
            f"Content-Type: application/pdf\r\n\r\n"
        ).encode(),
        pdf_bytes,
    ]
    for name, value in [
        ("backend", "pipeline"),
        ("lang_list", "latin"),
        ("table_enable", "true"),
        ("return_md", "true"),
    ]:
        chunks.append(
            f"\r\n--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}".encode()
        )
    chunks.append(f"\r\n--{boundary}--\r\n".encode())

    req = urllib.request.Request(
        url,
        data=b"".join(chunks),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=1800) as resp:
        result = json.load(resp)

    if "created_at" in result and "completed_at" in result:
        from datetime import datetime

        t0 = datetime.fromisoformat(result["created_at"])
        t1 = datetime.fromisoformat(result["completed_at"])
        log.info("MinerU %s: %.1fs", result.get("backend", "?"), (t1 - t0).total_seconds())

    # v3.x: {"results": {"<filename>": {"md_content": "..."}}}
    if "results" in result:
        file_result = next(iter(result["results"].values()))
        return file_result["md_content"]
    raise ValueError(f"Unexpected MinerU response keys: {list(result.keys())}")


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
