"""One-off smoke probe for a model against the locked Experiment 1 prompt.

Used to verify a model's behaviour (finish_reason, cost, wall time, token
distribution) before adding it to the journal model set, or to diagnose
issues observed in a production sweep.

Smoke calls are billed by OpenRouter but do NOT carry job-board provenance.
They are diagnostic, not production data. The saved JSON has the same
shape as a production record so the smoke output can be inspected with
the usual tools, but a smoke record should never be treated as one of
the configured `repeat` reps for a journal-set model.

Usage:
    uv run --project .. --env-file ../.env python -m aedist.smoke \\
        --model qwen/qwen3.6-flash \\
        --calls 2 \\
        --output outputs/smoke/

By default, --output defaults to /tmp/aedist-smoke (non-tracked); pass an
explicit path under outputs/ to keep the records.

Per-call output filenames:
    {output_dir}/{model_slug}-smoke{N}.json

Schema mirrors the worker's _query_and_save record shape so
`make rebuild-measurements` would in principle pick them up if pointed at
the smoke directory. The recommended practice is to inspect smoke records
manually and exclude them from any measurements.jsonl build.

Configuration mirrors `sweep_ablation_p1_direct_base` in experiments.toml
unless overridden via CLI flags:
    prompt_modules = []           (-> 2_goal + 5_table always-pair)
    temperature    = 0.0
    seed           = 42
    max_tokens     = 32768
    system_instruction = "You have no web search capability. ..."
"""

import argparse
import json
import logging
import sys
import time
from datetime import date
from pathlib import Path

from .harness import (
    assemble_prompt,
    build_api_kwargs,
    build_messages,
    compute_cost,
    load_models,
    make_client,
    model_metadata,
    query_single_turn,
)

log = logging.getLogger(__name__)

DEFAULT_SYSTEM_INSTRUCTION = (
    "You have no web search capability. Do not claim to perform searches, "
    "do not invoke tools, do not fabricate URLs. Answer from parametric knowledge only."
)


def _resolve_model_entry(model_id: str, models_file: Path) -> dict:
    """Find the registry entry for *model_id* in *models_file*, or
    construct a minimal stub if the entry doesn't exist (allows smoking
    a model that hasn't been added to the registry yet)."""
    if models_file.exists():
        models = load_models(str(models_file))
        for m in models:
            if m.get("name") == model_id or m.get("model_id") == model_id:
                return m
    log.warning(
        "Model %s not in registry %s; using stub entry. Cost may be uncomputed.",
        model_id,
        models_file,
    )
    return {
        "name": model_id,
        "model_id": model_id,
        "display_name": model_id,
        "provider": "unknown",
        "country": "unknown",
        "architecture": "unknown",
        "context_window": None,
        "price_per_mtok_in": None,
        "price_per_mtok_out": None,
        "size_class": "unknown",
    }


