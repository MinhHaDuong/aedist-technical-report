"""Exp1 recognition matrix derivation — shared library for figure 0373 and table 0434.

Common-cause consistency: both the recognition matrix figure (0373) and the
status difficulty table (0434) derive the per-(run x plant) recognition data
from this shared helper. No side-output chaining: each consumer imports this
library and builds its own view; neither reads the other's output file.

The single entry point :func:`load_exp1_recognition` reconciles every record
once and returns *both* the per-(run x reference-plant) recognition cells and
the per-run false-positive presence, so the figure's TP view and its FP view
cannot silently diverge.
"""

import csv
import glob as globmod
import json
import random
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .evaluate import load_plants_csv, plants_from_dicts
from .metrics import _MATCHED_TYPES
from .reconcile import reconcile
from .schema import MatchType
from .util import normalize_model

# Status group ordering (author-ratified 2026-06-05): operational assets first
# (easiest to recall), then the pipeline statuses, ending with the
# historical/retired tail. Shared by the recognition matrix figure (0373,
# column bands) and the status difficulty table (0434, row order) so both
# consumers order statuses identically from one source — common cause, no
# producer-consumer chaining.
STATUS_ORDER = ["operational", "proposed", "planned", "constructing", "cancelled", "retired"]
# French display labels — shared by the recognition matrix figure (0373, column
# band annotations) and the status difficulty table (0434, row labels) so both
# consumers render the same language in the French-language report annex.
STATUS_LABELS = {
    "operational": "Opérationnelle",
    "proposed": "En projet",
    "planned": "Planifiée",
    "constructing": "En construction",
    "cancelled": "Annulée",
    "retired": "Retirée",
}


def status_rank(status: str) -> int:
    """Sort rank for a status group; unknown statuses sort last (stable tail)."""
    try:
        return STATUS_ORDER.index(status)
    except ValueError:
        return len(STATUS_ORDER)


@dataclass(frozen=True)
class RecognitionCell:
    """One cell in the (run x reference-plant) recognition matrix.

    ``plant_id`` is the reference plant's positional index in the loaded
    reference list. It distinguishes the two pairs of reference plants that
    share a name (Formosa phases differing by capacity/status) so each gets its
    own matrix column — keying columns by name alone would silently merge them
    and miscount the reference (161 vs the 163 distinct plants).
    """

    model: str
    run: int
    size_class: str | None
    plant_id: int
    plant_name: str
    status: str
    capacity_mw: float
    recognized: bool  # True if matched (TP), False if missed (FN)


@dataclass
class RecognitionData:
    """Result of reconciling all Exp1 records once.

    Attributes:
        cells: one RecognitionCell per (model, run, reference plant).
        fp_presence: maps (model, run) -> set of false-positive system names
            emitted by that run (SYSTEM_ONLY matches).
    """

    cells: list[RecognitionCell] = field(default_factory=list)
    fp_presence: dict[tuple[str, int], set[str]] = field(default_factory=dict)


def _parse_model_run(record_path: Path, record: dict) -> tuple[str, int] | None:
    """Resolve (model, run) for a record.

    Model comes from the record's ``method_params.model`` (normalized), so it
    matches measurements.jsonl rather than the filename. Run number is parsed
    from the ``-run{N}`` filename suffix.
    """
    model = normalize_model(record.get("method_params", {}).get("model", ""))
    stem = record_path.stem
    if stem.endswith(".record"):
        stem = stem[: -len(".record")]
    parts = stem.rsplit("-run", 1)
    if len(parts) != 2 or not parts[1].isdigit():
        return None
    return (model, int(parts[1]))


def load_exp1_recognition(
    records_glob: str,
    reference_path: Path,
) -> RecognitionData:
    """Reconcile every Exp1 record once; return recognition cells and FP presence.

    Args:
        records_glob: Glob for record.json files
            (e.g. ``experiments/outputs/exp1_batch2/*.record.json``).
        reference_path: Path to the gold reference CSV (vietnam_thermal_v1.csv).

    Returns:
        :class:`RecognitionData`. ``cells`` holds one cell per
        (model, run, reference plant); ``recognized`` is True when the plant is
        matched (any of :data:`aedist.metrics._MATCHED_TYPES`), False when it is
        a reference-only miss. ``fp_presence`` maps each run to its set of
        false-positive (SYSTEM_ONLY) system names.
    """
    reference = load_plants_csv(reference_path)
    data = RecognitionData()

    for record_str in sorted(globmod.glob(records_glob)):
        record_path = Path(record_str)
        with open(record_path) as f:
            record = json.load(f)
        model_run = _parse_model_run(record_path, record)
        if model_run is None:
            continue
        model, run = model_run
        size_class = (record.get("method_params", {}).get("extra") or {}).get("size_class")

        result_file = Path(record["result_file"])
        if not result_file.exists():
            continue
        with open(result_file, newline="", encoding="utf-8") as f:
            model_rows = list(csv.DictReader(f))
        system = plants_from_dicts(model_rows)
        entries = reconcile(reference, system)

        # Recognized reference plants, keyed by (name, capacity) so the two
        # same-name Formosa phases are told apart wherever capacity differs.
        recognized: set[tuple[str, float]] = set()
        fps: set[str] = set()
        for entry in entries:
            if entry.match_type in _MATCHED_TYPES and entry.reference_name:
                recognized.add((entry.reference_name, round(entry.reference_capacity_mwe or 0.0, 1)))
            elif entry.match_type == MatchType.SYSTEM_ONLY and entry.system_name:
                fps.add(entry.system_name)

        for plant_id, plant in enumerate(reference):
            key = (plant.name, round(plant.capacity_mwe or 0.0, 1))
            data.cells.append(
                RecognitionCell(
                    model=model,
                    run=run,
                    size_class=size_class,
                    plant_id=plant_id,
                    plant_name=plant.name,
                    status=plant.status.value if plant.status else "",
                    capacity_mw=plant.capacity_mwe or 0.0,
                    recognized=key in recognized,
                )
            )
        data.fp_presence[(model, run)] = fps

    return data


def top_false_positives(
    fp_presence: dict[tuple[str, int], set[str]],
    top_n: int = 40,
    seed: int = 42,
) -> list[tuple[str, int]]:
    """Return the top-N most common false positives across all runs.

    Counts how many runs emitted each false-positive system name, sorts by
    count descending, and breaks ties with a fixed-seed shuffle so the result
    is rebuild-stable.

    Args:
        fp_presence: per-run FP sets from :func:`load_exp1_recognition`.
        top_n: number of false positives to return.
        seed: random seed for tie-breaking.

    Returns:
        List of ``(system_name, run_count)`` tuples, longest first.
    """
    counts: Counter[str] = Counter()
    for fps in fp_presence.values():
        counts.update(fps)

    # Sort by name first so the input order is independent of set-iteration /
    # hash randomization across processes; then the seeded shuffle and the
    # stable count-sort make the tie order fully rebuild-stable.
    items = sorted(counts.items(), key=lambda kv: kv[0])
    rng = random.Random(seed)
    rng.shuffle(items)
    items.sort(key=lambda kv: kv[1], reverse=True)
    return items[:top_n]
