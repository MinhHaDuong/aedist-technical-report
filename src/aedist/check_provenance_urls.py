"""Automated provenance spot-check — verify N=10 source URLs per run.

Pipeline phase: P2 companion (on-demand only) — not wired into the default
Makefile/report DAG to avoid network dependencies in clean-room builds.

For each run, samples N=10 matched plant rows and verifies whether Source 1
is (a) a real URL that resolves and (b) a page whose text mentions the plant
by name and (plausibly) the claimed capacity.

Algorithm:
1. Parse the run's .md file to extract the plant table and bibliography.
2. For a row with a citation-key Source 1 (e.g. [1], [23]), resolve the key
   against the bibliography to obtain a full URL.
3. HTTP GET the URL (10s timeout, single retry on network error).
   Classify result: resolved / unresolved / no-url / no-source.
4. If resolved, search page text for the plant's name (Vietnamese or English,
   case-insensitive). If found, extract capacity figures and normalise to MWe
   (GW × 1000, MW as-is); if any found capacity is within ±10% of the claimed
   value: PASS.
5. Emit per-row result and aggregate: provenance_score = n_pass / n_sampled.

Design choice — row selection:
  Rows are sampled from those whose Source 1 is not "not found" / empty
  (i.e. rows that have a non-trivial citation to check). This directly tests
  the verifiable fraction of the run's citations without requiring per-plant
  match metadata from sota_cross_eval.csv.  The caller may optionally restrict
  to a list of plant names (from matched rows in the cross-eval CSV) via the
  --plant-names argument.

Usage:
    python -m aedist.check_provenance_urls \\
        --md experiments/derived/arm1_flat/anthropic_run01.md \\
        --output derived/provenance_sample_anthropic_run01.csv

    # Limit to N=5 samples, dry-run (no HTTP):
    python -m aedist.check_provenance_urls \\
        --md experiments/derived/arm1_flat/anthropic_run01.md \\
        --n 5 --dry-run

    # Restrict to matched plants from cross-eval:
    python -m aedist.check_provenance_urls \\
        --md experiments/derived/arm1_flat/anthropic_run01.md \\
        --cross-eval experiments/derived/sota_cross_eval.csv \\
        --arm naive --model claude-opus-4-6 --run 1
"""

import argparse
import csv
import json
import logging
import random
import re
import time
from pathlib import Path

import httpx

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_N = 10
_HTTP_TIMEOUT = 10.0  # seconds
_CAPACITY_TOLERANCE = 0.10  # ±10%

# Patterns that indicate no useful source was cited
_EMPTY_MARKERS: frozenset[str] = frozenset({"", "—", "–", "-", "n/a", "na", "none"})
_NOTFOUND_PATTERNS = [
    "not found",
    "not available",
    "unable to verify",
    "could not verify",
    "no source",
    "unverified",
]

# Output columns for the provenance sample CSV
_OUT_FIELDNAMES = [
    "plant_name_vi",
    "plant_name_en",
    "claimed_capacity_mwe",
    "source_1_raw",
    "source_1_url",
    "url_status",
    "name_found",
    "capacity_match",
    "verdict",
    "detail",
]

# ---------------------------------------------------------------------------
# Markdown parsing helpers
# ---------------------------------------------------------------------------

_SEPARATOR_RE = re.compile(r"^[\s|:\-]+$")
# Bibliography entry: **[N]** … URL: `https://...`
_BIB_ENTRY_RE = re.compile(r"^\*\*\[(\d+)\]\*\*")
_BIB_URL_RE = re.compile(r"URL:\s+`(https?://[^`]+)`")
# Source 1/2 cell containing only a citation key like [1] or [20]
_CITATION_KEY_RE = re.compile(r"^\s*\[(\d+)\]\s*$")
# URL embedded directly in a cell (some runs use markdown links)
_INLINE_URL_RE = re.compile(r"https?://[^\s)>\]]+")
# Capacity figures in MW / GW on a page
_MW_RE = re.compile(r"([\d,\.]+)\s*(?:MW|mw)")
_GW_RE = re.compile(r"([\d,\.]+)\s*(?:GW|gw)")


