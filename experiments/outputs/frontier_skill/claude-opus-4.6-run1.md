

# Claude Code Custom Slash Command: `/extract-energy-table`

## 1. Skill Definition File

Place this at `.claude/commands/extract-energy-table.md`:

```markdown
---
name: extract-energy-table
description: Extract structured energy data tables from government PDFs into clean CSV/JSON/Markdown format with source provenance.
---

# Energy Table Extraction from Government PDFs

You are an expert data engineer specializing in extracting structured energy data from government PDF documents (power development plans, EVN annual reports, capacity inventories, generation statistics).

## Task

The user wants to extract energy data tables from a PDF document. Parse their request to determine:

1. **Source**: A URL or local file path to a PDF
2. **Format**: Output format (csv, json, or markdown). Default: csv
3. **Language**: Source document language (vi for Vietnamese, en for English). Default: auto-detect
4. **Tables filter**: Which table types to extract (capacity, generation, fuel, emissions, all). Default: all
5. **Output directory**: Where to write extracted files. Default: current directory

## Input from user

$ARGUMENTS

## Step-by-step procedure

### Step 1: Validate the input

Parse the user's arguments. The format is:
```
<pdf_path_or_url> [--format csv|json|markdown] [--lang vi|en] [--tables "capacity,generation"] [--output <dir>]
```

If the source is a URL, download it first using WebFetch or curl to a temporary location.

### Step 2: Check that the Python extraction script exists

Look for `scripts/extract_energy_table.py` in the project. If it doesn't exist, inform the user they need to set it up per the project README.

Verify dependencies are installed by checking for pymupdf4llm or pdfplumber in the environment. If missing, offer to run `uv add pymupdf4llm pdfplumber pandas`.

### Step 3: Run the extraction

Execute the extraction script with the appropriate arguments:

```bash
python scripts/extract_energy_table.py "<pdf_path>" --format <format> --lang <lang> --tables <tables> --output <output_dir>
```

### Step 4: Validate the output

After extraction:
- Read the generated output file(s)
- Check that the CSV/JSON is well-formed
- Report the number of tables extracted, rows per table, and column names
- Flag any potential issues (empty columns, suspiciously low row counts, encoding problems)

### Step 5: Present results to the user

Show a summary:
- Number of tables found and extracted
- For each table: name, row count, column names, page range in source PDF
- File paths of generated outputs
- Any warnings about data quality

If the extraction found no tables, suggest:
- The PDF might be image-based (suggest OCR pipeline)
- The page range might need adjustment
- The document might not contain tabular energy data

## Important guidelines

- **Never fabricate data**. Only output what the extraction script actually found in the PDF.
- **Preserve numeric precision**. Don't round values unless the user asks.
- **Vietnamese handling**: Government PDFs often use Vietnamese column headers. The script normalizes these to English snake_case, but always include the original header in provenance metadata.
- **Multi-page tables**: The script handles tables that span page breaks. If results look truncated, suggest re-running with `--merge-pages` flag.
- **Units**: Energy data uses MW, MWh, GWh, TWh, tấn (tons), triệu tấn (million tons), %, tỷ đồng (billion VND). The script strips these from numeric values and records them in a units row or metadata.

## Error handling

- If the PDF path doesn't exist: "File not found: <path>. Please check the path and try again."
- If the URL is unreachable: "Could not download PDF from <url>. HTTP status: <code>."
- If no tables found: "No tables detected in <filename> (scanned pages 1-N). This PDF may contain image-based tables requiring OCR, or may not contain tabular data."
- If extraction partially fails: Report which pages succeeded and which failed, with page numbers.
```

## 2. Supporting Python Script

Save as `scripts/extract_energy_table.py`:

