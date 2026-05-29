# Exp2 analysis DAG
#
# This file declares the analysis pipeline from run outputs to report-ready
# artifacts. Override the path variables below to relocate the repository or
# point at alternate output trees.

SHELL := /bin/bash

ANALYSIS_REPO_ROOT ?= .
ANALYSIS_EXPERIMENTS_DIR ?= $(ANALYSIS_REPO_ROOT)/experiments
ANALYSIS_REPORT_DIR ?= $(ANALYSIS_REPO_ROOT)/report
ANALYSIS_GENERATED_DIR ?= $(ANALYSIS_REPORT_DIR)/inputs/generated
ANALYSIS_GEN ?= $(ANALYSIS_GENERATED_DIR)
ANALYSIS_OUTPUTS_DIR ?= $(ANALYSIS_EXPERIMENTS_DIR)/outputs
ANALYSIS_DERIVED_DIR ?= $(ANALYSIS_EXPERIMENTS_DIR)/derived

ANALYSIS_EXP2_NAIVE_DIR ?= $(ANALYSIS_DERIVED_DIR)/arm1_flat
ANALYSIS_EXP2_OPTIMISED_DIR ?= $(ANALYSIS_DERIVED_DIR)/arm2_flat
ANALYSIS_EXP2_ARM3_DIR ?= $(ANALYSIS_DERIVED_DIR)/arm3_flat
ANALYSIS_EXP2_ARM4_DIR ?= $(ANALYSIS_DERIVED_DIR)/arm4_flat
ANALYSIS_EXP2_CROSS_EVAL_CSV ?= $(ANALYSIS_DERIVED_DIR)/sota_cross_eval.csv
ANALYSIS_EXP1_CROSS_EVAL_CSV ?= $(ANALYSIS_DERIVED_DIR)/exp1_cross_eval.csv

