"""Query LLMs via OpenRouter and save results.

Usage:
    python -m aedist.query --prompt prompts/prompt1.txt \
                           --models models.yaml \
                           --output outputs/sweep1/
    python -m aedist.query --prompt prompts/prompt1.txt \
                           --models models.yaml \
                           --output outputs/sweep1/ \
                           --model deepseek/deepseek-r1 \
                           --repeat 3 --budget-usd 5
"""

import argparse
import logging
from datetime import date
from pathlib import Path

from .harness import (
    BudgetTracker,
    compute_cost,
    load_models,
    make_client,
    model_metadata,
    output_path,
    query_single_turn,
    save_json,
    should_skip,
)

log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Query LLMs via OpenRouter")
    parser.add_argument("--prompt", required=True, help="Path to prompt text file")
    parser.add_argument("--models", required=True, help="Path to models.yaml")
    parser.add_argument("--output", required=True, help="Output directory for results")
    parser.add_argument("--model", help="Query only this model (OpenRouter ID)")
    parser.add_argument("--repeat", type=int, default=1, help="Number of runs per model")
    parser.add_argument("--budget-usd", type=float, default=None, help="Stop if cumulative cost exceeds budget")
    parser.add_argument("--dry-run", action="store_true", help="List what would be queried, don't call API")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    prompt = Path(args.prompt).read_text().strip()
    models = load_models(args.models)
    output_dir = Path(args.output)

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

            log.info("Querying %s run %d/%d...", label, run, args.repeat)
            try:
                result = query_single_turn(
                    client, model_id,
                    [{"role": "user", "content": prompt}],
                )
                usage = result.get("usage") or {}
                cost = compute_cost(usage, model)
                budget.add(cost)

                filepath = output_path(output_dir, model_id, run)
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
            except Exception as e:
                log.error("Error querying %s run %d: %s", label, run, e)
                filepath = output_path(output_dir, model_id, run)
                record = {
                    "model": model_id,
                    "date": date.today().isoformat(),
                    "run": run,
                    "prompt": prompt,
                    "response": None,
                    "finish_reason": "error",
                    "error": str(e),
                    "usage": None,
                    "wall_seconds": 0.0,
                    "cost_usd": 0.0,
                    "model_metadata": model_metadata(model),
                }
                save_json(filepath, record)

    log.info("Completed. Total cost: %.6f USD", budget.total_cost)


if __name__ == "__main__":
    main()