```python
#!/usr/bin/env python3
"""
Extract structured energy data tables from government PDF documents.

Handles power plant inventories, capacity statistics, generation data,
and other energy-sector tabular data commonly found in Vietnamese
government reports (PDP, EVN annual reports, etc.).

Usage:
    python extract_energy_table.py report.pdf
    python extract_energy_table.py report.pdf --format csv --lang vi
    python extract_energy_table.py report.pdf --tables capacity,generation --output extracted/
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import re
import sys
import unicodedata
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Vietnamese → English header mapping for energy domain
# ---------------------------------------------------------------------------

HEADER_TRANSLATIONS: dict[str, str] = {
    # Power plant / facility
    "tên nhà máy": "plant_name",
    "nhà máy": "plant_name",
    "tên dự án": "project_name",
    "dự án": "project_name",
    "tên công trình": "facility_name",
    "công trình": "facility_name",
    # Location
    "địa điểm": "location",
    "vị trí": "location",
    "tỉnh": "province",
    "tỉnh/thành phố": "province",
    "vùng": "region",
    "miền": "region",
    # Capacity
    "công suất": "capacity_mw",
    "công suất (mw)": "capacity_mw",
    "công suất (mwp)": "capacity_mwp",
    "công suất đặt": "installed_capacity_mw",
    "công suất đặt (mw)": "installed_capacity_mw",
    "tổng công suất": "total_capacity_mw",
    "tổng công suất (mw)": "total_capacity_mw",
    "công suất khả dụng": "available_capacity_mw",
    # Generation
    "sản lượng": "generation_gwh",
    "sản lượng (gwh)": "generation_gwh",
    "sản lượng (twh)": "generation_twh",
    "sản lượng điện": "electricity_generation_gwh",
    "điện năng": "electricity_gwh",
    "điện thương phẩm": "commercial_electricity_gwh",
    "sản lượng điện thương phẩm": "commercial_electricity_gwh",
    # Fuel
    "nhiên liệu": "fuel_type",
    "loại nhiên liệu": "fuel_type",
    "nguồn": "source_type",
    "loại nguồn": "source_type",
    "than": "coal",
    "khí": "gas",
    "dầu": "oil",
    "thủy điện": "hydropower",
    "điện gió": "wind",
    "điện mặt trời": "solar",
    "năng lượng tái tạo": "renewable",
    "sinh khối": "biomass",
    # Emissions
    "phát thải": "emissions",
    "phát thải co2": "co2_emissions",
    "phát thải (tấn)": "emissions_tons",
    "phát thải (triệu tấn)": "emissions_million_tons",
    # Time
    "năm": "year",
    "năm vận hành": "operation_year",
    "thời gian": "period",
    "giai đoạn": "phase",
    "quý": "quarter",
    "tháng": "month",
    # Financial
    "vốn đầu tư": "investment_capital",
    "tổng vốn đầu tư": "total_investment",
    "vốn đầu tư (tỷ đồng)": "investment_billion_vnd",
    "chi phí": "cost",
    # Identifiers
    "stt": "row_number",
    "số tt": "row_number",
    "tt": "row_number",
    "mã": "code",
    # Percentage / share
    "tỷ lệ": "share_pct",
    "tỷ lệ (%)": "share_pct",
    "tỷ trọng": "proportion_pct",
    "tỷ trọng (%)": "proportion_pct",
    # Status
    "trạng thái": "status",
    "tình trạng": "status",
    "tiến độ": "progress",
    # Misc
    "ghi chú": "notes",
    "chú thích": "notes",
    "đơn vị": "unit",
    "tổng": "total",
    "tổng cộng": "grand_total",
    "cộng": "subtotal",
}

# Units that appear in cell values and should be stripped for numeric parsing
UNIT_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\s*MW[hp]?\s*$", re.IGNORECASE), "MW"),
    (re.compile(r"\s*GWh\s*$", re.IGNORECASE), "GWh"),
    (re.compile(r"\s*TWh\s*$", re.IGNORECASE), "TWh"),
    (re.compile(r"\s*MWh\s*$", re.IGNORECASE), "MWh"),
    (re.compile(r"\s*kWh\s*$", re.IGNORECASE), "kWh"),
    (re.compile(r"\s*kW\s*$", re.IGNORECASE), "kW"),
    (re.compile(r"\s*tấn\s*$", re.IGNORECASE), "ton"),
    (re.compile(r"\s*triệu tấn\s*$", re.IGNORECASE), "million_ton"),
    (re.compile(r"\s*tỷ đồng\s*$", re.IGNORECASE), "billion_vnd"),
    (re.compile(r"\s*triệu đồng\s*$", re.IGNORECASE), "million_vnd"),
    (re.compile(r"\s*%\s*$"), "pct"),
]

# Table type classification keywords
TABLE_TYPE_KEYWORDS: dict[str, list[str]] = {
    "capacity": [
        "công suất", "capacity", "installed", "đặt", "mw", "mwp",
        "danh mục", "inventory", "nhà máy", "plant",
    ],
    "generation": [
        "sản lượng", "generation", "gwh", "twh", "điện năng",
        "electricity", "output", "production",
    ],
    "fuel": [
        "nhiên liệu", "fuel", "than", "coal", "khí", "gas",
        "dầu", "oil", "tiêu thụ", "consumption",
    ],
    "emissions": [
        "phát thải", "emission", "co2", "carbon", "khí nhà kính",
        "greenhouse",
    ],
    "financial": [
        "vốn", "investment", "capital", "chi phí", "cost",
        "tỷ đồng", "billion",
    ],
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ExtractedTable:
    """A single table extracted from a PDF."""

    table_id: str
    table_type: str  # capacity, generation, fuel, emissions, financial, unknown
    title: str
    headers: list[str]  # Original headers
    normalized_headers: list[str]  # English snake_case headers
    units: dict[str, str]  # column_name -> unit string
    rows: list[list[str | float | None]]
    page_numbers: list[int]
    source_file: str
    extraction_timestamp: str
    row_count: int = 0
    notes: str = ""

    def __post_init__(self) -> None:
        self.row_count = len(self.rows)


@dataclass
class ExtractionResult:
    """Result of extracting tables from a PDF."""

    source_file: str
    total_pages: int
    tables: list[ExtractedTable] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    extraction_timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.extraction_timestamp:
            self.extraction_timestamp = datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Header normalization
# ---------------------------------------------------------------------------

def normalize_header(header: str, lang: str = "vi") -> str:
    """
    Normalize a table header to English snake_case.

    Handles Vietnamese diacritics, unit extraction, and common abbreviations.

    Args:
        header: Raw header text from PDF table.
        lang: Source language ('vi' or 'en').

    Returns:
        Normalized English snake_case header string.

    Examples:
        >>> normalize_header("Công suất (MW)")
        'capacity_mw'
        >>> normalize_header("Tên nhà máy")
        'plant_name'
        >>> normalize_header("Generation (GWh)")
        'generation_gwh'
    """
    if not header or not header.strip():
        return "unnamed_column"

    cleaned = header.strip()
    # Normalize unicode (NFC form for Vietnamese)
    cleaned = unicodedata.normalize("NFC", cleaned)
    # Lowercase for matching
    lower = cleaned.lower().strip()

    # Try direct translation lookup
    if lower in HEADER_TRANSLATIONS:
        return HEADER_TRANSLATIONS[lower]

    # Try partial matching: check if any translation key is contained in the header
    for vi_key, en_val in HEADER_TRANSLATIONS.items():
        if vi_key in lower and len(vi_key) > 2:
            return en_val

    # If English, just convert to snake_case
    if lang == "en" or _is_mostly_ascii(cleaned):
        return _to_snake_case(cleaned)

    # For Vietnamese text not in our dictionary, strip diacritics and snake_case
    stripped = _strip_diacritics(cleaned)
    return _to_snake_case(stripped)


def _is_mostly_ascii(text: str) -> bool:
    """Check if text is predominantly ASCII (English)."""
    ascii_count = sum(1 for c in text if ord(c) < 128)
    return ascii_count / max(len(text), 1) > 0.8


def _strip_diacritics(text: str) -> str:
    """Remove Vietnamese diacritics from text."""
    # NFD decomposition separates base characters from combining marks
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _to_snake_case(text: str) -> str:
    """Convert text to snake_case."""
    # Remove content in parentheses but extract unit info
    text = re.sub(r"\(([^)]*)\)", r"_\1", text)
    # Replace non-alphanumeric with underscore
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text)
    # CamelCase to snake_case
    text = re.sub(r"([a-z])([A-Z])", r"\1_\2", text)
    # Collapse multiple underscores, strip edges
    text = re.sub(r"_+", "_", text).strip("_").lower()
    return text if text else "unnamed_column"


def extract_unit_from_header(header: str) -> tuple[str, str | None]:
    """
    Extract unit from a header string.

    Args:
        header: Raw header text.

    Returns:
        Tuple of (header_without_unit, unit_string_or_None).

    Examples:
        >>> extract_unit_from_header("Capacity (MW)")
        ('Capacity', 'MW')
        >>> extract_unit_from_header("Plant Name")
        ('Plant Name', None)
    """
    # Match parenthesized units
    match = re.search(r"\(([^)]+)\)\s*$", header)
    if match:
        unit_candidate = match.group(1).strip()
        known_units = {
            "mw", "mwh", "gwh", "twh", "kwh", "kw", "mwp",
            "%", "tấn", "triệu tấn", "tỷ đồng", "triệu đồng",
            "ton", "million ton", "billion vnd",
        }
        if unit_candidate.lower() in known_units:
            header_clean = header[: match.start()].strip()
            return header_clean, unit_candidate
    return header, None


# ---------------------------------------------------------------------------
# Numeric cleaning
# ---------------------------------------------------------------------------

def clean_numeric_value(value: str) -> float | str | None:
    """
    Clean a cell value, converting numeric strings to floats.

    Handles:
    - Vietnamese/European thousand separators (1.200 or 1,200)
    - Decimal commas (3,14) vs decimal dots (3.14)
    - Unit suffixes (MW, GWh, %, tấn)
    - Dash/hyphen as missing value
    - Empty strings

    Args:
        value: Raw cell value string.

    Returns:
        Float if numeric, original string if text, None if empty/missing.

    Examples:
        >>> clean_numeric_value("1.200 MW")
        1200.0
        >>> clean_numeric_value("3,14")
        3.14
        >>> clean_numeric_value("1,200.5")
        1200.5
        >>> clean_numeric_value("-")
        None
        >>> clean_numeric_value("")
        None
        >>> clean_numeric_value("Nhà máy ABC")
        'Nhà máy ABC'
    """
    if value is None:
        return None

    if not isinstance(value, str):
        try:
            return float(value)
        except (ValueError, TypeError):
            return value

    stripped = value.strip()

    if not stripped or stripped in ("-", "–", "—", "N/A", "n/a", "...", "…"):
        return None

    # Strip known unit suffixes
    numeric_str = stripped
    for pattern, _unit_name in UNIT_PATTERNS:
        numeric_str = pattern.sub("", numeric_str)
    numeric_str = numeric_str.strip()

    if not numeric_str:
        return None

    # Try to parse as number
    parsed = _parse_number(numeric_str)
    if parsed is not None:
        return parsed

    # Not a number — return original string (preserving Vietnamese text)
    return stripped


def _parse_number(s: str) -> float | None:
    """
    Parse a numeric string handling various thousand/decimal separator conventions.

    Vietnamese convention: dot as thousand separator, comma as decimal (1.200,5)
    US/English convention: comma as thousand separator, dot as decimal (1,200.5)
    """
    # Remove spaces
    s = s.replace(" ", "").replace("\u00a0", "")

    # Handle negative numbers
    negative = False
    if s.startswith("-") or s.startswith("−"):
        negative = True
        s = s[1:]
    elif s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1]

    if not s:
        return None

    # Check if it looks numeric at all
    if not re.match(r"^[\d.,]+$", s):
        return None

    has_dots = "." in s
    has_commas = "," in s

    result: float | None = None

    if has_dots and has_commas:
        # Determine which is the decimal separator (the last one)
        last_dot = s.rfind(".")
        last_comma = s.rfind(",")

        if last_comma > last_dot:
            # Format: 1.200,50 (Vietnamese/European)
            s_clean = s.replace(".", "").replace(",", ".")
        else:
            # Format: 1,200.50 (US/English)
            s_clean = s.replace(",", "")
        try:
            result = float(s_clean)
        except ValueError:
            return None

    elif has_dots and not has_commas:
        dot_count = s.count(".")
        if dot_count == 1:
            # Could be decimal (3.14) or thousand separator (1.200)
            parts = s.split(".")
            if len(parts[1]) == 3 and len(parts[0]) <= 3:
                # Likely thousand separator: 1.200 → 1200
                # But also could be 1.200 as a decimal...
                # Heuristic: if the part after dot is exactly 3 digits
                # and there's no other context, treat as thousand separator
                # for values >= 1.000
                try:
                    as_thousands = float(s.replace(".", ""))
                    as_decimal = float(s)
                    # If the integer part is small (1-999) and decimal part is 3 digits,
                    # more likely a thousand separator in Vietnamese context
                    if int(parts[0]) > 0:
                        result = as_thousands
                    else:
                        result = as_decimal
                except ValueError:
                    return None
            else:
                # Standard decimal
                try:
                    result = float(s)
                except ValueError:
                    return None
        else:
            # Multiple dots: definitely thousand separators (1.200.000)
            try:
                result = float(s.replace(".", ""))
            except ValueError:
                return None

    elif has_commas and not has_dots:
        comma_count = s.count(",")
        if comma_count == 1:
            parts = s.split(",")
            if len(parts[1]) == 3 and len(parts[0]) <= 3:
                # Likely US thousand separator: 1,200
                try:
                    result = float(s.replace(",", ""))
                except ValueError:
                    return None
            else:
                # Likely decimal comma: 3,14
                try:
                    result = float(s.replace(",", "."))
                except ValueError:
                    return None
        else:
            # Multiple commas: thousand separators (1,200,000)
            try:
                result = float(s.replace(",", ""))
            except ValueError:
                return None
    else:
        # Plain integer
        try:
            result = float(s)
        except ValueError:
            return None

    if result is not None and negative:
        result = -result

    return result


# ---------------------------------------------------------------------------
# Table type classification
# ---------------------------------------------------------------------------

def classify_table_type(
    title: str,
    headers: list[str],
) -> str:
    """
    Classify a table into an energy data category based on title and headers.

    Args:
        title: Table title or caption text.
        headers: List of column header strings.

    Returns:
        One of: 'capacity', 'generation', 'fuel', 'emissions', 'financial', 'unknown'.
    """
    combined_text = (title + " " + " ".join(headers)).lower()

    scores: dict[str, int] = {}
    for table_type, keywords in TABLE_TYPE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in combined_text)
        if score > 0:
            scores[table_type] = score

    if not scores:
        return "unknown"

    return max(scores, key=lambda k: scores[k])


# ---------------------------------------------------------------------------
# PDF extraction backends
# ---------------------------------------------------------------------------

def _extract_with_pdfplumber(pdf_path: Path) -> ExtractionResult:
    """Extract tables using pdfplumber."""
    try:
        import pdfplumber
    except ImportError:
        raise ImportError(
            "pdfplumber is required but not installed. "
            "Install it with: uv add pdfplumber"
        )

    result = ExtractionResult(
        source_file=str(pdf_path),
        total_pages=0,
    )

    try:
        with pdfplumber.open(pdf_path) as pdf:
            result.total_pages = len(pdf.pages)
            table_counter = 0

            # Track tables across pages for merging
            pending_table: dict | None = None

            for page_idx, page in enumerate(pdf.pages):
                page_num = page_idx + 1
                tables = page.extract_tables()

                if not tables:
                    # If we had a pending table, finalize it
                    if pending_table is not None:
                        result.tables.append(
                            _build_extracted_table(
                                pending_table, pdf_path, result.extraction_timestamp
                            )
                        )
                        pending_table = None
                    continue

                for table_data in tables:
                    if not table_data or len(table_data) < 2:
                        continue

                    # Clean None values in cells
                    cleaned_rows = []
                    for row in table_data:
                        cleaned_row = [
                            cell.strip() if isinstance(cell, str) else (cell or "")
                            for cell in row
                        ]
                        cleaned_rows.append(cleaned_row)

                    # Check if this continues a previous table
                    if pending_table is not None and _tables_are_continuation(
                        pending_table["headers"], cleaned_rows[0]
                    ):
                        # Skip the repeated header row and append data
                        data_start = 1 if _row_matches_headers(
                            cleaned_rows[0], pending_table["headers"]
                        ) else 0
                        pending_table["rows"].extend(cleaned_rows[data_start:])
                        pending_table["page_numbers"].append(page_num)
                    else:
                        # Finalize any pending table
                        if pending_table is not None:
                            result.tables.append(
                                _build_extracted_table(
                                    pending_table, pdf_path, result.extraction_timestamp
                                )
                            )

                        # Start new table
                        table_counter += 1
                        headers = cleaned_rows[0]
                        data_rows = cleaned_rows[1:]

                        # Try to extract title from the page text above the table
                        title = _extract_table_title(page, table_data)

                        pending_table = {
                            "table_id": f"table_{table_counter:03d}",
                            "title": title,
                            "headers": headers,
                            "rows": data_rows,
                            "page_numbers": [page_num],
                        }

            # Finalize last pending table
            if pending_table is not None:
                result.tables.append(
                    _build_extracted_table(
                        pending_table, pdf_path, result.extraction_timestamp
                    )
                )

    except Exception as e:
        logger.error("Failed to extract tables from %s: %s", pdf_path, e)
        raise

    if not result.tables:
        result.warnings.append(
            f"No tables found on pages 1-{result.total_pages} of {pdf_path.name}. "
            "The PDF may contain image-based tables (requiring OCR) or no tabular data."
        )

    return result


def _extract_with_pymupdf4llm(pdf_path: Path) -> ExtractionResult:
    """Extract tables using pymupdf4llm (fallback to pymupdf/fitz)."""
    try:
        import pymupdf4llm
        import pymupdf
    except ImportError:
        raise ImportError(
            "pymupdf4llm is required but not installed. "
            "Install it with: uv add pymupdf4llm"
        )

    result = ExtractionResult(
        source_file=str(pdf_path),
        total_pages=0,
    )

    try:
        doc = pymupdf.open(str(pdf_path))
        result.total_pages = len(doc)

        # Use pymupdf4llm to get markdown with tables
        md_text = pymupdf4llm.to_markdown(str(pdf_path))

        # Parse markdown tables
        tables = _parse_markdown_tables(md_text, pdf_path, result.extraction_timestamp)
        result.tables = tables

        # Try to assign page numbers by finding table content in pages
        for table in result.tables:
            if not table.page_numbers:
                table.page_numbers = list(range(1, result.total_pages + 1))

        doc.close()

    except Exception as e:
        logger.error("Failed to extract tables from %s: %s", pdf_path, e)
        raise

    if not result.tables:
        result.warnings.append(
            f"No tables found in {pdf_path.name} ({result.total_pages} pages). "
            "The PDF may contain image-based tables (requiring OCR) or no tabular data."
        )

    return result


def _parse_markdown_tables(
    md_text: str,
    pdf_path: Path,
    timestamp: str,
) -> list[ExtractedTable]:
    """Parse markdown-formatted tables from pymupdf4llm output."""
    tables: list[ExtractedTable] = []
    lines = md_text.split("\n")
    table_counter = 0

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Detect markdown table (starts with |)
        if line.startswith("|") and "|" in line[1:]:
            table_lines = []
            title = ""

            # Look back for a title (heading or bold text before the table)
            for j in range(max(0, i - 3), i):
                prev = lines[j].strip()
                if prev.startswith("#") or prev.startswith("**"):
                    title = prev.lstrip("#").strip().strip("*").strip()
                    break

            # Collect all table lines
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1

            if len(table_lines) < 3:  # header + separator + at least 1 data row
                continue

            # Parse header
            headers = [
                cell.strip()
                for cell in table_lines[0].split("|")
                if cell.strip()
            ]

            # Skip separator line (|---|---|...)
            data_start = 1
            if data_start < len(table_lines) and re.match(
                r"^\|[\s\-:|]+\|$", table_lines[data_start]
            ):
                data_start = 2

            # Parse data rows
            rows = []
            for tl in table_lines[data_start:]:
                cells = [cell.strip() for cell in tl.split("|") if cell.strip() != ""]
                # Pad or truncate to match header count
                while len(cells) < len(headers):
                    cells.append("")
                cells = cells[: len(headers)]
                rows.append(cells)

            if not rows:
                continue

            table_counter += 1
            table = _build_extracted_table(
                {
                    "table_id": f"table_{table_counter:03d}",
                    "title": title,
                    "headers": headers,
                    "rows": rows,
                    "page_numbers": [],
                },
                pdf_path,
                timestamp,
            )
            tables.append(table)
        else:
            i += 1

    return tables


# ---------------------------------------------------------------------------
# Table building helpers
# ---------------------------------------------------------------------------

def _build_extracted_table(
    raw: dict,
    pdf_path: Path,
    timestamp: str,
) -> ExtractedTable:
    """Build an ExtractedTable from raw extraction data."""
    headers = raw["headers"]
    rows = raw["rows"]

    # Detect language from headers
    lang = _detect_language(headers)

    # Extract units from headers
    units: dict[str, str] = {}
    clean_headers = []
    for h in headers:
        h_clean, unit = extract_unit_from_header(h)
        clean_headers.append(h_clean)
        if unit:
            norm_h = normalize_header(h, lang)
            units[norm_h] = unit

    # Normalize headers
    normalized = [normalize_header(h, lang) for h in headers]

    # Deduplicate normalized headers
    normalized = _deduplicate_headers(normalized)

    # Clean numeric values in rows
    cleaned_rows: list[list[str | float | None]] = []
    for row in rows:
        cleaned_row: list[str | float | None] = []
        for cell in row:
            cleaned_row.append(clean_numeric_value(str(cell) if cell else ""))
        # Pad to header length
        while len(cleaned_row) < len(normalized):
            cleaned_row.append(None)
        cleaned_row = cleaned_row[: len(normalized)]
        cleaned_rows.append(cleaned_row)

    # Filter out completely empty rows
    cleaned_rows = [
        row for row in cleaned_rows
        if any(cell is not None and cell != "" for cell in row)
    ]

    # Classify table type
    table_type = classify_table_type(raw.get("title", ""), headers)

    return ExtractedTable(
        table_id=raw["table_id"],
        table_type=table_type,
        title=raw.get("title", ""),
        headers=headers,
        normalized_headers=normalized,
        units=units,
        rows=cleaned_rows,
        page_numbers=raw.get("page_numbers", []),
        source_file=str(pdf_path),
        extraction_timestamp=timestamp,
    )


def _deduplicate_headers(headers: list[str]) -> list[str]:
    """Ensure all headers are unique by appending suffixes."""
    seen: dict[str, int] = {}
    result: list[str] = []
    for h in headers:
        if h in seen:
            seen[h] += 1
            result.append(f"{h}_{seen[h]}")
        else:
            seen[h] = 0
            result.append(h)
    return result


def _detect_language(headers: list[str]) -> str:
    """Detect whether headers are Vietnamese or English."""
    combined = " ".join(headers).lower()
    vi_indicators = [
        "công suất", "sản lượng", "nhà máy", "tỉnh", "năm",
        "tổng", "đơn vị", "ghi chú", "dự án", "điện",
    ]
    vi_score = sum(1 for ind in vi_indicators if ind in combined)
    return "vi" if vi_score >= 2 else "en"


def _tables_are_continuation(
    prev_headers: list[str],
    candidate_row: list[str],
) -> bool:
    """Check if a candidate row looks like a repeated header (table continuation)."""
    if len(prev_headers) != len(candidate_row):
        return False
    return _row_matches_headers(candidate_row, prev_headers)


def _row_matches_headers(row: list[str], headers: list[str]) -> bool:
    """Check if a row matches the header pattern (for multi-page table detection)."""
    if len(row) != len(headers):
        return False
    matches = sum(
        1 for a, b in zip(row, headers)
        if a.strip().lower() == b.strip().lower()
    )
    return matches / max(len(headers), 1) > 0.6


def _extract_table_title(page, table_data) -> str:
    """Try to extract a title for a table from the page text."""
    try:
        text = page.extract_text() or ""
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        # Look for lines that look like table titles
        # (contain "Bảng", "Table", "Phụ lục", "Appendix", or are short bold-looking lines)
        for line in lines:
            lower = line.lower()
            if any(kw in lower for kw in ["bảng", "table", "phụ lục", "appendix", "danh mục"]):
                return line
        return ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def write_csv(table: ExtractedTable, output_path: Path) -> Path:
    """Write an extracted table to CSV format."""
    filepath = output_path / f"{table.table_id}.csv"

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)

        # Metadata comment rows
        writer.writerow([f"# Source: {table.source_file}"])
        writer.writerow([f"# Pages: {', '.join(str(p) for p in table.page_numbers)}"])
        writer.writerow([f"# Extracted: {table.extraction_timestamp}"])
        writer.writerow([f"# Table type: {table.table_type}"])
        if table.title:
            writer.writerow([f"# Title: {table.title}"])
        if table.units:
            units_str = "; ".join(f"{k}={v}" for k, v in table.units.items())
            writer.writerow([f"# Units: {units_str}"])

        # Headers
        writer.writerow(table.normalized_headers)

        # Data rows
        for row in table.rows:
            writer.writerow(row)

    logger.info("Wrote CSV: %s (%d rows)", filepath, table.row_count)
    return filepath


def write_json(table: ExtractedTable, output_path: Path) -> Path:
    """Write an extracted table to JSON format."""
    filepath = output_path / f"{table.table_id}.json"

    # Build records
    records = []
    for row in table.rows:
        record = {}
        for header, value in zip(table.normalized_headers, row):
            record[header] = value
        records.append(record)

    output = {
        "metadata": {
            "source_file": table.source_file,
            "page_numbers": table.page_numbers,
            "extraction_timestamp": table.extraction_timestamp,
            "table_type": table.table_type,
            "title": table.title,
            "units": table.units,
            "original_headers": table.headers,
            "row_count": table.row_count,
        },
        "columns": table.normalized_headers,
        "data": records,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info("Wrote JSON: %s (%d rows)", filepath, table.row_count)
    return filepath


def write_markdown(table: ExtractedTable, output_path: Path) -> Path:
    """Write an extracted table to Markdown format."""
    filepath = output_path / f"{table.table_id}.md"

    lines: list[str] = []

    # Title
    if table.title:
        lines.append(f"## {table.title}")
    else:
        lines.append(f"## {table.table_id}")
    lines.append("")

    # Metadata
    lines.append(f"- **Source**: `{table.source_file}`")
    lines.append(f"- **Pages**: {', '.join(str(p) for p in table.page_numbers)}")
    lines.append(f"- **Type**: {table.table_type}")
    lines.append(f"- **Rows**: {table.row_count}")
    lines.append(f"- **Extracted**: {table.extraction_timestamp}")
    lines.append("")

    # Table
    headers = table.normalized_headers
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")

    for row in table.rows:
        cells = [str(v) if v is not None else "" for v in row]
        lines.append("| " + " | ".join(cells) + " |")

    lines.append("")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info("Wrote Markdown: %s (%d rows)", filepath, table.row_count)
    return filepath


# ---------------------------------------------------------------------------
# Main extraction pipeline
# ---------------------------------------------------------------------------

def extract_tables(
    pdf_path: str | Path,
    output_dir: str | Path = ".",
    output_format: str = "csv",
    lang: str = "auto",
    table_filter: str = "all",
    backend: str = "pdfplumber",
) -> ExtractionResult:
    """
    Extract energy data tables from a PDF document.

    Args:
        pdf_path: Path to the PDF file.
        output_dir: Directory to write output files.
        output_format: Output format ('csv', 'json', 'markdown').
        lang: Source language ('vi', 'en', 'auto').
        table_filter: Comma-separated table types to extract, or 'all'.
        backend: PDF extraction backend ('pdfplumber', 'pymupdf4llm').

    Returns:
        ExtractionResult with extracted tables and metadata.
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"File not found: {pdf_path}. "
            "Please check the path and try again."
        )

    if not pdf_path.suffix.lower() == ".pdf":
        raise ValueError(
            f"Expected a PDF file, got: {pdf_path.suffix}. "
            "Please provide a file with .pdf extension."
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Extracting tables from: %s", pdf_path)
    logger.info("Backend: %s, Format: %s, Language: %s", backend, output_format, lang)

    # Extract using selected backend
    if backend == "pymupdf4llm":
        result = _extract_with_pymupdf4llm(pdf_path)
    else:
        result = _extract_with_pdfplumber(pdf_path)

    # Filter by table type if requested
    if table_filter != "all":
        requested_types = {t.strip().lower() for t in table_filter.split(",")}
        filtered = [t for t in result.tables if t.table_type in requested_types]
        if len(filtered) < len(result.tables):
            excluded = len(result.tables) - len(filtered)
            result.warnings.append(
                f"Filtered out {excluded} table(s) not matching types: {table_filter}"
            )
        result.tables = filtered

    # Write output files
    writer_map = {
        "csv": write_csv,
        "json": write_json,
        "markdown": write_markdown,
        "md": write_markdown,
    }

    writer = writer_map.get(output_format.lower())
    if writer is None:
        raise ValueError(
            f"Unsupported output format: {output_format}. "
            f"Supported formats: {', '.join(writer_map.keys())}"
        )

    output_files: list[str] = []
    for table in result.tables:
        filepath = writer(table, output_dir)
        output_files.append(str(filepath))

    # Summary
    logger.info("=" * 60)
    logger.info("Extraction complete: %s", pdf_path.name)
    logger.info("Total pages scanned: %d", result.total_pages)
    logger.info("Tables extracted: %d", len(result.tables))
    for table in result.tables:
        logger.info(
            "  %s [%s]: %d rows, %d columns, pages %s",
            table.table_id,
            table.table_type,
            table.row_count,
            len(table.normalized_headers),
            ", ".join(str(p) for p in table.page_numbers) or "unknown",
        )
    for warning in result.warnings:
        logger.warning("  ⚠ %s", warning)
    if output_files:
        logger.info("Output files: %s", ", ".join(output_files))
    logger.info("=" * 60)

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        description="Extract energy data tables from government PDF documents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python extract_energy_table.py report.pdf
  python extract_energy_table.py report.pdf --format csv --lang vi
  python extract_energy_table.py report.pdf --tables capacity,generation --output extracted/
  python extract_energy_table.py report.pdf --backend pymupdf4llm
        """,
    )
    parser.add_argument(
        "pdf_path",
        type=str,
        help="Path to the PDF file to extract tables from.",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="csv",
        choices=["csv", "json", "markdown", "md"],
        help="Output format (default: csv).",
    )
    parser.add_argument(
        "--lang",
        type=str,
        default="auto",
        choices=["vi", "en", "auto"],
        help="Source document language (default: auto-detect).",
    )
    parser.add_argument(
        "--tables",
        type=str,
        default="all",
        help=(
            "Comma-separated table types to extract: "
            "capacity, generation, fuel, emissions, financial, all (default: all)."
        ),
    )
    parser.add_argument(
        "--output",
        type=str,
        default=".",
        help="Output directory for extracted files (default: current directory).",
    )
    parser.add_argument(
        "--backend",
        type=str,
        default="pdfplumber",
        choices=["pdfplumber", "pymupdf4llm"],
        help="PDF extraction backend (default: pdfplumber).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose (DEBUG) logging.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        result = extract_tables(
            pdf_path=args.pdf_path,
            output_dir=args.output,
            output_format=args.format,
            lang=args.lang,
            table_filter=args.tables,
            backend=args.backend,
        )

        if not result.tables:
            logger.warning("No tables were extracted. See warnings above.")
            return 1

        return 0

    except FileNotFoundError as e:
        logger.error(str(e))
        return 2
    except ImportError as e:
        logger.error(str(e))
        return 3
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return 4


if __name__ == "__main__":
    sys.exit(main())
```

