"""Multi-turn conversational queries against LLMs.

Sends an initial prompt followed by followup questions in a single
conversation, collecting the full exchange for evaluation.

Usage:
    python -m aedist.query_multiturn \
        --prompt prompts/prompt_extract.txt \
        --followups prompts/prompt_followups.txt \
        --models models.yaml \
        --output outputs/direct_multiturn/ \
        --repeat 3 --budget-usd 5
"""

import argparse
import logging
from datetime import date
from pathlib import Path

import openai

from .harness import (
    CONTEXT_WINDOW_SAFETY_MARGIN,
    BudgetTracker,
    build_api_kwargs,
    compute_cost,
    estimate_messages_tokens,
    load_experiments,
    load_models,
    make_client,
    make_client_for_route,
    model_metadata,
    output_path,
    query_ollama_native,
    query_single_turn,
    save_json,
    select_models,
    should_skip,
)

log = logging.getLogger(__name__)


def _check_context(messages: list[dict], model: dict, turn: int) -> bool:
    """Return True if estimated tokens fit within model context window."""

    ctx_window = model.get("context_window", 0)
    if not ctx_window:
        return True
    est = estimate_messages_tokens(messages)
    limit = int(ctx_window * CONTEXT_WINDOW_SAFETY_MARGIN)
    if est > limit:
        log.warning(
            "Context overflow: ~%d tokens > %d (80%% of %d). Stopping at turn %d.",
            est,
            limit,
            ctx_window,
            turn,
        )
        return False
    return True


def run_conversation(
    client,
    model_id: str,
    prompt: str,
    followups: list[str],
    model: dict,
    budget: BudgetTracker,
    stateless: bool = False,
    ollama_base_url: str | None = None,
    no_think: bool = False,
    **api_kwargs,
) -> dict | None:
    """Run a multi-turn conversation. Returns record dict or None if budget exceeded."""
    is_ollama = model.get("route") == "ollama"
    num_ctx = min(model.get("context_window", 32768), 81920) if is_ollama else None
    ollama_url = ollama_base_url or "http://localhost:11434/v1"

    def _call(msgs):
        if is_ollama:
            return query_ollama_native(ollama_url, model_id, msgs, num_ctx, no_think=no_think)
        return query_single_turn(client, model_id, msgs, **api_kwargs)

    messages: list[dict] = []
    turns: list[dict] = []
    total_cost = 0.0
    total_wall = 0.0
    context_overflow = False

    # Initial prompt
    messages.append({"role": "user", "content": prompt})
    turns.append({"role": "user", "content": prompt, "turn": 0})

    if not budget.check_or_warn():
        return None

    if not _check_context(messages, model, 0):
        return {
            "turns": turns,
            "total_cost_usd": 0.0,
            "total_wall_seconds": 0.0,
            "context_overflow": True,
        }

    result = _call(messages)
    usage = result.get("usage") or {}
    cost = compute_cost(usage, model)
    budget.add(cost)
    total_cost += cost
    total_wall += result["wall_seconds"]

    messages.append({"role": "assistant", "content": result["content"]})
    turns.append(
        {
            "role": "assistant",
            "content": result["content"],
            "thinking": result.get("thinking", ""),
            "turn": 0,
            "wall_seconds": result["wall_seconds"],
            "usage": usage,
            "cost_usd": cost,
        }
    )

    # Followups
    for i, followup in enumerate(followups, start=1):
        if not budget.check_or_warn():
            break

        if stateless:
            messages = [{"role": "user", "content": prompt + "\n\n" + followup}]
        else:
            messages.append({"role": "user", "content": followup})

        turns.append({"role": "user", "content": followup, "turn": i})

        if not _check_context(messages, model, i):
            context_overflow = True
            break

        result = _call(messages)
        usage = result.get("usage") or {}
        cost = compute_cost(usage, model)
        budget.add(cost)
        total_cost += cost
        total_wall += result["wall_seconds"]

        messages.append({"role": "assistant", "content": result["content"]})
        turns.append(
            {
                "role": "assistant",
                "content": result["content"],
                "thinking": result.get("thinking", ""),
                "turn": i,
                "wall_seconds": result["wall_seconds"],
                "usage": usage,
                "cost_usd": cost,
            }
        )

    return {
        "turns": turns,
        "total_cost_usd": total_cost,
        "total_wall_seconds": total_wall,
        "context_overflow": context_overflow,
    }


