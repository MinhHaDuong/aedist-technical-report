"""Source URL verification audit — rubric calibration.

One-time audit that validates the evidence rubric (0-4) by checking whether
cited URLs resolve and whether cited content can be confirmed via web search.
Produces a calibration table: evidence score tier vs. verification rate.

Usage:
    uv run python scripts/audit_source_urls.py --dry-run
    uv run python scripts/audit_source_urls.py
"""

import argparse
import csv
import json
import logging
import os
import random
import re
from collections import defaultdict
from pathlib import Path

import httpx
from rapidfuzz import fuzz

from aedist.verify import (
    _PRIMARY_PATTERNS,
    classify_source_by_text,
    score_evidence,
)

log = logging.getLogger(__name__)

_DEFAULT_INPUTS = [
    Path("experiments/outputs/sourced/claude-opus-4.6-run1.csv"),
    Path("experiments/outputs/sourced/claude-opus-4.6-run2.csv"),
    Path("experiments/outputs/sourced/claude-opus-4.6-run3.csv"),
]
_DEFAULT_GEM = Path("data/reference/gem_thermal.csv")
_DEFAULT_OUTPUT_DIR = Path("derived/audit/")


# ---------------------------------------------------------------------------
# Step 2: Extract and stratify
# ---------------------------------------------------------------------------


def _read_sourced_csv(csv_path: Path) -> list[dict]:
    """Read a sourced CSV into list of dicts."""
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _compute_tier(row: dict) -> int:
    """Compute evidence tier for a single row using the rubric."""
    sources = []
    for key in ("source_1", "source_2"):
        text = (row.get(key) or "").strip()
        if text:
            stype = classify_source_by_text(text)
            sources.append({"text": text, "type": stype})
    return score_evidence(sources)


def extract_and_stratify(
    csv_paths: Path | list[Path],
) -> dict[int, list[dict]]:
    """Read sourced CSVs, compute evidence tier, group by tier.

    Accepts a single Path or a list of Paths.  When multiple paths are
    given, rows are deduplicated by plant name (first occurrence wins).
    """
    if isinstance(csv_paths, Path):
        csv_paths = [csv_paths]

    seen_names: set[str] = set()
    all_rows: list[dict] = []
    for p in csv_paths:
        for row in _read_sourced_csv(p):
            name = (row.get("name") or "").strip()
            if name and name not in seen_names:
                seen_names.add(name)
                all_rows.append(row)

    stratified: dict[int, list[dict]] = defaultdict(list)
    for row in all_rows:
        tier = _compute_tier(row)
        row["evidence_tier"] = tier
        stratified[tier].append(row)

    return dict(stratified)


# ---------------------------------------------------------------------------
# Step 3: Select sample
# ---------------------------------------------------------------------------


def select_sample(
    stratified: dict[int, list[dict]],
    n_per_tier: int = 10,
) -> list[dict]:
    """Deterministic sample from each tier.

    Tier 1 gets min(5, len), other tiers get min(n_per_tier, len).
    """
    rng = random.Random(42)
    sample: list[dict] = []

    for tier in sorted(stratified.keys()):
        rows = list(stratified[tier])
        limit = 5 if tier == 1 else n_per_tier
        k = min(limit, len(rows))
        chosen = rng.sample(rows, k)
        for row in chosen:
            row_copy = dict(row)
            row_copy["evidence_tier"] = tier
            sample.append(row_copy)

    return sample


# ---------------------------------------------------------------------------
# Step 4: Verify URL
# ---------------------------------------------------------------------------


def verify_url(citation_text: str) -> dict:
    """Extract URL from citation text and check HTTP status.

    Returns dict with has_url, status_code, final_url.
    """
    match = re.search(r"https?://[^\s)]+", citation_text or "")
    if not match:
        return {"has_url": False, "status_code": None, "final_url": None}

    url = match.group()
    try:
        resp = httpx.head(url, timeout=10.0, follow_redirects=True)
        return {
            "has_url": True,
            "status_code": resp.status_code,
            "final_url": str(resp.url),
        }
    except (httpx.HTTPError, httpx.InvalidURL):
        return {"has_url": True, "status_code": None, "final_url": None}


