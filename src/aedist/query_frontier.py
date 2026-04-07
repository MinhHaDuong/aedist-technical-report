"""Frontier deep-research benchmark: comprehensive Vietnam thermal sector report.

Sends a maximally-optimized comprehensive prompt to frontier reasoning models
and captures full responses for qualitative evaluation.  Uses high max_tokens
and temperature=0 for deterministic, exhaustive output.

Usage:
    uv run python -m aedist.query_frontier \
        --prompt prompts/prompt_frontier.txt \
        --models models_frontier.yaml \
        --output outputs/frontier/ \
        --budget-usd 20

    # Single model:
    uv run python -m aedist.query_frontier \
        --prompt prompts/prompt_frontier.txt \
        --models models_frontier.yaml \
        --output outputs/frontier/ \
        --model anthropic/claude-opus-4.6
"""

import argparse
import logging
import time
from datetime import date
from pathlib import Path

import openai

from .harness import (
    BudgetTracker,
    compute_cost,
    load_models,
    make_client,
    model_metadata,
    output_path,
    save_json,
    should_skip,
)

log = logging.getLogger(__name__)

# Frontier defaults: maximize quality and output length
DEFAULT_MAX_TOKENS = 32768
DEFAULT_TEMPERATURE = 0.0


REASONING_MODELS = {
    "openai/o3",
    "openai/o3-pro",
    "openai/o3-deep-research",
    "openai/o3-mini",
    "openai/o3-mini-high",
    "openai/o4-mini",
    "openai/o4-mini-high",
    "openai/o4-mini-deep-research",
}


def query_frontier(
    client: openai.OpenAI,
    model_id: str,
    messages: list[dict],
    *,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
) -> dict:
    """Send messages with frontier-optimized parameters.

    Higher max_tokens than standard queries to allow comprehensive
    multi-section reports.  Temperature 0 for deterministic output.
    Reasoning models (o3/o4 family) don't accept temperature.
    """
    kwargs: dict = {"model": model_id, "messages": messages, "max_tokens": max_tokens}
    if model_id not in REASONING_MODELS:
        kwargs["temperature"] = temperature
    t0 = time.monotonic()
    response = client.chat.completions.create(**kwargs)
    wall_seconds = round(time.monotonic() - t0, 3)
    choice = response.choices[0]
    usage = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
    }
    return {
        "content": choice.message.content,
        "finish_reason": choice.finish_reason,
        "usage": usage,
        "wall_seconds": wall_seconds,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Frontier deep-research benchmark for comprehensive extraction"
    )
    parser.add_argument("--prompt", required=True, help="Path to prompt text file")
    parser.add_argument("--models", required=True, help="Path to models YAML")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--model", help="Query only this model (full ID)")
    parser.add_argument("--repeat", type=int, default=1, help="Runs per model")
    parser.add_argument("--budget-usd", type=float, default=20.0, help="Budget cap (USD)")
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help=f"Max output tokens (default {DEFAULT_MAX_TOKENS})",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=DEFAULT_TEMPERATURE,
        help=f"Sampling temperature (default {DEFAULT_TEMPERATURE})",
    )
    parser.add_argument("--dry-run", action="store_true", help="List queries without calling API")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    prompt = Path(args.prompt).read_text().strip()
    models = load_models(args.models)
    output_dir = Path(args.output)

    if args.model:
        models = [m for m in models if m["id"] == args.model]
        if not models:
            raise SystemExit(f"Model {args.model} not found in {args.models}")

    # Estimate cost ceiling
    prompt_tokens_est = len(prompt) // 4
    for model in models:
        est_cost_in = prompt_tokens_est * model.get("price_per_mtok_in", 0) / 1_000_000
        est_cost_out = args.max_tokens * model.get("price_per_mtok_out", 0) / 1_000_000
        est_total = (est_cost_in + est_cost_out) * args.repeat
        log.info(
            "  %s: ~%d prompt tokens, max %d output → est $%.4f/run, $%.4f total",
            model.get("name", model["id"]),
            prompt_tokens_est,
            args.max_tokens,
            est_cost_in + est_cost_out,
            est_total,
        )

    if args.dry_run:
        log.info("Dry run — no API calls made.")
        return

    client = make_client()
    budget = BudgetTracker(args.budget_usd)

    for model in models:
        model_id = model["id"]
        label = model.get("name", model_id)

        for run in range(1, args.repeat + 1):
            if not budget.check_or_warn():
                return

            if should_skip(output_dir, model_id, run):
                log.info("Skip %s run %d (cached)", label, run)
                continue

            log.info(
                "Querying %s run %d/%d (frontier, max_tokens=%d, temp=%.1f)...",
                label,
                run,
                args.repeat,
                args.max_tokens,
                args.temperature,
            )

            try:
                result = query_frontier(
                    client,
                    model_id,
                    [{"role": "user", "content": prompt}],
                    max_tokens=args.max_tokens,
                    temperature=args.temperature,
                )
                usage = result.get("usage") or {}
                cost = compute_cost(usage, model)
                budget.add(cost)

                filepath = output_path(output_dir, model_id, run)
                record = {
                    "model": model_id,
                    "date": date.today().isoformat(),
                    "run": run,
                    "sweep": "frontier",
                    "prompt": prompt,
                    "response": result["content"],
                    "finish_reason": result["finish_reason"],
                    "usage": usage,
                    "wall_seconds": result["wall_seconds"],
                    "cost_usd": cost,
                    "max_tokens": args.max_tokens,
                    "temperature": args.temperature,
                    "model_metadata": model_metadata(model),
                }
                save_json(filepath, record)

                # Report
                tok_in = usage.get("prompt_tokens", 0)
                tok_out = usage.get("completion_tokens", 0)
                log.info(
                    "  %s run %d: %d→%d tokens, %.1fs, $%.4f (total $%.4f) finish=%s",
                    label,
                    run,
                    tok_in,
                    tok_out,
                    result["wall_seconds"],
                    cost,
                    budget.total_cost,
                    result["finish_reason"],
                )
            except openai.APIError as e:
                log.error("Error querying %s run %d: %s", label, run, e)

    log.info("Frontier benchmark complete. Total cost: $%.4f", budget.total_cost)


if __name__ == "__main__":
    main()
