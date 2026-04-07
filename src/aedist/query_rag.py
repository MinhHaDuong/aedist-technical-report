"""RAG (Retrieval-Augmented Generation) queries against LLMs.

Wholesale strategy: concatenate all corpus documents as system context,
then send the prompt as user message. Checks corpus size against model
context window before querying.

Usage:
    python -m aedist.query_rag \
        --prompt prompts/prompt_structured.txt \
        --corpus data/rag_corpus/ \
        --strategy wholesale \
        --models models.yaml \
        --output outputs/sweep_rag/ \
        --repeat 3
"""

import argparse
import logging
from datetime import date
from pathlib import Path

import openai

from .harness import (
    CONTEXT_WINDOW_SAFETY_MARGIN,
    BudgetTracker,
    compute_cost,
    estimate_tokens,
    load_experiments,
    load_models,
    make_client,
    make_client_for_router,
    model_metadata,
    output_path,
    query_ollama_native,
    query_single_turn,
    save_json,
    select_models,
    should_skip,
)

log = logging.getLogger(__name__)


def load_corpus(corpus_dir: Path) -> tuple[str, list[str]]:
    """Load all .md files from corpus directory, return (text, filenames)."""
    files = sorted(corpus_dir.glob("*.md"))
    if not files:
        raise SystemExit(f"No .md files found in {corpus_dir}")

    parts = []
    names = []
    for f in files:
        parts.append(f.read_text().strip())
        names.append(f.name)

    return "\n---\n".join(parts), names


def main():
    parser = argparse.ArgumentParser(description="RAG queries via OpenRouter")
    parser.add_argument("--prompt", required=True, help="Path to prompt text file")
    parser.add_argument("--corpus", required=True, help="Directory containing .md corpus files")
    parser.add_argument(
        "--strategy",
        default="wholesale",
        choices=["wholesale"],
        help="RAG strategy (currently only 'wholesale')",
    )
    parser.add_argument("--models", required=True, help="Path to models.yaml")
    parser.add_argument("--output", required=True, help="Output directory for results")
    parser.add_argument("--model", help="Query only this model (OpenRouter ID)")
    parser.add_argument("--repeat", type=int, default=1, help="Number of runs per model")
    parser.add_argument(
        "--budget-usd", type=float, default=None, help="Stop if cumulative cost exceeds budget"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="List what would be queried, don't call API"
    )
    parser.add_argument("--model-set", default=None, help="Model set name from experiments.toml")
    parser.add_argument("--experiments", default="experiments.toml", help="Path to experiments.toml")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    prompt = Path(args.prompt).read_text().strip()
    corpus_text, corpus_files = load_corpus(Path(args.corpus))
    corpus_tokens = estimate_tokens(corpus_text)
    models = load_models(args.models)
    output_dir = Path(args.output)

    # Filter by model set from experiments.toml
    experiments = None
    if args.model_set:
        experiments = load_experiments(args.experiments)
        set_ids = experiments["sets"][args.model_set]["model_ids"]
        models = select_models(models, set_ids)

    log.info("Corpus: %d files, ~%d tokens", len(corpus_files), corpus_tokens)

    if args.model:
        models = [m for m in models if m["id"] == args.model]
        if not models:
            raise SystemExit(f"Model {args.model} not found in {args.models}")

    if args.dry_run:
        for model in models:
            ctx = model.get("context_window", 0)
            fits = (
                "OK" if corpus_tokens < ctx * CONTEXT_WINDOW_SAFETY_MARGIN else "SKIP (too large)"
            )
            for run in range(1, args.repeat + 1):
                log.info("Would query %s run %d [%s]", model["id"], run, fits)
        return

    budget = BudgetTracker(args.budget_usd)
    routers_config = experiments.get("routers", {}) if experiments else {}
    clients: dict[str, object] = {}

    for model in models:
        model_id = model["id"]
        label = model.get("name", model_id)
        router = model.get("router")
        base_url = model.get("base_url")  # legacy path
        is_ollama = router == "ollama" if router else bool(base_url)

        ctx_window = model.get("context_window", 0)

        # Context window guard
        if corpus_tokens > ctx_window * CONTEXT_WINDOW_SAFETY_MARGIN:
            log.warning(
                "Skip %s: corpus ~%d tokens exceeds 80%% of context window (%d)",
                label,
                corpus_tokens,
                ctx_window,
            )
            continue

        for run in range(1, args.repeat + 1):
            if not budget.check_or_warn():
                return

            if should_skip(output_dir, model_id, run):
                log.info("Skip %s run %d (cached)", label, run)
                continue

            # Create/switch client per router
            if router and routers_config:
                if router not in clients:
                    clients[router] = make_client_for_router(router, routers_config)
                client = clients[router]
            elif base_url:
                if base_url not in clients:
                    clients[base_url] = make_client(base_url)
                client = clients[base_url]
            else:
                if "_openrouter" not in clients:
                    clients["_openrouter"] = make_client()
                client = clients["_openrouter"]

            log.info("Querying %s run %d/%d (RAG %s)...", label, run, args.repeat, args.strategy)

            try:
                messages = [
                    {"role": "system", "content": corpus_text},
                    {"role": "user", "content": prompt},
                ]
                # Use native Ollama API to set num_ctx (OpenAI /v1/ ignores it)
                # Size to actual need, not model max — saves KV cache VRAM
                # router_model is the ID the router expects (future-proof for Phase B)
                api_model_id = model.get("router_model", model_id)
                if is_ollama:
                    ollama_cfg = routers_config.get("ollama", {})
                    ollama_url = (
                        ollama_cfg.get("base_url")
                        or base_url
                        or "http://localhost:11434/v1"
                    )
                    num_ctx = min(ctx_window, 81920)
                    result = query_ollama_native(
                        ollama_url, api_model_id, messages, num_ctx,
                    )
                else:
                    result = query_single_turn(client, api_model_id, messages)
                usage = result.get("usage") or {}

                # Truncation guard: prompt should not fill entire context
                prompt_tokens = usage.get("prompt_tokens", 0)
                if prompt_tokens and prompt_tokens >= ctx_window:
                    log.error(
                        "TRUNCATED: %s run %d prompt_tokens=%d >= ctx_window=%d",
                        label, run, prompt_tokens, ctx_window,
                    )
                    continue

                cost = compute_cost(usage, model)
                budget.add(cost)

                filepath = output_path(output_dir, model_id, run)
                record = {
                    "model": model_id,
                    "run": run,
                    "date": date.today().isoformat(),
                    "strategy": args.strategy,
                    "corpus_files": corpus_files,
                    "corpus_tokens": corpus_tokens,
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
