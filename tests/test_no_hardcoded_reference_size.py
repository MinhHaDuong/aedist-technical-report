"""No hardcoded reference-list size literal in render scripts.

Exit criterion of ticket 0447: the v2 adoption (163 -> 170 plants) surfaced
a class of bug -- hardcoded reference size in plot_*/tabulate_* scripts
(``axvline(x=163)``, ``"163 plants"`` labels, ylim that clips the reference
line). Four scripts were fixed in PR #767. This ratchet catches the class
at the source so it cannot recur.

Detection uses the same AST-based docstring/comment exclusion as
``test_no_hardcoded_reference_path.py``. Integer literals AND string
occurrences are caught via word-boundary regex on code lines (not just
AST integer constants), because the bug manifests both as ``axvline(x=163)``
and as ``f"163 plants"`` label strings.

Out of scope: ``set_ylim`` clipping forms contain no size literal, so a
textual ratchet cannot catch them -- visual inspection remains the guard.

Canonical source of truth: ``evaluate.reference_plant_count()``.
"""

import ast
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src" / "aedist"

# All historical and current reference sizes. The current literal hardcoded
# is the same bug with a different number -- the ratchet must catch all of them.
# v1 = 163, v2 = 170, v2.1 = 173.
FORBIDDEN_SIZES = {163, 170, 173}
_PATTERN = re.compile(r"\b(" + "|".join(str(n) for n in sorted(FORBIDDEN_SIZES)) + r")\b")

# Allowlist: (filename, set-of-allowed-values).
# tabulate_self_consistency.py uses 163 as a legacy v1 fallback for records
# that predate the n_reference field -- semantically correct, not a display bug.
# Value-scoped: only 163 is allowed; a future 170/173 in that file still trips.
ALLOWLIST: dict[str, set[int]] = {
    "tabulate_self_consistency.py": {163},
}


def _docstring_lines(tree: ast.Module) -> set[int]:
    """Line numbers spanned by docstrings (module/class/function level)."""
    lines: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(
            node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
        ):
            continue
        body = getattr(node, "body", [])
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            start = first.value.lineno
            end = first.value.end_lineno or start
            lines.update(range(start, end + 1))
    return lines


def _code_lines(path: Path) -> list[tuple[int, str]]:
    """Return (lineno, line) for lines that are neither comments nor docstrings."""
    source = path.read_text()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    docstring_lines = _docstring_lines(tree)
    result: list[tuple[int, str]] = []
    for i, line in enumerate(source.splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue  # comment line -- allowed
        if i in docstring_lines:
            continue  # inside a docstring -- allowed
        result.append((i, line))
    return result


def test_no_hardcoded_reference_size():
    """Forbidden reference-size literals must not appear in plot_*/tabulate_* code lines."""
    violations = []
    for pattern in ("plot_*.py", "tabulate_*.py"):
        for py_file in sorted(SRC_DIR.glob(pattern)):
            fname = py_file.name
            allowed_values = ALLOWLIST.get(fname, set())
            for lineno, line in _code_lines(py_file):
                match = _PATTERN.search(line)
                if match and int(match.group(1)) not in allowed_values:
                    rel = py_file.relative_to(REPO_ROOT)
                    violations.append(f"{rel}:{lineno}: {line.strip()}")

    assert not violations, (
        f"{len(violations)} hardcoded reference-size literal(s) in render scripts.\n"
        "Use evaluate.reference_plant_count() instead.\n"
        + "\n".join(f"  {v}" for v in violations)
    )
