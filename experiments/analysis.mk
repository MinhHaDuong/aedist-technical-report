# Exp2 analysis DAG — P2 (score & consolidate) build phase.
#
# PHASE: P2 score & consolidate. This file extracts run outputs, scores them,
# and assembles the canonical mart ($(ANALYSIS_EXP2_MART_JSONL)) and the
# cross-eval CSVs. The P3 (render) phase that turns these outcomes into
# figures/tables/macros lives in experiments/render.mk (ticket 0409, tracker
# 0406 S2) — a figure build can no longer reach back into this scoring DAG.
#
# Shared path variables come from experiments/paths.mk. Override the path
# variables there to relocate the repository or point at alternate output
# trees. (analysis.mk becomes score.mk in tracker 0406 step S3 — not renamed
# yet.)

include $(dir $(lastword $(MAKEFILE_LIST)))paths.mk

# --- P2-local input wildcards -----------------------------------------------

ANALYSIS_EXP2_NAIVE_DIR ?= $(ANALYSIS_DERIVED_DIR)/arm1_flat
ANALYSIS_EXP2_OPTIMISED_DIR ?= $(ANALYSIS_DERIVED_DIR)/arm2_flat
ANALYSIS_EXP2_ARM3_DIR ?= $(ANALYSIS_DERIVED_DIR)/arm3_flat
ANALYSIS_EXP2_ARM4_DIR ?= $(ANALYSIS_DERIVED_DIR)/arm4_flat

ANALYSIS_EXP1_INPUT_CSVS := $(wildcard $(ANALYSIS_EXPERIMENTS_DIR)/outputs/exp1_batch2/*.csv)

ANALYSIS_EXP2_NAIVE_JSONS := $(wildcard $(ANALYSIS_EXP2_NAIVE_DIR)/*.json)
ANALYSIS_EXP2_OPTIMISED_JSONS := $(wildcard $(ANALYSIS_EXP2_OPTIMISED_DIR)/*.json)
ANALYSIS_EXP2_ARM3_JSONS := $(wildcard $(ANALYSIS_EXP2_ARM3_DIR)/*.json)
ANALYSIS_EXP2_ARM4_JSONS := $(wildcard $(ANALYSIS_EXP2_ARM4_DIR)/*.json)
ANALYSIS_EXP2_NAIVE_MDS := $(wildcard $(ANALYSIS_EXP2_NAIVE_DIR)/*.md)
ANALYSIS_EXP2_OPTIMISED_MDS := $(wildcard $(ANALYSIS_EXP2_OPTIMISED_DIR)/*.md)
ANALYSIS_EXP2_ARM3_MDS := $(wildcard $(ANALYSIS_EXP2_ARM3_DIR)/*.md)
ANALYSIS_EXP2_ARM4_MDS := $(wildcard $(ANALYSIS_EXP2_ARM4_DIR)/*.md)
ANALYSIS_EXP2_PROBE_RAWS := $(wildcard $(ANALYSIS_EXP2_OPTIMISED_DIR)/probes/*/*.raw.json)
ANALYSIS_EXP2_PROBE_CLSF := $(wildcard $(ANALYSIS_EXP2_OPTIMISED_DIR)/probes/*/*.classification.json)

# --- Extraction stamps -------------------------------------------------------

$(ANALYSIS_DERIVED_DIR)/arm1_flat/.done: $(wildcard $(ANALYSIS_EXPERIMENTS_DIR)/outputs/sota_exp3_arm1_batch1/run*/*.json)
	uv run python -m aedist.extract_arm_single_turn \
	    --input-dir $(ANALYSIS_EXPERIMENTS_DIR)/outputs/sota_exp3_arm1_batch1 \
	    --output-dir $(ANALYSIS_DERIVED_DIR)/arm1_flat
	touch $@

$(ANALYSIS_DERIVED_DIR)/arm2_flat/.done: $(wildcard $(ANALYSIS_EXPERIMENTS_DIR)/outputs/sota_exp3_arm2_batch1/run*/summary.json)
	uv run python -m aedist.extract_arm_multi_turn \
	    --input-dir $(ANALYSIS_EXPERIMENTS_DIR)/outputs/sota_exp3_arm2_batch1 \
	    --output-dir $(ANALYSIS_DERIVED_DIR)/arm2_flat
	touch $@

$(ANALYSIS_DERIVED_DIR)/exp1_cross_eval/.done: $(ANALYSIS_EXP1_INPUT_CSVS) $(ANALYSIS_EXPERIMENTS_DIR)/../src/aedist/score_exp1.py
	rm -f $(ANALYSIS_EXP1_CROSS_EVAL_CSV)
	uv run python -m aedist.score_exp1 \
	    --input-dir $(ANALYSIS_EXPERIMENTS_DIR)/outputs/exp1_batch2 \
	    --output $(ANALYSIS_EXP1_CROSS_EVAL_CSV)
	mkdir -p $(ANALYSIS_DERIVED_DIR)/exp1_cross_eval
	touch $@