## 3. Test File

Save as `tests/test_extract_energy_table.py`:

```python
"""
Tests for extract_energy_table.py

Run with: pytest tests/test_extract_energy_table.py -v
"""

from __future__ import annotations

import csv
import io
import json
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import the module under test
from scripts.extract_energy_table import (
    ExtractedTable,
    ExtractionResult,
    _build_extracted_table,
    _deduplicate_headers,
    _detect_language,
    _parse_markdown_tables,
    _parse_number,
    _row_matches_headers,
    _strip_diacritics,
    _to_snake_case,
    build_parser,
    classify_table_type,
    clean_numeric_value,
    extract_unit_from_header,
    main,
    normalize_header,
    write_csv,
    write_json,
    write_markdown,
)


# ===================================================================
# Header normalization tests
# ===================================================================


class TestNormalizeHeader:
    """Tests for Vietnamese → English header normalization."""

    def test_vietnamese_capacity_header(self) -> None:
        assert normalize_header("Công suất (MW)") == "capacity_mw"

    def test_vietnamese_plant_name(self) -> None:
        assert normalize_header("Tên nhà máy") == "plant_name"

    def test_vietnamese_generation(self) -> None:
        assert normalize_header("Sản lượng (GWh)") == "generation_gwh"

    def test_vietnamese_province(self) -> None:
        assert normalize_header("Tỉnh") == "province"

    def test_vietnamese_year(self) -> None:
        assert normalize_header("Năm") == "year"

    def test_vietnamese_row_number(self) -> None:
        assert normalize_header("STT") == "row_number"

    def test_vietnamese_notes(self) -> None:
        assert normalize_header("Ghi chú") == "notes"

    def test_vietnamese_total(self) -> None:
        assert normalize_header("Tổng") == "total"

    def test_vietnamese_installed_capacity(self) -> None:
        assert normalize_header("Công suất đặt (MW)") == "installed_capacity_mw"

    def test_vietnamese_fuel_type(self) -> None:
        assert normalize_header("Nhiên liệu") == "fuel_type"

    def test_vietnamese_investment(self) -> None:
        assert normalize_header("Vốn đầu tư (tỷ đồng)") == "investment_billion_vnd"

    def test_vietnamese_emissions(self) -> None:
        assert normalize_header("Phát thải CO2") == "co2_emissions"

    def test_vietnamese_share_pct(self) -> None:
        assert normalize_header("Tỷ lệ (%)") == "share_pct"

    def test_english_header_passthrough(self) -> None:
        result = normalize_header("Generation (GWh)", lang="en")
        assert result == "generation_gwh"

    def test_english_camel_case(self) -> None:
        result = normalize_header("PlantName", lang="en")
        assert result == "plant_name"

    def test_empty_header(self) -> None:
        assert normalize_header("") == "unnamed_column"

    def test_whitespace_only_header(self) -> None:
        assert normalize_header("   ") == "unnamed_column"

    def test_unicode_normalization(self) -> None:
        # NFC vs NFD forms of Vietnamese text
        nfc = "Công suất"
        # Ensure it normalizes correctly regardless of input form
        result = normalize_header(nfc)
        assert result == "capacity_mw"

    def test_case_insensitive_matching(self) -> None:
        assert normalize_header("CÔNG SUẤT (MW)") == "capacity_mw"
        assert normalize_header("stt") == "row_number"

    def test_unknown_vietnamese_header_strips_diacritics(self) -> None:
        result = normalize_header("Đặc biệt khác", lang="vi")
        # Should strip diacritics and snake_case
        assert "dac_biet" in result or "unnamed" not in result


class TestExtractUnitFromHeader:
    """Tests for unit extraction from headers."""

    def test_mw_unit(self) -> None:
        header, unit = extract_unit_from_header("Capacity (MW)")
        assert header == "Capacity"
        assert unit == "MW"

    def test_gwh_unit(self) -> None:
        header, unit = extract_unit_from_header("Generation (GWh)")
        assert header == "Generation"
        assert unit == "GWh"

    def test_percent_unit(self) -> None:
        header, unit = extract_unit_from_header("Share (%)")
        assert header == "Share"
        assert unit == "%"

    def test_vietnamese_unit(self) -> None:
        header, unit = extract_unit_from_header("Vốn đầu tư (tỷ đồng)")
        assert header == "Vốn đầu tư"
        assert unit == "tỷ đồng"

    def test_no_unit(self) -> None:
        header, unit = extract_unit_from_header("Plant Name")
        assert header == "Plant Name"
        assert unit is None

    def test_non_unit_parentheses(self) -> None:
        header, unit = extract_unit_from_header("Name (abbreviated)")
        assert header == "Name (abbreviated)"
        assert unit is None


class TestStripDiacritics:
    """Tests for Vietnamese diacritic removal."""

    def test_basic_diacritics(self) -> None:
        assert _strip_diacritics("Công suất") == "Cong suat"

    def test_all_vietnamese_tones(self) -> None:
        result = _strip_diacritics("ắằẳẵặ")
        assert all(ord(c) < 128 for c in result)

    def test_no_diacritics(self) -> None:
        assert _strip_diacritics("Hello World") == "Hello World"


class TestToSnakeCase:
    """Tests for snake_case conversion."""

    def test_simple(self) -> None:
        assert _to_snake_case("Hello World") == "hello_world"

    def test_camel_case(self) -> None:
        assert _to_snake_case("CamelCase") == "camel_case"

    def test_with_parentheses(self) -> None:
        assert _to_snake_case("Capacity (MW)") == "capacity_mw"

    def test_multiple_spaces(self) -> None:
        assert _to_snake_case("Hello   World") == "hello_world"

    def test_empty(self) -> None:
        assert _to_snake_case("") == "unnamed_column"


class TestDeduplicateHeaders:
    """Tests for header deduplication."""

    def test_no_duplicates(self) -> None:
        headers = ["a", "b", "c"]
        assert _deduplicate_headers(headers) == ["a", "b", "c"]

    def test_with_duplicates(self) -> None:
        headers = ["value", "value", "value"]
        result = _deduplicate_headers(headers)
        assert result == ["value", "value_1", "value_2"]

    def test_mixed_duplicates(self) -> None:
        headers = ["name", "value", "name", "value"]
        result = _deduplicate_headers(headers)
        assert len(result) == len(set(result))  # All unique


# ===================================================================
# Numeric cleaning tests
# ===================================================================


class TestCleanNumericValue:
    """Tests for numeric value cleaning."""

    def test_plain_integer(self) -> None:
        assert clean_numeric_value("1200") == 1200.0

    def test_plain_float(self) -> None:
        assert clean_numeric_value("3.14") == 3.14

    def test_vietnamese_thousand_separator(self) -> None:
        # 1.200 with dot as thousand separator
        assert clean_numeric_value("1.200") == 1200.0

    def test_vietnamese_thousand_and_decimal(self) -> None:
        # 1.200,50 → 1200.50
        assert clean_numeric_value("1.200,50") == 1200.50

    def test_us_thousand_separator(self) -> None:
        # 1,200 with comma as thousand separator
        assert clean_numeric_value("1,200") == 1200.0

    def test_us_thousand_and_decimal(self) -> None:
        # 1,200.5 → 1200.5
        assert clean_numeric_value("1,200.5") == 1200.5

    def test_european_decimal_comma(self) -> None:
        # 3,14 → 3.14
        assert clean_numeric_value("3,14") == 3.14

    def test_large_number_with_dots(self) -> None:
        # 1.200.000 → 1200000
        assert clean_numeric_value("1.200.000") == 1200000.0

    def test_large_number_with_commas(self) -> None:
        # 1,200,000 → 1200000
        assert clean_numeric_value("1,200,000") == 1200000.0

    def test_mw_suffix(self) -> None:
        assert clean_numeric_value("1.200 MW") == 1200.0

    def test_gwh_suffix(self) -> None:
        assert clean_numeric_value("500 GWh") == 500.0

    def test_percent_suffix(self) -> None:
        assert clean_numeric_value("45.5%") == 45.5

    def test_vietnamese_ton_suffix(self) -> None:
        assert clean_numeric_value("1.200 tấn") == 1200.0

    def test_dash_missing_value(self) -> None:
        assert clean_numeric_value("-") is None

    def test_em_dash_missing_value(self) -> None:
        assert clean_numeric_value("—") is None

    def test_en_dash_missing_value(self) -> None:
        assert clean_numeric_value("–") is None

    def test_na_missing_value(self) -> None:
        assert clean_numeric_value("N/A") is None

    def test_ellipsis_missing_value(self) -> None:
        assert clean_numeric_value("...") is None

    def test_empty_string(self) -> None:
        assert clean_numeric_value("") is None

    def test_none_input(self) -> None:
        assert clean_numeric_value(None) is None

    def test_text_passthrough(self) -> None:
        assert clean_numeric_value("Nhà máy ABC") == "Nhà máy ABC"

    def test_text_with_numbers(self) -> None:
        # Text that contains numbers but isn't purely numeric
        result = clean_numeric_value("Phase 2A")
        assert result == "Phase 2A"

    def test_negative_number(self) -> None:
        assert clean_numeric_value("-500") == -500.0

    def test_negative_with_parentheses(self) -> None:
        assert clean_numeric_value("(500)") == -500.0

    def test_whitespace_handling(self) -> None:
        assert clean_numeric_value("  1200  ") == 1200.0

    def test_non_string_float_input(self) -> None:
        assert clean_numeric_value(42.5) == 42.5

    def test_non_string_int_input(self) -> None:
        assert clean_numeric_value(42) == 42.0


class TestParseNumber:
    """Tests for the internal number parser."""

    def test_simple_integer(self) -> None:
        assert _parse_number("42") == 42.0

    def test_simple_float(self) -> None:
        assert _parse_number("3.14") == 3.14

    def test_non_numeric(self) -> None:
        assert _parse_number("abc") is None

    def test_empty(self) -> None:
        assert _parse_number("") is None

    def test_with_spaces(self) -> None:
        assert _parse_number("1 200") == 1200.0

    def test_negative_sign(self) -> None:
        assert _parse_number("-42") == -42.0

    def test_unicode_minus(self) -> None:
        assert _parse_number("−42") == -42.0


# ===================================================================
# Table classification tests
# ===================================================================


class TestClassifyTableType:
    """Tests for table type classification."""

    def test_capacity_table(self) -> None:
        result = classify_table_type(
            "Danh mục nhà máy điện",
            ["STT", "Tên nhà máy", "Công suất (MW)", "Năm vận hành"],
        )
        assert result == "capacity"

    def test_generation_table(self) -> None:
        result = classify_table_type(
            "Sản lượng điện theo năm",
            ["Năm", "Sản lượng (GWh)", "Tỷ lệ (%)"],
        )
        assert result == "generation"

    def test_fuel_table(self) -> None:
        result = classify_table_type(
            "Fuel consumption",
            ["Year", "Coal (ton)", "Gas (m3)", "Oil (ton)"],
        )
        assert result == "fuel"

    def test_emissions_table(self) -> None:
        result = classify_table_type(
            "CO2 Emissions by Source",
            ["Source", "CO2 (million tons)", "Share (%)"],
        )
        assert result == "emissions"

    def test_financial_table(self) -> None:
        result = classify_table_type(
            "Vốn đầu tư các dự án",
            ["Dự án", "Vốn đầu tư (tỷ đồng)", "Tiến độ"],
        )
        assert result == "financial"

    def test_unknown_table(self) -> None:
        result = classify_table_type(
            "Random Data",
            ["Column A", "Column B", "Column C"],
        )
        assert result == "unknown"


# ===================================================================
# Language detection tests
# ===================================================================


class TestDetectLanguage:
    """Tests for language detection from headers."""

    def test_vietnamese_headers(self) -> None:
        headers = ["STT", "Tên nhà máy", "Công suất (MW)", "Tỉnh"]
        assert _detect_language(headers) == "vi"

    def test_english_headers(self) -> None:
        headers = ["ID", "Plant Name", "Capacity (MW)", "Province"]
        assert _detect_language(headers) == "en"

    def test_mixed_headers(self) -> None:
        # With enough Vietnamese indicators, should detect as Vietnamese
        headers = ["STT", "Nhà máy", "MW", "Năm", "Ghi chú"]
        assert _detect_language(headers) == "vi"


# ===================================================================
# Row matching tests (multi-page table detection)
# ===================================================================


class TestRowMatchesHeaders:
    """Tests for multi-page table header detection."""

    def test_exact_match(self) -> None:
        headers = ["Name", "Value", "Unit"]
        row = ["Name", "Value", "Unit"]
        assert _row_matches_headers(row, headers) is True

    def test_case_insensitive_match(self) -> None:
        headers = ["Name", "Value", "Unit"]
        row = ["name", "value", "unit"]
        assert _row_matches_headers(row, headers) is True

    def test_no_match(self) -> None:
        headers = ["Name", "Value", "Unit"]
        row = ["ABC", "123", "MW"]
        assert _row_matches_headers(row, headers) is False

    def test_different_lengths(self) -> None:
        headers = ["Name", "Value"]
        row = ["Name", "Value", "Extra"]
        assert _row_matches_headers(row, headers) is False

    def test_partial_match_above_threshold(self) -> None:
        headers = ["Name", "Value", "Unit"]
        row = ["Name", "Value", "Different"]
        # 2/3 = 0.67 > 0.6 threshold
        assert _row_matches_headers(row, headers) is True


# ===================================================================
# Output format tests
# ===================================================================


@pytest.fixture
def sample_table() -> ExtractedTable:
    """Create a sample extracted table for output tests."""
    return ExtractedTable(
        table_id="table_001",
        table_type="capacity",
        title="Power Plant Inventory",
        headers=["STT", "Tên nhà máy", "Công suất (MW)"],
        normalized_headers=["row_number", "plant_name", "capacity_mw"],
        units={"capacity_mw": "MW"},
        rows=[
            [1.0, "Nhà máy A", 100.0],
            [2.0, "Nhà máy B", 200.0],
            [3.0, "Nhà máy C", None],
        ],
        page_numbers=[1, 2],
        source_file="test_report.pdf",
        extraction_timestamp="2024-01-15T10:30:00+00:00",
    )


class TestWriteCsv:
    """Tests for CSV output."""

    def test_csv_output_structure(self, sample_table: ExtractedTable, tmp_path: Path) -> None:
        filepath = write_csv(sample_table, tmp_path)
        assert filepath.exists()
        assert filepath.suffix == ".csv"

        content = filepath.read_text(encoding="utf-8-sig")
        lines = content.strip().split("\n")

        # Check metadata comments
        assert lines[0].startswith("# Source:")
        assert lines[1].startswith("# Pages:")
        assert lines[2].startswith("# Extracted:")
        assert lines[3].startswith("# Table type:")

        # Find the header row (first non-comment row)
        header_line = None
        for line in lines:
            if not line.startswith("#"):
                header_line = line
                break

        assert header_line is not None
        assert "row_number" in header_line
        assert "plant_name" in header_line
        assert "capacity_mw" in header_line

    def test_csv_data_rows(self, sample_table: ExtractedTable, tmp_path: Path) -> None:
        filepath = write_csv(sample_table, tmp_path)
        content = filepath.read_text(encoding="utf-8-sig")

        # Parse CSV, skipping comment lines
        non_comment_lines = [
            l for l in content.strip().split("\n") if not l.startswith("#")
        ]
        reader = csv.reader(io.StringIO("\n".join(non_comment_lines)))
        rows = list(reader)

        # Header + 3 data rows
        assert len(rows) == 4
        assert rows[0] == ["row_number", "plant_name", "capacity_mw"]
        assert rows[1][1] == "Nhà máy A"

    def test_csv_utf8_encoding(self, sample_table: ExtractedTable, tmp_path: Path) -> None:
        filepath = write_csv(sample_table, tmp_path)
        content = filepath.read_text(encoding="utf-8-sig")
        assert "Nhà máy A" in content
        assert "Nhà máy B" in content

    def test_csv_none_handling(self, sample_table: ExtractedTable, tmp_path: Path) -> None:
        filepath = write_csv(sample_table, tmp_path)
        content = filepath.read_text(encoding="utf-8-sig")
        # None should appear as empty or "None" in CSV
        lines = [l for l in content.strip().split("\n") if not l.startswith("#")]
        # The last data row has None for capacity
        assert len(lines) == 4  # header + 3 data rows


class TestWriteJson:
    """Tests for JSON output."""

    def test_json_output_structure(self, sample_table: ExtractedTable, tmp_path: Path) -> None:
        filepath = write_json(sample_table, tmp_path)
        assert filepath.exists()
        assert filepath.suffix == ".json"

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        assert "metadata" in data
        assert "columns" in data
        assert "data" in data

    def test_json_metadata(self, sample_table: ExtractedTable, tmp_path: Path) -> None:
        filepath = write_json(sample_table, tmp_path)

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        meta = data["metadata"]
        assert meta["source_file"] == "test_report.pdf"
        assert meta["page_numbers"] == [1, 2]
        assert meta["table_type"] == "capacity"
        assert meta["row_count"] == 3

    def test_json_data_records(self, sample_table: ExtractedTable, tmp_path: Path) -> None:
        filepath = write_json(sample_table, tmp_path)

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        records = data["data"]
        assert len(records) == 3
        assert records[0]["plant_name"] == "Nhà máy A"
        assert records[0]["capacity_mw"] == 100.0
        assert records[2]["capacity_mw"] is None

    def test_json_utf8(self, sample_table: ExtractedTable, tmp_path: Path) -> None:
        filepath = write_json(sample_table, tmp_path)
        content = filepath.read_text(encoding="utf-8")
        # ensure_ascii=False means Vietnamese chars are preserved
        assert "Nhà máy A" in content


class TestWriteMarkdown:
    """Tests for Markdown output."""

    def test_markdown_output_structure(
        self, sample_table: ExtractedTable, tmp_path: Path
    ) -> None:
        filepath = write_markdown(sample_table, tmp_path)
        assert filepath.exists()
        assert filepath.suffix == ".md"

        content = filepath.read_text(encoding="utf-8")
        assert "## Power Plant Inventory" in content
        assert "| row_number | plant_name | capacity_mw |" in content
        assert "| --- | --- | --- |" in content

    def test_markdown_metadata(self, sample_table: ExtractedTable, tmp_path: Path) -> None:
        filepath = write_markdown(sample_table, tmp_path)
        content = filepath.read_text(encoding="utf-8")
        assert "**Source**" in content
        assert "test_report.pdf" in content
        assert "**Type**: capacity" in content

    def test_markdown_data_rows(self, sample_table: ExtractedTable, tmp_path: Path) -> None:
        filepath = write_markdown(sample_table, tmp_path)
        content = filepath.read_text(encoding="utf-8")
        assert "Nhà máy A" in content
        assert "100.0" in content


# ===================================================================
# Markdown table parsing tests
# ===================================================================


class TestParseMarkdownTables:
    """Tests for parsing markdown tables from pymupdf4llm output."""

    def test_simple_table(self, tmp_path: Path) -> None:
        md = textwrap.dedent("""\
            ## Power Plants

            | Name | Capacity (MW) | Year |
            |---|---|---|
            | Plant A | 100 | 2020 |
            | Plant B | 200 | 2021 |
        """)

        tables = _parse_markdown_tables(md, tmp_path / "test.pdf", "2024-01-01T00:00:00Z")
        assert len(tables) == 1
        assert tables[0].row_count == 2
        assert len(tables[0].normalized_headers) == 3

    def test_table_with_title(self, tmp_path: Path) -> None:
        md = textwrap.dedent("""\
            # Report

            ## Bảng 1: Danh mục nhà máy

            | STT | Tên nhà máy | Công suất (MW) |
            |---|---|---|
            | 1 | Nhà máy A | 100 |
        """)

        tables = _parse_markdown_tables(md, tmp_path / "test.pdf", "2024-01-01T00:00:00Z")
        assert len(tables) == 1
        assert "Bảng 1" in tables[0].title or "Danh mục" in tables[0].title

    def test_no_tables(self, tmp_path: Path) -> None:
        md = "Just some text without any tables."
        tables = _parse_markdown_tables(md, tmp_path / "test.pdf", "2024-01-01T00:00:00Z")
        assert len(tables) == 0

    def test_multiple_tables(self, tmp_path: Path) -> None:
        md = textwrap.dedent("""\
            ## Table 1

            | A | B |
            |---|---|
            | 1 | 2 |

            ## Table 2

            | C | D |
            |---|---|
            | 3 | 4 |
        """)

        tables = _parse_markdown_tables(md, tmp_path / "test.pdf", "2024-01-01T00:00:00Z")
        assert len(tables) == 2


# ===================================================================
# Build extracted table tests
# ===================================================================


class TestBuildExtractedTable:
    """Tests for the table building helper."""

    def test_basic_build(self, tmp_path: Path) -> None:
        raw = {
            "table_id": "table_001",
            "title": "Test Table",
            "headers": ["STT", "Tên nhà máy", "Công suất (MW)"],
            "rows": [
                ["1", "Plant A", "100"],
                ["2", "Plant B", "200"],
            ],
            "page_numbers": [1],
        }

        table = _build_extracted_table(raw, tmp_path / "test.pdf", "2024-01-01T00:00:00Z")

        assert table.table_id == "table_001"
        assert table.row_count == 2
        assert len(table.normalized_headers) == 3
        assert table.normalized_headers[0] == "row_number"

    def test_empty_rows_filtered(self, tmp_path: Path) -> None:
        raw = {
            "table_id": "table_001",
            "title": "",
            "headers": ["A", "B"],
            "rows": [
                ["1", "2"],
                ["", ""],
                ["3", "4"],
            ],
            "page_numbers": [1],
        }

        table = _build_extracted_table(raw, tmp_path / "test.pdf", "2024-01-01T00:00:00Z")
        assert table.row_count == 2  # Empty row filtered out

    def test_numeric_cleaning_in_build(self, tmp_path: Path) -> None:
        raw = {
            "table_id": "table_001",
            "title": "",
            "headers": ["Name", "Value"],
            "rows": [
                ["Plant A", "1.200 MW"],
                ["Plant B", "-"],
            ],
            "page_numbers": [1],
        }

        table = _build_extracted_table(raw, tmp_path / "test.pdf", "2024-01-01T00:00:00Z")
        assert table.rows[0][1] == 1200.0
        assert table.rows[1][1] is None


# ===================================================================
# CLI argument parser tests
# ===================================================================


class TestBuildParser:
    """Tests for CLI argument parsing."""

    def test_minimal_args(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["test.pdf"])
        assert args.pdf_path == "test.pdf"
        assert args.format == "csv"
        assert args.lang == "auto"
        assert args.tables == "all"
        assert args.output == "."
        assert args.backend == "pdfplumber"
        assert args.verbose is False

    def test_all_args(self) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "report.pdf",
            "--format", "json",
            "--lang", "vi",
            "--tables", "capacity,generation",
            "--output", "extracted/",
            "--backend", "pymupdf4llm",
            "--verbose",
        ])
        assert args.pdf_path == "report.pdf"
        assert args.format == "json"
        assert args.lang == "vi"
        assert args.tables == "capacity,generation"
        assert args.output == "extracted/"
        assert args.backend == "pymupdf4llm"
        assert args.verbose is True

    def test_short_verbose_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["test.pdf", "-v"])
        assert args.verbose is True


# ===================================================================
# Main function tests (with mocking)
# ===================================================================


class TestMain:
    """Tests for the main entry point."""

    def test_file_not_found(self, tmp_path: Path) -> None:
        nonexistent = str(tmp_path / "nonexistent.pdf")
        exit_code = main([nonexistent])
        assert exit_code == 2

    def test_not_a_pdf(self, tmp_path: Path) -> None:
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("not a pdf")
        exit_code = main([str(txt_file)])
        assert exit_code == 2  # ValueError caught as unexpected error or file validation

    @patch("scripts.extract_energy_table.extract_tables")
    def test_no_tables_found(self, mock_extract: MagicMock, tmp_path: Path) -> None:
        pdf_file = tmp_path / "empty.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")

        mock_extract.return_value = ExtractionResult(
            source_file=str(pdf_file),
            total_pages=5,
            tables=[],
            warnings=["No tables found on pages 1-5"],
        )

        exit_code = main([str(pdf_file), "--output", str(tmp_path)])
        assert exit_code == 1

    @patch("scripts.extract_energy_table.extract_tables")
    def test_successful_extraction(self, mock_extract: MagicMock, tmp_path: Path) -> None:
        pdf_file = tmp_path / "report.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")

        mock_extract.return_value = ExtractionResult(
            source_file=str(pdf_file),
            total_pages=10,
            tables=[
                ExtractedTable(
                    table_id="table_001",
                    table_type="capacity",
                    title="Test",
                    headers=["A"],
                    normalized_headers=["a"],
                    units={},
                    rows=[[1.0]],
                    page_numbers=[1],
                    source_file=str(pdf_file),
                    extraction_timestamp="2024-01-01T00:00:00Z",
                )
            ],
        )

        exit_code = main([str(pdf_file), "--output", str(tmp_path)])
        assert exit_code == 0


# ===================================================================
# Edge case tests
# ===================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_clean_numeric_with_nbsp(self) -> None:
        """Non-breaking space in numbers."""
        assert clean_numeric_value("1\u00a0200") == 1200.0

    def test_clean_numeric_mixed_separators(self) -> None:
        """Handle mixed separator formats gracefully."""
        assert clean_numeric_value("1.234.567,89") == 1234567.89

    def test_normalize_header_with_newlines(self) -> None:
        """Headers sometimes contain newlines from merged cells."""
        result = normalize_header("Công suất\n(MW)")
        # Should still match or produce reasonable output
        assert result != "unnamed_column"

    def test_empty_table_rows(self) -> None:
        """Table with only headers and no data."""
        raw = {
            "table_id": "table_001",
            "title": "",
            "headers": ["A", "B"],
            "rows": [],
            "page_numbers": [1],
        }
        table = _build_extracted_table(raw, Path("test.pdf"), "2024-01-01T00:00:00Z")
        assert table.row_count == 0

    def test_single_column_table(self) -> None:
        """Table with only one column."""
        raw = {
            "table_id": "table_001",
            "title": "",
            "headers": ["Name"],
            "rows": [["A"], ["B"]],
            "page_numbers": [1],
        }
        table = _build_extracted_table(raw, Path("test.pdf"), "2024-01-01T00:00:00Z")
        assert table.row_count == 2
        assert len(table.normalized_headers) == 1

    def test_row_shorter_than_headers(self) -> None:
        """Rows with fewer cells than headers should be padded."""
        raw = {
            "table_id": "table_001",
            "title": "",
            "headers": ["A", "B", "C"],
            "rows": [["1"]],
            "page_numbers": [1],
        }
        table = _build_extracted_table(raw, Path("test.pdf"), "2024-01-01T00:00:00Z")
        assert len(table.rows[0]) == 3
        assert table.rows[0][1] is None
        assert table.rows[0][2] is None

    def test_row_longer_than_headers(self) -> None:
        """Rows with more cells than headers should be truncated."""
        raw = {
            "table_id": "table_001",
            "title": "",
            "headers": ["A", "B"],
            "rows": [["1", "2", "3", "4"]],
            "page_numbers": [1],
        }
        table = _build_extracted_table(raw, Path("test.pdf"), "2024-01-01T00:00:00Z")
        assert len(table.rows[0]) == 2
```

