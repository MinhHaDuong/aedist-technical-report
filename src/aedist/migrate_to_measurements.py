"""Migrate sweep output JSONs to measurements.jsonl (RunRecord rows).

Reads per-run query JSON files and optional all_metrics.json to produce
a canonical measurements.jsonl file using the RunRecord schema.

Usage:
    uv run python -m aedist.migrate_to_measurements \
        --queries outputs/sweep1_census/ \
        --mode single --sweep-name sweep1_census \
        --metrics results/sweep1_census/all_metrics.json \
        --output measurements.jsonl

Can be invoked multiple times with --append to accumulate runs from
different sweeps into a single measurements file.
"""

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from .schema import (
    Method,
    MethodParams,
    ResourceUse,
    ResultSummary,
    RunRecord,
)
from .tabulate_utils import strip_label as slug_from_label

log = logging.getLogger(__name__)


def _load_metrics_index(metrics_path: Path) -> dict[str, dict]:
    """Load all_metrics.json and index by slug (first entry wins)."""
    with open(metrics_path) as f:
        entries = json.load(f)
    index: dict[str, dict] = {}
    for entry in entries:
        slug = slug_from_label(entry["label"])
        if slug not in index:
            index[slug] = entry
    return index


def migrate_query_json(
    json_path: Path,
    method: Method,
    sweep_name: str,
    metrics_index: dict[str, dict] | None = None,
) -> RunRecord:
    """Convert a single query output JSON to a RunRecord."""
    record = json.loads(json_path.read_text(encoding="utf-8"))

    model_id = record["model"]
    usage = record.get("usage") or {}
    run_num = record.get("run", 1)

    model_short = slug_from_label(json_path.stem)
    label = f"{sweep_name}/{model_short}-run{run_num}"
    metrics = metrics_index.get(slug_from_label(label)) if metrics_index else None

    date_str = record.get("date", "")
    try:
        ts = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        ts = datetime.now(timezone.utc)

    return RunRecord(
        timestamp=ts,
        method=method,
        method_params=MethodParams(
            model=model_id,
            prompt_version=sweep_name,
            extra=record.get("model_metadata"),
        ),
        resource_use=ResourceUse(
            wall_s=record.get("wall_seconds"),
            cost_usd=record.get("cost_usd"),
            tokens_in=usage.get("prompt_tokens"),
            tokens_out=usage.get("completion_tokens"),
        ),
        result_file=str(json_path),
        result_summary=ResultSummary(
            status="ok" if record.get("response") else "empty",
            n_plants=metrics["n_system"] if metrics else None,
            tp=metrics["n_matched"] if metrics else None,
            fp=metrics["n_hallucinated"] if metrics else None,
            fn=metrics["n_missed"] if metrics else None,
            f1=metrics["f1"] if metrics else None,
        ),
    )


def migrate_sweep(
    query_dir: Path,
    method: Method,
    sweep_name: str,
    metrics_path: Path | None = None,
) -> list[RunRecord]:
    """Migrate all query JSONs from a sweep output directory."""
    metrics_index = _load_metrics_index(metrics_path) if metrics_path else None

    records = []
    for json_path in sorted(query_dir.glob("*-run*.json")):
        try:
            rec = migrate_query_json(json_path, method, sweep_name, metrics_index)
            records.append(rec)
            log.info("  Migrated: %s", json_path.name)
        except Exception as e:
            log.error("  Failed: %s — %s", json_path.name, e)

    return records


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Migrate sweep results to measurements.jsonl"
    )
    parser.add_argument(
        "--queries", required=True, type=Path,
        help="Directory containing query output JSON files",
    )
    parser.add_argument(
        "--mode", required=True, choices=[m.value for m in Method],
        help="Sweep method (single, multiturn, rag, web)",
    )
    parser.add_argument(
        "--sweep-name", required=True,
        help="Sweep identifier (e.g. sweep1_census)",
    )
    parser.add_argument(
        "--metrics", type=Path, default=None,
        help="Path to all_metrics.json (optional, for evaluation results)",
    )
    parser.add_argument(
        "--output", required=True, type=Path,
        help="Output measurements.jsonl path",
    )
    parser.add_argument(
        "--append", action="store_true",
        help="Append to existing file instead of overwriting",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    method = Method(args.mode)
    records = migrate_sweep(args.queries, method, args.sweep_name, args.metrics)

    if not records:
        log.warning("No records migrated.")
        return

    log.info("Migrated %d records", len(records))

    if args.append and args.output.exists():
        existing = RunRecord.load_jsonl(args.output)
        records = existing + records

    RunRecord.save_jsonl(records, args.output)
    log.info("Wrote %d records to %s", len(records), args.output)


if __name__ == "__main__":
    main()
