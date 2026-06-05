"""Command-line tools for the aedist benchmark.

Pipeline phase: P2 (score & consolidate) — invoked by experiments/derived/score.mk.

Usage:
    aedist evaluate <system_file> [--reference <ref_csv>] [--output <dir>]
    aedist assemble <record_files>... --output <measurements.jsonl>

The ``evaluate`` command scores a single system output (CSV or qualitative
JSON) against the reference and writes a ``.record.json`` RunRecord plus a
reconciliation CSV.  Batch scheduling belongs in Make; see
``experiments/derived/score.mk`` for the pattern-rule orchestration.

The ``assemble`` command concatenates record JSON files into a single
``measurements.jsonl``.
"""

import argparse
import csv
import json
import logging
import re
import sys
from pathlib import Path

from pydantic import ValidationError

from .config import VN_THERMAL_PLANTS_RELEASE_CSV
from .metrics import BenchmarkMetrics, compute_metrics, format_metrics
from .reconcile import reconcile
from .schema import (
    FuelType,
    Method,
    MethodParams,
    Plant,
    PlantStatus,
    ResourceUse,
    ResultSummary,
    RunRecord,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

_FUEL_MAP = {
    "coal": FuelType.COAL,
    "gas": FuelType.GAS,
    "natural gas": FuelType.GAS,
    "local gas": FuelType.GAS,
    "local natural gas": FuelType.GAS,
    "lng": FuelType.IMPORTED_LNG,
    "imported lng": FuelType.IMPORTED_LNG,
    "imported gas": FuelType.IMPORTED_LNG,
    "oil": FuelType.OIL,
}

_STATUS_MAP = {
    "operational": PlantStatus.OPERATIONAL,
    "operating": PlantStatus.OPERATIONAL,
    "retired": PlantStatus.RETIRED,
    "constructing": PlantStatus.CONSTRUCTING,
    "construction": PlantStatus.CONSTRUCTING,
    "under construction": PlantStatus.CONSTRUCTING,
    "planned": PlantStatus.PLANNED,
    "proposed": PlantStatus.PROPOSED,
    "announced": PlantStatus.PROPOSED,
    "cancelled": PlantStatus.CANCELLED,
    "canceled": PlantStatus.CANCELLED,
    "shelved": PlantStatus.CANCELLED,
}


def _get(row: dict, col_map: dict, candidates: list[str]) -> str | None:
    for c in candidates:
        orig = col_map.get(c)
        if orig and row.get(orig):
            return row[orig]
    return None


def load_plants_csv(path: Path) -> list[Plant]:
    """Load a CSV file into a list of Plant objects."""
    plants: list[Plant] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return plants
        col_map = {c.strip().lower().replace(" ", "_"): c for c in reader.fieldnames}
        for row in reader:
            # Preference order: name > name_vi > name_en.  Vietnamese names
            # match the reference dataset better (diacritics aid fuzzy matching).
            name = _get(row, col_map, ["name", "name_vi", "name_en", "plant_name", "plant"])
            if not name:
                continue
            fuel_raw = _get(row, col_map, ["fuel", "fuel_type"])
            status_raw = _get(row, col_map, ["status", "construction_stage", "stage"])
            cod = _get(row, col_map, ["cod", "connection_date", "date"])
            province = _get(row, col_map, ["province", "location"])
            cap_raw = _get(row, col_map, ["capacity_mwe", "capacity", "generation_capacity"])

            fuel = (
                _FUEL_MAP.get(fuel_raw.strip().lower(), FuelType.UNKNOWN)
                if fuel_raw
                else FuelType.UNKNOWN
            )
            status = (
                _STATUS_MAP.get(status_raw.strip().lower(), PlantStatus.UNKNOWN)
                if status_raw
                else PlantStatus.UNKNOWN
            )

            cap = None
            if cap_raw:
                try:
                    cap = float(cap_raw.strip().replace(",", ""))
                except ValueError:
                    cap = None

            source_ref = _get(row, col_map, ["source_ref"])

            try:
                plants.append(
                    Plant(
                        name=name.strip(),
                        fuel=fuel,
                        status=status,
                        cod=cod.strip() if cod else None,
                        province=province.strip() if province else None,
                        capacity_mwe=cap,
                        source_ref=source_ref.strip() if source_ref else None,
                    )
                )
            except (ValueError, ValidationError):
                continue
    return plants


def plants_from_dicts(rows: list[dict]) -> list[Plant]:
    """Convert CSV row dicts to Plant objects via a temp file.

    Reuses load_plants_csv for header normalization and enum parsing.
    """
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        tmp = Path(f.name)
    try:
        return load_plants_csv(tmp)
    finally:
        tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Project root
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).parent.parent.parent


# ---------------------------------------------------------------------------
# Helpers shared with other modules
# ---------------------------------------------------------------------------


