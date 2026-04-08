"""Extract CSV tables from LLM JSON responses.

Each JSON file contains raw assistant text which usually embeds a CSV inside
Markdown code fences.  This script extracts that CSV, canonicalizes the
columns, and writes a clean comma-delimited CSV so it can be evaluated.

Usage:
  python -m aedist.extract --input outputs/census --output outputs/census
"""

import argparse
import csv
import io
import json
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from aedist.util import parse_number

log = logging.getLogger(__name__)


# Bonus per recognized header keyword in CSV scoring
HEADER_KEYWORD_BONUS = 0.2

# Keywords that signal a CSV header row about power plants.
# Shared between score_csv_like_block() and fallback_extract_inline_csv()
# to prevent the two lists from drifting apart.
_HEADER_KEYWORDS = (
    "name",
    "plant",
    "project",
    "fuel",
    "status",
    "stage",
    "cod",
    "connection",
    "province",
    "capacity",
)
# Cap for length bonus normalization (number of lines)
LENGTH_BONUS_CAP_LINES = 50.0


def extract_fenced_blocks(text: str) -> list[str]:
    # Capture content in ```csv ...``` or ``` ... ```
    blocks: list[str] = []
    for m in re.finditer(r"```(?:csv)?\s*\n(.*?)\n```", text, flags=re.IGNORECASE | re.DOTALL):
        blocks.append(m.group(1))
    return blocks


def score_csv_like_block(block: str) -> float:
    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    if not lines:
        return -1.0

    # Exclude obvious non-CSV
    if any("|" in ln and ln.count("|") >= 2 for ln in lines[:5]):
        return -1.0

    comma_lines = sum(1 for ln in lines if "," in ln)
    semicolon_lines = sum(1 for ln in lines if ";" in ln)
    tab_lines = sum(1 for ln in lines if "\t" in ln)
    delimiter_hits = max(comma_lines, semicolon_lines, tab_lines)

    header = lines[0].lower()
    header_bonus = 0.0
    for token in _HEADER_KEYWORDS:
        if token in header:
            header_bonus += HEADER_KEYWORD_BONUS

    # Prefer longer blocks and those with many delimited lines
    length_bonus = min(len(lines) / LENGTH_BONUS_CAP_LINES, 1.0)  # cap
    return (delimiter_hits / max(len(lines), 1)) + header_bonus + length_bonus


def _extract_pipe_table(text: str) -> str | None:
    """Convert a Markdown pipe table to CSV.

    Finds lines with ≥3 pipe characters, strips the separator row (---),
    and converts to comma-delimited CSV.
    """
    lines = text.splitlines()
    table_lines: list[str] = []
    for ln in lines:
        stripped = ln.strip()
        if "|" in stripped and stripped.count("|") >= 3:
            # Skip separator rows like |---|---|---|
            if re.match(r"^\|?[\s\-:|]+\|?$", stripped):
                continue
            # Strip leading/trailing pipes, split on |
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            table_lines.append(",".join(f'"{c}"' for c in cells))

    if len(table_lines) < 2:
        return None
    return "\n".join(table_lines)


def fallback_extract_inline_csv(text: str) -> str | None:
    """Extract a CSV-looking region when there are no fenced blocks."""
    lines = text.splitlines()
    # Find likely header
    header_idx = None
    for i, ln in enumerate(lines):
        stripped = ln.strip()
        if not stripped:
            continue
        low = stripped.lower()
        if ("," in stripped or ";" in stripped or "\t" in stripped) and any(
            kw in low for kw in _HEADER_KEYWORDS
        ):
            header_idx = i
            break
    if header_idx is None:
        # Otherwise, take the first sufficiently CSV-like line
        for i, ln in enumerate(lines):
            stripped = ln.strip()
            if stripped.count(",") >= 2 or stripped.count(";") >= 2 or stripped.count("\t") >= 2:
                header_idx = i
                break

    if header_idx is None:
        return None

    out: list[str] = []
    blank_streak = 0
    for ln in lines[header_idx:]:
        if not ln.strip():
            blank_streak += 1
            if blank_streak >= 2:
                break
            continue
        blank_streak = 0
        out.append(ln)

    return "\n".join(out).strip() if out else None


def sniff_dialect(sample: str) -> csv.Dialect:
    sample = sample.strip()
    # Some LLMs emit a leading Excel hint: sep=;
    if sample.lower().startswith("sep="):
        sample = "\n".join(sample.splitlines()[1:]).lstrip()

    sniffer = csv.Sniffer()
    try:
        # `delimiters` expects a string of candidate delimiter characters.
        dialect_any: Any = sniffer.sniff(sample[:4096], delimiters=",;\t|")
        # Some type stubs describe `sniff()` as returning a dialect *class*.
        if isinstance(dialect_any, type):
            dialect_any = dialect_any()
        return cast(csv.Dialect, dialect_any)
    except csv.Error:
        # Default to comma
        class _Comma(csv.Dialect):
            delimiter = ","
            quotechar = '"'
            doublequote = True
            skipinitialspace = True
            lineterminator = "\n"
            quoting = csv.QUOTE_MINIMAL

        return _Comma()


def norm_header(h: str) -> str:
    h = h.strip().lower()
    h = re.sub(r"\([^)]*\)", "", h)  # drop parenthesized units
    h = re.sub(r"[^a-z0-9]+", "_", h)
    return h.strip("_")


_CANON = ["name", "fuel", "status", "cod", "province", "capacity_mwe"]


