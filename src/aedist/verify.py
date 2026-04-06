"""Verification pipeline for LLM-generated power plant data.

Modes:
  tool  — Check each plant against a reference CSV using fuzzy name matching.
  self  — Send CSV back to same model for self-verification.
  cross — Send CSV to a different verifier model.
  web   — Verify each plant via web search (requires Tavily).

Usage:
    python -m aedist.verify \
        --input outputs/sweep2_rag/2026-04-02/claude-sonnet-4.6-run1.json \
        --mode tool \
        --reference data/reference/vietnam_thermal_v1.csv \
        --output outputs/sweep4_verification/
"""

import argparse
import csv
import io
import json
import logging
import os
import re
from collections import Counter
from pathlib import Path

from rapidfuzz import fuzz

from .extract import (
    extract_fenced_blocks,
    fallback_extract_inline_csv,
    map_header_to_canonical,
    norm_header,
    sniff_dialect,
)
from .harness import make_client, query_single_turn, save_json
from .schema import SourceType

log = logging.getLogger(__name__)

_DEFAULT_REF = (
    Path(__file__).parent.parent.parent / "data" / "reference" / "vietnam_thermal_v1.csv"
)

# Default subject for LLM verification prompts (configurable for other domains)
DEFAULT_VERIFICATION_SUBJECT = "thermal power plants in Vietnam"

# Similarity threshold (0-100) for fuzzy name matching against reference database
SIMILARITY_THRESHOLD = 70.0

# Valid source type strings for LLM response validation
_VALID_SOURCE_TYPES = {SourceType.PRIMARY, SourceType.SECONDARY, SourceType.NONE}

# ---------------------------------------------------------------------------
# Source classification and evidence scoring
# ---------------------------------------------------------------------------

# Domains classified as primary sources (government, companies, registries)
_PRIMARY_DOMAINS = {
    "gov.vn",
    "chinhphu.vn",
    "moit.gov.vn",
    "evn.com.vn",
    "globalenergymonitor.org",
    "gem.wiki",
    "platts.com",
    "iea.org",
    "irena.org",
}

# Domains classified as secondary sources
_SECONDARY_DOMAINS = {
    "wikipedia.org",
    "en.m.wikipedia.org",
    "bbc.com",
    "reuters.com",
    "bloomberg.com",
    "nikkei.com",
}

# Patterns in citation text that indicate primary sources
_PRIMARY_PATTERNS = [
    r"(?i)decision\s+\d+/(?:QD|QĐ)",  # Vietnamese government decisions
    r"(?i)(?:PDP|quy\s+hoạch)\s*[78]",  # Power Development Plans
    r"(?i)EVN\s+(?:annual|báo\s+cáo)",  # EVN reports
    r"(?i)(?:annual\s+report|prospectus|10-K|10-Q)",  # Company filings
    r"(?i)satellite\s+imag",  # Satellite imagery
    r"(?i)(?:MOIT|BCT|Bộ\s+Công\s+Thương)",  # Ministry of Industry and Trade
]


def classify_source_by_url(url: str) -> str:
    """Classify a source URL as primary, secondary, or unknown.

    Returns a SourceType value for known domains, or "unknown" for
    unrecognized domains (treated as non-evidence by score_evidence).
    """
    url_lower = url.lower()
    for domain in _PRIMARY_DOMAINS:
        if domain in url_lower:
            return SourceType.PRIMARY
    for domain in _SECONDARY_DOMAINS:
        if domain in url_lower:
            return SourceType.SECONDARY
    return "unknown"


def classify_source_by_text(citation: str) -> str:
    """Classify a citation string as primary, secondary, or none.

    Uses pattern matching on the citation text. For LLM-declared types,
    prefer the model's own classification; this is a fallback/cross-check.
    """
    if not citation or citation.strip().lower() == "none":
        return SourceType.NONE
    for pattern in _PRIMARY_PATTERNS:
        if re.search(pattern, citation):
            return SourceType.PRIMARY
    # If it has a URL, classify by domain
    url_match = re.search(r"https?://[^\s]+", citation)
    if url_match:
        return classify_source_by_url(url_match.group())
    # Has text but no primary indicators
    return SourceType.SECONDARY


