"""Verification pipeline for LLM-generated power plant data.

Modes:
  tool  — Check each plant against GEM database using fuzzy name matching.
  self  — Send CSV back to same model for self-verification.
  cross — Send CSV to a different verifier model.
  web   — Verify each plant via web search (requires Tavily).

Usage:
    python -m aedist.verify \
        --input outputs/sweep2_rag/2026-04-02/claude-sonnet-4.6-run1.json \
        --mode tool \
        --reference data/reference/gem_thermal.csv \
        --output outputs/sweep4_verification/
"""

import argparse
import csv
import io
import json
import logging
import re
from pathlib import Path

from rapidfuzz import fuzz

from .harness import make_client, query_single_turn

log = logging.getLogger(__name__)

_DEFAULT_REF = Path(__file__).parent.parent.parent / "data" / "reference" / "gem_thermal.csv"

# Similarity threshold for fuzzy name matching
_SIMILARITY_THRESHOLD = 70.0


# ---------------------------------------------------------------------------
# CSV extraction from response text
# ---------------------------------------------------------------------------

def extract_csv_rows(response_text: str) -> list[dict]:
    """Extract CSV rows from LLM response text (handles fenced blocks)."""
    # Try fenced blocks first
    blocks = re.findall(r"```(?:csv)?\s*\n(.*?)\n```", response_text, re.DOTALL | re.IGNORECASE)
    if blocks:
        text = max(blocks, key=lambda b: b.count("\n"))
    else:
        # Fallback: look for CSV-like content
        text = response_text

    try:
        reader = csv.DictReader(io.StringIO(text.strip()))
        rows = []
        for row in reader:
            # Normalize keys
            normalized = {k.strip().lower().replace(" ", "_"): v.strip() if v else ""
                         for k, v in row.items() if k}
            if normalized.get("name") or normalized.get("plant_name") or normalized.get("plant"):
                name_key = "name"
                if "plant_name" in normalized:
                    normalized["name"] = normalized.pop("plant_name")
                elif "plant" in normalized:
                    normalized["name"] = normalized.pop("plant")
                rows.append(normalized)
        return rows
    except Exception:
        return []


# ---------------------------------------------------------------------------
# GEM reference loading
# ---------------------------------------------------------------------------

def load_gem_reference(path: Path) -> list[dict]:
    """Load GEM thermal CSV into list of dicts with normalized names."""
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "name": row.get("Name", "").strip(),
                "name_lower": row.get("Name", "").strip().lower(),
                "province": row.get("Province", "").strip(),
                "fuel": row.get("Fuel", "").strip().lower(),
                "capacity": row.get("Capacity", "").strip(),
                "status": row.get("Status", "").strip(),
            })
    return rows


def fuzzy_match_gem(plant_name: str, gem_plants: list[dict]) -> dict | None:
    """Find best fuzzy match in GEM database."""
    best_score = 0.0
    best_match = None
    name_lower = plant_name.lower().strip()

    for gem in gem_plants:
        score = fuzz.token_sort_ratio(name_lower, gem["name_lower"])
        if score > best_score:
            best_score = score
            best_match = gem

    if best_score >= _SIMILARITY_THRESHOLD:
        return best_match
    return None


# ---------------------------------------------------------------------------
# Tool-based verification
# ---------------------------------------------------------------------------

def verify_tool(rows: list[dict], reference_path: Path) -> tuple[list[dict], dict]:
    """Verify plants against GEM database. Returns (annotated_rows, summary)."""
    gem_plants = load_gem_reference(reference_path)
    log.info("Loaded %d plants from GEM reference", len(gem_plants))

    verified_count = 0
    fabricated_count = 0
    uncertain_count = 0

    annotated = []
    for row in rows:
        name = row.get("name", "")
        match = fuzzy_match_gem(name, gem_plants)

        entry = dict(row)
        if match:
            entry["verified"] = "True"
            entry["verification_source"] = f"GEM: {match['name']}"
            entry["confidence"] = str(round(fuzz.token_sort_ratio(
                name.lower(), match["name_lower"]
            ) / 100, 2))
            verified_count += 1
        else:
            entry["verified"] = "False"
            entry["verification_source"] = "Not found in GEM"
            entry["confidence"] = "0.0"
            fabricated_count += 1

        annotated.append(entry)

    total = len(rows) or 1
    summary = {
        "total_plants": len(rows),
        "verified_count": verified_count,
        "fabricated_count": fabricated_count,
        "uncertain_count": uncertain_count,
        "verified_rate": round(verified_count / total, 4),
        "fabricated_rate": round(fabricated_count / total, 4),
        "uncertain_rate": round(uncertain_count / total, 4),
    }
    return annotated, summary