def _strip_run_suffix(name: str) -> str:
    """Remove -runN suffix from a model label: 'claude-opus-4.6-run1' -> 'claude-opus-4.6'."""
    return re.sub(r"-run\d+$", "", name)


def _infer_method(dir_name: str) -> Method:
    """Infer Method enum from output subdirectory name.

    Recognises both pre-0122 (legacy) directory names and new directory names.
    Always emits new-vocabulary Method values (ticket 0120).

    Legacy directory → new method:
        census / (default)       → direct
        frontier / frontier_*    → direct
        multiturn                → direct+multiturn
        rag / rag_*              → rag
        web                      → rag_livesearch
        decomposed / decomposed_*→ rag
        sourced                  → rag
        verification / *verify*  → rag+verification
    """
    if "multiturn" in dir_name:
        return Method.DIRECT_MULTITURN
    if "verification" in dir_name:
        return Method.RAG_VERIFICATION
    if "web" in dir_name:
        return Method.RAG_LIVESEARCH
    if "rag" in dir_name and "sourced" not in dir_name:
        return Method.RAG
    if "decomposed" in dir_name:
        return Method.RAG
    if "sourced" in dir_name:
        return Method.RAG
    if "frontier" in dir_name:
        return Method.DIRECT
    return Method.DIRECT


def _backfill_resource_use(record: RunRecord, json_path: Path) -> None:
    """Populate resource_use and model metadata from a companion JSON file."""

    raw = json.loads(json_path.read_text(encoding="utf-8"))
    usage = raw.get("usage") or {}
    # OpenRouter passes reasoning tokens under completion_tokens_details
    # (per-ticket 0195 the harness now preserves the full usage dict).
    # Surfaced as thinking_tokens — the same ResourceUse slot the direct-
    # adapter paths (Anthropic, OpenAI Responses, Qwen DashScope) populate.
    details = usage.get("completion_tokens_details") or {}
    thinking_tokens = details.get("reasoning_tokens") if isinstance(details, dict) else None
    record.resource_use = ResourceUse(
        wall_s=raw.get("wall_seconds") or raw.get("total_wall_seconds"),
        cost_usd=raw.get("cost_usd") or raw.get("total_cost_usd"),
        tokens_in=usage.get("prompt_tokens"),
        tokens_out=usage.get("completion_tokens"),
        thinking_tokens=thinking_tokens,
    )
    record.method_params.model = raw.get("model", record.method_params.model)
    extra = dict(raw.get("model_metadata") or {})
    # Surface per-sweep / per-model controls into the metrics dict via extra
    # (ticket 0175 / ADR-7): system_instruction declares the baseline
    # no-web-search regime; reasoning_effort is a per-model capability flag
    # (gpt-oss-*, qwen3-max). The 0139 batch (seed, provider_order, num_ctx,
    # web_search, finish_reason) makes JobSpec API params analyst-visible
    # without re-reading raw JSON.
    for key in (
        "system_instruction",
        "evidence_pack_manifest",
        "reasoning_effort",
        "seed",
        "provider_order",
        "num_ctx",
        "web_search",
        "finish_reason",
    ):
        if raw.get(key) is not None:
            extra[key] = raw[key]
    record.method_params.extra = extra or None
    if "temperature" in raw:
        record.method_params.temperature = raw["temperature"]
    if "max_tokens" in raw and raw["max_tokens"] is not None:
        record.method_params.max_tokens = raw["max_tokens"]
    # finish_reason promotes to first-class RunRecord field too (ticket 0139
    # Action 6). The extra-dict backfill above keeps the records_to_metrics
    # path stable; this assignment lets r.finish_reason take precedence in
    # measurements.records_to_metrics when both are populated.
    if raw.get("finish_reason") is not None and record.finish_reason is None:
        record.finish_reason = raw["finish_reason"]


def _rel_path(path: Path) -> str:
    """Return path relative to project root, falling back to str(path)."""
    try:
        return str(path.resolve().relative_to(_PROJECT_ROOT))
    except ValueError:
        return str(path)


def _write_record(record: RunRecord, out: Path, stem: str) -> Path:
    """Write a RunRecord to {out}/{stem}.record.json, return the path."""
    record_path = out / f"{stem}.record.json"
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(record.model_dump_json(indent=2, exclude_none=True), encoding="utf-8")
    return record_path


def _metrics_to_runrecord(
    metrics: BenchmarkMetrics,
    label: str,
    result_file: str,
) -> RunRecord:
    """Build a RunRecord from evaluation metrics.

    *result_file* should be a relative path (e.g. experiments/outputs/...).
    """
    condition = label.split("/")[0] if "/" in label else ""
    stem = label.rsplit("/", 1)[-1]
    method = _infer_method(condition)

    return RunRecord(
        method=method,
        method_params=MethodParams(
            model=_strip_run_suffix(stem),
            prompt_version=condition,
        ),
        result_file=result_file,
        result_summary=ResultSummary(
            n_plants=metrics.n_system,
            tp=metrics.n_matched,
            fp=metrics.n_hallucinated,
            fn=metrics.n_missed,
            f1=metrics.f1,
            fuel_accuracy=metrics.fuel_accuracy,
            status_accuracy=metrics.status_accuracy,
            province_accuracy=metrics.province_accuracy,
        ),
    )