# ---------------------------------------------------------------------------
# Step 5: Verify content via Tavily
# ---------------------------------------------------------------------------


def _extract_citation_key(citation_text: str) -> str:
    """Extract the key identifier from a citation for search purposes.

    Prepends "Vietnam power development plan" to short identifiers like
    PDP7/PDP8 that are otherwise ambiguous (e.g. DEC minicomputers).
    """
    # Try to extract decision/report identifiers
    patterns = [
        r"Decision\s+(?:No\.?\s*)?\d+/[^\s,]+",
        r"(?:PDP|QH)[78]\w*",
        r"EVN\s+Annual\s+Report\s+\d{4}",
        r"(?:MOIT|BCT)\s+\w+",
    ]
    for pat in patterns:
        m = re.search(pat, citation_text, re.IGNORECASE)
        if m:
            key = m.group()
            # Disambiguate short identifiers that collide with unrelated terms
            if re.match(r"(?:PDP|QH)[78]", key, re.IGNORECASE):
                return f"Vietnam power development plan {key}"
            return key
    # Fallback: use first 50 chars
    return citation_text[:50].strip()


def verify_content_tavily(
    plant_name: str,
    citation_text: str,
    tavily_key: str,
) -> dict:
    """Search Tavily for plant + citation key terms.

    Returns dict with query, n_results, entity_found, top_result_url,
    top_result_snippet.
    """
    from aedist.query_livesearch import tavily_search

    key_terms = _extract_citation_key(citation_text)
    query = f"{plant_name} {key_terms}"

    try:
        results = tavily_search(query, tavily_key)
    except Exception as exc:
        log.warning("Tavily search failed for %r: %s", query, exc)
        return {
            "query": query,
            "n_results": 0,
            "entity_found": False,
            "top_result_url": None,
            "top_result_snippet": None,
        }

    entity_found = False
    name_lower = plant_name.lower()
    for r in results:
        content = (r.get("content") or "").lower()
        title = (r.get("title") or "").lower()
        if name_lower in content or name_lower in title:
            entity_found = True
            break

    return {
        "query": query,
        "n_results": len(results),
        "entity_found": entity_found,
        "top_result_url": results[0].get("url") if results else None,
        "top_result_snippet": (results[0].get("content") or "")[:200] if results else None,
    }


# ---------------------------------------------------------------------------
# Step 6: Check fabrication
# ---------------------------------------------------------------------------


def check_fabrication(
    citation_text: str,
    tavily_key: str | None = None,
) -> dict:
    """Check if a primary-pattern citation might be fabricated.

    For citations matching _PRIMARY_PATTERNS, search for the exact
    identifier. Flag as fabrication_suspect if zero results.
    """
    is_primary = False
    identifier = None

    for pattern in _PRIMARY_PATTERNS:
        m = re.search(pattern, citation_text or "")
        if m:
            is_primary = True
            identifier = m.group()
            break

    if not is_primary or not tavily_key:
        return {
            "is_primary_pattern": is_primary,
            "identifier": identifier,
            "fabrication_suspect": None,
            "search_evidence": None,
        }

    from aedist.query_livesearch import tavily_search

    # Disambiguate short identifiers (e.g. PDP7 -> DEC minicomputer)
    search_term = identifier
    if re.match(r"(?:PDP|QH)[78]", identifier, re.IGNORECASE):
        search_term = f"Vietnam power development plan {identifier}"

    try:
        results = tavily_search(search_term, tavily_key)
    except Exception as exc:
        log.warning("Fabrication check failed for %r: %s", identifier, exc)
        return {
            "is_primary_pattern": True,
            "identifier": identifier,
            "fabrication_suspect": None,
            "search_evidence": f"error: {exc}",
        }

    # Check if any result mentions the identifier
    id_lower = identifier.lower()
    found = any(
        id_lower in (r.get("content") or "").lower() or id_lower in (r.get("title") or "").lower()
        for r in results
    )

    return {
        "is_primary_pattern": True,
        "identifier": identifier,
        "fabrication_suspect": not found,
        "search_evidence": results[0].get("content", "")[:200] if results else None,
    }


