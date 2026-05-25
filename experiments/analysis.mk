# Exp2 analysis DAG
#
# This file declares the analysis pipeline from run outputs to report-ready
# artifacts. Override the path variables below to relocate the repository or
# point at alternate output trees.

ANALYSIS_REPO_ROOT ?= .
ANALYSIS_EXPERIMENTS_DIR ?= $(ANALYSIS_REPO_ROOT)/experiments
ANALYSIS_REPORT_DIR ?= $(ANALYSIS_REPO_ROOT)/report
ANALYSIS_GENERATED_DIR ?= $(ANALYSIS_REPORT_DIR)/inputs/generated
ANALYSIS_GEN ?= $(ANALYSIS_GENERATED_DIR)
ANALYSIS_OUTPUTS_DIR ?= $(ANALYSIS_EXPERIMENTS_DIR)/outputs
ANALYSIS_DERIVED_DIR ?= $(ANALYSIS_EXPERIMENTS_DIR)/derived

ANALYSIS_EXP2_NAIVE_DIR ?= $(ANALYSIS_DERIVED_DIR)/arm1_flat
ANALYSIS_EXP2_OPTIMISED_DIR ?= $(ANALYSIS_DERIVED_DIR)/arm2_flat
ANALYSIS_EXP2_CROSS_EVAL_CSV ?= $(ANALYSIS_DERIVED_DIR)/sota_cross_eval.csv
ANALYSIS_EXP1_CROSS_EVAL_CSV ?= $(ANALYSIS_DERIVED_DIR)/exp1_cross_eval.csv

