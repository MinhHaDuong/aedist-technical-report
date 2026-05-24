# experiment2.mk — SOTA experiment runs (Arms 3 and 4)
#
# Run from the experiments/ directory:
#   make -f experiment2.mk arm3-run02
#   make -f experiment2.mk arm4-run02
#
# Exp 1 Qwen 3.7 top-up: modelset_exp1_baseline includes qwen/qwen3.7-max
# (commit 8c30c78). Use main Makefile census targets (skip-existing logic):
#   make census-generate && make census-run
#
# Bootstrap from pre-Makefile N=1 gate runs (run01 dirs must exist):
#   mkdir -p outputs/sota_exp3_arm3_batch1/run01
#   cp outputs/sota_exp3_arm3_batch1/summary.json \
#      outputs/sota_exp3_arm3_batch1/run01/summary.json
#   mkdir -p outputs/sota_exp3_arm4_batch1/run01
#   echo '[]' > outputs/sota_exp3_arm4_batch1/run01/summary.json

UV_RUN  := PYTHONPATH=.. uv run --project .. --env-file ../.env
AGENTS  := mistral openai anthropic qwen
EP      := evidence_packs/all18tables.yaml
ARM3    := outputs/sota_exp3_arm3_batch1
ARM4    := outputs/sota_exp3_arm4_batch1

# ─── Arm 3: naive single-shot + evidence pack ─────────────────────────────────

$(ARM3)/run%/summary.json: $(EP)
	$(UV_RUN) python sota/exp2_naive_arm.py \
	    --agents $(AGENTS) \
	    --output-dir $(@D) \
	    --evidence-pack-manifest $(EP)

# ─── Arm 4: interactive multi-turn + evidence pack ────────────────────────────

$(ARM4)/run%/summary.json: $(EP)
	$(UV_RUN) python sota/exp2_interactive_smoke.py \
	    --agents $(AGENTS) \
	    --output-dir $(@D) \
	    --evidence-pack-manifest $(EP) \
	    --no-confirm

# ─── Aliases ──────────────────────────────────────────────────────────────────
# .PRECIOUS prevents Make from deleting summary.json as an intermediate file
# after building the alias target.

.PRECIOUS: $(ARM3)/run%/summary.json $(ARM4)/run%/summary.json

arm3-%: $(ARM3)/%/summary.json ;
arm4-%: $(ARM4)/%/summary.json ;
