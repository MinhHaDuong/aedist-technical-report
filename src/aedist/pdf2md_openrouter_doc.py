"""Convert PDF to Markdown via OpenRouter document-level file-parser plugin.

Unlike pdf2md_openrouter (page-by-page vision), this sends the entire PDF to
OpenRouter's file-parser plugin which routes to Mistral OCR or Cloudflare AI
for whole-document conversion — similar to how Marker processes the full doc
in one call.

Engines:
    mistral-ocr   — OCR + table structure, $2/1000 pages
    cloudflare-ai — text extraction, free

Usage:
    python -m aedist.pdf2md_openrouter_doc input.pdf
    python -m aedist.pdf2md_openrouter_doc input.pdf --engine mistral-ocr --model anthropic/claude-sonnet-4
    python -m aedist.pdf2md_openrouter_doc input.pdf --engine cloudflare-ai

Minh Ha-Duong, CNRS, 2025–
License CC-BY-SA
"""

import argparse
import base64
import logging
import os
import sys
from pathlib import Path

from openai import OpenAI

from .pdf2md_utils import get_output_path, metadata_comment

log = logging.getLogger(__name__)

DEFAULT_ENGINE = "mistral-ocr"
DEFAULT_MODEL = "anthropic/claude-sonnet-4"
ENGINES = ("mistral-ocr", "cloudflare-ai")

EXTRACT_PROMPT = (
    "Convert this PDF document to well-structured Markdown. "
    "Preserve all tables using HTML table syntax (<table>, <tr>, <td>, <th>). "
    "Preserve all Vietnamese diacritics exactly. "
    "Include all text content. Omit page numbers."
)


def pdf_to_markdown(
    pdf_path: Path,
    *,
    engine: str = DEFAULT_ENGINE,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 65536,
) -> str:
    """Send entire PDF to OpenRouter file-parser plugin, return markdown."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("Set OPENROUTER_API_KEY environment variable")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    pdf_bytes = pdf_path.read_bytes()
    b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
    data_url = f"data:application/pdf;base64,{b64_pdf}"

    log.info(
        "Sending %s (%.1f MB) to OpenRouter engine=%s model=%s",
        pdf_path.name,
        len(pdf_bytes) / 1e6,
        engine,
        model,
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": EXTRACT_PROMPT},
                    {
                        "type": "file",
                        "file": {
                            "filename": pdf_path.name,
                            "file_data": data_url,
                        },
                    },
                ],
            },
        ],
        max_tokens=max_tokens,
        extra_body={
            "plugins": [
                {
                    "id": "file-parser",
                    "pdf": {"engine": engine},
                }
            ],
        },
    )

    if not response.choices:
        raise ValueError("OpenRouter returned empty choices")

    content = response.choices[0].message.content
    if not content:
        raise ValueError("OpenRouter returned empty content")

    log.info("Received %d chars of markdown", len(content))
    return content


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Convert PDF to Markdown via OpenRouter file-parser plugin"
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
        "--engine",
        default=DEFAULT_ENGINE,
        choices=ENGINES,
        help=f"PDF parsing engine (default: {DEFAULT_ENGINE})",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"LLM model for post-processing (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=65536,
        help="Max output tokens (default: 65536)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not args.pdf.exists():
        parser.error(f"File not found: {args.pdf}")
    if args.pdf.suffix.lower() != ".pdf":
        parser.error(f"Not a PDF: {args.pdf}")

    result = pdf_to_markdown(
        args.pdf,
        engine=args.engine,
        model=args.model,
        max_tokens=args.max_tokens,
    )

    output = get_output_path(args.pdf, args.output)
    mod = __spec__.name if __spec__ else __name__
    actual_argv = sys.argv if argv is None else ["python", "-m", mod] + argv
    output.write_text(
        result
        + metadata_comment(
            args.pdf,
            backend=f"OpenRouter/{args.engine}",
            model=args.model,
            argv=actual_argv,
        ),
        encoding="utf-8",
    )
    log.info("Wrote %s", output)


if __name__ == "__main__":
    main()
