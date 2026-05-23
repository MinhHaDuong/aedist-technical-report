"""Consolidate Phase B-0 per-agent subdirectory output into naive-arm layout.

Reads the per-agent subdirectories produced by exp2_interactive_smoke.py and
emits a layout that matches the naive arm (3 files per run + probes subdir):

    <phase-b0-dir>/
      README.md
      summary.json
      {agent}_run01.md         # narrative from final report turn
      {agent}_run01.json       # per-run metadata record
      {agent}_run01.raw.json   # raw provider response (final report turn)
      probes/
        {agent}/               # per-turn debug artefacts (moved)
        summary_openai+qwen.md # preserved first-attempt audit (moved)
        summary.md             # script-generated 2-agent table (moved)
"""

import argparse
import json
import logging
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path

log = logging.getLogger(__name__)

AGENTS = ["openai", "qwen", "mistral", "anthropic"]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _turn_files(agent_dir: Path, agent: str) -> list[Path]:
    return sorted(agent_dir.glob(f"{agent}_turn_*.cost.json"))


def _turn_number(path: Path) -> int:
    m = re.search(r"_turn_(\d+)\.", path.name)
    return int(m.group(1)) if m else 0


def _narrative_from_raw(raw_path: Path) -> str:
    """Extract plain-text narrative from a raw provider response file.

    Handles OpenAI (choices[0].message.content), Anthropic (content[*].text),
    and Mistral Agents API (outputs[0].content[*].text) response shapes.
    Returns empty string on any failure.
    """
    try:
        raw = _load_json(raw_path)
    except Exception:
        return ""
    # OpenAI / OpenRouter chat completions
    choices = raw.get("choices")
    if choices:
        msg = choices[0].get("message") or {}
        c = msg.get("content") or ""
        if isinstance(c, str):
            return c
        if isinstance(c, list):
            return "".join(item.get("text", "") for item in c if item.get("type") == "text")
    # Anthropic messages API
    content = raw.get("content")
    if isinstance(content, list):
        return "".join(item.get("text", "") for item in content if item.get("type") == "text")
    # Mistral Agents API: outputs[0].content[*].{type,text}
    outputs = raw.get("outputs")
    if outputs and isinstance(outputs, list):
        items = outputs[0].get("content") or []
        return "".join(item.get("text", "") for item in items if item.get("type") == "text")
    return ""


def _count_table_rows(text: str) -> int:
    """Count non-header markdown table rows (lines starting with | that aren't ---separators)."""
    rows = 0
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            if re.match(r"^\|[-| :]+\|$", stripped):
                in_table = True
                continue
            if in_table:
                rows += 1
        else:
            in_table = False
    return rows


