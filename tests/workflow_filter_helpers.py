"""Shared helpers for emulating dorny/paths-filter gating in GHA workflows.

Used by test_ci_workflow.py and test_docs_build_workflow.py (tickets 0525,
0527): both workflows carry an inverted `non-chore` filter under
predicate-quantifier: every, and steps gate on `!= 'false'`.
"""

import re

import yaml


def filter_patterns(wf: dict, changes_job: str = "changes") -> tuple[str, list[str]]:
    """Return (filter_name, patterns) from the paths-filter step."""
    steps = wf["jobs"][changes_job].get("steps") or []
    filter_step = next(
        (s for s in steps if "dorny/paths-filter" in (s.get("uses") or "")),
        None,
    )
    assert filter_step is not None, "dorny/paths-filter step not found"
    raw_filters = (filter_step.get("with") or {}).get("filters", "")
    parsed = yaml.safe_load(raw_filters)
    assert len(parsed) == 1, f"expected exactly one filter, got {list(parsed)}"
    name, patterns = next(iter(parsed.items()))
    return name, patterns


def glob_match(path: str, pattern: str) -> bool:
    """Minimal picomatch subset covering the workflows' patterns.

    Supports brace expansion `{a,b}`, the catch-all `**`, `dir/**`
    prefixes, and literal filenames — nothing more.
    """
    if pattern.startswith("{") and pattern.endswith("}"):
        return any(glob_match(path, p) for p in pattern[1:-1].split(","))
    if pattern == "**":
        return True
    if pattern.endswith("/**"):
        return path.startswith(pattern[:-2])
    return path == pattern


def paths_filter_output(changed_files: list[str], patterns: list[str]) -> bool:
    """Emulate dorny/paths-filter with predicate-quantifier: every.

    The filter output is true iff ANY changed file matches ALL patterns;
    a leading `!` negates the individual pattern (per upstream README).
    """

    def file_matches(path: str) -> bool:
        for pat in patterns:
            if pat.startswith("!"):
                if glob_match(path, pat[1:]):
                    return False
            elif not glob_match(path, pat):
                return False
        return True

    return any(file_matches(f) for f in changed_files)


def gate_allows(cond: str, output: str, name: str) -> bool:
    """Evaluate the filter-output comparison clause inside one `if:` condition."""
    expr = cond.replace("${{", "").replace("}}", "").strip()
    match = re.search(
        rf"needs\.changes\.outputs\.{re.escape(name)}\s*(==|!=)\s*'([^']*)'", expr
    )
    assert match, f"no {name} comparison found in gate {cond!r}"
    op, rhs = match.groups()
    equal = output == rhs
    return equal if op == "==" else not equal


def job_runs(wf: dict, job_name: str, filter_output: bool | None) -> bool:
    """Evaluate every step gate in a job as GitHub Actions would.

    `filter_output is None` models an empty/errored filter output (the
    expression then compares against the empty string). All steps must
    agree — a step whose gate diverges from the others is an error.
    """
    steps = wf["jobs"][job_name].get("steps") or []
    output = "" if filter_output is None else str(filter_output).lower()
    name, _ = filter_patterns(wf)
    verdicts = {gate_allows(str(s.get("if", "")), output, name) for s in steps}
    assert len(verdicts) == 1, f"{job_name} steps disagree on the {name} gate"
    return verdicts.pop()
