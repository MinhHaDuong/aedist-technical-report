# experiment1.mk — Exp 1 parametric baseline (no web search)
#
# Run from the experiments/ directory:
#   make -f experiment1.mk exp1-batch2
#
# Exp 1 measures parametric memory: same prompt as Exp 2 Arm 1
# (sota/protocol_07_naive_prompt.md) but no web search.
# batch1 = original run with prompt_complete.txt (frozen, outputs/direct_complete)
# batch2 = rerun with protocol_07_naive_prompt.md (GEM vocab, unified schema)

UV_RUN  := PYTHONPATH=.. uv run --project ..
PROMPT  := sota/protocol_07_naive_prompt.md
MODELS  := models.yaml
SET     := modelset_exp1_batch2
OUT     := outputs/exp1_batch2
NO_WEB_SYS := You have no web search capability. Do not claim to perform searches, \
              do not invoke tools, do not fabricate URLs. Answer from parametric knowledge only.

# ─── Batch 2 ──────────────────────────────────────────────────────────────────

$(OUT)/.done: $(PROMPT) $(MODELS)
	$(UV_RUN) python -m aedist.query_direct \
	    --prompt $(PROMPT) \
	    --models-registry $(MODELS) \
	    --model-set $(SET) \
	    --output $(OUT) \
	    --no-web-search \
	    --repeat 5 \
	    --max-tokens 65536 \
	    --system-instruction "$(NO_WEB_SYS)"
	touch $@

# ─── Aliases ──────────────────────────────────────────────────────────────────

.PRECIOUS: $(OUT)/.done

exp1-batch2: $(OUT)/.done ;
