"""Run aggregation primitives for AEDIST self-ensembling experiments.

Pipeline phase: analysis — consumes committed per-run CSVs from
experiments/outputs/exp1_batch2/*.csv and produces an aggregated plant list.

Three merge primitives:
- union: any run mentioned the plant → include
- majority: ≥ k of n runs mentioned the plant → include
- confidence_weighted: sum confidence scores across runs, threshold to include

Ticket 0375.
"""

import csv
import logging
from pathlib import Path

log = logging.getLogger(__name__)

# Categorical confidence → numeric score (for confidence-weighted aggregation).
_CONFIDENCE_SCORE: dict[str, float] = {
    "HIGH": 1.0,
    "MEDIUM": 0.5,
    "LOW": 0.25,
    "": 0.0,
}


def load_run_names(csv_path: Path) -> list[str]:
    """Return the list of plant names from a single-run CSV file."""
    names: list[str] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("name", "").strip()
            if name:
                names.append(name)
    return names


def load_run_confidence(csv_path: Path) -> dict[str, float]:
    """Return {plant_name: confidence_score} from a single-run CSV file.

    Uses the 'confidence' column (HIGH/MEDIUM/LOW). Plants without a confidence
    entry receive score 0.0.
    """
    scores: dict[str, float] = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("name", "").strip()
            if not name:
                continue
            conf_raw = row.get("confidence", "").strip().upper()
            scores[name] = _CONFIDENCE_SCORE.get(conf_raw, 0.0)
    return scores


def merge_union(run_name_lists: list[list[str]]) -> list[str]:
    """Union aggregation: include a plant if any run mentioned it.

    Returns a sorted list of unique plant names.
    """
    seen: set[str] = set()
    for names in run_name_lists:
        seen.update(names)
    return sorted(seen)


def merge_majority(run_name_lists: list[list[str]], k: int) -> list[str]:
    """Majority aggregation: include a plant if ≥ k runs mentioned it.

    Args:
        run_name_lists: list of per-run plant name lists.
        k: minimum number of runs that must mention a plant.

    Returns a sorted list of plant names that appear in ≥ k runs.
    """
    from collections import Counter

    counts: Counter[str] = Counter()
    for names in run_name_lists:
        # Count each name once per run (not total occurrences within a run).
        counts.update(set(names))
    return sorted(name for name, cnt in counts.items() if cnt >= k)


def merge_confidence_weighted(
    run_confidence_maps: list[dict[str, float]],
    threshold: float,
) -> list[str]:
    """Confidence-weighted aggregation: sum per-run confidence scores and threshold.

    Args:
        run_confidence_maps: list of {plant_name: score} dicts (one per run).
        threshold: minimum summed score to include a plant.

    Returns a sorted list of plant names whose summed score ≥ threshold.
    Cells without per-plant confidence data (all scores 0.0) are marked N/A
    by returning an empty list; callers should check for this case via
    has_confidence_data().
    """
    from collections import defaultdict

    total: dict[str, float] = defaultdict(float)
    for conf_map in run_confidence_maps:
        for name, score in conf_map.items():
            total[name] += score
    return sorted(name for name, score in total.items() if score >= threshold)


def has_confidence_data(run_confidence_maps: list[dict[str, float]]) -> bool:
    """Return True if at least one run has any non-zero confidence scores.

    Used to determine whether confidence-weighted aggregation is meaningful
    (as opposed to N/A when records lack per-plant confidence values).
    """
    return any(any(v > 0 for v in conf_map.values()) for conf_map in run_confidence_maps)
