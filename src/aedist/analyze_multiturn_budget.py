"""Analyze multi-turn token budget from existing experiment outputs.

Reads JSON results from multiturn outputs and extrapolates token growth
to N turns, reporting which models would overflow their context window.

Usage:
    python -m aedist.analyze_multiturn_budget \
        --input experiments/outputs/direct_multiturn \
        --turns 10
"""

import argparse
import json
import logging
from pathlib import Path

from .harness import CONTEXT_WINDOW_SAFETY_MARGIN, iter_model_replies

log = logging.getLogger(__name__)


def load_multiturn_results(output_dir: Path) -> list[dict]:
    """Load all JSON results from an experiment output directory."""
    results = []
    for f in iter_model_replies(output_dir):
        with open(f) as fh:
            results.append(json.load(fh))
    return results


def per_turn_token_usage(record: dict) -> list[dict]:
    """Extract per-turn prompt_tokens and completion_tokens from assistant turns."""
    return [
        {
            "turn": t["turn"],
            "prompt_tokens": t.get("usage", {}).get("prompt_tokens", 0) or 0,
            "completion_tokens": t.get("usage", {}).get("completion_tokens", 0) or 0,
        }
        for t in record.get("turns", [])
        if t["role"] == "assistant"
    ]


def extrapolate_to_n_turns(
    per_turn: list[dict],
    n_turns: int,
    context_window: int,
) -> dict:
    """Extrapolate token growth to n_turns. Returns projection dict."""
    if len(per_turn) < 2:
        last_prompt = per_turn[0]["prompt_tokens"] if per_turn else 0
        return {
            "observed_turns": len(per_turn),
            "last_prompt_tokens": last_prompt,
            "avg_growth_per_turn": 0,
            "projected_prompt_at_n": last_prompt,
            "context_window": context_window,
            "limit_80pct": int(context_window * CONTEXT_WINDOW_SAFETY_MARGIN),
            "projected_pct": last_prompt / context_window * 100 if context_window else 0,
            "overflow": False,
        }

    # Growth per turn = delta in prompt_tokens between consecutive turns
    deltas = []
    for i in range(1, len(per_turn)):
        delta = per_turn[i]["prompt_tokens"] - per_turn[i - 1]["prompt_tokens"]
        deltas.append(delta)

    avg_growth = sum(deltas) / len(deltas)
    last_prompt = per_turn[-1]["prompt_tokens"]
    last_turn = per_turn[-1]["turn"]
    # Turns are 0-indexed: turn 0 is the initial prompt, turn 1 is first relance, etc.
    # So n_turns=10 means turns 0..9, and remaining = 9 - last_observed_turn.
    remaining = n_turns - 1 - last_turn
    projected = last_prompt + max(0, remaining) * avg_growth

    limit = int(context_window * CONTEXT_WINDOW_SAFETY_MARGIN)

    return {
        "observed_turns": len(per_turn),
        "last_prompt_tokens": last_prompt,
        "avg_growth_per_turn": round(avg_growth),
        "projected_prompt_at_n": round(projected),
        "context_window": context_window,
        "limit_80pct": limit,
        "projected_pct": projected / context_window * 100 if context_window else 0,
        "overflow": projected > limit if context_window else False,
    }


def main():
    parser = argparse.ArgumentParser(description="Analyze multi-turn token budget")
    parser.add_argument("--input", required=True, help="Sweep output directory")
    parser.add_argument("--turns", type=int, default=10, help="Target number of turns")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    results = load_multiturn_results(Path(args.input))
    if not results:
        raise SystemExit(f"No JSON files found in {args.input}")

    log.info(
        "%-35s %4s  %6s  %6s  %8s  %10s  %6s  %s",
        "model",
        "run",
        "turns",
        "growth",
        "last_pt",
        "proj@" + str(args.turns),
        "pct",
        "overflow",
    )
    log.info("-" * 100)

    for record in results:
        model = record.get("model", "?")
        run = record.get("run", "?")
        ctx = record.get("model_metadata", {}).get("context_window", 0)

        per_turn = per_turn_token_usage(record)
        proj = extrapolate_to_n_turns(per_turn, args.turns, ctx)

        log.info(
            "%-35s %4s  %6d  %6d  %8d  %10d  %5.1f%%  %s",
            model,
            run,
            proj["observed_turns"],
            proj["avg_growth_per_turn"],
            proj["last_prompt_tokens"],
            proj["projected_prompt_at_n"],
            proj["projected_pct"],
            "OVERFLOW" if proj["overflow"] else "ok",
        )


if __name__ == "__main__":
    main()
