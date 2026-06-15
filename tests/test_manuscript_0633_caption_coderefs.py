"""Ticket 0633 — global caption sweep: text AND captions standalone at the
maths/ideas level; code references (file paths, module/function/script names,
config keys, filenames) live ONLY in the annexes.

Canonical re-articulation of finding 22 (author, 2026-06-15): the main text and
the figure/table captions must be self-contained at the level of ideas, with
``\\ref`` to the annexes for implementation detail. This SUPERSEDES ticket
0591's caption exemption (``test_manuscript_codenames_coderefs.py`` excised
``\\caption{…}`` blocks before scanning; this sweep brings captions into scope).

Negative/structural guards only (CI test polarity rule, ticket 0557): every
assertion forbids a *defect class* — a code reference where it does not belong —
and never pins a positive authorial phrasing.

Boundary: the document body up to ``\\appendix`` (§1–§9, Conclusion, the
backmatter blocks, and every figure/table caption among them). Code references
are allowed AFTER ``\\appendix`` (the annexes) and are not scanned here.

Exempt, and deliberately NOT matched by the code-ref patterns: reader-facing
data tokens that are not code — the OpenStreetMap ``power=plant`` tag, the
Wikipedia revision id, the controlled status vocabulary. These are data the
reader queries or reads, not repo artifacts; the patterns below target paths,
source-file extensions, and config/sweep identifiers, none of which those
tokens carry.
"""

import re

import pytest
from manuscript_source import body_raw, strip_comments

pytestmark = pytest.mark.adherence

# Code-reference signatures: \fpath, source trees, source-file extensions,
# config-set / sweep-dir identifiers. None of these belongs in the body or in a
# body caption — they are repo artifacts the annexes own.
_CODEREF_PATTERNS = [
    r"\\fpath\{",
    r"\bsrc/aedist",
    r"experiments/",
    r"data/reference/",
    r"data/rag_corpus/",
    r"report/inputs/",
    r"docs/",
    r"\.py\b",
    r"\.toml\b",
    r"\.csv\b",
    r"\.json\b",
    r"\.yaml\b",
    r"\.md\b",
    r"modelset_",
    r"\bexp[12]_",
]

# Build directives that embed a generated artifact by path — typesetting
# mechanics, not prose, so the artifact path inside them is not a code reference
# (\includegraphics resolves the figure PDF; \input/\bibliography load files).
_INCLUDE_RE = re.compile(
    r"\\(?:includegraphics(?:\[[^\]]*\])?|input|bibliography)\{[^}]*\}"
)


def _body_before_appendix() -> str:
    """Document body from \\begin{document} up to \\appendix, comments dropped
    and build-mechanics include directives removed.

    This is the region that must be standalone at the maths/ideas level:
    §1–§9 + Conclusion, the backmatter, and EVERY figure/table caption among
    them. The annexes (after \\appendix) are out of scope."""
    body = strip_comments(body_raw())
    cut = re.search(r"\\appendix(?![A-Za-z])", body)
    if cut:
        body = body[: cut.start()]
    return _INCLUDE_RE.sub("", body)


def _captions(text: str) -> list[str]:
    """Every brace-balanced ``\\caption{…}`` block found in `text`."""
    out: list[str] = []
    needle = r"\caption{"
    i = 0
    while True:
        m = re.search(re.escape(needle), text[i:])
        if not m:
            return out
        start = i + m.start() + len(needle)
        depth = 1
        j = start
        while j < len(text) and depth:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            j += 1
        out.append(text[start : j - 1])
        i = j


@pytest.mark.parametrize("pattern", _CODEREF_PATTERNS)
def test_no_code_refs_in_body_captions(pattern):
    """No figure/table caption before \\appendix carries a code reference —
    file path, source module, config key, or filename. Load-bearing detail is
    relocated to the relevant annex and reached by \\ref (ticket 0633,
    superseding 0591's caption exemption)."""
    captions = "\n".join(_captions(_body_before_appendix()))
    hits = re.findall(pattern, captions)
    assert not hits, (
        f"code reference {pattern!r} found in a body caption: {hits}. "
        "Move the detail to an annex and \\ref it; keep captions standalone."
    )


@pytest.mark.parametrize("pattern", _CODEREF_PATTERNS)
def test_no_code_refs_in_body_before_appendix(pattern):
    """The whole body up to \\appendix — §1–§9, Conclusion, backmatter, AND
    the captions among them — carries no code reference. Annexes (after
    \\appendix) are out of scope and may carry them (ticket 0633)."""
    hits = re.findall(pattern, _body_before_appendix())
    assert not hits, (
        f"code reference {pattern!r} found in the body before \\appendix: "
        f"{hits}. Move the detail to an annex or reword it out."
    )