def main():
    parser = argparse.ArgumentParser(description="Multi-turn LLM queries via OpenRouter")
    parser.add_argument("--prompt", required=True, help="Path to initial prompt text file")
    parser.add_argument("--followups", required=True, help="Path to followups file (one per line)")
    parser.add_argument("--models-registry", required=True, help="Path to models.yaml")
    parser.add_argument("--output", required=True, help="Output directory for results")
    parser.add_argument("--model", help="Query only this model (OpenRouter ID)")
    parser.add_argument("--repeat", type=int, default=1, help="Number of runs per model")
    parser.add_argument(
        "--budget-usd", type=float, default=None, help="Stop if cumulative cost exceeds budget"
    )
    parser.add_argument(
        "--stateless",
        action="store_true",
        help="Stateless batch mode: each followup sent independently (no accumulated history)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature (default 0.0)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="List what would be queried, don't call API"
    )
    parser.add_argument(
        "--no-think", action="store_true", help="Disable reasoning (Qwen3/thinking models)"
    )
    parser.add_argument("--model-set", default=None, help="Model set name from experiments.toml")
    parser.add_argument(
        "--experiments", default="experiments.toml", help="Path to experiments.toml"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    prompt = Path(args.prompt).read_text().strip()
    followups = [
        line.strip() for line in Path(args.followups).read_text().splitlines() if line.strip()
    ]
    models = load_models(args.models_registry)
    output_dir = Path(args.output)

    if args.model_set:
        experiments = load_experiments(args.experiments)
        set_ids = experiments["sets"][args.model_set]["model_ids"]
        models = select_models(models, set_ids)

    if args.model:
        models = [m for m in models if m["name"] == args.model]
        if not models:
            raise SystemExit(f"Model {args.model} not found in {args.models_registry}")

    if args.dry_run:
        for model in models:
            for run in range(1, args.repeat + 1):
                log.info(
                    "Would query %s run %d (%d turns)", model["name"], run, 1 + len(followups)
                )
        return

    legacy_client = None
    if args.model_set:
        clients: dict = {}
    else:
        legacy_client = make_client()
    budget = BudgetTracker(args.budget_usd)

    for model in models:
        model_id = model["name"]
        label = model.get("display_name", model_id)

        route = model.get("route")
        if args.model_set and route:
            if route not in clients:
                clients[route] = make_client_for_route(model)
            client = clients[route]
        else:
            if legacy_client is None:
                raise SystemExit(
                    f"{model_id}: no route field and no legacy client (use --base-url or add route to registry)"
                )
            client = legacy_client

        for run in range(1, args.repeat + 1):
            if not budget.check_or_warn():
                return

            if should_skip(output_dir, model_id, run):
                log.info("Skip %s run %d (cached)", label, run)
                continue

            log.info(
                "Querying %s run %d/%d (multiturn, %d followups)...",
                label,
                run,
                args.repeat,
                len(followups),
            )

            try:
                api_model_id = model.get("model_id", model_id)
                mt_api_kwargs = build_api_kwargs(
                    model,
                    temperature=args.temperature,
                    no_think=args.no_think,
                )
                ollama_base_url = model.get("base_url") if model.get("route") == "ollama" else None
                conv = run_conversation(
                    client,
                    api_model_id,
                    prompt,
                    followups,
                    model,
                    budget,
                    stateless=args.stateless,
                    ollama_base_url=ollama_base_url,
                    no_think=args.no_think,
                    **mt_api_kwargs,
                )
                if conv is None:
                    return

                filepath = output_path(output_dir, model_id, run)
                record = {
                    "model": model_id,
                    "run": run,
                    "date": date.today().isoformat(),
                    "prompt_file": args.prompt,
                    "followups_file": args.followups,
                    "temperature": args.temperature,
                    "model_metadata": model_metadata(model),
                    **conv,
                }
                save_json(filepath, record)
                log.info(
                    "  Done. cost=%.6f total=%.6f USD", conv["total_cost_usd"], budget.total_cost
                )
            except openai.APIError as e:
                log.error("Error querying %s run %d: %s", label, run, e)

    log.info("Completed. Total cost: %.6f USD", budget.total_cost)


if __name__ == "__main__":
    main()
