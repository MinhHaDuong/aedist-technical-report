"""Migrate result_file paths in measurements.jsonl to match renamed output directories (ticket 0122).

Migration table (path segment → new path segment):
    outputs/census/             -> outputs/direct_extract/
    outputs/frontier/           -> outputs/direct_complete/
    outputs/decomposed/         -> outputs/rag_per_fuel/
    outputs/decomposed_v2/      -> outputs/rag_per_fuel_v2/
    outputs/rag/                -> outputs/rag_extract/
    outputs/web/                -> outputs/rag_livesearch/
    outputs/sourced/            -> outputs/rag_cited/
    outputs/multiturn/          -> outputs/direct_multiturn/
    outputs/ablation/parametric/ -> outputs/ablation/direct/
    outputs/ablation/websearch/  -> outputs/ablation/livesearch/

Idempotent: records whose result_file already matches the new vocabulary are
passed through unchanged.

Usage:
    python scripts/migrate_result_paths.py --dry-run
    python scripts/migrate_result_paths.py --backup
    python scripts/migrate_result_paths.py   # in-place rewrite (no backup)
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

MEASUREMENTS_FILE = Path("measurements.jsonl")

# Order matters: longer/more-specific patterns must precede shorter ones that
# could be a prefix of them (e.g. decomposed_v2 before decomposed, rag_* new
# names must not be re-matched by the rag replacement).
PATH_REPLACEMENTS: list[tuple[str, str]] = [
    # ablation subdirs — most specific first
    ("outputs/ablation/parametric/", "outputs/ablation/direct/"),
    ("outputs/ablation/websearch/", "outputs/ablation/livesearch/"),
    # decomposed_v2 before decomposed
    ("outputs/decomposed_v2/", "outputs/rag_per_fuel_v2/"),
    ("outputs/decomposed/", "outputs/rag_per_fuel/"),
    # /rag/ must be anchored carefully so rag_extract / rag_per_fuel / rag_cited
    # (new vocab already in place) are not re-mangled.
    ("outputs/rag/", "outputs/rag_extract/"),
    # remaining top-level dirs
    ("outputs/census/", "outputs/direct_extract/"),
    ("outputs/frontier/", "outputs/direct_complete/"),
    ("outputs/web/", "outputs/rag_livesearch/"),
    ("outputs/sourced/", "outputs/rag_cited/"),
    ("outputs/multiturn/", "outputs/direct_multiturn/"),
]


def migrate_path(path: str) -> str:
    """Apply replacements to a single result_file path string.

    Idempotent: if no old-vocabulary segment is found, the path is returned
    unchanged.
    """
    for old, new in PATH_REPLACEMENTS:
        if old in path:
            return path.replace(old, new, 1)
    return path


def migrate_record(record: dict) -> tuple[dict, bool]:
    """Migrate result_file in one record. Returns (new_record, changed)."""
    rf = record.get("result_file")
    if rf is None:
        return record, False
    new_rf = migrate_path(rf)
    if new_rf == rf:
        return record, False
    new_record = dict(record)
    new_record["result_file"] = new_rf
    return new_record, True


def run(dry_run: bool, backup: bool) -> int:
    if not MEASUREMENTS_FILE.exists():
        print(f"ERROR: {MEASUREMENTS_FILE} not found. Run from the repo root.", file=sys.stderr)
        return 1

    lines = MEASUREMENTS_FILE.read_text(encoding="utf-8").splitlines(keepends=True)
    new_lines: list[str] = []
    changed_count = 0
    error_count = 0

    for lineno, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if not stripped:
            new_lines.append(raw)
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError as exc:
            print(f"  WARNING: line {lineno}: JSON parse error: {exc}", file=sys.stderr)
            new_lines.append(raw)
            error_count += 1
            continue

        new_record, changed = migrate_record(record)
        if changed:
            changed_count += 1
            old_rf = record.get("result_file", "")
            new_rf = new_record.get("result_file", "")
            if dry_run:
                print(f"  [DRY RUN] line {lineno}: {old_rf!r} -> {new_rf!r}")
            new_lines.append(json.dumps(new_record, ensure_ascii=False) + "\n")
        else:
            new_lines.append(raw)

    print(f"Records changed: {changed_count} / {len(lines)}")
    if error_count:
        print(f"Parse errors (lines left unchanged): {error_count}", file=sys.stderr)

    if dry_run:
        print("[DRY RUN] No files written.")
        return 0

    if backup:
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        backup_path = MEASUREMENTS_FILE.with_suffix(f".jsonl.bak-{ts}")
        backup_path.write_text(MEASUREMENTS_FILE.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Backup written: {backup_path}")

    MEASUREMENTS_FILE.write_text("".join(new_lines), encoding="utf-8")
    print(f"Wrote {MEASUREMENTS_FILE}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    parser.add_argument(
        "--backup", action="store_true", help="Write timestamped backup before rewriting"
    )
    args = parser.parse_args()

    sys.exit(run(dry_run=args.dry_run, backup=args.backup))


if __name__ == "__main__":
    main()
