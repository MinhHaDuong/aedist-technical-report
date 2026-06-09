"""Score provenance quality from sourced extraction runs.

Reads extracted CSVs with provenance columns (source_1, source_2, note)
and computes evidence scores and honesty rates using the existing
verification rubric from verify.py.

Usage:
    python -m aedist.score_provenance \
        --input experiments/outputs/rag_cited \
        --output derived/sourced_evidence_summary.json
"""

import argparse
import csv
import json
import logging
import re
from collections import Counter
from pathlib import Path

from .verify import classify_source_by_text, score_evidence

log = logging.getLogger(__name__)

# Colocated non-run outputs to skip by filename (ticket 0499).
#
# The content filter alone (_has_provenance_columns) excludes reconciliation_*
# files because their match_type schema has no source_1 column. The real leak it
# misses is *_filtered.csv: query_verification writes both {stem}.csv and
# {stem}_filtered.csv into the same output dir, and the filtered copy RETAINS
# source_1, so the content filter passes it and it would be scored as a spurious
# second run alongside its base run. The suffix skip closes that.
#
# _SKIP_PREFIXES mirrors the sibling consumers for class-consistency. The
# reconciliation_ prefix is redundant with the content filter here; "filtered_"
# is a defensive prefix that matches no current artifact (the real filtered files
# use the _filtered.csv suffix above), kept only to match the shared pattern.
_SKIP_PREFIXES = ("reconciliation_", "filtered_")
_SKIP_SUFFIXES = ("_filtered.csv",)

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
            "primary_count": 0,
            "secondary_count": 0,
            "none_count": 0,
            "total_sources": 0,
            "sum_evidence_scores": 0,
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

    primary_count = type_counts.get("primary", 0)
    secondary_count = type_counts.get("secondary", 0)
    none_count = type_counts.get("none", 0)
    raw_score_sum = sum(scores)

    return {
        "n_plants": n_plants,
        "mean_evidence_score": round(raw_score_sum / n_plants, 2),
        "score_distribution": {i: score_dist.get(i, 0) for i in range(5)},
        "primary_frac": round(primary_count / max(total_sources, 1), 3),
        "secondary_frac": round(secondary_count / max(total_sources, 1), 3),
        "none_frac": round(none_count / max(total_sources, 1), 3),
        # Raw counts for precise cross-run aggregation
        "primary_count": primary_count,
        "secondary_count": secondary_count,
        "none_count": none_count,
        "total_sources": total_sources,
        "sum_evidence_scores": raw_score_sum,
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


def _has_provenance_columns(csv_path: Path) -> bool:
    """Check if a CSV has the source_1 column in its header."""
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, [])
    return "source_1" in header


def score_directory(input_dir: Path) -> dict:
    """Score all CSVs in a directory and produce aggregate summary.

    Skips CSVs that lack provenance columns, plus colocated non-run outputs by
    filename: *_filtered.csv (which retains source_1 and would otherwise be scored
    as a spurious run alongside its base {stem}.csv — query_verification emits
    both into the same dir) and reconciliation_*/filtered_* prefixes for
    class-consistency with the sibling consumers (ticket 0499).
    """
    csv_files = sorted(
        f
        for f in input_dir.glob("*.csv")
        if not any(f.name.startswith(p) for p in _SKIP_PREFIXES)
        and not any(f.name.endswith(s) for s in _SKIP_SUFFIXES)
        and _has_provenance_columns(f)
    )
    if not csv_files:
        raise SystemExit(f"No sourced CSV files (with source_1 column) in: {input_dir}")

    runs = {}
    all_score_sum = 0
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

        all_plants += evidence["n_plants"]
        all_score_sum += evidence["sum_evidence_scores"]

        all_primary += evidence["primary_count"]
        all_secondary += evidence["secondary_count"]
        all_none += evidence["none_count"]
        all_total_sources += evidence["total_sources"]

        all_honesty_markers += honesty["n_with_epistemic_marker"]

    aggregate_mean = round(all_score_sum / max(all_plants, 1), 2)
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


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Score provenance quality from sourced runs")
    parser.add_argument(
        "--input",
        required=True,
        help="Directory containing extracted CSVs with provenance columns",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write summary JSON",
    )
    args = parser.parse_args(argv)

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
