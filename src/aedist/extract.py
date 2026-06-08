"""Extract CSV tables from LLM JSON responses.

Pipeline phase: P2 (score & consolidate) — invoked by experiments/derived/score.mk.

Each JSON file contains raw assistant text which usually embeds a CSV inside
Markdown code fences.  This script extracts that CSV, canonicalizes the
columns, and writes a clean comma-delimited CSV so it can be evaluated.

Usage:
  python -m aedist.extract --input outputs/direct_extract --output outputs/direct_extract
"""

import argparse
import csv
import enum
import io
import json
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from .harness import iter_model_replies
from .util import parse_number, strip_diacritics

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
    # Use \r?\n to handle both LF and CRLF line endings.
    return [
        m.group(1).replace("\r", "")
        for m in re.finditer(
            r"```(?:csv)?\s*\r?\n(.*?)\r?\n```", text, flags=re.IGNORECASE | re.DOTALL
        )
    ]


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


def _extract_pipe_tables(text: str) -> list[str]:
    """Extract all Markdown pipe tables from *text* as CSV strings.

    Splits on non-pipe gaps so that multiple tables in one response are
    returned as separate candidates, each scored independently.
    """
    lines = text.splitlines()
    tables: list[str] = []
    current: list[str] = []
    ncols: int | None = None

    def _flush() -> None:
        if len(current) >= 2:
            tables.append("\n".join(current))
        current.clear()

    for ln in lines:
        stripped = ln.strip()
        # Some models (observed in streaming anthropic output) emit a reasoning
        # preamble glued onto the same physical line as the table header, e.g.
        # "Let me search.| Name | Fuel |". The leading prose adds a phantom
        # first cell to the header, so every data row is later dropped as a
        # column-count mismatch. A genuine pipe-table row opens with `|`; when a
        # line ends with `|` but does not start with one, the text before the
        # first `|` is a glued prefix — slice it off so cell counts align.
        if stripped.endswith("|") and not stripped.startswith("|") and stripped.count("|") >= 3:
            stripped = stripped[stripped.index("|") :]
        if "|" in stripped and stripped.count("|") >= 3:
            if re.match(r"^\|?[\s\-:|]+\|?$", stripped):
                continue  # skip separator rows
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if ncols is None or not current:
                ncols = len(cells)
                current.clear()
            elif len(cells) != ncols:
                continue  # skip mismatched rows
            current.append(",".join(f'"{c}"' for c in cells))
        elif current and "|" in stripped and stripped.count("|") == 2:
            # Single-cell row inside a table — typically a markdown section
            # divider like `| **Coal-Fired Power Plants** |`. Skip it
            # silently without flushing so the table stays cohesive across
            # sections (observed empirically in qwen3-max-thinking output).
            continue
        else:
            if current:
                _flush()
                ncols = None

    _flush()
    return tables


def _is_inventory_header(header_line: str) -> bool:
    """Return True when a CSV header line looks like the plant inventory table.

    Statistical recap tables (for example `fuel,capacity`) must not be merged
    into inventory candidates.
    """
    try:
        header_cells = next(csv.reader([header_line]))
    except Exception:
        return False

    canonical = {map_header_to_canonical(norm_header(cell)) for cell in header_cells}
    canonical.discard(None)

    # Inventory table must have a plant-name column and enough plant-attribute
    # columns to distinguish it from recap/statistical tables.
    if "name" not in canonical:
        return False
    attribute_hits = len(canonical & {"fuel", "status", "cod", "province", "capacity_mwe"})
    return attribute_hits >= 2