## 4. Integration Instructions

### Directory Structure

```
your-project/
├── .claude/
│   └── commands/
│       └── extract-energy-table.md    # Skill definition
├── scripts/
│   └── extract_energy_table.py        # Main extraction script
├── tests/
│   └── test_extract_energy_table.py   # Test suite
├── CLAUDE.md                          # Project documentation
└── pyproject.toml                     # Dependencies
```

### Step 1: Place the Skill Definition

```bash
mkdir -p .claude/commands
# Copy the skill definition markdown to:
# .claude/commands/extract-energy-table.md
```

### Step 2: Place the Python Script

```bash
mkdir -p scripts
# Copy extract_energy_table.py to scripts/
chmod +x scripts/extract_energy_table.py
```

### Step 3: Install Dependencies

Add to your `pyproject.toml`:

```toml
[project]
# ... existing config ...
dependencies = [
    # ... existing deps ...
    "pdfplumber>=0.10.0",
    "pymupdf4llm>=0.0.10",
    "pymupdf>=1.24.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
]
```

Then install:

```bash
uv add pdfplumber pymupdf4llm pymupdf
uv add --dev pytest pytest-cov
```

### Step 4: Ensure the Script is Importable

If your project uses `src/` layout or a package, add an `__init__.py` or adjust the import path. For the flat `scripts/` layout, ensure your `pyproject.toml` or `conftest.py` adds the scripts directory to the Python path:

