"""3 sub-calls split by fuel type, results merged: task decomposition query pipeline.

Instead of asking for all thermal power plants in one query (which causes
truncation), split into 3 sub-queries by fuel type:
  1. Coal-fired plants
  2. Gas and LNG plants
  3. Oil and other thermal plants

Each sub-query gets the same RAG corpus. The 3 CSV responses are extracted
and merged into a single consolidated CSV.

Usage:
    python -m aedist.query_per_fuel \
        --prompt prompts/prompt_extract.txt \
        --corpus data/rag_corpus/ \
        --models models_selected.yaml \
        --output outputs/decomposed/ \
        --repeat 3 --budget-usd 2
"""

import argparse
import csv
import io
import logging
from datetime import date
from pathlib import Path

import openai

from .extract import (
    extract_fenced_blocks,
    fallback_extract_inline_csv,
    parse_and_canonicalize,
    score_csv_like_block,
)
from .harness import (
    BudgetTracker,
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
from .query_rag import CONTEXT_WINDOW_SAFETY_MARGIN, estimate_tokens, load_corpus

log = logging.getLogger(__name__)

# Sub-prompts for each fuel category.
# Ticket 0068: removed "be absolutely exhaustive — include ... cancelled plants"
# instruction, which invited parametric-memory fallback and 40–52% FP rates.
# Added explicit grounding clause.
_FUEL_PROMPTS = {
    "coal": (
        "Based only on the provided documents, list the COAL-FIRED thermal power "
        "plants in Vietnam, including their fuel type (coal), construction stage, "
        "connection date (observed or planned COD), province, and generation "
        "capacity (in MWe). Do not include plants that are not mentioned in the "
        "documents. Format the response in CSV."
    ),
    "gas": (
        "Based only on the provided documents, list the GAS and LNG thermal power "
        "plants in Vietnam, including their fuel type (local natural gas / imported "
        "LNG), construction stage, connection date (observed or planned COD), "
        "province, and generation capacity (in MWe). Do not include plants that are "
        "not mentioned in the documents. Format the response in CSV."
    ),
    "other": (
        "Based only on the provided documents, list the OIL-FIRED and OTHER thermal "
        "power plants in Vietnam (excluding coal, gas, and LNG — include oil, diesel, "
        "biomass, co-generation), with their fuel type, construction stage, connection "
        "date (observed or planned COD), province, and generation capacity (in MWe). "
        "Do not include plants that are not mentioned in the documents. Format the "
        "response in CSV."
    ),
}


def extract_csv_text(response: str | None) -> str | None:
    """Extract and canonicalize CSV from a model response."""
    if not response:
        return None
    blocks = extract_fenced_blocks(response)
    if not blocks:
        inline = fallback_extract_inline_csv(response)
        if inline:
            blocks = [inline]
    if not blocks:
        return None

    best = max(blocks, key=score_csv_like_block)
    try:
        return parse_and_canonicalize(best)
    except Exception as e:
        log.warning("CSV parse failed: %s", e)
        return None


def merge_csvs(csv_texts: list[str]) -> str:
    """Merge multiple canonical CSVs, deduplicating by name."""
    seen_names: set[str] = set()
    merged_rows: list[list[str]] = []
    header: list[str] | None = None

    for csv_text in csv_texts:
        reader = csv.reader(io.StringIO(csv_text.strip()))
        rows = list(reader)
        if not rows:
            continue
        if header is None:
            header = rows[0]
        for row in rows[1:]:
            if not row or not row[0].strip():
                continue
            name_key = row[0].strip().lower()
            if name_key not in seen_names:
                seen_names.add(name_key)
                merged_rows.append(row)

    if header is None:
        return ""

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    for row in merged_rows:
        writer.writerow(row)
    return buf.getvalue()


def query_decomposed(
    client,
    model_id: str,
    corpus_text: str,
    budget: BudgetTracker,
    model: dict,
    **api_kwargs,
) -> dict | None:
    """Run 3 sub-queries and merge results. Returns record dict or None."""
    sub_results = {}
    total_cost = 0.0
    total_wall = 0.0
    all_usage = {"prompt_tokens": 0, "completion_tokens": 0}

    for fuel, fuel_prompt in _FUEL_PROMPTS.items():
        if not budget.check_or_warn():
            return None

        messages = [
            {"role": "system", "content": corpus_text},
            {"role": "user", "content": fuel_prompt},
        ]

        try:
            result = query_single_turn(client, model_id, messages, **api_kwargs)
        except openai.APIError as e:
            log.error("  Error on %s sub-query: %s", fuel, e)
            return None

        usage = result.get("usage") or {}
        cost = compute_cost(usage, model)
        budget.add(cost)
        total_cost += cost
        total_wall += result["wall_seconds"]
        all_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
        all_usage["completion_tokens"] += usage.get("completion_tokens", 0)

        sub_results[fuel] = {
            "prompt": fuel_prompt,
            "response": result["content"],
            "finish_reason": result["finish_reason"],
            "usage": usage,
            "cost_usd": cost,
            "wall_seconds": result["wall_seconds"],
        }
        log.info("    %s: %d tokens, $%.6f", fuel, usage.get("completion_tokens", 0), cost)

    # Merge CSV outputs
    csv_texts = []
    for fuel in _FUEL_PROMPTS:
        csv_text = extract_csv_text(sub_results[fuel]["response"])
        if csv_text:
            csv_texts.append(csv_text)
            lines = csv_text.strip().split("\n")
            log.info("    %s: extracted %d rows", fuel, len(lines) - 1)
        else:
            log.warning("    %s: no CSV extracted", fuel)

    merged_csv = merge_csvs(csv_texts) if csv_texts else ""
    merged_lines = merged_csv.strip().split("\n") if merged_csv else []
    n_merged = len(merged_lines) - 1 if len(merged_lines) > 1 else 0
    log.info("  Merged: %d unique plants from %d sub-queries", n_merged, len(csv_texts))

    return {
        "strategy": "decomposed",
        "sub_queries": sub_results,
        "merged_csv": merged_csv,
        "n_merged_plants": n_merged,
        "total_cost_usd": total_cost,
        "total_wall_seconds": round(total_wall, 3),
        "total_usage": all_usage,
    }


def main():
    parser = argparse.ArgumentParser(description="Decomposed RAG queries by fuel type")
    parser.add_argument("--prompt", required=True, help="Path to base prompt (for reference)")
    parser.add_argument("--corpus", required=True, help="Directory with .md corpus files")
    parser.add_argument("--models", required=True, help="Path to models.yaml")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--model", help="Query only this model (OpenRouter ID)")
    parser.add_argument("--repeat", type=int, default=1, help="Number of runs per model")
    parser.add_argument("--budget-usd", type=float, default=None, help="Budget cap in USD")
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature (default 0.0)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would run")
    parser.add_argument("--model-set", default=None, help="Model set name from experiments.toml")
    parser.add_argument(
        "--experiments", default="experiments.toml", help="Path to experiments.toml"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    base_prompt = Path(args.prompt).read_text().strip()
    corpus_text, corpus_files = load_corpus(Path(args.corpus))
    corpus_tokens = estimate_tokens(corpus_text)
    models = load_models(args.models)
    output_dir = Path(args.output)

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
            for run in range(1, args.repeat + 1):
                log.info("Would query %s run %d (3 sub-queries)", model["id"], run)
        return

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
        ctx_window = model.get("context_window", 0)

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

        if corpus_tokens > ctx_window * CONTEXT_WINDOW_SAFETY_MARGIN:
            log.warning("Skip %s: corpus too large for context window", label)
            continue

        for run in range(1, args.repeat + 1):
            if not budget.check_or_warn():
                return

            if should_skip(output_dir, model_id, run):
                log.info("Skip %s run %d (cached)", label, run)
                continue

            log.info("Querying %s run %d/%d (decomposed RAG)...", label, run, args.repeat)

            api_model_id = model.get("router_model", model_id)
            dec_api_kwargs = build_api_kwargs(
                model,
                temperature=args.temperature,
            )
            decomposed = query_decomposed(
                client,
                api_model_id,
                corpus_text,
                budget,
                model,
                **dec_api_kwargs,
            )

            if decomposed is None:
                continue

            filepath = output_path(output_dir, model_id, run)
            record = {
                "model": model_id,
                "run": run,
                "date": date.today().isoformat(),
                "strategy": "decomposed",
                "corpus_files": corpus_files,
                "corpus_tokens": corpus_tokens,
                "prompt": base_prompt,
                "response": decomposed["merged_csv"],
                "finish_reason": "merged",
                "usage": decomposed["total_usage"],
                "wall_seconds": decomposed["total_wall_seconds"],
                "cost_usd": decomposed["total_cost_usd"],
                "temperature": args.temperature,
                "model_metadata": model_metadata(model),
                "decomposition": {
                    fuel: {
                        "prompt": sub["prompt"],
                        "response": sub["response"],
                        "finish_reason": sub["finish_reason"],
                        "usage": sub["usage"],
                        "cost_usd": sub["cost_usd"],
                    }
                    for fuel, sub in decomposed["sub_queries"].items()
                },
                "n_merged_plants": decomposed["n_merged_plants"],
            }
            save_json(filepath, record)
            log.info(
                "  Done. %d plants, $%.6f total=$%.6f",
                decomposed["n_merged_plants"],
                decomposed["total_cost_usd"],
                budget.total_cost,
            )

    log.info("Completed. Total cost: $%.6f", budget.total_cost)


if __name__ == "__main__":
    main()
