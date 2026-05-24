"""Single direct LLM call, no retrieval context: comprehensive Vietnam thermal sector report.

Sends a maximally-optimized comprehensive prompt to frontier reasoning models
and captures full responses for qualitative evaluation.  Uses high max_tokens
and temperature=0 for deterministic, exhaustive output.

Usage:
    uv run python -m aedist.query_direct \
        --prompt sota/protocol_07_naive_prompt.md \
        --models-registry models_frontier.yaml \
        --output outputs/direct_complete/ \
        --budget-usd 20

    # Single model:
    uv run python -m aedist.query_direct \
        --prompt sota/protocol_07_naive_prompt.md \
        --models-registry models_frontier.yaml \
        --output outputs/direct_complete/ \
        --model anthropic/claude-opus-4.6
"""

import argparse
import logging
from datetime import date
from pathlib import Path

import openai

from .harness import (
    BudgetTracker,
    append_evidence_pack,
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
    query_claude_cli,
    query_ollama_native,
    query_single_turn,
    save_json,
    select_models,
    should_skip,
)

log = logging.getLogger(__name__)

# Frontier defaults: maximize quality and output length.
# prompt_complete responses run 30–80K tokens on capable models; 32K caused
# near-truncation on Claude Opus (31374 tok). Raised to 65536 — check
# finish_reason="length" in outputs to detect models that still hit the cap.
DEFAULT_MAX_TOKENS = 65536
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
    parser.add_argument("--models-registry", required=True, help="Path to models YAML")
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
    parser.add_argument(
        "--no-think", action="store_true", help="Disable reasoning (Qwen3/thinking models)"
    )
    parser.add_argument("--model-set", default=None, help="Model set name from experiments.toml")
    parser.add_argument(
        "--experiments", default="experiments.toml", help="Path to experiments.toml"
    )
    parser.add_argument(
        "--sweep",
        default=None,
        help="Sweep name from experiments.toml; reads system_instruction from [sweeps.<name>].",
    )
    parser.add_argument(
        "--system-instruction",
        default=None,
        help="System message prepended to every API call (overrides --sweep value).",
    )
    parser.add_argument(
        "--evidence-pack-manifest",
        default=None,
        help=(
            "Optional evidence-pack manifest YAML path. "
            "When set, append the assembled evidence pack to the prompt."
        ),
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
    models = load_models(args.models_registry)
    output_dir = Path(args.output)

    system_instruction = args.system_instruction
    evidence_pack_manifest = args.evidence_pack_manifest
    if args.model_set:
        experiments = load_experiments(args.experiments)
        set_ids = experiments["sets"][args.model_set]["model_ids"]
        models = select_models(models, set_ids)
        if args.sweep and (system_instruction is None or evidence_pack_manifest is None):
            sweep_section = experiments.get("sweeps", {}).get(args.sweep, {})
        if args.sweep and system_instruction is None:
            system_instruction = sweep_section.get("system_instruction")
        if args.sweep and evidence_pack_manifest is None:
            evidence_pack_manifest = sweep_section.get("evidence_pack_manifest")
    elif args.sweep and (system_instruction is None or evidence_pack_manifest is None):
        experiments = load_experiments(args.experiments)
        sweep_section = experiments.get("sweeps", {}).get(args.sweep, {})
        if system_instruction is None:
            system_instruction = sweep_section.get("system_instruction")
        if evidence_pack_manifest is None:
            evidence_pack_manifest = sweep_section.get("evidence_pack_manifest")

    prompt = append_evidence_pack(prompt, evidence_pack_manifest)

    if args.model:
        models = [m for m in models if m["name"] == args.model]
        if not models:
            raise SystemExit(f"Model {args.model} not found in {args.models_registry}")

    # Estimate cost ceiling
    prompt_tokens_est = len(prompt) // 4
    for model in models:
        est_cost_in = prompt_tokens_est * model.get("price_per_mtok_in", 0) / 1_000_000
        est_cost_out = args.max_tokens * model.get("price_per_mtok_out", 0) / 1_000_000
        est_total = (est_cost_in + est_cost_out) * args.repeat
        log.info(
            "  %s: ~%d prompt tokens, max %d output → est $%.4f/run, $%.4f total",
            model.get("display_name", model["name"]),
            prompt_tokens_est,
            args.max_tokens,
            est_cost_in + est_cost_out,
            est_total,
        )

    if args.dry_run:
        log.info("Dry run — no API calls made.")
        return

    # Build client(s): per-route when using experiments.toml, else single legacy client
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
                if route == "claude-code-cli":
                    # Adapter is a subprocess; no OpenAI-style client needed.
                    clients[route] = None
                else:
                    clients[route] = make_client_for_route(model)
            client = clients[route]
        elif route == "claude-code-cli":
            # Legacy path also supports claude-code-cli (no client needed).
            client = None
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
                "Querying %s run %d/%d (direct, max_tokens=%d, temp=%.1f)...",
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
                    no_think=args.no_think,
                )
                api_model_id = model.get("model_id", model_id)
                messages = build_messages(prompt, system_instruction)
                # Ollama: bypass /v1/ shim to honour num_ctx (output cap via num_predict)
                if model.get("route") == "ollama":
                    ollama_url = model.get("base_url", "http://localhost:11434/v1")
                    ctx_window = model.get("context_window", 32768)
                    num_ctx = min(ctx_window, 81920)
                    result = query_ollama_native(
                        ollama_url,
                        api_model_id,
                        messages,
                        num_ctx,
                        num_predict=args.max_tokens,
                        no_think=args.no_think,
                    )
                elif model.get("route") == "claude-code-cli":
                    # Subprocess adapter; auth via user's Claude Code session.
                    # Temperature/seed/max_tokens are not configurable via the
                    # CLI — sweep flags are ignored on this route.
                    result = query_claude_cli(
                        api_model_id,
                        messages,
                    )
                else:
                    result = query_single_turn(
                        client,
                        api_model_id,
                        messages,
                        **api_kwargs,
                    )
                usage = result.get("usage") or {}
                # Claude CLI reports cost in the result; other routes
                # compute from registry pricing.
                if model.get("route") == "claude-code-cli":
                    cost = float(result.get("cost_usd") or 0.0)
                else:
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
                    "thinking": result.get("thinking", ""),
                    "finish_reason": result["finish_reason"],
                    "usage": usage,
                    "wall_seconds": result["wall_seconds"],
                    "cost_usd": cost,
                    "max_tokens": args.max_tokens,
                    "temperature": args.temperature,
                    "model_metadata": model_metadata(model),
                }
                if system_instruction:
                    record["system_instruction"] = system_instruction
                if evidence_pack_manifest:
                    record["evidence_pack_manifest"] = evidence_pack_manifest
                if model.get("reasoning_effort"):
                    record["reasoning_effort"] = model["reasoning_effort"]
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

    log.info("Direct benchmark complete. Total cost: $%.4f", budget.total_cost)


if __name__ == "__main__":
    main()
