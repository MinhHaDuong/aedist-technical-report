"""Query LLMs via OpenRouter (or any OpenAI-compatible endpoint) and save results.

Usage:
    python -m aedist.query --prompt prompts/prompt1.txt \
                           --models models.yaml \
                           --output outputs/direct_extract/
    python -m aedist.query --prompt prompts/prompt1.txt \
                           --models models.yaml \
                           --output outputs/direct_extract/ \
                           --model deepseek/deepseek-r1 \
                           --repeat 3 --budget-usd 5

    # Local Ollama backend:
    python -m aedist.query --prompt prompts/prompt1.txt \
                           --models models_padme.yaml \
                           --output outputs/direct_extract/ \
                           --base-url http://localhost:11434/v1 \
                           --output-prefix padme
"""

import argparse
import hashlib
import logging
from datetime import date
from pathlib import Path

import openai

from .harness import (
    BudgetTracker,
    assemble_prompt,
    build_api_kwargs,
    build_messages,
    compute_cost,
    load_experiments,
    load_models,
    make_client,
    make_client_for_route,
    model_metadata,
    output_path,
    query_single_turn,
    save_json,
    select_models,
    should_skip,
)
from .provider_health import ProviderHealth, park_cell

log = logging.getLogger(__name__)

DEFAULT_TEMPERATURE = 0.0


def main():
    parser = argparse.ArgumentParser(
        description="Query LLMs via OpenRouter or compatible endpoint"
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
    parser.add_argument("--models", required=True, help="Path to models.yaml")
    parser.add_argument("--output", required=True, help="Output directory for results")
    parser.add_argument("--model", help="Query only this model (full ID from YAML)")
    parser.add_argument("--repeat", type=int, default=1, help="Number of runs per model")
    parser.add_argument(
        "--budget-usd", type=float, default=None, help="Stop if cumulative cost exceeds budget"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=DEFAULT_TEMPERATURE,
        help=f"Sampling temperature (default {DEFAULT_TEMPERATURE})",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="List what would be queried, don't call API"
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Override API base URL (e.g. http://localhost:11434/v1 for Ollama)",
    )
    parser.add_argument(
        "--output-prefix", default="", help="Prefix for output filenames (e.g. 'padme')"
    )
    parser.add_argument("--model-set", default=None, help="Model set name from experiments.toml")
    parser.add_argument(
        "--experiments", default="experiments.toml", help="Path to experiments.toml"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.prompt_modules is not None:
        prompt = assemble_prompt(Path(args.modules_dir), args.prompt_modules)
        prompt_path: str | None = None
    else:
        prompt = Path(args.prompt).read_text().strip()
        prompt_path = args.prompt
    models = load_models(args.models)
    output_dir = Path(args.output)

    # Filter by model set from experiments.toml
    if args.model_set:
        experiments = load_experiments(args.experiments)
        set_ids = experiments["sets"][args.model_set]["model_ids"]
        models = select_models(models, set_ids)

    # Filter to single model if requested
    if args.model:
        models = [m for m in models if m["name"] == args.model]
        if not models:
            raise SystemExit(f"Model {args.model} not found in {args.models}")

    if args.dry_run:
        for model in models:
            for run in range(1, args.repeat + 1):
                log.info("Would query %s run %d", model["name"], run)
        return

    # Build client(s): per-route when using experiments.toml, else single legacy client
    legacy_client = None
    if args.model_set:
        clients: dict[str, object] = {}
    else:
        legacy_client = make_client(args.base_url)
    budget = BudgetTracker(args.budget_usd)
    prefix = args.output_prefix

    # Ticket 0074: consult provider health before dispatch so a capped
    # router parks remaining cells instead of silently degrading the
    # method x model matrix.
    health = ProviderHealth()
    sweep_id = output_dir.name or "sweep"
    # Full 64-char digest so a resume path can reliably detect prompt
    # drift; the 16-char prefix previously stored here risked collisions
    # and gave the resumer no source reference.
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    for model in models:
        model_id = model["name"]
        label = model.get("display_name", model_id)

        # Resolve client
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

        # Route key for health tracking. Falls back to the model id's
        # namespace (e.g. "deepseek") when a legacy single-client run
        # has no route field.
        router_key = route or (model_id.split("/", 1)[0] if "/" in model_id else "default")

        for run in range(1, args.repeat + 1):
            if not budget.check_or_warn():
                return

            if should_skip(output_dir, model_id, run, prefix):
                log.info("Skip %s run %d (cached)", label, run)
                continue

            if health.is_blocked(router_key, model_id):
                reason = health.block_reason(router_key, model_id) or "blocked"
                log.warning("Park %s run %d (%s)", label, run, reason)
                park_cell(
                    output_dir,
                    sweep_id=sweep_id,
                    model_id=model_id,
                    run=run,
                    prompt_hash=prompt_hash,
                    prompt_path=prompt_path,
                    reason=reason,
                )
                continue

            log.info("Querying %s run %d/%d...", label, run, args.repeat)
            try:
                api_model_id = model.get("model_id", model_id)
                api_kwargs = build_api_kwargs(
                    model,
                    temperature=args.temperature,
                )
                result = query_single_turn(
                    client,
                    api_model_id,
                    build_messages(prompt, None),
                    **api_kwargs,
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
                    "temperature": args.temperature,
                    "model_metadata": model_metadata(model),
                }
                save_json(filepath, record)
                health.record_success(router_key, model_id)
                log.info("  Done. cost=%.6f total=%.6f USD", cost, budget.total_cost)
            except openai.APIError as e:
                verdict = health.record_failure(router_key, model_id, e)
                log.error("Error querying %s run %d: %s [%s]", label, run, e, verdict)
                park_cell(
                    output_dir,
                    sweep_id=sweep_id,
                    model_id=model_id,
                    run=run,
                    prompt_hash=prompt_hash,
                    prompt_path=prompt_path,
                    reason=str(verdict),
                )

    log.info("Completed. Total cost: %.6f USD", budget.total_cost)


if __name__ == "__main__":
    main()
