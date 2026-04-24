#!/usr/bin/env python3
"""
Validator: check that no .erg ticket has log entries in the body section.

Log entries belong between --- log --- and --- body ---.
Appending log entries at end-of-file places them in the body section — this
is a spec violation that this script detects.

Usage:
    uv run python scripts/check_ticket_structure.py

Exit code:
    0  — all clear
    1  — one or more violations found
"""

import re
import sys
from pathlib import Path

LOG_ENTRY_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z \w+ (created|status|claimed|released|note|bump)"
)


def check_erg_file(path: Path) -> list[str]:
    """
    Return a list of violation messages for the given .erg file.
    """
    content = path.read_text(encoding="utf-8")

    if "--- body ---" not in content:
        return []  # No body section; skip (other validators handle missing separator)

    # Everything after the first --- body --- is the body section
    _pre, body = content.split("--- body ---", 1)

    violations = []
    for lineno, line in enumerate(body.splitlines(), start=1):
        stripped = line.strip()
        if stripped and LOG_ENTRY_PATTERN.match(stripped):
            violations.append(
                f"{path}: log entry found in body section (body line {lineno}): {stripped}"
            )
    return violations


def main() -> int:
    repo_root = Path(__file__).parent.parent
    tickets_dir = repo_root / "tickets"
    archive_dir = tickets_dir / "archive"

    dirs = [tickets_dir]
    if archive_dir.exists() and archive_dir.is_dir():
        dirs.append(archive_dir)

    all_violations: list[str] = []
    checked = 0
    for d in dirs:
        for fpath in sorted(d.glob("*.erg")):
            violations = check_erg_file(fpath)
            all_violations.extend(violations)
            checked += 1

    if all_violations:
        print(f"TICKET STRUCTURE CHECK FAILED ({len(all_violations)} violation(s)):")
        for v in all_violations:
            print(f"  {v}")
        print()
        print(
            "Fix: run 'uv run python scripts/fix_ticket_log_placement.py' to move"
            " misplaced log entries to the log section."
        )
        return 1

    print(f"Ticket structure OK ({checked} files checked).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