def smoke_one(
    client,
    model_entry: dict,
    messages: list[dict],
    api_kwargs: dict,
    call_number: int,
    output_dir: Path,
    *,
    promote_as_production: bool = False,
) -> dict:
    """Run a single smoke call, save the full record, return a summary dict.

    When *promote_as_production* is True, the saved file follows the worker
    naming convention ({slug}-run{N}.json) and omits the ``smoke: True``
    marker, so the record is indistinguishable from one produced by
    ``aedist.worker``. Use this only when the smoke call is intentionally
    serving as one of the configured ``repeat`` reps for a production
    sweep (e.g. to skip a redundant job-board drain for a model that has
    already passed a separate smoke check).
    """
    model_id = model_entry["name"]
    mode = "production" if promote_as_production else "smoke"
    log.info("Calling %s (%s %d) ...", model_id, mode, call_number)
    t0 = time.monotonic()
    result = query_single_turn(client, model_id, messages, **api_kwargs)
    wall = round(time.monotonic() - t0, 3)

    usage = result.get("usage") or {}
    cost = compute_cost(usage, model_entry) if model_entry.get("price_per_mtok_in") else 0.0

    record = {
        "model": model_id,
        "date": date.today().isoformat(),
        "run": call_number,
        "response": result["content"],  # FULL response, not just a tail
        "finish_reason": result["finish_reason"],
        "usage": usage,
        "wall_seconds": wall,
        "cost_usd": cost,
        "temperature": api_kwargs.get("temperature"),
        "seed": api_kwargs.get("seed"),
        "max_tokens": api_kwargs.get("max_tokens"),
        "model_metadata": model_metadata(model_entry),
        "prompt": messages[-1]["content"] if messages else "",
        "system_instruction": messages[0]["content"]
        if messages and messages[0].get("role") == "system"
        else None,
    }
    if not promote_as_production:
        # explicit marker so consumers can filter out; absent in production mode
        record["smoke"] = True

    slug = model_id.split("/")[-1].replace(":", "-")
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = "run" if promote_as_production else "smoke"
    filepath = output_dir / f"{slug}-{suffix}{call_number}.json"
    filepath.write_text(json.dumps(record, indent=2))
    log.info("Saved %s", filepath)

    return {
        "call": call_number,
        "finish_reason": record["finish_reason"],
        "completion_tokens": usage.get("completion_tokens"),
        "prompt_tokens": usage.get("prompt_tokens"),
        "wall_seconds": wall,
        "cost_usd": cost,
        "response_len_chars": len(record["response"] or ""),
        "file": str(filepath),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="aedist.smoke",
        description="One-off smoke probe for a model against the locked "
        "Experiment 1 prompt. Saves full response JSON.",
    )
    parser.add_argument(
        "--model",
        required=True,
        help="Full OpenRouter model id (e.g. qwen/qwen3.6-flash).",
    )
    parser.add_argument(
        "--calls",
        type=int,
        default=2,
        help="Number of smoke calls (default: 2).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/aedist-smoke"),
        help="Directory to write smoke JSON records "
        "(default: /tmp/aedist-smoke; use outputs/smoke/ to track).",
    )
    parser.add_argument(
        "--models-file",
        type=Path,
        default=Path("models.yaml"),
        help="Path to model registry (default: models.yaml, relative to cwd).",
    )
    parser.add_argument(
        "--modules-dir",
        type=Path,
        default=Path("prompts/modules"),
        help="Path to prompts modules (default: prompts/modules, "
        "matches Makefile cwd convention).",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature (default: 0.0).",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=32768,
        help="Max completion tokens (default: 32768, matches sweep_ablation_p1_direct_base).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="RNG seed (default: 42, matches sweep config).",
    )
    parser.add_argument(
        "--system-instruction",
        default=DEFAULT_SYSTEM_INSTRUCTION,
        help="System prompt prepended to messages (default: the locked "
        "Experiment 1 no-web-search instruction).",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=None,
        help="Optional path to write a JSON summary (one row per call). Default: stdout only.",
    )
    parser.add_argument(
        "--promote-as-production",
        action="store_true",
        help="Save records under the worker naming convention "
        "({slug}-run{N}.json) and omit the 'smoke: True' marker, so the "
        "files are indistinguishable from production worker output. Use "
        "only when the smoke calls are intentionally serving as production "
        "reps for a sweep (e.g. to skip a redundant job-board drain).",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    model_entry = _resolve_model_entry(args.model, args.models_file)
    prompt_text = assemble_prompt(args.modules_dir, [])
    messages = build_messages(prompt_text, args.system_instruction)
    api_kwargs = build_api_kwargs(
        model_entry,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        seed=args.seed,
        enable_web_search=False,
        no_think=False,
    )

    log.info("=== aedist.smoke ===")
    log.info("model: %s", args.model)
    log.info("calls: %d", args.calls)
    log.info("output: %s", args.output)
    log.info("mode: %s", "production" if args.promote_as_production else "smoke")
    log.info("api_kwargs: %s", api_kwargs)

    client = make_client()
    summaries = []
    for n in range(1, args.calls + 1):
        try:
            summary = smoke_one(
                client,
                model_entry,
                messages,
                api_kwargs,
                n,
                args.output,
                promote_as_production=args.promote_as_production,
            )
            summaries.append(summary)
        except Exception as exc:  # surfaces auth, rate-limit, timeout, etc.
            log.error("Call %d failed: %s: %s", n, type(exc).__name__, exc)
            summaries.append({"call": n, "error": f"{type(exc).__name__}: {exc}"})

    log.info("=== Summary ===")
    successes = [s for s in summaries if "error" not in s]
    log.info("calls: %d", len(summaries))
    log.info("successes: %d", len(successes))
    log.info("finish=stop: %d", sum(1 for s in successes if s["finish_reason"] == "stop"))
    log.info("finish=length: %d", sum(1 for s in successes if s["finish_reason"] == "length"))
    if successes:
        log.info("total cost: $%.5f", sum(s["cost_usd"] for s in successes))
        log.info("total wall: %.1fs", sum(s["wall_seconds"] for s in successes))

    if args.summary_output:
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_output.write_text(json.dumps(summaries, indent=2))
        log.info("Summary written to %s", args.summary_output)

    # Exit non-zero if any call errored or any call hit finish=length —
    # the smoke is gating downstream work, so failures should be visible.
    if any("error" in s for s in summaries):
        return 1
    if any(s.get("finish_reason") == "length" for s in summaries):
        log.warning(
            "At least one call hit finish_reason=length — "
            "model may need a higher max_tokens cap for production."
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
