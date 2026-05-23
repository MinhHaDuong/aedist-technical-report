"""Extract bibliography quality metrics from Exp2 markdown narratives.

Usage:
    python -m aedist.extract_exp2_bib \
        --naive-dir experiments/outputs/sota_exp2_naive_arm \
        --optimised-dir experiments/outputs/sota_exp2_brerun1 \
        --output report/inputs/generated/tab_exp2_bib_quality.csv

Parses per-run markdown files, classifies source cells, and emits a flat CSV
with one row per (agent, arm, run).
"""

import argparse
import csv
import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)

_DEFAULT_NAIVE_DIR = Path("experiments/outputs/sota_exp2_naive_arm")
_DEFAULT_OPTIMISED_DIR = Path("experiments/outputs/sota_exp2_brerun1")

_RUN_RE = re.compile(r"^([a-z]+)_run(\d+)\.md$")

# Key-reference: short codes like B01, B1, [B05], S01, S1, [S10]
# Also matches markdown-linked keys: [S01](https://...)
_KEY_REF_CELL_RE = re.compile(
    r"^\s*\[?[A-Z]\d{1,3}\]?"  # the key itself
    r"(?:\(https?://[^\)]*\))?"  # optional markdown link URL
    r"\s*$"
)

# Empty / null markers
_EMPTY_MARKERS = {"", "—", "–", "-", "n/a", "na", "none"}

# Not-found markers (case-insensitive match)
_NOTFOUND_PATTERNS = [
    "not found",
    "url not verified",
    "not verified",
    "not available",
    "unable to verify",
    "could not verify",
    "no source",
    "unverified",
]

# --- Primary source classification ---

_PRIMARY_PATTERNS = [
    r"\bevn\b",
    r"\bmoit\b",
    r"\bpdp\s*8\b",
    r"\bpdp\s*viii\b",
    r"\bpv\s*power\b",
    r"\bpvpower\b",
    r"\bevngenco",
    r"\bgenco\s*[123]\b",
    r"\btkv\b",
    r"\bvinacomin\b",
    r"\bdecision\s+\d+",
    r"\bquyết\s+định\b",
    r"\bqd-ttg\b",
    r"\bqđ-ttg\b",
    r"\bqđ-bct\b",
    r"annual\s+report",
    r"\.gov\.vn\b",
    r"\bmoit\.gov",
    r"\bevn\.com\.vn\b",
    r"\bpvpower\.vn\b",
    r"\bgenco[123]\.com",
    r"\bdienluctkv\b",
    r"\berav\b",
    r"\bformosa\b",
    r"\bhòa\s+phát\b",
    r"\bhoa\s+phat\b",
    r"\bnăng\s+lượng\s+việt\s+nam\b",
    r"\bvietnamplus\b",
    r"\bttxvn\b",
    r"\blawnet\.vn\b",
    r"\bthuvienphapluat\b",
]

_SECONDARY_PATTERNS = [
    r"\bgem\b",
    r"\bglobal\s+energy\s+monitor\b",
    r"\bkpmg\b",
    r"\bs&p\b",
    r"\bspglobal\b",
    r"\bcarbon\s+brief\b",
    r"\bpower\s+technolog",
    r"\bdfdl\b",
    r"\bmayer\s+brown\b",
    r"\bfrasers?\b",
    r"\bieefa\b",
    r"\bjica\b",
    r"\badb\.org\b",
    r"\bnorton\s+rose\b",
    r"\bwatson\s+farley\b",
    r"\bmondaq\b",
    r"\bmordor\b",
    r"\breuters\b",
    r"\bnikkei\b",
    r"\boffshore[- ]energy\b",
    r"\bearth\s+journalism\b",
]

_PRIMARY_RES = [re.compile(p, re.IGNORECASE) for p in _PRIMARY_PATTERNS]
_SECONDARY_RES = [re.compile(p, re.IGNORECASE) for p in _SECONDARY_PATTERNS]


def classify_source_tier(ref: str) -> str:
    """Classify a source reference string as primary, secondary, or tertiary."""
    if not ref or ref.strip().lower() in _EMPTY_MARKERS:
        return "tertiary"
    for pat in _PRIMARY_RES:
        if pat.search(ref):
            return "primary"
    for pat in _SECONDARY_RES:
        if pat.search(ref):
            return "secondary"
    return "tertiary"


