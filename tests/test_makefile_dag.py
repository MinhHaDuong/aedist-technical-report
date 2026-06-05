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
# Any-extension variant for the tracked-artifact guard below (ticket 0417):
# committed CSV/txt handoff artifacts count there, not just figures/includes.
GEN_ANY_RE = re.compile(r"report/inputs/generated/[^/\s:*?)]+\.[A-Za-z0-9]+")
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


def _parse_to_vars_rules(path: Path) -> tuple[dict[str, str], list[str]]:
    """Scan `path` into (resolved variables, rule lines).

    Shared preamble for _parse and _all_targets_any_ext: skips recipe and
    comment lines, pulls sibling-include variable assignments in, applies
    `+=`/`?=`/`=` semantics, and collects every non-recipe line containing
    a `:` as a rule line for the caller to split.
    """
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
    return variables, rules


def _parse(path: Path) -> tuple[set[str], dict[str, set[str]]]:
    """Return (targets, prereq_sources) of generated-artifact keys."""
    variables, rules = _parse_to_vars_rules(path)
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


def _all_targets_any_ext(path: Path) -> set[str]:
    """All rule targets of `path` that resolve under report/inputs/generated/.

    Same scan as _parse but keyed on GEN_ANY_RE (any extension) and targets
    only — prerequisites are irrelevant to the tracked-artifact guard.
    """
    variables, rules = _parse_to_vars_rules(path)
    mk_dir = path.parent.relative_to(REPO_ROOT)
    targets: set[str] = set()
    for line in rules:
        lhs, _, _rhs = line.partition(":")
        lhs = lhs.rstrip().rstrip("&").rstrip()  # drop grouped-target marker
        for tok in _expand(lhs, variables).split():
            norm = os.path.normpath(os.path.join(str(mk_dir), tok))
            if (m := GEN_ANY_RE.search(norm)) is not None:
                targets.add(m.group(0))
    return targets


# Deliberately frozen artifacts: committed under report/inputs/generated/
# without a producer rule, each with a documented reason (ticket 0417 action
# 1(b) escape hatch). Keep one comment per entry explaining why regeneration
# is impossible or deliberately suspended.
FROZEN_ALLOWLIST: dict[str, str] = {
    "report/inputs/generated/tab_decomposition_fix.tex": (
        "Reconciliation CSVs were gitignored (c14136ff) and never archived. "
        "The committed table is correct (ticket 0068) but unreproducible from "
        "the current DAG. Restore requires wiring a reconcile-from-archive P2 "
        "step (ticket 0421 follow-up)."
    ),
}