def _merge_pipe_table_candidates(tables: list[str]) -> str | None:
    """Merge split pipe-table candidates that share the same header row.

    Some model outputs split one logical plant table into multiple markdown
    subtables with repeated headers. Group by header and merge rows for the
    largest group so downstream parsing/evaluation sees a single inventory.
    """
    if len(tables) < 2:
        return None

    groups: dict[str, list[str]] = {}
    for table in tables:
        lines = [ln for ln in table.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        header = lines[0]
        if not _is_inventory_header(header):
            continue
        rows = lines[1:]
        groups.setdefault(header, []).extend(rows)

    if not groups:
        return None

    best_header = max(groups.keys(), key=lambda h: len(groups[h]))
    seen: set[str] = set()
    merged_rows: list[str] = []
    for row in groups[best_header]:
        if row in seen:
            continue
        seen.add(row)
        merged_rows.append(row)

    if len(merged_rows) < 2:
        return None
    return "\n".join([best_header, *merged_rows])


def _headers_compatible(h1: str, h2: str) -> bool:
    """Return True when two CSV header lines share ≥2 identical canonical column names.

    This detects tables with the same logical schema expressed with slightly
    different column labels (e.g. "Units × MW" vs "Technology" columns added
    or dropped between fuel sub-tables in the same response).
    """
    try:
        cells1 = next(csv.reader([h1]))
        cells2 = next(csv.reader([h2]))
    except Exception:
        return False
    norms1 = {map_header_to_canonical(norm_header(c)) for c in cells1}
    norms2 = {map_header_to_canonical(norm_header(c)) for c in cells2}
    norms1.discard(None)
    norms2.discard(None)
    return len(norms1 & norms2) >= 2


def _norm_plant_name(name: str) -> str:
    """Normalise a plant name for deduplication: lowercase, strip diacritics."""
    import unicodedata

    nfd = unicodedata.normalize("NFKD", name.strip().lower())
    return "".join(c for c in nfd if not unicodedata.combining(c))


def merge_fragmented_tables(text: str, tables: list[str]) -> str | None:
    """Merge plant-inventory sub-tables that are fragments of one logical table.

    Fragmentation heuristic: two or more inventory tables within 50 source
    lines of each other that share the same column count **and** have
    compatible headers (≥2 identical normalised canonical column names) are
    treated as fuel-split fragments and concatenated.

    Data rows are deduplicated by normalised plant name (case-insensitive,
    diacritics stripped via NFKD decomposition) so that repeated header rows
    and copy-pasted plants do not inflate counts.

    Returns the merged CSV string for the largest compatible group, or None
    when no multi-table group is found.
    """
    if len(tables) < 2:
        return None

    # Locate each table's start line in the source text.
    source_lines = text.splitlines()
    table_starts: list[int] = []
    table_ends: list[int] = []
    for tbl in tables:
        first_row = tbl.splitlines()[0] if tbl.strip() else ""
        # Recover the original pipe-row text from the first CSV row of the table.
        # The CSV row was built as `",".join(f'"{c}"' for c in cells)`, so we
        # can extract the cell content to search for it in the source.
        try:
            first_cells = next(csv.reader([first_row]))
        except Exception:
            first_cells = []
        # Search for the source line containing the first cell of the header.
        anchor = first_cells[0] if first_cells else ""
        start = 0
        for i, ln in enumerate(source_lines):
            if anchor and anchor in ln and "|" in ln:
                start = i
                break
        tbl_line_count = len(tbl.splitlines())
        table_starts.append(start)
        table_ends.append(start + tbl_line_count)

    # Filter to inventory tables only.
    inv_indices: list[int] = []
    for idx, tbl in enumerate(tables):
        lines = [ln for ln in tbl.splitlines() if ln.strip()]
        if len(lines) >= 2 and _is_inventory_header(lines[0]):
            inv_indices.append(idx)

    if len(inv_indices) < 2:
        return None

    # Group inventory tables into compatible clusters using proximity + schema.
    # A greedy chain: seed from the largest inventory table, absorb neighbours.
    def _ncols(tbl: str) -> int:
        try:
            return len(next(csv.reader([tbl.splitlines()[0]])))
        except Exception:
            return 0

    # Build proximity + compatibility graph edges.
    clusters: list[list[int]] = []
    used: set[int] = set()

    # Sort inv_indices by source position so we can walk forward.
    inv_indices_sorted = sorted(inv_indices, key=lambda i: table_starts[i])

    for i_pos, i in enumerate(inv_indices_sorted):
        if i in used:
            continue
        cluster = [i]
        used.add(i)
        cluster_end = table_ends[i]
        cluster_header = tables[i].splitlines()[0] if tables[i].strip() else ""
        cluster_ncols = _ncols(tables[i])

        for j in inv_indices_sorted[i_pos + 1 :]:
            if j in used:
                continue
            gap = table_starts[j] - cluster_end
            if gap > 50:
                break  # sorted by start; no further table can be close enough
            j_header = tables[j].splitlines()[0] if tables[j].strip() else ""
            j_ncols = _ncols(tables[j])
            if j_ncols == cluster_ncols and _headers_compatible(cluster_header, j_header):
                cluster.append(j)
                used.add(j)
                cluster_end = max(cluster_end, table_ends[j])

        clusters.append(cluster)

    # Pick the largest cluster by total data-row count.
    def _row_count(cluster: list[int]) -> int:
        return sum(len(tables[i].splitlines()) - 1 for i in cluster)

    multi_clusters = [c for c in clusters if len(c) > 1]
    if not multi_clusters:
        return None

    best_cluster = max(multi_clusters, key=_row_count)

    # Merge: use header from the largest table in the cluster; concatenate
    # data rows; deduplicate by normalised plant name.
    best_idx = max(best_cluster, key=lambda i: len(tables[i].splitlines()))
    merged_header = tables[best_idx].splitlines()[0]

    seen_names: set[str] = set()
    merged_rows: list[str] = []
    for idx in best_cluster:
        tbl_lines = [ln for ln in tables[idx].splitlines() if ln.strip()]
        for row in tbl_lines[1:]:  # skip header
            try:
                cells = next(csv.reader([row]))
            except Exception:
                merged_rows.append(row)
                continue
            # First non-empty cell that maps to "name" in any position
            name_val = ""
            try:
                hdr_cells = next(csv.reader([tables[idx].splitlines()[0]]))
            except Exception:
                hdr_cells = []
            for ci, hc in enumerate(hdr_cells):
                if map_header_to_canonical(norm_header(hc)) == "name" and ci < len(cells):
                    name_val = cells[ci]
                    break
            key = _norm_plant_name(name_val) if name_val else row
            if key in seen_names:
                continue
            seen_names.add(key)
            merged_rows.append(row)

    if len(merged_rows) < 2:
        return None
    return "\n".join([merged_header, *merged_rows])


def fallback_extract_inline_csv(text: str) -> str | None:
    """Extract a CSV-looking region when there are no fenced blocks."""
    lines = text.splitlines()
    # Find likely header: require ≥2 delimiters AND a header keyword
    # to avoid matching prose sentences like "tracks fuel, capacity, status".
    header_idx = None
    for i, ln in enumerate(lines):
        stripped = ln.strip()
        if not stripped:
            continue
        low = stripped.lower()
        has_delimiters = (
            stripped.count(",") >= 2 or stripped.count(";") >= 2 or stripped.count("\t") >= 2
        )
        if has_delimiters and any(kw in low for kw in _HEADER_KEYWORDS):
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
    h = strip_diacritics(h.strip()).lower()
    h = re.sub(r"\([^)]*\)", "", h)  # drop parenthesized units
    h = re.sub(r"[^a-z0-9]+", "_", h)
    return h.strip("_")


_CANON = [
    "name",
    "fuel",
    "status",
    "status_as_of",
    "cod",
    "province",
    "capacity_mwe",
    "confidence",
    "source_1",
    "source_2",
    "note",
]


def map_header_to_canonical(norm: str) -> str | None:
    if norm in {
        "name",
        "name_vi",
        "name_en",
        "plant",
        "plant_name",
        "plantname",
        "power_plant",
        "power_plant_name",
        "project",
        "project_name",
        "plant_name_project",
        # SOTA arm2/arm4 runs label the plant-name column "Asset" / "Asset Name"
        # (sometimes with a "(VN / EN)" or "(Vietnamese)/(English)" suffix that
        # norm_header strips). These are the same plant-name column.
        "asset",
        "asset_name",
        "assetname",
    }:
        return "name"
    if norm in {"fuel", "fuel_type", "fueltype", "fuel_source", "source_fuel"}:
        return "fuel"
    if norm in {
        "status",
        "current_status",
        "current_status_resolution",
        "status_resolution",
        "construction_stage",
        "stage",
        "constructionstage",
        "cod_status",
        "status_cod",
        "cod_or_status",
    }:
        return "status"
    if norm in {
        "status_as_of",
        "status_as_of_date",
        "as_of",
        "as_of_date",
        "freshness_date",
    }:
        return "status_as_of"
    if norm in {"cod", "connection_date", "date", "connectiondate"}:
        return "cod"
    if norm in {"province", "location"}:
        return "province"
    if norm in {
        "capacity_mwe",
        "capacity",
        "orig_cap",
        "orig_capacity",
        "original_cap",
        "original_capacity",
        "generation_capacity",
        "installed_capacity",
        "installed_capacity_mwe",
        "total_mw",
        "total_mwe",
        "net_mw",
        "net_mwe",
        "gross_mw",
        "gross_mwe",
        "capacity_mw",
        "capacity_mwe_",
        "capacity_mwe__",
    }:
        return "capacity_mwe"
    # Common variants that still normalize with parentheses removed
    if norm.startswith("capacity"):
        return "capacity_mwe"
    # Provenance columns
    if norm in {
        "confidence",
        "confidence_level",
        "evidence_confidence",
        "conf_provenance",
        "confidence_provenance",
    }:
        return "confidence"
    if norm in {"source_1", "source", "reference", "citation"}:
        return "source_1"
    if norm in {"source_2", "reference_2", "citation_2"}:
        return "source_2"
    if norm in {"note", "notes", "comment", "comments"}:
        return "note"
    return None


def parse_capacity_value(cell: str) -> str:
    value = (cell or "").strip()
    parsed = parse_number(value, integer_expected=True)
    if parsed is None:
        match = re.search(r"[~≈≤≥<>]?\s*\d[\d,\.\s]*", value)
        if match:
            parsed = parse_number(match.group(0).lstrip("~≈≤≥<> "), integer_expected=True)
    return str(parsed) if parsed is not None else "0"


class ExtractStatus(enum.Enum):
    WROTE = "wrote"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class ExtractResult:
    status: ExtractStatus
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
                cell = parse_capacity_value(cell)
            out_row.append(cell)
        # Skip completely empty lines (shouldn't happen, but safe)
        if not out_row[0]:
            continue
        writer.writerow(out_row)
    return out_buf.getvalue()


def count_best_table_rows(text: str) -> int:
    """Return data-row count for the best plant-table candidate in *text*.

    This mirrors the extraction path used by `extract_one()`: score all pipe-table
    candidates, select the best one, canonicalize it, then count resulting data
    rows. Summary tables should therefore not inflate the count when a larger,
    more plant-like inventory table is present in the same markdown response.
    """
    pipe_candidates = _extract_pipe_tables(text)
    candidates = list(pipe_candidates)
    merged_pipe = _merge_pipe_table_candidates(pipe_candidates)
    if merged_pipe:
        candidates.append(merged_pipe)
    fragmented = merge_fragmented_tables(text, pipe_candidates)
    if fragmented:
        candidates.append(fragmented)
    if not candidates:
        return 0

    best = max(candidates, key=score_csv_like_block)
    try:
        canonical_csv = parse_and_canonicalize(best)
    except Exception:
        return 0

    row_count = sum(1 for line in canonical_csv.splitlines()[1:] if line.strip())
    return row_count


def extract_one(json_path: Path, output_dir: Path, overwrite: bool) -> ExtractResult:
    out_path = output_dir / f"{json_path.stem}.csv"
    if out_path.exists() and not overwrite:
        return ExtractResult(ExtractStatus.SKIPPED, out_path, f"{json_path.name}: skip (exists)")

    try:
        record = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as e:
        return ExtractResult(ExtractStatus.FAILED, None, f"{json_path.name}: invalid JSON ({e})")

    response = record.get("response")
    # Handle multiturn JSON format: join all assistant turns so we score
    # every table across the conversation, not just the last turn.
    if (not response or not isinstance(response, str)) and "turns" in record:
        turns = record["turns"]
        assistant_turns = [t for t in turns if t.get("role") == "assistant"]
        if assistant_turns:
            response = "\n".join(t.get("content", "") for t in assistant_turns)
    if not isinstance(response, str) or not response.strip():
        return ExtractResult(ExtractStatus.FAILED, None, f"{json_path.name}: no response text")

    blocks = extract_fenced_blocks(response)
    pipe_candidates = _extract_pipe_tables(response)
    candidates = blocks[:]
    candidates.extend(pipe_candidates)
    merged_pipe = _merge_pipe_table_candidates(pipe_candidates)
    merged_subtables = merged_pipe is not None
    if merged_pipe:
        candidates.append(merged_pipe)
    fragmented = merge_fragmented_tables(response, pipe_candidates)
    if fragmented:
        if not merged_subtables:
            merged_subtables = True
        candidates.append(fragmented)
    # Only try inline fallback when no fenced blocks or pipe tables found
    if not candidates:
        inline = fallback_extract_inline_csv(response)
        if inline:
            candidates.append(inline)

    if not candidates:
        return ExtractResult(ExtractStatus.FAILED, None, f"{json_path.name}: no CSV found")

    # On tie max() picks the first candidate — checked 246 files, 0 ties (2026-04).
    best = max(candidates, key=score_csv_like_block)
    try:
        canonical_csv = parse_and_canonicalize(best)
    except Exception as e:
        return ExtractResult(
            ExtractStatus.FAILED, None, f"{json_path.name}: CSV parse failed ({e})"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(canonical_csv, encoding="utf-8")
    merge_note = " (merged split subtables)" if merged_subtables else ""
    return ExtractResult(
        ExtractStatus.WROTE,
        out_path,
        f"{json_path.name}: wrote {out_path.name}{merge_note}",
    )


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Extract CSV from LLM JSON outputs")
    parser.add_argument(
        "--input",
        required=True,
        help="Directory containing JSON outputs",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Directory to write extracted CSV files into",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing CSV files")
    args = parser.parse_args(argv)

    input_dir = Path(args.input)
    output_dir = Path(args.output)

    if not input_dir.exists() or not input_dir.is_dir():
        raise SystemExit(f"Input dir not found: {input_dir}")

    json_files = list(iter_model_replies(input_dir))
    if not json_files:
        raise SystemExit(f"No JSON files in: {input_dir}")

    wrote = 0
    failed = 0
    skipped = 0
    for jf in json_files:
        res = extract_one(jf, output_dir, overwrite=args.overwrite)
        log.info(res.message)
        if res.status is ExtractStatus.WROTE:
            wrote += 1
        elif res.status is ExtractStatus.SKIPPED:
            skipped += 1
        else:
            failed += 1

    log.info("Done. wrote=%d skipped=%d failed=%d (from %s)", wrote, skipped, failed, input_dir)
    if wrote == 0 and skipped == 0 and failed > 0:
        sys.exit(2)


if __name__ == "__main__":
    main()