def detect_citation_style(source_cells: list[str]) -> str:
    """Detect whether source cells use key-ref or inline-ref citation style.

    Key-ref: cells contain short codes like B01, S1, [B05], [S10].
    Inline-ref: cells contain descriptive text like "EVN AR2023 p.44".

    Detection: if >50% of non-empty source cells match a short-code pattern,
    the run is key-ref.
    """
    non_empty = [c for c in source_cells if c.strip().lower() not in _EMPTY_MARKERS]
    if not non_empty:
        return "inline-ref"
    key_count = sum(1 for c in non_empty if _KEY_REF_CELL_RE.match(c))
    if key_count / len(non_empty) > 0.5:
        return "key-ref"
    return "inline-ref"


def _is_empty(cell: str) -> bool:
    """Check if a cell is empty/null."""
    return cell.strip().lower() in _EMPTY_MARKERS


def _is_notfound(cell: str) -> bool:
    """Check if a cell indicates source not found."""
    lower = cell.strip().lower()
    return any(pat in lower for pat in _NOTFOUND_PATTERNS)


def _find_source_columns(header_cells: list[str]) -> dict[str, int]:
    """Find Source 1, Source 2, and Notes column indices in the header."""
    result: dict[str, int] = {}
    for i, cell in enumerate(header_cells):
        c = cell.strip().lower()
        if c in ("source 1", "src 1", "s1"):
            result["src1"] = i
        elif c in ("source 2", "src 2", "s2"):
            result["src2"] = i
        elif c == "notes":
            result["notes"] = i
    return result


def _parse_table_rows(lines: list[str]) -> tuple[list[str], list[list[str]]]:
    """Extract header and data rows from markdown pipe tables.

    Returns (header_cells, data_rows) where data_rows is a list of cell lists.
    Skips separator rows (containing only |, -, :, spaces).
    """
    header_cells: list[str] = []
    data_rows: list[list[str]] = []
    found_header = False
    separator_re = re.compile(r"^[\s|:\-]+$")

    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if separator_re.match(stripped):
            continue

        cells = [c.strip() for c in stripped.split("|")]
        # Remove empty first/last from leading/trailing |
        if cells and cells[0] == "":
            cells = cells[1:]
        if cells and cells[-1] == "":
            cells = cells[:-1]

        if not found_header:
            # Look for a header containing BOTH Source 1 AND Source 2 columns
            # (a two-column source key lookup table has only "S1" as data, not header)
            lower_cells = [c.lower() for c in cells]
            has_src1 = any(lc in ("source 1", "src 1", "s1") for lc in lower_cells)
            has_src2 = any(lc in ("source 2", "src 2", "s2") for lc in lower_cells)
            # Require both Source columns and at least 8 columns (plant table)
            if has_src1 and has_src2 and len(cells) >= 8:
                header_cells = cells
                found_header = True
            continue

        # Skip repeated header rows from subsection tables
        lower_cells = [c.lower() for c in cells]
        is_repeated_header = any(
            lc in ("source 1", "source 2", "src 1", "src 2", "s1", "s2") for lc in lower_cells
        )
        if not is_repeated_header:
            data_rows.append(cells)

    return header_cells, data_rows


def _find_bib_section(text: str) -> str:
    """Extract the bibliography/references section text."""
    lines = text.split("\n")
    bib_start = None
    bib_header_re = re.compile(
        r"^#{1,4}\s+.*(?:bibliography|references|annotated\s+bibliography)",
        re.IGNORECASE,
    )

    for i, line in enumerate(lines):
        if bib_header_re.match(line.strip()):
            bib_start = i
            break

    if bib_start is None:
        return ""

    # Find the end: next section header at same or higher level, or EOF
    header_level = len(lines[bib_start].split()[0])  # count '#' chars
    bib_lines = [lines[bib_start]]
    for line in lines[bib_start + 1 :]:
        stripped = line.strip()
        if stripped.startswith("#"):
            level = len(stripped.split()[0])
            if level <= header_level:
                break
        bib_lines.append(line)

    return "\n".join(bib_lines)


