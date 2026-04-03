"""Convert PDF pages to Markdown via vision LLM (OCR + structuring).

Ported from MinhHaDuong/aedist pdfOCR2md tool.
Minh Ha-Duong, CNRS, 2025–
License CC-BY-SA

Usage:
    python -m aedist.pdf2md input.pdf
    python -m aedist.pdf2md input.pdf --output output.md --model gpt-4o --dpi 300
"""

import argparse
import base64
import datetime
import logging
import platform
import re
import sys
import tempfile
from pathlib import Path

from openai import OpenAI

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an assistant that converts PDF page images to structured Markdown text.
Follow these rules:

Text Formatting:
- Fix any OCR errors
- Include all text except page numbers

Document Title and First Page:
- Use `#` for the document title only
- For Vietnamese administrative documents:
  * Print order of letterhead elements: country, tagline, ministry, reference number, place and date
  * Letterhead elements BEFORE the title.
  * The title block has a Type subblock and a Subject subblock
  * First line, in ALL CAPS, is the document type (BÁO CÁO, QUYẾT ĐỊNH, PHỤ LỤC, etc.)
  * After that, ALL centered lines is the document Subject subblock
  * The document Subject is NEVER empty
  * Title = DOCUMENT TYPE + <br> + document Subject
  * Title example 1: '#BÁO CÁO <br> Kế hoạch thực hiện Quy hoạch phát triển điện lực quốc gia thời kỳ 2021-2030, tầm nhìn đến năm 2050'
  * Title example 2 : '#QUYẾT ĐỊNH <br> Phê duyệt bổ sung, cập nhật Kế hoạch thực hiện Quy hoạch phát triển điện lực quốc gia thời kỳ 2021 - 2030, tầm nhìn đến năm 2050'
  * Title example 3: '#TỜ TRÌNH <br> Đề nghị ban hành bổ sung, cập nhật Kế hoạch thực hiện Quy hoạch phát triển điện lực quốc gia thời kỳ 2021-2030, tầm nhìn đến năm 2050'

Section Headers Throughout Document:
- Mark ALL section headers with `##`, `###` etc., even on the first page
- Section headers may appear anywhere, including first page after title
- Never skip marking a section header

Content Structure:
- Preserve document's logical hierarchy
- Keep all paragraphs, including those before section headers
- Use proper Markdown list formatting with one blank line between items
- Format footnotes as [^X] in text with corresponding [^X]: at bottom

Tables:
- Always use HTML table syntax (<table>, <tr>, <td>), never Markdown tables
- Preserve all table formatting, including merged cells and alignments
- For tables that appear to continue from previous page (no caption, partial content):
  * Insert <!-- TableContinues --> before the opening <table> tag
  * Maintain same column structure and alignment
  * Include table headers if present on the page
  * Omit <caption> tag since it's a continuation
- Keep all table section headings and subheadings within the table structure
"""

USER_PROMPT = """Here is the Markdown from the previous page (if empty, this is the first page):
{}

Now, convert the following base64-encoded page to Markdown, without adding explanations or comments.
Limit your response to the image content, without repeating the text above."""


def clean_markdown(raw_text):
    """Strip code fences, normalise table indentation, trim trailing whitespace."""
    text = re.sub(r"^```(?:markdown|html)?[ \t]*\n", "", raw_text)
    text = re.sub(r"\n```[ \t]*$", "", text)

    text = re.sub(r"^(\s*)<tr", r"  <tr", text, flags=re.MULTILINE)
    text = re.sub(r"^(\s*)<td", r"    <td", text, flags=re.MULTILINE)
    text = re.sub(r"^(\s*)<th", r"    <th", text, flags=re.MULTILINE)

    text = "\n".join(line.rstrip() for line in text.splitlines())
    return text


def process_model_response(response, page_num):
    """Extract content from API response, clean it, prepend page comment."""
    if not response.choices:
        raise ValueError("Unexpected model response: 'choices' is empty.")

    message = response.choices[0].message
    if not (message and hasattr(message, "content")):
        raise ValueError(f"Unexpected model response for page {page_num + 1}")

    cleaned = clean_markdown(message.content)
    return f"<!-- PDF page {page_num + 1} -->\n" + cleaned


def get_output_path(pdf_path, output_arg):
    """Determine output path: explicit arg > stem.md > stem_converted.md."""
    if output_arg:
        return Path(output_arg)
    candidate = pdf_path.with_suffix(".md")
    if candidate.exists():
        return pdf_path.with_name(pdf_path.stem + "_converted.md")
    return candidate


def metadata_comment(pdf_path, model, argv):
    """Conversion metadata appended as HTML comment."""
    return (
        f"\n\n<!-- Converted from PDF using:\n"
        f"Command: python {' '.join(argv)}\n"
        f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Source: {pdf_path.name}\n"
        f"Platform: {platform.platform()}\n"
        f"Python: {platform.python_version()}\n"
        f"Model: {model}\n"
        f"-->"
    )


def pdf_to_markdown(pdf_path, *, model, dpi, max_tokens):
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
                        "text": USER_PROMPT.format(previous_page_markdown),
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


def main():
    parser = argparse.ArgumentParser(
        description="Convert PDF to Markdown via vision LLM"
    )
    parser.add_argument("pdf", type=Path, help="Input PDF file")
    parser.add_argument("--output", "-o", type=Path, default=None,
                        help="Output .md path (default: same name as PDF)")
    parser.add_argument("--model", default="gpt-4o",
                        help="Vision model to use (default: gpt-4o)")
    parser.add_argument("--dpi", type=int, default=300,
                        help="DPI for PDF rasterisation (default: 300)")
    parser.add_argument("--max-tokens", type=int, default=4096,
                        help="Max output tokens per page (default: 4096)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not args.pdf.exists():
        parser.error(f"File not found: {args.pdf}")
    if args.pdf.suffix.lower() != ".pdf":
        parser.error(f"Not a PDF: {args.pdf}")

    result = pdf_to_markdown(args.pdf, model=args.model, dpi=args.dpi,
                             max_tokens=args.max_tokens)

    output = get_output_path(args.pdf, args.output)
    output.write_text(result + metadata_comment(args.pdf, args.model, sys.argv),
                      encoding="utf-8")
    log.info("Wrote %s", output)


if __name__ == "__main__":
    main()
