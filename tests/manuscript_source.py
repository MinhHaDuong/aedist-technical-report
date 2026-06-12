"""Shared accessors for the manuscript LaTeX source (ticket 0524).

The manuscript is `slides/manuscript/main.tex` — hand-curated LaTeX,
tectonic-built (the pandoc/pandoc-crossref `main.md` was retired by ticket
0524). Adherence tests assert on prose substrings, so this module provides a
*normalized* view of the source where LaTeX-isms that would break a plain
substring match are folded back to the characters the prose means:

- generated value macros (`\\NumRefPlants`, `\\ExpOneFOneMean`, …) are expanded
  to their values, read from the macros files the preamble `\\input`s (ticket
  0531) — so prose assertions keep matching the literal numbers after the
  macros-everywhere conversion;
- hard-wrapped lines are joined (whitespace runs collapse to single spaces);
- TeX ligatures `---`/`--` become the em/en dashes they typeset to;
- non-breaking ties `~` become plain spaces;
- escaped specials `\\$ \\% \\& \\_ \\#` become the bare character.

Structural macro calls (`\\emph{…}`, `\\textbf{…}`, `\\ref{…}`) are left
intact: tests anchor on them explicitly. Comment lines are dropped from the
body so that source-maintenance notes (ticket numbers, etc.) are not scanned
as prose.
"""

import functools
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MANUSCRIPT = REPO_ROOT / "slides" / "manuscript" / "main.tex"

_COMMENT_RE = re.compile(r"(?<!\\)%.*$", re.MULTILINE)
# Any macros file the preamble \inputs (no hardcoded path: the preamble is the
# source of truth for which file(s) carry the generated values).
_MACRO_INPUT_RE = re.compile(r"\\input\{([^}]*macros[^}]*\.tex)\}")
_NEWCOMMAND_RE = re.compile(r"^\\newcommand\{\\([A-Za-z]+)\}\{(.*)\}\s*$")


@functools.lru_cache(maxsize=1)
def _macro_table() -> dict[str, str]:
    """name -> value for every \\newcommand in the preamble's macros inputs."""
    if not MANUSCRIPT.exists():
        return {}
    preamble = MANUSCRIPT.read_text(encoding="utf-8").split("\\begin{document}", 1)[0]
    table: dict[str, str] = {}
    for m in _MACRO_INPUT_RE.finditer(strip_comments(preamble)):
        macros_path = (MANUSCRIPT.parent / m.group(1)).resolve()
        if not macros_path.exists():
            continue
        for line in macros_path.read_text(encoding="utf-8").splitlines():
            mm = _NEWCOMMAND_RE.match(line)
            if mm:
                table[mm.group(1)] = mm.group(2)
    return table


def _expand_macros(text: str) -> str:
    """Substitute generated value macros with their values.

    Longest name first, so ``\\ExpOneFOneMean`` is never half-eaten by a
    shorter prefix. Both the bare ``\\Name`` call and the argument-stopped
    ``\\Name{}`` form are recognised; a trailing letter means a different
    macro and is left alone. Replacement goes through a lambda so backslashes
    in values (e.g. ``75.0\\%``) are taken literally.
    """
    table = _macro_table()
    for name in sorted(table, key=len, reverse=True):
        value = table[name]
        text = re.sub(rf"\\{name}(\{{\}})?(?![A-Za-z])", lambda _m, v=value: v, text)
    return text


def raw() -> str:
    """The full main.tex source, exactly as committed."""
    if not MANUSCRIPT.exists():
        pytest.skip("slides/manuscript/main.tex not found")
    return MANUSCRIPT.read_text(encoding="utf-8")


def strip_comments(text: str) -> str:
    """Drop unescaped-% comments (escaped \\% percents survive)."""
    return _COMMENT_RE.sub("", text)


def body_raw() -> str:
    """The document body (between \\begin{document} and \\end{document})."""
    text = raw()
    return text.split("\\begin{document}", 1)[1].rsplit("\\end{document}", 1)[0]


