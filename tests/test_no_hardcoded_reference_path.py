"""No hardcoded default-reference filename outside config.py, docstrings, comments.

Exit criterion 1 of ticket 0419 (extended by 0413's v2 adoption): a single
source of truth for the default reference path. The literal filename may only
live in ``src/aedist/config.py``; everywhere else modules import
``config.VN_THERMAL_PLANTS_RELEASE_CSV``. ``TARGET`` tracks the *current*
adopted default (v2) so the guard stays live.

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
# The adopted default reference filename (ticket 0413: v2 replaced v1). Tracking
# the *current* default keeps the guard live — if it lagged on the retired v1
# name, nothing would reference it and the check would pass while protecting
# nothing.
TARGET = "vietnam_thermal_plants_v2_classified.csv"


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
    """config.VN_THERMAL_PLANTS_RELEASE_CSV must point to an existing file."""
    from aedist.config import VN_THERMAL_PLANTS_RELEASE_CSV  # noqa: PLC0415

    assert VN_THERMAL_PLANTS_RELEASE_CSV.exists(), (
        f"config.VN_THERMAL_PLANTS_RELEASE_CSV points to a non-existent file: {VN_THERMAL_PLANTS_RELEASE_CSV}"
    )


def test_raw_snapshots_are_datestamped():
    """All files in raw/ (except README.md, import.sh) must have -YYYY-MM-DD.ext pattern."""
    import re

    raw = REPO_ROOT / "data" / "reference" / "raw"
    exempt = {"README.md", "import.sh"}
    pat = re.compile(r"-\d{4}-\d{2}-\d{2}\.[a-z0-9]+$")
    undated = [f.name for f in raw.iterdir()
               if f.name not in exempt and not pat.search(f.name)]
    assert undated == [], f"raw/ files without capture datestamp: {undated}"


def test_config_snapshot_path_exists():
    """config.VN_THERMAL_MASTER_SNAPSHOT_ODS must point to an existing file."""
    from aedist.config import VN_THERMAL_MASTER_SNAPSHOT_ODS  # noqa: PLC0415

    assert VN_THERMAL_MASTER_SNAPSHOT_ODS.exists(), (
        f"config.VN_THERMAL_MASTER_SNAPSHOT_ODS points to a non-existent file: {VN_THERMAL_MASTER_SNAPSHOT_ODS}"
    )


def test_acquire_mk_snapshot_path_not_hardcoded():
    """The acquire.mk extract recipe must consult the config snapshot pin.

    Ratchet for ticket 0430 (extends 0419's single-source-of-truth guard to the
    raw/ snapshot): the ``extract-reference-ods`` recipe must read its ODS input
    from ``config.VN_THERMAL_MASTER_SNAPSHOT_ODS`` rather than hardcoding a
    ``raw/pipeline*.ods`` literal. A hardcoded datestamped filename would silently
    diverge from the config pin on the next re-import.
    """
    import re  # noqa: PLC0415

    acquire_mk = REPO_ROOT / "experiments" / "acquire.mk"
    source = acquire_mk.read_text()

    # The recipe block: from the target line to the next blank line.
    recipe = []
    in_recipe = False
    for line in source.splitlines():
        if line.startswith("extract-reference-ods:"):
            in_recipe = True
            continue
        if in_recipe:
            if line.strip() == "":
                break
            recipe.append(line)
    assert recipe, "extract-reference-ods recipe not found in acquire.mk"

    recipe_text = "\n".join(recipe)
    # Recipe lines (not comments) must not hardcode a raw/pipeline*.ods literal.
    hardcoded = re.search(r"raw/pipeline[-.][^\s'\"]*\.ods", recipe_text)
    assert hardcoded is None, (
        "acquire.mk extract-reference-ods hardcodes a snapshot path "
        f"({hardcoded.group(0)!r}); read it from config.VN_THERMAL_MASTER_SNAPSHOT_ODS instead"
    )
    assert "VN_THERMAL_MASTER_SNAPSHOT_ODS" in recipe_text, (
        "acquire.mk extract-reference-ods must consult "
        "config.VN_THERMAL_MASTER_SNAPSHOT_ODS for the snapshot path"
    )
