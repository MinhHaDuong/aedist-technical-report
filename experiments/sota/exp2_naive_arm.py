"""Naive arm — single-shot dispatch of Doc 07 to each of the four subjects.

The Exp 2 naive arm is the comparator to the optimized arm: same agents,
same task, same budget envelope, but with NO protocol scaffolding —
single user message, no system prompt, web_search enabled, single response.
The contrast with the optimized arm (Phase A meta-prompt + multi-turn
state machine) isolates the protocol's contribution.

Doc 07 (`experiments/sota/protocol_07_naive_prompt.md`) is the user-side
prompt — Doc 02's GOAL + QUALITY DIMENSIONS + FORMAT sections, with the
Phase A/B scaffolding language minimally adapted. The file's opening
meta-framing line is stripped by `strip_meta_framing` before dispatch.

Each response is classified via the dialogue classifier (Nemotron).
Outcome categories per session:
- `report`: agent produced a structured inventory
- `no_report`: clarifying question, planning text, or refusal

Usage:
    uv run python -m experiments.sota.exp2_naive_arm \\
        [--agents mistral qwen openai anthropic] [--n 5]
"""

import argparse
import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path

import yaml

from aedist.harness import append_evidence_pack
from experiments.sota import dialogue_classifier
from experiments.sota.exp2_interactive_smoke import strip_meta_framing

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
NAIVE_PROMPT_PATH = REPO_ROOT / "experiments" / "sota" / "protocol_07_naive_prompt.md"
MODELS_YAML = REPO_ROOT / "experiments" / "models.yaml"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "experiments" / "outputs" / "sota_exp2_naive_arm"

AGENTS = ("mistral", "qwen", "openai", "anthropic")
PROBE_MAX_TOKENS = 16_000  # mistral baseline
OPENAI_MAX_TOKENS = 32_000  # gpt-5.5 truncated at 16K
QWEN_MAX_TOKENS = 32_000  # qwen3.7-max (thinking disabled)
ANTHROPIC_MAX_TOKENS = 32_000  # 64K triggers SDK streaming requirement; 32K fits ~9 min
QWEN_CALL_TIMEOUT = 600  # 160K+ char prompt with evidence pack is slow
PROBE_CAP_USD = 3.00
ANTHROPIC_CAP_USD = 6.00  # input alone costs ~$1.7; 64K output adds ~$1.6


def load_naive_prompt(path: Path = NAIVE_PROMPT_PATH) -> str:
    """Read Doc 07 from disk, strip the meta-framing line, return the prompt."""
    return strip_meta_framing(path.read_text(encoding="utf-8"))


def _write_summary_md(output_dir: Path, summary: list[dict]) -> Path:
    agents_slug = "_".join(dict.fromkeys(r["agent"] for r in summary if "error" not in r))
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%MZ")
    filename = f"summary_{ts}_{agents_slug}.md"
    total_cost = sum(r.get("cost_usd", 0.0) for r in summary)
    lines = [
        "# Naive Arm Summary",
        "",
        "| Agent | Run | Model | Classification | Cost USD | Wall s | Narrative chars |",
        "|---|---:|---|---|---:|---:|---:|",
    ]
    for r in summary:
        if "error" in r:
            lines.append(f"| {r['agent']} | {r['run']} | error | error | 0 | 0 | 0 |")
        else:
            lines.append(
                "| {agent} | {run} | {model} | {cls} | {cost:.4f} | {wall:.1f} | {chars} |".format(
                    agent=r["agent"],
                    run=r["run"],
                    model=r.get("model", "?"),
                    cls=r.get("classification", "?"),
                    cost=float(r.get("cost_usd", 0.0)),
                    wall=float(r.get("wall_s", 0.0)),
                    chars=int(r.get("narrative_chars", 0)),
                )
            )
    lines += ["", f"Total cost: ${total_cost:.4f}"]
    path = output_dir / filename
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def load_model_meta(family: str) -> dict:
    registry = yaml.safe_load(MODELS_YAML.read_text())
    if isinstance(registry, dict):
        registry = registry.get("models", [])
    for entry in registry:
        if entry.get("family") == family:
            return entry
    raise ValueError(f"No entry with family={family!r} in {MODELS_YAML}")


