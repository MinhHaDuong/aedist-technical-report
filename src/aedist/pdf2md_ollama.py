"""Convert PDF pages to Markdown via local multimodal LLM (Ollama).

Renders each page as JPEG, sends to a local Ollama vision model,
returns structured Markdown. No cloud API required.

Usage:
    python -m aedist.pdf2md_ollama input.pdf
    python -m aedist.pdf2md_ollama input.pdf --output out.md --model gemma4:26b --dpi 200
"""

import argparse
import base64
import json
import logging
import sys
import tempfile
import urllib.request
from pathlib import Path

from .pdf2md_utils import (
    PREV_PAGE_PLACEHOLDER,
    SYSTEM_PROMPT,
    USER_PROMPT,
    clean_markdown,
    get_output_path,
    metadata_comment,
)

log = logging.getLogger(__name__)

DEFAULT_MODEL = "gemma4:26b"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_DPI = 200  # lower than cloud (300) — local bandwidth is free, GPU is the bottleneck


def _ollama_chat_vision(model: str, messages: list[dict],
                        ollama_url: str = DEFAULT_OLLAMA_URL) -> str:
    """Call Ollama chat API with image content, return text response."""
    url = f"{ollama_url}/api/chat"
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
    }).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    # Vision inference on large pages can be slow; 10 min timeout per page
    with urllib.request.urlopen(req, timeout=600) as resp:
        result = json.loads(resp.read())
    content = result.get("message", {}).get("content", "")
    if not content:
        raise ValueError(f"Ollama returned empty response for model {model}")
    return content


def pdf_to_markdown(pdf_path, *, model=DEFAULT_MODEL, dpi=DEFAULT_DPI,
                    ollama_url=DEFAULT_OLLAMA_URL):
    """Convert a PDF to Markdown by sending each page image to a local vision LLM."""
    from pdf2image import convert_from_path  # heavy dep, import lazily

    log.info("Converting %s to images at %d DPI...", pdf_path.name, dpi)
    images = convert_from_path(str(pdf_path), dpi=dpi, fmt="jpeg")

    markdown_pieces = []
    previous_page_markdown = ""

    for page_num, image in enumerate(images):
        log.info("Processing page %d/%d...", page_num + 1, len(images))

        with tempfile.NamedTemporaryFile(suffix=".jpeg", delete=True) as tmp:
            image.save(tmp, "JPEG")
            tmp.flush()
            tmp.seek(0)
            encoded_image = base64.b64encode(tmp.read()).decode("utf-8")

        user_text = USER_PROMPT.replace(
            PREV_PAGE_PLACEHOLDER, previous_page_markdown, 1
        )

        # Ollama multimodal format: images as base64 in the message
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": user_text,
                "images": [encoded_image],
            },
        ]

        raw = _ollama_chat_vision(model, messages, ollama_url)
        cleaned = clean_markdown(raw)
        markdown_text = f"<!-- PDF page {page_num + 1} -->\n" + cleaned
        markdown_pieces.append(markdown_text)
        previous_page_markdown = markdown_text

        log.info("Page %d/%d done.", page_num + 1, len(images))

    return "\n".join(markdown_pieces)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Convert PDF to Markdown via local vision LLM (Ollama)"
    )
    parser.add_argument("pdf", type=Path, help="Input PDF file")
    parser.add_argument("--output", "-o", type=Path, default=None,
                        help="Output .md path (default: same name as PDF)")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Ollama vision model (default: {DEFAULT_MODEL})")
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI,
                        help=f"DPI for PDF rasterisation (default: {DEFAULT_DPI})")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL,
                        help=f"Ollama service URL (default: {DEFAULT_OLLAMA_URL})")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not args.pdf.exists():
        parser.error(f"File not found: {args.pdf}")
    if args.pdf.suffix.lower() != ".pdf":
        parser.error(f"Not a PDF: {args.pdf}")

    result = pdf_to_markdown(args.pdf, model=args.model, dpi=args.dpi,
                             ollama_url=args.ollama_url)

    output = get_output_path(args.pdf, args.output)
    actual_argv = sys.argv if argv is None else ["python", "-m", "aedist.pdf2md_ollama"] + argv
    output.write_text(
        result + metadata_comment(args.pdf, backend="Ollama", model=args.model,
                                  argv=actual_argv),
        encoding="utf-8",
    )
    log.info("Wrote %s", output)


if __name__ == "__main__":
    main()
