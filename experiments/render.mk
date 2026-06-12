# AEDIST P3 (analyze & render) build phase.
#
# PHASE: P3 render. This file turns committed P2 outcomes into the
# figures, tables and macros the manuscript and slides include.
#
# SOURCES (consumed, never produced here — they appear only as
# prerequisites, and render.mk carries NO rule able to rebuild them):
#   * measurements.jsonl                          (P2 outcome, mart v0)
#   * experiments/derived/exp2_mart.jsonl         (P2 outcome, consolidated mart)
#   * experiments/derived/sota_cross_eval.csv     (P2 outcome, Exp2 cross-eval)
#   * experiments/derived/exp1_cross_eval.csv     (P2 outcome, Exp1 cross-eval)
#   * experiments/outputs/**                      (P1 raw model replies)
#   * data/reference/*, data/capability_timeline.csv, experiments/*.toml|yaml
#
# OUTCOMES (produced): figures/tables/macros under
#   report/inputs/generated/  (the single P3 deliverable tree, ticket 0408),
#   plus P3-internal derived analysis files under derived/ (variance JSON,
#   verification tradeoff CSV) consumed only by later P3 rules.
#
# INVARIANT: render.mk declares NO rule for an upstream (P1/P2) outcome. If a
#   source is missing, make MUST stop with "No rule to make target" — it must
#   never fall back to regenerating the mart or cross-eval CSVs (the
#   2026-06-03 cascade, ticket 0383). Shared path variables come from
#   experiments/paths.mk; experiments/derived/score.mk (P2) owns the producing
#   rules.
#
# Regenerate (mart-staleness hazard 0383: prefer dry-run for DAG checks):
#   make -f experiments/render.mk report-tables report-figures chart-figures
#
# Tracker 0406 step S2 (ticket 0409) extracted this file from the former P2
# score makefile (since consolidated into experiments/derived/score.mk, S3).

include $(dir $(lastword $(MAKEFILE_LIST)))paths.mk

# --- P3 output artifact paths (render-only) ---------------------------------

ANALYSIS_EXP2_ARM_FIG := $(ANALYSIS_GEN)/fig_exp2_arms_comparison.pdf
ANALYSIS_EXP2_TURN_FIG := $(ANALYSIS_GEN)/fig_exp2_turn_trajectory.pdf
ANALYSIS_EXP2_BIB_TABLE := $(ANALYSIS_GEN)/tab_exp2_bib_quality.tex
ANALYSIS_EXP2_BIB_TABLE_FR := $(ANALYSIS_GEN)/tab_exp2_bib_quality_fr.tex
ANALYSIS_EXP2_COVERAGE_FIG := $(ANALYSIS_GEN)/fig_exp2_coverage_certainty.pdf
ANALYSIS_EXP2_SPIRE_FIG := $(ANALYSIS_GEN)/fig_quality_spider.pdf
ANALYSIS_EXP2_2X2_CSV := $(ANALYSIS_DERIVED_DIR)/tab_exp2_2x2.csv
ANALYSIS_EXP2_2X2_TEX := $(ANALYSIS_GEN)/tab_exp2_2x2.tex
ANALYSIS_EXP2_2X2_FR_TEX := $(ANALYSIS_GEN)/tab_exp2_2x2_fr.tex
ANALYSIS_EXP2_2X2_AGENTS_TEX := $(ANALYSIS_GEN)/tab_exp2_2x2_agents.tex
ANALYSIS_EXP2_FONE_MACROS := $(ANALYSIS_GEN)/macros_exp2_f1.tex
ANALYSIS_EXP2_COVERAGE_SPLIT := $(ANALYSIS_GEN)/fig_exp2_coverage.pdf
ANALYSIS_EXP2_COST_SPLIT := $(ANALYSIS_GEN)/fig_exp2_cost.pdf
ANALYSIS_GROUNDING_LADDER_FIG := $(ANALYSIS_GEN)/fig_grounding_ladder.pdf
ANALYSIS_SLIDE_MACROS := $(ANALYSIS_GEN)/macros_slides.tex

ANALYSIS_EXP2_WIKI_CSV := $(ANALYSIS_GEN)/tab_exp2_wiki_compliance.csv
ANALYSIS_EXP2_WIKI_MACROS := $(ANALYSIS_GEN)/macros_wiki_compliance.tex

ANALYSIS_EXP1_SPIDER_FAMILIES := $(ANALYSIS_GEN)/fig_spider_exp1_families.pdf
ANALYSIS_EXP1_SPIDER_CLAUDE := $(ANALYSIS_GEN)/fig_spider_exp1_claude.pdf
# French-label variants for the French conference deck (slides.tex). The
# unsuffixed PDFs above are English (preprint-first; author 2026-06-06: all
# preprint figures in English, ticket 0455).
ANALYSIS_EXP1_SPIDER_FAMILIES_FR := $(ANALYSIS_GEN)/fig_spider_exp1_families_fr.pdf
ANALYSIS_EXP1_SPIDER_CLAUDE_FR := $(ANALYSIS_GEN)/fig_spider_exp1_claude_fr.pdf
ANALYSIS_EXP2_COVERAGE_FIG_FR := $(ANALYSIS_GEN)/fig_exp2_coverage_certainty_fr.pdf
# Quality-floor heatmap (ticket 0466): replaces spider in manuscript (main.tex).
ANALYSIS_EXP1_QUALITY_HEATMAP := $(ANALYSIS_GEN)/fig_quality_floor_heatmap_exp1.pdf
# Reliability-vs-accuracy screen (ticket 0506): section-4 figure + annex sweep.
# The sweep CSV is a P3→P4 handoff artifact, tracked in experiments/derived/.
ANALYSIS_EXP1_RELIABILITY_FIG := $(ANALYSIS_GEN)/fig_exp1_reliability.pdf
ANALYSIS_EXP1_RELIABILITY_SENS_CSV := $(ANALYSIS_DERIVED_DIR)/exp1_reliability_sensitivity.csv
ANALYSIS_EXP1_RELIABILITY_SENS_TEX := $(ANALYSIS_GEN)/tab_exp1_reliability_sensitivity.tex
# Within-model screen validation summary CSV (ticket 0467) and the annex
# macros fragment derived from the same single analysis pass (ticket 0531).
ANALYSIS_EXP1_SCREEN_VALID_CSV := $(ANALYSIS_GEN)/tab_screen_validation_within_model.csv
ANALYSIS_EXP1_SCREEN_MACROS := $(ANALYSIS_GEN)/macros_screen_validation.tex
# Exp1 run-stats macros: F1 min/mean/max/n_runs/n_models (ticket 0474).
ANALYSIS_EXP1_RUN_STATS_MACROS := $(ANALYSIS_GEN)/macros_exp1_run_stats.tex
# Status difficulty macros (proposed share/rate, overall rate, status accuracy
# excluding the proposed stratum — tickets 0531/0534).
ANALYSIS_STATUS_DIFFICULTY_MACROS := $(ANALYSIS_GEN)/macros_status_difficulty.tex
# Aggregation-sweep fusion-annex macros (ticket 0531).
ANALYSIS_AGG_SWEEP_MACROS := $(ANALYSIS_GEN)/macros_aggregation_sweep.tex
# Reference-register macros: count + fuel split (tickets 0501/0531).
ANALYSIS_REFERENCE_MACROS := $(ANALYSIS_GEN)/macros_reference.tex
# Consolidated manuscript macros file: concatenation of the curated fragments
# below; the manuscript preamble \inputs this single file (ticket 0531).
ANALYSIS_MANUSCRIPT_MACROS := $(ANALYSIS_GEN)/macros_manuscript.tex
# Reference-count anchoring analysis CSV (ticket 0293 — one-time exploration).
ANALYSIS_REF_COUNT_CSV := $(ANALYSIS_GEN)/ref_count_anchoring_analysis.csv
# Fusion MVP outputs (ticket 0473): §5 discovery gain figure + CSV + macros.
ANALYSIS_FUSION_MVP_CSV    := $(ANALYSIS_GEN)/fusion_mvp.csv
ANALYSIS_FUSION_MVP_MACROS := $(ANALYSIS_GEN)/macros_fusion_mvp.tex
ANALYSIS_FUSION_MVP_FIG    := $(ANALYSIS_GEN)/fig_fusion_mvp.pdf

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