# ---------------------------------------------------------------------------
# Step 7: Build calibration table
# ---------------------------------------------------------------------------


def build_calibration_table(audit_rows: list[dict]) -> dict[int, dict]:
    """Aggregate per-tier verification rates."""
    tiers: dict[int, list[dict]] = defaultdict(list)
    for row in audit_rows:
        tiers[row["evidence_tier"]].append(row)

    table: dict[int, dict] = {}
    for tier, rows in sorted(tiers.items()):
        n = len(rows)
        url_resolved = sum(
            1
            for r in rows
            if r.get("has_url")
            and r.get("status_code") is not None
            and 200 <= r["status_code"] < 400
        )
        content_confirmed = sum(1 for r in rows if r.get("entity_found"))
        fabrication_suspects = sum(
            1 for r in rows if r.get("is_primary_pattern") and r.get("fabrication_suspect") is True
        )
        primary_count = sum(1 for r in rows if r.get("is_primary_pattern"))

        table[tier] = {
            "n_sampled": n,
            "url_resolve_rate": round(url_resolved / n, 3) if n else 0.0,
            "content_confirm_rate": round(content_confirmed / n, 3) if n else 0.0,
            "fabrication_rate": (
                round(fabrication_suspects / primary_count, 3) if primary_count else None
            ),
        }

    return table


# ---------------------------------------------------------------------------
# Step 8: Cross-reference GEM
# ---------------------------------------------------------------------------


def cross_reference_gem(
    audit_rows: list[dict],
    gem_path: Path,
) -> list[dict]:
    """Fuzzy-match audited plants against GEM thermal database."""
    with open(gem_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        gem_plants = list(reader)

    gem_names = [(r.get("Name") or "").strip() for r in gem_plants]

    for row in audit_rows:
        plant_name = (row.get("name") or "").strip()
        best_score = 0.0
        best_match = None

        for gname in gem_names:
            score = fuzz.token_sort_ratio(plant_name.lower(), gname.lower())
            if score > best_score:
                best_score = score
                best_match = gname

        if best_score >= 70:
            row["gem_match"] = best_match
            row["gem_agrees"] = True
        else:
            row["gem_match"] = None
            row["gem_agrees"] = None

    return audit_rows


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------


def _write_audit_csv(audit_rows: list[dict], path: Path) -> None:
    """Write audit rows to CSV."""
    if not audit_rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(audit_rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(audit_rows)
    log.info("Wrote %s", path)


def _write_calibration_json(table: dict, path: Path) -> None:
    """Write calibration table as JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Convert int keys to strings for JSON
    serializable = {str(k): v for k, v in table.items()}
    path.write_text(json.dumps(serializable, indent=2) + "\n")
    log.info("Wrote %s", path)


def _write_calibration_tex(table: dict, path: Path) -> None:
    """Write calibration table as LaTeX."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{Rubric calibration: verification rates by evidence score tier}",
        r"\label{tab:rubric-calibration}",
        r"\begin{tabular}{ccccc}",
        r"\toprule",
        r"Score & $n$ & URL resolve & Content confirm & Fabrication \\",
        r"\midrule",
    ]
    for tier in sorted(table.keys()):
        row = table[tier]
        fab = f"{row['fabrication_rate']:.1%}" if row["fabrication_rate"] is not None else "---"
        lines.append(
            f"  {tier} & {row['n_sampled']} & "
            f"{row['url_resolve_rate']:.1%} & "
            f"{row['content_confirm_rate']:.1%} & "
            f"{fab} \\\\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
        ]
    )
    path.write_text("\n".join(lines) + "\n")
    log.info("Wrote %s", path)