def _is_empty(cell: str) -> bool:
    return cell.strip().lower() in _EMPTY_MARKERS


def _is_notfound(cell: str) -> bool:
    lower = cell.strip().lower()
    return any(pat in lower for pat in _NOTFOUND_PATTERNS)


def _parse_table(text: str) -> tuple[list[str], list[list[str]]]:
    """Return (header_cells, data_rows) from the pipe table in the markdown.

    Looks for the first table whose header contains both 'Source 1'
    and at least 8 columns (the full plant table).
    """
    lines = text.split("\n")
    header_cells: list[str] = []
    data_rows: list[list[str]] = []
    found_header = False

    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            if found_header and data_rows:
                break  # table ended
            continue
        if _SEPARATOR_RE.match(stripped):
            continue

        cells = [c.strip() for c in stripped.split("|")]
        if cells and cells[0] == "":
            cells = cells[1:]
        if cells and cells[-1] == "":
            cells = cells[:-1]

        if not found_header:
            lower = [c.lower() for c in cells]
            has_src1 = any(c in ("source 1", "src 1") for c in lower)
            if has_src1 and len(cells) >= 8:
                header_cells = cells
                found_header = True
            continue

        # Skip repeated header rows
        lower = [c.lower() for c in cells]
        is_repeated = any(c in ("source 1", "source 2", "src 1", "src 2") for c in lower)
        if not is_repeated:
            data_rows.append(cells)

    return header_cells, data_rows


def _parse_bibliography(text: str) -> dict[str, str]:
    """Return {citation_number_str: url} from the bibliography section.

    Handles the format: **[N]** … URL: `https://...`
    Returns an empty dict when no bibliography section is found.
    Entries without a URL: `...` are excluded.
    """
    result: dict[str, str] = {}
    in_bib = False

    for line in text.split("\n"):
        stripped = line.strip()

        # Detect bib section start
        if not in_bib:
            if re.match(
                r"^#{1,4}\s+.*(?:bibliography|references|annotated\s+bibliography)",
                stripped,
                re.IGNORECASE,
            ):
                in_bib = True
            continue

        m_entry = _BIB_ENTRY_RE.match(stripped)
        if m_entry:
            key = m_entry.group(1)
            m_url = _BIB_URL_RE.search(stripped)
            if m_url:
                result[key] = m_url.group(1)

    return result


def _col_index(header: list[str], *names: str) -> int | None:
    """Return the index of the first header cell matching any of the given names."""
    lower = [c.lower() for c in header]
    for name in names:
        if name.lower() in lower:
            return lower.index(name.lower())
    return None


def _resolve_source_url(cell: str, bib: dict[str, str]) -> str | None:
    """Return the URL for a Source 1 cell, or None if not resolvable.

    - Citation key [N] → look up in bib dict.
    - Inline URL (https://...) → return directly.
    - Anything else (inline text, "not found", empty) → None.
    """
    cell = cell.strip()

    # Citation key form
    m = _CITATION_KEY_RE.match(cell)
    if m:
        return bib.get(m.group(1))  # None if key absent from bib

    # Inline URL in the cell
    m2 = _INLINE_URL_RE.search(cell)
    if m2:
        return m2.group()

    return None


# ---------------------------------------------------------------------------
# HTTP verification
# ---------------------------------------------------------------------------


def _fetch_page(url: str) -> tuple[str, int | None]:
    """Fetch URL and return (page_text, status_code).

    On network error: returns ("", None).
    Retries once on connection error.
    """
    for attempt in range(2):
        try:
            resp = httpx.get(
                url,
                timeout=_HTTP_TIMEOUT,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (research bot; academic use)"},
            )
            return resp.text, resp.status_code
        except (httpx.HTTPError, httpx.InvalidURL) as exc:
            if attempt == 0:
                log.debug("Retry after error on %s: %s", url, exc)
                time.sleep(1)
            else:
                log.debug("Failed to fetch %s: %s", url, exc)
    return "", None


