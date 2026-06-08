"""No name synthesis in the reference pipeline outside the GEM allowlist.

Author rule (ticket 0416, absolute): a project name is never synthesized —
parentage and identity are data, not inference.  PR #760 removed the last
name-parsing from the HDM/v2 chain, and this ratchet prevents regression.

"Name synthesis" means *decomposing* a name string to derive a different
name — pandas str accessor decomposition (``.str.extract``, ``.str.split``,
``.str.partition``, ``.str.findall``, ``.str.replace``) applied to columns
whose name contains "name" (case-insensitive).  The historically-attested
threat is ``HDM_aggregate.normalize_plant_name`` which parsed "X Unit N" off
a name string to find the parent, and ``GEM_aggregate.aggregate_table``
which ``str.extract``-s Phase information from "Unit name" and appends it to
"Plant name".

Legitimate operations that are NOT flagged:
  - Concatenating address columns into the attested designation
    (``extract_ods.derive_name``: ``f"{plant} {unit}"``).
  - ``.strip()``, ``.casefold()``, ``unicodedata.normalize()`` on names
    (normalisation, not synthesis).
  - ``.join()`` / ``.split(",")`` on ``units_included`` (comma-separated
    lists, not name derivation).

``GEM_aggregate.py`` is allowlisted because it still performs name parsing
(its rework is ticket 0429, out of preprint scope).

Mirrors the AST-scan pattern of ``test_no_hardcoded_reference_path.py``.
"""

import ast
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
REFERENCE_DIR = REPO_ROOT / "data" / "reference"

# GEM_aggregate.py is allowlisted: it still parses names (rework = ticket 0429).
ALLOWLISTED = {"GEM_aggregate.py"}

# ----- Detection predicates ------------------------------------------------
#
# We scan for **pandas str accessor decomposition** on a column whose name
# contains "name" (case-insensitive): .str.extract, .str.split,
# .str.partition, .str.findall, .str.replace (regex-based).
#
# This is the historically-attested threat vector: GEM_aggregate used
# ``df["Unit name"].str.extract(r"(Phase ...)")`` and the deleted
# HDM_aggregate parsed name strings via similar pandas ops.
#
# The source-text scan is intentionally conservative: it looks for
# ``["...name..."].str.<decompose>`` patterns on non-comment,
# non-docstring code lines. It does NOT flag bare concatenation, strip,
# casefold, or unicodedata.normalize — those are normalisation, not
# synthesis. ``extract_ods.derive_name`` (``f"{plant} {unit}"``)
# composes the attested designation from address columns and is
# deliberately not caught.

# Pandas .str decomposition methods that parse/split a string value.
_PANDAS_DECOMPOSE = {"extract", "split", "partition", "findall", "replace"}

# Pattern: ["<something>name<something>"].str.<decompose_method>
# Catches df["Unit name"].str.extract(...), dataframe["Plant name"].str.split(...)
_PAT_PANDAS_NAME_DECOMPOSE = re.compile(
    r"""\[["'][^"']*name[^"']*["']\]"""   # ["...name..."]
    r"""\.str\."""                          # .str.
    r"""("""
    + "|".join(_PANDAS_DECOMPOSE)
    + r""")""",
    re.IGNORECASE,
)


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
            continue
        if i in docstring_lines:
            continue
        result.append((i, line))
    return result


def test_no_name_synthesis():
    """No name-decomposition ops on name columns in data/reference/*.py (except allowlist)."""
    violations: list[str] = []
    py_files = sorted(REFERENCE_DIR.glob("*.py"))
    assert py_files, f"No .py files found in {REFERENCE_DIR}"

    for py_file in py_files:
        if py_file.name in ALLOWLISTED:
            continue
        for lineno, line in _code_lines(py_file):
            match = _PAT_PANDAS_NAME_DECOMPOSE.search(line)
            if match:
                violations.append(
                    f"{py_file.relative_to(REPO_ROOT)}:{lineno}: "
                    f"pandas name-decomposition ({match.group()}): {line.strip()}"
                )

    assert not violations, (
        f"Name synthesis detected in {len(violations)} location(s) outside the "
        f"allowlist ({', '.join(sorted(ALLOWLISTED))}). The author rule (ticket "
        f"0416) forbids parsing/decomposing name strings to derive new names — "
        f"parentage is data, not inference:\n"
        + "\n".join(f"  {v}" for v in violations)
    )