# Report-side (measurements/mart-derived) P3 inputs and intermediates.
# ANALYSIS_MEASUREMENTS is defined in paths.mk (shared P2 outcome, now produced
# by score.mk and consumed here as a source).
ANALYSIS_EXP1_BATCH2_RECORDS := $(wildcard $(ANALYSIS_EXPERIMENTS_DIR)/outputs/exp1_batch2/*.record.json)
ANALYSIS_EXP1_INPUT_CSVS := $(wildcard $(ANALYSIS_EXPERIMENTS_DIR)/outputs/exp1_batch2/*.csv)

ANALYSIS_REPORT_DERIVED_DIR ?= $(ANALYSIS_REPO_ROOT)/derived
ANALYSIS_VARIANCE_JSON := $(ANALYSIS_REPORT_DERIVED_DIR)/variance_decomposition.json
ANALYSIS_VERIFICATION_DIR := $(ANALYSIS_REPORT_DERIVED_DIR)/verification
ANALYSIS_VERIFICATION_TRADEOFF := $(ANALYSIS_VERIFICATION_DIR)/tradeoff.csv

# Reconciliation CSVs regenerated from the archived raw replies by the P2
# decomp-fix step (experiments/derived/score.mk, ticket 0424 — unfreezing the
# 0421 freeze). Gitignored regenerable P2 intermediates (run
# `make -f experiments/derived/score.mk decomp-fix` first); the prereq lists
# wildcard the DERIVED dir, not the archive listing: in a clean room (no P2
# run) they are empty, so the committed tab_decomposition_fix.tex stands as
# up to date and render never scores (test_render_build_clean_room). Staleness
# vs a fresh P2 run is caught by the post-clean oracle, not by this rule.
ANALYSIS_DECOMP_FIX_DIR := $(ANALYSIS_DERIVED_DIR)/decomp_fix
ANALYSIS_DECOMP_BEFORE := $(wildcard $(ANALYSIS_DECOMP_FIX_DIR)/rag_per_fuel/reconciliation_*.csv)
ANALYSIS_DECOMP_AFTER  := $(wildcard $(ANALYSIS_DECOMP_FIX_DIR)/rag_per_fuel_v2/reconciliation_*.csv)
# Raw rag_extract CSVs moved to archive/ by edda724b.
ANALYSIS_RAG_CSVS      := $(wildcard $(ANALYSIS_EXPERIMENTS_DIR)/archive/outputs/rag_extract/*.csv)
ANALYSIS_EXPERT_REF    := $(ANALYSIS_REPO_ROOT)/data/reference/vietnam_thermal_plants_v2_classified.csv
ANALYSIS_GEM_REF       := $(ANALYSIS_REPO_ROOT)/data/reference/gem_thermal.csv
ANALYSIS_WIKI_COAL     := $(ANALYSIS_REPO_ROOT)/data/reference/raw/wikipedia_coal_vietnam-2026-06-09.wikitext
ANALYSIS_WIKI_POWER    := $(ANALYSIS_REPO_ROOT)/data/reference/raw/wikipedia_power_vietnam-2026-06-09.wikitext
ANALYSIS_CONCORDANCE_CSV := $(ANALYSIS_REPO_ROOT)/data/reference/tab_source_concordance.csv
ANALYSIS_WIKI_BAR_CSV  := $(ANALYSIS_REPO_ROOT)/data/reference/tab_wikipedia_recall_bar.csv
# Long-tail per-plant layer-membership table (ticket 0514): one row per
# reference plant with Gold/GEM/Wikipedia/OSM documentation flags.
# The long-tail figure reads THIS CSV; caption counts re-derive from it.
ANALYSIS_LONGTAIL_CSV  := $(ANALYSIS_REPO_ROOT)/data/reference/tab_longtail_layers.csv
# OSM power=plant extract (Overpass fetch) — the OSM recognition layer
# (ticket 0537). The directory name contains a space; escape it for Make.
ANALYSIS_OSM_CSV       := $(ANALYSIS_REPO_ROOT)/data/reference/OSM\ fetch/vn_power_plants.csv
# Fusion MVP scores against the live adopted reference (v2.4, 177 plants),
# like every other Exp1/2 manuscript artifact. It was pinned to the v2.1
# locked CSV (173 plants, ticket 0485) while the manuscript still carried the
# v2.1 vintage; #906 (ticket 0497) adopted v2.4 and ticket 0531 reconciles
# the manuscript to it, so the pin is retired (author decision 2026-06-09:
# ship the preprint at 177).
ANALYSIS_FUSION_MVP_REF := $(ANALYSIS_EXPERT_REF)

ANALYSIS_CONVERTER_TEST := $(ANALYSIS_EXPERIMENTS_DIR)/data/converter_test
ANALYSIS_CONVERTER_META := $(ANALYSIS_CONVERTER_TEST)/benchmark_meta.yaml
ANALYSIS_CONVERTER_DOCS := $(wildcard $(ANALYSIS_CONVERTER_TEST)/*/Decision-1509.md)

# --- Mart-derived views (P3 render-time projection of the P2 mart) ----------
# The mart itself ($(ANALYSIS_EXP2_MART_JSONL)) is a P2 outcome with NO rule
# here — it is a committed source. These views are the render-time shaping of
# that source and are produced by build_exp2_mart_views (the P3 projection).

$(ANALYSIS_EXP2_MART_VIEWS): $(ANALYSIS_EXP2_MART_JSONL)
	@mkdir -p $(dir $@)
	uv run python -m aedist.build_exp2_mart_views \
	    --mart-jsonl $(ANALYSIS_EXP2_MART_JSONL) \
	    --output-dir $(ANALYSIS_GEN) \
	    --repo-root $(ANALYSIS_REPO_ROOT)

# --- Tables and figures -----------------------------------------------------

# The comparison figure now loads Exp1 baseline data from the mart (via
# exp1_cost_quality), matching the split figure's E1 bar derivation.
$(ANALYSIS_EXP2_ARM_FIG): $(ANALYSIS_GEN)/tab_exp2_arms_runs_view.csv $(ANALYSIS_MEASUREMENTS) $(ANALYSIS_CONCORDANCE_CSV)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp2_arms_comparison \
	    --input $< \
	    --output $@

$(ANALYSIS_EXP2_TURN_FIG): $(ANALYSIS_GEN)/exp2_turn_trajectory_view.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp2_turn_trajectory \
	    --input $< \
	    --output $@

$(ANALYSIS_REF_COUNT_CSV): $(ANALYSIS_EXP2_MART_JSONL) \
		$(ANALYSIS_GEN)/sota_cross_eval_view.csv \
		$(ANALYSIS_GEN)/tab_exp2_bib_quality_view.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.analyze_ref_count_anchoring \
	    --mart $(ANALYSIS_EXP2_MART_JSONL) \
	    --cross-eval $(ANALYSIS_GEN)/sota_cross_eval_view.csv \
	    --bib-quality $(ANALYSIS_GEN)/tab_exp2_bib_quality_view.csv \
	    --output $@

$(ANALYSIS_EXP2_BIB_TABLE): $(ANALYSIS_GEN)/tab_exp2_bib_quality_view.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_bib_quality \
	    --input $< \
	    --output $@ --lang en

$(ANALYSIS_EXP2_BIB_TABLE_FR): $(ANALYSIS_GEN)/tab_exp2_bib_quality_view.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_bib_quality \
	    --input $< \
	    --output $@ --lang fr

# The plot script is a prerequisite: it carries the language labels (ticket
# 0455), so a label edit must re-trigger the figure build (mirrors the
# recognition-matrix rules).
$(ANALYSIS_EXP2_COVERAGE_FIG): $(ANALYSIS_GEN)/tab_exp2_bib_quality_view.csv \
		$(ANALYSIS_GEN)/tab_exp2_arms_runs_view.csv \
		$(ANALYSIS_REPO_ROOT)/src/aedist/plot_exp2_coverage_certainty.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp2_coverage_certainty \
	    --input $(ANALYSIS_GEN)/tab_exp2_bib_quality_view.csv \
	    --arms-input $(ANALYSIS_GEN)/tab_exp2_arms_runs_view.csv \
	    --output $@ \
	    --lang en

$(ANALYSIS_EXP2_COVERAGE_FIG_FR): $(ANALYSIS_GEN)/tab_exp2_bib_quality_view.csv \
		$(ANALYSIS_GEN)/tab_exp2_arms_runs_view.csv \
		$(ANALYSIS_REPO_ROOT)/src/aedist/plot_exp2_coverage_certainty.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp2_coverage_certainty \
	    --input $(ANALYSIS_GEN)/tab_exp2_bib_quality_view.csv \
	    --arms-input $(ANALYSIS_GEN)/tab_exp2_arms_runs_view.csv \
	    --output $@ \
	    --lang fr

$(ANALYSIS_EXP2_SPIRE_FIG): $(ANALYSIS_GEN)/sota_cross_eval_view.csv experiments/quality_spider_config.yaml
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_quality_spider \
	    --input $< \
	    --config experiments/quality_spider_config.yaml \
	    --output $@

# Exp1 quality spiders: one script, two invocations (family 2x2 panels vs a
# single-model large spider) -> two targets, not a grouped rule. The plot
# script is a prerequisite — it carries the language labels (ticket 0455), so a
# label edit must re-trigger the build.
$(ANALYSIS_EXP1_SPIDER_FAMILIES): $(ANALYSIS_EXP1_CROSS_EVAL_CSV) \
		$(ANALYSIS_REPO_ROOT)/src/aedist/plot_quality_spider_exp1.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_quality_spider_exp1 \
	    --input $(ANALYSIS_EXP1_CROSS_EVAL_CSV) \
	    --output $@ \
	    --lang en

$(ANALYSIS_EXP1_SPIDER_FAMILIES_FR): $(ANALYSIS_EXP1_CROSS_EVAL_CSV) \
		$(ANALYSIS_REPO_ROOT)/src/aedist/plot_quality_spider_exp1.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_quality_spider_exp1 \
	    --input $(ANALYSIS_EXP1_CROSS_EVAL_CSV) \
	    --output $@ \
	    --lang fr

$(ANALYSIS_EXP1_SPIDER_CLAUDE): $(ANALYSIS_EXP1_CROSS_EVAL_CSV) \
		$(ANALYSIS_REPO_ROOT)/src/aedist/plot_quality_spider_exp1.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_quality_spider_exp1 \
	    --input $(ANALYSIS_EXP1_CROSS_EVAL_CSV) \
	    --model claude-opus-4.6 \
	    --output $@ \
	    --lang en

$(ANALYSIS_EXP1_SPIDER_CLAUDE_FR): $(ANALYSIS_EXP1_CROSS_EVAL_CSV) \
		$(ANALYSIS_REPO_ROOT)/src/aedist/plot_quality_spider_exp1.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_quality_spider_exp1 \
	    --input $(ANALYSIS_EXP1_CROSS_EVAL_CSV) \
	    --model claude-opus-4.6 \
	    --output $@ \
	    --lang fr

# Quality-floor heatmap (ticket 0466): manuscript Figure 2b replacement.
# Columns = the 14 census models in fig_direct_p1_base order (deepseek included).
# Rows = discriminating 0–1 sub-scores (mean over runs, continuous red→green);
# the internal-coherence veto renders as 1−veto inside the Coherence group.
$(ANALYSIS_EXP1_QUALITY_HEATMAP): $(ANALYSIS_EXP1_CROSS_EVAL_CSV) \
		$(ANALYSIS_REPO_ROOT)/src/aedist/plot_quality_floor_heatmap_exp1.py \
		$(ANALYSIS_REPO_ROOT)/src/aedist/plot_quality_spider_exp1.py \
		$(ANALYSIS_REPO_ROOT)/src/aedist/plot_method_convergence.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_quality_floor_heatmap_exp1 \
	    --input $(ANALYSIS_EXP1_CROSS_EVAL_CSV) \
	    --output $@

