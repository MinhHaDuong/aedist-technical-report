"""CLI module to extract multi-turn arm2 outputs into flat files.

Pipeline phase: P2 (score & consolidate) — invoked by experiments/derived/score.mk.

Walks an input directory shaped like::

    sota_exp3_arm2_batch1/
      run01/
        summary.json
        {agent}_run01/
          {agent}_turn_01.record.json
          {agent}_turn_02.record.json
          ...

and writes per-run×agent flat files into the output directory::

    {agent}_run{N}.json   – normalized metadata
    {agent}_run{N}.md     – verbatim model text from the last turn
    {agent}_run{N}_bib.md – bibliography section extracted from that text
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
from pathlib import Path
from typing import Any

from .extract import _extract_pipe_tables, parse_and_canonicalize, score_csv_like_block

_BIB_HEADING_RE = re.compile(
    r"^(#{1,3}\s*(?:Annotated\s+)?Bibliography"
    r"|#{1,3}\s*Sources"
    r"|#{1,3}\s*References)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

_TURN_RECORD_RE = re.compile(r"_turn_(\d+)\.record\.json$")
_TURN_RAW_RE = re.compile(r"_turn_(\d+)\.raw\.json$")


def extract_agent_name(dir_name: str) -> str:
    """Derive the agent slug from a subdirectory like ``anthropic_run01``."""
    return re.sub(r"_run\d+$", "", dir_name)


def find_turns_descending(agent_dir: Path) -> list[Path]:
    """Return turn record paths in *agent_dir* ordered most-recent-first.

    Prefers ``*_turn_N.record.json`` files; falls back to ``*_turn_N.raw.json``
    only when no record files exist (mirrors the historical lookup order).
    """
    candidates: list[tuple[int, Path]] = []
    for path in agent_dir.glob("*_turn_*.record.json"):
        match = _TURN_RECORD_RE.search(path.name)
        if match:
            candidates.append((int(match.group(1)), path))
    if not candidates:
        for path in agent_dir.glob("*_turn_*.raw.json"):
            match = _TURN_RAW_RE.search(path.name)
            if match:
                candidates.append((int(match.group(1)), path))
    candidates.sort(key=lambda x: x[0], reverse=True)
    return [path for _, path in candidates]


def find_last_turn(agent_dir: Path) -> Path | None:
    """Return the path to the highest-numbered turn record in *agent_dir*."""
    turns = find_turns_descending(agent_dir)
    return turns[0] if turns else None


def _raw_sibling(turn_path: Path) -> Path | None:
    """Map a ``*_turn_N.record.json`` path to its ``*_turn_N.raw.json`` sibling.

    Returns ``None`` when *turn_path* is not a record file (e.g. it is already a
    raw file, so there is no further fallback to attempt).
    """
    if not turn_path.name.endswith(".record.json"):
        return None
    raw_name = turn_path.name[: -len(".record.json")] + ".raw.json"
    return turn_path.with_name(raw_name)


def extract_output_text(record: dict[str, Any]) -> str:
    """Pull the model's text response out of a record JSON.

    Handles four provider formats before the generic fallbacks:
    - Anthropic native: ``content`` is a list at root with type="text" blocks.
    - Qwen: ``output`` is a dict with a ``choices`` key.
    - Mistral Agents: ``outputs`` is a list of message items.
    - OpenAI-style: ``output`` is a list of message items (existing branch).
    """
    # Anthropic native: {"content": [{"type": "thinking", ...}, {"type": "text", "text": "..."}]}
    content_root = record.get("content")
    if isinstance(content_root, list):
        text = " ".join(
            block.get("text", "")
            for block in content_root
            if isinstance(block, dict) and block.get("type") == "text"
        )
        if text.strip():
            return text.strip()

    # Qwen: {"output": {"choices": [{"message": {"content": "..."}}]}}
    output = record.get("output")
    if isinstance(output, dict) and "choices" in output:
        choices = output.get("choices", [])
        if choices:
            msg_content = choices[0].get("message", {}).get("content", "")
            if isinstance(msg_content, str) and msg_content.strip():
                return msg_content.strip()

    # Mistral Agents: {"outputs": [{"type": "message.output", "content": "..."}]}
    outputs = record.get("outputs")
    if isinstance(outputs, list):
        for item in reversed(outputs):
            if item.get("type") == "message.output":
                item_content = item.get("content", "")
                if isinstance(item_content, list):
                    text = " ".join(
                        block.get("text", "") for block in item_content if isinstance(block, dict)
                    )
                    if text.strip():
                        return text.strip()
                elif isinstance(item_content, str) and item_content.strip():
                    return item_content.strip()

    # OpenAI-style: {"output": [{"type": "message", "content": [...]}]}
    if isinstance(output, list):
        for item in output:
            if item.get("type") != "message":
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            texts = [
                part.get("text", "")
                for part in content
                if isinstance(part, dict)
                and part.get("type") in {"output_text", "text"}
                and isinstance(part.get("text"), str)
            ]
            merged = "".join(texts).strip()
            if merged:
                return merged

    for key in ("output", "text", "content", "response"):
        value = record.get(key)
        if isinstance(value, str):
            return value
    justification = record.get("justification")
    if isinstance(justification, dict):
        text = justification.get("output_text")
        if isinstance(text, str):
            return text
    return ""


def _read_turn_text(turn_path: Path) -> str:
    """Read the model text from a turn record, with raw-sibling fallback.

    Some providers (mistral-direct) write the report only into the sibling
    ``.raw.json`` — their ``.record.json`` has an empty justification. When the
    record yields no text, re-extract from the matching raw payload.
    """
    with turn_path.open(encoding="utf-8") as fh:
        record = json.load(fh)
    text = extract_output_text(record)
    if not text:
        raw_path = _raw_sibling(turn_path)
        if raw_path is not None and raw_path.exists():
            with raw_path.open(encoding="utf-8") as fh:
                raw_record = json.load(fh)
            text = extract_output_text(raw_record)
    return text


def _count_inventory_rows(text: str) -> int:
    tables = _extract_pipe_tables(text)
    if not tables:
        return 0
    best = max(tables, key=score_csv_like_block)
    try:
        canonical_csv = parse_and_canonicalize(best)
    except Exception:
        lines = [ln.strip() for ln in best.splitlines() if ln.strip()]
        data_rows = [
            ln for ln in lines if ln.count("|") >= 3 and not re.match(r"^\|?[\s\-:|]+\|?$", ln)
        ]
        return max(len(data_rows) - 1, 0)
    return len(list(csv.DictReader(io.StringIO(canonical_csv))))


def extract_bibliography(text: str) -> tuple[str | None, int]:
    """Split bibliography section from report text.

    Returns ``(bib_text, n_entries)``.  *bib_text* is ``None`` when no
    recognised heading is found.
    """
    match = _BIB_HEADING_RE.search(text)
    if not match:
        return None, 0

    bib_text = text[match.start() :].strip()
    lines = bib_text.splitlines()

    # Count lines that look like list items (numbered or bulleted)
    entries = 0
    for line in lines[1:]:  # skip the heading itself
        if re.match(r"^\s*(?:\d+\.|[-*])\s", line):
            entries += 1

    # Fallback: if no list markers, count non-empty lines after the heading
    if entries == 0:
        entries = sum(1 for line in lines[1:] if line.strip())

    return bib_text, entries


def process_batch(input_dir: Path, output_dir: Path) -> None:
    """Transform one arm2 batch tree into flat files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for run_dir in sorted(input_dir.glob("run*")):
        if not run_dir.is_dir():
            continue

        run_match = re.match(r"run(\d+)", run_dir.name, re.IGNORECASE)
        if not run_match:
            continue
        run_num = int(run_match.group(1))

        summary_path = run_dir / "summary.json"
        if not summary_path.exists():
            continue
        with summary_path.open(encoding="utf-8") as fh:
            summaries: list[dict[str, Any]] = json.load(fh)

        for entry in summaries:
            if entry.get("status") != "pass":
                continue

            agent: str = entry["agent"]

            # Locate the agent subdirectory (e.g. anthropic_run01)
            agent_dirs = [
                d for d in run_dir.iterdir() if d.is_dir() and extract_agent_name(d.name) == agent
            ]
            if not agent_dirs:
                continue
            agent_dir = agent_dirs[0]

            turns_desc = find_turns_descending(agent_dir)
            if not turns_desc:
                continue

            chosen_turn_path = turns_desc[0]
            text = _read_turn_text(chosen_turn_path)

            # Earlier-turn fallback: some runs end with a short meta-message
            # ("the inventory table has been produced in full above … budget
            # won't permit more") whose turn yields no inventory rows. The
            # actual table lives in an earlier turn. When the last turn has no
            # inventory table, scan earlier turns most-recent-first and adopt
            # the first one that does. Runs whose last turn already carries a
            # table are unaffected.
            if _count_inventory_rows(text) == 0:
                for earlier_path in turns_desc[1:]:
                    earlier_text = _read_turn_text(earlier_path)
                    if _count_inventory_rows(earlier_text) > 0:
                        chosen_turn_path = earlier_path
                        text = earlier_text
                        break

            with chosen_turn_path.open(encoding="utf-8") as fh:
                record = json.load(fh)

            bib_text, n_bib = extract_bibliography(text)

            model: str | None = None
            method_params = record.get("method_params")
            if isinstance(method_params, dict):
                model = method_params.get("model")
            if not model:
                model = record.get("model")
            if not model:
                # Some run01 final-turn records carry no model (their text came
                # via the raw fallback). Recover it from the agent's Phase A
                # design record, which always records the dispatched model.
                phase_a = next(agent_dir.glob("*_phase_a.json"), None)
                if phase_a is not None:
                    with phase_a.open(encoding="utf-8") as fh:
                        pa = json.load(fh)
                    pa_mp = pa.get("method_params")
                    model = (pa_mp or {}).get("model") if isinstance(pa_mp, dict) else None
                    model = model or pa.get("model")

            raw_trace = entry.get("class_trace")
            class_trace: list[str] = []
            if isinstance(raw_trace, str) and raw_trace:
                class_trace = [s.strip() for s in raw_trace.split(",") if s.strip()]

            inventory_rows = _count_inventory_rows(text)

            metadata = {
                "agent": agent,
                "model": model,
                "run": run_num,
                "classification": class_trace[-1] if class_trace else None,
                "total_cost_usd": entry.get("total_cost_usd"),
                "wall_s": entry.get("wall_s"),
                "turns": entry.get("turns"),
                "class_trace": class_trace,
                "n_rows": inventory_rows,
                "n_bib_entries": n_bib,
                "narrative_chars": len(text),
            }

            base_name = f"{agent}_run{run_num:02d}"
            (output_dir / f"{base_name}.json").write_text(
                json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            (output_dir / f"{base_name}.md").write_text(text, encoding="utf-8")
            (output_dir / f"{base_name}_bib.md").write_text(
                bib_text if bib_text is not None else "",
                encoding="utf-8",
            )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Extract arm2 multi-turn outputs into flat files."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Root directory containing run{N}/ subdirectories.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory where flat files will be written.",
    )
    args = parser.parse_args(argv)
    process_batch(args.input_dir, args.output_dir)


if __name__ == "__main__":
    main()