def _process_agent(agent_dir: Path, agent: str) -> dict:
    turn_cost_files = sorted(_turn_files(agent_dir, agent), key=_turn_number)
    turns = len(turn_cost_files)

    # Build class trace; track last turn and last report turn separately.
    class_trace_parts = []
    last_turn_base: Path | None = None
    last_report_turn_base: Path | None = None
    total_phase_b_cost = 0.0
    total_wall_s = 0.0
    total_classifier_cost = 0.0

    for cost_path in turn_cost_files:
        cost = _load_json(cost_path)
        cls = cost.get("classification", "no_report")
        class_trace_parts.append(cls)
        total_phase_b_cost += float(cost.get("spent_usd", 0.0))
        total_classifier_cost += float(cost.get("classifier_cost_usd", 0.0))

        base = Path(str(cost_path).replace(".cost.json", ""))
        record_path = base.parent / (base.name + ".record.json")
        if record_path.exists():
            rec = _load_json(record_path)
            total_wall_s += float((rec.get("resource_use") or {}).get("wall_s") or 0.0)
        last_turn_base = base
        if cls == "report":
            last_report_turn_base = base

    # Use last report turn if any; otherwise fall back to last turn.
    final_report_turn = last_report_turn_base or last_turn_base

    class_trace = "→".join(class_trace_parts)
    final_classification = (
        "report"
        if last_report_turn_base
        else (class_trace_parts[-1] if class_trace_parts else "no_report")
    )

    # Phase A cost
    phase_a_path = agent_dir / f"{agent}_phase_a.json"
    phase_a_cost = 0.0
    model = "unknown"
    if phase_a_path.exists():
        phase_a = _load_json(phase_a_path)
        phase_a_cost = float((phase_a.get("resource_use") or {}).get("cost_usd") or 0.0)
        model = (phase_a.get("method_params") or {}).get("model") or "unknown"

    # Narrative and metadata from final turn
    narrative = ""
    tokens_out = 0
    narrative_chars = 0
    inventory_rows = None

    if final_report_turn is not None:
        record_path = final_report_turn.parent / (final_report_turn.name + ".record.json")
        if record_path.exists():
            rec = _load_json(record_path)
            ru = rec.get("resource_use") or {}
            tokens_out = int(ru.get("tokens_out") or 0)
            if not model or model == "unknown":
                model = (rec.get("method_params") or {}).get("model") or "unknown"
            j = rec.get("justification") or {}
            narrative = j.get("output_text") or ""
            if not narrative:
                raw_path = final_report_turn.parent / (final_report_turn.name + ".raw.json")
                narrative = _narrative_from_raw(raw_path)
            narrative_chars = len(narrative)
            inventory_rows = _count_table_rows(narrative) or None

    return {
        "agent": agent,
        "run": 1,
        "arm": "optimized",
        "model": model,
        "classification": final_classification,
        "turns": turns,
        "class_trace": class_trace,
        "inventory_rows": inventory_rows,
        "phase_a_cost_usd": round(phase_a_cost, 6),
        "phase_b_cost_usd": round(total_phase_b_cost, 6),
        "total_cost_usd": round(phase_a_cost + total_phase_b_cost, 6),
        "classifier_cost_usd": round(total_classifier_cost, 6),
        "wall_s": round(total_wall_s, 1),
        "tokens_out": tokens_out,
        "narrative_chars": narrative_chars,
        "_narrative": narrative,
        "_final_turn_base": str(final_report_turn) if final_report_turn else None,
    }