def score_evidence(sources: list[dict]) -> int:
    """Score evidence quality on the 0-4 rubric.

    Each source dict has keys: 'text' and 'type' (primary/secondary/hallucinated/none).

    Returns:
        0 — any hallucinated source
        1 — no sources provided
        2 — one secondary source (no primary)
        3 — one primary source
        4 — two or more independent primary sources
    """
    if not sources:
        return 1

    types = [s.get("type", SourceType.NONE) for s in sources if s.get("text", "").strip()]
    if not types:
        return 1

    if SourceType.HALLUCINATED in types:
        return 0

    primary_count = types.count(SourceType.PRIMARY)
    secondary_count = types.count(SourceType.SECONDARY)

    if primary_count >= 2:
        return 4
    if primary_count == 1:
        return 3
    if secondary_count >= 1:
        return 2
    return 1


def filter_by_score(annotated_rows: list[dict], min_score: int = 3) -> list[dict]:
    """Return only rows with evidence_score >= min_score."""
    return [r for r in annotated_rows if int(r.get("evidence_score", 0)) >= min_score]


def _build_summary(mode: str, annotated: list[dict], **extra) -> dict:
    """Build the standard verification summary dict from annotated rows."""
    total = len(annotated) or 1
    scores = [int(r["evidence_score"]) for r in annotated]
    counts = Counter(scores)
    summary = {
        "mode": mode,
        "total_plants": len(annotated),
        "mean_evidence_score": round(sum(scores) / total, 2),
        "score_distribution": {str(i): counts.get(i, 0) for i in range(5)},
    }
    summary.update(extra)
    return summary


def _annotate_sources(entry: dict, sources: list[dict]) -> None:
    """Set source_1/2, evidence_score, and verified fields on an entry dict."""
    for i in (1, 2):
        if i <= len(sources):
            entry[f"source_{i}"] = sources[i - 1].get("text", "")
            entry[f"source_{i}_type"] = sources[i - 1].get("type", SourceType.NONE)
        else:
            entry[f"source_{i}"] = ""
            entry[f"source_{i}_type"] = SourceType.NONE
    score = score_evidence(sources)
    entry["evidence_score"] = str(score)
    entry["verified"] = "True" if score >= 3 else "False"


# ---------------------------------------------------------------------------
# CSV extraction from response text
# ---------------------------------------------------------------------------


def extract_csv_rows(response_text: str) -> list[dict]:
    """Extract CSV rows from LLM response text (handles fenced blocks).

    Uses shared extraction utilities from aedist.extract.
    """
    # Try fenced blocks first (reuse extract.py logic)
    blocks = extract_fenced_blocks(response_text)
    if blocks:
        text = max(blocks, key=lambda b: b.count("\n"))
    else:
        # Fallback: look for CSV-like content
        inline = fallback_extract_inline_csv(response_text)
        text = inline if inline else response_text

    try:
        dialect = sniff_dialect(text.strip())
        reader = csv.DictReader(io.StringIO(text.strip()), dialect=dialect)
        rows = []
        for row in reader:
            # Normalize keys using shared extract.py utilities
            normalized: dict[str, str] = {}
            for k, v in row.items():
                if not k:
                    continue
                norm = norm_header(k)
                canon = map_header_to_canonical(norm)
                key = canon if canon else norm
                normalized[key] = v.strip() if v else ""
            if normalized.get("name"):
                rows.append(normalized)
        return rows
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Reference loading
# ---------------------------------------------------------------------------


def load_reference(path: Path) -> list[dict]:
    """Load reference CSV into list of dicts with normalized names.

    Supports both lowercase headers (name, province, fuel, capacity_mwe,
    status) and title-case headers (Name, Province, Fuel, Capacity, Status).
    The primary reference is vietnam_thermal_v1.csv, hand-assembled from
    government sources (PDP7, PDP7A, PDP8, EVN reports). Secondary sources
    like GEM may use title-case headers and serve as cross-checks only.
    """
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Support both header conventions
            name = (row.get("name") or row.get("Name") or "").strip()
            rows.append(
                {
                    "name": name,
                    "name_lower": name.lower(),
                    "province": (row.get("province") or row.get("Province") or "").strip(),
                    "fuel": (row.get("fuel") or row.get("Fuel") or "").strip().lower(),
                    "capacity": (row.get("capacity_mwe") or row.get("Capacity") or "").strip(),
                    "status": (row.get("status") or row.get("Status") or "").strip(),
                }
            )
    return rows


def fuzzy_match_reference(plant_name: str, ref_plants: list[dict]) -> dict | None:
    """Find best fuzzy match in reference database."""
    best_score = 0.0
    best_match = None
    name_lower = plant_name.lower().strip()

    for ref in ref_plants:
        score = fuzz.token_sort_ratio(name_lower, ref["name_lower"])
        if score > best_score:
            best_score = score
            best_match = ref

    if best_score >= SIMILARITY_THRESHOLD:
        return best_match
    return None