def map_header_to_canonical(norm: str) -> str | None:
    if norm in {
        "name",
        "plant",
        "plant_name",
        "plantname",
        "power_plant",
        "power_plant_name",
        "project",
    }:
        return "name"
    if norm in {"fuel", "fuel_type", "fueltype"}:
        return "fuel"
    if norm in {"status", "construction_stage", "stage", "constructionstage"}:
        return "status"
    if norm in {"cod", "connection_date", "date", "connectiondate"}:
        return "cod"
    if norm in {"province", "location"}:
        return "province"
    if norm in {
        "capacity_mwe",
        "capacity",
        "generation_capacity",
        "capacity_mw",
        "capacity_mwe_",
        "capacity_mwe__",
    }:
        return "capacity_mwe"
    # Common variants that still normalize with parentheses removed
    if norm.startswith("capacity"):
        return "capacity_mwe"
    return None


@dataclass
class ExtractResult:
    wrote: bool
    output_path: Path | None
    message: str


def parse_and_canonicalize(csv_text: str) -> str:
    csv_text = csv_text.strip()
    if csv_text.lower().startswith("sep="):
        csv_text = "\n".join(csv_text.splitlines()[1:]).lstrip()

    dialect = sniff_dialect(csv_text)
    reader = csv.reader(io.StringIO(csv_text), dialect=dialect)
    rows = [row for row in reader if any((cell or "").strip() for cell in row)]
    if len(rows) < 2:
        raise ValueError("CSV seems empty (missing data rows)")

    raw_headers = rows[0]
    norm_headers = [norm_header(h) for h in raw_headers]
    idx_by_canon: dict[str, int] = {}
    for i, nh in enumerate(norm_headers):
        canon = map_header_to_canonical(nh)
        if canon and canon not in idx_by_canon:
            idx_by_canon[canon] = i

    if "name" not in idx_by_canon:
        raise ValueError("CSV missing a recognizable plant name column")

    out_buf = io.StringIO()
    writer = csv.writer(out_buf, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(_CANON)
    for row in rows[1:]:
        out_row: list[str] = []
        for canon in _CANON:
            idx = idx_by_canon.get(canon)
            val = row[idx] if (idx is not None and idx < len(row)) else ""
            cell = (val or "").strip()
            if canon == "capacity_mwe":
                n = parse_number(cell, integer_expected=True)
                cell = str(n) if n is not None else "0"
            out_row.append(cell)
        # Skip completely empty lines (shouldn't happen, but safe)
        if not out_row[0]:
            continue
        writer.writerow(out_row)
    return out_buf.getvalue()


def extract_one(json_path: Path, output_dir: Path, overwrite: bool) -> ExtractResult:
    out_path = output_dir / f"{json_path.stem}.csv"
    if out_path.exists() and not overwrite:
        return ExtractResult(False, out_path, f"{json_path.name}: skip (exists)")

    try:
        record = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as e:
        return ExtractResult(False, None, f"{json_path.name}: invalid JSON ({e})")

    response = record.get("response")
    # Handle multiturn JSON format: extract from turns[-1]["content"]
    if (not response or not isinstance(response, str)) and "turns" in record:
        turns = record["turns"]
        assistant_turns = [t for t in turns if t.get("role") == "assistant"]
        if assistant_turns:
            response = assistant_turns[-1].get("content", "")
    if not isinstance(response, str) or not response.strip():
        return ExtractResult(False, None, f"{json_path.name}: no response text")

    blocks = extract_fenced_blocks(response)
    candidates = blocks[:]
    pipe_csv = _extract_pipe_table(response)
    if pipe_csv:
        candidates.append(pipe_csv)
    # Only try inline fallback when no fenced blocks or pipe tables found
    if not candidates:
        inline = fallback_extract_inline_csv(response)
        if inline:
            candidates.append(inline)

    if not candidates:
        return ExtractResult(False, None, f"{json_path.name}: no CSV found")

    best = max(candidates, key=score_csv_like_block)
    try:
        canonical_csv = parse_and_canonicalize(best)
    except Exception as e:
        return ExtractResult(False, None, f"{json_path.name}: CSV parse failed ({e})")

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(canonical_csv, encoding="utf-8")
    return ExtractResult(True, out_path, f"{json_path.name}: wrote {out_path.name}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(description="Extract CSV from LLM JSON outputs")
    p.add_argument(
        "--input",
        required=True,
        help="Directory containing JSON outputs",
    )
    p.add_argument(
        "--output",
        required=True,
        help="Directory to write extracted CSV files into",
    )
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing CSV files")
    args = p.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)

    if not input_dir.exists() or not input_dir.is_dir():
        raise SystemExit(f"Input dir not found: {input_dir}")

    json_files = sorted(input_dir.glob("*.json"))
    if not json_files:
        raise SystemExit(f"No JSON files in: {input_dir}")

    wrote = 0
    failed = 0
    skipped = 0
    for jf in json_files:
        res = extract_one(jf, output_dir, overwrite=args.overwrite)
        log.info(res.message)
        if "wrote" in res.message:
            wrote += 1
        elif "skip" in res.message:
            skipped += 1
        else:
            failed += 1

    log.info("Done. wrote=%d skipped=%d failed=%d (from %s)", wrote, skipped, failed, input_dir)
    if wrote == 0 and failed > 0:
        sys.exit(2)


if __name__ == "__main__":
    main()
