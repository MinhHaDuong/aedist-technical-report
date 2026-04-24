"""Single direct LLM call, no retrieval context: comprehensive Vietnam thermal sector report.

Sends a maximally-optimized comprehensive prompt to frontier reasoning models
and captures full responses for qualitative evaluation.  Uses high max_tokens
and temperature=0 for deterministic, exhaustive output.

Usage:
    uv run python -m aedist.query_direct \
        --prompt prompts/prompt_complete.txt \
        --models models_frontier.yaml \
        --output outputs/frontier/ \
        --budget-usd 20

    # Single model:
    uv run python -m aedist.query_direct \
        --prompt prompts/prompt_complete.txt \
        --models models_frontier.yaml \
        --output outputs/frontier/ \
        --model anthropic/claude-opus-4.6
"""

import argparse
import logging
from datetime import date
from pathlib import Path

import openai

from .harness import (
    BudgetTracker,
    assemble_prompt,
    build_api_kwargs,
    compute_cost,
    load_experiments,
    load_models,
    make_client,
    make_client_for_router,
    model_metadata,
    output_path,
    query_single_turn,
    save_json,
    select_models,
    should_skip,
)

log = logging.getLogger(__name__)

# Frontier defaults: maximize quality and output length
DEFAULT_MAX_TOKENS = 32768
DEFAULT_TEMPERATURE = 0.0


def main():
    parser = argparse.ArgumentParser(
        description="Frontier deep-research benchmark for comprehensive extraction"
    )
    prompt_group = parser.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("--prompt", help="Path to prompt text file")
    prompt_group.add_argument(
        "--prompt-modules",
        nargs="*",
        default=None,
        help="Module names for assemble_prompt() (e.g. persona overview)",
    )
    parser.add_argument(
        "--modules-dir",
        default="experiments/prompts/modules",
        help="Directory containing prompt module text files",
    )
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
    parser.add_argument(
        "--no-web-search",
        action="store_true",
        help="Disable web search even if model has web_search=true",
    )
    parser.add_argument("--dry-run", action="store_true", help="List queries without calling API")
    parser.add_argument("--model-set", default=None, help="Model set name from experiments.toml")
    parser.add_argument(
        "--experiments", default="experiments.toml", help="Path to experiments.toml"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.prompt_modules is not None:
        modules_dir = Path(args.modules_dir)
        prompt = assemble_prompt(modules_dir, args.prompt_modules)
        if args.prompt_modules:
            sweep = "modules_" + "_".join(args.prompt_modules)
        else:
            sweep = "modules_base"
    else:
        prompt = Path(args.prompt).read_text().strip()
        sweep = Path(args.prompt).stem
        if sweep.startswith("prompt_"):
            sweep = sweep[len("prompt_") :]
    models = load_models(args.models)
    output_dir = Path(args.output)

    if args.model_set:
        experiments = load_experiments(args.experiments)
        set_ids = experiments["sets"][args.model_set]["model_ids"]
        models = select_models(models, set_ids)

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

    # Build client(s): per-router when using experiments.toml, else single legacy client
    legacy_client = None
    if args.model_set:
        routers_config = experiments.get("routers", {})
        clients: dict = {}
    else:
        legacy_client = make_client()
    budget = BudgetTracker(args.budget_usd)

    for model in models:
        model_id = model["id"]
        label = model.get("name", model_id)

        router = model.get("router")
        if args.model_set and router:
            if router not in clients:
                clients[router] = make_client_for_router(router, routers_config)
            client = clients[router]
        else:
            if legacy_client is None:
                raise SystemExit(
                    f"{model_id}: no router field and no legacy client (use --base-url or add router to registry)"
                )
            client = legacy_client

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
                effective_model = model
                if args.no_web_search:
                    effective_model = {**model, "web_search": False}
                api_kwargs = build_api_kwargs(
                    effective_model,
                    max_tokens=args.max_tokens,
                    temperature=args.temperature,
                )
                api_model_id = model.get("router_model", model_id)
                result = query_single_turn(
                    client,
                    api_model_id,
                    [{"role": "user", "content": prompt}],
                    **api_kwargs,
                )
                usage = result.get("usage") or {}
                cost = compute_cost(usage, model)
                budget.add(cost)

                filepath = output_path(output_dir, model_id, run)
                record = {
                    "model": model_id,
                    "date": date.today().isoformat(),
                    "run": run,
                    "sweep": sweep,
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
