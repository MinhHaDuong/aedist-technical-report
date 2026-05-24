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
# Bootstrap stamps after pre-Makefile N=1 gate runs:
#   touch outputs/sota_exp3_arm3_batch1/.stamp-run01
#   touch outputs/sota_exp3_arm4_batch1/.stamp-run01

UV_RUN  := uv run --project .. --env-file ../.env
AGENTS  := mistral openai anthropic qwen
EP      := evidence_packs/all18tables.yaml
ARM3    := outputs/sota_exp3_arm3_batch1
ARM4    := outputs/sota_exp3_arm4_batch1

# ─── Arm 3: naive single-shot + evidence pack (Exp 3) ────────────────────────
# Uses --run-number: one rep per invocation, O(1) API spend per step.

$(ARM3)/.stamp-run01: $(EP)
	$(UV_RUN) python sota/exp2_naive_arm.py \
	    --agents $(AGENTS) --run-number 1 \
	    --output-dir $(ARM3) \
	    --evidence-pack-manifest $(EP)
	@touch $@

$(ARM3)/.stamp-run02: $(ARM3)/.stamp-run01
	$(UV_RUN) python sota/exp2_naive_arm.py \
	    --agents $(AGENTS) --run-number 2 \
	    --output-dir $(ARM3) \
	    --evidence-pack-manifest $(EP)
	@touch $@

$(ARM3)/.stamp-run03: $(ARM3)/.stamp-run02
	$(UV_RUN) python sota/exp2_naive_arm.py \
	    --agents $(AGENTS) --run-number 3 \
	    --output-dir $(ARM3) \
	    --evidence-pack-manifest $(EP)
	@touch $@

.PHONY: arm3-run01 arm3-run02 arm3-run03
arm3-run01: $(ARM3)/.stamp-run01
arm3-run02: $(ARM3)/.stamp-run02
arm3-run03: $(ARM3)/.stamp-run03

# ─── Arm 4: interactive multi-turn + evidence pack (Exp 3) ───────────────────

$(ARM4)/.stamp-run01: $(EP)
	$(UV_RUN) python sota/exp2_interactive_smoke.py \
	    --agents $(AGENTS) \
	    --output-dir $(ARM4) \
	    --evidence-pack-manifest $(EP) \
	    --run-number 1 \
	    --no-confirm
	@touch $@

$(ARM4)/.stamp-run02: $(ARM4)/.stamp-run01
	$(UV_RUN) python sota/exp2_interactive_smoke.py \
	    --agents $(AGENTS) \
	    --output-dir $(ARM4) \
	    --evidence-pack-manifest $(EP) \
	    --run-number 2 \
	    --no-confirm
	@touch $@

$(ARM4)/.stamp-run03: $(ARM4)/.stamp-run02
	$(UV_RUN) python sota/exp2_interactive_smoke.py \
	    --agents $(AGENTS) \
	    --output-dir $(ARM4) \
	    --evidence-pack-manifest $(EP) \
	    --run-number 3 \
	    --no-confirm
	@touch $@

.PHONY: arm4-run01 arm4-run02 arm4-run03
arm4-run01: $(ARM4)/.stamp-run01
arm4-run02: $(ARM4)/.stamp-run02
arm4-run03: $(ARM4)/.stamp-run03
