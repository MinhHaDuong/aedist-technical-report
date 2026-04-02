"""Shared utilities for the AEDIST query harness.

All query scripts (query, query_multiturn, query_rag, query_web) import
from here to avoid duplicating client setup, budget tracking, model loading,
save/skip logic, and cost computation.
"""

import json
import logging
import os
import time
from pathlib import Path

import yaml
from openai import OpenAI

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def load_models(path: str) -> list[dict]:
    """Load model registry from YAML file."""
    with open(path) as f:
        return yaml.safe_load(f)


def model_metadata(model: dict) -> dict:
    """Extract metadata fields from model registry entry."""
    return {
        k: model.get(k)
        for k in ("size_class", "country", "architecture", "provider", "context_window")
        if model.get(k) is not None
    }


# ---------------------------------------------------------------------------
# Cost computation
# ---------------------------------------------------------------------------

def compute_cost(usage: dict, model: dict) -> float:
    """Compute USD cost from token usage and model pricing."""
    price_in = model.get("price_per_mtok_in", 0.0)
    price_out = model.get("price_per_mtok_out", 0.0)
    prompt_tokens = usage.get("prompt_tokens", 0) or 0
    completion_tokens = usage.get("completion_tokens", 0) or 0
    return (prompt_tokens * price_in + completion_tokens * price_out) / 1_000_000


# ---------------------------------------------------------------------------
# Budget tracking
# ---------------------------------------------------------------------------

class BudgetTracker:
    """Track cumulative spend and stop when budget exceeded."""

    def __init__(self, budget_usd: float | None = None):
        self.budget_usd = budget_usd
        self.total_cost = 0.0

    def add(self, cost: float) -> None:
        self.total_cost += cost

    @property
    def exceeded(self) -> bool:
        if self.budget_usd is None:
            return False
        return self.total_cost >= self.budget_usd

    def check_or_warn(self) -> bool:
        """Return True if OK to proceed, False if budget exceeded."""
        if self.exceeded:
            log.warning(
                "Budget exceeded (%.4f >= %.4f USD). Stopping.",
                self.total_cost, self.budget_usd,
            )
            return False
        return True


# ---------------------------------------------------------------------------
# OpenAI client
# ---------------------------------------------------------------------------

def make_client() -> OpenAI:
    """Create an OpenRouter-compatible OpenAI client."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("Set OPENROUTER_API_KEY environment variable")
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )


# ---------------------------------------------------------------------------
# File naming and skip logic
# ---------------------------------------------------------------------------

def output_filename(model_id: str, run: int) -> str:
    """Generate output filename: {short_name}-run{n}.json."""
    short = model_id.split("/")[-1].replace(":", "-")
    return f"{short}-run{run}.json"


def output_path(output_dir: Path, model_id: str, run: int) -> Path:
    """Return the full output path for a model run."""
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / output_filename(model_id, run)


def should_skip(output_dir: Path, model_id: str, run: int) -> bool:
    """Return True if the output file already exists."""
    return output_path(output_dir, model_id, run).exists()


# ---------------------------------------------------------------------------
# Save helpers
# ---------------------------------------------------------------------------

def save_json(filepath: Path, record: dict) -> None:
    """Write a JSON record to file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    log.info("Saved %s", filepath)


# ---------------------------------------------------------------------------
# Single-turn query helper
# ---------------------------------------------------------------------------

def query_single_turn(
    client: OpenAI,
    model_id: str,
    messages: list[dict],
) -> dict:
    """Send messages to a model, return response dict with timing."""
    t0 = time.monotonic()
    response = client.chat.completions.create(
        model=model_id,
        messages=messages,
    )
    wall_seconds = round(time.monotonic() - t0, 3)
    choice = response.choices[0]
    usage = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
    }
    return {
        "content": choice.message.content,
        "finish_reason": choice.finish_reason,
        "usage": usage,
        "wall_seconds": wall_seconds,
    }
