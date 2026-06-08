"""Build a curated RAG corpus from Zotero PDFs.

Fully local pipeline (no cloud APIs required for conversion or scoring):

  1. Search  — query Zotero library for candidate documents
  2. Select  — document-level reranking (fuzzy match against reference set)
  3. Fetch   — download PDFs from Zotero API
  4. Convert — PDF → Markdown (GROBID, local vision, or cloud)
  5. Score   — local LLM (Ollama) selects relevant sections

Usage (GROBID — default, best for academic papers):
    python -m aedist.build_corpus --query "thermal power vietnam" \\
        --reference report/inputs/README.md \\
        --output experiments/data/rag_corpus

Usage (local vision — best for scanned/government docs):
    python -m aedist.build_corpus --query "thermal power vietnam" \\
        --converter vision --local-vision-model gemma4:31b \\
        --output experiments/data/rag_corpus

Usage (cloud vision fallback):
    python -m aedist.build_corpus --query "thermal power vietnam" \\
        --converter cloud \\
        --output experiments/data/rag_corpus

Requires: Ollama on localhost:11434 (scoring + vision converter).
    ollama serve
Optional: GROBID on localhost:8070 (grobid converter only).
    podman start grobid

Minh Ha-Duong, CNRS, 2025–
License CC-BY-SA
"""

import argparse
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from .pdf2md_utils import CONVERTERS, get_converter
from .pdf2md_utils import metadata_comment as _meta_comment

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Zotero API helpers
# ---------------------------------------------------------------------------

ZOTERO_BASE = "https://api.zotero.org"


def _zotero_headers(api_key: str) -> dict[str, str]:
    return {"Zotero-API-Key": api_key}


def _zotero_get(url: str, api_key: str):
    req = urllib.request.Request(url, headers=_zotero_headers(api_key))
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def zotero_search(user_id: str, api_key: str, query: str,
                  limit: int = 50) -> list[dict]:
    """Search Zotero library, return items with PDF attachments."""
    encoded_q = urllib.request.quote(query)
    url = (f"{ZOTERO_BASE}/users/{user_id}/items"
           f"?format=json&limit={limit}&q={encoded_q}")
    items = _zotero_get(url, api_key)

    results = []
    for item in items:
        data = item["data"]
        key = data["key"]
        item_type = data.get("itemType", "")
        title = data.get("title", "")

        if item_type == "note":
            continue

        # Check if this item IS a PDF attachment
        if item_type == "attachment" and data.get("contentType") == "application/pdf":
            results.append({
                "key": key,
                "title": title,
                "filename": data.get("filename", ""),
                "attachment_key": key,
            })
            continue

        # Check children for PDF attachments
        children_url = (f"{ZOTERO_BASE}/users/{user_id}/items/{key}"
                        f"/children?format=json")
        try:
            children = _zotero_get(children_url, api_key)
        except (urllib.error.URLError, json.JSONDecodeError):
            continue
        for child in children:
            cd = child["data"]
            if cd.get("contentType") == "application/pdf":
                results.append({
                    "key": key,
                    "title": title,
                    "filename": cd.get("filename", ""),
                    "attachment_key": cd["key"],
                })
                break  # one PDF per parent item

    return results


def zotero_download_pdf(user_id: str, api_key: str,
                        attachment_key: str, dest: Path) -> Path:
    """Download a PDF attachment from Zotero to dest directory."""
    dest.mkdir(parents=True, exist_ok=True)
    url = (f"{ZOTERO_BASE}/users/{user_id}/items/{attachment_key}/file")
    req = urllib.request.Request(url, headers=_zotero_headers(api_key))
    filepath = dest / f"{attachment_key}.pdf"
    if filepath.exists():
        log.info("  Already downloaded: %s", filepath.name)
        return filepath
    with urllib.request.urlopen(req, timeout=120) as resp:
        filepath.write_bytes(resp.read())
    log.info("  Downloaded: %s", filepath.name)
    return filepath


# ---------------------------------------------------------------------------
# Document-level selection — rerank by matching reference set
# ---------------------------------------------------------------------------

def parse_reference_titles(readme_path: Path) -> list[str]:
    """Extract document titles from a README.md bibliography.

    Parses LaTeX-style \\emph{...} titles and backtick-quoted titles
    from the report/inputs/README.md format.
    """
    text = readme_path.read_text(encoding="utf-8")
    # Match \emph{...} titles (government documents)
    titles = [m.group(1).strip() for m in re.finditer(r"\\emph\{([^}]+)\}", text)]

    # Match backtick-quoted titles (articles)
    titles.extend(m.group(1).strip() for m in re.finditer(r"`([^']+)'", text))

    return titles