ANALYSIS_EXP1_INPUT_CSVS := $(wildcard $(ANALYSIS_EXPERIMENTS_DIR)/outputs/exp1_batch2/*.csv)
ANALYSIS_EXP1_BATCH2_RECORDS := $(wildcard $(ANALYSIS_EXPERIMENTS_DIR)/outputs/exp1_batch2/*.record.json)

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

ANALYSIS_SLIDE_GEN ?= $(ANALYSIS_REPO_ROOT)/slides/inputs/generated
ANALYSIS_EXP2_MART_JSONL := $(ANALYSIS_DERIVED_DIR)/exp2_mart.jsonl
ANALYSIS_EXP2_MART_VIEWS := \
	$(ANALYSIS_GEN)/tab_exp2_arms_runs_view.csv \
	$(ANALYSIS_GEN)/tab_exp2_bib_quality_view.csv \
	$(ANALYSIS_GEN)/exp2_turn_trajectory_view.csv \
	$(ANALYSIS_GEN)/sota_cross_eval_view.csv

ANALYSIS_EXP2_ARM_FIG := $(ANALYSIS_GEN)/fig_exp2_arms_comparison.pdf
ANALYSIS_EXP2_TURN_FIG := $(ANALYSIS_GEN)/fig_exp2_turn_trajectory.pdf
ANALYSIS_EXP2_BIB_TABLE := $(ANALYSIS_GEN)/tab_exp2_bib_quality.tex
ANALYSIS_EXP2_COVERAGE_FIG := $(ANALYSIS_GEN)/fig_exp2_coverage_certainty.pdf
ANALYSIS_EXP2_SPIRE_FIG := $(ANALYSIS_GEN)/fig_quality_spider.pdf
ANALYSIS_EXP2_2X2_CSV := $(ANALYSIS_DERIVED_DIR)/tab_exp2_2x2.csv
ANALYSIS_EXP2_2X2_TEX := $(ANALYSIS_GEN)/tab_exp2_2x2.tex
ANALYSIS_EXP2_2X2_FR_TEX := $(ANALYSIS_SLIDE_GEN)/tab_exp2_2x2.tex
ANALYSIS_EXP2_COVERAGE_SPLIT := $(ANALYSIS_GEN)/fig_exp2_coverage.pdf
ANALYSIS_EXP2_COST_SPLIT := $(ANALYSIS_GEN)/fig_exp2_cost.pdf
ANALYSIS_SLIDE_MACROS := $(ANALYSIS_SLIDE_GEN)/macros.tex

ANALYSIS_EXP1_SPIDER_FAMILIES := $(ANALYSIS_GEN)/fig_spider_exp1_families.pdf
ANALYSIS_EXP1_SPIDER_CLAUDE := $(ANALYSIS_GEN)/fig_spider_exp1_claude.pdf

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

# --- Canonical mart and mart-derived views ---------------------------------

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

$(ANALYSIS_EXP2_COVERAGE_FIG): $(ANALYSIS_GEN)/tab_exp2_bib_quality_view.csv \
		$(ANALYSIS_GEN)/tab_exp2_arms_runs_view.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp2_coverage_certainty \
	    --input $(ANALYSIS_GEN)/tab_exp2_bib_quality_view.csv \
	    --arms-input $(ANALYSIS_GEN)/tab_exp2_arms_runs_view.csv \
	    --output $@

$(ANALYSIS_EXP2_SPIRE_FIG): $(ANALYSIS_GEN)/sota_cross_eval_view.csv experiments/quality_spider_config.yaml
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_quality_spider \
	    --input $< \
	    --config experiments/quality_spider_config.yaml \
	    --output $@

# Exp1 quality spiders: one script, two invocations (family 2x2 panels vs a
# single-model large spider) -> two targets, not a grouped rule.
$(ANALYSIS_EXP1_SPIDER_FAMILIES): $(ANALYSIS_DERIVED_DIR)/exp1_cross_eval/.done
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_quality_spider_exp1 \
	    --input $(ANALYSIS_EXP1_CROSS_EVAL_CSV) \
	    --output $@

$(ANALYSIS_EXP1_SPIDER_CLAUDE): $(ANALYSIS_DERIVED_DIR)/exp1_cross_eval/.done
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_quality_spider_exp1 \
	    --input $(ANALYSIS_EXP1_CROSS_EVAL_CSV) \
	    --model claude-opus-4.6 \
	    --output $@

$(ANALYSIS_GEN)/stat_tests_arm1_vs_arm2.txt: $(ANALYSIS_GEN)/tab_exp2_arms_runs_view.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_stat_tests \
	    --input $< \
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
	$(ANALYSIS_EXP2_ARM_FIG) \
	$(ANALYSIS_EXP2_TURN_FIG) \
	$(ANALYSIS_EXP2_BIB_TABLE) \
	$(ANALYSIS_EXP2_COVERAGE_FIG) \
	$(ANALYSIS_EXP2_SPIRE_FIG) \
	$(ANALYSIS_EXP2_OUTLINE_ARTIFACTS)

# 2x2 factorial table (F1 + cost, query-mode x documents). Co-produces the
# per-(agent,arm) CSV. Agent is the unit of replication; see the module docstring.
$(ANALYSIS_EXP2_2X2_TEX): $(ANALYSIS_EXP2_CROSS_EVAL_CSV) \
		$(ANALYSIS_DERIVED_DIR)/arm1_flat/.done \
		$(ANALYSIS_DERIVED_DIR)/arm2_flat/.done \
		$(ANALYSIS_DERIVED_DIR)/arm3_flat/.done \
		$(ANALYSIS_DERIVED_DIR)/arm4_flat/.done
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_2x2 \
	    --cross-eval-csv $(ANALYSIS_EXP2_CROSS_EVAL_CSV) \
	    --flat-root $(ANALYSIS_DERIVED_DIR) \
	    --output-csv $(ANALYSIS_EXP2_2X2_CSV) \
	    --output-tex $@ --lang en

$(ANALYSIS_EXP2_2X2_FR_TEX): $(ANALYSIS_EXP2_CROSS_EVAL_CSV) \
		$(ANALYSIS_DERIVED_DIR)/arm1_flat/.done \
		$(ANALYSIS_DERIVED_DIR)/arm2_flat/.done \
		$(ANALYSIS_DERIVED_DIR)/arm3_flat/.done \
		$(ANALYSIS_DERIVED_DIR)/arm4_flat/.done
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_2x2 \
	    --cross-eval-csv $(ANALYSIS_EXP2_CROSS_EVAL_CSV) \
	    --flat-root $(ANALYSIS_DERIVED_DIR) \
	    --output-csv $(ANALYSIS_EXP2_2X2_CSV) \
	    --output-tex $@ --lang fr

# --- Coverage/cost split figures (reads from mart views + Exp1 cost CSV) ------

$(ANALYSIS_EXP2_COVERAGE_SPLIT) $(ANALYSIS_EXP2_COST_SPLIT) &: \
		$(ANALYSIS_GEN)/tab_exp2_arms_runs_view.csv $(ANALYSIS_GEN)/cost_quality.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp2_arms_split \
	    --input $(ANALYSIS_GEN)/tab_exp2_arms_runs_view.csv \
	    --exp1-input $(ANALYSIS_GEN)/cost_quality.csv \
	    --coverage-output $(ANALYSIS_EXP2_COVERAGE_SPLIT) \
	    --cost-output $(ANALYSIS_EXP2_COST_SPLIT)

# --- Slide macros (census + measurements → slides/inputs/generated/) ----------

$(ANALYSIS_SLIDE_MACROS): $(ANALYSIS_GEN)/census_bars.csv $(ANALYSIS_REPO_ROOT)/measurements.jsonl
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_macros \
	    --census-csv $(ANALYSIS_GEN)/census_bars.csv --output $@

.PHONY: exp2-analysis-report exp1-analysis-figures report-tables report-figures chart-figures

exp2-analysis-report: $(ANALYSIS_EXP2_REPORT_TARGETS) \
	$(ANALYSIS_EXP2_2X2_TEX) $(ANALYSIS_EXP2_2X2_FR_TEX) \
	$(ANALYSIS_EXP2_COVERAGE_SPLIT) $(ANALYSIS_EXP2_COST_SPLIT) \
	$(ANALYSIS_SLIDE_MACROS)

exp1-analysis-figures: $(ANALYSIS_EXP1_SPIDER_FAMILIES) $(ANALYSIS_EXP1_SPIDER_CLAUDE)

# --- Report-side tables and figures (migrated from root Makefile by 0352) ---
# These produce committed handoff artifacts under $(ANALYSIS_GEN). The root
# Makefile's `report/report.pdf` rule depends on these files but has no
# recipes — `make report` is a writing-only build (tectonic) consuming
# committed artifacts. Regenerate them from this file:
#     make -f experiments/analysis.mk report-tables report-figures

ANALYSIS_MEASUREMENTS ?= $(ANALYSIS_REPO_ROOT)/measurements.jsonl

ANALYSIS_REPORT_DERIVED_DIR ?= $(ANALYSIS_REPO_ROOT)/derived
ANALYSIS_VARIANCE_JSON := $(ANALYSIS_REPORT_DERIVED_DIR)/variance_decomposition.json
ANALYSIS_VERIFICATION_DIR := $(ANALYSIS_REPORT_DERIVED_DIR)/verification
ANALYSIS_VERIFICATION_TRADEOFF := $(ANALYSIS_VERIFICATION_DIR)/tradeoff.csv

ANALYSIS_DECOMP_BEFORE := $(wildcard $(ANALYSIS_OUTPUTS_DIR)/rag_per_fuel/reconciliation_*.csv)
ANALYSIS_DECOMP_AFTER  := $(wildcard $(ANALYSIS_OUTPUTS_DIR)/rag_per_fuel_v2/reconciliation_*.csv)
ANALYSIS_RAG_CSVS      := $(wildcard $(ANALYSIS_OUTPUTS_DIR)/rag_extract/*.csv)
ANALYSIS_EXPERT_REF    := $(ANALYSIS_REPO_ROOT)/data/reference/vietnam_thermal_v1.csv
ANALYSIS_GEM_REF       := $(ANALYSIS_REPO_ROOT)/data/reference/gem_thermal.csv

ANALYSIS_CONVERTER_TEST := $(ANALYSIS_EXPERIMENTS_DIR)/data/converter_test
ANALYSIS_CONVERTER_META := $(ANALYSIS_CONVERTER_TEST)/benchmark_meta.yaml
ANALYSIS_CONVERTER_DOCS := $(wildcard $(ANALYSIS_CONVERTER_TEST)/*/Decision-1509.md)

