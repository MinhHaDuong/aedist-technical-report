"""Serial qwen3.6-flash topup with rate-limit-aware pauses.

The free-tier upstream rate-limits aggressively (often 429 within seconds
of a previous call). The drain worker exits on 429, so we bypass it and
call smoke_one directly with explicit pauses between attempts.
"""

import argparse
import logging
import sys
import time
from pathlib import Path

from aedist.harness import (
    assemble_prompt,
    build_api_kwargs,
    build_messages,
    make_client,
)
from aedist.smoke import _resolve_model_entry, smoke_one


def main(argv=None):
    parser = argparse.ArgumentParser(prog="qflash_topup")
    parser.add_argument("--model", default="qwen/qwen3.6-flash")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--runs", default="1,2,3", help="Comma-separated run numbers to produce")
    parser.add_argument("--pause", type=int, default=120, help="Seconds between attempts")
    parser.add_argument("--retry-pause", type=int, default=300, help="Seconds after a 429")
    parser.add_argument("--max-retries", type=int, default=3)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    log = logging.getLogger(__name__)

    model_entry = _resolve_model_entry(args.model, Path("models.yaml"))
    if model_entry is None:
        sys.exit(f"Model {args.model} not in registry")

    prompt = assemble_prompt(Path("prompts/modules"), [])
    system_instruction = (
        "You have no web search capability. Do not claim to perform searches, "
        "do not invoke tools, do not fabricate URLs. Answer from parametric knowledge only."
    )
    messages = build_messages(prompt, system_instruction=system_instruction)
    api_kwargs = build_api_kwargs(
        model_entry,
        temperature=0.0,
        max_tokens=32768,
        seed=42,
    )
    api_kwargs["timeout"] = 600

    client = make_client()
    args.output.mkdir(parents=True, exist_ok=True)

    runs = [int(x) for x in args.runs.split(",")]
    for run in runs:
        out_file = args.output / f"{args.model.split('/')[-1]}-run{run}.json"
        if out_file.exists():
            log.info("Skip run %d (exists: %s)", run, out_file)
            continue

        attempt = 0
        while attempt < args.max_retries:
            attempt += 1
            log.info("=== run %d attempt %d ===", run, attempt)
            try:
                smoke_one(
                    client,
                    model_entry,
                    messages,
                    api_kwargs,
                    run,
                    args.output,
                    promote_as_production=True,
                )
                log.info("Saved run %d", run)
                break
            except Exception as exc:
                msg = str(exc)
                if "429" in msg:
                    log.warning(
                        "Run %d attempt %d 429; sleeping %ds", run, attempt, args.retry_pause
                    )
                    time.sleep(args.retry_pause)
                else:
                    log.error("Run %d attempt %d failed: %s", run, attempt, msg[:200])
                    time.sleep(args.pause)

        # Pause before next run regardless
        if run != runs[-1]:
            log.info("Sleeping %ds before next run", args.pause)
            time.sleep(args.pause)


if __name__ == "__main__":
    main()
