"""Enforce the symbolic-cross-reference figure convention in main.md.

Ticket 0518 migrated the manuscript to pandoc-crossref. Under that filter a
figure must be a captioned, labelled image:

    ![Full caption text …](path){#fig:id}

— a *non-empty* alt text (the caption) plus a `{#fig:…}` label. This is the
exact inverse of the former option-1 convention (ticket 0448), which required
an empty alt text and a trailing backslash to suppress numbering. Numbering is
now delegated to LaTeX via the `\\label`/`\\ref` pairs pandoc-crossref emits, so
the old "Figure N: Figure N" double-numbering defect cannot occur (no literal
"Figure N." sits in the caption any more — see test_manuscript_crossref.py).

The Annex E recognition matrix is the one exception: it is a raw-LaTeX
`\\includepdf` block, not a pandoc image, and carries its own
`\\refstepcounter{figure}\\label{fig:recognition-matrix}`.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

MANUSCRIPT = (
    Path(__file__).resolve().parent.parent / "slides" / "manuscript" / "main.md"
)


def test_every_image_is_captioned_and_labelled() -> None:
    """Each `![…](path)` include carries a non-empty caption and a `{#fig:…}` label.

    A bare `![](path)` (empty alt) would render an uncaptioned, unnumbered
    figure under pandoc-crossref; an image without a `{#fig:}` label cannot be
    cross-referenced. Both are defects post-0518.
    """
    text = MANUSCRIPT.read_text(encoding="utf-8")
    image_re = re.compile(r"!\[(?P<alt>.*?)\]\((?P<path>[^)]+)\)(?P<attr>\{[^}]*\})?")
    violations = []
    for i, line in enumerate(text.splitlines(), 1):
        for m in image_re.finditer(line):
            alt = m.group("alt").strip()
            attr = m.group("attr") or ""
            if not alt:
                violations.append(f"{MANUSCRIPT.name}:{i}: empty alt (no caption): {line.strip()[:80]}")
            elif "#fig:" not in attr:
                violations.append(f"{MANUSCRIPT.name}:{i}: missing {{#fig:…}} label: {line.strip()[:80]}")
    assert not violations, (
        f"{len(violations)} figure include(s) not captioned+labelled — every "
        "image must be `![caption](path){#fig:id}` (ticket 0518):\n"
        + "\n".join(f"  {v}" for v in violations)
    )


def test_no_literal_figure_number_in_caption() -> None:
    """No caption may open with a hand-typed "Figure N." / "Figure SN." prefix.

    pandoc-crossref prepends the auto-generated "Figure N:" label itself; a
    literal "Figure 3." left in the alt text would double-number as
    "Figure 3: Figure 3. …" in the PDF.
    """
    text = MANUSCRIPT.read_text(encoding="utf-8")
    image_re = re.compile(r"!\[(?P<alt>.*?)\]\([^)]+\)", re.DOTALL)
    violations = []
    for m in image_re.finditer(text):
        alt = m.group("alt").lstrip()
        if re.match(r"\*?Figure S?\d+[.:]", alt):
            violations.append(alt[:80])
    assert not violations, (
        "Caption(s) begin with a literal 'Figure N.' that pandoc-crossref would "
        "double-number:\n  " + "\n  ".join(violations)
    )
