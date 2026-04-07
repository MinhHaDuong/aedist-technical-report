"""Query LLMs via OpenRouter (or any OpenAI-compatible endpoint) and save results.

Usage:
    python -m aedist.query --prompt prompts/prompt1.txt \
                           --models models.yaml \
                           --output outputs/sweep1/
    python -m aedist.query --prompt prompts/prompt1.txt \
                           --models models.yaml \
                           --output outputs/sweep1/ \
                           --model deepseek/deepseek-r1 \
                           --repeat 3 --budget-usd 5

    # Local Ollama backend:
    python -m aedist.query --prompt prompts/prompt1.txt \
                           --models models_padme.yaml \
                           --output outputs/sweep1/ \
                           --base-url http://localhost:11434/v1 \
                           --output-prefix padme
"""

import argparse
import logging
from datetime import date
from pathlib import Path

import openai

from .harness import (
    BudgetTracker,
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


def main():
    parser = argparse.ArgumentParser(description="Query LLMs via OpenRouter or compatible endpoint")
    parser.add_argument("--prompt", required=True, help="Path to prompt text file")
    parser.add_argument("--models", required=True, help="Path to models.yaml")
    parser.add_argument("--output", required=True, help="Output directory for results")
    parser.add_argument("--model", help="Query only this model (full ID from YAML)")
    parser.add_argument("--repeat", type=int, default=1, help="Number of runs per model")
    parser.add_argument("--budget-usd", type=float, default=None, help="Stop if cumulative cost exceeds budget")
    parser.add_argument("--dry-run", action="store_true", help="List what would be queried, don't call API")
    parser.add_argument("--base-url", default=None, help="Override API base URL (e.g. http://localhost:11434/v1 for Ollama)")
    parser.add_argument("--output-prefix", default="", help="Prefix for output filenames (e.g. 'padme')")
    parser.add_argument("--model-set", default=None, help="Model set name from experiments.toml")
    parser.add_argument("--experiments", default="experiments.toml", help="Path to experiments.toml")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    prompt = Path(args.prompt).read_text().strip()
    models = load_models(args.models)
    output_dir = Path(args.output)

    # Filter by model set from experiments.toml
    if args.model_set:
        experiments = load_experiments(args.experiments)
        set_ids = experiments["sets"][args.model_set]["model_ids"]
        models = select_models(models, set_ids)

    # Filter to single model if requested
    if args.model:
        models = [m for m in models if m["id"] == args.model]
        if not models:
            raise SystemExit(f"Model {args.model} not found in {args.models}")

    if args.dry_run:
        for model in models:
            for run in range(1, args.repeat + 1):
                log.info("Would query %s run %d", model["id"], run)
        return

    # Build client(s): per-router when using experiments.toml, else single legacy client
    legacy_client = None
    if args.model_set:
        routers_config = experiments.get("routers", {})
        clients: dict[str, object] = {}
    else:
        legacy_client = make_client(args.base_url)
    budget = BudgetTracker(args.budget_usd)
    prefix = args.output_prefix

    for model in models:
        model_id = model["id"]
        label = model.get("name", model_id)

        # Resolve client
        router = model.get("router")
        if args.model_set and router:
            if router not in clients:
                clients[router] = make_client_for_router(router, routers_config)
            client = clients[router]
        else:
            if legacy_client is None:
                raise SystemExit(f"{model_id}: no router field and no legacy client (use --base-url or add router to registry)")
            client = legacy_client

        for run in range(1, args.repeat + 1):
            if not budget.check_or_warn():
                return

            if should_skip(output_dir, model_id, run, prefix):
                log.info("Skip %s run %d (cached)", label, run)
                continue

            log.info("Querying %s run %d/%d...", label, run, args.repeat)
            try:
                api_model_id = model.get("router_model", model_id)
                result = query_single_turn(
                    client, api_model_id,
                    [{"role": "user", "content": prompt}],
                )
                usage = result.get("usage") or {}
                cost = compute_cost(usage, model)
                budget.add(cost)

                filepath = output_path(output_dir, model_id, run, prefix)
                record = {
                    "model": model_id,
                    "date": date.today().isoformat(),
                    "run": run,
                    "prompt": prompt,
                    "response": result["content"],
                    "finish_reason": result["finish_reason"],
                    "usage": usage,
                    "wall_seconds": result["wall_seconds"],
                    "cost_usd": cost,
                    "model_metadata": model_metadata(model),
                }
                save_json(filepath, record)
                log.info("  Done. cost=%.6f total=%.6f USD", cost, budget.total_cost)
            except openai.APIError as e:
                log.error("Error querying %s run %d: %s", label, run, e)

    log.info("Completed. Total cost: %.6f USD", budget.total_cost)


if __name__ == "__main__":
    main()
