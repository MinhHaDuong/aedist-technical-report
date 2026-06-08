"""Exp2 recognition matrix derivation — mart-layer loader for the four-arm matrix.

Produces the same ``RecognitionData`` contract as ``exp1_recognition`` so both
experiments feed the shared renderer in ``plot_exp1_matrix``.  The derivation
route goes through the mart JSONL (P2 outcome, never re-scored here) and the
paired markdown report files that the mart's ``result_file``/``parsed_table_file``
pointers reference.  Ingestion reuses ``score_ingest.ingest_run`` exactly as the
scorer does, giving consistency-by-common-cause with the mart's stored coverage
numbers (DAG rule 0436: no P3→P3 side-output edges).

The four arms and their canonical directory mapping come from the mart directly;
no arm→dir mapping is hardcoded here.
"""

import json
import logging
from pathlib import Path

from .evaluate import load_plants_csv, plants_from_dicts
from .exp1_recognition import RecognitionCell, RecognitionData
from .metrics import _MATCHED_TYPES
from .reconcile import reconcile
from .schema import MatchType
from .score_ingest import IngestionError, RunLocator, ingest_run

log = logging.getLogger(__name__)

# Arm → flat directory, derived from the mart (build_exp2_mart.py constants).
# Must match the paths stored in ``result_file`` pointers in exp2_mart.jsonl.
_ARM_FLAT_DIRS: dict[str, str] = {
    "naive": "experiments/derived/arm1_flat",
    "optimised": "experiments/derived/arm2_flat",
    "arm3": "experiments/derived/arm3_flat",
    "arm4": "experiments/derived/arm4_flat",
}


def load_exp2_recognition(
    mart_jsonl: Path,
    reference_path: Path,
    repo_root: Path,
    arm: str,
) -> RecognitionData:
    """Reconcile every Exp2 run record for one arm; return recognition cells and FP presence.

    Args:
        mart_jsonl: Path to the Exp2 mart JSONL (P2 outcome — not rebuilt here).
        reference_path: Path to the gold reference CSV
            (vietnam_thermal_plants_v2_classified.csv by default).
        repo_root: Repository root used to resolve relative artifact paths stored
            in the mart pointers.
        arm: One of ``naive``, ``optimised``, ``arm3``, ``arm4``.

    Returns:
        :class:`exp1_recognition.RecognitionData`.  ``cells`` holds one cell per
        (model, run, reference plant); ``recognized`` is True when the plant is
        matched (any of :data:`aedist.metrics._MATCHED_TYPES`), False when it is a
        reference-only miss.  ``fp_presence`` maps each ``(model, run)`` to its set
        of false-positive (SYSTEM_ONLY) system names.  ``size_class`` is always
        ``None`` for Exp2 rows (not stored in the mart).
    """
    if arm not in _ARM_FLAT_DIRS:
        raise ValueError(f"Unknown arm {arm!r}; expected one of {sorted(_ARM_FLAT_DIRS)}")

    arm_flat = repo_root / _ARM_FLAT_DIRS[arm]
    reference = load_plants_csv(reference_path)
    data = RecognitionData()

    with open(mart_jsonl) as f:
        records = [json.loads(line) for line in f]

    run_records = [r for r in records if r.get("record_kind") == "run" and r.get("arm") == arm]
    if not run_records:
        log.warning("No run records found in mart for arm=%r", arm)
        return data

    for record in sorted(run_records, key=lambda r: (r["model"], r["run"])):
        model = record["model"]
        run_num = record["run"]
        locator = RunLocator(arm=arm, model=model, run=run_num)

        # score_ingest expects naive_dir / optimised_dir / arm3_dir / arm4_dir kwargs.
        # Build the right kwarg name for the arm being loaded.
        if arm == "naive":
            ingest_kwargs: dict = {"naive_dir": arm_flat}
        elif arm == "optimised":
            ingest_kwargs = {"optimised_dir": arm_flat}
        elif arm == "arm3":
            ingest_kwargs = {"arm3_dir": arm_flat}
        elif arm == "arm4":
            ingest_kwargs = {"arm4_dir": arm_flat}
        else:
            ingest_kwargs = {}

        try:
            ingested = ingest_run(locator, **ingest_kwargs)
        except IngestionError as exc:
            log.warning("Skipping %s arm=%s run=%d: %s", model, arm, run_num, exc)
            continue

        system = plants_from_dicts(ingested.rows)
        entries = reconcile(reference, system)

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
                    run=run_num,
                    size_class=None,  # not stored in Exp2 mart records
                    plant_id=plant_id,
                    plant_name=plant.name,
                    status=plant.status.value if plant.status else "",
                    capacity_mw=plant.capacity_mwe or 0.0,
                    recognized=key in recognized,
                )
            )
        data.fp_presence[(model, run_num)] = fps

    return data
