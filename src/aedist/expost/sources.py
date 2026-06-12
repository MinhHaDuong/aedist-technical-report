"""Source handling for ex post extraction of EXP3 outputs (ticket 0292).

Four concerns live here:

1. Rendering Mistral mixed content blocks (``text`` + ``tool_reference``)
   into markdown with inline source links (moved from
   ``experiments/sota/exp2_naive_arm.py``).
2. Appending a deduplicated ``## Sources`` section (same origin).
3. Resolving bare reference numbers in Source 1 / Source 2 table cells
   (e.g. ``6,76``) against the LLM-generated numbered bibliography at the
   bottom of the report, replacing them with actual hyperlinks and keeping
   an audit trail for unresolved or ambiguous references.
4. Stripping non-table preambles from derived report outputs.
"""

import re

# A numbered bibliography entry: "1. **Title**" / "12) Title".
_NUMBERED_ENTRY_RE = re.compile(r"^\s*(\d+)[.)]\s+(.*\S)\s*$")
# First http(s) URL inside a markdown link target or bare.
_URL_RE = re.compile(r"https?://[^\s)\]>]+")
# A Source cell holding only bare reference numbers: "6", "6,76", "[16, 90]".
_BARE_REFS_RE = re.compile(r"^\s*\[?\s*(\d+(?:\s*,\s*\d+)*)\s*\]?\s*$")
# Table separator row: |---|:---:|...
_SEPARATOR_ROW_RE = re.compile(r"^\s*\|?\s*:?-{3,}.*$")
_SOURCE_HEADER_RE = re.compile(r"^source\s*[12]$", re.IGNORECASE)


def render_mistral_content_with_sources(
    content: list[dict],
) -> tuple[str, list[tuple[str, str]]]:
    """Render Mistral mixed content blocks into markdown with inline source links.

    Mistral probe outputs interleave `text` and `tool_reference` blocks. Keep the
    original order so references remain in table cells (e.g., Source 1/Source 2).
    """
    parts: list[str] = []
    sources: list[tuple[str, str]] = []

    for block in content:
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        if btype == "text":
            parts.append(block.get("text", ""))
            continue
        if btype == "tool_reference":
            title = str(block.get("title", "")).strip()
            url = str(block.get("url", "")).strip()
            if not url:
                continue
            label = title if title else url
            parts.append(f"[{label}]({url})")
            sources.append((label, url))

    return "".join(parts), sources


def append_sources_section(narrative: str, sources: list[tuple[str, str]]) -> str:
    """Append a compact deduplicated ``## Sources`` section to narrative markdown.

    The scoring pipeline consumes the generated `.md` file downstream.
    Keep web/tool references in-band so source-presence checks see them.
    """
    if not sources:
        return narrative

    dedup: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for title, url in sources:
        key = (title.strip(), url.strip())
        if not key[1] or key in seen:
            continue
        seen.add(key)
        dedup.append(key)

    if not dedup:
        return narrative

    lines = ["", "", "## Sources", ""]
    for title, url in dedup:
        label = title if title else url
        lines.append(f"- [{label}]({url})")
    return narrative.rstrip() + "\n" + "\n".join(lines) + "\n"


def parse_numbered_bibliography(markdown: str) -> dict[int, str]:
    """Map bibliography entry numbers to their URLs.

    Scans the document for numbered list entries (``1. **Title** ...``) and
    associates each number with the first http(s) URL found in the entry's
    block (the entry line plus its indented continuation lines). Numbered
    rows inside pipe tables are ignored. Entries without a URL are omitted.
    """
    mapping: dict[int, str] = {}
    current_num: int | None = None
    for line in markdown.splitlines():
        if line.lstrip().startswith("|"):
            current_num = None
            continue
        m = _NUMBERED_ENTRY_RE.match(line)
        if m:
            current_num = int(m.group(1))
            if current_num in mapping:
                current_num = None  # keep the first occurrence only
                continue
            url = _URL_RE.search(m.group(2))
            if url:
                mapping[current_num] = url.group(0)
                current_num = None
            continue
        if current_num is not None:
            if not line.strip():
                current_num = None
                continue
            url = _URL_RE.search(line)
            if url:
                mapping[current_num] = url.group(0)
                current_num = None
    return mapping