def test_tracked_generated_artifacts_have_a_producer():
    """Every tracked file under report/inputs/generated/ has a producer rule.

    Complements the prereq-side test below: that one only catches artifacts
    some makefile *consumes*; a committed handoff artifact consumed only by
    LaTeX (or by nothing) can still be orphaned from the DAG and silently go
    stale or unreproducible (ticket 0417 found four such files).
    """
    all_targets: set[str] = set()
    for mk in _makefiles():
        all_targets |= _all_targets_any_ext(mk)

    tracked = subprocess.run(
        ["git", "ls-files", "report/inputs/generated/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()

    orphans = sorted(f for f in tracked if f not in all_targets and f not in FROZEN_ALLOWLIST)
    detail = "\n".join(f"  - {f}" for f in orphans)
    assert not orphans, (
        "Tracked files under report/inputs/generated/ with no producer rule "
        "in any makefile (unreproducible from the DAG):\n"
        f"{detail}\n\n"
        "Either add a producing rule (experiments/render.mk for P3 render "
        "artifacts), retire the file (git rm + manifest row update in "
        "docs/pipeline-phases.md), or — for a deliberate freeze — add it to "
        "FROZEN_ALLOWLIST in this test with a reason."
    )


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


# ---------------------------------------------------------------------------
# Guard: empty $(wildcard experiments/outputs/...) with non-empty archive
# sibling (ticket 0423 — class guard for the edda724b archive move)
# ---------------------------------------------------------------------------

_PHASE_MKS: list[Path] = [
    REPO_ROOT / "experiments" / "render.mk",
    REPO_ROOT / "experiments" / "derived" / "score.mk",
    REPO_ROOT / "experiments" / "acquire.mk",
]


def _extract_wildcard_patterns(text: str) -> list[str]:
    """Return every PATTERN from $(wildcard PATTERN) in text, nesting-aware."""
    out: list[str] = []
    i = 0
    while i < len(text):
        idx = text.find("$(wildcard ", i)
        if idx == -1:
            break
        start = idx + len("$(wildcard ")
        depth, j = 1, start
        while j < len(text) and depth:
            depth += (text[j] == "(") - (text[j] == ")")
            j += 1
        if depth == 0:
            out.append(text[start : j - 1].strip())
        i = max(j, i + 1)
    return out


def _phase_variables(mk_path: Path) -> dict[str, str]:
    """Variables dict for a phase makefile, with experiments/paths.mk pre-loaded."""
    variables: dict[str, str] = {}
    shared = REPO_ROOT / "experiments" / "paths.mk"
    if shared.is_file():
        _collect_assignments(shared, variables)
    _collect_assignments(mk_path, variables)
    return variables


# ---------------------------------------------------------------------------
# Guard: no P3-to-P3 side-output edges in render.mk (ticket 0436)
# ---------------------------------------------------------------------------
# Figures and tables must each build from their OWN view of the data mart —
# consistency by common cause (the shared mart), never by one P3 script
# consuming another P3 script's side-output (a figure script feeding a figure
# script, or a plot_ script emitting a CSV/macro that a tabulate_ rule reads).
# The sanctioned exception is the dedicated projection module
# build_exp2_mart_views, whose *_view.csv outputs are the canonical mart views
# both figures and tables read.

_RENDER_MK = REPO_ROOT / "experiments" / "render.mk"
# A recipe that derives an artifact from the mart: any plot_*/tabulate_* module
# invoked as `python -m aedist.<module>`. build_exp2_mart_views is the
# sanctioned projection module (its outputs ARE the shared views) and is
# whitelisted as a producer below.
_P3_MODULE_RE = re.compile(r"\baedist\.(plot_[A-Za-z0-9_]+|tabulate_[A-Za-z0-9_]+)\b")
_VIEW_MODULE_RE = re.compile(r"\baedist\.build_exp2_mart_views\b")
# Any committed/handoff artifact under report/inputs/generated/ (any extension);
# derived/ intermediates are out of scope — the render.mk header sanctions them
# as "P3-internal derived analysis files consumed only by later P3 rules".
_GEN_PREREQ_RE = re.compile(r"report/inputs/generated/[^/\s:*?)]+\.[A-Za-z0-9]+")


def _parse_render_rules_with_recipes(
    path: Path,
) -> tuple[list[dict], dict[str, str]]:
    """Parse `path` into per-rule (targets, prereqs, recipe-module-tags).

    Unlike _parse, this keeps recipe lines so each rule's targets and
    prerequisites can be tagged with the aedist modules its recipe invokes.
    Returns (rules, variables) where each rule dict has keys:
        ``targets`` (set of generated-artifact keys),
        ``prereqs`` (set of generated-artifact keys),
        ``p3`` (True if the recipe invokes a plot_/tabulate_ module),
        ``view`` (True if the recipe invokes build_exp2_mart_views).
    """
    variables, _ = _parse_to_vars_rules(path)
    # Join backslash continuations into logical lines, but remember whether each
    # logical line began as a recipe line (leading TAB) so recipes stay
    # distinguishable from rule headers (a wrapped prereq list continues onto
    # TAB-prefixed lines that are NOT recipes — make joins them into the header).
    logical = _logical_lines(path)
    rules: list[dict] = []
    current: dict | None = None
    for raw in logical:
        is_recipe = raw.startswith("\t")
        if is_recipe:
            if current is not None:
                if _P3_MODULE_RE.search(raw):
                    current["p3"] = True
                if _VIEW_MODULE_RE.search(raw):
                    current["view"] = True
            continue
        # Non-recipe line: close any open rule, then look for a new target line.
        if current is not None:
            rules.append(current)
            current = None
        line = raw.split("#", 1)[0]
        if not line.strip() or line.lstrip().startswith(("include", ".PHONY")):
            continue
        if ":" not in line:
            continue
        lhs, _, rhs = line.partition(":")
        lhs = lhs.rstrip().rstrip("&").rstrip()
        targets = set()
        for tok in _expand(lhs, variables).split():
            m = _GEN_PREREQ_RE.search(os.path.normpath(tok))
            if m:
                targets.add(m.group(0))
        prereqs = set()
        for tok in _expand(rhs, variables).split():
            m = _GEN_PREREQ_RE.search(os.path.normpath(tok))
            if m:
                prereqs.add(m.group(0))
        current = {"targets": targets, "prereqs": prereqs, "p3": False, "view": False}
    if current is not None:
        rules.append(current)
    return rules, variables


@pytest.mark.adherence
def test_no_p3_to_p3_side_output_edges() -> None:
    """No render.mk rule consumes another P3 script's generated side-output.

    Collects every report/inputs/generated/ artifact produced by a rule whose
    recipe invokes a plot_/tabulate_ module (a P3 figure/table script), then
    asserts no *other* rule lists any of them as a prerequisite — unless the
    producer is the sanctioned mart-view builder (build_exp2_mart_views), whose
    *_view.csv outputs are the canonical shared views.

    Mechanics mirror tests/test_makefile_dag.py. Class guard for ticket 0436:
    figures and tables each read their own view of the mart (common cause),
    never one feeding another via an intermediate file.
    """
    rules, _ = _parse_render_rules_with_recipes(_RENDER_MK)

    # Outputs of P3 figure/table scripts (excluding the sanctioned view builder).
    p3_outputs: set[str] = set()
    # Whitelisted shared-view outputs of build_exp2_mart_views.
    view_outputs: set[str] = set()
    for rule in rules:
        if rule["view"]:
            view_outputs |= rule["targets"]
        elif rule["p3"]:
            p3_outputs |= rule["targets"]

    forbidden = p3_outputs - view_outputs

    # Consumer side: only real P3 script rules (recipe invokes a plot_/tabulate_
    # module) count. The .PHONY grouping targets (report-tables, chart-figures,
    # all, …) list every artifact as a prerequisite but run no recipe — they are
    # aggregation aliases, not data-flow edges, and must not be flagged.
    bad: list[tuple[str, str]] = []
    for rule in rules:
        if not rule["p3"]:
            continue
        for prereq in rule["prereqs"]:
            if prereq in forbidden:
                target = next(iter(sorted(rule["targets"])), "<phony>")
                bad.append((target, prereq))

    detail = "\n".join(f"  - {t}  consumes  {p}" for t, p in sorted(bad))
    assert not bad, (
        "render.mk rules consume a P3 figure/table script's generated "
        "side-output (P3-to-P3 edge — ticket 0436):\n"
        f"{detail}\n\n"
        "Figures and tables must each build their own view of the mart "
        "(common cause), never one feeding another via an intermediate file. "
        "Move the shared derivation into a library helper both consumers import "
        "(precedent: src/aedist/exp1_recognition.py), or produce the artifact "
        "from the sanctioned build_exp2_mart_views projection module."
    )


@pytest.mark.adherence
def test_no_empty_outputs_wildcard_with_nonempty_archive_sibling() -> None:
    """$(wildcard experiments/outputs/...) empty + non-empty archive sibling → fail.

    Guards the class of bug fixed by ticket 0421: after the edda724b archive
    move, any $(wildcard experiments/outputs/<dir>/...) that silently expands
    to zero files while the matching archive/outputs/ sibling is non-empty
    indicates a stale wildcard that should be repointed to archive.
    """
    import glob as _glob

    live_pfx = str(REPO_ROOT / "experiments" / "outputs") + os.sep
    arch_pfx = str(REPO_ROOT / "experiments" / "archive" / "outputs") + os.sep
    failures: list[str] = []

    for mk_path in _PHASE_MKS:
        if not mk_path.is_file():
            continue
        variables = _phase_variables(mk_path)
        mk_rel = mk_path.relative_to(REPO_ROOT)
        for raw in _logical_lines(mk_path):
            if raw.startswith("\t"):
                continue
            line = raw.split("#", 1)[0]
            if not line.strip():
                continue
            for pat in _extract_wildcard_patterns(line):
                expanded = _expand(pat, variables)
                if "$(" in expanded:
                    continue  # unexpanded make function — skip
                norm = os.path.normpath(
                    os.path.join(str(REPO_ROOT), expanded.strip())
                )
                if not norm.startswith(live_pfx):
                    continue
                if _glob.glob(norm):
                    continue  # wildcard resolves to files — OK
                arch = arch_pfx + norm[len(live_pfx):]
                arch_hits = _glob.glob(arch)
                if arch_hits:
                    failures.append(
                        f"  {mk_rel}: $(wildcard {expanded}) → 0 files; "
                        f"archive sibling has {len(arch_hits)} file(s) — "
                        f"repoint to archive?"
                    )

    assert not failures, (
        "$(wildcard experiments/outputs/...) expands empty but the archive "
        "sibling is non-empty (edda724b class guard — ticket 0423):\n"
        + "\n".join(failures)
    )