ANALYSIS_EXP1_INPUT_CSVS := $(wildcard $(ANALYSIS_EXPERIMENTS_DIR)/outputs/exp1_batch2/*.csv)

ANALYSIS_EXP2_NAIVE_JSONS := $(wildcard $(ANALYSIS_EXP2_NAIVE_DIR)/*.json)
ANALYSIS_EXP2_OPTIMISED_JSONS := $(wildcard $(ANALYSIS_EXP2_OPTIMISED_DIR)/*.json)
ANALYSIS_EXP2_NAIVE_MDS := $(wildcard $(ANALYSIS_EXP2_NAIVE_DIR)/*.md)
ANALYSIS_EXP2_OPTIMISED_MDS := $(wildcard $(ANALYSIS_EXP2_OPTIMISED_DIR)/*.md)
ANALYSIS_EXP2_PROBE_RAWS := $(wildcard $(ANALYSIS_EXP2_OPTIMISED_DIR)/probes/*/*.raw.json)
ANALYSIS_EXP2_PROBE_CLSF := $(wildcard $(ANALYSIS_EXP2_OPTIMISED_DIR)/probes/*/*.classification.json)

ANALYSIS_EXP2_MART_JSONL := $(ANALYSIS_GEN)/exp2_mart.jsonl
ANALYSIS_EXP2_MART_VIEWS := \
	$(ANALYSIS_GEN)/tab_exp2_arms_runs_view.csv \
	$(ANALYSIS_GEN)/tab_exp2_bib_quality_view.csv \
	$(ANALYSIS_GEN)/exp2_turn_trajectory_view.csv \
	$(ANALYSIS_GEN)/sota_cross_eval_view.csv

ANALYSIS_EXP2_TABLE := $(ANALYSIS_GEN)/tab_exp2_arms.tex
ANALYSIS_EXP2_ARM_FIG := $(ANALYSIS_GEN)/fig_exp2_arms_comparison.pdf
ANALYSIS_EXP2_TURN_FIG := $(ANALYSIS_GEN)/fig_exp2_turn_trajectory.pdf
ANALYSIS_EXP2_BIB_TABLE := $(ANALYSIS_GEN)/tab_exp2_bib_quality.tex
ANALYSIS_EXP2_COVERAGE_FIG := $(ANALYSIS_GEN)/fig_exp2_coverage_certainty.pdf
ANALYSIS_EXP2_SPIRE_FIG := $(ANALYSIS_GEN)/fig_quality_spider.pdf

ANALYSIS_EXP2_OUTLINE_ARTIFACTS := \
	$(ANALYSIS_GEN)/tab_exp2_outline_dataset.tex \
	$(ANALYSIS_GEN)/fig_exp2_outline_dataset.tex \
	$(ANALYSIS_GEN)/tab_exp2_outline_hypotheses_map.tex \
	$(ANALYSIS_GEN)/tab_exp2_outline_protocol_fidelity.tex \
	$(ANALYSIS_GEN)/tab_exp2_outline_h1.tex \
	$(ANALYSIS_GEN)/fig_exp2_outline_h2.tex \
	$(ANALYSIS_GEN)/tab_exp2_outline_h3.tex \
	$(ANALYSIS_GEN)/tab_exp2_outline_h4.tex \
	$(ANALYSIS_GEN)/tab_exp2_outline_h5.tex \
	$(ANALYSIS_GEN)/fig_exp2_outline_h6.tex \
	$(ANALYSIS_GEN)/tab_exp2_outline_hypothesis_status.tex

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

# --- Canonical mart and mart-derived views ---------------------------------

$(ANALYSIS_EXP2_MART_JSONL): $(ANALYSIS_DERIVED_DIR)/arm1_flat/.done \
		$(ANALYSIS_DERIVED_DIR)/arm2_flat/.done \
		$(ANALYSIS_EXP2_NAIVE_JSONS) $(ANALYSIS_EXP2_NAIVE_MDS) \
		$(ANALYSIS_EXP2_OPTIMISED_JSONS) $(ANALYSIS_EXP2_OPTIMISED_MDS) \
		$(ANALYSIS_EXP2_CROSS_EVAL_CSV) $(ANALYSIS_EXP2_PROBE_RAWS) $(ANALYSIS_EXP2_PROBE_CLSF)
	@mkdir -p $(dir $@)
	uv run python -m aedist.build_exp2_mart \
	    --naive-dir $(ANALYSIS_EXP2_NAIVE_DIR) \
	    --optimised-dir $(ANALYSIS_EXP2_OPTIMISED_DIR) \
	    --cross-eval-csv $(ANALYSIS_EXP2_CROSS_EVAL_CSV) \
	    --output $@ \
	    --repo-root $(ANALYSIS_REPO_ROOT)

$(ANALYSIS_EXP2_MART_VIEWS): $(ANALYSIS_EXP2_MART_JSONL)
	@mkdir -p $(dir $@)
	uv run python -m aedist.build_exp2_mart_views \
	    --mart-jsonl $(ANALYSIS_EXP2_MART_JSONL) \
	    --output-dir $(ANALYSIS_GEN) \
	    --repo-root $(ANALYSIS_REPO_ROOT)

# --- Dual-run parity staging -------------------------------------------------

ANALYSIS_EXP2_OLD_STAGE := $(ANALYSIS_GEN)/exp2-old-path
ANALYSIS_EXP2_MART_STAGE := $(ANALYSIS_GEN)/exp2-mart-path

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

# --- Tables and figures -----------------------------------------------------

$(ANALYSIS_EXP2_TABLE): $(ANALYSIS_GEN)/tab_exp2_arms_runs_view.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_arms \
	    --input $< \
	    --naive-dir $(ANALYSIS_EXP2_NAIVE_DIR) \
	    --optimised-dir $(ANALYSIS_EXP2_OPTIMISED_DIR) \
	    --output $@

$(ANALYSIS_EXP2_ARM_FIG): $(ANALYSIS_GEN)/tab_exp2_arms_runs_view.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp2_arms_comparison \
	    --input $< \
	    --output $@

$(ANALYSIS_EXP2_TURN_FIG): $(ANALYSIS_GEN)/exp2_turn_trajectory_view.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp2_turn_trajectory \
	    --input $< \
	    --output $@

$(ANALYSIS_EXP2_BIB_TABLE): $(ANALYSIS_GEN)/tab_exp2_bib_quality_view.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_bib_quality \
	    --input $< \
	    --output $@

$(ANALYSIS_EXP2_COVERAGE_FIG): $(ANALYSIS_GEN)/tab_exp2_bib_quality_view.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp2_coverage_certainty \
	    --input $< \
	    --output $@

$(ANALYSIS_EXP2_SPIRE_FIG): $(ANALYSIS_GEN)/sota_cross_eval_view.csv experiments/quality_spider_config.yaml
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_quality_spider \
	    --input $< \
	    --config experiments/quality_spider_config.yaml \
	    --output $@

# --- Outline placeholder artifacts (post-conference skeleton) ----------------

$(ANALYSIS_GEN)/tab_exp2_outline_dataset.tex:
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_outline_dataset --output $@

$(ANALYSIS_GEN)/fig_exp2_outline_dataset.tex:
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp2_outline_dataset --output $@

$(ANALYSIS_GEN)/tab_exp2_outline_hypotheses_map.tex:
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_outline_hypotheses_map --output $@

$(ANALYSIS_GEN)/tab_exp2_outline_protocol_fidelity.tex:
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_outline_protocol_fidelity --output $@

$(ANALYSIS_GEN)/tab_exp2_outline_h1.tex:
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_outline_h1 --output $@

$(ANALYSIS_GEN)/fig_exp2_outline_h2.tex:
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp2_outline_h2 --output $@

$(ANALYSIS_GEN)/tab_exp2_outline_h3.tex:
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_outline_h3 --output $@

$(ANALYSIS_GEN)/tab_exp2_outline_h4.tex:
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_outline_h4 --output $@

$(ANALYSIS_GEN)/tab_exp2_outline_h5.tex:
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_outline_h5 --output $@

$(ANALYSIS_GEN)/fig_exp2_outline_h6.tex:
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp2_outline_h6 --output $@

$(ANALYSIS_GEN)/tab_exp2_outline_hypothesis_status.tex:
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_outline_hypothesis_status --output $@

ANALYSIS_EXP2_REPORT_TARGETS := \
	$(ANALYSIS_EXP2_MART_VIEWS) \
	$(ANALYSIS_EXP2_TABLE) \
	$(ANALYSIS_EXP2_ARM_FIG) \
	$(ANALYSIS_EXP2_TURN_FIG) \
	$(ANALYSIS_EXP2_BIB_TABLE) \
	$(ANALYSIS_EXP2_COVERAGE_FIG) \
	$(ANALYSIS_EXP2_SPIRE_FIG) \
	$(ANALYSIS_EXP2_OUTLINE_ARTIFACTS)

.PHONY: exp2-analysis-report

exp2-analysis-report: $(ANALYSIS_EXP2_REPORT_TARGETS)