def _resolve_cell(cell: str, bib: dict[int, str], unresolved: list[int]) -> str:
    m = _BARE_REFS_RE.match(cell)
    if not m:
        return cell
    refs = [int(tok) for tok in m.group(1).split(",")]
    parts: list[str] = []
    for ref in refs:
        url = bib.get(ref)
        if url is None:
            unresolved.append(ref)
            parts.append(str(ref))
        else:
            parts.append(f"[{ref}]({url})")
    return " " + ", ".join(parts) + " "


def resolve_source_cells(markdown: str) -> tuple[str, dict]:
    """Replace bare reference numbers in Source columns with hyperlinks.

    Numbers are resolved against the numbered bibliography found in the same
    document (see :func:`parse_numbered_bibliography`). Returns the rewritten
    markdown and an audit dict::

        {"n_refs": int, "n_resolved": int, "unresolved": [int, ...],
         "audit_status": "complete" | "in_progress" | "no_bibliography"}

    ``audit_status`` is ``"in_progress"`` when any reference could not be
    resolved — the extraction is then only partially certain and downstream
    consumers must treat the Source columns as an audit in progress.
    """
    bib = parse_numbered_bibliography(markdown)
    audit: dict = {"n_refs": 0, "n_resolved": 0, "unresolved": [], "audit_status": "complete"}
    if not bib:
        audit["audit_status"] = "no_bibliography"
        return markdown, audit

    lines = markdown.splitlines()
    source_cols: list[int] = []
    unresolved: list[int] = []
    n_refs = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("|"):
            source_cols = []
            continue
        if _SEPARATOR_ROW_RE.match(stripped):
            continue
        cells = line.split("|")
        headers = [c.strip() for c in cells]
        header_cols = [j for j, h in enumerate(headers) if _SOURCE_HEADER_RE.match(h)]
        if header_cols:
            source_cols = header_cols
            continue
        if not source_cols:
            continue
        changed = False
        for j in source_cols:
            if j >= len(cells):
                continue
            m = _BARE_REFS_RE.match(cells[j])
            if not m:
                continue
            n_refs += len(m.group(1).split(","))
            cells[j] = _resolve_cell(cells[j], bib, unresolved)
            changed = True
        if changed:
            lines[i] = "|".join(cells)

    audit["n_refs"] = n_refs
    audit["unresolved"] = sorted(set(unresolved))
    audit["n_resolved"] = n_refs - len(unresolved)
    if unresolved:
        audit["audit_status"] = "in_progress"
    trailing = "\n" if markdown.endswith("\n") else ""
    return "\n".join(lines) + trailing, audit


def strip_preamble(markdown: str) -> str:
    """Drop leading non-table prose from a derived report output.

    Removes every line before the first markdown heading (``#``) or pipe-table
    row, whichever comes first. Conservative by design: headings, tables, and
    everything after them are preserved verbatim. Returns the input unchanged
    when no heading or table exists.

    Salvage case: some frozen raw records glue the table header onto the last
    preamble sentence with no newline ("...searches.| Name | ..."). When a
    preamble line contains a ``|`` and the NEXT line is a table separator row
    (``|---|...``), the fused header is kept from its first ``|`` onward.
    """
    lines = markdown.splitlines(keepends=True)
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith(("#", "|")):
            return "".join(lines[i:])
        if "|" in stripped and i + 1 < len(lines):
            next_stripped = lines[i + 1].strip()
            if next_stripped.startswith("|") and _SEPARATOR_ROW_RE.match(next_stripped):
                return stripped[stripped.index("|") :] + "".join(lines[i + 1 :])
    return markdown
