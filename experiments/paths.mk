# Shared path/variable definitions for the AEDIST analysis + render phases.
#
# VARIABLES ONLY — this file declares zero rules. It is included by both
# experiments/analysis.mk (P2 score & consolidate) and experiments/render.mk
# (P3 analyze & render) so the two phases agree on where the repository tree,
# the derived data, and the P2 outcomes they share live. Override any path
# below to relocate the repository or point at alternate output trees.
#
# Ownership: a variable lives here only if BOTH phases reference it. Variables
# used by a single phase live in that phase's .mk (kept minimal here on
# purpose — ticket 0409 / tracker 0406 S2).

SHELL := /bin/bash

ANALYSIS_REPO_ROOT ?= .
ANALYSIS_EXPERIMENTS_DIR ?= $(ANALYSIS_REPO_ROOT)/experiments
ANALYSIS_REPORT_DIR ?= $(ANALYSIS_REPO_ROOT)/report
ANALYSIS_GENERATED_DIR ?= $(ANALYSIS_REPORT_DIR)/inputs/generated
ANALYSIS_GEN ?= $(ANALYSIS_GENERATED_DIR)
ANALYSIS_OUTPUTS_DIR ?= $(ANALYSIS_EXPERIMENTS_DIR)/outputs
ANALYSIS_DERIVED_DIR ?= $(ANALYSIS_EXPERIMENTS_DIR)/derived

# Shared P2 outcome paths. analysis.mk owns the rules that PRODUCE these;
# render.mk references them only as prerequisites (sources). Defining the
# paths here keeps the producer and the consumer in agreement.
ANALYSIS_EXP2_CROSS_EVAL_CSV ?= $(ANALYSIS_DERIVED_DIR)/sota_cross_eval.csv
ANALYSIS_EXP1_CROSS_EVAL_CSV ?= $(ANALYSIS_DERIVED_DIR)/exp1_cross_eval.csv
ANALYSIS_EXP2_MART_JSONL := $(ANALYSIS_DERIVED_DIR)/exp2_mart.jsonl

# Mart → view CSV projections. The PRODUCING rule is P3 (render.mk); the
# variable is shared because analysis.mk's dual-run parity staging still names
# the same four view basenames for its left/right comparison.
ANALYSIS_EXP2_MART_VIEWS := \
	$(ANALYSIS_GEN)/tab_exp2_arms_runs_view.csv \
	$(ANALYSIS_GEN)/tab_exp2_bib_quality_view.csv \
	$(ANALYSIS_GEN)/exp2_turn_trajectory_view.csv \
	$(ANALYSIS_GEN)/sota_cross_eval_view.csv