# ---------------------------------------------------------------------------
# CLI: evaluate
# ---------------------------------------------------------------------------


def cmd_evaluate(args: argparse.Namespace) -> None:
    """Evaluate a single system output against the reference.

    Accepts a CSV (quantitative) or a JSON (qualitative, no CSV companion).
    Writes a ``{stem}.record.json`` RunRecord and, for CSV inputs, a
    reconciliation CSV.
    """
    system_path = Path(args.system_file)
    ref_path = Path(args.reference) if args.reference else VN_THERMAL_PLANTS_RELEASE_CSV

    if system_path.suffix == ".json":
        _evaluate_qualitative(system_path, args)
    else:
        _evaluate_csv_file(system_path, ref_path, args)


def _evaluate_csv_file(system_path: Path, ref_path: Path, args: argparse.Namespace) -> None:
    """Evaluate a CSV system output and write record + reconciliation."""
    reference = load_plants_csv(ref_path)
    system = load_plants_csv(system_path)

    log.info("Reference: %d plants from %s", len(reference), ref_path.name)
    log.info("System:    %d plants from %s", len(system), system_path.name)

    entries = reconcile(reference, system)
    metrics = compute_metrics(entries)
    log.info(format_metrics(metrics))

    if args.output:
        out = Path(args.output)
        label = f"{system_path.parent.name}/{system_path.stem}"
        record = _metrics_to_runrecord(metrics, label, _rel_path(system_path))

        # Mark empty system CSVs so they appear as status="empty" in the
        # measurements table rather than the default "ok".
        if len(system) == 0:
            record.result_summary.status = "empty"

        json_companion = system_path.with_suffix(".json")
        if json_companion.exists():
            _backfill_resource_use(record, json_companion)

        _save_reconciliation_csv(entries, out / f"reconciliation_{system_path.stem}.csv")
        record_path = _write_record(record, out, system_path.stem)
        log.info("Saved: %s, %s", out / f"reconciliation_{system_path.stem}.csv", record_path)


_REFUSAL_OPENERS = re.compile(
    r"^\s*(?:[⚠*#]+\s*)?(?:\*+)?\s*"
    r"(?:I (?:cannot|can(?:'|’)t|am unable to|won(?:'|’)t|will not|"
    r"do not have|don(?:'|’)t have)"
    r"|Critical Limitation"
    r"|Per (?:your|my) (?:constraints?|operational constraints))",
    re.IGNORECASE,
)


def _looks_like_refusal(response: str) -> bool:
    """Detect refusal-opener language in the first lines of a response.

    Refusals often include a token-gesture table after the decline text,
    which the table-presence heuristic alone misclassifies as 'error'.
    The semantic intent is decline regardless of trailing content shape.
    """
    head = response.lstrip()[:400]
    return bool(_REFUSAL_OPENERS.match(head))


def _classify_orphan(raw: dict) -> str:
    """Classify a JSON-only result (no CSV companion) into a status string.

    Returns one of: "empty", "refusal", "error".
    """
    from .extract import _extract_pipe_tables, extract_fenced_blocks

    # Extract response text (same logic as extract.py extract_one)
    response = raw.get("response")
    if (not response or not isinstance(response, str)) and "turns" in raw:
        turns = raw["turns"]
        assistant_turns = [t for t in turns if t.get("role") == "assistant"]
        if assistant_turns:
            response = "\n".join(t.get("content", "") for t in assistant_turns)

    if not isinstance(response, str) or not response.strip():
        return "empty"

    # Refusal language at the start of the response wins regardless of
    # whether the model bolted a token-gesture table onto the decline.
    # Semantic intent — the model declined to produce the requested
    # output — should classify as refusal, not error.
    if _looks_like_refusal(response):
        return "refusal"

    # Only use strong table signals (fenced blocks, pipe tables).
    # The inline CSV fallback is too aggressive for classification —
    # comma-separated phrases in refusal prose trigger false positives.
    candidates = extract_fenced_blocks(response)
    candidates.extend(_extract_pipe_tables(response))

    return "error" if candidates else "refusal"


