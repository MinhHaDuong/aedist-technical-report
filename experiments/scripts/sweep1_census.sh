#!/usr/bin/env bash
# Sweep 1: Model census — query all 24 models, 3 runs each, extract, evaluate.
# Budget: $10 maximum. Models queried cheapest-first so budget exhaustion
# still yields maximum model coverage.
#
# Prerequisites:
#   - OPENROUTER_API_KEY set and valid
#   - uv installed
#   - Run from the aedist repo root
#
# Usage:
#   bash scripts/sweep1_census.sh [--dry-run]

set -euo pipefail

PROMPT="prompts/prompt_structured.txt"
MODELS="models.yaml"
OUTPUT="outputs/sweep1_census"
REPEAT=3
BUDGET=10

DRYRUN=""
if [[ "${1:-}" == "--dry-run" ]]; then
    DRYRUN="--dry-run"
    echo "[DRY RUN] No API calls will be made."
fi

# Verify API key
if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
    echo "ERROR: OPENROUTER_API_KEY not set"
    exit 1
fi

echo "=== Sweep 1: Model Census ==="
echo "Budget: \$${BUDGET}"
echo "Repeat: ${REPEAT} runs per model"
echo "Output: ${OUTPUT}/"
echo ""

# Models ordered by estimated cost (cheapest first).
# Cost estimate = 3 runs * ~2000 output tokens * price_per_mtok_out / 1e6
# Free tier first, then by output price ascending.
MODELS_ORDERED=(
    "qwen/qwen3.6-plus-preview:free"       # $0.00/Mtok
    "nvidia/nemotron-3-nano-30b-a3b"        # $0.20/Mtok
    "xiaomi/mimo-v2-flash"                  # $0.29/Mtok
    "deepseek/deepseek-v3.2"               # $0.38/Mtok
    "openai/gpt-5-nano"                    # $0.40/Mtok
    "google/gemini-2.5-flash-lite"         # $0.40/Mtok
    "mistralai/mistral-small-2603"         # $0.60/Mtok
    "meta-llama/llama-4-maverick"          # $0.60/Mtok
    "inception/mercury-2"                  # $0.75/Mtok
    "minimax/minimax-m2.7"                 # $1.20/Mtok
    "qwen/qwen3.5-35b-a3b"                # $1.30/Mtok
    "qwen/qwen3.5-27b"                    # $1.56/Mtok
    "qwen/qwen3.5-plus-02-15"             # $1.56/Mtok
    "moonshotai/kimi-k2.5"                # $1.99/Mtok
    "bytedance-seed/seed-2.0-lite"         # $2.00/Mtok
    "openai/gpt-5-mini"                   # $2.00/Mtok
    "qwen/qwen3.5-397b-a17b"              # $2.34/Mtok
    "google/gemini-3-flash-preview"        # $3.00/Mtok
    "xiaomi/mimo-v2-pro"                   # $3.00/Mtok
    "z-ai/glm-5-turbo"                    # $4.00/Mtok
    "x-ai/grok-4.20"                      # $6.00/Mtok
    "anthropic/claude-sonnet-4.6"          # $15.00/Mtok
    "openai/gpt-5.4"                      # $15.00/Mtok
    "anthropic/claude-opus-4.6"            # $25.00/Mtok
)

echo "Querying ${#MODELS_ORDERED[@]} models..."
echo ""

for model_id in "${MODELS_ORDERED[@]}"; do
    echo "--- $model_id ---"
    uv run python -m aedist.query \
        --prompt "$PROMPT" \
        --models "$MODELS" \
        --output "$OUTPUT" \
        --model "$model_id" \
        --repeat "$REPEAT" \
        --budget-usd "$BUDGET" \
        $DRYRUN \
    || echo "WARNING: $model_id failed or budget exceeded"
    echo ""
done

echo "=== Query phase complete ==="
echo ""

if [[ -n "$DRYRUN" ]]; then
    echo "[DRY RUN] Skipping extract and evaluate."
    exit 0
fi

# Extract CSVs from JSON responses
echo "=== Extracting CSVs ==="
uv run python -m aedist.extract \
    --input "$OUTPUT" \
    --output "$OUTPUT" \
    --overwrite \
|| echo "WARNING: Some extractions failed"
echo ""

# Evaluate all extracted CSVs
echo "=== Evaluating ==="
uv run python -m aedist.runner evaluate-all \
    --outputs-dir "$OUTPUT" \
    --output results/sweep1_census/ \
|| echo "WARNING: Evaluation had issues"
echo ""

echo "=== Sweep 1 complete ==="
echo "Results summary: results/sweep1_census/all_metrics.json"