def select_by_reference(items: list[dict],
                        reference_titles: list[str],
                        threshold: int = 60) -> list[dict]:
    """Rerank and filter items by fuzzy matching against reference titles.

    Uses rapidfuzz for efficient fuzzy matching. Items that match a reference
    title above the threshold are kept, sorted by match score.
    """
    from rapidfuzz import fuzz

    scored = []
    for item in items:
        candidate = item.get("title", "") or item.get("filename", "")
        best_score = 0
        best_ref = ""
        for ref_title in reference_titles:
            score = fuzz.token_sort_ratio(candidate, ref_title)
            if score > best_score:
                best_score = score
                best_ref = ref_title
        scored.append((item, best_score, best_ref))

    # Sort by score descending
    scored.sort(key=lambda x: x[1], reverse=True)

    selected = []
    for item, score, ref in scored:
        if score >= threshold:
            selected.append(item)
            log.info("  [%3d] %s", score, item.get("title", "")[:70])
            log.info("        ↳ %s", ref[:70])
        else:
            log.debug("  [%3d] SKIP: %s", score, item.get("title", "")[:70])

    return selected


# ---------------------------------------------------------------------------
# Section extraction — split markdown into scorable chunks
# ---------------------------------------------------------------------------

def split_into_sections(markdown: str) -> list[dict]:
    """Split markdown into sections by page markers and headings.

    Returns list of {"text": str, "page": int|None, "heading": str}.
    """
    pages = re.split(r"(?=<!-- PDF page \d+ -->)", markdown)
    sections = []

    for page_block in pages:
        if not page_block.strip():
            continue

        page_match = re.match(r"<!-- PDF page (\d+) -->", page_block)
        page_num = int(page_match.group(1)) if page_match else None

        # Further split by headings within the page
        heading_parts = re.split(r"(?=^#{1,4}\s)", page_block, flags=re.MULTILINE)

        for part in heading_parts:
            text = part.strip()
            if not text or text == f"<!-- PDF page {page_num} -->":
                continue

            heading_match = re.match(r"^(#{1,4})\s+(.+?)$", text, re.MULTILINE)
            heading = heading_match.group(2).strip() if heading_match else ""

            sections.append({
                "text": text,
                "page": page_num,
                "heading": heading,
            })

    return sections


# ---------------------------------------------------------------------------
# LLM-based relevance scoring
# ---------------------------------------------------------------------------

SCORE_SYSTEM = """You are a document relevance scorer for a research project on
Vietnamese thermal power plants.

You will be given a section of a document converted from PDF to Markdown.
Score how relevant this section is for building a knowledge base about
thermal power plants in Vietnam.

HIGH relevance (score 3): Contains a TABLE or LIST of power plants, their
capacities, locations, fuel types, construction stages, or commissioning dates.
This includes annex tables from government planning documents (PDP7, PDP7A, PDP8),
implementation reports, or energy databases.

MEDIUM relevance (score 2): Contains narrative text ABOUT specific thermal power
plants, projects, or policies directly affecting thermal power development.

LOW relevance (score 1): General energy policy, renewable energy, or tangentially
related content.

NOT relevant (score 0): Procedural text (signatures, distribution lists),
unrelated content, or empty/corrupted sections.

Respond with ONLY a JSON object: {"score": N, "reason": "brief explanation"}"""

SCORE_USER = """Score this document section for relevance to Vietnamese thermal
power plant inventories:

---
{section_text}
---"""

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_SCORER_MODEL = "qwen3.5:9b"


def _ollama_generate(model: str, messages: list[dict],
                     ollama_url: str = DEFAULT_OLLAMA_URL) -> dict:
    """Call Ollama chat API, return {"content": str, "usage": dict}."""
    url = f"{ollama_url}/api/chat"
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
    }).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.monotonic()
    # 10 min: local models on large sections can be slow (qwen3.5:9b on A4000)
    with urllib.request.urlopen(req, timeout=600) as resp:
        result = json.loads(resp.read())
    wall = round(time.monotonic() - t0, 3)
    msg = result.get("message", {})
    return {
        "content": msg.get("content", ""),
        "usage": {
            "prompt_tokens": result.get("prompt_eval_count", 0),
            "completion_tokens": result.get("eval_count", 0),
        },
        "wall_seconds": wall,
    }


