# experiment1.mk — Exp 1 parametric baseline (no web search)
#
# Run from the experiments/ directory:
#   make -f experiment1.mk exp1-batch2
#
# Exp 1 measures parametric memory: same prompt as Exp 2 Arm 1
# (sota/protocol_07_naive_prompt.md) but no web search.
# batch1 = original run with prompt_complete.txt (frozen, outputs/direct_complete)
# batch2 = rerun with protocol_07_naive_prompt.md (GEM vocab, unified schema)

UV_RUN  := PYTHONPATH=.. uv run --project .. --env-file ../.env
PROMPT  := sota/protocol_07_naive_prompt.md
MODELS  := models.yaml
SET     := modelset_frontier_10labs
OUT     := outputs/exp1_batch2

# ─── Batch 2 ──────────────────────────────────────────────────────────────────

$(OUT)/.done: $(PROMPT) $(MODELS)
	$(UV_RUN) python -m aedist.query_direct \
	    --prompt $(PROMPT) \
	    --models-registry $(MODELS) \
	    --model-set $(SET) \
	    --output $(OUT)
	touch $@

# ─── Aliases ──────────────────────────────────────────────────────────────────

.PRECIOUS: $(OUT)/.done

exp1-batch2: $(OUT)/.done ;