# ---------------------------------------------------------------------------
# Self/Cross verification via LLM
# ---------------------------------------------------------------------------

def verify_llm(
    rows: list[dict],
    model_id: str,
    input_path: Path,
) -> tuple[str, dict]:
    """Send CSV to an LLM for verification. Returns (raw_response, summary)."""
    client = make_client()

    # Format rows as CSV text for the prompt
    csv_text = _rows_to_csv_text(rows)

    prompt = (
        "I have the following CSV data about thermal power plants in Vietnam. "
        "Please verify each plant: does it exist? Is the information correct? "
        "For each plant, state VERIFIED, FABRICATED, or UNCERTAIN.\n\n"
        f"```csv\n{csv_text}\n```"
    )

    result = query_single_turn(client, model_id, [{"role": "user", "content": prompt}])
    response_text = result["content"]

    # Parse verification results (best-effort)
    verified = response_text.lower().count("verified") - response_text.lower().count("unverified")
    fabricated = response_text.lower().count("fabricated")
    uncertain = response_text.lower().count("uncertain")
    total = max(len(rows), 1)

    summary = {
        "mode": "self" if model_id else "cross",
        "verifier_model": model_id,
        "total_plants": len(rows),
        "verified_rate": round(max(verified, 0) / total, 4),
        "fabricated_rate": round(fabricated / total, 4),
        "uncertain_rate": round(uncertain / total, 4),
        "raw_response": response_text,
    }
    return response_text, summary


def _rows_to_csv_text(rows: list[dict]) -> str:
    """Convert list of dicts to CSV string."""
    if not rows:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Verify LLM-generated plant data")
    parser.add_argument("--input", required=True, help="Path to query output JSON")
    parser.add_argument("--mode", required=True, choices=["tool", "self", "cross", "web"],
                        help="Verification mode")
    parser.add_argument("--reference", default=None,
                        help="Path to GEM reference CSV (for --mode tool)")
    parser.add_argument("--verifier-model", default=None,
                        help="Model ID for cross-verification (--mode cross)")
    parser.add_argument("--output", required=True, help="Output directory")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load input JSON
    record = json.loads(input_path.read_text())
    response_text = record.get("response", "")

    # Handle multiturn format
    if not response_text and "turns" in record:
        # Use the last assistant turn
        assistant_turns = [t for t in record["turns"] if t.get("role") == "assistant"]
        if assistant_turns:
            response_text = assistant_turns[-1].get("content", "")

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

    if args.mode == "tool":
        ref_path = Path(args.reference) if args.reference else _DEFAULT_REF
        annotated, summary = verify_tool(rows, ref_path)

        # Write annotated CSV
        csv_path = output_dir / f"{stem}_verified.csv"
        if annotated:
            with open(csv_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(annotated[0].keys()))
                writer.writeheader()
                writer.writerows(annotated)
            log.info("Wrote %s", csv_path)

        # Write summary
        summary_path = output_dir / f"{stem}_summary.json"
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
        log.info("Wrote %s", summary_path)

    elif args.mode == "self":
        model_id = record.get("model")
        if not model_id:
            raise SystemExit("Input JSON missing 'model' field for self-verification")
        raw_response, summary = verify_llm(rows, model_id, input_path)

        summary_path = output_dir / f"{stem}_summary.json"
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
        log.info("Wrote %s", summary_path)

    elif args.mode == "cross":
        verifier = args.verifier_model
        if not verifier:
            raise SystemExit("--verifier-model required for --mode cross")
        raw_response, summary = verify_llm(rows, verifier, input_path)

        summary_path = output_dir / f"{stem}_summary.json"
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
        log.info("Wrote %s", summary_path)

    elif args.mode == "web":
        log.warning("Web verification not yet implemented.")

    log.info("Verification complete.")


if __name__ == "__main__":
    main()
