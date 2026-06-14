"""Ticket 0591 — global sweep: internal codenames out, no code refs in §1–§9.

Reading-2 findings 8, 22, 23, 24 (tracker 0578). Negative/structural guards
only (CI test polarity rule, ticket 0557): each assertion forbids a *defect
class* — an internal codename or a code reference where it does not belong —
never pins a positive authorial phrasing.

Two scopes:

- **Codenames** (``Doc-07`` / ``Doc-NN``, ``ADR-N``) are internal repo
  identifiers and must not appear anywhere in the manuscript body — not in the
  numbered sections, not in the annexes, not in the verbatim prompt boxes
  (the shipped prompts never carried these labels; they are doc cross-refs the
  manuscript invented and the sweep removed). Class guard, whole body.

- **Code references** (file paths, module/function/script names, config keys)
  belong in annexes, figure/table captions, and the Data-&-Code backmatter
  only. The numbered sections §1–§9 + Conclusion — the region from
  ``\\section{Introduction}`` up to ``\\section*{Acknowledgements}``, with
  ``\\caption{…}`` blocks excised — must be free of them.

Exempt, and deliberately NOT matched by the code-ref patterns: reader-facing
data tokens that are not code — the OpenStreetMap ``power=plant`` tag, the
Wikipedia revision id, the controlled status vocabulary. These are data the
reader queries or reads, not repo artifacts.
"""

import re

import pytest
from manuscript_source import body_raw, strip_comments

pytestmark = pytest.mark.adherence

# Internal codename classes. ``Doc-07`` and any ``ADR-N`` are repo-doc
# identifiers; a reader of the paper has no referent for them.
_CODENAME_RE = re.compile(r"\bDoc-?\d|\bADR[ -]?\d")

# Code-reference signatures: \fpath, source trees, source-file extensions,
# config-set / sweep-dir identifiers. None of these should surface in §1–§9.
_CODEREF_PATTERNS = [
    r"\\fpath\{",
    r"\bsrc/aedist",
    r"experiments/",
    r"data/reference/",
    r"report/inputs/",
    r"\.py\b",
    r"\.toml\b",
    r"\.csv\b",
    r"\.json\b",
    r"\.yaml\b",
    r"\.md\b",
    r"modelset_",
    r"\bexp[12]_",
]


# Build directives that embed a generated artifact by path — these are
# typesetting mechanics, not prose, so the artifact path inside them is not a
# prose code reference.
_INCLUDE_RE = re.compile(r"\\(?:includegraphics(?:\[[^\]]*\])?|input|bibliography)\{[^}]*\}")


def _strip_captions(text: str) -> str:
    """Remove every ``\\caption{…}`` block (brace-balanced) and every figure/
    table include directive (``\\includegraphics``/``\\input``/``\\bibliography``).

    Captions may carry code references (ticket 0591 scope), and include
    directives are build mechanics rather than prose; excising both leaves only
    the running prose of the section."""
    text = _INCLUDE_RE.sub("", text)
    out: list[str] = []
    i = 0
    needle = r"\caption{"
    while True:
        m = re.search(re.escape(needle), text[i:])
        if not m:
            out.append(text[i:])
            break
        start = i + m.start()
        out.append(text[i:start])
        j = start + len(needle)
        depth = 1
        while j < len(text) and depth:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            j += 1
        i = j
    return "".join(out)


def _numbered_sections() -> str:
    """The §1–§9 + Conclusion prose: Introduction .. Acknowledgements, comments
    and caption blocks removed."""
    body = strip_comments(body_raw())
    start = body.index(r"\section{Introduction}")
    end = body.index(r"\section*{Acknowledgements}")
    return _strip_captions(body[start:end])


def test_no_internal_codenames_anywhere_in_body():
    """``Doc-07`` / ``ADR-N`` codenames appear nowhere in the manuscript body
    (findings 8, 24). The shipped prompts never carried them, so the verbatim
    prompt boxes are not an exception."""
    body = strip_comments(body_raw())
    hits = _CODENAME_RE.findall(body)
    assert not hits, f"internal codename(s) leaked into the manuscript: {hits}"


@pytest.mark.parametrize("pattern", _CODEREF_PATTERNS)
def test_no_code_refs_in_numbered_sections(pattern):
    """§1–§9 + Conclusion (caption blocks excised) carry no code reference —
    file paths, source modules, config keys (finding 22). Annexes, captions,
    and the Data-&-Code backmatter are out of scope and may carry them."""
    main = _numbered_sections()
    hits = re.findall(pattern, main)
    assert not hits, (
        f"code reference {pattern!r} found in §1–§9 prose: {hits}. "
        "Move the detail to an annex or a caption, or reword it out."
    )