def _evaluate_qualitative(json_path: Path, args: argparse.Namespace) -> None:
    """Create a RunRecord from a JSON-only result (no CSV companion)."""
    try:
        raw = json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        log.warning("Skipping unreadable JSON: %s", json_path)
        return

    if "model" not in raw:
        log.warning("Skipping JSON without model field: %s", json_path)
        return

    status = _classify_orphan(raw)
    dir_name = json_path.parent.name
    record = RunRecord(
        method=_infer_method(dir_name),
        method_params=MethodParams(
            model=raw["model"],
            prompt_version=dir_name,
        ),
        result_file=_rel_path(json_path),
        result_summary=ResultSummary(status=status),
    )
    _backfill_resource_use(record, json_path)

    if args.output:
        out = Path(args.output)
        _write_record(record, out, json_path.stem)
        log.info(
            "%s/%s  %s  $%.4f",
            dir_name,
            json_path.stem,
            status,
            record.resource_use.cost_usd or 0,
        )


# ---------------------------------------------------------------------------
# CLI: assemble
# ---------------------------------------------------------------------------


def cmd_assemble(args: argparse.Namespace) -> None:
    """Assemble record JSONs into measurements.jsonl.

    At assemble-time this is the read-into-measurements trust boundary
    (ticket 0072). For each record with a ``result_file`` pointer to a
    raw provider JSON, run ``validate_run()`` on the raw body and attach
    the result as ``RunRecord.validation``. Records with missing raw JSON
    (e.g. historical orphans) are left with ``validation=None`` and flow
    through unchanged; downstream consumers should treat ``None`` as
    "unknown, do not filter".
    """
    from .validate import validate_run

    records = []
    for path_str in args.record_files:
        p = Path(path_str)
        if not p.exists():
            log.warning("Skipping missing record file: %s", p)
            continue
        raw = json.loads(p.read_text(encoding="utf-8"))
        record = RunRecord.model_validate(raw)
        record.validation = _validate_companion_raw(record, p, validate_run)
        records.append(record)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    RunRecord.save_jsonl(records, out)
    log.info("Assembled %d records -> %s", len(records), out)


def _validate_companion_raw(record: RunRecord, record_path: Path, validate_run) -> dict | None:
    """Locate the raw provider JSON for a record and validate it.

    Real CSV-backed records store ``result_file`` as the ``.csv`` companion
    path (see ``_evaluate_csv_file``). The raw provider JSON lives at the
    same stem with a ``.json`` suffix. Qualitative/JSON-only records (see
    ``_evaluate_qualitative``) already point ``result_file`` at a ``.json``
    file; leave those unchanged.

    The path is stored relative to the repo root, but at test time we may
    be running in an arbitrary working directory, so also try alongside
    the record file itself. If no candidate exists, return None (validation
    unknown — downstream treats this as "do not filter").
    """
    if not record.result_file:
        return None
    result_path = Path(record.result_file)
    if result_path.suffix == ".json":
        raw_name = result_path
    else:
        raw_name = result_path.with_suffix(".json")
    candidates = [raw_name, record_path.parent / raw_name.name]
    for candidate in candidates:
        if candidate.suffix != ".json" or not candidate.exists():
            continue
        try:
            raw_body = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return validate_run(raw_body).to_dict()
    return None


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


def _save_reconciliation_csv(entries: list, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "match_type",
                "reference_name",
                "system_name",
                "reference_province",
                "system_province",
                "reference_fuel",
                "system_fuel",
                "reference_capacity_mwe",
                "system_capacity_mwe",
                "capacity_diff_pct",
                "fuel_match",
                "status_match",
                "province_match",
                "reference_source_ref",
                "system_source_ref",
                "similarity_score",
            ]
        )
        for e in entries:
            w.writerow(
                [
                    e.match_type.value,
                    e.reference_name,
                    e.system_name,
                    e.reference_province,
                    e.system_province,
                    e.reference_fuel,
                    e.system_fuel,
                    e.reference_capacity_mwe,
                    e.system_capacity_mwe,
                    e.capacity_diff_pct,
                    e.fuel_match,
                    e.status_match,
                    e.province_match,
                    e.reference_source_ref,
                    e.system_source_ref,
                    e.similarity_score,
                ]
            )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(prog="aedist", description="AEDIST benchmark tools")
    sub = parser.add_subparsers(dest="command")

    p_eval = sub.add_parser("evaluate", help="Evaluate one system output (CSV or JSON)")
    p_eval.add_argument("system_file", help="Path to system output CSV or qualitative JSON")
    p_eval.add_argument("--reference", help="Path to reference CSV")
    p_eval.add_argument("--output", help="Directory for reconciliation & record output")

    p_asm = sub.add_parser("assemble", help="Assemble record JSONs into measurements.jsonl")
    p_asm.add_argument("record_files", nargs="+", help="Paths to .record.json files")
    p_asm.add_argument("--output", required=True, help="Path to output measurements.jsonl")

    args = parser.parse_args()
    if args.command == "evaluate":
        cmd_evaluate(args)
    elif args.command == "assemble":
        cmd_assemble(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