# ---------------------------------------------------------------------------
# Step 9: CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """Run the source URL verification audit."""
    parser = argparse.ArgumentParser(
        description="Audit source citations: URL checks + content verification"
    )
    parser.add_argument(
        "--input",
        nargs="+",
        default=None,
        help="Sourced CSV path(s). Default: 3 Claude Opus runs.",
    )
    parser.add_argument(
        "--gem",
        default=str(_DEFAULT_GEM),
        help="Path to GEM thermal reference CSV.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(_DEFAULT_OUTPUT_DIR),
        help="Output directory for audit results.",
    )
    parser.add_argument(
        "--n-per-tier",
        type=int,
        default=10,
        help="Sample size per evidence tier (default: 10).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip Tavily/HTTP calls; only extract, stratify, and GEM cross-ref.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Resolve input paths
    if args.input:
        input_paths = [Path(p) for p in args.input]
    else:
        input_paths = _DEFAULT_INPUTS

    gem_path = Path(args.gem)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    tavily_key = os.environ.get("TAVILY_API_KEY")

    # Step 2: Extract and stratify
    log.info("Extracting and stratifying from %d CSV(s)...", len(input_paths))
    stratified = extract_and_stratify(input_paths)
    for tier in sorted(stratified.keys()):
        log.info("  Tier %d: %d plants", tier, len(stratified[tier]))

    # Step 3: Select sample
    sample = select_sample(stratified, n_per_tier=args.n_per_tier)
    log.info("Selected %d plants for audit", len(sample))

    # Steps 4-6: Verification (skip in dry-run)
    # Check both source_1 and source_2 independently; aggregate results.
    for row in sample:
        citations = [(row.get(key) or "").strip() for key in ("source_1", "source_2")]
        citations = [c for c in citations if c]

        if args.dry_run:
            # Populate with empty verification fields
            row.update(
                {
                    "has_url": False,
                    "status_code": None,
                    "final_url": None,
                    "entity_found": False,
                    "is_primary_pattern": any(
                        re.search(p, c) for c in citations for p in _PRIMARY_PATTERNS
                    )
                    if citations
                    else False,
                    "identifier": None,
                    "fabrication_suspect": None,
                    "search_evidence": None,
                }
            )
        else:
            # Step 4: URL check — use first citation with a URL, else first
            url_result = {"has_url": False, "status_code": None, "final_url": None}
            for cit in citations:
                url_result = verify_url(cit)
                if url_result["has_url"]:
                    break

            row.update(url_result)

            # Step 5: Content verification via Tavily
            # Check each citation; entity_found if any confirms
            row["entity_found"] = False
            if tavily_key:
                for cit in citations:
                    content_result = verify_content_tavily(row.get("name", ""), cit, tavily_key)
                    time.sleep(0.5)
                    if content_result["entity_found"]:
                        row["entity_found"] = True
                        break

            # Step 6: Fabrication check — check each citation independently
            row.update(
                {
                    "is_primary_pattern": False,
                    "identifier": None,
                    "fabrication_suspect": None,
                    "search_evidence": None,
                }
            )
            if tavily_key:
                for cit in citations:
                    fab_result = check_fabrication(cit, tavily_key)
                    time.sleep(0.5)
                    if fab_result["is_primary_pattern"]:
                        row.update(
                            {
                                "is_primary_pattern": fab_result["is_primary_pattern"],
                                "identifier": fab_result["identifier"],
                                "fabrication_suspect": fab_result["fabrication_suspect"],
                                "search_evidence": fab_result["search_evidence"],
                            }
                        )
                        break

    # Step 8: Cross-reference GEM
    sample = cross_reference_gem(sample, gem_path)

    # Step 7: Build calibration table
    cal_table = build_calibration_table(sample)

    # Write outputs
    _write_audit_csv(sample, output_dir / "source_audit.csv")
    _write_calibration_json(cal_table, output_dir / "calibration_table.json")
    _write_calibration_tex(cal_table, output_dir / "calibration_table.tex")

    # Print summary
    log.info("\n=== Calibration Table ===")
    log.info(
        "%-6s %6s %12s %16s %14s", "Tier", "n", "URL resolve", "Content confirm", "Fabrication"
    )
    for tier in sorted(cal_table.keys()):
        row = cal_table[tier]
        fab = f"{row['fabrication_rate']:.1%}" if row["fabrication_rate"] is not None else "---"
        line = (
            f"{tier:<6d} {row['n_sampled']:6d} "
            f"{row['url_resolve_rate'] * 100:11.1f}% "
            f"{row['content_confirm_rate'] * 100:15.1f}% "
            f"{fab:>14s}"
        )
        log.info(
            "%s",
            line,
        )


if __name__ == "__main__":
    main()
