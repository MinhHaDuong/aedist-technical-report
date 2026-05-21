"""Migrate .record.json files on disk to the post-0120 method vocabulary.

Companion to scripts/migrate_method_values.py (which targeted measurements.jsonl).
PR #286 migrated measurements.jsonl in place but never rewrote the source
.record.json files. As a result, any future `make rebuild-measurements` would
silently revert the migration by regenerating jsonl rows from un-migrated
.record.json sources. This script closes that loop.

Migration table (mirrors migrate_method_values.py):
    single          -> method=direct,           prompt_version=extract
    frontier        -> method=direct,           prompt_version=complete (scenarios if result_file marker)
    web             -> method=rag_livesearch,    prompt_version=extract
    rag             -> method=rag,              prompt_version=extract
    decomposed      -> method=rag,              prompt_version=per_fuel
    sourced         -> method=rag,              prompt_version=cited
    multiturn       -> method=direct+multiturn, prompt_version=followups
    verification    -> method=rag+verification, prompt_version=per_fuel

Idempotent: a record already on the new vocabulary is passed through unchanged.
"""

import argparse
import json
import sys
from pathlib import Path

METHOD_MIGRATION: dict[str, tuple[str, str]] = {
    "single": ("direct", "extract"),
    "frontier": ("direct", "complete"),
    "web": ("rag_livesearch", "extract"),
    "rag": ("rag", "extract"),
    "decomposed": ("rag", "per_fuel"),
    "sourced": ("rag", "cited"),
    "multiturn": ("direct+multiturn", "followups"),
    "verification": ("rag+verification", "per_fuel"),
}

NEW_METHODS = {
    "direct",
    "rag",
    "rag_livesearch",
    "direct+multiturn",
    "rag+verification",
    "fusion",
}

FRONTIER_SCENARIOS_MARKER = "scenarios"


def migrate_record(record: dict) -> tuple[dict, bool]:
    record = dict(record)
    old_method = record.get("method")
    if old_method is None or old_method in NEW_METHODS:
        return record, False
    if old_method not in METHOD_MIGRATION:
        return record, False
    new_method, default_pv = METHOD_MIGRATION[old_method]
    if old_method == "frontier":
        if FRONTIER_SCENARIOS_MARKER in record.get("result_file", ""):
            default_pv = "scenarios"
    mp = record.get("method_params", {})
    if isinstance(mp, dict):
        mp = dict(mp)
        if mp.get("prompt_version") in (None, old_method, ""):
            mp["prompt_version"] = default_pv
    else:
        mp = {"prompt_version": default_pv}
    record["method"] = new_method
    record["method_params"] = mp
    return record, True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Root directory containing experiments/outputs and experiments/derived (default: cwd).",
    )
    args = parser.parse_args()

    roots = [args.root / "experiments/outputs", args.root / "experiments/derived"]
    paths: list[Path] = []
    for r in roots:
        if r.exists():
            paths.extend(p for p in r.rglob("*.record.json") if "_extracted" not in p.parts)
    paths.sort()

    changed_count = 0
    skipped_count = 0
    unknown_methods: dict[str, int] = {}
    for path in paths:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"  SKIP unreadable: {path}: {e}", file=sys.stderr)
            skipped_count += 1
            continue
        new_record, changed = migrate_record(record)
        if not changed:
            old = record.get("method")
            if old and old not in NEW_METHODS and old not in METHOD_MIGRATION:
                unknown_methods[old] = unknown_methods.get(old, 0) + 1
            continue
        if args.dry_run:
            print(f"  WOULD MIGRATE {record.get('method')!r} -> {new_record['method']!r}: {path}")
        else:
            path.write_text(json.dumps(new_record, indent=2) + "\n", encoding="utf-8")
        changed_count += 1

    verb = "Would migrate" if args.dry_run else "Migrated"
    print(f"{verb} {changed_count} of {len(paths)} files ({skipped_count} unreadable).")
    if unknown_methods:
        print(f"Unknown methods seen: {unknown_methods}", file=sys.stderr)


if __name__ == "__main__":
    main()
