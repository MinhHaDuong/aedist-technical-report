"""Shared utilities for PDF-to-Markdown converters.

Contains prompts, cleaning, output path logic, and metadata used by all
three converter backends (grobid, ollama, openrouter).
"""

import platform
import re
from datetime import UTC, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

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

PREV_PAGE_PLACEHOLDER = "<<PREVIOUS_PAGE>>"

USER_PROMPT = f"""Here is the Markdown from the previous page (if empty, this is the first page):
{PREV_PAGE_PLACEHOLDER}

Now, convert the following base64-encoded page to Markdown, without adding explanations or comments.
Limit your response to the image content, without repeating the text above."""


# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------

def clean_markdown(raw_text):
    """Strip code fences, normalise table indentation, trim trailing whitespace."""
    text = re.sub(r"^```(?:markdown|html)?[ \t]*\n", "", raw_text)
    text = re.sub(r"\n```[ \t]*$", "", text)

    text = re.sub(r"^\s*<tr", r"  <tr", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*<td", r"    <td", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*<th", r"    <th", text, flags=re.MULTILINE)

    text = "\n".join(line.rstrip() for line in text.splitlines())
    return text


# ---------------------------------------------------------------------------
# Output path
# ---------------------------------------------------------------------------

def get_output_path(pdf_path, output_arg):
    """Determine output path: explicit arg > stem.md > stem_converted.md."""
    if output_arg:
        return Path(output_arg)
    candidate = pdf_path.with_suffix(".md")
    if candidate.exists():
        return pdf_path.with_name(pdf_path.stem + "_converted.md")
    return candidate


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

def metadata_comment(pdf_path, *, backend, model, argv):
    """Conversion metadata appended as HTML comment.

    All three converters use this same function and format.
    """
    return (
        f"\n\n<!-- Converted from PDF using:\n"
        f"Command: python {' '.join(argv)}\n"
        f"Date: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        f"Source: {pdf_path.name}\n"
        f"Platform: {platform.platform()}\n"
        f"Python: {platform.python_version()}\n"
        f"Backend: {backend}\n"
        f"Model: {model}\n"
        f"-->"
    )
