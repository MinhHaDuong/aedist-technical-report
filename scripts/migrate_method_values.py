"""Migrate measurements.jsonl method vocabulary to the new namespace (ticket 0120).

Migration table:
    single          -> method=direct,            prompt_version=extract
    frontier        -> method=direct,            prompt_version=complete
    frontier_scenarios -> method=direct,         prompt_version=scenarios (via result_file)
    web             -> method=rag_livesearch,     prompt_version=extract
    rag             -> method=rag,               prompt_version=extract
    decomposed      -> method=rag,               prompt_version=per_fuel
    sourced         -> method=rag,               prompt_version=cited
    multiturn       -> method=direct+multiturn,  prompt_version=followups
    verification    -> method=rag+verification,  prompt_version=per_fuel

Idempotent: if a record already has a new-vocabulary method value, it is
passed through unchanged. Running twice produces the same result.

Usage:
    python scripts/migrate_method_values.py --dry-run
    python scripts/migrate_method_values.py --backup
    python scripts/migrate_method_values.py  # in-place rewrite (no backup)
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

MEASUREMENTS_FILE = Path("measurements.jsonl")

# Old method -> (new method, new prompt_version)
# New-vocabulary method values are passed through unchanged.
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

# New-vocabulary method values — already migrated, pass through.
NEW_METHODS = {
    "direct",
    "rag",
    "rag_livesearch",
    "direct+multiturn",
    "rag+verification",
    "fusion",  # fusion is unchanged
}

# frontier_scenarios is not a method value; it is inferred from result_file.
# Records with method=frontier whose result_file contains "scenarios" get
# prompt_version=scenarios instead of complete.
FRONTIER_SCENARIOS_MARKER = "scenarios"


def migrate_record(record: dict) -> tuple[dict, bool]:
    """Return (migrated_record, changed) for one JSONL record.

    The record is mutated in-place only when changed=True. Returns a copy.
    """
    record = dict(record)  # shallow copy
    old_method = record.get("method")

    if old_method is None:
        return record, False

    if old_method in NEW_METHODS:
        # Already migrated — idempotent pass-through.
        return record, False

    if old_method not in METHOD_MIGRATION:
        print(
            f"  WARNING: unknown method {old_method!r} in {record.get('result_file', '?')}",
            file=sys.stderr,
        )
        return record, False

    new_method, default_pv = METHOD_MIGRATION[old_method]

    # Special case: frontier vs frontier_scenarios
    # Both had method=frontier in old vocabulary. Distinguish by result_file.
    if old_method == "frontier":
        result_file = record.get("result_file", "")
        if FRONTIER_SCENARIOS_MARKER in result_file:
            default_pv = "scenarios"

    # Build or update method_params
    mp = record.get("method_params", {})
    if isinstance(mp, dict):
        mp = dict(mp)
        # Only set prompt_version if not already set to a new-vocabulary value.
        existing_pv = mp.get("prompt_version")
        if existing_pv in (None, old_method, ""):
            mp["prompt_version"] = default_pv
        mp_updated = mp
    else:
        mp_updated = {"prompt_version": default_pv}

    record["method"] = new_method
    record["method_params"] = mp_updated

    return record, True


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate measurements.jsonl method vocabulary.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print changes without writing.",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Write measurements.jsonl.bak-{timestamp} before rewriting.",
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=MEASUREMENTS_FILE,
        help="Path to measurements.jsonl (default: measurements.jsonl).",
    )
    args = parser.parse_args()

    path: Path = args.file
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        sys.exit(1)

    lines = path.read_text(encoding="utf-8").splitlines()
    records = []
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            print(f"ERROR: line {i}: {exc}", file=sys.stderr)
            sys.exit(1)

    migrated = []
    n_changed = 0
    for record in records:
        new_record, changed = migrate_record(record)
        migrated.append(new_record)
        if changed:
            n_changed += 1
            if args.dry_run:
                rf = record.get("result_file", "?")
                old_m = record.get("method")
                new_m = new_record.get("method")
                new_pv = new_record.get("method_params", {}).get("prompt_version")
                print(f"  {rf}")
                print(f"    method: {old_m!r} -> {new_m!r}  prompt_version: {new_pv!r}")

    print(f"Records: {len(records)}, to migrate: {n_changed}")

    if args.dry_run:
        print("Dry run — no file written.")
        return

    if args.backup:
        ts = datetime.now().strftime("%Y%m%dT%H%M%S")
        backup_path = path.with_suffix(f".jsonl.bak-{ts}")
        backup_path.write_bytes(path.read_bytes())
        print(f"Backup written to {backup_path}")

    out_lines = [json.dumps(r, ensure_ascii=False) for r in migrated]
    path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print(f"Written {len(out_lines)} records to {path}")


if __name__ == "__main__":
    main()