def _name_found(page_text: str, name_vi: str, name_en: str) -> bool:
    """Return True if either plant name appears in the page text."""
    lower = page_text.lower()
    return bool(
        (name_vi and name_vi.lower() in lower)
        or (name_en and name_en.lower() in lower)
    )


def _capacity_matches(page_text: str, claimed_mwe: float) -> bool:
    """Return True if any capacity figure on the page is within ±10% of claimed_mwe."""
    candidates: list[float] = []
    for m in _MW_RE.findall(page_text):
        try:
            candidates.append(float(m.replace(",", "")))
        except ValueError:
            pass
    for m in _GW_RE.findall(page_text):
        try:
            candidates.append(float(m.replace(",", "")) * 1000.0)
        except ValueError:
            pass
    if not candidates:
        return False
    lo = claimed_mwe * (1 - _CAPACITY_TOLERANCE)
    hi = claimed_mwe * (1 + _CAPACITY_TOLERANCE)
    return any(lo <= c <= hi for c in candidates)


# ---------------------------------------------------------------------------
# Per-row verification
# ---------------------------------------------------------------------------


def check_row(
    name_vi: str,
    name_en: str,
    claimed_mwe: float | None,
    source_1_raw: str,
    bib: dict[str, str],
    dry_run: bool = False,
) -> dict:
    """Check one plant row and return a result dict.

    Verdict values: PASS, FAIL, UNRESOLVED, NO_URL, NO_SOURCE.
    """
    url = _resolve_source_url(source_1_raw, bib)

    base = {
        "plant_name_vi": name_vi,
        "plant_name_en": name_en,
        "claimed_capacity_mwe": str(claimed_mwe) if claimed_mwe is not None else "",
        "source_1_raw": source_1_raw,
        "source_1_url": url or "",
        "url_status": "",
        "name_found": "",
        "capacity_match": "",
        "verdict": "",
        "detail": "",
    }

    if _is_notfound(source_1_raw) or _is_empty(source_1_raw):
        base["verdict"] = "NO_SOURCE"
        base["detail"] = "Source 1 is empty or 'not found'"
        return base

    if url is None:
        base["verdict"] = "NO_URL"
        base["detail"] = "Source 1 has no resolvable URL (inline-text citation)"
        return base

    if dry_run:
        base["verdict"] = "DRY_RUN"
        base["detail"] = f"Would fetch: {url}"
        return base

    page_text, status = _fetch_page(url)

    if status is None:
        base["url_status"] = "network_error"
        base["verdict"] = "UNRESOLVED"
        base["detail"] = "Network error fetching URL"
        return base

    base["url_status"] = str(status)

    if status >= 400:
        base["verdict"] = "UNRESOLVED"
        base["detail"] = f"HTTP {status}"
        return base

    # Page resolved — check name
    found = _name_found(page_text, name_vi, name_en)
    base["name_found"] = "yes" if found else "no"

    if not found:
        base["verdict"] = "FAIL"
        base["detail"] = "Page loaded but plant name not found in text"
        return base

    # Name found — check capacity if we have a claimed value
    if claimed_mwe is None or claimed_mwe <= 0:
        base["verdict"] = "PASS"
        base["capacity_match"] = "n/a"
        base["detail"] = "Name found; no claimed capacity to check"
        return base

    cap_match = _capacity_matches(page_text, claimed_mwe)
    base["capacity_match"] = "yes" if cap_match else "no"
    if cap_match:
        base["verdict"] = "PASS"
        base["detail"] = "Name and capacity (±10%) both found on page"
    else:
        base["verdict"] = "FAIL"
        base["detail"] = "Name found but no matching capacity figure on page"

    return base


