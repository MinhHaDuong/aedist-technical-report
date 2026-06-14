"""Ticket 0587 — §7 (Extensions) subsection headings use the house style.

Reading-2 finding 21 (tracker 0578). Every section in the manuscript follows
the writing guide (no numbered subsections); §7 was the lone exception. Its
four subsections are now the starred house form (`\\subsection*{...}` +
`\\addcontentsline`), with their stable labels kept attached
(label-stability-contract).

Negative / structural guards only (CI polarity rule, 0557):
- no numbered ``\\subsection{`` survives inside §7 (sec:extensions);
- each of the four §7 subsection labels stays attached to a heading.
"""

import re

import pytest
from manuscript_source import raw

pytestmark = pytest.mark.adherence

# The four §7 subsection labels — the label-stability contract for this section.
EXTENSIONS_SUBSECTION_LABELS = (
    "sec:ext-difficulty",
    "sec:ext-screen",
    "sec:fusion",
    "sec:ext-system",
)


def _extensions_source() -> str:
    """Raw LaTeX of §7, from ``\\section{Extensions}`` to the next ``\\section``.

    Structural scan needs the raw source (heading syntax), not normalized prose.
    """
    text = raw()
    start = text.index("\\section{Extensions}")
    nxt = re.search(r"\\section\*?\{|\\appendix(?![A-Za-z])", text[start + 1 :])
    end = start + 1 + nxt.start() if nxt else len(text)
    return text[start:end]


def test_no_numbered_subsection_in_extensions() -> None:
    """Finding 21: §7 carries no numbered ``\\subsection{`` heading.

    A numbered subsection in §7 would render ``§7.N`` while every other
    section uses the unnumbered house form — the defect this ticket fixes.
    Starred ``\\subsection*{`` is the allowed form and does not match.
    """
    src = _extensions_source()
    numbered = re.findall(r"\\subsection\{[^}]*\}", src)
    assert not numbered, (
        "§7 (sec:extensions) must use the unnumbered house subsection form "
        "(\\subsection*{...} + \\addcontentsline); numbered \\subsection{...} "
        f"headings found: {numbered} (ticket 0587, finding 21)"
    )


def test_extensions_subsection_labels_attached() -> None:
    """The four §7 subsection labels stay attached to starred headings.

    Label-stability contract (editorial-brief label-stability-contract): the
    headings may be retitled or unnumbered, but the labels must survive so
    every ``§\\ref{sec:ext-*}`` / ``§\\ref{sec:fusion}`` call site resolves.
    """
    src = _extensions_source()
    for label in EXTENSIONS_SUBSECTION_LABELS:
        assert re.search(
            r"\\subsection\*?\{(?:[^{}]|\{[^{}]*\})*\}\s*\\label\{"
            + re.escape(label)
            + r"\}",
            src,
        ), (
            f"label {label!r} must stay attached to its §7 subsection heading "
            "(label-stability-contract, ticket 0587)"
        )
