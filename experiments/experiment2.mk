# experiment2.mk — SOTA experiment runs (Arms 3 and 4)
#
# Run from the experiments/ directory:
#   make -f experiment2.mk arm3-n2
#   make -f experiment2.mk arm4-run02
#   make -f experiment2.mk arm4-run03
#
# Exp 1 Qwen 3.7 top-up: the modelset_exp1_baseline now includes
# qwen/qwen3.7-max (commit 8c30c78). Use the main Makefile census targets
# which have skip-existing logic:
#   make census-generate && make census-run
#
# ── Arm 3 stamp note ─────────────────────────────────────────────────────────
# exp2_naive_arm.py --n N re-runs ALL reps 1..N on every invocation (no skip).
# Stamps are not chained — each target depends only on the evidence pack to
# avoid triple-running rep 1 when stepping from n1 → n2 → n3.
# Bootstrap after the pre-Makefile N=1 gate run:
#   touch outputs/sota_exp3_arm3_batch1/.stamp-n1
# ─────────────────────────────────────────────────────────────────────────────

UV_RUN  := uv run --project .. --env-file ../.env
AGENTS  := mistral openai anthropic qwen
EP      := evidence_packs/all18tables.yaml
ARM3    := outputs/sota_exp3_arm3_batch1
ARM4    := outputs/sota_exp3_arm4_batch1

# ─── Arm 3: naive single-shot + evidence pack (Exp 3) ────────────────────────

$(ARM3)/.stamp-n1: $(EP)
	$(UV_RUN) python sota/exp2_naive_arm.py \
	    --agents $(AGENTS) --n 1 \
	    --output-dir $(ARM3) \
	    --evidence-pack-manifest $(EP)
	@touch $@

$(ARM3)/.stamp-n2: $(EP)
	$(UV_RUN) python sota/exp2_naive_arm.py \
	    --agents $(AGENTS) --n 2 \
	    --output-dir $(ARM3) \
	    --evidence-pack-manifest $(EP)
	@touch $@

$(ARM3)/.stamp-n3: $(EP)
	$(UV_RUN) python sota/exp2_naive_arm.py \
	    --agents $(AGENTS) --n 3 \
	    --output-dir $(ARM3) \
	    --evidence-pack-manifest $(EP)
	@touch $@

.PHONY: arm3-n1 arm3-n2 arm3-n3
arm3-n1: $(ARM3)/.stamp-n1
arm3-n2: $(ARM3)/.stamp-n2
arm3-n3: $(ARM3)/.stamp-n3

# ─── Arm 4: interactive multi-turn + evidence pack (Exp 3) ───────────────────
# Each --run-number is a truly independent rep; stamps chain as review gates.
# Bootstrap after the pre-Makefile run01:
#   touch outputs/sota_exp3_arm4_batch1/.stamp-run01

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