# ---------------------------------------------------------------------------
# Tool-based verification
# ---------------------------------------------------------------------------


def verify_tool(rows: list[dict], reference_path: Path) -> tuple[list[dict], dict]:
    """Verify plants against reference database with evidence scoring.

    Returns (annotated_rows, summary). Each row gets evidence_score:
      - 3 (one primary) if found in reference
      - 1 (no sources) if not found
    """
    ref_plants = load_reference(reference_path)
    log.info("Loaded %d plants from reference: %s", len(ref_plants), reference_path.name)

    annotated = []
    for row in rows:
        name = row.get("name", "")
        match = fuzzy_match_reference(name, ref_plants)

        entry = dict(row)
        if match:
            source_text = f"ref: {match['name']}"
            entry["verification_source"] = source_text
            entry["confidence"] = str(
                round(fuzz.token_sort_ratio(name.lower(), match["name_lower"]) / 100, 2)
            )
            _annotate_sources(entry, [{"text": source_text, "type": SourceType.PRIMARY}])
        else:
            entry["verification_source"] = "Not found in reference"
            entry["confidence"] = "0.0"
            _annotate_sources(entry, [])

        annotated.append(entry)

    scores = [int(r["evidence_score"]) for r in annotated]
    return annotated, _build_summary(
        "tool",
        annotated,
        verified_count=sum(1 for s in scores if s >= 3),
        fabricated_count=0,
        uncertain_count=sum(1 for s in scores if s == 1),
    )


# ---------------------------------------------------------------------------
# LLM-based verification (self / cross) with per-plant citations
# ---------------------------------------------------------------------------

_VERIFICATION_PROMPT = """\
You previously generated a list of {subject}. For each plant below, \
cite up to 2 sources that confirm it exists with the stated attributes.

Requirements:
- Prefer primary sources: government decisions, company reports, regulatory \
filings, satellite imagery databases.
- Secondary sources (Wikipedia, news articles) are acceptable if no primary \
source is available, but label them honestly.
- Be specific: document name, date, section/page when available.
- For each source, classify as "primary" or "secondary".
- If you cannot find a reliable source, write "none" for source and type.

Respond with ONLY a JSON array, one object per plant:
[
  {{"name": "Pha Lai", "source_1": "Decision 1195/QD-TTg 2006, Annex I", \
"source_1_type": "primary", "source_2": "EVN Annual Report 2020 p.34", \
"source_2_type": "primary"}},
  ...
]

Plants to verify:
{plant_list}"""


def _build_plant_list(rows: list[dict]) -> str:
    """Format rows as a numbered list for the verification prompt."""
    lines = []
    for i, row in enumerate(rows, 1):
        name = row.get("name", "?")
        fuel = row.get("fuel", "")
        province = row.get("province", "")
        capacity = row.get("capacity_mwe", "")
        lines.append(f"{i}. {name} — {fuel}, {province}, {capacity} MWe")
    return "\n".join(lines)


def _parse_verification_json(response_text: str, rows: list[dict]) -> list[dict]:
    """Parse structured JSON verification response into annotated rows.

    Tries json.loads() first, then falls back to extracting JSON objects
    via regex. Returns annotated rows with source_1, source_1_type,
    source_2, source_2_type, and evidence_score fields.
    """
    # Try to parse the full JSON array
    verdicts: list[dict] = []
    try:
        # Find the JSON array in the response (may have surrounding text)
        match = re.search(r"\[.*\]", response_text, re.DOTALL)
        if match:
            verdicts = json.loads(match.group())
    except (json.JSONDecodeError, TypeError):
        pass

    # Fallback: extract individual JSON objects
    if not verdicts:
        for m in re.finditer(r"\{[^}]+\}", response_text):
            try:
                obj = json.loads(m.group())
                if "name" in obj:
                    verdicts.append(obj)
            except json.JSONDecodeError:
                continue

    # Build a lookup by plant name (fuzzy)
    verdict_by_name: dict[str, dict] = {}
    for v in verdicts:
        vname = v.get("name", "").strip().lower()
        if vname:
            verdict_by_name[vname] = v

    annotated = []
    for row in rows:
        entry = dict(row)
        name = row.get("name", "").strip()
        name_lower = name.lower()

        # Find matching verdict (exact or fuzzy)
        verdict = verdict_by_name.get(name_lower)
        if not verdict:
            best_score = 0.0
            for vname, v in verdict_by_name.items():
                score = fuzz.token_sort_ratio(name_lower, vname)
                if score > best_score and score >= 70:
                    best_score = score
                    verdict = v

        if verdict:
            sources = []
            for key in ("source_1", "source_2"):
                text = verdict.get(key, "").strip()
                stype = verdict.get(f"{key}_type", SourceType.NONE).strip().lower()
                if text and stype not in _VALID_SOURCE_TYPES:
                    stype = classify_source_by_text(text)
                if text:
                    sources.append({"text": text, "type": stype})
            _annotate_sources(entry, sources)
        else:
            _annotate_sources(entry, [])

        annotated.append(entry)

    return annotated


