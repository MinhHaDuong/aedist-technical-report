"""Exp1 recognition matrix derivation — shared library for figure 0373 and table 0434.

Common-cause consistency: both the recognition matrix figure (0373) and the
status difficulty table (0434) derive the per-(run × plant) recognition data
from this shared helper. No side-output chaining.
"""

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .evaluate import load_plants_csv, plants_from_dicts
from .reconcile import reconcile
from .schema import MatchType


@dataclass
class RecognitionCell:
    """One cell in the (run × plant) recognition matrix."""

    model: str
    run: int
    plant_name: str
    status: str
    capacity_mw: float
    recognized: bool  # True if TP, False if FN


def load_exp1_recognition_matrix(
    records_glob: str,
    reference_path: Path,
) -> list[RecognitionCell]:
    """Load per-(run × plant) recognition data for Exp1 direct/p1-base sweeps.

    Args:
        records_glob: Glob pattern for record.json files (e.g. "experiments/outputs/exp1_batch2/*.record.json")
        reference_path: Path to gold reference CSV (vietnam_thermal_v1.csv)

    Returns:
        List of RecognitionCell, one per (model, run, plant) combination.
        Only reference plants (TP + FN) are included; FPs are excluded.
        The 'recognized' field is True for TP, False for FN.
    """
    # Load reference plants
    reference = load_plants_csv(reference_path)
    ref_by_name = {p.name: p for p in reference}

    # Process each record
    cells = []
    for record_path in sorted(Path().glob(records_glob)):
        # Parse model and run from filename: "{model}-run{N}.record.json"
        stem = record_path.stem
        if not stem.endswith(".record"):
            stem = stem  # Already stripped
        parts = stem.rsplit("-run", 1)
        if len(parts) != 2:
            continue
        model = parts[0]
        run = int(parts[1].replace(".record", ""))

        # Load record and its CSV output
        with open(record_path) as f:
            record = json.load(f)
        result_file = Path(record["result_file"])
        if not result_file.exists():
            continue

        # Load model output and reconcile
        with open(result_file, newline="", encoding="utf-8") as f:
            model_rows = list(csv.DictReader(f))
        system = plants_from_dicts(model_rows)
        reconciliation = reconcile(reference, system)

        # Build per-plant recognition map for this run
        recognized_plants = set()
        for entry in reconciliation:
            # TP = EXACT or FUZZY match
            if entry.match_type in (MatchType.EXACT, MatchType.FUZZY):
                if entry.reference_name:
                    recognized_plants.add(entry.reference_name)

        # Emit one cell per reference plant
        for plant_name, plant in ref_by_name.items():
            cells.append(
                RecognitionCell(
                    model=model,
                    run=run,
                    plant_name=plant_name,
                    status=plant.status.value if plant.status else "",
                    capacity_mw=plant.capacity_mwe or 0.0,
                    recognized=plant_name in recognized_plants,
                )
            )

    return cells


def get_top_false_positives(
    records_glob: str,
    reference_path: Path,
    top_n: int = 40,
    seed: int = 42,
) -> list[tuple[str, int]]:
    """Get the top N most common false-positive plants across all runs.

    Args:
        records_glob: Glob pattern for record.json files
        reference_path: Path to gold reference CSV
        top_n: Number of FPs to return
        seed: Random seed for tie-breaking (rebuild-stable)

    Returns:
        List of (plant_name, count) tuples, sorted by count descending.
        Ties are shuffled with the given seed.
    """
    import random

    reference = load_plants_csv(reference_path)
    fp_counts: dict[str, int] = defaultdict(int)

    for record_path in sorted(Path().glob(records_glob)):
        with open(record_path) as f:
            record = json.load(f)
        result_file = Path(record["result_file"])
        if not result_file.exists():
            continue

        with open(result_file, newline="", encoding="utf-8") as f:
            model_rows = list(csv.DictReader(f))
        system = plants_from_dicts(model_rows)
        reconciliation = reconcile(reference, system)

        # Count system-only (FP) plants
        for entry in reconciliation:
            if entry.match_type == MatchType.SYSTEM_ONLY:
                if entry.system_name:
                    fp_counts[entry.system_name] += 1

    # Sort by count, shuffle ties with fixed seed
    items = list(fp_counts.items())
    random.seed(seed)
    random.shuffle(items)  # Shuffle first, then stable-sort by count
    items.sort(key=lambda x: x[1], reverse=True)

    return items[:top_n]
