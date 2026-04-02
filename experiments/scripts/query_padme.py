"""Query local Ollama models on Padme for sweep1 census.

Usage:
    uv run python scripts/query_padme.py \
        --prompt prompts/prompt_structured.txt \
        --output outputs/sweep1_census/ \
        --repeat 3

Requires Ollama running on padme:11434.
"""

import argparse
import json
import logging
import time
from datetime import date
from pathlib import Path

from openai import OpenAI

log = logging.getLogger(__name__)

PADME_MODELS = [
    {"id": "qwen3.5:122b", "name": "Qwen 3.5 122B (local)"},
    {"id": "qwen3.5:35b", "name": "Qwen 3.5 35B (local)"},
    {"id": "qwen3.5:27b", "name": "Qwen 3.5 27B (local)"},
    {"id": "qwen3.5:9b", "name": "Qwen 3.5 9B (local)"},
    {"id": "mistral-small3.2", "name": "Mistral Small 3.2 (local)"},
    {"id": "glm-4.7-flash", "name": "GLM 4.7 Flash (local)"},
    {"id": "nemotron-3-nano", "name": "Nemotron 3 Nano (local)"},
    {"id": "devstral-small-2", "name": "Devstral Small 2 (local)"},
]


def output_filename(model_id: str, run: int) -> str:
    short = model_id.replace(":", "-").replace("/", "-")
    return f"padme-{short}-run{run}.json"


def main():
    parser = argparse.ArgumentParser(description="Query Padme Ollama models")
    parser.add_argument("--prompt", required=True, help="Path to prompt file")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--repeat", type=int, default=3, help="Runs per model")
    parser.add_argument("--model", help="Query only this model ID")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    prompt = Path(args.prompt).read_text().strip()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    models = PADME_MODELS
    if args.model:
        models = [m for m in models if m["id"] == args.model]
        if not models:
            raise SystemExit(f"Model {args.model} not in PADME_MODELS")

    client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

    for model in models:
        model_id = model["id"]
        label = model["name"]

        for run in range(1, args.repeat + 1):
            fname = output_filename(model_id, run)
            filepath = output_dir / fname
            if filepath.exists():
                log.info("Skip %s run %d (cached)", label, run)
                continue

            log.info("Querying %s run %d/%d...", label, run, args.repeat)
            try:
                t0 = time.monotonic()
                response = client.chat.completions.create(
                    model=model_id,
                    messages=[{"role": "user", "content": prompt}],
                )
                wall_seconds = round(time.monotonic() - t0, 3)

                choice = response.choices[0]
                usage = {}
                if response.usage:
                    usage = {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                    }

                record = {
                    "model": f"padme/{model_id}",
                    "date": date.today().isoformat(),
                    "run": run,
                    "prompt": prompt,
                    "response": choice.message.content,
                    "finish_reason": choice.finish_reason,
                    "usage": usage,
                    "wall_seconds": wall_seconds,
                    "cost_usd": 0.0,
                    "model_metadata": {
                        "size_class": "local",
                        "country": "local",
                        "provider": "Ollama/Padme",
                    },
                }
                with open(filepath, "w") as f:
                    json.dump(record, f, indent=2, ensure_ascii=False)
                log.info("  Done. %.1fs", wall_seconds)

            except Exception as e:
                log.error("Error querying %s run %d: %s", label, run, e)
                record = {
                    "model": f"padme/{model_id}",
                    "date": date.today().isoformat(),
                    "run": run,
                    "prompt": prompt,
                    "response": None,
                    "finish_reason": "error",
                    "error": str(e),
                    "usage": None,
                    "wall_seconds": 0.0,
                    "cost_usd": 0.0,
                    "model_metadata": {
                        "size_class": "local",
                        "country": "local",
                        "provider": "Ollama/Padme",
                    },
                }
                with open(filepath, "w") as f:
                    json.dump(record, f, indent=2, ensure_ascii=False)

    log.info("Padme sweep complete.")


if __name__ == "__main__":
    main()
