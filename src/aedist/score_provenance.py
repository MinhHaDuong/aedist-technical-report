"""Score provenance quality from sourced extraction runs.

Reads extracted CSVs with provenance columns (source_1, source_2, note)
and computes evidence scores and honesty rates using the existing
verification rubric from verify.py.

Usage:
    python -m aedist.score_provenance \
        --input experiments/outputs/sourced \
        --output derived/sourced_evidence_summary.json
"""

import argparse
import csv
import json
import logging
import re
from collections import Counter
from pathlib import Path

from aedist.verify import classify_source_by_text, score_evidence

log = logging.getLogger(__name__)

# Epistemic markers that signal intellectual honesty in notes
_EPISTEMIC_PATTERNS = [
    r"uncertain",
    r"conflicting",
    r"no data",
    r"unclear",
    r"estimated",
    r"approximate",
    r"planned but",
    r"discrepancy",
    r"unconfirmed",
]

_EPISTEMIC_RE = re.compile("|".join(_EPISTEMIC_PATTERNS), re.IGNORECASE)


def score_sourced_run(csv_path: Path) -> dict:
    """Score evidence quality for a single extracted CSV with provenance columns.

    Reads source_1 and source_2 columns, classifies each via
    verify.classify_source_by_text(), computes per-plant evidence_score
    using the 0-4 rubric from verify.score_evidence(), and returns a
    summary dict.
    """
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        return {
            "n_plants": 0,
            "mean_evidence_score": 0.0,
            "score_distribution": {i: 0 for i in range(5)},
            "primary_frac": 0.0,
            "secondary_frac": 0.0,
            "none_frac": 0.0,
        }

    scores = []
    type_counts = Counter()  # track source types across all plants

    for row in rows:
        s1_text = (row.get("source_1") or "").strip()
        s2_text = (row.get("source_2") or "").strip()

        sources = []
        if s1_text:
            s1_type = classify_source_by_text(s1_text)
            sources.append({"text": s1_text, "type": s1_type})
            type_counts[s1_type] += 1
        if s2_text:
            s2_type = classify_source_by_text(s2_text)
            sources.append({"text": s2_text, "type": s2_type})
            type_counts[s2_type] += 1

        if not sources:
            type_counts["none"] += 1

        plant_score = score_evidence(sources)
        scores.append(plant_score)

    n_plants = len(rows)
    total_sources = sum(type_counts.values())
    score_dist = Counter(scores)

    return {
        "n_plants": n_plants,
        "mean_evidence_score": round(sum(scores) / n_plants, 2),
        "score_distribution": {i: score_dist.get(i, 0) for i in range(5)},
        "primary_frac": round(type_counts.get("primary", 0) / max(total_sources, 1), 3),
        "secondary_frac": round(type_counts.get("secondary", 0) / max(total_sources, 1), 3),
        "none_frac": round(type_counts.get("none", 0) / max(total_sources, 1), 3),
    }


def score_honesty(csv_path: Path) -> dict:
    """Score intellectual honesty from epistemic markers in the note column.

    Counts plants with notes containing epistemic markers like "uncertain",
    "conflicting", "no data", etc.
    """
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    n_plants = len(rows)
    if n_plants == 0:
        return {
            "n_plants": 0,
            "n_with_note": 0,
            "n_with_epistemic_marker": 0,
            "honesty_rate": 0.0,
        }

    n_with_note = 0
    n_with_marker = 0

    for row in rows:
        note = (row.get("note") or "").strip()
        if note:
            n_with_note += 1
            if _EPISTEMIC_RE.search(note):
                n_with_marker += 1

    return {
        "n_plants": n_plants,
        "n_with_note": n_with_note,
        "n_with_epistemic_marker": n_with_marker,
        "honesty_rate": round(n_with_marker / n_plants, 4),
    }


def score_directory(input_dir: Path) -> dict:
    """Score all CSVs in a directory and produce aggregate summary."""
    csv_files = sorted(input_dir.glob("*.csv"))
    if not csv_files:
        raise SystemExit(f"No CSV files in: {input_dir}")

    runs = {}
    all_scores = []
    all_primary = 0
    all_secondary = 0
    all_none = 0
    all_total_sources = 0
    all_honesty_markers = 0
    all_plants = 0

    for csv_path in csv_files:
        run_name = csv_path.stem
        evidence = score_sourced_run(csv_path)
        honesty = score_honesty(csv_path)

        runs[run_name] = {**evidence, **honesty}

        n = evidence["n_plants"]
        all_plants += n
        all_scores.extend([evidence["mean_evidence_score"]] * n)

        # Reconstruct raw source counts from fracs
        total_src = round(
            evidence["primary_frac"] + evidence["secondary_frac"] + evidence["none_frac"], 3
        )
        if total_src > 0:
            scale = n  # approximate: at least 1 source classification per plant
            all_primary += round(evidence["primary_frac"] * scale)
            all_secondary += round(evidence["secondary_frac"] * scale)
            all_none += round(evidence["none_frac"] * scale)
            all_total_sources += scale

        all_honesty_markers += honesty["n_with_epistemic_marker"]

    aggregate_mean = round(sum(all_scores) / max(len(all_scores), 1), 2)
    aggregate_primary_frac = round(all_primary / max(all_total_sources, 1), 3)
    aggregate_honesty = round(all_honesty_markers / max(all_plants, 1), 4)

    return {
        "runs": runs,
        "aggregate": {
            "mean_evidence_score": aggregate_mean,
            "primary_frac": aggregate_primary_frac,
            "honesty_rate": aggregate_honesty,
        },
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(description="Score provenance quality from sourced runs")
    p.add_argument(
        "--input",
        required=True,
        help="Directory containing extracted CSVs with provenance columns",
    )
    p.add_argument(
        "--output",
        required=True,
        help="Path to write summary JSON",
    )
    args = p.parse_args()

    input_dir = Path(args.input)
    output_path = Path(args.output)

    if not input_dir.exists() or not input_dir.is_dir():
        raise SystemExit(f"Input dir not found: {input_dir}")

    summary = score_directory(input_dir)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    log.info("Wrote %s", output_path)


if __name__ == "__main__":
    main()