# Reliability-vs-accuracy screen figure (ticket 0506): section-4 main figure.
# X = good runs out of 5 (12-dim reference-free gate), Y = mean F1 over good runs.
$(ANALYSIS_EXP1_RELIABILITY_FIG): $(ANALYSIS_EXP1_CROSS_EVAL_CSV) \
		$(ANALYSIS_REPO_ROOT)/src/aedist/plot_exp1_reliability.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp1_reliability \
	    --input $(ANALYSIS_EXP1_CROSS_EVAL_CSV) \
	    --output $@

# Gate sensitivity sweep (ticket 0506): tau x indicator-set grid for the annex.
# One invocation, two outputs (grouped &: rule): committed CSV + LaTeX table.
$(ANALYSIS_EXP1_RELIABILITY_SENS_CSV) $(ANALYSIS_EXP1_RELIABILITY_SENS_TEX) &: \
		$(ANALYSIS_EXP1_CROSS_EVAL_CSV) \
		$(ANALYSIS_REPO_ROOT)/src/aedist/plot_exp1_reliability.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp1_reliability \
	    --input $(ANALYSIS_EXP1_CROSS_EVAL_CSV) \
	    --sensitivity-csv $(ANALYSIS_EXP1_RELIABILITY_SENS_CSV) \
	    --annex-table $(ANALYSIS_EXP1_RELIABILITY_SENS_TEX)

# Within-model screen validation (ticket 0467): Annex F supporting CSV, plus
# the manuscript macros fragment from the same pass (grouped &: rule, 0531).
# Consumes raw exp1_batch2 CSVs (cap_distinct/status_distinct) + cross-eval F1.
# Two-source prereq: the cross-eval CSV (P2) and the raw run outputs (P1).
$(ANALYSIS_EXP1_SCREEN_VALID_CSV) $(ANALYSIS_EXP1_SCREEN_MACROS) &: \
		$(ANALYSIS_EXP1_CROSS_EVAL_CSV) \
		$(ANALYSIS_EXP1_INPUT_CSVS) \
		$(ANALYSIS_REPO_ROOT)/src/aedist/screen_validation_within_model.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.screen_validation_within_model \
	    --exp1-dir $(ANALYSIS_EXPERIMENTS_DIR)/outputs/exp1_batch2 \
	    --cross-eval $(ANALYSIS_EXP1_CROSS_EVAL_CSV) \
	    --output $(ANALYSIS_EXP1_SCREEN_VALID_CSV) \
	    --output-macros $(ANALYSIS_EXP1_SCREEN_MACROS)

# Exp1 run-stats macros: F1 min/mean/max, n_runs, n_models (ticket 0474).
# Consumes only the canonical cross-eval CSV (P2 committed source).
$(ANALYSIS_EXP1_RUN_STATS_MACROS): $(ANALYSIS_EXP1_CROSS_EVAL_CSV) \
		$(ANALYSIS_REPO_ROOT)/src/aedist/tabulate_exp1_run_stats.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp1_run_stats \
	    --cross-eval $(ANALYSIS_EXP1_CROSS_EVAL_CSV) \
	    --output $@

$(ANALYSIS_GEN)/stat_tests_arm1_vs_arm2.txt: $(ANALYSIS_GEN)/tab_exp2_arms_runs_view.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_stat_tests \
	    --input $< \
	    --output $@