def verify_llm(
    rows: list[dict],
    model_id: str,
    subject: str = DEFAULT_VERIFICATION_SUBJECT,
) -> tuple[list[dict], dict]:
    """Ask an LLM to cite primary sources for each plant.

    Returns (annotated_rows, summary) where each row has evidence_score
    and per-plant source citations.
    """
    client = make_client()

    plant_list = _build_plant_list(rows)
    prompt = _VERIFICATION_PROMPT.format(subject=subject, plant_list=plant_list)

    result = query_single_turn(client, model_id, [{"role": "user", "content": prompt}])
    response_text = result["content"]
    usage = result.get("usage") or {}

    annotated = _parse_verification_json(response_text, rows)

    return annotated, _build_summary(
        "llm",
        annotated,
        verifier_model=model_id,
        usage=usage,
        wall_seconds=result.get("wall_seconds", 0),
    )


def verify_self(
    rows: list[dict],
    model_id: str,
    subject: str = DEFAULT_VERIFICATION_SUBJECT,
) -> tuple[list[dict], dict]:
    """Self-verification: same model cites sources for its own output."""
    annotated, summary = verify_llm(rows, model_id, subject)
    summary["mode"] = "self"
    return annotated, summary


def verify_cross(
    rows: list[dict],
    verifier_model: str,
    subject: str = DEFAULT_VERIFICATION_SUBJECT,
) -> tuple[list[dict], dict]:
    """Cross-verification: different model cites sources for the output."""
    annotated, summary = verify_llm(rows, verifier_model, subject)
    summary["mode"] = "cross"
    return annotated, summary


# ---------------------------------------------------------------------------
# Web-based verification via Tavily
# ---------------------------------------------------------------------------


def _load_tavily_cache(cache_path: Path) -> dict[str, list[dict]]:
    """Load cached Tavily search results from a JSON file."""
    if cache_path.exists():
        return json.loads(cache_path.read_text())
    return {}


def verify_web(
    rows: list[dict],
    tavily_key: str,
    cache_path: Path | None = None,
    subject: str = DEFAULT_VERIFICATION_SUBJECT,
) -> tuple[list[dict], dict]:
    """Verify each plant via Tavily web search with URL-based source classification.

    Returns (annotated_rows, summary). Caches search results to avoid
    redundant API calls across runs.
    """
    from .query_web import tavily_search

    cache: dict[str, list[dict]] = {}
    if cache_path:
        cache = _load_tavily_cache(cache_path)

    annotated = []
    searches_performed = 0

    for row in rows:
        name = row.get("name", "").strip()
        if not name:
            entry = dict(row)
            _annotate_sources(entry, [])
            annotated.append(entry)
            continue

        query = f"{name} {subject}"
        if query in cache:
            results = cache[query]
        else:
            try:
                results = tavily_search(query, tavily_key)
                searches_performed += 1
            except Exception as e:
                log.warning("Tavily search failed for '%s': %s", name, e)
                results = []
            cache[query] = results

        # Classify search results and find best sources
        sources: list[dict] = []
        name_lower = name.lower()
        for r in results:
            url = r.get("url", "")
            content = r.get("content", "")
            title = r.get("title", "")

            relevance = max(
                fuzz.partial_ratio(name_lower, content.lower()),
                fuzz.partial_ratio(name_lower, title.lower()),
            )
            if relevance < 50:
                continue

            sources.append(
                {
                    "text": f"{title} ({url})",
                    "type": classify_source_by_url(url),
                    "relevance": relevance,
                }
            )

        # Sort by: primary first, then by relevance
        type_order = {SourceType.PRIMARY: 0, SourceType.SECONDARY: 1, "unknown": 2}
        sources.sort(key=lambda s: (type_order.get(s["type"], 9), -s["relevance"]))

        entry = dict(row)
        _annotate_sources(entry, sources[:2])
        annotated.append(entry)

    if cache_path:
        save_json(cache_path, cache)

    return annotated, _build_summary(
        "web",
        annotated,
        searches_performed=searches_performed,
    )