def _count_bib_entries(bib_text: str) -> int:
    """Count bibliography entries in various formats."""
    if not bib_text.strip():
        return 0

    count = 0
    lines = bib_text.split("\n")

    # Format 1: Table rows (|Code|Citation|URL|...)
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            # Skip header and separator rows
            if re.match(r"^[\s|:\-]+$", stripped):
                continue
            cells = [c.strip() for c in stripped.split("|") if c.strip()]
            if not cells:
                continue
            # Check if first cell looks like a bib key
            first = cells[0]
            if re.match(r"^\[?[A-Z]\d{1,3}\]?$", first):
                count += 1
                continue

    if count > 0:
        return count

    # Format 2: Numbered list entries (1. **Title**...)
    numbered_re = re.compile(r"^\d+\.\s+\*\*")
    for line in lines:
        if numbered_re.match(line.strip()):
            count += 1

    if count > 0:
        return count

    # Format 3: Bold-keyed entries (**[S01]...**)
    keyed_re = re.compile(r"^\*\*\[?[A-Z]\d{1,3}\]?")
    for line in lines:
        if keyed_re.match(line.strip()):
            count += 1

    return count


def _classify_bib_entries(bib_text: str) -> int:
    """Count primary-source entries in the bibliography section."""
    if not bib_text.strip():
        return 0

    primary_count = 0
    lines = bib_text.split("\n")

    # For table-format bibliographies
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        if re.match(r"^[\s|:\-]+$", stripped):
            continue
        # Classify the whole line
        if classify_source_tier(stripped) == "primary":
            primary_count += 1

    if primary_count > 0:
        return primary_count

    # For list-format: check each entry (paragraph block starting with number or key)
    current_entry: list[str] = []
    for line in lines:
        stripped = line.strip()
        is_entry_start = bool(
            re.match(r"^\d+\.\s+\*\*", stripped) or re.match(r"^\*\*\[?[A-Z]\d{1,3}\]?", stripped)
        )
        if is_entry_start:
            if current_entry:
                entry_text = " ".join(current_entry)
                if classify_source_tier(entry_text) == "primary":
                    primary_count += 1
            current_entry = [stripped]
        elif current_entry and stripped:
            current_entry.append(stripped)

    # Last entry
    if current_entry:
        entry_text = " ".join(current_entry)
        if classify_source_tier(entry_text) == "primary":
            primary_count += 1

    return primary_count


def _resolve_key_ref(cell: str, bib_text: str) -> bool | None:
    """Check if a key reference (e.g. B05, S10) appears in the bibliography.

    Returns True if found, False if not found, None if no bibliography.
    """
    if not bib_text.strip():
        return None
    # Extract the key code from the cell
    match = re.search(r"\[?([A-Z]\d{1,3})\]?", cell)
    if not match:
        return None
    key = match.group(1)
    # Check if this key appears in the bibliography section
    # Look for it in brackets or as a standalone entry
    return bool(re.search(rf"\b{re.escape(key)}\b", bib_text))


