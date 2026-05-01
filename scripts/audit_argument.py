"""Audit docs/argument.md with a panel of frontier LLMs.

Usage:
    # Pilot one model:
    python scripts/audit_argument.py --pilot
    # Full panel:
    python scripts/audit_argument.py
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from aedist.harness import make_client, query_single_turn  # noqa: E402

ARGUMENT_PATH = ROOT / "docs" / "argument.md"
OUTPUT_DIR = ROOT / "docs" / "audit-responses"

PANEL = [
    "deepseek/deepseek-v3.2",
    "openai/gpt-5.4",
    "anthropic/claude-opus-4.6",
    "google/gemini-3-flash-preview",
    "mistralai/mistral-large-2512",
    "qwen/qwen3-max-thinking",
]

AUDIT_PROMPT = """\
You are a peer reviewer for a research paper on extracting energy \
infrastructure statistics from LLMs. Below is the paper's central \
argument document. Read it carefully and respond to all four questions.

Cite specific sections or phrases from the document to ground your \
critique. Quote at least one phrase verbatim from the document for each \
point you make.

Questions:
(a) What is the strongest internal inconsistency in this argument?
(b) What is the weakest empirical claim?
(c) What is the most likely methodological objection a peer reviewer \
would raise?
(d) If you were forced to drop one claim from this argument, which \
would it be and why?

Be terse — no more than 300 words total. Structure your response as:

## (a) Strongest inconsistency
...
## (b) Weakest empirical claim
...
## (c) Most likely methodological objection
...
## (d) Claim to drop
...
"""


def run_audit(model_id: str, client, argument_text: str) -> dict:
    messages = [
        {"role": "system", "content": AUDIT_PROMPT},
        {"role": "user", "content": argument_text},
    ]
    result = query_single_turn(client, model_id, messages, temperature=0.3, max_tokens=2048)
    result["model_id"] = model_id
    result["timestamp"] = datetime.now(UTC).isoformat()
    return result


def save_result(result: dict) -> Path:
    slug = result["model_id"].replace("/", "_")
    out_json = OUTPUT_DIR / f"{slug}.json"
    out_md = OUTPUT_DIR / f"{slug}.md"
    out_json.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    header = (
        f"# Audit response: {result['model_id']}\n\n"
        f"**Date:** {result['timestamp']}\n"
        f"**Tokens:** {result['usage']['prompt_tokens']} in / "
        f"{result['usage']['completion_tokens']} out\n"
        f"**Wall time:** {result['wall_seconds']}s\n\n---\n\n"
    )
    out_md.write_text(header + (result["content"] or "(empty response)"))
    return out_md


def main():
    pilot_only = "--pilot" in sys.argv
    argument_text = ARGUMENT_PATH.read_text()
    client = make_client()

    models = [PANEL[0]] if pilot_only else PANEL
    print(f"Running audit on {len(models)} model(s): {', '.join(models)}")

    results = []
    for model_id in models:
        print(f"\n--- {model_id} ---")
        try:
            result = run_audit(model_id, client, argument_text)
            path = save_result(result)
            results.append(result)
            print(f"  OK  {result['usage']}  {result['wall_seconds']}s  → {path.name}")
            if result["content"]:
                preview = result["content"][:200].replace("\n", " ")
                print(f"  Preview: {preview}...")
        except Exception as e:
            print(f"  FAIL: {e}")
            results.append({"model_id": model_id, "error": str(e)})

    print(f"\n{'=' * 60}")
    print(f"Completed: {sum(1 for r in results if 'content' in r)}/{len(models)}")
    for r in results:
        status = "OK" if "content" in r else f"FAIL: {r.get('error', '?')}"
        print(f"  {r['model_id']}: {status}")


if __name__ == "__main__":
    main()
