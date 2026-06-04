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
ANALYSIS_EXP2_COVERAGE_FIG := $(ANALYSIS_GEN)/fig_exp2_coverage_certainty.pdf
ANALYSIS_EXP2_SPIRE_FIG := $(ANALYSIS_GEN)/fig_quality_spider.pdf
ANALYSIS_EXP2_2X2_CSV := $(ANALYSIS_DERIVED_DIR)/tab_exp2_2x2.csv
ANALYSIS_EXP2_2X2_TEX := $(ANALYSIS_GEN)/tab_exp2_2x2.tex
ANALYSIS_EXP2_2X2_FR_TEX := $(ANALYSIS_GEN)/tab_exp2_2x2_fr.tex
ANALYSIS_EXP2_COVERAGE_SPLIT := $(ANALYSIS_GEN)/fig_exp2_coverage.pdf
ANALYSIS_EXP2_COST_SPLIT := $(ANALYSIS_GEN)/fig_exp2_cost.pdf
ANALYSIS_SLIDE_MACROS := $(ANALYSIS_GEN)/macros_slides.tex

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

# Report-side (measurements/mart-derived) P3 inputs and intermediates.
# ANALYSIS_MEASUREMENTS is defined in paths.mk (shared P2 outcome, now produced
# by score.mk and consumed here as a source).
ANALYSIS_EXP1_BATCH2_RECORDS := $(wildcard $(ANALYSIS_EXPERIMENTS_DIR)/outputs/exp1_batch2/*.record.json)

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
$(ANALYSIS_EXP1_SPIDER_FAMILIES): $(ANALYSIS_EXP1_CROSS_EVAL_CSV)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_quality_spider_exp1 \
	    --input $(ANALYSIS_EXP1_CROSS_EVAL_CSV) \
	    --output $@

$(ANALYSIS_EXP1_SPIDER_CLAUDE): $(ANALYSIS_EXP1_CROSS_EVAL_CSV)
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
# Reads the committed cross-eval CSV (P2 source) and the flat arm dirs (P1
# source); produces nothing under P2 outcome paths.
$(ANALYSIS_EXP2_2X2_TEX): $(ANALYSIS_EXP2_CROSS_EVAL_CSV)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_2x2 \
	    --cross-eval-csv $(ANALYSIS_EXP2_CROSS_EVAL_CSV) \
	    --flat-root $(ANALYSIS_DERIVED_DIR) \
	    --output-csv $(ANALYSIS_EXP2_2X2_CSV) \
	    --output-tex $@ --lang en

$(ANALYSIS_EXP2_2X2_FR_TEX): $(ANALYSIS_EXP2_CROSS_EVAL_CSV)
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

# --- Slide macros (census + measurements → report/inputs/generated/macros_slides.tex) ---

$(ANALYSIS_SLIDE_MACROS): $(ANALYSIS_GEN)/census_bars.csv $(ANALYSIS_MEASUREMENTS)
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
#     make -f experiments/render.mk report-tables report-figures

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

# Grouping targets — drive end-to-end regeneration of report-side handoff
# artifacts. tab_self_consistency.tex and tab_per_run.tex are produced by the
# `self-consistency` verb above (single producer, 0354 → migrated here 0410).
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

$(ANALYSIS_GEN)/fig_method_convergence.pdf: $(ANALYSIS_MEASUREMENTS)
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

chart-figures: \
	$(ANALYSIS_GEN)/census_bars.csv \
	$(ANALYSIS_GEN)/fig_direct_cost_quality.pdf \
	$(ANALYSIS_GEN)/fig_direct_p1_base.pdf \
	$(ANALYSIS_GEN)/fig_capability_timeline.pdf \
	$(ANALYSIS_GEN)/fig_capability_dag.pdf \
	$(ANALYSIS_GEN)/fig_spider_cross_exp.pdf \
	$(ANALYSIS_EXP1_SPIDER_FAMILIES) \
	$(ANALYSIS_GEN)/fig_method_convergence.pdf \
	$(ANALYSIS_GEN)/fig_regimes_scatter.pdf \
	$(ANALYSIS_GEN)/fig_scaling_curve.pdf

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
