"""Fix stale `result_file` paths inside .record.json files.

PR #354 et al. inherited a lineage of .record.json files where the
`result_file` field points at where the source CSV/JSON USED TO LIVE,
not where it currently lives. Symptom: `aedist.evaluate assemble` emits
jsonl rows whose result_file paths don't exist on disk — the "phantom
rows" surfaced by the Exp 1 result-table audit.

Fix: each .record.json's result_file should point to its own sibling
file (same directory, same stem, .csv preferred, .json fallback).

Idempotent: records already pointing at a real sibling are skipped.
"""

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def find_sibling(record_path: Path) -> Path | None:
    stem = record_path.name.removesuffix(".record.json")
    for ext in (".csv", ".json"):
        sib = record_path.parent / f"{stem}{ext}"
        if sib.exists():
            return sib
    return None


def rel_from_repo(p: Path) -> str:
    return str(p.resolve().relative_to(REPO_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()

    roots = [args.root / "experiments/outputs", args.root / "experiments/derived"]
    paths: list[Path] = []
    for r in roots:
        if r.exists():
            paths.extend(p for p in r.rglob("*.record.json") if "_extracted" not in p.parts)
    paths.sort()

    fixed = 0
    orphaned = 0
    unchanged = 0
    for path in paths:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        sibling = find_sibling(path)
        if sibling is None:
            orphaned += 1
            continue
        expected = rel_from_repo(sibling)
        actual = record.get("result_file")
        if actual == expected:
            unchanged += 1
            continue
        if args.dry_run:
            print(f"  {path.relative_to(args.root)}: {actual!r} -> {expected!r}")
        else:
            record["result_file"] = expected
            path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        fixed += 1

    verb = "Would fix" if args.dry_run else "Fixed"
    print(
        f"{verb} {fixed} stale paths; {unchanged} already-correct; {orphaned} orphan records (no sibling)."
    )


if __name__ == "__main__":
    main()
