"""Enforce the captioned-and-labelled figure convention in main.tex.

Ticket 0518 migrated the manuscript to symbolic cross-references; ticket 0524
converted it to hand-curated LaTeX. A figure must be a captioned, labelled
environment:

    \\begin{figure} … \\caption{…}\\label{fig:id} … \\end{figure}

— a *non-empty* caption plus a `fig:` label, so every figure is numbered and
cross-referenceable. The Annex E recognition matrix is the one exception: it
is an `\\includepdf` block carrying its own
`\\refstepcounter{figure}\\label{fig:recognition-matrix}`.
"""

import re

import pytest
from manuscript_source import body_raw

pytestmark = pytest.mark.adherence

FIGURE_ENV_RE = re.compile(r"\\begin\{figure\}.*?\\end\{figure\}", re.DOTALL)


def test_every_figure_is_captioned_and_labelled() -> None:
    """Each figure environment carries a non-empty \\caption and a fig: \\label."""
    violations = []
    blocks = FIGURE_ENV_RE.findall(body_raw())
    assert blocks, "no figure environments found in main.tex — parse regression"
    for block in blocks:
        head = block[:120].replace("\n", " ")
        cap = re.search(r"\\caption\{(.{0,40})", block, re.DOTALL)
        if not cap or not cap.group(1).strip().strip("}"):
            violations.append(f"empty/missing caption: {head}")
        if not re.search(r"\\label\{fig:[a-z0-9-]+\}", block):
            violations.append(f"missing \\label{{fig:…}}: {head}")
    assert not violations, (
        f"{len(violations)} figure(s) not captioned+labelled (tickets 0518/0524):\n"
        + "\n".join(f"  {v}" for v in violations)
    )


def test_no_literal_figure_number_in_caption() -> None:
    """No caption may open with a hand-typed "Figure N." / "Figure SN." prefix.

    LaTeX prepends the auto-generated "Figure N:" label itself; a literal
    "Figure 3." left at the start of the caption would double-number as
    "Figure 3: Figure 3. …" in the PDF.
    """
    violations = []
    for block in FIGURE_ENV_RE.findall(body_raw()):
        cap = re.search(r"\\caption\{\s*(.{0,40})", block, re.DOTALL)
        if cap and re.match(r"\*?Figure S?\d+[.:]", cap.group(1).lstrip()):
            violations.append(cap.group(1)[:60])
    assert not violations, (
        "Caption(s) begin with a literal 'Figure N.' that LaTeX would "
        "double-number:\n  " + "\n  ".join(violations)
    )
