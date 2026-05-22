"""Dispatch the Exp 2 protocol spec to each of the four SOTA agents for blind review.

Ticket 0224 (author's "now" idea #2). One call per agent, no multi-turn.
Each agent receives `exp2_protocol_spec.md` verbatim and is asked to
return a review + VERDICT line.

Single-pass. No state machine, no classifier. Pure dispatch + collect.
Outputs land under `experiments/outputs/sota_exp2_protocol_review/`.
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import yaml

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = REPO_ROOT / "experiments" / "sota" / "exp2_protocol_spec.md"
MODELS_YAML = REPO_ROOT / "experiments" / "models.yaml"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "experiments" / "outputs" / "sota_exp2_protocol_review"

AGENTS = ("mistral", "qwen", "openai", "anthropic")


def load_model_meta(family: str) -> dict:
    """Read the SOTA-route registry entry by family name."""
    registry = yaml.safe_load(MODELS_YAML.read_text())
    if isinstance(registry, dict):
        registry = registry.get("models", [])
    for entry in registry:
        if entry.get("family") == family:
            return entry
    raise ValueError(f"No entry with family={family!r} found in {MODELS_YAML}")


def review_mistral(spec: str, output_dir: Path) -> dict:
    from aedist import adapter_mistral

    meta = load_model_meta("mistral-direct")
    raw_path = output_dir / "mistral_review.raw.json"
    t0 = time.monotonic()
    try:
        record = adapter_mistral.run(
            spec,
            dry_run=False,
            model_meta=meta,
            max_tokens=2000,
            cap_usd=0.50,
            agent_mode="protocol_review",
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
        wall_s = round(time.monotonic() - t0, 2)
        return {
            "narrative": narrative,
            "cost_usd": (record.resource_use.cost_usd or 0) + (record.tool_calls_cost_usd or 0),
            "tokens_out": record.resource_use.tokens_out,
            "wall_s": wall_s,
            "model": meta.get("model_id"),
        }
    except AttributeError as exc:
        log.warning("Mistral adapter parse failed (%s); reading from raw", exc)
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        narrative = ""
        for item in raw.get("outputs", []):
            if item.get("type") == "message.output":
                content = item.get("content")
                if isinstance(content, str):
                    narrative = content
        usage = raw.get("usage", {})
        wall_s = round(time.monotonic() - t0, 2)
        p_in = float(meta.get("price_per_mtok_in", 0.0)) / 1_000_000
        p_out = float(meta.get("price_per_mtok_out", 0.0)) / 1_000_000
        return {
            "narrative": narrative,
            "cost_usd": int(usage.get("prompt_tokens", 0)) * p_in
            + int(usage.get("completion_tokens", 0)) * p_out,
            "tokens_out": int(usage.get("completion_tokens", 0)),
            "wall_s": wall_s,
            "model": meta.get("model_id"),
        }


def review_openai(spec: str, output_dir: Path) -> dict:
    """Bypass the adapter — review is a plain text call, no tools needed.

    The adapter forces a web_search tool which OpenAI rejects when
    reasoning.effort='minimal' (HTTP 400). Reviews are pure reasoning
    over the spec; no need for web. Call client.responses.create
    directly with no tools.
    """
    import os

    from openai import OpenAI

    meta = load_model_meta("openai-direct")
    # OpenAI adapter reads the key from a file; replicate the lookup here.
    key_path = Path.home() / ".config" / "keys" / "openai.env"
    api_key = None
    if key_path.exists():
        for line in key_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("OPENAI_API_KEY="):
                api_key = line.split("=", 1)[1].strip().strip("'\"")
                break
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    t0 = time.monotonic()
    resp = client.responses.create(
        model=meta.get("model_id"),
        input=spec,
        max_output_tokens=2000,
        reasoning={"effort": "low"},
    )
    wall_s = round(time.monotonic() - t0, 2)
    narrative = ""
    for item in resp.output or []:
        if getattr(item, "type", "") == "message":
            for content in item.content or []:
                if getattr(content, "type", "") == "output_text":
                    narrative += content.text or ""
    raw_path = output_dir / "openai_review.raw.json"
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


def review_qwen(spec: str, output_dir: Path) -> dict:
    """Bypass the adapter — the dashscope adapter parses but does not expose narrative.

    Call dashscope.Generation.call directly so we can capture the raw
    response text. No thinking, no search (this is a review, not a
    retrieval task).
    """
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
    t0 = time.monotonic()
    resp = dashscope.Generation.call(
        model=meta.get("model_id"),
        messages=[{"role": "user", "content": spec}],
        result_format="message",
        max_tokens=2000,
        enable_thinking=False,
        enable_search=False,
    )
    wall_s = round(time.monotonic() - t0, 2)
    narrative = ""
    if hasattr(resp, "output") and resp.output is not None:
        try:
            narrative = resp.output["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            narrative = ""
    raw_path = output_dir / "qwen_review.raw.json"
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


def review_anthropic(spec: str, output_dir: Path) -> dict:
    from aedist import query_anthropic

    meta = load_model_meta("anthropic-direct")
    payload = query_anthropic.assemble_request(
        spec,
        model=meta.get("model_id"),
        max_tokens=2000,
    )
    t0 = time.monotonic()
    result = query_anthropic.dispatch(
        payload,
        meta,
        dry_run=False,
        output_dir=output_dir,
        run=1,
        agent_mode="protocol_review",
        cap_usd=1.00,
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


REVIEWERS = {
    "mistral": review_mistral,
    "qwen": review_qwen,
    "openai": review_openai,
    "anthropic": review_anthropic,
}


def extract_verdict(narrative: str) -> str:
    """Pull the VERDICT: line out of the agent's review, or empty if absent."""
    for line in reversed(narrative.splitlines()):
        line = line.strip().strip("`").strip()
        if line.startswith("VERDICT:"):
            return line
    return ""


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--agents",
        nargs="*",
        choices=AGENTS,
        default=list(AGENTS),
        help="Subset of agents to dispatch to (default: all four).",
    )
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    spec = SPEC_PATH.read_text(encoding="utf-8")
    log.info("Spec loaded: %d chars from %s", len(spec), SPEC_PATH)

    summary: list[dict] = []
    for agent in args.agents:
        log.info("[%s] dispatching protocol review...", agent)
        try:
            result = REVIEWERS[agent](spec, args.output_dir)
        except Exception as exc:  # noqa: BLE001 — keep going, log + record
            log.exception("[%s] review failed: %s", agent, exc)
            summary.append({"agent": agent, "status": "failed", "error": repr(exc)[:500]})
            continue
        verdict = extract_verdict(result["narrative"])
        log.info(
            "[%s] done cost=$%.4f tokens_out=%s wall=%.1fs verdict=%r",
            agent,
            result["cost_usd"],
            result["tokens_out"],
            result["wall_s"],
            verdict,
        )
        review_path = args.output_dir / f"{agent}_review.md"
        review_path.write_text(result["narrative"], encoding="utf-8")
        meta_path = args.output_dir / f"{agent}_review.json"
        meta_path.write_text(
            json.dumps(
                {
                    "agent": agent,
                    "model": result["model"],
                    "verdict": verdict,
                    "cost_usd": result["cost_usd"],
                    "tokens_out": result["tokens_out"],
                    "wall_s": result["wall_s"],
                    "review_chars": len(result["narrative"]),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        summary.append(
            {
                "agent": agent,
                "status": "ok",
                "verdict": verdict,
                "cost_usd": result["cost_usd"],
                "tokens_out": result["tokens_out"],
                "wall_s": result["wall_s"],
            }
        )

    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    total_cost = sum(s.get("cost_usd", 0) or 0 for s in summary)
    log.info(
        "Done. %d agents reviewed. Total cost $%.4f. Summary -> %s",
        len(summary),
        total_cost,
        summary_path,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
