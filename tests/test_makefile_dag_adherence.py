"""Makefile prerequisites must cover what the recipes' scripts actually use.

Standing guard for the defect class hit three times in the 2026-06-11 raid
(tickets 0505-0507, fixed piecemeal in PRs #949/#960, recurrence in 0530):
a Makefile rule whose prerequisite list lags behind the code it runs, so an
edit to a behavior-carrying script (or a new manuscript include) does not
re-trigger the build and the committed artifact silently goes stale.

Two checks, both purely static (no make execution, no imports executed):

1. Script-prerequisite import closure (score.mk + render.mk).
   The repo convention is that a rule lists a ``src/aedist/*.py`` file as a
   prerequisite when that script *carries behavior* for the artifact (label
   sets, scoring logic, layout). Shared library modules (config, evaluate,
   metrics, ...) are deliberately NOT per-rule prerequisites — a library
   change is handled by a deliberate ``make world`` re-run, not by per-rule
   edges. The invariant enforced here: when a rule lists script X, every
   module in X's *transitive first-party import closure* that is itself a
   script (i.e. executed via ``python -m aedist.<mod>`` by some rule in the
   registered makefiles) must also be listed. This is exactly the PR #949
   defect: exp1_cross_eval listed score_exp1.py but not score_mechanical.py,
   which score_exp1 imports and which carries the scoring behavior.

2. MANUSCRIPT_ASSETS parity (slides/Makefile vs slides/manuscript/main.tex).
   The asset list must equal exactly the set of report/inputs/generated/
   files main.tex pulls in via \\includegraphics / \\includepdf / \\input —
   no missing prerequisite (stale PDF, the PR #960 defect) and no ghost
   prerequisite (spurious rebuilds, the PR #969 review finding).
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src" / "aedist"

# The registered analysis makefiles (ticket 0535 scope: P2 score + P3 render).
ANALYSIS_MAKEFILES = [
    "experiments/derived/score.mk",
    "experiments/render.mk",
]

# Rules exempt from the closure check, by (makefile, raw target text).
# sota_cross_eval: ticket 0530 (sibling, in flight) adds score_mechanical.py
# to this rule's prerequisites; once it lands, lift this exemption and add
# the closure scripts (extract.py) the check will then demand.
CLOSURE_EXEMPT = {
    ("experiments/derived/score.mk", "$(ANALYSIS_EXP2_CROSS_EVAL_CSV)"),
}

ASSIGN_RE = re.compile(r"^\s*[A-Za-z_.][A-Za-z0-9_.]*\s*(:=|\?=|\+=|=)")
LISTED_SCRIPT_RE = re.compile(r"src/aedist/(\w+)\.py")
EXECUTED_MODULE_RE = re.compile(r"-m aedist\.(\w+)\b")
FIRST_PARTY_IMPORT_RE = re.compile(
    r"^(?:from (?:aedist\.|\.)(\w+)|import aedist\.(\w+))", re.M
)


def parse_rules(makefile_text: str) -> list[tuple[str, str, str]]:
    """Return (target, prerequisites, recipe) per rule, statically parsed.

    Backslash continuations are joined; comments stripped; variable
    assignments and non-rule lines skipped. Grouped targets (``a b &:``)
    yield one entry. No variable expansion is performed — the checks below
    match path *suffixes* (src/aedist/<mod>.py), which survive any
    $(VAR)-prefixed spelling used in the makefiles.
    """
    rules: list[list[str]] = []
    current: list[str] | None = None
    for line in makefile_text.replace("\\\n", " ").splitlines():
        if line.startswith("\t"):
            if current is not None:
                current[2] += line + "\n"
            continue
        code = line.split("#", 1)[0]
        if not code.strip():
            continue
        if ASSIGN_RE.match(code) or ":" not in code:
            current = None
            continue
        target, _, prereqs = code.partition(":")
        target = target.strip().removesuffix("&").strip()
        current = [target, prereqs.lstrip(":").strip(), ""]
        rules.append(current)
    return [tuple(r) for r in rules]


def listed_scripts(prereqs: str) -> set[str]:
    """Module names of src/aedist/*.py files in a prerequisite list."""
    return set(LISTED_SCRIPT_RE.findall(prereqs))


def executed_scripts(rules: list[tuple[str, str, str]]) -> set[str]:
    """Module names run via ``python -m aedist.<mod>`` in any recipe."""
    found: set[str] = set()
    for _, _, recipe in rules:
        found |= set(EXECUTED_MODULE_RE.findall(recipe))
    return found


def first_party_imports(module_source: str) -> set[str]:
    """Direct first-party imports (``from .x`` / ``from aedist.x`` forms)."""
    return {a or b for a, b in FIRST_PARTY_IMPORT_RE.findall(module_source)}


def import_closure(module: str, sources: dict[str, str]) -> set[str]:
    """Transitive first-party import closure of `module` (excluded itself).

    `sources` maps module name -> source text; names absent from it
    (subpackages, third-party) are ignored.
    """
    seen: set[str] = set()
    stack = [module]
    while stack:
        mod = stack.pop()
        if mod not in sources:
            continue
        for dep in first_party_imports(sources[mod]):
            if dep not in seen and dep in sources:
                seen.add(dep)
                stack.append(dep)
    return seen - {module}


def closure_violations(
    makefiles: dict[str, str],
    sources: dict[str, str],
    exempt: set[tuple[str, str]] = frozenset(),
) -> list[tuple[str, str, list[str]]]:
    """(makefile, target, missing-modules) for every rule breaking the rule.

    A violation: the rule lists script X as a prerequisite, but some script
    (executed module) in X's transitive first-party import closure is not
    listed alongside it.
    """
    parsed = {name: parse_rules(text) for name, text in makefiles.items()}
    scripts = set().union(*(executed_scripts(r) for r in parsed.values()))
    violations = []
    for name, rules in parsed.items():
        for target, prereqs, _ in rules:
            if (name, target) in exempt:
                continue
            listed = listed_scripts(prereqs)
            if not listed:
                continue
            needed: set[str] = set()
            for mod in listed:
                needed |= import_closure(mod, sources) & scripts
            missing = sorted(needed - listed)
            if missing:
                violations.append((name, target, missing))
    return violations


def _repo_sources() -> dict[str, str]:
    return {p.stem: p.read_text() for p in SRC_DIR.glob("*.py")}


def test_script_prereqs_cover_import_closure():
    makefiles = {rel: (REPO_ROOT / rel).read_text() for rel in ANALYSIS_MAKEFILES}
    violations = closure_violations(makefiles, _repo_sources(), CLOSURE_EXEMPT)
    msg = "\n".join(
        f"{mk}: rule '{tgt}' lists a src/aedist script whose import closure "
        f"includes script(s) not in its prerequisites: "
        + ", ".join(f"src/aedist/{m}.py" for m in missing)
        for mk, tgt, missing in violations
    )
    assert not violations, (
        "Makefile prerequisite gaps (add the missing script .py files to the "
        "rule's prerequisite list so edits re-trigger the build):\n" + msg
    )


# --- MANUSCRIPT_ASSETS parity ------------------------------------------------

GENERATED_BASENAME_RE = re.compile(r"generated/([\w.-]+\.[A-Za-z0-9]+)")
TEX_INCLUDE_RE = re.compile(
    r"^[^%\n]*\\(?:includegraphics|includepdf|input)\s*(?:\[[^]]*\])?"
    r"\{([^}]*/inputs/generated/[^}]+)\}",
    re.M,
)


