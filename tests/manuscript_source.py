"""Shared accessors for the manuscript LaTeX source (ticket 0524).

The manuscript is `slides/manuscript/main.tex` — hand-curated LaTeX,
tectonic-built (the pandoc/pandoc-crossref `main.md` was retired by ticket
0524). Adherence tests assert on prose substrings, so this module provides a
*normalized* view of the source where LaTeX-isms that would break a plain
substring match are folded back to the characters the prose means:

- hard-wrapped lines are joined (whitespace runs collapse to single spaces);
- TeX ligatures `---`/`--` become the em/en dashes they typeset to;
- non-breaking ties `~` become plain spaces;
- escaped specials `\\$ \\% \\& \\_ \\#` become the bare character.

Macro calls (`\\emph{…}`, `\\textbf{…}`, `\\ref{…}`) are left intact: tests
anchor on them explicitly. Comment lines are dropped from the body so that
source-maintenance notes (ticket numbers, etc.) are not scanned as prose.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MANUSCRIPT = REPO_ROOT / "slides" / "manuscript" / "main.tex"

_COMMENT_RE = re.compile(r"(?<!\\)%.*$", re.MULTILINE)


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
