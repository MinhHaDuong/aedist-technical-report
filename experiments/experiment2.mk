# experiment2.mk — SOTA experiment runs (all four arms)
#
# Run from the experiments/ directory:
#   make -f experiment2.mk arm1-run01   # naive, no EP (N=5)
#   make -f experiment2.mk arm2-run01   # optimized, no EP (N=5)
#   make -f experiment2.mk arm3-run03   # naive + EP (N=3, start at run03)
#   make -f experiment2.mk arm4-run02   # optimized + EP (N=3, start at run02)
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
ARM1    := outputs/sota_exp3_arm1_batch1
ARM2    := outputs/sota_exp3_arm2_batch1
ARM3    := outputs/sota_exp3_arm3_batch1
ARM4    := outputs/sota_exp3_arm4_batch1

# ─── Arm 1: naive single-shot, no evidence pack ───────────────────────────────

$(ARM1)/run%/summary.json:
	$(UV_RUN) python sota/exp2_naive_arm.py \
	    --agents $(AGENTS) \
	    --output-dir $(@D)

# ─── Arm 2: interactive multi-turn, no evidence pack ─────────────────────────

$(ARM2)/run%/summary.json:
	$(UV_RUN) python sota/exp2_interactive_smoke.py \
	    --agents $(AGENTS) \
	    --output-dir $(@D) \
	    --no-confirm

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

.PRECIOUS: $(ARM1)/run%/summary.json $(ARM2)/run%/summary.json \
           $(ARM3)/run%/summary.json $(ARM4)/run%/summary.json

arm1-%: $(ARM1)/%/summary.json ;
arm2-%: $(ARM2)/%/summary.json ;
arm3-%: $(ARM3)/%/summary.json ;
arm4-%: $(ARM4)/%/summary.json ;
