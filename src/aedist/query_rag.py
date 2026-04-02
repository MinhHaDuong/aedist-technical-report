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
        --output outputs/sweep2_rag/ \
        --repeat 3
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


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English text."""
    return len(text) // 4


def main():
    parser = argparse.ArgumentParser(description="RAG queries via OpenRouter")
    parser.add_argument("--prompt", required=True, help="Path to prompt text file")
    parser.add_argument("--corpus", required=True, help="Directory containing .md corpus files")
    parser.add_argument("--strategy", default="wholesale", choices=["wholesale"],
                        help="RAG strategy (currently only 'wholesale')")
    parser.add_argument("--models", required=True, help="Path to models.yaml")
    parser.add_argument("--output", required=True, help="Output directory for results")
    parser.add_argument("--model", help="Query only this model (OpenRouter ID)")
    parser.add_argument("--repeat", type=int, default=1, help="Number of runs per model")
    parser.add_argument("--budget-usd", type=float, default=None, help="Stop if cumulative cost exceeds budget")
    parser.add_argument("--dry-run", action="store_true", help="List what would be queried, don't call API")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    prompt = Path(args.prompt).read_text().strip()
    corpus_text, corpus_files = load_corpus(Path(args.corpus))
    corpus_tokens = estimate_tokens(corpus_text)
    models = load_models(args.models)
    output_dir = Path(args.output)

    log.info("Corpus: %d files, ~%d tokens", len(corpus_files), corpus_tokens)

    if args.model:
        models = [m for m in models if m["id"] == args.model]
        if not models:
            raise SystemExit(f"Model {args.model} not found in {args.models}")

    if args.dry_run:
        for model in models:
            ctx = model.get("context_window", 0)
            fits = "OK" if corpus_tokens < ctx * 0.8 else "SKIP (too large)"
            for run in range(1, args.repeat + 1):
                log.info("Would query %s run %d [%s]", model["id"], run, fits)
        return

    client = make_client()
    budget = BudgetTracker(args.budget_usd)

    for model in models:
        model_id = model["id"]
        label = model.get("name", model_id)
        ctx_window = model.get("context_window", 0)

        # Context window guard
        if corpus_tokens > ctx_window * 0.8:
            log.warning(
                "Skip %s: corpus ~%d tokens exceeds 80%% of context window (%d)",
                label, corpus_tokens, ctx_window,
            )
            continue

        for run in range(1, args.repeat + 1):
            if not budget.check_or_warn():
                return

            if should_skip(output_dir, model_id, run):
                log.info("Skip %s run %d (cached)", label, run)
                continue

            log.info("Querying %s run %d/%d (RAG %s)...",
                     label, run, args.repeat, args.strategy)

            try:
                messages = [
                    {"role": "system", "content": corpus_text},
                    {"role": "user", "content": prompt},
                ]
                result = query_single_turn(client, model_id, messages)
                usage = result.get("usage") or {}
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
            except Exception as e:
                log.error("Error querying %s run %d: %s", label, run, e)

    log.info("Completed. Total cost: %.6f USD", budget.total_cost)


if __name__ == "__main__":
    main()
