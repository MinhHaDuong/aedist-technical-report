"""Multi-turn conversational queries against LLMs.

Sends an initial prompt followed by followup questions in a single
conversation, collecting the full exchange for evaluation.

Usage:
    python -m aedist.query_multiturn \
        --prompt prompts/prompt_structured.txt \
        --followups prompts/followups.txt \
        --models models.yaml \
        --output outputs/sweep2_multiturn/ \
        --repeat 3 --budget-usd 5
"""

import argparse
import logging
from datetime import date
from pathlib import Path

from .harness import (
    BudgetTracker,
    compute_cost,
    output_path,
    load_models,
    make_client,
    model_metadata,

    query_single_turn,
    save_json,
    should_skip,
)

log = logging.getLogger(__name__)


def run_conversation(
    client,
    model_id: str,
    prompt: str,
    followups: list[str],
    model: dict,
    budget: BudgetTracker,
) -> dict | None:
    """Run a multi-turn conversation. Returns record dict or None if budget exceeded."""
    messages: list[dict] = []
    turns: list[dict] = []
    total_cost = 0.0
    total_wall = 0.0

    # Initial prompt
    messages.append({"role": "user", "content": prompt})
    turns.append({"role": "user", "content": prompt, "turn": 0})

    if not budget.check_or_warn():
        return None

    result = query_single_turn(client, model_id, messages)
    usage = result.get("usage") or {}
    cost = compute_cost(usage, model)
    budget.add(cost)
    total_cost += cost
    total_wall += result["wall_seconds"]

    messages.append({"role": "assistant", "content": result["content"]})
    turns.append({
        "role": "assistant",
        "content": result["content"],
        "turn": 0,
        "wall_seconds": result["wall_seconds"],
        "usage": usage,
        "cost_usd": cost,
    })

    # Followups
    for i, followup in enumerate(followups, start=1):
        if not budget.check_or_warn():
            break

        messages.append({"role": "user", "content": followup})
        turns.append({"role": "user", "content": followup, "turn": i})

        result = query_single_turn(client, model_id, messages)
        usage = result.get("usage") or {}
        cost = compute_cost(usage, model)
        budget.add(cost)
        total_cost += cost
        total_wall += result["wall_seconds"]

        messages.append({"role": "assistant", "content": result["content"]})
        turns.append({
            "role": "assistant",
            "content": result["content"],
            "turn": i,
            "wall_seconds": result["wall_seconds"],
            "usage": usage,
            "cost_usd": cost,
        })

    return {
        "turns": turns,
        "total_cost_usd": total_cost,
        "total_wall_seconds": total_wall,
    }


def main():
    parser = argparse.ArgumentParser(description="Multi-turn LLM queries via OpenRouter")
    parser.add_argument("--prompt", required=True, help="Path to initial prompt text file")
    parser.add_argument("--followups", required=True, help="Path to followups file (one per line)")
    parser.add_argument("--models", required=True, help="Path to models.yaml")
    parser.add_argument("--output", required=True, help="Output directory for results")
    parser.add_argument("--model", help="Query only this model (OpenRouter ID)")
    parser.add_argument("--repeat", type=int, default=1, help="Number of runs per model")
    parser.add_argument("--budget-usd", type=float, default=None, help="Stop if cumulative cost exceeds budget")
    parser.add_argument("--dry-run", action="store_true", help="List what would be queried, don't call API")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    prompt = Path(args.prompt).read_text().strip()
    followups = [
        line.strip()
        for line in Path(args.followups).read_text().splitlines()
        if line.strip()
    ]
    models = load_models(args.models)
    output_dir = Path(args.output)

    if args.model:
        models = [m for m in models if m["id"] == args.model]
        if not models:
            raise SystemExit(f"Model {args.model} not found in {args.models}")

    if args.dry_run:
        for model in models:
            for run in range(1, args.repeat + 1):
                log.info("Would query %s run %d (%d turns)", model["id"], run, 1 + len(followups))
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

            log.info("Querying %s run %d/%d (multiturn, %d followups)...",
                     label, run, args.repeat, len(followups))

            try:
                conv = run_conversation(client, model_id, prompt, followups, model, budget)
                if conv is None:
                    return

                filepath = output_path(output_dir, model_id, run)
                record = {
                    "model": model_id,
                    "run": run,
                    "date": date.today().isoformat(),
                    "prompt_file": args.prompt,
                    "followups_file": args.followups,
                    "model_metadata": model_metadata(model),
                    **conv,
                }
                save_json(filepath, record)
                log.info("  Done. cost=%.6f total=%.6f USD",
                         conv["total_cost_usd"], budget.total_cost)
            except Exception as e:
                log.error("Error querying %s run %d: %s", label, run, e)

    log.info("Completed. Total cost: %.6f USD", budget.total_cost)


if __name__ == "__main__":
    main()
