#!/usr/bin/env python3
"""
Fix misplaced log entries in .erg ticket files.

Agents have been appending log entries at end-of-file (in the body section)
instead of into the log section (between --- log --- and --- body ---).

This script:
- Reads every .erg file in tickets/ and tickets/archive/
- Splits on --- body ---
- Extracts lines from the body section that match the log-entry pattern
- Moves those lines into the log section (appended before --- body ---)
- Writes the fixed file back

Idempotent: a second run produces no changes.
"""

import re
import sys
from pathlib import Path

LOG_ENTRY_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z \w+ (created|status|claimed|released|note|bump)"
)


def fix_erg_file(path: Path) -> bool:
    """
    Fix a single .erg file. Returns True if the file was modified.
    """
    content = path.read_text(encoding="utf-8")

    # Split into pre-body and body sections
    split_marker = "--- body ---"
    if split_marker not in content:
        return False  # No body section; skip

    pre_body, body = content.split(split_marker, 1)

    # Find misplaced log entries in body
    body_lines = body.split("\n")
    misplaced = []
    remaining_body_lines = []

    for line in body_lines:
        stripped = line.strip()
        if stripped and LOG_ENTRY_PATTERN.match(stripped):
            misplaced.append(stripped)
        else:
            remaining_body_lines.append(line)

    if not misplaced:
        return False  # Nothing to fix

    # Remove trailing blank lines from pre_body, then add misplaced entries,
    # then restore the blank line before --- body --- (standard format).
    pre_body_stripped = pre_body.rstrip("\n")
    # Append misplaced log entries to the log section
    extra_log = "\n".join(misplaced)
    new_pre_body = pre_body_stripped + "\n" + extra_log + "\n\n"

    # Rebuild body — drop leading blank line that often follows the marker
    new_body = "\n".join(remaining_body_lines)

    new_content = new_pre_body + split_marker + new_body
    path.write_text(new_content, encoding="utf-8")
    return True


def main() -> int:
    repo_root = Path(__file__).parent.parent
    tickets_dir = repo_root / "tickets"
    archive_dir = tickets_dir / "archive"

    dirs = [tickets_dir]
    if archive_dir.exists() and archive_dir.is_dir():
        dirs.append(archive_dir)

    fixed = []
    for d in dirs:
        for fpath in sorted(d.glob("*.erg")):
            if fix_erg_file(fpath):
                fixed.append(fpath.relative_to(repo_root))
                print(f"  fixed: {fpath.relative_to(repo_root)}")

    if fixed:
        print(f"\nFixed {len(fixed)} file(s).")
    else:
        print("No misplaced log entries found. Nothing to do.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