# ---------------------------------------------------------------------------
# Unverified baseline
# ---------------------------------------------------------------------------


def verify_unverified(rows: list[dict]) -> tuple[list[dict], dict]:
    """Baseline: score existing citations in the raw output (if any).

    Plants without sources get score 1. Plants with inline citations
    get scored via heuristic.
    """
    annotated = []
    for row in rows:
        entry = dict(row)
        source_ref = row.get("source_ref", "").strip()
        if source_ref:
            stype = classify_source_by_text(source_ref)
            _annotate_sources(entry, [{"text": source_ref, "type": stype}])
        else:
            _annotate_sources(entry, [])
        annotated.append(entry)

    return annotated, _build_summary("unverified", annotated)


# ---------------------------------------------------------------------------
# Shared: extract response text from query output JSON
# ---------------------------------------------------------------------------


def extract_response_text(record: dict) -> str:
    """Get the LLM response text from a query output JSON record.

    Handles both single-shot (record['response']) and multiturn
    (record['turns'][-1 assistant]) formats.
    """
    response_text = record.get("response", "")
    if not response_text and "turns" in record:
        assistant_turns = [t for t in record["turns"] if t.get("role") == "assistant"]
        if assistant_turns:
            response_text = assistant_turns[-1].get("content", "")
    return response_text


def write_annotated_csv(annotated: list[dict], path: Path) -> None:
    """Write annotated rows to CSV."""
    if not annotated:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(annotated[0].keys()))
        writer.writeheader()
        writer.writerows(annotated)
    log.info("Wrote %s", path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Verify LLM-generated plant data")
    parser.add_argument("--input", required=True, help="Path to query output JSON")
    parser.add_argument(
        "--mode",
        required=True,
        choices=["unverified", "tool", "self", "cross", "web"],
        help="Verification mode",
    )
    parser.add_argument(
        "--reference", default=None, help="Path to reference CSV (for --mode tool)"
    )
    parser.add_argument(
        "--verifier-model", default=None, help="Model ID for cross-verification (--mode cross)"
    )
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument(
        "--subject",
        default=DEFAULT_VERIFICATION_SUBJECT,
        help="Domain description for LLM verification prompt (default: '%(default)s')",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load input JSON
    record = json.loads(input_path.read_text())
    response_text = extract_response_text(record)

    if not response_text:
        log.warning("No response text found in %s", input_path)
        return

    # Extract CSV rows
    rows = extract_csv_rows(response_text)
    if not rows:
        log.warning("No CSV data found in response from %s", input_path)
        return

    log.info("Extracted %d plants from %s", len(rows), input_path.name)

    stem = input_path.stem

    if args.mode == "unverified":
        annotated, summary = verify_unverified(rows)
    elif args.mode == "tool":
        ref_path = Path(args.reference) if args.reference else _DEFAULT_REF
        annotated, summary = verify_tool(rows, ref_path)
    elif args.mode == "self":
        model_id = record.get("model")
        if not model_id:
            raise SystemExit("Input JSON missing 'model' field for self-verification")
        annotated, summary = verify_self(rows, model_id, subject=args.subject)
    elif args.mode == "cross":
        verifier = args.verifier_model
        if not verifier:
            raise SystemExit("--verifier-model required for --mode cross")
        annotated, summary = verify_cross(rows, verifier, subject=args.subject)
    elif args.mode == "web":
        tavily_key = os.environ.get("TAVILY_API_KEY")
        if not tavily_key:
            raise SystemExit("TAVILY_API_KEY not set")
        cache_path = output_dir / "tavily_cache.json"
        annotated, summary = verify_web(rows, tavily_key, cache_path, subject=args.subject)
    else:
        raise SystemExit(f"Unknown mode: {args.mode}")

    # Write annotated CSV
    csv_path = output_dir / f"{stem}_verified.csv"
    write_annotated_csv(annotated, csv_path)

    # Write summary
    summary_path = output_dir / f"{stem}_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    log.info("Wrote %s", summary_path)
    log.info(
        "Verification complete. Mean evidence score: %.2f", summary.get("mean_evidence_score", 0)
    )


if __name__ == "__main__":
    main()
