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
# Bootstrap from pre-Makefile N=1 gate runs (run01 dirs must exist before
# make will accept run02 as a valid target):
#   mkdir -p outputs/sota_exp3_arm3_batch1/run01
#   cp outputs/sota_exp3_arm3_batch1/summary.json \
#      outputs/sota_exp3_arm3_batch1/run01/summary.json
#   mkdir -p outputs/sota_exp3_arm4_batch1/run01
#   echo '[]' > outputs/sota_exp3_arm4_batch1/run01/summary.json

UV_RUN  := uv run --project .. --env-file ../.env
AGENTS  := mistral openai anthropic qwen
EP      := evidence_packs/all18tables.yaml
ARM3    := outputs/sota_exp3_arm3_batch1
ARM4    := outputs/sota_exp3_arm4_batch1

# ─── Arm 3: naive single-shot + evidence pack (Exp 3) ────────────────────────
# summary.json in each per-run subdir is the build signal — no stamps.

$(ARM3)/run01/summary.json: $(EP)
	$(UV_RUN) python sota/exp2_naive_arm.py \
	    --agents $(AGENTS) \
	    --output-dir $(ARM3)/run01 \
	    --evidence-pack-manifest $(EP)

$(ARM3)/run02/summary.json: $(ARM3)/run01/summary.json
	$(UV_RUN) python sota/exp2_naive_arm.py \
	    --agents $(AGENTS) \
	    --output-dir $(ARM3)/run02 \
	    --evidence-pack-manifest $(EP)

$(ARM3)/run03/summary.json: $(ARM3)/run02/summary.json
	$(UV_RUN) python sota/exp2_naive_arm.py \
	    --agents $(AGENTS) \
	    --output-dir $(ARM3)/run03 \
	    --evidence-pack-manifest $(EP)

.PHONY: arm3-run01 arm3-run02 arm3-run03
arm3-run01: $(ARM3)/run01/summary.json
arm3-run02: $(ARM3)/run02/summary.json
arm3-run03: $(ARM3)/run03/summary.json

# ─── Arm 4: interactive multi-turn + evidence pack (Exp 3) ───────────────────

$(ARM4)/run01/summary.json: $(EP)
	$(UV_RUN) python sota/exp2_interactive_smoke.py \
	    --agents $(AGENTS) \
	    --output-dir $(ARM4)/run01 \
	    --evidence-pack-manifest $(EP) \
	    --run-number 1 \
	    --no-confirm

$(ARM4)/run02/summary.json: $(ARM4)/run01/summary.json
	$(UV_RUN) python sota/exp2_interactive_smoke.py \
	    --agents $(AGENTS) \
	    --output-dir $(ARM4)/run02 \
	    --evidence-pack-manifest $(EP) \
	    --run-number 2 \
	    --no-confirm

$(ARM4)/run03/summary.json: $(ARM4)/run02/summary.json
	$(UV_RUN) python sota/exp2_interactive_smoke.py \
	    --agents $(AGENTS) \
	    --output-dir $(ARM4)/run03 \
	    --evidence-pack-manifest $(EP) \
	    --run-number 3 \
	    --no-confirm

.PHONY: arm4-run01 arm4-run02 arm4-run03
arm4-run01: $(ARM4)/run01/summary.json
arm4-run02: $(ARM4)/run02/summary.json
arm4-run03: $(ARM4)/run03/summary.json
