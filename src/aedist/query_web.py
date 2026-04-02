"""Web-augmented queries against LLMs.

Runs predefined web searches via Tavily API, injects results as context,
then sends the prompt to LLMs. Requires TAVILY_API_KEY environment variable.

Usage:
    python -m aedist.query_web \
        --prompt prompts/prompt_structured.txt \
        --models models.yaml \
        --output outputs/sweep2_web/ \
        --repeat 3
"""

import argparse
import logging
import os
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

# Predefined search queries for Vietnam thermal power plants
_SEARCH_QUERIES = [
    "Vietnam thermal power plants list coal gas LNG 2024 2025",
    "Vietnam power development plan PDP8 thermal plants capacity",
    "Vietnam LNG import terminal gas-fired power plants under construction",
]


def tavily_search(query: str, api_key: str) -> list[dict]:
    """Search via Tavily API, return list of result dicts."""
    import httpx

    resp = httpx.post(
        "https://api.tavily.com/search",
        json={
            "api_key": api_key,
            "query": query,
            "search_depth": "advanced",
            "max_results": 5,
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    data = resp.json()
    return [
        {"title": r.get("title", ""), "content": r.get("content", ""), "url": r.get("url", "")}
        for r in data.get("results", [])
    ]


def run_web_searches(api_key: str) -> tuple[str, list[dict]]:
    """Run predefined searches, return (context_text, search_log)."""
    search_log: list[dict] = []
    context_parts: list[str] = []

    for query in _SEARCH_QUERIES:
        log.info("Searching: %s", query)
        try:
            results = tavily_search(query, api_key)
            search_log.append({"query": query, "results": results})
            for r in results:
                context_parts.append(f"## {r['title']}\n{r['content']}")
        except Exception as e:
            log.error("Search failed for '%s': %s", query, e)
            search_log.append({"query": query, "error": str(e), "results": []})

    context = "\n\n---\n\n".join(context_parts)
    return context, search_log


def main():
    parser = argparse.ArgumentParser(description="Web-augmented LLM queries via OpenRouter")
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

    if args.model:
        models = [m for m in models if m["id"] == args.model]
        if not models:
            raise SystemExit(f"Model {args.model} not found in {args.models}")

    tavily_key = os.environ.get("TAVILY_API_KEY")
    if not tavily_key:
        log.warning("TAVILY_API_KEY not set. Skipping all web-augmented queries.")
        return

    if args.dry_run:
        for model in models:
            for run in range(1, args.repeat + 1):
                log.info("Would query %s run %d (web-augmented)", model["id"], run)
        return

    # Run web searches once (same context for all models/runs)
    log.info("Running %d predefined web searches...", len(_SEARCH_QUERIES))
    web_context, search_log = run_web_searches(tavily_key)

    if not web_context.strip():
        log.warning("No web search results obtained. Aborting.")
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

            log.info("Querying %s run %d/%d (web-augmented)...",
                     label, run, args.repeat)

            try:
                messages = [
                    {"role": "system", "content": (
                        "Use the following web search results as context "
                        "to answer the user's question.\n\n" + web_context
                    )},
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
                    "prompt": prompt,
                    "response": result["content"],
                    "finish_reason": result["finish_reason"],
                    "usage": usage,
                    "wall_seconds": result["wall_seconds"],
                    "cost_usd": cost,
                    "web_searches": search_log,
                    "model_metadata": model_metadata(model),
                }
                save_json(filepath, record)
                log.info("  Done. cost=%.6f total=%.6f USD", cost, budget.total_cost)
            except Exception as e:
                log.error("Error querying %s run %d: %s", label, run, e)

    log.info("Completed. Total cost: %.6f USD", budget.total_cost)


if __name__ == "__main__":
    main()