# ---------------------------------------------------------------------------
# Run-level spot-check
# ---------------------------------------------------------------------------


def _parse_capacity(cell: str) -> float | None:
    """Parse a capacity cell like '1,200' or '~600' to float MWe."""
    cell = cell.strip().lstrip("~≈").replace(",", "")
    try:
        return float(cell)
    except ValueError:
        return None


def _load_matched_plants(
    cross_eval_csv: Path, arm: str, model: str, run: int
) -> set[str] | None:
    """Return the set of English plant names matched for a given run, or None.

    The cross_eval CSV is run-level aggregate (no per-plant matches), so this
    function currently returns None — meaning no filtering is applied and all
    rows with citable sources are eligible for sampling.

    If a per-plant match file becomes available in the future, this is the hook
    to add that filter.
    """
    return None  # no per-plant match data available in sota_cross_eval.csv


def spot_check_run(
    md_path: Path,
    n: int = _DEFAULT_N,
    seed: int = 42,
    dry_run: bool = False,
    plant_names: set[str] | None = None,
) -> dict:
    """Run the provenance spot-check on one run's markdown file.

    Returns a dict with:
      - sampled_rows: list of per-row result dicts
      - n_sampled: actual number of rows checked
      - n_pass: count of PASS verdicts
      - n_fail: count of FAIL verdicts
      - n_unresolved: count of UNRESOLVED verdicts
      - n_no_url: count of NO_URL verdicts
      - n_no_source: count of NO_SOURCE verdicts
      - provenance_score: n_pass / n_sampled (None if n_sampled == 0)
    """
    text = md_path.read_text(encoding="utf-8", errors="replace")
    header_cells, data_rows = _parse_table(text)
    bib = _parse_bibliography(text)

    if not header_cells or not data_rows:
        log.warning("No plant table found in %s", md_path)
        return _empty_result()

    col_name_vi = _col_index(header_cells, "Name (Vietnamese)", "name_vi", "name (vietnamese)")
    col_name_en = _col_index(header_cells, "Name (English)", "name_en", "name (english)")
    col_capacity = _col_index(
        header_cells, "Total MWe", "total_mwe", "capacity_mwe", "capacity"
    )
    col_src1 = _col_index(header_cells, "Source 1", "source 1", "src 1")

    if col_src1 is None:
        log.warning("No 'Source 1' column in %s", md_path)
        return _empty_result()

    def _cell(row: list[str], idx: int | None) -> str:
        if idx is None or idx >= len(row):
            return ""
        return row[idx].strip()

    # Build candidate rows: those with a non-trivial, URL-bearing Source 1
    candidates: list[tuple[str, str, float | None, str]] = []
    for row in data_rows:
        src1 = _cell(row, col_src1)
        if _is_empty(src1) or _is_notfound(src1):
            continue
        name_vi = _cell(row, col_name_vi)
        name_en = _cell(row, col_name_en)

        # Optional filter by matched plant names
        if plant_names is not None and name_en not in plant_names:
            continue

        cap_raw = _cell(row, col_capacity)
        cap = _parse_capacity(cap_raw)
        candidates.append((name_vi, name_en, cap, src1))

    if not candidates:
        log.warning("No citable rows in %s", md_path)
        return _empty_result()

    # Sample
    rng = random.Random(seed)
    sample = rng.sample(candidates, min(n, len(candidates)))

    results: list[dict] = []
    for name_vi, name_en, cap, src1 in sample:
        r = check_row(name_vi, name_en, cap, src1, bib, dry_run=dry_run)
        results.append(r)
        log.info(
            "%s (%s) → %s",
            name_en or name_vi,
            r["source_1_url"] or r["source_1_raw"],
            r["verdict"],
        )

    verdict_counts = {
        "PASS": 0,
        "FAIL": 0,
        "UNRESOLVED": 0,
        "NO_URL": 0,
        "NO_SOURCE": 0,
        "DRY_RUN": 0,
    }
    for r in results:
        verdict_counts[r["verdict"]] = verdict_counts.get(r["verdict"], 0) + 1

    n_sampled = len(results)
    n_pass = verdict_counts["PASS"]
    score = round(n_pass / n_sampled, 3) if n_sampled > 0 else None

    return {
        "n_candidates": len(candidates),
        "n_sampled": n_sampled,
        "n_pass": n_pass,
        "n_fail": verdict_counts["FAIL"],
        "n_unresolved": verdict_counts["UNRESOLVED"],
        "n_no_url": verdict_counts["NO_URL"],
        "n_no_source": verdict_counts["NO_SOURCE"],
        "provenance_score": score,
        "sampled_plants": [r["plant_name_en"] or r["plant_name_vi"] for r in results],
        "rows": results,
    }


