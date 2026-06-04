"""Every generated figure/table consumed by the build must have a producer.

The build is split into two workpackages (see slides/Makefile header):

  * analysis  -- experiments/*.mk, run on demand with data/network access,
                 writes artifacts into report/inputs/generated/ (the single
                 P3 deliverable tree; the slides-side tree was retired, 0408).
  * writing   -- Makefile + report/Makefile + slides/Makefile, compiles the
                 PDFs from those artifacts treated as committed inputs.

A producing rule may therefore live in *any* of the makefiles. This test
takes the UNION of all makefiles, expands variables (score.mk and render.mk
name their targets through $(ANALYSIS_*) variables, so a literal scan misses
them), and
asserts that every generated .pdf/.tex used as a prerequisite is the target
of some rule somewhere in that union. Grouped targets (`a b &:`) count as
producers of each member.

This guards the analysis<->writing seam: an artifact may be committed, but if
no makefile knows how to (re)build it, it is orphaned from the DAG and silently
goes stale.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent

# A generated artifact lives under <report|slides>/inputs/generated/ and is a
# figure (.pdf) or a LaTeX include (.tex). CSV data marts are out of scope.
GEN_RE = re.compile(r"(report|slides)/inputs/generated/([^/\s:*?)]+\.(?:pdf|tex))")
ASSIGN_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(:=|\?=|\+=|=)\s*(.*)$")
VAR_REF_RE = re.compile(r"\$\(([A-Za-z_][A-Za-z0-9_]*)\)")


def _makefiles() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    files = []
    for rel in out.split("\0"):
        if not rel or rel.startswith("tickets/"):
            continue
        name = rel.rsplit("/", 1)[-1]
        if name == "Makefile" or rel.endswith(".mk"):
            files.append(REPO_ROOT / rel)
    return files


def _logical_lines(path: Path) -> list[str]:
    return path.read_text().replace("\\\n", " ").splitlines()


def _expand(value: str, variables: dict[str, str], _depth: int = 0) -> str:
    if _depth > 25 or "$(" not in value:
        return value
    new = VAR_REF_RE.sub(lambda m: variables.get(m.group(1), ""), value)
    return new if new == value else _expand(new, variables, _depth + 1)


def _key(token: str, mk_dir: Path) -> str | None:
    norm = os.path.normpath(os.path.join(str(mk_dir), token))
    m = GEN_RE.search(norm)
    return f"{m.group(1)}/inputs/generated/{m.group(2)}" if m else None


INCLUDE_RE = re.compile(r"^\s*include\s+(.+)$")
# A sibling makefile name inside an include argument, tolerating a leading
# `$(dir $(lastword $(MAKEFILE_LIST)))` prefix glued to the basename.
INCLUDE_MK_RE = re.compile(r"([A-Za-z0-9_.-]+\.mk)\b")


def _collect_assignments(path: Path, variables: dict[str, str]) -> None:
    """Merge variable assignments from `path` (and its includes) into `variables`.

    GNU make's `include` is followed so a producer .mk that factors its shared
    path variables into a sibling file (e.g. render.mk including paths.mk) still
    has its $(ANALYSIS_*) target names expand. Only variable definitions are
    pulled in here; rules are parsed by the caller for the including file.
    """
    for raw in _logical_lines(path):
        if raw.startswith("\t"):
            continue
        line = raw.split("#", 1)[0]
        if not line.strip():
            continue
        inc = INCLUDE_RE.match(line)
        if inc:
            # The committed convention is
            # `include $(dir $(lastword $(MAKEFILE_LIST)))paths.mk`; resolve any
            # sibling .mk basename relative to the including file's directory.
            for name in INCLUDE_MK_RE.findall(inc.group(1)):
                sibling = path.parent / name
                if sibling.is_file():
                    _collect_assignments(sibling, variables)
            continue
        m = ASSIGN_RE.match(line)
        if m:
            name, op, val = m.group(1), m.group(2), m.group(3).strip()
            if op == "+=":
                variables[name] = f"{variables.get(name, '')} {val}".strip()
            elif op == "?=" and name in variables:
                pass
            else:
                variables[name] = val


def _parse(path: Path) -> tuple[set[str], dict[str, set[str]]]:
    """Return (targets, prereq_sources) of generated-artifact keys."""
    variables: dict[str, str] = {}
    rules: list[str] = []
    for raw in _logical_lines(path):
        if raw.startswith("\t"):  # recipe line
            continue
        line = raw.split("#", 1)[0]
        if not line.strip():
            continue
        inc = INCLUDE_RE.match(line)
        if inc:
            for name in INCLUDE_MK_RE.findall(inc.group(1)):
                sibling = path.parent / name
                if sibling.is_file():
                    _collect_assignments(sibling, variables)
            continue
        m = ASSIGN_RE.match(line)
        if m:
            name, op, val = m.group(1), m.group(2), m.group(3).strip()
            if op == "+=":
                variables[name] = f"{variables.get(name, '')} {val}".strip()
            elif op == "?=" and name in variables:
                pass
            else:
                variables[name] = val
            continue
        if ":" in line:
            rules.append(line)

    mk_dir = path.parent.relative_to(REPO_ROOT)
    targets: set[str] = set()
    prereqs: dict[str, set[str]] = {}
    rel = str(path.relative_to(REPO_ROOT))
    for line in rules:
        lhs, _, rhs = line.partition(":")
        lhs = lhs.rstrip().rstrip("&").rstrip()  # drop grouped-target marker
        for tok in _expand(lhs, variables).split():
            if (key := _key(tok, mk_dir)) is not None:
                targets.add(key)
        for tok in _expand(rhs, variables).split():
            if (key := _key(tok, mk_dir)) is not None:
                prereqs.setdefault(key, set()).add(rel)
    return targets, prereqs


def test_generated_artifacts_have_a_producer():
    all_targets: set[str] = set()
    all_prereqs: dict[str, set[str]] = {}
    for mk in _makefiles():
        targets, prereqs = _parse(mk)
        all_targets |= targets
        for key, srcs in prereqs.items():
            all_prereqs.setdefault(key, set()).update(srcs)

    orphans = sorted(k for k in all_prereqs if k not in all_targets)
    detail = "\n".join(
        f"  - {k}  (required by: {', '.join(sorted(all_prereqs[k]))})" for k in orphans
    )
    assert not orphans, (
        "Generated artifacts used as prerequisites but produced by no makefile "
        "rule (orphaned from the build DAG):\n"
        f"{detail}\n\n"
        "Add a producing rule (in experiments/render.mk for P3 render "
        "artifacts, experiments/derived/score.mk for P2 mart/cross-eval) or, "
        "for multi-output scripts, a grouped target `a b &:`."
    )