def probe_mistral(prompt: str, output_dir: Path) -> dict:
    from aedist import adapter_mistral

    meta = load_model_meta("mistral-direct")
    raw_path = output_dir / "mistral_probe.raw.json"
    t0 = time.monotonic()
    record = adapter_mistral.run(
        prompt,
        dry_run=False,
        model_meta=meta,
        max_tokens=PROBE_MAX_TOKENS,
        cap_usd=PROBE_CAP_USD,
        agent_mode="naive_probe",
        output_path=raw_path,
    )
    narrative = ""
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    for item in raw.get("outputs", []):
        if item.get("type") == "message.output":
            content = item.get("content")
            if isinstance(content, str):
                narrative = content
            elif isinstance(content, list):
                narrative = "".join(
                    c.get("text", "")
                    for c in content
                    if isinstance(c, dict) and c.get("type") == "text"
                )
    return {
        "narrative": narrative,
        "cost_usd": (record.resource_use.cost_usd or 0) + (record.tool_calls_cost_usd or 0),
        "tokens_out": record.resource_use.tokens_out or 0,
        "wall_s": round(time.monotonic() - t0, 2),
        "model": meta.get("model_id"),
    }


def probe_openai(prompt: str, output_dir: Path) -> dict:
    """Use the Responses API directly with web_search enabled."""
    import os

    from openai import OpenAI

    meta = load_model_meta("openai-direct")
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    t0 = time.monotonic()
    resp = client.responses.create(
        model=meta.get("model_id"),
        input=prompt,
        tools=[{"type": "web_search"}],
        reasoning={"effort": "low"},  # web_search rejects 'minimal'
        max_output_tokens=OPENAI_MAX_TOKENS,
    )
    wall_s = round(time.monotonic() - t0, 2)
    narrative = ""
    for item in resp.output or []:
        if getattr(item, "type", "") == "message":
            for content in item.content or []:
                if getattr(content, "type", "") == "output_text":
                    narrative += content.text or ""
    raw_path = output_dir / "openai_probe.raw.json"
    raw_path.write_text(resp.model_dump_json(indent=2), encoding="utf-8")
    usage = resp.usage
    tokens_in = getattr(usage, "input_tokens", 0) or 0
    tokens_out = getattr(usage, "output_tokens", 0) or 0
    p_in = float(meta.get("price_per_mtok_in", 0.0)) / 1_000_000
    p_out = float(meta.get("price_per_mtok_out", 0.0)) / 1_000_000
    return {
        "narrative": narrative,
        "cost_usd": tokens_in * p_in + tokens_out * p_out,
        "tokens_out": tokens_out,
        "wall_s": wall_s,
        "model": meta.get("model_id"),
    }


