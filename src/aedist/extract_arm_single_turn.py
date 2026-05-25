"""Flatten single-turn arm outputs into Exp2-mart-compatible per-run artifacts."""

import argparse
import json
import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)

_META_JSON_RE = re.compile(r"^[a-z]+\.json$")
_RUN_DIR_RE = re.compile(r"^run(\d+)$")
_BIB_HEADER_RE = re.compile(
    r"^#{1,6}\s+.*(?:sources|references|bibliography|annotated\s+bibliography)",
    re.IGNORECASE,
)
_BIB_ENTRY_RE = re.compile(r"^(?:[-*+]\s+|\d+[.)]\s+|\*\*\[[^\]]+\]\*\*\s*|\[[^\]]+\]\s*)")


def _extract_markdown_from_payload(payload: dict) -> str:
    run_record = payload.get("run_record")
    if isinstance(run_record, dict):
        messages = run_record.get("method_params", {}).get("extra", {}).get("messages", [])
        for message in reversed(messages):
            if message.get("role") == "assistant" and isinstance(message.get("content"), str):
                return message["content"]

    outputs = payload.get("outputs")
    if isinstance(outputs, list):
        for item in reversed(outputs):
            if item.get("role") != "assistant":
                continue
            content = item.get("content", [])
            if isinstance(content, str) and content.strip():
                return content
            parts = content
            texts = [
                part.get("text", "")
                for part in parts
                if isinstance(part, dict)
                and part.get("type") == "text"
                and isinstance(part.get("text"), str)
            ]
            markdown = "".join(texts).strip()
            if markdown:
                return markdown

    output = payload.get("output")
    if isinstance(output, dict):
        choices = output.get("choices", [])
        for choice in choices:
            message = choice.get("message", {})
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content

    if isinstance(output, list):
        for item in reversed(output):
            if item.get("type") != "message":
                continue
            parts = item.get("content", [])
            texts = [
                part.get("text", "")
                for part in parts
                if part.get("type") in {"output_text", "text"}
                and isinstance(part.get("text"), str)
            ]
            markdown = "".join(texts).strip()
            if markdown:
                return markdown

    raise ValueError("unable to extract assistant markdown from payload")


def _load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_raw_payload(run_dir: Path, agent: str) -> dict:
    for candidate in sorted(run_dir.glob(f"{agent}*.json")):
        if candidate.name == f"{agent}.json":
            continue
        payload = _load_json(candidate)
        if isinstance(payload, dict):
            try:
                _extract_markdown_from_payload(payload)
            except ValueError:
                continue
            return payload
    raise FileNotFoundError(f"no raw payload found for {agent} in {run_dir}")


def _extract_bib_section(markdown: str) -> str:
    lines = markdown.splitlines()
    start = None
    header_level = None

    for index, line in enumerate(lines):
        stripped = line.strip()
        if _BIB_HEADER_RE.match(stripped):
            start = index + 1
            header_level = len(stripped) - len(stripped.lstrip("#"))
            break

    if start is None:
        return ""

    section: list[str] = []
    for line in lines[start:]:
        stripped = line.strip()
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            if level <= header_level:
                break
        section.append(line)

    return "\n".join(section).strip()


def _normalize_bib_entry(text: str) -> str:
    normalized = _BIB_ENTRY_RE.sub("", text.strip())
    normalized = re.sub(r"^\*\*|\*\*$", "", normalized)
    return normalized.strip()


def _extract_bibliography_entries(markdown: str) -> list[str]:
    section = _extract_bib_section(markdown)
    if not section:
        return []

    entries: list[str] = []
    current: list[str] = []
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("|"):
            continue
        if _BIB_ENTRY_RE.match(line):
            if current:
                entry = _normalize_bib_entry(" ".join(current))
                if entry:
                    entries.append(entry)
            current = [line]
            continue
        if current:
            current.append(line)

    if current:
        entry = _normalize_bib_entry(" ".join(current))
        if entry:
            entries.append(entry)
    return entries


def _write_text(path: Path, content: str) -> None:
    path.write_text(f"{content.rstrip()}\n", encoding="utf-8")


def flatten_single_turn_arm(input_dir: Path, output_dir: Path) -> list[Path]:
    written: list[Path] = []
    output_dir.mkdir(parents=True, exist_ok=True)

    for run_dir in sorted(path for path in input_dir.iterdir() if path.is_dir()):
        run_match = _RUN_DIR_RE.match(run_dir.name)
        if run_match is None:
            continue
        run = int(run_match.group(1))

        for meta_path in sorted(run_dir.glob("*.json")):
            if not _META_JSON_RE.match(meta_path.name) or meta_path.stem == "summary":
                continue
            meta = _load_json(meta_path)
            if not isinstance(meta, dict) or meta.get("agent") != meta_path.stem:
                continue

            agent = str(meta["agent"])
            payload = _find_raw_payload(run_dir, agent)
            markdown = _extract_markdown_from_payload(payload)
            bib_entries = _extract_bibliography_entries(markdown)

            normalized = dict(meta)
            normalized["run"] = run
            normalized["class_trace"] = (
                [meta.get("classification")] if meta.get("classification") else []
            )
            normalized["n_bib_entries"] = len(bib_entries)

            base_name = f"{agent}_run{run:02d}"
            json_path = output_dir / f"{base_name}.json"
            md_path = output_dir / f"{base_name}.md"
            bib_path = output_dir / f"{base_name}_bib.md"

            _write_text(
                json_path, json.dumps(normalized, indent=2, sort_keys=True, ensure_ascii=False)
            )
            _write_text(md_path, markdown)
            bib_content = "\n".join(f"- {entry}" for entry in bib_entries)
            _write_text(bib_path, bib_content)
            written.extend([json_path, md_path, bib_path])

    return written


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Flatten single-turn arm outputs into per-run artifacts"
    )
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    written = flatten_single_turn_arm(args.input_dir, args.output_dir)
    log.info("wrote %d artifacts to %s", len(written), args.output_dir)


if __name__ == "__main__":
    main()