def parse_md(path: Path) -> dict:
    """Parse a single Exp2 markdown narrative and extract bib quality metrics.

    Returns a dict with fields matching the CSV schema.
    """
    if not path.exists() or path.stat().st_size == 0:
        return {
            "n_rows": 0,
            "src1_empty": 0,
            "src1_notfound": 0,
            "src1_present": 0,
            "src1_valid": None,
            "src1_primary": 0,
            "src2_empty": 0,
            "src2_notfound": 0,
            "src2_present": 0,
            "src2_valid": None,
            "src2_primary": 0,
            "notes_empty": 0,
            "notes_notfound": 0,
            "notes_present": 0,
            "bib_entries": 0,
            "bib_valid": None,
            "bib_primary": 0,
            "citation_style": "none",
        }

    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.split("\n")

    header_cells, data_rows = _parse_table_rows(lines)

    if not header_cells or not data_rows:
        return {
            "n_rows": 0,
            "src1_empty": 0,
            "src1_notfound": 0,
            "src1_present": 0,
            "src1_valid": None,
            "src1_primary": 0,
            "src2_empty": 0,
            "src2_notfound": 0,
            "src2_present": 0,
            "src2_valid": None,
            "src2_primary": 0,
            "notes_empty": 0,
            "notes_notfound": 0,
            "notes_present": 0,
            "bib_entries": 0,
            "bib_valid": None,
            "bib_primary": 0,
            "citation_style": "none",
        }

    col_idx = _find_source_columns(header_cells)

    # Collect all source cells for citation style detection
    all_source_cells: list[str] = []
    for row in data_rows:
        for col_key in ("src1", "src2"):
            idx = col_idx.get(col_key)
            if idx is not None and idx < len(row):
                all_source_cells.append(row[idx])

    citation_style = detect_citation_style(all_source_cells)
    bib_text = _find_bib_section(text)
    bib_entries = _count_bib_entries(bib_text)
    bib_primary = _classify_bib_entries(bib_text)

    n_rows = len(data_rows)
    metrics: dict[str, int | None] = {
        "n_rows": n_rows,
        "src1_empty": 0,
        "src1_notfound": 0,
        "src1_present": 0,
        "src1_valid": 0 if citation_style == "key-ref" else None,
        "src1_primary": 0,
        "src2_empty": 0,
        "src2_notfound": 0,
        "src2_present": 0,
        "src2_valid": 0 if citation_style == "key-ref" else None,
        "src2_primary": 0,
        "notes_empty": 0,
        "notes_notfound": 0,
        "notes_present": 0,
    }

    for row in data_rows:
        for prefix, col_key in [("src1", "src1"), ("src2", "src2"), ("notes", "notes")]:
            idx = col_idx.get(col_key)
            if idx is None or idx >= len(row):
                metrics[f"{prefix}_empty"] += 1  # type: ignore[operator]
                continue

            cell = row[idx]

            if _is_empty(cell):
                metrics[f"{prefix}_empty"] += 1  # type: ignore[operator]
            elif _is_notfound(cell):
                metrics[f"{prefix}_notfound"] += 1  # type: ignore[operator]
            else:
                metrics[f"{prefix}_present"] += 1  # type: ignore[operator]

                # For src1/src2 (not notes), check validity and primary
                if prefix in ("src1", "src2"):
                    if citation_style == "key-ref":
                        valid = _resolve_key_ref(cell, bib_text)
                        if valid:
                            metrics[f"{prefix}_valid"] += 1  # type: ignore[operator]
                    # Classify tier: for key-ref, look up bib; for inline-ref, use cell
                    if citation_style == "key-ref":
                        # Look up the full bib entry text for classification
                        match = re.search(r"\[?([A-Z]\d{1,3})\]?", cell)
                        if match:
                            key = match.group(1)
                            # Find the bib entry line
                            for bib_line in bib_text.split("\n"):
                                if re.search(rf"\b{re.escape(key)}\b", bib_line):
                                    if classify_source_tier(bib_line) == "primary":
                                        metrics[f"{prefix}_primary"] += 1  # type: ignore[operator]
                                    break
                    else:
                        if classify_source_tier(cell) == "primary":
                            metrics[f"{prefix}_primary"] += 1  # type: ignore[operator]

    return {
        **metrics,
        "bib_entries": bib_entries,
        "bib_valid": None,  # Only populated with --validate-urls
        "bib_primary": bib_primary,
        "citation_style": citation_style,
    }


_FIELDS = [
    "agent",
    "arm",
    "run",
    "n_rows",
    "src1_empty",
    "src1_notfound",
    "src1_present",
    "src1_valid",
    "src1_primary",
    "src2_empty",
    "src2_notfound",
    "src2_present",
    "src2_valid",
    "src2_primary",
    "notes_empty",
    "notes_notfound",
    "notes_present",
    "bib_entries",
    "bib_valid",
    "bib_primary",
    "citation_style",
]


def build_bib_quality_csv(naive_dir: Path, optimised_dir: Path) -> list[dict]:
    """Parse all markdown files and return flat rows for CSV."""
    rows: list[dict] = []
    for arm_dir, arm_label in [
        (naive_dir, "naive"),
        (optimised_dir, "optimised"),
    ]:
        for md_path in sorted(arm_dir.glob("*.md")):
            m = _RUN_RE.match(md_path.name)
            if not m:
                continue
            agent, run_str = m.group(1), m.group(2)
            run = int(run_str)

            log.info("Parsing %s/%s (arm=%s)", agent, md_path.name, arm_label)
            metrics = parse_md(md_path)

            rows.append({"agent": agent, "arm": arm_label, "run": run, **metrics})

    rows.sort(key=lambda r: (r["arm"], r["agent"], r["run"]))
    return rows


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Extract bibliography quality metrics from Exp2 narratives"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write tab_exp2_bib_quality.csv",
    )
    parser.add_argument("--naive-dir", default=str(_DEFAULT_NAIVE_DIR))
    parser.add_argument("--optimised-dir", default=str(_DEFAULT_OPTIMISED_DIR))
    parser.add_argument(
        "--validate-urls",
        action="store_true",
        help="Check bibliography URLs for HTTP 200 (slow, off by default)",
    )
    args = parser.parse_args(argv)

    rows = build_bib_quality_csv(Path(args.naive_dir), Path(args.optimised_dir))

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    log.info("Wrote %d rows to %s", len(rows), out)


if __name__ == "__main__":
    main()
