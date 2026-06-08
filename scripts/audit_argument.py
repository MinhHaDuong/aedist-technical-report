#!/usr/bin/env python3
"""Audit the AEDIST argument with multiple frontier LLMs.

Ticket 0148: stress-test docs/argument.md against independent LLM critics.
Each model receives the full document and a structured critique prompt.
Responses are saved individually, then aggregated into docs/argument-audit.md.

Usage:
    # Test one model first (workflow rule: test before blasting)
    uv run python scripts/audit_argument.py --models deepseek/deepseek-v3.2

    # Run full panel
    uv run python scripts/audit_argument.py

    # Aggregate only (responses already saved)
    uv run python scripts/audit_argument.py --aggregate-only

WARNING: --aggregate-only overwrites the entire argument-audit.md, including
manually-authored 'Consensus clusters' and 'Disposition' sections. Back up
or git-stash before re-running if those sections have been edited.
"""

import argparse
import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from openai import OpenAI

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
ARGUMENT_PATH = ROOT / "docs" / "argument.md"
OUTPUT_DIR = ROOT / "docs" / "audit-responses"

PANEL_MODELS = [
    "anthropic/claude-opus-4.6",
    "openai/gpt-5.4",
    "google/gemini-3-flash-preview",
    "deepseek/deepseek-v3.2",
    "mistralai/mistral-large-2512",
    "qwen/qwen3-max-thinking",
    "deepseek/deepseek-r1-0528",
]

AUDIT_PROMPT = """\
You are a critical academic reviewer. Read the working note below — it is \
the central argument for a paper on using LLMs to extract energy \
infrastructure statistics from open sources.

Your task: identify weaknesses. Be terse but specific. Cite section headings \
or quote phrases from the document when making claims.

Structure your response with exactly these four markdown sections:

## (a) Strongest internal inconsistency
Identify the place where the document contradicts itself or where two claims \
cannot both be true.

## (b) Weakest empirical claim
Which specific claim has the least empirical support as stated? What evidence \
would be needed to defend it?

## (c) Most likely methodological objection from a peer reviewer
What would a reviewer in energy economics, NLP, or statistics object to first?

## (d) One claim you would drop if forced
If you had to remove one claim to make the argument tighter, which one and why?

---

THE DOCUMENT:

{document}
"""


def make_openrouter_client() -> OpenAI:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        sys.exit("Set OPENROUTER_API_KEY environment variable")
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )


def call_model(client: OpenAI, model_id: str, document: str) -> dict:
    prompt = AUDIT_PROMPT.format(document=document)
    messages = [{"role": "user", "content": prompt}]

    kwargs: dict = {
        "model": model_id,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 4096,
    }

    log.info("Calling %s ...", model_id)
    t0 = datetime.now(UTC)
    response = client.chat.completions.create(**kwargs)
    t1 = datetime.now(UTC)

    content = response.choices[0].message.content or ""
    usage = response.usage
    result = {
        "model_id": model_id,
        "timestamp": t0.isoformat(),
        "wall_seconds": (t1 - t0).total_seconds(),
        "prompt_tokens": usage.prompt_tokens if usage else None,
        "completion_tokens": usage.completion_tokens if usage else None,
        "content": content,
    }
    log.info(
        "  %s: %d tokens in %.1fs",
        model_id,
        usage.completion_tokens if usage else 0,
        result["wall_seconds"],
    )
    return result


def save_response(result: dict) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = result["model_id"].split("/")[-1].replace(":", "-")
    path = OUTPUT_DIR / f"{slug}.json"
    with open(path, "w") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    return path


def load_responses() -> list[dict]:
    responses = []
    for p in sorted(OUTPUT_DIR.glob("*.json")):
        with open(p) as f:
            responses.append(json.load(f))
    return responses