def _write_readme(output_dir: Path, records: list[dict], run_date: str, probes_dir: Path) -> None:
    lines = [
        "# Exp 2 Optimized Arm — Phase B-0 Gate",
        "",
        f"Run date: {run_date}",
        "",
        "## Per-agent results",
        "",
        "| Agent | Model | Classification | Turns | Total cost | Inventory rows |",
        "|-------|-------|---------------|------:|-----------:|---------------:|",
    ]
    total_cost = 0.0
    for r in records:
        cls = r.get("classification", "n/a")
        rows = r.get("inventory_rows")
        rows_str = str(rows) if rows is not None else "n/a"
        lines.append(
            f"| {r['agent']} | {r['model']} | {cls} | {r['turns']} "
            f"| ${r['total_cost_usd']:.4f} | {rows_str} |"
        )
        total_cost += r.get("total_cost_usd", 0.0)

    lines += [
        "",
        f"**Total cost:** ${total_cost:.4f}",
        "",
        "## Classifier note",
        "",
        "OpenAI and Qwen runs (first attempt, 2026-05-22) had a broken classifier:",
        "`OPENROUTER_API_KEY` was absent from the subprocess environment.",
        "Turns 1–3 (openai) and 1–2 (qwen) returned `no_report` with `classifier_cost_usd=0.0`.",
        "The classifier was re-run on the final turns (2026-05-23) and returned `report` for both.",
        "",
        "Mistral and Anthropic re-runs (second attempt, 2026-05-23) used `uv run`",
        "so the classifier fired correctly on all turns.",
        "",
        "## Gating verdict",
        "",
    ]
    probe_summaries = sorted(probes_dir.glob("summary_*.md"))
    if probe_summaries:
        lines.append("Probe audit files in `probes/`:")
        for f in probe_summaries:
            lines.append(f"- `{f.name}`")
    lines += [
        "",
        "## File layout",
        "",
        "- `{agent}_run01.md` — inventory narrative from final report turn",
        "- `{agent}_run01.json` — per-run metadata record",
        "- `{agent}_run01.raw.json` — raw provider response (final report turn)",
        "- `summary.json` — machine-readable array of per-agent records",
        "- `probes/` — per-turn debug artefacts and earlier audit files",
    ]
    (output_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def consolidate(phase_b0_dir: Path, run_number: int = 1) -> None:
    probes_dir = phase_b0_dir / "probes"
    probes_dir.mkdir(exist_ok=True)

    run_date = datetime.now(UTC).strftime("%Y-%m-%d")
    records = []

    for agent in AGENTS:
        agent_dir = phase_b0_dir / f"{agent}_run{run_number:02d}"
        if not agent_dir.is_dir():
            log.warning("No subdir for %s (run %02d) — skipping", agent, run_number)
            records.append(
                {
                    "agent": agent,
                    "run": run_number,
                    "arm": "optimized",
                    "model": "n/a",
                    "classification": "n/a",
                    "turns": 0,
                    "class_trace": "",
                    "inventory_rows": None,
                    "phase_a_cost_usd": 0.0,
                    "phase_b_cost_usd": 0.0,
                    "total_cost_usd": 0.0,
                    "classifier_cost_usd": 0.0,
                    "wall_s": 0.0,
                    "tokens_out": 0,
                    "narrative_chars": 0,
                }
            )
            continue

        log.info("Processing %s ...", agent)
        rec = _process_agent(agent_dir, agent)
        narrative = rec.pop("_narrative", "")
        final_turn_base = rec.pop("_final_turn_base", None)

        run_slug = f"run{run_number:02d}"
        (phase_b0_dir / f"{agent}_{run_slug}.md").write_text(narrative, encoding="utf-8")

        run_json = {k: v for k, v in rec.items()}
        (phase_b0_dir / f"{agent}_{run_slug}.json").write_text(
            json.dumps(run_json, indent=2), encoding="utf-8"
        )

        if final_turn_base:
            raw_src = Path(final_turn_base + ".raw.json")
            if raw_src.exists():
                shutil.copy2(raw_src, phase_b0_dir / f"{agent}_{run_slug}.raw.json")
            else:
                log.warning("raw.json not found for %s final turn: %s", agent, raw_src)
        else:
            log.warning("No final turn found for %s — raw.json not copied", agent)

        records.append(rec)

        # Move agent subdir to probes/
        dest = probes_dir / f"{agent}_{run_slug}"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.move(str(agent_dir), str(dest))
        log.info("Moved %s/ → probes/%s/", agent_dir.name, dest.name)

    # Move any summary_*.md files from top level to probes/
    for src in phase_b0_dir.glob("summary_*.md"):
        shutil.move(str(src), str(probes_dir / src.name))
        log.info("Moved %s → probes/", src.name)

    # Write summary.json and README.md
    (phase_b0_dir / "summary.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    _write_readme(phase_b0_dir, records, run_date, probes_dir)

    log.info("Consolidation complete. Output: %s", phase_b0_dir)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--phase-b0-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "outputs" / "sota_exp2_phase_b0",
        help="Path to the Phase B-0 output directory.",
    )
    p.add_argument(
        "--run-number",
        type=int,
        default=1,
        help="Rep number to consolidate (1-indexed). Reads <agent>_run{N:02d}/ subdirs.",
    )
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if not args.phase_b0_dir.is_dir():
        log.error("Directory not found: %s", args.phase_b0_dir)
        return 1

    consolidate(args.phase_b0_dir, run_number=args.run_number)
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