# --- Fusion MVP (ticket 0473): §5 discovery gain — UNION vs ≥2-MODELS --------
# Three outputs from one script invocation (&: grouped rule).
# Sources: Exp1 batch2 .record.json files (P1) + arm3_flat .md files (P1).
# The record files are tracked; reconciliation CSVs are gitignored (generated
# on-the-fly by the script from record + raw CSV inputs).
$(ANALYSIS_FUSION_MVP_CSV) $(ANALYSIS_FUSION_MVP_MACROS) $(ANALYSIS_FUSION_MVP_FIG) &: \
		$(ANALYSIS_EXP1_BATCH2_RECORDS) \
		$(wildcard $(ANALYSIS_DERIVED_DIR)/arm3_flat/*.md) \
		$(ANALYSIS_REPO_ROOT)/src/aedist/plot_fusion_mvp.py \
		$(ANALYSIS_REPO_ROOT)/src/aedist/exp1_recognition.py \
		$(ANALYSIS_REPO_ROOT)/src/aedist/extract.py \
		$(ANALYSIS_FUSION_MVP_REF)
	@mkdir -p $(dir $(ANALYSIS_FUSION_MVP_CSV))
	uv run python -m aedist.plot_fusion_mvp \
	    --records-glob "$(ANALYSIS_EXPERIMENTS_DIR)/outputs/exp1_batch2/*.record.json" \
	    --arm3-dir $(ANALYSIS_DERIVED_DIR)/arm3_flat \
	    --reference $(ANALYSIS_FUSION_MVP_REF) \
	    --output-csv $(ANALYSIS_FUSION_MVP_CSV) \
	    --output-macros $(ANALYSIS_FUSION_MVP_MACROS) \
	    --output-figure $(ANALYSIS_FUSION_MVP_FIG)

.PHONY: fusion-mvp
fusion-mvp: $(ANALYSIS_FUSION_MVP_CSV) $(ANALYSIS_FUSION_MVP_MACROS) $(ANALYSIS_FUSION_MVP_FIG)

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
	$(ANALYSIS_EXP2_BIB_TABLE_FR) \
	$(ANALYSIS_EXP2_COVERAGE_FIG) \
	$(ANALYSIS_EXP2_COVERAGE_FIG_FR) \
	$(ANALYSIS_EXP2_SPIRE_FIG) \
	$(ANALYSIS_EXP2_OUTLINE_ARTIFACTS)

# 2x2 factorial table (F1 + cost, query-mode x documents). Co-produces the
# per-(agent,arm) CSV. Agent is the unit of replication; see the module docstring.
# Reads the committed cross-eval CSVs (P2 sources; the Exp1 one feeds the
# memory-baseline macros, ticket 0572) and the flat arm dirs (P1 source);
# produces nothing under P2 outcome paths.
$(ANALYSIS_EXP2_2X2_TEX) $(ANALYSIS_EXP2_2X2_AGENTS_TEX) $(ANALYSIS_EXP2_FONE_MACROS) &: \
		$(ANALYSIS_EXP2_CROSS_EVAL_CSV) \
		$(ANALYSIS_EXP1_CROSS_EVAL_CSV) \
		$(ANALYSIS_REPO_ROOT)/src/aedist/tabulate_exp2_2x2.py
	@mkdir -p $(ANALYSIS_GEN)
	uv run python -m aedist.tabulate_exp2_2x2 \
	    --cross-eval-csv $(ANALYSIS_EXP2_CROSS_EVAL_CSV) \
	    --flat-root $(ANALYSIS_DERIVED_DIR) \
	    --output-csv $(ANALYSIS_EXP2_2X2_CSV) \
	    --output-tex $(ANALYSIS_EXP2_2X2_TEX) \
	    --output-agents-tex $(ANALYSIS_EXP2_2X2_AGENTS_TEX) \
	    --exp1-cross-eval $(ANALYSIS_EXP1_CROSS_EVAL_CSV) \
	    --output-macros $(ANALYSIS_EXP2_FONE_MACROS) --lang en

$(ANALYSIS_EXP2_2X2_FR_TEX): $(ANALYSIS_EXP2_CROSS_EVAL_CSV)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_2x2 \
	    --cross-eval-csv $(ANALYSIS_EXP2_CROSS_EVAL_CSV) \
	    --flat-root $(ANALYSIS_DERIVED_DIR) \
	    --output-csv $(ANALYSIS_EXP2_2X2_CSV) \
	    --output-tex $@ --lang fr

# --- Coverage/cost split figures (mart views + Exp1 mart-derived baseline) ----
# The E1 baseline bars come from the shared aedist.exp1_cost_quality library
# (which reads measurements.jsonl directly), NOT from another figure script's
# cost_quality.csv — common cause, no P3-to-P3 side-output edge (ticket 0436).
$(ANALYSIS_EXP2_COVERAGE_SPLIT) $(ANALYSIS_EXP2_COST_SPLIT) &: \
		$(ANALYSIS_GEN)/tab_exp2_arms_runs_view.csv $(ANALYSIS_MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp2_arms_split \
	    --input $(ANALYSIS_GEN)/tab_exp2_arms_runs_view.csv \
	    --coverage-output $(ANALYSIS_EXP2_COVERAGE_SPLIT) \
	    --cost-output $(ANALYSIS_EXP2_COST_SPLIT)

# --- Grounding ladder figure (E1→1N→1D→5D, paired within-agent; ticket 0471) --
# Post-preprint / future work (deferred). Sources: both cross-eval CSVs (P2).
# The figure is a committed handoff artifact but is NOT included in the preprint
# (deferred per label in tickets/0471-...).
$(ANALYSIS_GROUNDING_LADDER_FIG): \
		$(ANALYSIS_EXP1_CROSS_EVAL_CSV) \
		$(ANALYSIS_EXP2_CROSS_EVAL_CSV) \
		$(ANALYSIS_REPO_ROOT)/src/aedist/plot_grounding_ladder.py \
		$(ANALYSIS_REPO_ROOT)/src/aedist/plot_exp2_arms_split.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_grounding_ladder \
	    --exp1 $(ANALYSIS_EXP1_CROSS_EVAL_CSV) \
	    --exp2 $(ANALYSIS_EXP2_CROSS_EVAL_CSV) \
	    --output $@

# --- Slide macros (measurements → report/inputs/generated/macros_slides.tex) ---
# The baseline census summary is derived from measurements.jsonl directly inside
# tabulate_macros (via aedist.exp1_census) — no census_bars.csv side-output from
# a figure script feeding this table rule (ticket 0436).
$(ANALYSIS_SLIDE_MACROS): $(ANALYSIS_MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_macros --census --output $@

# --- Exp2 Wikipedia/Wikidata compliance audit (protocol §3.4 H5 count) ------
# Scans Source 1/Source 2 cells and bibliography sections of all 40 registered
# runs for banned-domain citations. Co-produces CSV + macros (grouped &: rule).
# Prerequisites: two separate wildcard calls (Make wildcard has no brace
# expansion) over the flattened arm dirs (P1 sources via flatten, P3 audit).
$(ANALYSIS_EXP2_WIKI_CSV) $(ANALYSIS_EXP2_WIKI_MACROS) &: \
		$(wildcard $(ANALYSIS_DERIVED_DIR)/arm1_flat/*.md) \
		$(wildcard $(ANALYSIS_DERIVED_DIR)/arm2_flat/*.md) \
		$(ANALYSIS_REPO_ROOT)/src/aedist/audit_exp2_wiki_citations.py \
		$(ANALYSIS_REPO_ROOT)/src/aedist/extract_exp2_bib.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.audit_exp2_wiki_citations \
	    --naive-dir $(ANALYSIS_DERIVED_DIR)/arm1_flat \
	    --optimised-dir $(ANALYSIS_DERIVED_DIR)/arm2_flat \
	    --output $(ANALYSIS_EXP2_WIKI_CSV) \
	    --output-macros $(ANALYSIS_EXP2_WIKI_MACROS)

.PHONY: exp2-analysis-report exp1-analysis-figures report-tables report-figures chart-figures

RENDER_EXP2_ANALYSIS_REPORT := \
	$(ANALYSIS_EXP2_REPORT_TARGETS) \
	$(ANALYSIS_EXP2_2X2_TEX) $(ANALYSIS_EXP2_2X2_FR_TEX) \
	$(ANALYSIS_EXP2_2X2_AGENTS_TEX) \
	$(ANALYSIS_EXP2_COVERAGE_SPLIT) $(ANALYSIS_EXP2_COST_SPLIT) \
	$(ANALYSIS_SLIDE_MACROS) \
	$(ANALYSIS_GEN)/stat_tests_arm1_vs_arm2.txt

exp2-analysis-report: $(RENDER_EXP2_ANALYSIS_REPORT)

RENDER_EXP1_ANALYSIS_FIGURES := \
	$(ANALYSIS_EXP1_SPIDER_FAMILIES) \
	$(ANALYSIS_EXP1_SPIDER_CLAUDE) \
	$(ANALYSIS_EXP1_SPIDER_FAMILIES_FR) \
	$(ANALYSIS_EXP1_SPIDER_CLAUDE_FR)

exp1-analysis-figures: $(RENDER_EXP1_ANALYSIS_FIGURES)

# --- Report-side tables and figures (migrated from root Makefile by 0352) ---
# These produce committed handoff artifacts under $(ANALYSIS_GEN). The root
# Makefile's `report/report.pdf` rule depends on these files but has no
# recipes — `make report` is a writing-only build (tectonic) consuming
# committed artifacts. Regenerate them from this file:
#     make -f experiments/render.mk report-tables report-figures

$(ANALYSIS_GEN)/tab_decomposition.tex: $(ANALYSIS_MEASUREMENTS) $(ANALYSIS_REPO_ROOT)/src/aedist/tabulate_decomposition.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_decomposition --output $@

$(ANALYSIS_GEN)/tab_census.tex: $(ANALYSIS_MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_census --output $@

$(ANALYSIS_GEN)/macros.tex: $(ANALYSIS_MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_macros --output $@

# Census macros: emitted by the dedicated table module (tabulate_census_macros),
# which derives them from measurements.jsonl directly. Before ticket 0436 this
# was harvested as a side-output of plot_method_convergence, invoked purely to
# dump the macros while discarding its PDF to a sentinel path — a figure script
# run only to produce a table. The sentinel-PDF invocation is now retired.
$(ANALYSIS_GEN)/macros_census.tex: $(ANALYSIS_MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_census_macros \
	    --result-dir experiments/archive/outputs --output $@

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

$(ANALYSIS_VERIFICATION_TRADEOFF): $(wildcard $(ANALYSIS_VERIFICATION_DIR)/*-run*.csv) $(ANALYSIS_EXPERT_REF)
	uv run python -m aedist.tabulate_verification \
	    --input $(ANALYSIS_VERIFICATION_DIR) --output $@ \
	    --reference $(ANALYSIS_EXPERT_REF)

$(ANALYSIS_GEN)/tab_verification.tex: $(ANALYSIS_VERIFICATION_TRADEOFF)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_verification \
	    --input $(ANALYSIS_VERIFICATION_DIR) --latex $@ \
	    --reference $(ANALYSIS_EXPERT_REF)

# tab_decomposition_fix.tex: rule restored by ticket 0424 (frozen by 0421 —
# original reconciliation CSVs were gitignored and never archived). Inputs
# are the P2 decomp-fix reconciliation CSVs (score.mk decomp-fix; gitignored,
# regenerable from the committed archive).
# DRIFT (0383): a regenerated table reflects the CURRENT scorer/reference,
# not those in force when the 0068 table was produced — any diff vs the
# committed numbers needs explicit author review before committing.
$(ANALYSIS_GEN)/tab_decomposition_fix.tex: $(ANALYSIS_DECOMP_BEFORE) $(ANALYSIS_DECOMP_AFTER) $(ANALYSIS_REPO_ROOT)/src/aedist/tabulate_decomposition_fix.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_decomposition_fix --output $@ \
	    --before-dir $(ANALYSIS_DECOMP_FIX_DIR)/rag_per_fuel \
	    --after-dir $(ANALYSIS_DECOMP_FIX_DIR)/rag_per_fuel_v2

$(ANALYSIS_GEN)/tab_coherence.tex: $(ANALYSIS_RAG_CSVS) $(ANALYSIS_REPO_ROOT)/src/aedist/tabulate_coherence.py $(ANALYSIS_REPO_ROOT)/src/aedist/coherence.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_coherence \
	    --input $(ANALYSIS_EXPERIMENTS_DIR)/archive/outputs/rag_extract --output $@

$(ANALYSIS_GEN)/tab_converter_benchmark.tex: $(ANALYSIS_CONVERTER_META) $(ANALYSIS_CONVERTER_DOCS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.compare_converters \
	    --input $(ANALYSIS_CONVERTER_TEST) --meta $(ANALYSIS_CONVERTER_META) --output $@

# Rule restored by ticket 0417 (orphan found by the 0415 world-reach audit).
# The script writes the repo-rooted default path itself (== $@ under the
# default $(ANALYSIS_GEN)); it reads P1 raw replies directly, like
# tab_coherence above. The raw replies live under experiments/archive/
# (tracked P1 outcomes per 0405; live outputs/ keeps only .record.json).
$(ANALYSIS_GEN)/tab_source_grounding.tex: \
		$(wildcard $(ANALYSIS_EXPERIMENTS_DIR)/archive/outputs/rag_cited/claude-opus-4.6-run*.csv) \
		$(wildcard $(ANALYSIS_EXPERIMENTS_DIR)/archive/outputs/rag_per_fuel/deepseek-v3.2-run*.json) \
		$(ANALYSIS_REPO_ROOT)/src/aedist/tabulate_source_grounding.py \
		$(ANALYSIS_REPO_ROOT)/src/aedist/extract.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_source_grounding

# --- Self-consistency tables (render half; migrated from the P1 makefile (now
#     experiments/acquire.mk) by ticket 0410, tracker 0406 S3) ----------------
# The P2 score half ($(SCORE_SC_JSON): outputs/rag → derived/rag_consistency)
# lives in experiments/derived/score.mk. This render half tabulates the mart
# into the committed LaTeX handoff artifacts. Reads only measurements.jsonl (a
# P2 source) — writes nothing under a P2 outcome path.

ANALYSIS_SC_TEX    := $(ANALYSIS_GEN)/tab_self_consistency.tex
ANALYSIS_SC_PERRUN := $(ANALYSIS_GEN)/tab_per_run.tex

$(ANALYSIS_SC_TEX) $(ANALYSIS_SC_PERRUN) &: $(ANALYSIS_MEASUREMENTS) $(ANALYSIS_REPO_ROOT)/src/aedist/tabulate_self_consistency.py
	uv run python -m aedist.tabulate_self_consistency \
	    --output $(ANALYSIS_SC_TEX) --per-run-output $(ANALYSIS_SC_PERRUN)

.PHONY: self-consistency
self-consistency: $(ANALYSIS_SC_TEX) $(ANALYSIS_SC_PERRUN)

# --- Experiment 1 cost summary (migrated from the P1 makefile, now acquire.mk, 0410) ---

ANALYSIS_EXP1_COST_TEX := $(ANALYSIS_GEN)/tab_exp1_cost_summary.tex

$(ANALYSIS_EXP1_COST_TEX): $(ANALYSIS_MEASUREMENTS) $(ANALYSIS_REPO_ROOT)/src/aedist/tabulate_exp1_cost_summary.py
	uv run python -m aedist.tabulate_exp1_cost_summary \
	    --measurements $(ANALYSIS_MEASUREMENTS) --output $(ANALYSIS_EXP1_COST_TEX)

.PHONY: exp1-cost-summary
exp1-cost-summary: $(ANALYSIS_EXP1_COST_TEX)

# --- Experiment 1 reasoning top-up (migrated from the P1 makefile, now acquire.mk, 0410)

ANALYSIS_EXP1_TOPUP_TEX := $(ANALYSIS_GEN)/tab_exp1_reasoning_topup.tex

$(ANALYSIS_EXP1_TOPUP_TEX): $(ANALYSIS_MEASUREMENTS) $(ANALYSIS_REPO_ROOT)/src/aedist/tabulate_exp1_reasoning_topup.py
	uv run python -m aedist.tabulate_exp1_reasoning_topup \
	    --measurements $(ANALYSIS_MEASUREMENTS) --output $(ANALYSIS_EXP1_TOPUP_TEX)

.PHONY: exp1-reasoning-topup
exp1-reasoning-topup: $(ANALYSIS_EXP1_TOPUP_TEX)

# --- Exp3 false-negative triage summary (ticket 0374) -----------------------
# Reads the human-filled worksheet CSV (committed to experiments/derived/) and
# writes a per-bucket summary CSV + LaTeX table.
# Prerequisite: experiments/derived/exp3_fn_triage.csv must exist and have
# its bucket column filled in by the human reviewer before this rule is run.
# The worksheet itself is generated (one-shot, not a Make target) via:
#   uv run python -m aedist.tabulate_exp3_fn_triage --mode worksheet

ANALYSIS_EXP3_FN_TRIAGE_WORKSHEET := $(ANALYSIS_DERIVED_DIR)/exp3_fn_triage.csv
ANALYSIS_EXP3_FN_TRIAGE_SUMMARY_CSV := $(ANALYSIS_DERIVED_DIR)/tab_exp3_fn_triage_summary.csv
ANALYSIS_EXP3_FN_TRIAGE_TEX := $(ANALYSIS_GEN)/tab_exp3_fn_triage.tex

$(ANALYSIS_EXP3_FN_TRIAGE_TEX): $(ANALYSIS_EXP3_FN_TRIAGE_WORKSHEET) \
		$(ANALYSIS_REPO_ROOT)/src/aedist/tabulate_exp3_fn_triage.py \
		$(ANALYSIS_REPO_ROOT)/src/aedist/extract.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp3_fn_triage --mode summary \
	    --input $(ANALYSIS_EXP3_FN_TRIAGE_WORKSHEET) \
	    --output-csv $(ANALYSIS_EXP3_FN_TRIAGE_SUMMARY_CSV) \
	    --output-tex $@

.PHONY: exp3-fn-triage
exp3-fn-triage: $(ANALYSIS_EXP3_FN_TRIAGE_TEX)

# --- Run aggregation sweep (ticket 0375) ------------------------------------
# Two-step: (1) sweep_aggregations.py re-scores committed exp1_batch2 CSVs
# and writes the aggregation_sweep.csv; (2) tabulate_aggregation_sweep.py
# renders the LaTeX table. Step 1 is slow (~3 min LP matching); the CSV is
# committed so step 2 can run without step 1 on a clean-room build.

ANALYSIS_AGG_SWEEP_CSV := $(ANALYSIS_DERIVED_DIR)/aggregation_sweep.csv
ANALYSIS_AGG_SWEEP_TEX := $(ANALYSIS_GEN)/tab_aggregation_sweep.tex

# Step 1: generate the sweep CSV from committed per-run CSVs.
# Not a default dependency — run explicitly when exp1_batch2 data changes.
$(ANALYSIS_AGG_SWEEP_CSV): $(ANALYSIS_REPO_ROOT)/src/aedist/sweep_aggregations.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.sweep_aggregations --output $@

.PHONY: aggregation-sweep-csv
aggregation-sweep-csv: $(ANALYSIS_AGG_SWEEP_CSV)

# Step 2: render LaTeX table + fusion-annex macros (fast, clean-room safe).
# The macros also read the Exp1 cross-eval CSV (P2 committed source) for the
# single-run baseline — grouped &: rule, one invocation (ticket 0531).
$(ANALYSIS_AGG_SWEEP_TEX) $(ANALYSIS_AGG_SWEEP_MACROS) &: $(ANALYSIS_AGG_SWEEP_CSV) \
		$(ANALYSIS_EXP1_CROSS_EVAL_CSV) \
		$(ANALYSIS_REPO_ROOT)/src/aedist/tabulate_aggregation_sweep.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_aggregation_sweep \
	    --input $(ANALYSIS_AGG_SWEEP_CSV) \
	    --cross-eval $(ANALYSIS_EXP1_CROSS_EVAL_CSV) \
	    --output $(ANALYSIS_AGG_SWEEP_TEX) \
	    --output-macros $(ANALYSIS_AGG_SWEEP_MACROS)

.PHONY: aggregation-sweep
aggregation-sweep: $(ANALYSIS_AGG_SWEEP_TEX)

# --- Reference-register macros (tickets 0501/0531) ---------------------------
# Count via reference_plant_count() + fuel split from the adopted reference
# CSV; evaluate.py is a prerequisite because it owns the count derivation.
$(ANALYSIS_REFERENCE_MACROS): $(ANALYSIS_EXPERT_REF) \
		$(ANALYSIS_REPO_ROOT)/src/aedist/tabulate_reference_macros.py \
		$(ANALYSIS_REPO_ROOT)/src/aedist/evaluate.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_reference_macros \
	    --reference $(ANALYSIS_EXPERT_REF) \
	    --output $@

# --- Consolidated manuscript macros (ticket 0531) ----------------------------
# Concatenates the curated per-script fragments into the single file the
# manuscript preamble \inputs. Deliberately EXCLUDED: macros.tex,
# macros_slides.tex, macros_census.tex — they serve report.tex/slides.tex and
# reuse names defined here with different cohort values (\NumRefPlants,
# \NumCensusModels, \Census*); pulling them in would trip the duplicate guard
# and break slides.tex, which still \inputs them directly.
MANUSCRIPT_MACRO_FRAGMENTS := \
	$(ANALYSIS_GEN)/macros_phase_collisions.tex \
	$(ANALYSIS_EXP1_RUN_STATS_MACROS) \
	$(ANALYSIS_GEN)/macros_exp1_matrix.tex \
	$(ANALYSIS_GEN)/macros_exp2_matrix_naive.tex \
	$(ANALYSIS_GEN)/macros_exp2_matrix_optimised.tex \
	$(ANALYSIS_GEN)/macros_exp2_matrix_arm3.tex \
	$(ANALYSIS_GEN)/macros_exp2_matrix_arm4.tex \
	$(ANALYSIS_EXP2_FONE_MACROS) \
	$(ANALYSIS_GEN)/macros_p1_base.tex \
	$(ANALYSIS_FUSION_MVP_MACROS) \
	$(ANALYSIS_GEN)/macros_longtail.tex \
	$(ANALYSIS_GEN)/macros_source_concordance.tex \
	$(ANALYSIS_EXP2_WIKI_MACROS) \
	$(ANALYSIS_EXP1_SCREEN_MACROS) \
	$(ANALYSIS_STATUS_DIFFICULTY_MACROS) \
	$(ANALYSIS_AGG_SWEEP_MACROS) \
	$(ANALYSIS_REFERENCE_MACROS)

# Duplicate-name guard: two fragments defining the same \newcommand would make
# tectonic fail with "Command \X already defined" — fail fast here instead,
# naming the duplicates. .DELETE_ON_ERROR (paths.mk) removes the partial file.
$(ANALYSIS_MANUSCRIPT_MACROS): $(MANUSCRIPT_MACRO_FRAGMENTS)
	@mkdir -p $(dir $@)
	{ echo '% Consolidated manuscript macros — generated by experiments/render.mk (ticket 0531).'; \
	  echo '% DO NOT EDIT — concatenation of the per-script fragments in MANUSCRIPT_MACRO_FRAGMENTS.'; \
	  echo '% Regenerate with: make -f experiments/render.mk report-tables'; \
	  cat $^; } > $@
	@dups=$$(grep -ho '\\newcommand{\\[A-Za-z]*}' $@ | sort | uniq -d); \
	if [ -n "$$dups" ]; then \
	  echo "ERROR: duplicate macro definitions in $@:"; \
	  echo "$$dups"; \
	  exit 1; \
	fi

.PHONY: manuscript-macros
manuscript-macros: $(ANALYSIS_MANUSCRIPT_MACROS)

# Grouping targets — drive end-to-end regeneration of report-side handoff
# artifacts. tab_self_consistency.tex and tab_per_run.tex are produced by the
# `self-consistency` verb above (single producer, 0354 → migrated here 0410).
#
# DESIGN: the prerequisite lists are held in variables (RENDER_REPORT_TABLES,
# RENDER_REPORT_FIGURES, RENDER_CHART_FIGURES) so the `clean` target below
# can source its deletion set from the same vars — no hand-listed rm paths
# that drift from the actual targets (ticket 0360).

RENDER_REPORT_TABLES := \
	$(ANALYSIS_GEN)/tab_decomposition.tex \
	$(ANALYSIS_GEN)/tab_decomposition_fix.tex \
	$(ANALYSIS_GEN)/tab_census.tex \
	$(ANALYSIS_GEN)/macros.tex \
	$(ANALYSIS_GEN)/macros_census.tex \
	$(ANALYSIS_GEN)/tab_relances.tex \
	$(ANALYSIS_EXP2_2X2_TEX) \
	$(ANALYSIS_GEN)/tab_comparaison.tex \
	$(ANALYSIS_GEN)/tab_variance.tex \
	$(ANALYSIS_GEN)/tab_verification.tex \
	$(ANALYSIS_GEN)/tab_coherence.tex \
	$(ANALYSIS_GEN)/tab_reconciliation.tex \
	$(ANALYSIS_GEN)/tab_converter_benchmark.tex \
	$(ANALYSIS_GEN)/tab_source_grounding.tex \
	$(ANALYSIS_GEN)/tab_status_difficulty.tex \
	$(ANALYSIS_GEN)/tab_status_difficulty_en.tex \
	$(ANALYSIS_GEN)/macros_source_concordance.tex \
	$(ANALYSIS_GEN)/tab_source_concordance.tex \
	$(ANALYSIS_GEN)/macros_phase_collisions.tex \
	$(ANALYSIS_WIKI_BAR_CSV) \
	$(ANALYSIS_EXP2_WIKI_CSV) \
	$(ANALYSIS_AGG_SWEEP_TEX) \
	$(ANALYSIS_AGG_SWEEP_MACROS) \
	$(ANALYSIS_STATUS_DIFFICULTY_MACROS) \
	$(ANALYSIS_REFERENCE_MACROS) \
	$(ANALYSIS_MANUSCRIPT_MACROS)

report-tables: $(RENDER_REPORT_TABLES)

RENDER_REPORT_FIGURES := \
	$(ANALYSIS_EXP1_SPIDER_FAMILIES) \
	$(ANALYSIS_EXP1_QUALITY_HEATMAP) \
	$(ANALYSIS_EXP1_RELIABILITY_FIG) \
	$(ANALYSIS_EXP1_RELIABILITY_SENS_CSV) \
	$(ANALYSIS_EXP1_RELIABILITY_SENS_TEX) \
	$(ANALYSIS_EXP1_SCREEN_VALID_CSV) \
	$(ANALYSIS_EXP1_SCREEN_MACROS) \
	$(ANALYSIS_EXP1_RUN_STATS_MACROS)

report-figures: $(RENDER_REPORT_FIGURES)

# --- Chart-data figures (migrated from root Makefile by 0370) -----------------
# These produce committed handoff artifacts consumed by both report and slides.
# The writing-side `make report` and `make slides` have no recipes for these
# outputs — they are clean-room builds from committed artifacts only.

# Exp1 cost × quality: the figure (plot_) emits only the PDF; the audit CSV is
# emitted by the table half (tabulate_). Both derive their rows from the shared
# aedist.exp1_cost_quality library — no figure-script side-output another rule
# consumes (ticket 0436).
$(ANALYSIS_GEN)/fig_direct_cost_quality.pdf: $(ANALYSIS_MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_cost_quality \
	    --figure $(ANALYSIS_GEN)/fig_direct_cost_quality.pdf

$(ANALYSIS_GEN)/cost_quality.csv: $(ANALYSIS_MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_cost_quality \
	    --output $(ANALYSIS_GEN)/cost_quality.csv

$(ANALYSIS_GEN)/fig_method_convergence.pdf: $(ANALYSIS_MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_method_convergence \
	    --output $@ --core-only

$(ANALYSIS_GEN)/fig_direct_p1_base.pdf $(ANALYSIS_GEN)/macros_p1_base.tex &: $(ANALYSIS_MEASUREMENTS) $(ANALYSIS_EXP1_BATCH2_RECORDS) $(ANALYSIS_CONCORDANCE_CSV)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_method_convergence \
	    --output $(ANALYSIS_GEN)/fig_direct_p1_base.pdf --methods direct \
	    --coverage-source wikipedia \
	    --label-x 100 --label-ha left \
	    --xlabel "Assets identified (1 dot = 1 power plant / project)" \
	    --fp-label "Unrecognized" \
	    --title "How do models recall Vietnam's thermal power assets? Not well." \
	    --ui-scale 1.35 \
	    --fig-width 12 --fig-height-min 8 --fig-height-per-run 0.06 --fig-height-per-method 0.35 \
	    --result-dir experiments/outputs/exp1_batch2/ \
	    --output-macros $(dir $@)macros_p1_base.tex
# --result-dir is a repo-root-relative constant, NOT $(ANALYSIS_EXPERIMENTS_DIR):
# record result_file paths are always stored repo-root-relative (loaded via the
# package-anchored measurements._REPO_ROOT, cwd-invariant), so the prefix filter
# must be too. Wiring it to ANALYSIS_EXPERIMENTS_DIR made the filter track cwd
# (./experiments/... under the default ANALYSIS_REPO_ROOT=.), failing the match →
# 0 rows → degenerate figure (ticket 0440; cf. exp1_cost_quality.EXP1_BATCH2_DIR).

# Exp1 recognition matrix (ticket 0373): plants aligned vertically on the
# reference list, plus a top-40 false-positive panel. Derives per-(run x plant)
# recognition from the records + reference via aedist.exp1_recognition (shared
# library; the status table 0434 derives the same data independently — no
# side-output). Emits a macros file for the caption's plant/run/FP counts.
$(ANALYSIS_GEN)/fig_exp1_recognition_matrix.pdf $(ANALYSIS_GEN)/macros_exp1_matrix.tex &: $(ANALYSIS_EXP1_BATCH2_RECORDS) $(ANALYSIS_EXPERT_REF) $(ANALYSIS_REPO_ROOT)/src/aedist/plot_exp1_matrix.py $(ANALYSIS_REPO_ROOT)/src/aedist/exp1_recognition.py $(ANALYSIS_REPO_ROOT)/src/aedist/plot_method_convergence.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp1_matrix \
	    --records-glob "$(ANALYSIS_EXPERIMENTS_DIR)/outputs/exp1_batch2/*.record.json" \
	    --reference $(ANALYSIS_EXPERT_REF) \
	    --output $(ANALYSIS_GEN)/fig_exp1_recognition_matrix.pdf \
	    --output-macros $(ANALYSIS_GEN)/macros_exp1_matrix.tex

# French-label landscape version (the unsuffixed PDF is English,
# preprint-first — author 2026-06-06: all preprint figures in English).
# No longer referenced by report.tex (the FR annex adopted the portrait
# variant, ticket 0503); kept as a standalone exploration artifact like
# the strong/top subsets below.
$(ANALYSIS_GEN)/fig_exp1_recognition_matrix_fr.pdf: $(ANALYSIS_EXP1_BATCH2_RECORDS) $(ANALYSIS_EXPERT_REF) $(ANALYSIS_REPO_ROOT)/src/aedist/plot_exp1_matrix.py $(ANALYSIS_REPO_ROOT)/src/aedist/exp1_recognition.py $(ANALYSIS_REPO_ROOT)/src/aedist/plot_method_convergence.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp1_matrix \
	    --records-glob "$(ANALYSIS_EXPERIMENTS_DIR)/outputs/exp1_batch2/*.record.json" \
	    --reference $(ANALYSIS_EXPERT_REF) \
	    --output $@ \
	    --lang fr

# Model-subset versions of the recognition matrix (0446, author observation 2):
# the FP top-40 and macros are recomputed for each cohort. `strong` drops the
# weakest models (haiku, both gpt-oss, the two small qwen3.6); `top` keeps only
# the strongest model of each architectural family. Exploration artifacts — not
# yet referenced by the manuscript or report.
$(ANALYSIS_GEN)/fig_exp1_recognition_matrix_strong.pdf: $(ANALYSIS_EXP1_BATCH2_RECORDS) $(ANALYSIS_EXPERT_REF) $(ANALYSIS_REPO_ROOT)/src/aedist/plot_exp1_matrix.py $(ANALYSIS_REPO_ROOT)/src/aedist/exp1_recognition.py $(ANALYSIS_REPO_ROOT)/src/aedist/plot_method_convergence.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp1_matrix \
	    --records-glob "$(ANALYSIS_EXPERIMENTS_DIR)/outputs/exp1_batch2/*.record.json" \
	    --reference $(ANALYSIS_EXPERT_REF) \
	    --output $@ \
	    --exclude-models claude-haiku-4.5 gpt-oss-120b gpt-oss-20b qwen3.6-flash qwen3.6-35b-a3b

$(ANALYSIS_GEN)/fig_exp1_recognition_matrix_top.pdf: $(ANALYSIS_EXP1_BATCH2_RECORDS) $(ANALYSIS_EXPERT_REF) $(ANALYSIS_REPO_ROOT)/src/aedist/plot_exp1_matrix.py $(ANALYSIS_REPO_ROOT)/src/aedist/exp1_recognition.py $(ANALYSIS_REPO_ROOT)/src/aedist/plot_method_convergence.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp1_matrix \
	    --records-glob "$(ANALYSIS_EXPERIMENTS_DIR)/outputs/exp1_batch2/*.record.json" \
	    --reference $(ANALYSIS_EXPERT_REF) \
	    --output $@ \
	    --models claude-opus-4.6 deepseek-v4-pro gpt-5.5 mistral-large-2512 qwen3.7-max

# Portrait (transposed) variant (ticket 0451): plant names on rows (legible at
# ≥7pt/row, measured at build time), runs as columns with 3-level hierarchical
# header (family / version / run). Multi-page PDF: page 1 = terminal+active
# (operational/retired/cancelled, 78 rows), page 2 = pipeline
# (proposed/planned/constructing, 98 rows), page 3 = top-40 FP panel.
# Exploration artifact — not yet placed in the manuscript; author orientation
# decision deferred (ticket 0451 exit criterion). The script imports
# _order_runs/_order_plants from plot_exp1_matrix, so both are prerequisites.
$(ANALYSIS_GEN)/fig_exp1_recognition_matrix_portrait.pdf: $(ANALYSIS_EXP1_BATCH2_RECORDS) $(ANALYSIS_EXPERT_REF) $(ANALYSIS_REPO_ROOT)/src/aedist/plot_exp1_matrix_portrait.py $(ANALYSIS_REPO_ROOT)/src/aedist/plot_exp1_matrix.py $(ANALYSIS_REPO_ROOT)/src/aedist/exp1_recognition.py $(ANALYSIS_REPO_ROOT)/src/aedist/plot_method_convergence.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp1_matrix_portrait \
	    --records-glob "$(ANALYSIS_EXPERIMENTS_DIR)/outputs/exp1_batch2/*.record.json" \
	    --reference $(ANALYSIS_EXPERT_REF) \
	    --output $@

# French-label portrait variant for the report annex (ticket 0503): status
# band labels in FR, page titles stay EN (matches the landscape `_fr`
# precedent — only band/margin labels are localised).
$(ANALYSIS_GEN)/fig_exp1_recognition_matrix_portrait_fr.pdf: $(ANALYSIS_EXP1_BATCH2_RECORDS) $(ANALYSIS_EXPERT_REF) $(ANALYSIS_REPO_ROOT)/src/aedist/plot_exp1_matrix_portrait.py $(ANALYSIS_REPO_ROOT)/src/aedist/plot_exp1_matrix.py $(ANALYSIS_REPO_ROOT)/src/aedist/exp1_recognition.py $(ANALYSIS_REPO_ROOT)/src/aedist/plot_method_convergence.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp1_matrix_portrait \
	    --records-glob "$(ANALYSIS_EXPERIMENTS_DIR)/outputs/exp1_batch2/*.record.json" \
	    --reference $(ANALYSIS_EXPERT_REF) \
	    --output $@ \
	    --lang fr

# Exp2 recognition matrices (ticket 0449): one matrix per arm (four figures),
# same layout as the Exp1 matrix (status group column bands, FP left panel).
# Derives per-(run x plant) recognition from the Exp2 mart JSONL + paired
# markdown report files via aedist.exp2_recognition (mart-layer loader; no
# P3->P3 side-output, rule 0436). Exploration artifacts — not yet referenced by
# the manuscript; author placement decision deferred.
# The plot scripts (exp2_recognition.py + plot_exp2_matrix.py) are prerequisites
# so a script edit re-triggers the build (mirrors the exp1 matrix rules).
$(ANALYSIS_GEN)/fig_exp2_recognition_matrix_naive.pdf $(ANALYSIS_GEN)/macros_exp2_matrix_naive.tex &: $(ANALYSIS_EXP2_MART_JSONL) $(ANALYSIS_EXPERT_REF) $(ANALYSIS_REPO_ROOT)/src/aedist/plot_exp2_matrix.py $(ANALYSIS_REPO_ROOT)/src/aedist/exp2_recognition.py $(ANALYSIS_REPO_ROOT)/src/aedist/extract.py $(ANALYSIS_REPO_ROOT)/src/aedist/plot_exp1_matrix.py $(ANALYSIS_REPO_ROOT)/src/aedist/plot_method_convergence.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp2_matrix \
	    --mart-jsonl $(ANALYSIS_EXP2_MART_JSONL) \
	    --reference $(ANALYSIS_EXPERT_REF) \
	    --arm naive \
	    --output $(ANALYSIS_GEN)/fig_exp2_recognition_matrix_naive.pdf \
	    --output-macros $(ANALYSIS_GEN)/macros_exp2_matrix_naive.tex

$(ANALYSIS_GEN)/fig_exp2_recognition_matrix_optimised.pdf $(ANALYSIS_GEN)/macros_exp2_matrix_optimised.tex &: $(ANALYSIS_EXP2_MART_JSONL) $(ANALYSIS_EXPERT_REF) $(ANALYSIS_REPO_ROOT)/src/aedist/plot_exp2_matrix.py $(ANALYSIS_REPO_ROOT)/src/aedist/exp2_recognition.py $(ANALYSIS_REPO_ROOT)/src/aedist/extract.py $(ANALYSIS_REPO_ROOT)/src/aedist/plot_exp1_matrix.py $(ANALYSIS_REPO_ROOT)/src/aedist/plot_method_convergence.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp2_matrix \
	    --mart-jsonl $(ANALYSIS_EXP2_MART_JSONL) \
	    --reference $(ANALYSIS_EXPERT_REF) \
	    --arm optimised \
	    --output $(ANALYSIS_GEN)/fig_exp2_recognition_matrix_optimised.pdf \
	    --output-macros $(ANALYSIS_GEN)/macros_exp2_matrix_optimised.tex

$(ANALYSIS_GEN)/fig_exp2_recognition_matrix_arm3.pdf $(ANALYSIS_GEN)/macros_exp2_matrix_arm3.tex &: $(ANALYSIS_EXP2_MART_JSONL) $(ANALYSIS_EXPERT_REF) $(ANALYSIS_REPO_ROOT)/src/aedist/plot_exp2_matrix.py $(ANALYSIS_REPO_ROOT)/src/aedist/exp2_recognition.py $(ANALYSIS_REPO_ROOT)/src/aedist/extract.py $(ANALYSIS_REPO_ROOT)/src/aedist/plot_exp1_matrix.py $(ANALYSIS_REPO_ROOT)/src/aedist/plot_method_convergence.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp2_matrix \
	    --mart-jsonl $(ANALYSIS_EXP2_MART_JSONL) \
	    --reference $(ANALYSIS_EXPERT_REF) \
	    --arm arm3 \
	    --output $(ANALYSIS_GEN)/fig_exp2_recognition_matrix_arm3.pdf \
	    --output-macros $(ANALYSIS_GEN)/macros_exp2_matrix_arm3.tex

$(ANALYSIS_GEN)/fig_exp2_recognition_matrix_arm4.pdf $(ANALYSIS_GEN)/macros_exp2_matrix_arm4.tex &: $(ANALYSIS_EXP2_MART_JSONL) $(ANALYSIS_EXPERT_REF) $(ANALYSIS_REPO_ROOT)/src/aedist/plot_exp2_matrix.py $(ANALYSIS_REPO_ROOT)/src/aedist/exp2_recognition.py $(ANALYSIS_REPO_ROOT)/src/aedist/extract.py $(ANALYSIS_REPO_ROOT)/src/aedist/plot_exp1_matrix.py $(ANALYSIS_REPO_ROOT)/src/aedist/plot_method_convergence.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp2_matrix \
	    --mart-jsonl $(ANALYSIS_EXP2_MART_JSONL) \
	    --reference $(ANALYSIS_EXPERT_REF) \
	    --arm arm4 \
	    --output $(ANALYSIS_GEN)/fig_exp2_recognition_matrix_arm4.pdf \
	    --output-macros $(ANALYSIS_GEN)/macros_exp2_matrix_arm4.tex

# Exp1 status difficulty table (ticket 0434): reference-list composition by
# status vs mean recognition rate. Annex companion to the matrix figure above;
# derives the same per-(run x plant) recognition independently from the records
# + reference via aedist.exp1_recognition (shared library, no side-output). The
# status group order is shared with the matrix's column bands. The manuscript
# macros (proposed share/rate, overall rate, status accuracy excluding the
# proposed stratum) come from the same single pass (grouped &: rule, 0531).
$(ANALYSIS_GEN)/tab_status_difficulty.tex $(ANALYSIS_GEN)/tab_status_difficulty_en.tex $(ANALYSIS_STATUS_DIFFICULTY_MACROS) &: $(ANALYSIS_EXP1_BATCH2_RECORDS) $(ANALYSIS_EXPERT_REF) $(ANALYSIS_REPO_ROOT)/src/aedist/tabulate_status_difficulty.py $(ANALYSIS_REPO_ROOT)/src/aedist/exp1_recognition.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_status_difficulty \
	    --records-glob "$(ANALYSIS_EXPERIMENTS_DIR)/outputs/exp1_batch2/*.record.json" \
	    --reference $(ANALYSIS_EXPERT_REF) \
	    --output $(ANALYSIS_GEN)/tab_status_difficulty.tex \
	    --output-body-en $(ANALYSIS_GEN)/tab_status_difficulty_en.tex \
	    --output-macros $(ANALYSIS_STATUS_DIFFICULTY_MACROS)

# Source concordance (ticket 0486): reference vs GEM + Wikipedia, bidirectional
# by status. One invocation co-produces the headline macros (this target), the
# per-status CSV ($(ANALYSIS_CONCORDANCE_CSV)), and the annex table body that
# main.tex \inputs; all three are committed. Reads the reference, GEM, and the
# two cached Wikipedia wikitext snapshots; denominator via
# reference_plant_count() (no hardcoded count).
$(ANALYSIS_GEN)/macros_source_concordance.tex $(ANALYSIS_CONCORDANCE_CSV) \
		$(ANALYSIS_GEN)/tab_source_concordance.tex &: \
		$(ANALYSIS_EXPERT_REF) $(ANALYSIS_GEM_REF) $(ANALYSIS_WIKI_COAL) $(ANALYSIS_WIKI_POWER) \
		$(ANALYSIS_REPO_ROOT)/src/aedist/tabulate_source_concordance.py \
		$(ANALYSIS_REPO_ROOT)/src/aedist/exp1_recognition.py \
		$(ANALYSIS_REPO_ROOT)/src/aedist/reconcile.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_source_concordance \
	    --csv $(ANALYSIS_CONCORDANCE_CSV) \
	    --macros $(ANALYSIS_GEN)/macros_source_concordance.tex \
	    --table $(ANALYSIS_GEN)/tab_source_concordance.tex

# Matcher phase-collision exposure (ticket 0544): structural false-match set
# of the partial_ratio threshold on the reference (raw exposure / veto-blocked
# / residual), plus realised sensitivity from the committed threshold sweep.
# One invocation co-produces the per-pair CSV and the headline macros; both
# are committed (the manuscript \inputs the macros, so the rule re-runs when
# the script or its data inputs change).
$(ANALYSIS_GEN)/tab_phase_collisions.csv \
$(ANALYSIS_GEN)/macros_phase_collisions.tex &: \
		$(ANALYSIS_EXPERT_REF) \
		$(ANALYSIS_REPO_ROOT)/src/aedist/analyze_matcher_phase_collisions.py \
		$(ANALYSIS_REPO_ROOT)/src/aedist/evaluate.py \
		$(ANALYSIS_REPO_ROOT)/src/aedist/matching/lp.py \
		$(ANALYSIS_REPO_ROOT)/src/aedist/reconcile.py \
		$(ANALYSIS_DERIVED_DIR)/matching_sensitivity.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.analyze_matcher_phase_collisions \
	    --reference $(ANALYSIS_EXPERT_REF) \
	    --sensitivity $(ANALYSIS_DERIVED_DIR)/matching_sensitivity.csv \
	    --output-csv $(ANALYSIS_GEN)/tab_phase_collisions.csv \
	    --output-macros $(ANALYSIS_GEN)/macros_phase_collisions.tex

# Wikipedia recall bar (ticket 0494): per-raw-status seeded-ceiling coverage.
# Shares the matcher/fold machinery with the concordance script (imported), so
# both scripts are honest prerequisites. Distinct artifact from the 0486
# concordance by design: seeded derivative (contamination-aware recall bar),
# not independent reproduction.
$(ANALYSIS_WIKI_BAR_CSV): $(ANALYSIS_EXPERT_REF) $(ANALYSIS_WIKI_COAL) $(ANALYSIS_WIKI_POWER) \
		$(ANALYSIS_REPO_ROOT)/src/aedist/tabulate_wikipedia_recall_bar.py \
		$(ANALYSIS_REPO_ROOT)/src/aedist/tabulate_source_concordance.py \
		$(ANALYSIS_REPO_ROOT)/src/aedist/reconcile.py
	uv run python -m aedist.tabulate_wikipedia_recall_bar --output $@

# Long-tail recognition (tickets 0514, 0537). Two one-output rules:
#   (1) the per-plant layer CSV — the slow LP-reconciliation derivation, shared
#       with the concordance script's fold/reconcile machinery (imported), plus
#       the name-only OSM presence check; reads reference + GEM + Wikipedia
#       snapshots + OSM extract + those scripts.
#   (2) the PDF — renders FROM the committed CSV (--from-csv), so its only data
#       prerequisite is the CSV (plus the plot script). Caption counts are
#       re-derived from the CSV by the plot script (derive-prose rule).
$(ANALYSIS_LONGTAIL_CSV): $(ANALYSIS_EXPERT_REF) \
		$(ANALYSIS_GEM_REF) $(ANALYSIS_WIKI_COAL) $(ANALYSIS_WIKI_POWER) \
		$(ANALYSIS_OSM_CSV) \
		$(ANALYSIS_REPO_ROOT)/src/aedist/plot_longtail_recognition.py \
		$(ANALYSIS_REPO_ROOT)/src/aedist/tabulate_source_concordance.py \
		$(ANALYSIS_REPO_ROOT)/src/aedist/reconcile.py
	uv run python -m aedist.plot_longtail_recognition --csv-only \
	    --reference $(ANALYSIS_EXPERT_REF) --gem $(ANALYSIS_GEM_REF) \
	    --osm "$(ANALYSIS_REPO_ROOT)/data/reference/OSM fetch/vn_power_plants.csv" \
	    --csv $@

$(ANALYSIS_GEN)/fig_longtail_recognition.pdf $(ANALYSIS_GEN)/macros_longtail.tex &: \
		$(ANALYSIS_LONGTAIL_CSV) \
		$(ANALYSIS_REPO_ROOT)/src/aedist/plot_longtail_recognition.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_longtail_recognition --from-csv \
	    --csv $(ANALYSIS_LONGTAIL_CSV) \
	    --output $(ANALYSIS_GEN)/fig_longtail_recognition.pdf \
	    --output-macros $(ANALYSIS_GEN)/macros_longtail.tex

# Interactive recognition matrix (ticket 0450): dev-tool HTML for LP matcher
# QA — hover any cell to see the reference-vs-reply comparison table.  Output
# is gitignored (nothing downstream consumes it); not in RENDER_CHART_FIGURES.
# One output per rule (single HTML), DAG-wired to records + reference + scripts.
$(ANALYSIS_GEN)/exp1_recognition_matrix_interactive.html: $(ANALYSIS_EXP1_BATCH2_RECORDS) $(ANALYSIS_EXPERT_REF) $(ANALYSIS_REPO_ROOT)/src/aedist/plot_exp1_matrix_interactive.py $(ANALYSIS_REPO_ROOT)/src/aedist/exp1_recognition.py $(ANALYSIS_REPO_ROOT)/src/aedist/plot_exp1_matrix.py $(ANALYSIS_REPO_ROOT)/src/aedist/plot_method_convergence.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp1_matrix_interactive \
	    --records-glob "$(ANALYSIS_EXPERIMENTS_DIR)/outputs/exp1_batch2/*.record.json" \
	    --reference $(ANALYSIS_EXPERT_REF) \
	    --output $@

$(ANALYSIS_GEN)/fig_regimes_scatter.pdf: $(ANALYSIS_MEASUREMENTS) $(ANALYSIS_EXPERIMENTS_DIR)/figures.toml
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_regimes_scatter \
	    --output $@

$(ANALYSIS_GEN)/fig_scaling_curve.pdf: $(ANALYSIS_MEASUREMENTS)
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

RENDER_CHART_FIGURES := \
	$(ANALYSIS_GEN)/fig_direct_cost_quality.pdf \
	$(ANALYSIS_GEN)/cost_quality.csv \
	$(ANALYSIS_GEN)/fig_direct_p1_base.pdf \
	$(ANALYSIS_GEN)/macros_p1_base.tex \
	$(ANALYSIS_GEN)/fig_exp1_recognition_matrix.pdf \
	$(ANALYSIS_GEN)/macros_exp1_matrix.tex \
	$(ANALYSIS_GEN)/fig_exp1_recognition_matrix_fr.pdf \
	$(ANALYSIS_GEN)/fig_exp1_recognition_matrix_strong.pdf \
	$(ANALYSIS_GEN)/fig_exp1_recognition_matrix_top.pdf \
	$(ANALYSIS_GEN)/fig_exp1_recognition_matrix_portrait.pdf \
	$(ANALYSIS_GEN)/fig_exp1_recognition_matrix_portrait_fr.pdf \
	$(ANALYSIS_GEN)/fig_exp2_recognition_matrix_naive.pdf \
	$(ANALYSIS_GEN)/macros_exp2_matrix_naive.tex \
	$(ANALYSIS_GEN)/fig_exp2_recognition_matrix_optimised.pdf \
	$(ANALYSIS_GEN)/macros_exp2_matrix_optimised.tex \
	$(ANALYSIS_GEN)/fig_exp2_recognition_matrix_arm3.pdf \
	$(ANALYSIS_GEN)/macros_exp2_matrix_arm3.tex \
	$(ANALYSIS_GEN)/fig_exp2_recognition_matrix_arm4.pdf \
	$(ANALYSIS_GEN)/macros_exp2_matrix_arm4.tex \
	$(ANALYSIS_GEN)/fig_capability_timeline.pdf \
	$(ANALYSIS_GEN)/fig_capability_dag.pdf \
	$(ANALYSIS_GEN)/fig_spider_cross_exp.pdf \
	$(ANALYSIS_EXP1_SPIDER_FAMILIES) \
	$(ANALYSIS_EXP1_SPIDER_FAMILIES_FR) \
	$(ANALYSIS_EXP1_QUALITY_HEATMAP) \
	$(ANALYSIS_GEN)/fig_method_convergence.pdf \
	$(ANALYSIS_GEN)/fig_regimes_scatter.pdf \
	$(ANALYSIS_GEN)/fig_scaling_curve.pdf \
	$(ANALYSIS_GROUNDING_LADDER_FIG) \
	$(ANALYSIS_FUSION_MVP_CSV) \
	$(ANALYSIS_FUSION_MVP_MACROS) \
	$(ANALYSIS_FUSION_MVP_FIG) \
	$(ANALYSIS_LONGTAIL_CSV) \
	$(ANALYSIS_GEN)/fig_longtail_recognition.pdf \
	$(ANALYSIS_GEN)/macros_longtail.tex

chart-figures: $(RENDER_CHART_FIGURES)

# --- Full-phase aggregate (P3 render surface) -------------------------------
# `all` rebuilds every committed handoff artifact this phase produces, so the
# root `world`/`staleness` entries (tracker 0406 S5, ticket 0415) drive the
# whole P3 surface through one recursive `-f render.mk all` delegation. It is
# the UNION of every P3 grouping target — dropping any member would silently
# omit those figures/tables from a "full" rebuild. Consumes committed P2
# outcomes as sources only (clean-room: no scoring/extraction here, guarded by
# tests/test_render_build_clean_room.py).
.PHONY: all
all: report-tables report-figures chart-figures self-consistency \
	exp1-cost-summary exp1-reasoning-topup \
	exp2-analysis-report exp1-analysis-figures

# --- Clean: remove all P3 render outputs (ticket 0360) ----------------------
# The deletion set is sourced from the SAME variables used by the grouping
# targets above — never a hand-listed glob that could drift from actual
# targets and delete an artifact without a rule. (tab_decomposition_fix.tex
# was such a FROZEN case until ticket 0424 restored its producer rule; it is
# now a regular RENDER_REPORT_TABLES member.) Also removes P3-internal intermediates
# (variance_decomposition.json, tradeoff.csv) whose only consumers are render
# targets; they are NOT P2 outcomes (those never get cleaned — see ticket body).
#
# Post-clean oracle: make -f experiments/render.mk all && git diff --exit-code
# A non-empty diff means a committed handoff artifact is out of sync with
# the data (timestamp-gated world misses this because it sees existing files as
# up-to-date; forcing regeneration reveals the divergence).
#
# Usage:
#   make -f experiments/render.mk clean   # P3 clean alone
#   make cleaner                          # root entry: P3 clean + oracle check

# (Reuse the grouping-target vars — clean set stays in sync with all targets.)
RENDER_EXP2_ANALYSIS := $(RENDER_EXP2_ANALYSIS_REPORT)
RENDER_EXP1_ANALYSIS := $(RENDER_EXP1_ANALYSIS_FIGURES)

RENDER_SELF_CONSISTENCY := $(ANALYSIS_SC_TEX) $(ANALYSIS_SC_PERRUN)

RENDER_EXP1_EXTRAS := $(ANALYSIS_EXP1_COST_TEX) $(ANALYSIS_EXP1_TOPUP_TEX)

# P3-internal intermediates: produced by render.mk rules, consumed only by
# later render.mk rules — not P2 outcomes (no rule in score.mk produces them).
# Also includes ANALYSIS_EXP2_2X2_CSV, which lives under ANALYSIS_DERIVED_DIR
# (not ANALYSIS_GEN) but is a P3 render output produced by the 2x2 table rule.
RENDER_INTERMEDIATES := \
	$(ANALYSIS_VARIANCE_JSON) \
	$(ANALYSIS_VERIFICATION_TRADEOFF) \
	$(ANALYSIS_EXP2_2X2_CSV) \
	$(ANALYSIS_REF_COUNT_CSV) \
	$(ANALYSIS_EXP2_WIKI_MACROS)

RENDER_CLEAN_FILES := \
	$(RENDER_REPORT_TABLES) \
	$(RENDER_REPORT_FIGURES) \
	$(RENDER_CHART_FIGURES) \
	$(RENDER_EXP2_ANALYSIS) \
	$(RENDER_EXP1_ANALYSIS) \
	$(RENDER_SELF_CONSISTENCY) \
	$(RENDER_EXP1_EXTRAS) \
	$(RENDER_INTERMEDIATES)

.PHONY: clean
clean:
	@echo 'render.mk clean: removing P3 render outputs (keeping P2 sources: measurements.jsonl, mart, cross-eval CSVs)'
	rm -f $(RENDER_CLEAN_FILES)
