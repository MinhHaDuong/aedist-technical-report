"""`experiments/acquire.mk` is the P1 (acquire) phase — every target is .PHONY.

Tracker 0406, step S4 (ticket 0411) renamed the P1 experiments makefile to
`experiments/acquire.mk` and made the P1 invariant mechanical: acquire.mk holds
only manually-invoked, money-gated sweep verbs (census, regimes, decomposed,
verification, sourced, frontier — each fans out the manager/worker pipeline and
costs API dollars) plus corpus utilities (pdf2md, build-corpus, preflight,
help). None of these produce a file a downstream phase may depend on, so EVERY
rule target must be declared `.PHONY`. A file target here would let score.mk
(P2) or render.mk (P3) silently trigger a money-costing re-acquisition through
an ordinary timestamp-driven rebuild — exactly the seam this guard closes.

The two invariants enforced:

  1. Every rule target in acquire.mk is named in a `.PHONY:` line.
  2. No rule target is a filesystem path (no `/`) and none escapes the
     experiments/ tree (no `..`) — acquire.mk writes raw replies under
     experiments/outputs/** through the worker pipeline, never as a make file
     target.

Mirrors the structure of ``tests/test_render_build_clean_room.py`` (S2's P3
guard) and ``tests/test_score_build_no_acquire.py`` (S3's P2 guard), but this
one is a pure SOURCE scan: P1 has no file targets to dry-run, so the invariant
is "the target set equals the .PHONY set."

Parsing note: acquire.mk carries make assignments (``UV_RUN :=``, ``MODEL ?=``,
``_NEEDS_ENV :=``, ``ZOTERO_API_KEY :=``) whose left-hand side would be misread
as a rule target by a naive ``":" in line`` split. We strip assignments
(mirroring test_makefile_dag.py's ASSIGN_RE), conditional/include/export
directives, and ``.``-prefixed special targets (``.PHONY``) before collecting
rule targets. ``experiments/common.mk`` (the sole include) holds zero rules, so
scanning acquire.mk alone is sufficient.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
ACQUIRE_MK = REPO_ROOT / "experiments" / "acquire.mk"

# A variable assignment, not a rule (matches test_makefile_dag.py's ASSIGN_RE).
ASSIGN_RE = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_]*\s*(:=|\?=|\+=|=)")
# Make directives whose line may contain a ':' but is not a rule.
DIRECTIVE_RE = re.compile(
    r"^\s*(ifeq|ifneq|ifdef|ifndef|else|endif|include|-include|export|unexport)\b"
)


def _phony_names_and_targets(text: str) -> tuple[set[str], list[str]]:
    """Return (declared .PHONY names, list of rule-target tokens)."""
    phony: set[str] = set()
    targets: list[str] = []
    for raw in text.replace("\\\n", " ").splitlines():
        if raw.startswith("\t"):
            continue  # recipe line
        line = raw.split("#", 1)[0]
        if not line.strip():
            continue
        if DIRECTIVE_RE.match(line):
            continue
        if ASSIGN_RE.match(line):
            continue
        if ":" not in line:
            continue
        lhs = line.split(":", 1)[0].rstrip().rstrip("&").rstrip()
        toks = lhs.split()
        if not toks:
            continue
        if toks[0] == ".PHONY":
            # `.PHONY: a b c` — collect the declared names (rhs of the colon).
            phony.update(line.split(":", 1)[1].split())
            continue
        for tok in toks:
            if tok.startswith("."):
                continue  # other special target (.SHELLFLAGS handled by ASSIGN)
            targets.append(tok)
    return phony, targets


def test_acquire_mk_exists():
    assert ACQUIRE_MK.is_file(), (
        "experiments/acquire.mk must exist (P1 acquire phase; renamed from the "
        "P1 experiments makefile by ticket 0411, tracker 0406 step S4)."
    )


def test_every_target_is_phony():
    """Every rule target in acquire.mk is declared .PHONY (the P1 invariant)."""
    phony, targets = _phony_names_and_targets(ACQUIRE_MK.read_text())
    missing = sorted({t for t in targets if t not in phony})
    assert not missing, (
        "acquire.mk declares rule target(s) not in any `.PHONY:` line: "
        f"{missing}. P1 acquire is all-.PHONY by invariant — every sweep verb "
        "and corpus utility is manually invoked and money-gated; nothing "
        "downstream may depend on a P1 target as a file. Either declare the "
        "target .PHONY (if it is a P1 verb) or relocate it to the right phase "
        ".mk (score.mk / render.mk)."
    )


def test_no_filesystem_path_targets():
    """No rule target is a filesystem path, and none escapes experiments/."""
    _, targets = _phony_names_and_targets(ACQUIRE_MK.read_text())
    offending = sorted({t for t in targets if "/" in t or ".." in t})
    assert not offending, (
        "acquire.mk declares a rule whose TARGET is a filesystem path: "
        f"{offending}. P1 has no file targets — raw replies are written under "
        "experiments/outputs/** by the worker pipeline, never as a make file "
        "target. A path target (especially one escaping experiments/ via '..') "
        "would couple a money-gated re-acquisition to a timestamp rebuild."
    )


def _parse_needs_env(text: str) -> set[str]:
    """Return the set of names declared in the _NEEDS_ENV assignment."""
    joined = text.replace("\\\n", " ")
    m = re.search(r"_NEEDS_ENV\s*:=\s*([^\n#]+)", joined)
    if not m:
        return set()
    return set(m.group(1).split())


def test_env_file_verbs_covered_by_needs_env():
    """Every sweep group X (with X-generate and X-run) must have X and X-run in _NEEDS_ENV.

    All sweep groups invoke the manager/worker pipeline via $(MANAGER) / $(OR_DRAIN),
    which expand through $(UV_RUN) and carry --env-file ../.env.  The _NEEDS_ENV
    sentinel must cover the top-level verb X and its X-run sub-target so that
    invoking either without a populated .env fails fast rather than burning API
    quota mid-run.
    """
    text = ACQUIRE_MK.read_text()
    phony, _ = _phony_names_and_targets(text)

    sweep_groups = sorted(
        name[: -len("-generate")]
        for name in phony
        if name.endswith("-generate")
        and name[: -len("-generate")] + "-run" in phony
    )

    needs_env = _parse_needs_env(text)

    missing = []
    for group in sweep_groups:
        if group not in needs_env:
            missing.append(group)
        if f"{group}-run" not in needs_env:
            missing.append(f"{group}-run")

    assert not missing, (
        f"Sweep verbs with --env-file recipes not covered by _NEEDS_ENV: "
        f"{sorted(missing)}. "
        "Add them to the _NEEDS_ENV list so `make <verb>` fails fast when "
        "../.env is absent instead of launching a money-costing API sweep."
    )