def manuscript_assets(slides_makefile_text: str) -> set[str]:
    """Basenames listed in the MANUSCRIPT_ASSETS variable.

    The entries are spelled ``$(LOCAL_ROOT_REPORT_GEN)/<basename>``, so the
    comparison key is the basename (unique within the generated tree).
    """
    text = slides_makefile_text.replace("\\\n", " ")
    for line in text.splitlines():
        m = re.match(r"^MANUSCRIPT_ASSETS\s*:?=\s*(.*)$", line)
        if m:
            return {tok.rsplit("/", 1)[-1] for tok in m.group(1).split()}
    raise AssertionError("MANUSCRIPT_ASSETS not found in slides/Makefile")


def manuscript_includes(main_tex_text: str) -> set[str]:
    """Basenames of generated files main.tex includes (non-comment lines)."""
    return {
        GENERATED_BASENAME_RE.search(path).group(1)
        for path in TEX_INCLUDE_RE.findall(main_tex_text)
    }


def test_manuscript_assets_match_main_tex_includes():
    assets = manuscript_assets((REPO_ROOT / "slides" / "Makefile").read_text())
    includes = manuscript_includes(
        (REPO_ROOT / "slides" / "manuscript" / "main.tex").read_text()
    )
    missing = sorted(includes - assets)
    ghosts = sorted(assets - includes)
    assert not missing, (
        f"main.tex includes generated files absent from MANUSCRIPT_ASSETS "
        f"(stale-PDF hazard, PR #960 class): {missing}"
    )
    assert not ghosts, (
        f"MANUSCRIPT_ASSETS lists generated files main.tex does not include "
        f"(ghost prerequisites, spurious rebuilds): {ghosts}"
    )