def score_section(section: dict, model: str,
                  ollama_url: str = DEFAULT_OLLAMA_URL) -> dict:
    """Score a section for relevance using local Ollama LLM."""
    text = section["text"]
    if len(text) > 8000:
        text = text[:8000] + "\n[... truncated ...]"

    messages = [
        {"role": "system", "content": SCORE_SYSTEM},
        {"role": "user", "content": SCORE_USER.format(section_text=text)},
    ]

    result = _ollama_generate(model, messages, ollama_url)

    # Parse score from response — extract JSON from possible think tags
    content = result["content"]
    # Strip <think>...</think> blocks (e.g. qwen3.5 reasoning)
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

    try:
        parsed = json.loads(content)
        score = int(parsed["score"])
        reason = parsed.get("reason", "")
    except (json.JSONDecodeError, KeyError, ValueError):
        # Try to extract JSON from mixed text
        m = re.search(r'\{[^}]*"score"\s*:\s*(\d)', content)
        if m:
            score = int(m.group(1))
            reason = content[:100]
        else:
            score = 0
            reason = f"Parse error: {content[:100]}"

    return {
        **section,
        "score": score,
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Build RAG corpus: Zotero → PDF → Markdown → select tables"
    )

    # Source selection
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--query", help="Zotero search query")
    source.add_argument("--items", help="Comma-separated Zotero attachment keys")

    # Zotero config
    parser.add_argument("--zotero-user", default="95318",
                        help="Zotero user ID (default: 95318)")

    # Document-level selection
    parser.add_argument("--reference", type=Path, default=None,
                        help="Reference bibliography (README.md) for document reranking")
    parser.add_argument("--match-threshold", type=int, default=60,
                        help="Fuzzy match threshold 0-100 (default: 60)")

    # Output
    parser.add_argument("--output", required=True, type=Path,
                        help="Output directory for corpus .md files")
    parser.add_argument("--work-dir", type=Path, default=None,
                        help="Working directory for PDFs and intermediate files")

    # Conversion backend
    parser.add_argument("--converter", default="grobid",
                        choices=sorted(CONVERTERS),
                        help="PDF converter backend (default: grobid)")
    parser.add_argument("--grobid-url", default="http://localhost:8070",
                        help="GROBID service URL (default: http://localhost:8070)")
    parser.add_argument("--vision-model", default="gpt-4o",
                        help="Vision model for cloud conversion (default: gpt-4o)")
    parser.add_argument("--local-vision-model", default="gemma4:31b",
                        help="Ollama vision model for local conversion (default: gemma4:31b)")
    parser.add_argument("--dpi", type=int, default=200,
                        help="DPI for cloud PDF rasterisation (default: 200)")

    # Section scoring
    parser.add_argument("--scorer-model", default=DEFAULT_SCORER_MODEL,
                        help=f"Ollama model for scoring (default: {DEFAULT_SCORER_MODEL})")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL,
                        help=f"Ollama service URL (default: {DEFAULT_OLLAMA_URL})")
    parser.add_argument("--min-score", type=int, default=2, choices=[1, 2, 3],
                        help="Minimum score to include (default: 2)")

    # Modes
    parser.add_argument("--skip-download", action="store_true",
                        help="Skip download, use existing PDFs in work-dir")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without calling APIs")

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    zotero_key = os.environ.get("ZOTERO_API_KEY")
    if not zotero_key and not args.skip_download:
        raise SystemExit("Set ZOTERO_API_KEY environment variable")

    work_dir = args.work_dir or args.output.parent / "rag_work"
    pdf_dir = work_dir / "pdfs"
    md_dir = work_dir / "markdown"

    # ── Stage 1: Find documents ──────────────────────────────────────────
    log.info("═══ Stage 1: Document discovery ═══")

    if args.items:
        items = [{"attachment_key": k.strip(), "title": k.strip(), "filename": ""}
                 for k in args.items.split(",")]
        log.info("Using %d specified items", len(items))
    else:
        log.info("Searching Zotero for: %s", args.query)
        items = zotero_search(args.zotero_user, zotero_key, args.query)
        log.info("Found %d items with PDF attachments", len(items))

    if not items:
        raise SystemExit("No items found")

    # ── Stage 2: Select (document-level reranking) ───────────────────────
    if args.reference and not args.items:
        log.info("\n═══ Stage 2: Document-level selection ═══")
        ref_titles = parse_reference_titles(args.reference)
        log.info("Reference set: %d titles from %s", len(ref_titles), args.reference)
        items = select_by_reference(items, ref_titles, args.match_threshold)
        log.info("Selected %d items above threshold %d", len(items), args.match_threshold)
        if not items:
            raise SystemExit("No items matched the reference set")
    elif args.reference and args.items:
        log.info("(Skipping select stage — explicit items provided)")

    if args.dry_run:
        for item in items:
            log.info("  %s: %s", item["attachment_key"],
                     item.get("title", item.get("filename", "")))
        log.info("Dry run — stopping here.")
        return

    # ── Stage 3: Fetch PDFs ──────────────────────────────────────────────
    log.info("\n═══ Stage 3: Fetch PDFs ═══")

    pdf_paths = []
    for item in items:
        if args.skip_download:
            pdf_path = pdf_dir / f"{item['attachment_key']}.pdf"
            if pdf_path.exists():
                pdf_paths.append(pdf_path)
            else:
                log.warning("  Missing: %s", pdf_path)
        else:
            pdf_path = zotero_download_pdf(
                args.zotero_user, zotero_key,
                item["attachment_key"], pdf_dir,
            )
            pdf_paths.append(pdf_path)

    log.info("Downloaded %d PDFs to %s", len(pdf_paths), pdf_dir)

    # ── Stage 4: Convert to Markdown ─────────────────────────────────────
    log.info("\n═══ Stage 4: PDF → Markdown conversion (%s) ═══", args.converter)

    md_dir.mkdir(parents=True, exist_ok=True)
    md_paths = []

    for pdf_path in pdf_paths:
        md_path = md_dir / pdf_path.with_suffix(".md").name
        if md_path.exists():
            log.info("  Already converted: %s", md_path.name)
            md_paths.append(md_path)
            continue

        log.info("  Converting: %s", pdf_path.name)
        try:
            converter = get_converter(args.converter)
            # Build backend-specific kwargs from CLI args
            convert_kwargs: dict = {}
            if args.converter == "grobid":
                convert_kwargs["grobid_url"] = args.grobid_url
                backend, model = "GROBID", "n/a"
            elif args.converter == "vision":
                convert_kwargs.update(model=args.local_vision_model,
                                      dpi=args.dpi, ollama_url=args.ollama_url)
                backend, model = "Ollama", args.local_vision_model
            else:
                convert_kwargs.update(model=args.vision_model,
                                      dpi=args.dpi, max_tokens=4096)
                backend, model = "OpenRouter", args.vision_model
            result = converter.pdf_to_markdown(pdf_path, **convert_kwargs)
            comment = _meta_comment(pdf_path, backend=backend, model=model,
                                       argv=["build_corpus", str(pdf_path)])
            md_path.write_text(result + comment, encoding="utf-8")
            md_paths.append(md_path)
            log.info("  Wrote: %s", md_path.name)
        except Exception as e:
            log.error("  Failed to convert %s: %s", pdf_path.name, e)

    log.info("Converted %d documents", len(md_paths))

    # ── Stage 5: Score and select relevant sections ──────────────────────
    log.info("\n═══ Stage 5: Section scoring via Ollama (%s) ═══",
             args.scorer_model)

    args.output.mkdir(parents=True, exist_ok=True)
    corpus_file_count = 0

    for md_path in md_paths:
        markdown = md_path.read_text(encoding="utf-8")
        sections = split_into_sections(markdown)
        log.info("  %s: %d sections", md_path.name, len(sections))

        scored = []
        for section in sections:
            result = score_section(
                section, args.scorer_model, args.ollama_url,
            )
            scored.append(result)

        # Keep sections at or above threshold
        selected = [s for s in scored if s["score"] >= args.min_score]

        if not selected:
            log.info("    No sections scored >= %d", args.min_score)
            continue

        # Group consecutive selected sections (preserve document flow)
        selected.sort(key=lambda s: (s.get("page") or 0))

        # Write one corpus file per source document (selected sections only)
        stem = md_path.stem
        corpus_path = args.output / f"{stem}.md"
        parts = [s["text"] for s in selected]
        corpus_path.write_text("\n\n".join(parts), encoding="utf-8")
        corpus_file_count += 1

        log.info("    Selected %d/%d sections → %s (%.1f kB)",
                 len(selected), len(scored), corpus_path.name,
                 corpus_path.stat().st_size / 1024)

    # ── Summary ──────────────────────────────────────────────────────────
    log.info("\n═══ Done ═══")
    log.info("Corpus files: %d in %s", corpus_file_count, args.output)
    total_bytes = sum(f.stat().st_size for f in args.output.glob("*.md"))
    log.info("Total size: %.1f kB", total_bytes / 1024)

    # Save build manifest
    manifest = {
        "items": [
            {"key": it.get("attachment_key", ""), "title": it.get("title", "")}
            for it in items
        ],
        "corpus_files": sorted(f.name for f in args.output.glob("*.md")),
        "total_bytes": total_bytes,
        "converter": args.converter,
        "scorer_model": args.scorer_model,
        "min_score": args.min_score,
    }
    manifest_path = args.output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    log.info("Manifest: %s", manifest_path)


if __name__ == "__main__":
    main()
