"""Verify source grounding: check whether LLM citations trace to the RAG corpus.

For each extracted plant with source_1 / source_2 columns, we:
  1. Fuzzy-match the citation text against the 18 corpus filenames.
  2. If a file matches, search it for the plant name.
  3. Report three rates:
     - source_rate:        fraction of plants with any non-empty citation
     - grounding_rate:     fraction of plants whose citation matches a corpus file
     - traceability_rate:  fraction of plants whose citation matches AND the
                           matched file mentions the plant name

This replaces post-hoc LLM verification (ticket 0059 showed 0-10% inter-
verifier agreement).  No API calls required -- everything is local.

Usage:
    python -m aedist.verify_source_grounding \
        --input experiments/outputs/rag_cited \
        --corpus data/rag_corpus \
        --output derived/source_grounding_summary.json
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
from pathlib import Path

from rapidfuzz import fuzz

from .config import VN_THERMAL_PLANTS_RELEASE_CSV

log = logging.getLogger(__name__)

# Minimum fuzzy-match score for citation -> corpus filename
FILENAME_MATCH_THRESHOLD = 70

# Minimum fuzzy-match score for plant name -> file content
PLANT_NAME_MATCH_THRESHOLD = 60


# ---------------------------------------------------------------------------
# Corpus filename normalisation
# ---------------------------------------------------------------------------


def _normalise_filename(name: str) -> str:
    """Strip extension and convert underscores/camelCase to lowercase tokens.

    >>> _normalise_filename("EVN_Annual_Report_2010_2011_CapacitiesTable.md")
    'evn annual report 2010 2011 capacitiestable'
    """
    stem = Path(name).stem
    return stem.replace("_", " ").lower()


def _normalise_citation(text: str) -> str:
    """Normalise a free-text citation for fuzzy matching against filenames.

    Drops page references (p13, pp34-35), parenthesised detail, and
    punctuation noise while keeping the document identity tokens.
    """
    t = text.strip()
    # Remove parenthesised details
    t = re.sub(r"\([^)]*\)", "", t)
    # Remove page references like p13, pp34-35, page 5
    t = re.sub(r"\b(?:pp?\.?\s*\d[\d\-]*)", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\bpage\s+\d+", "", t, flags=re.IGNORECASE)
    # Normalise whitespace
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t


# ---------------------------------------------------------------------------
# Core verification
# ---------------------------------------------------------------------------


def match_citation_to_corpus(
    citation: str,
    corpus_filenames: list[str],
    *,
    threshold: int = FILENAME_MATCH_THRESHOLD,
) -> str | None:
    """Return the best-matching corpus filename, or None if below threshold."""
    if not citation or not citation.strip():
        return None

    norm_cit = _normalise_citation(citation)
    best_score = 0.0
    best_file: str | None = None

    for fname in corpus_filenames:
        norm_fn = _normalise_filename(fname)
        score = fuzz.token_sort_ratio(norm_cit, norm_fn)
        if score > best_score:
            best_score = score
            best_file = fname

    if best_score >= threshold:
        return best_file
    return None


def plant_name_in_file(
    plant_name: str,
    file_content: str,
    *,
    threshold: int = PLANT_NAME_MATCH_THRESHOLD,
) -> bool:
    """Check whether the plant name appears (fuzzily) in the file content.

    We search line-by-line for a partial-ratio match, which catches
    Vietnamese diacritical variants (e.g. "Duyen Hai" vs "Duyên Hải").
    """
    name_lower = plant_name.strip().lower()
    if not name_lower:
        return False

    # Quick exact substring check first (fast path)
    content_lower = file_content.lower()
    if name_lower in content_lower:
        return True

    # Fuzzy search line-by-line
    for line in file_content.split("\n"):
        if fuzz.partial_ratio(name_lower, line.lower()) >= threshold:
            return True

    return False


def _load_reference_names(
    reference_path: Path,
    *,
    name_column: str = "name",
) -> list[str]:
    """Load plant names from a reference CSV."""
    names: list[str] = []
    with open(reference_path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            n = (row.get(name_column) or "").strip()
            if n:
                names.append(n)
    return names


def _name_in_reference(
    plant_name: str,
    reference_names: list[str],
    *,
    threshold: int = FILENAME_MATCH_THRESHOLD,
) -> bool:
    """Check whether *plant_name* fuzzy-matches any name in the reference list."""
    if not plant_name:
        return False
    name_lower = plant_name.strip().lower()
    for ref in reference_names:
        ref_lower = ref.strip().lower()
        if name_lower == ref_lower:
            return True
        if fuzz.token_sort_ratio(name_lower, ref_lower) >= threshold:
            return True
    return False


def verify_source_grounding(
    rows: list[dict],
    corpus_dir: Path,
    *,
    reference_path: Path | None = None,
) -> tuple[list[dict], dict]:
    """Verify source grounding for extracted rows with source_1/source_2 columns.

    Parameters
    ----------
    rows : list[dict]
        CSV row dicts, each with at least 'name' and optionally
        'source_1', 'source_2'.
    corpus_dir : Path
        Directory containing the .md corpus files.
    reference_path : Path | None
        Path to the reference CSV with a ``name`` column.  Defaults to
        ``config.VN_THERMAL_PLANTS_RELEASE_CSV``.

    Returns
    -------
    annotated : list[dict]
        Input rows with added boolean columns:
        source_file_found, source_content_found, source_verified
    summary : dict
        Aggregate metrics: source_rate, grounding_rate, traceability_rate,
        and a 2x2 counts table.
    """
    if reference_path is None:
        reference_path = VN_THERMAL_PLANTS_RELEASE_CSV

    # Load reference names
    if reference_path.is_file():
        reference_names = _load_reference_names(reference_path)
    else:
        log.warning(
            "Reference file not found: %s — in_reference will be False for all", reference_path
        )
        reference_names = []

    # Load corpus
    corpus_files = sorted(f.name for f in corpus_dir.glob("*.md"))
    corpus_contents: dict[str, str] = {}
    for fname in corpus_files:
        corpus_contents[fname] = (corpus_dir / fname).read_text(encoding="utf-8")

    annotated = []
    n_has_source = 0
    n_file_found = 0
    n_content_found = 0
    n_verified = 0

    # 2x2 counters: (traceable, in_reference)
    # "traceable" = source_verified; "in_reference" = plant exists in reference CSV
    counts_2x2 = {"tt": 0, "tf": 0, "ft": 0, "ff": 0}

    for row in rows:
        entry = dict(row)
        name = row.get("name", "").strip()
        s1 = (row.get("source_1") or "").strip()
        s2 = (row.get("source_2") or "").strip()

        has_source = bool(s1 or s2)
        file_found = False
        content_found = False
        matched_file: str | None = None

        # Try source_1 first, then source_2
        for citation in [s1, s2]:
            if not citation:
                continue
            mf = match_citation_to_corpus(citation, corpus_files)
            if mf:
                matched_file = mf
                file_found = True
                # Check if plant name appears in the matched file
                if plant_name_in_file(name, corpus_contents[mf]):
                    content_found = True
                    break  # Fully verified — no need to try next citation
                # File matched but plant not found — continue to next citation

        verified = file_found and content_found

        entry["source_file_found"] = str(file_found)
        entry["source_content_found"] = str(content_found)
        entry["source_verified"] = str(verified)
        entry["matched_corpus_file"] = matched_file or ""
        annotated.append(entry)

        if has_source:
            n_has_source += 1
        if file_found:
            n_file_found += 1
        if content_found:
            n_content_found += 1
        if verified:
            n_verified += 1

        # 2x2: traceable (verified) x in_reference (name found in reference CSV)
        in_ref = _name_in_reference(name, reference_names) if name else False

        if verified and in_ref:
            counts_2x2["tt"] += 1
        elif verified and not in_ref:
            counts_2x2["tf"] += 1
        elif not verified and in_ref:
            counts_2x2["ft"] += 1
        else:
            counts_2x2["ff"] += 1

    total = len(rows) or 1
    summary = {
        "total_plants": len(rows),
        "n_has_source": n_has_source,
        "n_file_found": n_file_found,
        "n_content_found": n_content_found,
        "n_verified": n_verified,
        "source_rate": round(n_has_source / total, 4),
        "grounding_rate": round(n_file_found / total, 4),
        "traceability_rate": round(n_verified / total, 4),
        "counts_2x2": counts_2x2,
    }

    return annotated, summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Verify source grounding against RAG corpus")
    parser.add_argument(
        "--input",
        required=True,
        help="Directory with sourced CSV files (or a single CSV path)",
    )
    parser.add_argument(
        "--corpus",
        required=True,
        help="Path to RAG corpus directory",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write summary JSON",
    )
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    corpus_dir = Path(args.corpus)
    output_path = Path(args.output)

    if not corpus_dir.is_dir():
        raise SystemExit(f"Corpus directory not found: {corpus_dir}")

    # Collect CSV files
    if input_path.is_dir():
        csv_files = sorted(
            f
            for f in input_path.glob("*.csv")
            if _has_source_columns(f) and "reconciliation" not in f.name
        )
    elif input_path.is_file():
        csv_files = [input_path]
    else:
        raise SystemExit(f"Input not found: {input_path}")

    if not csv_files:
        raise SystemExit(f"No CSV files with source columns found in: {input_path}")

    all_summaries = {}
    for csv_path in csv_files:
        rows = _load_csv(csv_path)
        if not rows:
            continue
        annotated, summary = verify_source_grounding(rows, corpus_dir)
        all_summaries[csv_path.stem] = summary
        log.info(
            "%s: %d plants, source_rate=%.1f%%, grounding=%.1f%%, traceable=%.1f%%",
            csv_path.stem,
            summary["total_plants"],
            100 * summary["source_rate"],
            100 * summary["grounding_rate"],
            100 * summary["traceability_rate"],
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(all_summaries, indent=2) + "\n", encoding="utf-8")
    log.info("Wrote %s", output_path)


def _has_source_columns(csv_path: Path) -> bool:
    """Check if a CSV has source_1 in its header."""
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, [])
    return "source_1" in header


def _load_csv(csv_path: Path) -> list[dict]:
    """Load a CSV into a list of dicts."""
    with open(csv_path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


if __name__ == "__main__":
    main()
