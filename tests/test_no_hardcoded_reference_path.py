"""No hardcoded 'vietnam_thermal_v1.csv' outside config.py, docstrings, comments.

Exit criterion 1 of ticket 0419: a single source of truth for the default
reference path. The literal filename may only live in ``src/aedist/config.py``;
everywhere else modules import ``config.DEFAULT_REFERENCE``.

The filename can only appear inside a Python string literal, so exempting all
string literals would make this check vacuous. Instead we exempt only
*docstrings* (the first ``Expr``-wrapped string statement of a module, class, or
function) and ``#`` comments. Ordinary string literals — including path-building
expressions and ``help=`` strings — are checked.
"""

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src" / "aedist"
CONFIG_MODULE = SRC_DIR / "config.py"
TARGET = "vietnam_thermal_v1.csv"


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
            continue  # comment line — allowed
        if i in docstring_lines:
            continue  # inside a docstring — allowed
        result.append((i, line))
    return result


def test_no_hardcoded_reference_path():
    """TARGET must not appear in code lines of any src/aedist/*.py except config.py."""
    violations = []
    for py_file in sorted(SRC_DIR.glob("*.py")):
        if py_file == CONFIG_MODULE:
            continue  # config.py is the single allowed home
        for lineno, line in _code_lines(py_file):
            if TARGET in line:
                violations.append(f"{py_file.relative_to(REPO_ROOT)}:{lineno}: {line.strip()}")
    assert not violations, (
        f"{len(violations)} hardcoded reference path(s) outside config.py:\n"
        + "\n".join(f"  {v}" for v in violations)
    )


def test_config_default_reference_exists():
    """config.DEFAULT_REFERENCE must point to an existing file."""
    from aedist.config import DEFAULT_REFERENCE  # noqa: PLC0415

    assert DEFAULT_REFERENCE.exists(), (
        f"config.DEFAULT_REFERENCE points to a non-existent file: {DEFAULT_REFERENCE}"
    )
