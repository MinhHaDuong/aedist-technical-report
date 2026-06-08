"""JSON EOF newline policy: all single-object JSON writers must append exactly one trailing newline.

Project stance (see .claude/rules/workflow.md § "JSON EOF newline policy"):
- json.dump(x, f, ...) must be followed by f.write("\\n") on the next non-blank line.
- .write_text(json.dumps(...)) must end with + "\\n".
- .write_text(model.model_dump_json(...)) must end with + "\\n".

JSONL writers (to_jsonl_line() + "\\n" per record) are exempt.

Verification command:
    pytest -m adherence tests/test_json_eof_newline.py
"""

import re
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent


def _tracked_python_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [
        REPO_ROOT / f
        for f in result.stdout.split("\0")
        if f.endswith(".py") and not f.startswith("tests/")
    ]


# Matches write_text(json.dumps(...)) or write_text(model.model_dump_json(...))
# that does NOT already end with + "\n" before the closing paren/comma.
_WRITE_TEXT_DUMPS_RE = re.compile(
    r'\.write_text\(\s*(?:json\.dumps|[\w.]+\.model_dump_json)\s*\(',
)

# Matches write_text calls that already have + "\n" somewhere before encoding=
_ALREADY_NEWLINE_RE = re.compile(r'\+\s*"\\n"')


def _check_write_text_violations(path: Path) -> list[str]:
    """Return list of 'file:lineno' for write_text(json.dumps/model_dump_json)
    calls that don't contain + "\\n"."""
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    violations = []

    i = 0
    while i < len(lines):
        if _WRITE_TEXT_DUMPS_RE.search(lines[i]):
            # Gather the full statement (may span multiple lines)
            stmt_lines = []
            depth = 0
            j = i
            while j < len(lines):
                stmt_lines.append(lines[j])
                depth += lines[j].count("(") - lines[j].count(")")
                j += 1
                if depth <= 0:
                    break
            stmt = "\n".join(stmt_lines)
            if not _ALREADY_NEWLINE_RE.search(stmt):
                rel = path.relative_to(REPO_ROOT)
                violations.append(f"{rel}:{i + 1}")
        i += 1

    return violations


def test_write_text_json_has_trailing_newline():
    """write_text(json.dumps(...)) and write_text(model_dump_json(...)) must include + '\\n'."""
    all_violations = []
    for py_file in _tracked_python_files():
        all_violations.extend(_check_write_text_violations(py_file))

    assert not all_violations, (
        f"{len(all_violations)} write_text JSON call(s) missing trailing newline "
        f"(see .claude/rules/workflow.md § JSON EOF newline policy):\n"
        + "\n".join(f"  {v}" for v in sorted(all_violations))
    )


def test_json_dump_to_file_has_trailing_newline():
    """json.dump(x, f, ...) calls must be followed by f.write('\\n').

    Checks that every json.dump( line in a 'with open(... "w") as f:' context
    has f.write("\\n") (or fh.write / handle.write) on the next non-blank,
    non-comment line within the same indentation block.
    """
    all_violations = []
    for py_file in _tracked_python_files():
        source = py_file.read_text(encoding="utf-8")
        lines = source.splitlines()
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Match json.dump( calls (not json.dumps)
            if not re.search(r"\bjson\.dump\s*\(", stripped):
                continue
            if "json.dumps" in stripped:
                continue
            # Look at the next non-blank, non-comment line
            j = i + 1
            while j < len(lines) and (
                not lines[j].strip() or lines[j].strip().startswith("#")
            ):
                j += 1
            if j >= len(lines):
                rel = py_file.relative_to(REPO_ROOT)
                all_violations.append(f"{rel}:{i + 1} (end of file after json.dump)")
                continue
            next_stripped = lines[j].strip()
            if not re.search(r'\.write\s*\(\s*"\\n"\s*\)', next_stripped):
                rel = py_file.relative_to(REPO_ROOT)
                all_violations.append(f"{rel}:{i + 1}")

    assert not all_violations, (
        f"{len(all_violations)} json.dump() call(s) not followed by .write('\\n') "
        f"(see .claude/rules/workflow.md § JSON EOF newline policy):\n"
        + "\n".join(f"  {v}" for v in sorted(all_violations))
    )