$(ANALYSIS_GEN)/tab_census.tex: $(ANALYSIS_MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_census --output $@

$(ANALYSIS_GEN)/macros.tex: $(ANALYSIS_MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_macros --output $@

# Co-target fig_census_direct.pdf was retired with the ablation thread (0361);
# the script still requires --output, so the PDF is written to a sentinel path
# in $(ANALYSIS_REPORT_DERIVED_DIR) and not consumed by any downstream rule.
$(ANALYSIS_GEN)/macros_census.tex: $(ANALYSIS_MEASUREMENTS)
	@mkdir -p $(dir $@) $(ANALYSIS_REPORT_DERIVED_DIR)
	uv run python -m aedist.plot_method_convergence \
	    --output $(ANALYSIS_REPORT_DERIVED_DIR)/_macros_census_unused.pdf \
	    --methods direct --prompt-version census \
	    --output-macros $@

$(ANALYSIS_GEN)/tab_relances.tex: $(ANALYSIS_MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_relances --output $@

$(ANALYSIS_GEN)/tab_comparaison.tex: $(ANALYSIS_MEASUREMENTS) $(ANALYSIS_VARIANCE_JSON)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_comparaison --output $@ --variance-json $(ANALYSIS_VARIANCE_JSON)

$(ANALYSIS_GEN)/tab_reconciliation.tex: $(ANALYSIS_MEASUREMENTS) $(ANALYSIS_EXPERT_REF) $(ANALYSIS_GEM_REF)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_reconciliation --output $@ --expert-ref $(ANALYSIS_EXPERT_REF) --gem-ref $(ANALYSIS_GEM_REF)

$(ANALYSIS_VARIANCE_JSON): $(ANALYSIS_MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.variance_decomposition --output $@

$(ANALYSIS_GEN)/tab_variance.tex: $(ANALYSIS_VARIANCE_JSON)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_variance --input $< --output $@

$(ANALYSIS_VERIFICATION_TRADEOFF): $(wildcard $(ANALYSIS_VERIFICATION_DIR)/*-run*.csv)
	uv run python -m aedist.tabulate_verification \
	    --input $(ANALYSIS_VERIFICATION_DIR) --output $@

$(ANALYSIS_GEN)/tab_verification.tex: $(ANALYSIS_VERIFICATION_TRADEOFF)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_verification \
	    --input $(ANALYSIS_VERIFICATION_DIR) --latex $@

$(ANALYSIS_GEN)/tab_decomposition_fix.tex: $(ANALYSIS_DECOMP_BEFORE) $(ANALYSIS_DECOMP_AFTER)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_decomposition_fix --output $@

$(ANALYSIS_GEN)/tab_coherence.tex: $(ANALYSIS_RAG_CSVS) $(ANALYSIS_REPO_ROOT)/src/aedist/tabulate_coherence.py $(ANALYSIS_REPO_ROOT)/src/aedist/coherence.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_coherence \
	    --input $(ANALYSIS_OUTPUTS_DIR)/rag_extract --output $@

$(ANALYSIS_GEN)/tab_converter_benchmark.tex: $(ANALYSIS_CONVERTER_META) $(ANALYSIS_CONVERTER_DOCS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.compare_converters \
	    --input $(ANALYSIS_CONVERTER_TEST) --meta $(ANALYSIS_CONVERTER_META) --output $@

# Grouping targets — drive end-to-end regeneration of report-side handoff
# artifacts. tab_self_consistency.tex and tab_per_run.tex are produced by the
# experiments/Makefile self-consistency target (single producer, 0354) and
# remain committed handoff artifacts without a rule here.
report-tables: \
	$(ANALYSIS_GEN)/tab_census.tex \
	$(ANALYSIS_GEN)/macros.tex \
	$(ANALYSIS_GEN)/macros_census.tex \
	$(ANALYSIS_GEN)/tab_relances.tex \
	$(ANALYSIS_EXP2_2X2_TEX) \
	$(ANALYSIS_GEN)/tab_comparaison.tex \
	$(ANALYSIS_GEN)/tab_variance.tex \
	$(ANALYSIS_GEN)/tab_verification.tex \
	$(ANALYSIS_GEN)/tab_decomposition_fix.tex \
	$(ANALYSIS_GEN)/tab_coherence.tex \
	$(ANALYSIS_GEN)/tab_reconciliation.tex \
	$(ANALYSIS_GEN)/tab_converter_benchmark.tex

report-figures: $(ANALYSIS_EXP1_SPIDER_FAMILIES)

# --- Chart-data figures (migrated from root Makefile by 0370) -----------------
# These produce committed handoff artifacts consumed by both report and slides.
# The writing-side `make report` and `make slides` have no recipes for these
# outputs — they are clean-room builds from committed artifacts only.

$(ANALYSIS_GEN)/census_bars.csv: $(ANALYSIS_MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_census --output $@

$(ANALYSIS_GEN)/fig_direct_cost_quality.pdf $(ANALYSIS_GEN)/cost_quality.csv &: $(ANALYSIS_MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_cost_quality \
	    --output $(ANALYSIS_GEN)/cost_quality.csv --figure $(ANALYSIS_GEN)/fig_direct_cost_quality.pdf

$(ANALYSIS_SLIDE_GEN)/regimes.csv: $(ANALYSIS_GEN)/regimes.csv
	@mkdir -p $(dir $@)
	cp $< $@

$(ANALYSIS_SLIDE_GEN)/fig_method_convergence.pdf: $(ANALYSIS_MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_method_convergence \
	    --output $@ --core-only

$(ANALYSIS_GEN)/fig_direct_p1_base.pdf $(ANALYSIS_GEN)/macros_p1_base.tex &: $(ANALYSIS_MEASUREMENTS) $(ANALYSIS_EXP1_BATCH2_RECORDS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_method_convergence \
	    --output $(ANALYSIS_GEN)/fig_direct_p1_base.pdf --methods direct \
	    --label-x 100 --label-ha left \
	    --xlabel "Assets identified (1 dot = 1 power plant / project)" \
	    --title "How do models recall Vietnam's thermal power assets? Not well." \
	    --ui-scale 1.35 \
	    --fig-width 12 --fig-height-min 8 --fig-height-per-run 0.06 --fig-height-per-method 0.35 \
	    --result-dir $(ANALYSIS_EXPERIMENTS_DIR)/outputs/exp1_batch2/ \
	    --output-macros $(dir $@)macros_p1_base.tex

$(ANALYSIS_SLIDE_GEN)/fig_regimes_scatter.pdf: $(ANALYSIS_MEASUREMENTS) $(ANALYSIS_EXPERIMENTS_DIR)/figures.toml
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_regimes_scatter \
	    --output $@

$(ANALYSIS_SLIDE_GEN)/fig_scaling_curve.pdf: $(ANALYSIS_MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_scaling_curve \
	    --output $@

$(ANALYSIS_GEN)/fig_capability_timeline.pdf: $(ANALYSIS_REPO_ROOT)/data/capability_timeline.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_capability_timeline \
	    --input $< --output $@

$(ANALYSIS_GEN)/fig_capability_dag.pdf: $(ANALYSIS_REPO_ROOT)/data/capability_timeline.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_capability_dag \
	    --input $< --output $@

$(ANALYSIS_GEN)/fig_spider_cross_exp.pdf: $(ANALYSIS_EXP1_CROSS_EVAL_CSV) $(ANALYSIS_EXP2_CROSS_EVAL_CSV)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_spider_cross_exp \
	    --exp1 $(ANALYSIS_EXP1_CROSS_EVAL_CSV) \
	    --exp2 $(ANALYSIS_EXP2_CROSS_EVAL_CSV) \
	    --output $@

chart-figures: \
	$(ANALYSIS_GEN)/census_bars.csv \
	$(ANALYSIS_GEN)/fig_direct_cost_quality.pdf \
	$(ANALYSIS_GEN)/fig_direct_p1_base.pdf \
	$(ANALYSIS_GEN)/fig_capability_timeline.pdf \
	$(ANALYSIS_GEN)/fig_capability_dag.pdf \
	$(ANALYSIS_GEN)/fig_spider_cross_exp.pdf \
	$(ANALYSIS_EXP1_SPIDER_FAMILIES) \
	$(ANALYSIS_SLIDE_GEN)/fig_method_convergence.pdf \
	$(ANALYSIS_SLIDE_GEN)/fig_regimes_scatter.pdf \
	$(ANALYSIS_SLIDE_GEN)/fig_scaling_curve.pdf