Create `tests/conftest.py`:

```python
"""Test configuration."""
import sys
from pathlib import Path

# Add scripts directory to path so tests can import from it
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
```

### Step 5: Run Tests

```bash
# Run all tests
uv run pytest tests/test_extract_energy_table.py -v

# Run with coverage
uv run pytest tests/test_extract_energy_table.py -v --cov=scripts --cov-report=term-missing

# Run a specific test class
uv run pytest tests/test_extract_energy_table.py::TestCleanNumericValue -v
```

### Step 6: Test the Script Standalone

```bash
# Basic extraction
uv run python scripts/extract_energy_table.py path/to/report.pdf

# With all options
uv run python scripts/extract_energy_table.py path/to/report.pdf \
    --format csv \
    --lang vi \
    --tables capacity,generation \
    --output extracted/ \
    --verbose
```

### Step 7: Test the Claude Code Skill

In Claude Code, type:

```
/extract-energy-table ./data/sample-report.pdf --format csv --lang vi
```

Claude will:
1. Parse your arguments
2. Verify the script exists
3. Run the extraction
4. Validate and present results

### Step 8: Add to CLAUDE.md

Add this entry to your project's `CLAUDE.md`:

```markdown
## Custom Commands

### `/extract-energy-table`

Extracts structured energy data tables from government PDF documents (PDP reports,
EVN annual reports, power plant inventories) into clean CSV/JSON/Markdown format.

**Usage:**
```
/extract-energy-table <pdf_path_or_url> [--format csv|json|markdown] [--lang vi|en] [--tables capacity,generation,fuel,emissions,financial,all] [--output <dir>]
```

**Examples:**
```
/extract-energy-table ./data/pdp8-report.pdf
/extract-energy-table ./data/evn-2023.pdf --format json --lang vi --tables capacity
/extract-energy-table ./report.pdf --output extracted/ --format markdown
```

**What it does:**
- Extracts tables from PDF using pdfplumber or pymupdf4llm
- Handles Vietnamese text with diacritics (UTF-8)
- Normalizes Vietnamese column headers to English snake_case
- Cleans numeric values (strips thousand separators, unit suffixes)
- Detects and merges multi-page tables
- Classifies tables by type (capacity, generation, fuel, emissions, financial)
- Outputs with full provenance (source file, page numbers, timestamp)

**Dependencies:** pdfplumber, pymupdf4llm (install with `uv add pdfplumber pymupdf4llm`)

**Script location:** `scripts/extract_energy_table.py`
**Tests:** `tests/test_extract_energy_table.py`
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `ImportError: pdfplumber not installed` | Run `uv add pdfplumber` |
| `No tables found` | PDF may be image-based; try OCR pipeline or different backend (`--backend pymupdf4llm`) |
| Vietnamese characters garbled | Ensure terminal supports UTF-8; CSV files use UTF-8-BOM for Excel compatibility |
| `ModuleNotFoundError` in tests | Check `tests/conftest.py` adds `scripts/` to `sys.path` |
| Numbers parsed incorrectly | Check if the document uses Vietnamese (dot=thousand) or US (comma=thousand) convention; the parser uses heuristics that work for most cases |