def probe_qwen(prompt: str, output_dir: Path) -> dict:
    import dashscope

    meta = load_model_meta("qwen-direct")
    key_path = Path.home() / ".config" / "keys" / "alibaba.env"
    api_key = None
    if key_path.exists():
        for line in key_path.read_text().splitlines():
            line = line.strip()
            for prefix in ("DASHSCOPE_API_KEY=", "QWEN_API_KEY_AEDIST=", "QWEN_API_KEY="):
                if line.startswith(prefix):
                    api_key = line.split("=", 1)[1].strip().strip("'\"")
                    break
            if api_key:
                break
    dashscope.api_key = api_key
    dashscope.base_http_api_url = "https://dashscope-intl.aliyuncs.com/api/v1"
    dashscope.request_timeout = QWEN_CALL_TIMEOUT
    t0 = time.monotonic()
    resp = dashscope.Generation.call(
        model=meta.get("model_id"),
        messages=[{"role": "user", "content": prompt}],
        result_format="message",
        max_tokens=QWEN_MAX_TOKENS,
        enable_thinking=False,
        enable_search=True,  # the whole point of the probe
    )
    wall_s = round(time.monotonic() - t0, 2)
    narrative = ""
    if hasattr(resp, "output") and resp.output is not None:
        try:
            narrative = resp.output["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            narrative = ""
    raw_path = output_dir / "qwen_probe.raw.json"
    raw_path.write_text(json.dumps(dict(resp), default=str, indent=2), encoding="utf-8")
    usage = getattr(resp, "usage", None) or {}
    tokens_in = (usage.get("input_tokens") if isinstance(usage, dict) else 0) or 0
    tokens_out = (usage.get("output_tokens") if isinstance(usage, dict) else 0) or 0
    p_in = float(meta.get("price_per_mtok_in", 0.0)) / 1_000_000
    p_out = float(meta.get("price_per_mtok_out", 0.0)) / 1_000_000
    return {
        "narrative": narrative,
        "cost_usd": tokens_in * p_in + tokens_out * p_out,
        "tokens_out": tokens_out,
        "wall_s": wall_s,
        "model": meta.get("model_id"),
    }


def probe_anthropic(prompt: str, output_dir: Path) -> dict:
    from aedist import query_anthropic

    meta = load_model_meta("anthropic-direct")
    payload = query_anthropic.assemble_request(
        prompt,
        model=meta.get("model_id"),
        max_tokens=ANTHROPIC_MAX_TOKENS,
    )
    t0 = time.monotonic()
    result = query_anthropic.dispatch(
        payload,
        meta,
        dry_run=False,
        output_dir=output_dir,
        run=1,
        agent_mode="naive_probe",
        cap_usd=ANTHROPIC_CAP_USD,
    )
    wall_s = round(time.monotonic() - t0, 2)
    record = result.get("run_record")
    raw = result.get("raw_response")
    narrative = ""
    if isinstance(raw, dict):
        for block in raw.get("content", []):
            if isinstance(block, dict) and block.get("type") == "text":
                narrative += block.get("text", "")
    elif raw is not None and hasattr(raw, "content"):
        for block in raw.content:
            if hasattr(block, "type") and block.type == "text":
                narrative += block.text or ""
    return {
        "narrative": narrative,
        "cost_usd": record.resource_use.cost_usd if record else 0,
        "tokens_out": record.resource_use.tokens_out if record else 0,
        "wall_s": wall_s,
        "model": meta.get("model_id"),
    }


PROBERS = {
    "mistral": probe_mistral,
    "openai": probe_openai,
    "qwen": probe_qwen,
    "anthropic": probe_anthropic,
}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--agents",
        nargs="+",
        choices=AGENTS,
        default=list(AGENTS),
        help="Which subject agents to probe.",
    )
    p.add_argument(
        "--n",
        type=int,
        default=1,
        help="Replications per agent (default 1).",
    )
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    p.add_argument(
        "--evidence-pack-manifest",
        type=str,
        default=None,
        metavar="YAML",
        help="Path to an evidence-pack manifest YAML (Arm 3). Omit for Arm 1 baseline.",
    )
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    run_range = list(range(1, args.n + 1))
    use_subdir = args.n > 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    prompt = load_naive_prompt()
    prompt = append_evidence_pack(prompt, args.evidence_pack_manifest)
    log.info("Naive prompt loaded: %d chars from %s", len(prompt), NAIVE_PROMPT_PATH)

    summary: list[dict] = []
    for agent in args.agents:
        for run in run_range:
            tag = f"{agent}_run{run:02d}" if use_subdir else agent
            log.info("[%s] dispatching naive single-shot (run %d)...", agent, run)
            run_dir = args.output_dir / tag if use_subdir else args.output_dir
            run_dir.mkdir(parents=True, exist_ok=True)
            try:
                result = PROBERS[agent](prompt, run_dir)
            except Exception as exc:
                log.error("[%s run %d] failed: %s", agent, run, exc)
                summary.append({"agent": agent, "run": run, "error": str(exc)})
                continue

            narrative_path = args.output_dir / f"{tag}.md"
            narrative_path.write_text(result["narrative"], encoding="utf-8")

            cls_result = dialogue_classifier.classify_report(result["narrative"])
            classification = cls_result.class_

            meta_record = {
                "agent": agent,
                "run": run,
                "model": result["model"],
                "classification": classification,
                "tokens_out": result["tokens_out"],
                "wall_s": result["wall_s"],
                "cost_usd": round(result["cost_usd"], 4),
                "classifier_cost_usd": round(cls_result.classifier_cost_usd, 6),
                "narrative_chars": len(result["narrative"]),
                **(
                    {"evidence_pack_manifest": args.evidence_pack_manifest}
                    if args.evidence_pack_manifest
                    else {}
                ),
            }
            (args.output_dir / f"{tag}.json").write_text(
                json.dumps(meta_record, indent=2),
                encoding="utf-8",
            )
            summary.append(meta_record)
            log.info(
                "[%s run %d] class=%s tokens_out=%d cost=$%.4f wall=%.1fs chars=%d",
                agent,
                run,
                classification,
                result["tokens_out"],
                result["cost_usd"],
                result["wall_s"],
                len(result["narrative"]),
            )

    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    summary_md_path = _write_summary_md(args.output_dir, summary)
    total_cost = sum(s.get("cost_usd", 0) for s in summary)
    n_report = sum(1 for s in summary if s.get("classification") == "report")
    n_no_report = sum(1 for s in summary if s.get("classification") == "no_report")
    log.info(
        "Done. %d sessions. report=%d no_report=%d. Total cost $%.4f. Summary -> %s",
        len(summary),
        n_report,
        n_no_report,
        total_cost,
        summary_md_path,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