def normalized(text: str) -> str:
    """Fold LaTeX surface syntax back to prose for substring assertions."""
    # Expand generated value macros FIRST, so a value like `75.0\%` then folds
    # through the escape handling below exactly like hand-typed prose.
    text = _expand_macros(text)
    text = strip_comments(text)
    text = text.replace("---", "—").replace("--", "–")
    for esc, ch in (("\\$", "$"), ("\\%", "%"), ("\\&", "&"), ("\\_", "_"), ("\\#", "#")):
        text = text.replace(esc, ch)
    # Non-breaking tie -> space (never used escaped in the manuscript prose).
    text = text.replace("~", " ")
    return " ".join(text.split())


def body() -> str:
    """Normalized document body — the standard surface for prose assertions."""
    return normalized(body_raw())


# A sectioning heading: \section or \section*, title with at most one level
# of brace nesting. Used both to anchor a label to its heading and to find
# the terminator of a slice (any sectioning command, or \appendix).
_SECTION_TITLE = r"\\section\*?\{(?:[^{}]|\{[^{}]*\})*\}"
_SECTIONING_RE = re.compile(r"\\section\*?\{|\\appendix(?![A-Za-z])")
_SECTION_LABELS_RE = re.compile(_SECTION_TITLE + r"\s*\\label\{([^}]*)\}")


def section(label: str) -> str:
    """Normalized text of the section labelled `label`, heading included.

    Label-keyed extraction (ticket 0561; stability contract in ticket 0560):
    the section is located by the ``\\label{...}`` attached to its
    ``\\section``/``\\section*`` heading and sliced to the NEXT sectioning
    command of ANY kind (``\\section``, ``\\section*``, ``\\appendix``) or the
    end of the body. Retitles, reorders, annex-letter changes, and unlabelled
    neighbours therefore cannot break the extraction — only removing the
    label can, and that is the contract violation this error reports.

    Only ``\\section``/``\\section*`` headings are searched: a label that
    moves to a ``\\subsection`` heading (level demotion) is NOT found. A
    restructure that demotes a labelled section (e.g. 0562 making
    ``sec:fusion`` a subsection) must extend this helper or re-key the
    consuming tests in the same PR.
    """
    text = body()
    heading_re = re.compile(_SECTION_TITLE + r"\s*" + re.escape(f"\\label{{{label}}}"))
    m = heading_re.search(text)
    assert m is not None, (
        f"no \\section/\\section* heading labelled {label!r} in the manuscript "
        f"body (label-stability contract, ticket 0560) — section labels "
        f"present: {sorted(set(_SECTION_LABELS_RE.findall(text)))}"
    )
    nxt = _SECTIONING_RE.search(text, m.end())
    return text[m.start() : nxt.start() if nxt else len(text)]


def figure_caption(label: str) -> str:
    """Normalized \\caption text of the figure environment labelled `label`."""
    text = body_raw()
    anchor = f"\\label{{{label}}}"
    pos = text.find(anchor)
    assert pos != -1, f"no figure labelled {label} in main.tex"
    start = text.rfind("\\caption{", 0, pos)
    assert start != -1, f"no \\caption before \\label{{{label}}}"
    # Balance braces from the caption's opening brace.
    i = start + len("\\caption{")
    depth = 1
    while depth:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    return normalized(text[start + len("\\caption{") : i - 1])


def longtable_rows(header_cell: str) -> list[list[str]]:
    """Data rows of the longtable whose header row contains `header_cell`.

    Returns each `&`-separated row (after \\endlastfoot, before
    \\end{longtable}) as a list of stripped cell strings.
    """
    text = body_raw()
    for m in re.finditer(r"\\begin\{longtable\}.*?\\end\{longtable\}", text, re.DOTALL):
        block = m.group(0)
        if header_cell not in block:
            continue
        data = block.split("\\endlastfoot", 1)[1] if "\\endlastfoot" in block else block
        rows = []
        for line in data.splitlines():
            line = line.strip()
            if line.endswith("\\\\"):
                cells = [normalized(c) for c in line[:-2].split("&")]
                rows.append(cells)
        return rows
    raise AssertionError(f"no longtable with header cell {header_cell!r} in main.tex")


def title() -> str:
    """Normalized \\title{...} content from the preamble (\\thanks included)."""
    text = raw()
    start = text.index("\\title{")
    i = start + len("\\title{")
    depth = 1
    while depth:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    return normalized(text[start + len("\\title{") : i - 1])
