"""Convert PDF pages to Markdown via OpenRouter vision LLM.

Renders each page as JPEG, sends to a cloud vision model via OpenRouter
(OpenAI-compatible API), returns structured Markdown.

Usage:
    python -m aedist.pdf2md_openrouter input.pdf
    python -m aedist.pdf2md_openrouter input.pdf --output out.md --model gpt-4o --dpi 300

Minh Ha-Duong, CNRS, 2025–
License CC-BY-SA
"""

import argparse
import base64
import logging
import sys
import tempfile
from pathlib import Path

from openai import OpenAI

from .pdf2md_utils import (
    PREV_PAGE_PLACEHOLDER,
    SYSTEM_PROMPT,
    USER_PROMPT,
    clean_markdown,
    get_output_path,
    metadata_comment,
)

log = logging.getLogger(__name__)

DEFAULT_DPI = 300  # higher than local (200) — cloud has no GPU bottleneck


def process_model_response(response, page_num):
    """Extract content from API response, clean it, prepend page comment."""
    if not response.choices:
        raise ValueError("Unexpected model response: 'choices' is empty.")

    message = response.choices[0].message
    if not (message and getattr(message, "content", None)):
        raise ValueError(f"Unexpected model response for page {page_num + 1}")

    cleaned = clean_markdown(message.content)
    return f"<!-- PDF page {page_num + 1} -->\n" + cleaned


def pdf_to_markdown(pdf_path, *, model="gpt-4o", dpi=DEFAULT_DPI, max_tokens=4096):
    """Convert a PDF to Markdown by sending each page image to a vision LLM."""
    from pdf2image import convert_from_path  # heavy dep, import lazily

    client = OpenAI()

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

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": USER_PROMPT.replace(
                            PREV_PAGE_PLACEHOLDER, previous_page_markdown, 1
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encoded_image}"
                        },
                    },
                ],
            },
        ]

        response = client.chat.completions.create(
            model=model, messages=messages, max_tokens=max_tokens
        )

        markdown_text = process_model_response(response, page_num)
        markdown_pieces.append(markdown_text)
        previous_page_markdown = markdown_text

        log.info("Page %d/%d done.", page_num + 1, len(images))

    return "\n".join(markdown_pieces)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Convert PDF to Markdown via OpenRouter vision LLM"
    )
    parser.add_argument("pdf", type=Path, help="Input PDF file")
    parser.add_argument("--output", "-o", type=Path, default=None,
                        help="Output .md path (default: same name as PDF)")
    parser.add_argument("--model", default="gpt-4o",
                        help="Vision model to use (default: gpt-4o)")
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI,
                        help=f"DPI for PDF rasterisation (default: {DEFAULT_DPI})")
    parser.add_argument("--max-tokens", type=int, default=4096,
                        help="Max output tokens per page (default: 4096)")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not args.pdf.exists():
        parser.error(f"File not found: {args.pdf}")
    if args.pdf.suffix.lower() != ".pdf":
        parser.error(f"Not a PDF: {args.pdf}")

    result = pdf_to_markdown(args.pdf, model=args.model, dpi=args.dpi,
                             max_tokens=args.max_tokens)

    output = get_output_path(args.pdf, args.output)
    actual_argv = sys.argv if argv is None else ["python", "-m", "aedist.pdf2md_openrouter"] + argv
    output.write_text(
        result + metadata_comment(args.pdf, backend="OpenRouter", model=args.model,
                                  argv=actual_argv),
        encoding="utf-8",
    )
    log.info("Wrote %s", output)


if __name__ == "__main__":
    main()