# --- Fang: the checks must go red on seeded violations ------------------------


def test_closure_check_catches_seeded_violation():
    sources = {
        "score_a": "import csv\nfrom .score_b import scorer\n",
        "score_b": "from .lib import helper\n",
        "lib": "import re\n",
    }
    makefile = (
        "out.csv: in.csv $(ROOT)/src/aedist/score_a.py\n"
        "\tuv run python -m aedist.score_a --output $@\n"
        "other.csv: in2.csv\n"
        "\tuv run python -m aedist.score_b --output $@\n"
    )
    violations = closure_violations({"test.mk": makefile}, sources)
    assert violations == [("test.mk", "out.csv", ["score_b"])]
    # lib is in the closure but is not a script: never demanded.
    fixed = makefile.replace(
        "score_a.py", "score_a.py $(ROOT)/src/aedist/score_b.py"
    )
    assert closure_violations({"test.mk": fixed}, sources) == []


def test_closure_check_handles_continuations_and_grouped_targets():
    sources = {"plot_x": "from .plot_y import style\n", "plot_y": ""}
    makefile = (
        "a.pdf b.pdf &: data.csv \\\n"
        "\t\t$(ROOT)/src/aedist/plot_x.py\n"
        "\tuv run python -m aedist.plot_x\n"
        "c.pdf: $(ROOT)/src/aedist/plot_y.py\n"
        "\tuv run python -m aedist.plot_y\n"
    )
    violations = closure_violations({"test.mk": makefile}, sources)
    assert violations == [("test.mk", "a.pdf b.pdf", ["plot_y"])]


def test_manuscript_parity_catches_seeded_violation():
    mk = (
        "MANUSCRIPT_ASSETS := \\\n"
        "\t$(LOCAL_ROOT_REPORT_GEN)/fig_one.pdf \\\n"
        "\t$(LOCAL_ROOT_REPORT_GEN)/fig_ghost.pdf\n"
    )
    tex = (
        "\\includegraphics{../../report/inputs/generated/fig_one.pdf}\n"
        "\\input{../../report/inputs/generated/tab_two.tex}\n"
        "% \\includegraphics{../../report/inputs/generated/fig_commented.pdf}\n"
    )
    assets = manuscript_assets(mk)
    includes = manuscript_includes(tex)
    assert includes - assets == {"tab_two.tex"}
    assert assets - includes == {"fig_ghost.pdf"}