def aggregate(responses: list[dict]) -> str:
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ")
    sections = {"a": [], "b": [], "c": [], "d": []}

    for r in responses:
        model = r["model_id"]
        content = r["content"]
        for key, heading in [
            ("a", "## (a)"),
            ("b", "## (b)"),
            ("c", "## (c)"),
            ("d", "## (d)"),
        ]:
            start = content.find(heading)
            if start == -1:
                sections[key].append((model, "*Section not found in response.*"))
                continue
            end = len(content)
            for next_heading in ["## (a)", "## (b)", "## (c)", "## (d)"]:
                idx = content.find(next_heading, start + len(heading))
                if idx != -1 and idx < end:
                    end = idx
            text = content[start + len(heading) : end].strip()
            text = text.lstrip("# \n").strip()
            sections[key].append((model, text))

    lines = [
        "# Argument audit — multi-LLM critique",
        "",
        f"*Generated {now} by `scripts/audit_argument.py` (ticket 0148).*",
        "",
        "**Orchestrator:** Claude Sonnet 4.6 (claude-sonnet-4-6) via Claude Code.",
        "",
        f"**Panel:** {len(responses)} models queried via OpenRouter.",
        "",
        "| Model | Tokens | Wall time |",
        "|---|---|---|",
    ]
    for r in responses:
        tokens = r.get("completion_tokens") or "?"
        wall = f"{r.get('wall_seconds', 0):.1f}s"
        lines.append(f"| `{r['model_id']}` | {tokens} | {wall} |")

    lines += [
        "",
        "**Source document:** `docs/argument.md`",
        "",
        "**Limitation:** Models cannot follow relative links "
        "(`capability-timeline.md`) or verify cited references. "
        "This audit targets the argument's internal logic, not citation accuracy.",
        "",
    ]

    section_names = {
        "a": "Strongest internal inconsistency",
        "b": "Weakest empirical claim",
        "c": "Most likely methodological objection",
        "d": "One claim to drop if forced",
    }

    for key in ["a", "b", "c", "d"]:
        lines.append(f"## ({key}) {section_names[key]}")
        lines.append("")
        for model, text in sections[key]:
            short = model.split("/")[-1]
            lines.append(f"### {short}")
            lines.append("")
            lines.append(text)
            lines.append("")

    lines += [
        "## Consensus clusters",
        "",
        "*To be filled manually after reviewing the per-model responses above. "
        "Cluster by which claim each model contests; consensus objections go first.*",
        "",
        "## Disposition",
        "",
        "| Cluster | Objection | Action | Justification |",
        "|---|---|---|---|",
        "| | | revised / kept | |",
        "",
    ]

    return "\n".join(lines)


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Audit argument.md with LLM panel")
    parser.add_argument(
        "--models",
        nargs="+",
        default=PANEL_MODELS,
        help="Model IDs to query (default: full panel)",
    )
    parser.add_argument(
        "--aggregate-only",
        action="store_true",
        help="Skip API calls, just regenerate audit doc from saved responses",
    )
    args = parser.parse_args()

    if not args.aggregate_only:
        if not ARGUMENT_PATH.exists():
            sys.exit(f"Document not found: {ARGUMENT_PATH}")
        document = ARGUMENT_PATH.read_text()
        client = make_openrouter_client()

        for model_id in args.models:
            out_path = OUTPUT_DIR / f"{model_id.split('/')[-1].replace(':', '-')}.json"
            if out_path.exists():
                log.info("Skipping %s (response exists: %s)", model_id, out_path)
                continue
            result = call_model(client, model_id, document)
            path = save_response(result)
            log.info("  Saved: %s", path)

    responses = load_responses()
    if not responses:
        sys.exit("No responses found. Run without --aggregate-only first.")

    audit_doc = aggregate(responses)
    audit_path = ROOT / "docs" / "argument-audit.md"
    audit_path.write_text(audit_doc)
    log.info("Wrote %s (%d models)", audit_path, len(responses))


if __name__ == "__main__":
    main()
