"""Mandate symbolic cross-references in slides/manuscript/main.md (ticket 0518).

Since the manuscript builds with pandoc-crossref + `--number-sections`, every
section/figure/table number is auto-generated. Two invariants follow:

1. *No hand-typed reference literal in prose.* A bare ``§3`` / ``Figure 4`` /
   ``Figure S1`` / ``Annex C`` / ``Table 1`` in the body would silently rot
   under restructuring — exactly the failure mode 0518 removes. References must
   be symbolic: ``[@sec:…]`` / ``[@fig:…]`` / ``[@tbl:…]`` (or the
   prefix-suppressed ``[-@…]`` form).

2. *Every symbolic reference resolves.* Each ``@sec:`` / ``@fig:`` / ``@tbl:``
   reference must point at a label defined somewhere in the document — either a
   pandoc attribute ``{#sec:…}`` / ``{#fig:…}`` / ``{#tbl:…}`` or a raw-LaTeX
   ``\\label{…}`` (the recognition-matrix includepdf case). No orphan refs.

Code spans and fenced code blocks are excluded from the prose scan: a literal
like ``status_distinct ≤ 1`` or a filename is not a cross-reference. Equally,
``Figure``/``§`` tokens *inside* a figure-caption alt text are real references
and ARE scanned — they must be symbolic too.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

MANUSCRIPT = (
    Path(__file__).resolve().parent.parent / "slides" / "manuscript" / "main.md"
)

# Hand-typed reference literals that must NOT appear in prose.
HANDTYPED_RES = [
    (re.compile(r"§\s*\d"), "§N section reference"),
    (re.compile(r"\bFigure\s+S?\d"), "Figure N / Figure SN reference"),
    (re.compile(r"\bAnnex\s+[A-G]\b"), "Annex X reference"),
    (re.compile(r"\bTable\s+\d"), "Table N reference"),
]

# Definition forms: pandoc attribute {#id} or raw-LaTeX \label{id}.
DEF_RE = re.compile(r"\{#((?:sec|fig|tbl):[a-z0-9-]+)\}|\\label\{((?:sec|fig|tbl):[a-z0-9-]+)\}")
# Reference form: [@id] or [-@id], possibly several in one bracket.
REF_RE = re.compile(r"[-]?@((?:sec|fig|tbl):[a-z0-9-]+)")
CODE_SPAN_RE = re.compile(r"```.*?```|`[^`]*`", re.DOTALL)


def _read() -> str:
    if not MANUSCRIPT.exists():
        pytest.skip("main.md not found")
    return MANUSCRIPT.read_text(encoding="utf-8")


def _strip_code(text: str) -> str:
    """Replace fenced/inline code with blanks so it is not scanned for refs."""
    return CODE_SPAN_RE.sub(lambda m: " " * len(m.group(0)), text)


def test_no_hand_typed_references_in_prose() -> None:
    """No literal §N / Figure N / Annex X / Table N survives outside code."""
    prose = _strip_code(_read())
    violations = []
    for i, line in enumerate(prose.splitlines(), 1):
        for rx, label in HANDTYPED_RES:
            if rx.search(line):
                violations.append(f"main.md:{i}: {label}: {line.strip()[:90]}")
    assert not violations, (
        f"{len(violations)} hand-typed cross-reference literal(s) — use "
        "[@sec:…]/[@fig:…]/[@tbl:…] (ticket 0518):\n"
        + "\n".join(f"  {v}" for v in violations)
    )


def test_every_reference_resolves_to_a_defined_label() -> None:
    """Each @sec/@fig/@tbl reference points at a defined label (no orphans)."""
    text = _read()
    defined = {a or b for a, b in DEF_RE.findall(text)}
    referenced = set(REF_RE.findall(text))
    orphans = sorted(referenced - defined)
    assert not orphans, (
        f"{len(orphans)} symbolic reference(s) with no matching label "
        f"definition: {orphans}\n  defined labels: {sorted(defined)}"
    )


def test_at_least_one_symbolic_reference_of_each_kind() -> None:
    """Guard against a regex that passes vacuously: the migration is real.

    The manuscript must actually use section, figure, and table references in
    symbolic form — otherwise test_no_hand_typed_references_in_prose could pass
    on a document that simply deleted every cross-reference.
    """
    referenced = set(REF_RE.findall(_read()))
    for prefix in ("sec:", "fig:", "tbl:"):
        assert any(r.startswith(prefix) for r in referenced), (
            f"no symbolic {prefix} reference found — migration incomplete"
        )