$(ANALYSIS_DERIVED_DIR)/arm3_flat/.done: $(wildcard $(ANALYSIS_EXPERIMENTS_DIR)/outputs/sota_exp3_arm3_batch1/run*/*.json)
	uv run python -m aedist.extract_arm_single_turn \
	    --input-dir $(ANALYSIS_EXPERIMENTS_DIR)/outputs/sota_exp3_arm3_batch1 \
	    --output-dir $(ANALYSIS_DERIVED_DIR)/arm3_flat
	touch $@

$(ANALYSIS_DERIVED_DIR)/arm4_flat/.done: $(wildcard $(ANALYSIS_EXPERIMENTS_DIR)/outputs/sota_exp3_arm4_batch1/run*/summary.json)
	uv run python -m aedist.extract_arm_multi_turn \
	    --input-dir $(ANALYSIS_EXPERIMENTS_DIR)/outputs/sota_exp3_arm4_batch1 \
	    --output-dir $(ANALYSIS_DERIVED_DIR)/arm4_flat
	touch $@

# --- Cross-eval CSV (scored per-run, both arms) ----------------------------

$(ANALYSIS_EXP2_CROSS_EVAL_CSV): $(ANALYSIS_DERIVED_DIR)/arm1_flat/.done \
		$(ANALYSIS_DERIVED_DIR)/arm2_flat/.done \
		$(ANALYSIS_DERIVED_DIR)/arm3_flat/.done \
		$(ANALYSIS_DERIVED_DIR)/arm4_flat/.done
	@mkdir -p $(dir $@)
	rm -f $@
	@for f in $(ANALYSIS_EXP2_NAIVE_DIR)/*.json; do \
		read m r < <(python3 -c "import json,sys; d=json.load(open('$$f')); print(d['model'], d['run'])"); \
		[ "$$m" = "None" ] && { echo "skip (model=None): $$f"; continue; }; \
		uv run python -m aedist.score_mechanical --arm naive --model "$$m" --run "$$r" \
		    --naive-dir $(ANALYSIS_EXP2_NAIVE_DIR) --optimised-dir $(ANALYSIS_EXP2_OPTIMISED_DIR) \
		    --output-csv $@ || true; \
	done
	@for f in $(ANALYSIS_EXP2_OPTIMISED_DIR)/*.json; do \
		read m r < <(python3 -c "import json,sys; d=json.load(open('$$f')); print(d['model'], d['run'])"); \
		[ "$$m" = "None" ] && { echo "skip (model=None): $$f"; continue; }; \
		uv run python -m aedist.score_mechanical --arm optimised --model "$$m" --run "$$r" \
		    --naive-dir $(ANALYSIS_EXP2_NAIVE_DIR) --optimised-dir $(ANALYSIS_EXP2_OPTIMISED_DIR) \
		    --output-csv $@ || true; \
	done
	@for f in $(ANALYSIS_EXP2_ARM3_DIR)/*.json; do \
		read m r < <(python3 -c "import json,sys; d=json.load(open('$$f')); print(d['model'], d['run'])"); \
		[ "$$m" = "None" ] && { echo "skip (model=None): $$f"; continue; }; \
		uv run python -m aedist.score_mechanical --arm arm3 --model "$$m" --run "$$r" \
		    --arm3-dir $(ANALYSIS_EXP2_ARM3_DIR) --arm4-dir $(ANALYSIS_EXP2_ARM4_DIR) \
		    --output-csv $@ || true; \
	done
	@for f in $(ANALYSIS_EXP2_ARM4_DIR)/*.json; do \
		read m r < <(python3 -c "import json,sys; d=json.load(open('$$f')); print(d['model'], d['run'])"); \
		[ "$$m" = "None" ] && { echo "skip (model=None): $$f"; continue; }; \
		uv run python -m aedist.score_mechanical --arm arm4 --model "$$m" --run "$$r" \
		    --arm3-dir $(ANALYSIS_EXP2_ARM3_DIR) --arm4-dir $(ANALYSIS_EXP2_ARM4_DIR) \
		    --output-csv $@ || true; \
	done

# --- Canonical mart ---------------------------------------------------------
# The mart-derived VIEW projections (*_view.csv) are render-time shaping (P3)
# and live in experiments/render.mk. This file produces only the mart itself.

$(ANALYSIS_EXP2_MART_JSONL): $(ANALYSIS_DERIVED_DIR)/arm1_flat/.done \
		$(ANALYSIS_DERIVED_DIR)/arm2_flat/.done \
		$(ANALYSIS_DERIVED_DIR)/arm3_flat/.done \
		$(ANALYSIS_DERIVED_DIR)/arm4_flat/.done \
		$(ANALYSIS_EXP2_NAIVE_JSONS) $(ANALYSIS_EXP2_NAIVE_MDS) \
		$(ANALYSIS_EXP2_OPTIMISED_JSONS) $(ANALYSIS_EXP2_OPTIMISED_MDS) \
		$(ANALYSIS_EXP2_ARM3_JSONS) $(ANALYSIS_EXP2_ARM3_MDS) \
		$(ANALYSIS_EXP2_ARM4_JSONS) $(ANALYSIS_EXP2_ARM4_MDS) \
		$(ANALYSIS_EXP2_CROSS_EVAL_CSV) $(ANALYSIS_EXP2_PROBE_RAWS) $(ANALYSIS_EXP2_PROBE_CLSF)
	@mkdir -p $(dir $@)
	uv run python -m aedist.build_exp2_mart \
	    --naive-dir $(ANALYSIS_EXP2_NAIVE_DIR) \
	    --optimised-dir $(ANALYSIS_EXP2_OPTIMISED_DIR) \
	    --arm3-dir $(ANALYSIS_EXP2_ARM3_DIR) \
	    --arm4-dir $(ANALYSIS_EXP2_ARM4_DIR) \
	    --cross-eval-csv $(ANALYSIS_EXP2_CROSS_EVAL_CSV) \
	    --output $@ \
	    --repo-root $(ANALYSIS_REPO_ROOT)

# --- Dual-run parity staging -------------------------------------------------
# P2 mart-validation scratch. Staged under the P2-owned derived/ tree (NOT the
# P3 handoff tree report/inputs/generated/) so this P2 file never writes a
# render artifact — the analysis.mk/render.mk seam stays clean (ticket 0409).
# Transient: untracked, consumed only by check-mart-parity below.

ANALYSIS_EXP2_OLD_STAGE := $(ANALYSIS_DERIVED_DIR)/parity/exp2-old-path
ANALYSIS_EXP2_MART_STAGE := $(ANALYSIS_DERIVED_DIR)/parity/exp2-mart-path

$(ANALYSIS_EXP2_OLD_STAGE)/tab_exp2_arms_runs.csv: $(ANALYSIS_EXP2_NAIVE_JSONS) $(ANALYSIS_EXP2_NAIVE_MDS) $(ANALYSIS_EXP2_OPTIMISED_JSONS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_arms_runs \
	    --naive-dir $(ANALYSIS_EXP2_NAIVE_DIR) \
	    --optimised-dir $(ANALYSIS_EXP2_OPTIMISED_DIR) \
	    --output $@

$(ANALYSIS_EXP2_OLD_STAGE)/tab_exp2_bib_quality.csv: $(ANALYSIS_EXP2_NAIVE_MDS) $(ANALYSIS_EXP2_OPTIMISED_MDS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.extract_exp2_bib \
	    --naive-dir $(ANALYSIS_EXP2_NAIVE_DIR) \
	    --optimised-dir $(ANALYSIS_EXP2_OPTIMISED_DIR) \
	    --output $@

$(ANALYSIS_EXP2_OLD_STAGE)/exp2_turn_trajectory.csv: $(ANALYSIS_EXP2_PROBE_RAWS) $(ANALYSIS_EXP2_PROBE_CLSF)
	@mkdir -p $(dir $@)
	uv run python -m aedist.export_exp2_turn_trajectory_csv \
	    --probes-dir $(ANALYSIS_EXP2_OPTIMISED_DIR)/probes \
	    --output $@

$(ANALYSIS_EXP2_OLD_STAGE)/sota_cross_eval.csv: $(ANALYSIS_EXP2_CROSS_EVAL_CSV)
	@mkdir -p $(dir $@)
	cp $< $@

$(ANALYSIS_EXP2_MART_STAGE)/tab_exp2_arms_runs_view.csv $(ANALYSIS_EXP2_MART_STAGE)/tab_exp2_bib_quality_view.csv \
$(ANALYSIS_EXP2_MART_STAGE)/exp2_turn_trajectory_view.csv $(ANALYSIS_EXP2_MART_STAGE)/sota_cross_eval_view.csv: $(ANALYSIS_EXP2_MART_JSONL)
	@mkdir -p $(dir $@)
	uv run python -m aedist.build_exp2_mart_views \
	    --mart-jsonl $(ANALYSIS_EXP2_MART_JSONL) \
	    --output-dir $(ANALYSIS_EXP2_MART_STAGE) \
	    --repo-root $(ANALYSIS_REPO_ROOT)

exp2-old-path: \
	$(ANALYSIS_EXP2_OLD_STAGE)/tab_exp2_arms_runs.csv \
	$(ANALYSIS_EXP2_OLD_STAGE)/tab_exp2_bib_quality.csv \
	$(ANALYSIS_EXP2_OLD_STAGE)/exp2_turn_trajectory.csv \
	$(ANALYSIS_EXP2_OLD_STAGE)/sota_cross_eval.csv

exp2-mart-path: \
	$(ANALYSIS_EXP2_MART_STAGE)/tab_exp2_arms_runs_view.csv \
	$(ANALYSIS_EXP2_MART_STAGE)/tab_exp2_bib_quality_view.csv \
	$(ANALYSIS_EXP2_MART_STAGE)/exp2_turn_trajectory_view.csv \
	$(ANALYSIS_EXP2_MART_STAGE)/sota_cross_eval_view.csv

check-mart-parity: exp2-old-path exp2-mart-path
	uv run python -m aedist.check_exp2_mart_parity \
	    --left-dir $(ANALYSIS_EXP2_OLD_STAGE) \
	    --right-dir $(ANALYSIS_EXP2_MART_STAGE)