def _empty_result() -> dict:
    return {
        "n_candidates": 0,
        "n_sampled": 0,
        "n_pass": 0,
        "n_fail": 0,
        "n_unresolved": 0,
        "n_no_url": 0,
        "n_no_source": 0,
        "provenance_score": None,
        "sampled_plants": [],
        "rows": [],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Provenance spot-check — verify N=10 source URLs for a single run"
    )
    parser.add_argument(
        "--md",
        required=True,
        type=Path,
        help="Path to the run's .md file (plant table + bibliography)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path to write per-row CSV output (default: stdout summary only)",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="Path to write full JSON result",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=_DEFAULT_N,
        help=f"Number of rows to sample (default: {_DEFAULT_N})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for sampling (default: 42)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip HTTP requests; show which URLs would be fetched",
    )
    parser.add_argument(
        "--cross-eval",
        type=Path,
        default=None,
        help=(
            "Path to sota_cross_eval.csv (or sota_cross_eval_view.csv). "
            "Currently reserved for future per-plant match filtering."
        ),
    )
    parser.add_argument("--arm", default=None, help="Arm label (for cross-eval filtering)")
    parser.add_argument("--model", default=None, help="Model ID (for cross-eval filtering)")
    parser.add_argument(
        "--run", type=int, default=None, help="Run index (for cross-eval filtering)"
    )

    args = parser.parse_args(argv)

    if not args.md.exists():
        raise SystemExit(f"Markdown file not found: {args.md}")

    plant_names: set[str] | None = None
    if args.cross_eval and args.arm and args.model and args.run:
        plant_names = _load_matched_plants(args.cross_eval, args.arm, args.model, args.run)

    result = spot_check_run(
        md_path=args.md,
        n=args.n,
        seed=args.seed,
        dry_run=args.dry_run,
        plant_names=plant_names,
    )

    # Print summary
    score_str = (
        f"{result['provenance_score']:.3f}" if result["provenance_score"] is not None else "N/A"
    )
    log.info(
        "\nProvenance spot-check: %s",
        args.md,
    )
    log.info(
        "  Sampled %d/%d candidates | PASS %d | FAIL %d | UNRESOLVED %d | "
        "NO_URL %d | NO_SOURCE %d",
        result["n_sampled"],
        result["n_candidates"],
        result["n_pass"],
        result["n_fail"],
        result["n_unresolved"],
        result["n_no_url"],
        result["n_no_source"],
    )
    log.info("  provenance_score = %s", score_str)

    # Write CSV output
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=_OUT_FIELDNAMES)
            writer.writeheader()
            writer.writerows(result["rows"])
        log.info("Wrote per-row CSV to %s", args.output)

    # Write JSON output
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        payload = {k: v for k, v in result.items() if k != "rows"}
        payload["rows"] = result["rows"]
        args.json_output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        log.info("Wrote JSON result to %s", args.json_output)


if __name__ == "__main__":
    main()
