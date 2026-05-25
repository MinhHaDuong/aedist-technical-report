"""CLI module to extract multi-turn arm2 outputs into flat files.

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
import json
import re
from pathlib import Path
from typing import Any

_BIB_HEADING_RE = re.compile(
    r"^(#{1,3}\s*(?:Annotated\s+)?Bibliography"
    r"|#{1,3}\s*Sources"
    r"|#{1,3}\s*References)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

_TURN_RE = re.compile(r"_turn_(\d+)\.record\.json$")


def extract_agent_name(dir_name: str) -> str:
    """Derive the agent slug from a subdirectory like ``anthropic_run01``."""
    return re.sub(r"_run\d+$", "", dir_name)


def find_last_turn(agent_dir: Path) -> Path | None:
    """Return the path to the highest-numbered turn record in *agent_dir*."""
    candidates: list[tuple[int, Path]] = []
    for path in agent_dir.glob("*_turn_*.record.json"):
        match = _TURN_RE.search(path.name)
        if match:
            candidates.append((int(match.group(1)), path))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[-1][1]


def extract_output_text(record: dict[str, Any]) -> str:
    """Pull the model's text response out of a record JSON."""
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

            last_turn_path = find_last_turn(agent_dir)
            if last_turn_path is None:
                continue

            with last_turn_path.open(encoding="utf-8") as fh:
                record = json.load(fh)

            text = extract_output_text(record)
            bib_text, n_bib = extract_bibliography(text)

            model: str | None = None
            method_params = record.get("method_params")
            if isinstance(method_params, dict):
                model = method_params.get("model")

            raw_trace = entry.get("class_trace")
            class_trace: list[str] = []
            if isinstance(raw_trace, str) and raw_trace:
                class_trace = [s.strip() for s in raw_trace.split(",") if s.strip()]

            metadata = {
                "agent": agent,
                "model": model,
                "run": run_num,
                "classification": class_trace[-1] if class_trace else None,
                "total_cost_usd": entry.get("total_cost_usd"),
                "wall_s": entry.get("wall_s"),
                "turns": entry.get("turns"),
                "class_trace": class_trace,
                "n_rows": entry.get("inventory_rows"),
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
