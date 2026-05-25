# AEDIST Technical Report — Root Makefile
#
# Complete DAG: `make report` or `make slides` pulls all dependencies.
#
#   report.pdf ← tab_census.tex, macros.tex ← measurements.jsonl
#   slides.pdf ← fig_direct_p1_base.pdf, cost_quality.csv ← measurements.jsonl

MEASUREMENTS := measurements.jsonl
GEN          := report/inputs/generated
SLIDE_GEN    := slides/inputs/generated

include report/exp2-analysis.mk

.PHONY: test test-fast lint check-fast check census census-summary show-prompts

# --- Tests --------------------------------------------------------------------

test-fast:
	uv run pytest -m "not integration and not slow"

test:
	uv run pytest

lint:
	uv run ruff check src/ tests/ scripts/
	uv run python scripts/check_ticket_structure.py

check-fast: test-fast lint

check: test lint

# --- Prompt inspection -------------------------------------------------------

show-prompts:
	@uv run python -c "\
	from aedist.harness import assemble_prompt; \
	from pathlib import Path; \
	d = Path('experiments/prompts/modules'); \
	ALL = ['persona','overview','sourcing','narratives','bibliography','statistics']; \
	configs = [('base', []), ('composite', ALL)] + [(m, [m]) for m in ALL]; \
	[print(f'=== {n} ({len(assemble_prompt(d,ms).split(chr(10)))} lines) ===\n{assemble_prompt(d,ms)}\n') for n,ms in configs]"

# --- Measurements (materialized view of all outputs) -------------------------
#
# measurements.jsonl is rebuilt from all experiments/outputs/*/ by:
#   1. Extracting CSVs from structured conditions (extract.py)
#   2. Evaluating each CSV against reference (evaluate.py evaluate)
#   3. Assembling record JSONs into measurements.jsonl (evaluate.py assemble)

$(MEASUREMENTS): $(wildcard experiments/outputs/*/*.json) $(wildcard experiments/outputs/*/*.csv)
	$(MAKE) -C experiments ../measurements.jsonl

.PHONY: measurements
measurements: $(MEASUREMENTS)

# --- Model selection ----------------------------------------------------------

experiments/models_selected.yaml: $(MEASUREMENTS) experiments/models.yaml
	uv run python -m aedist.select_models \
	    --registry experiments/models.yaml \
	    --output $@ --n 1

# --- Tables for report --------------------------------------------------------

$(GEN)/tab_census.tex: $(MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_census --output $@

P1_BASE_RECORDS := $(wildcard experiments/outputs/ablation/direct/p1_base/*.record.json)

$(GEN)/tab_base_vs_census.tex: $(MEASUREMENTS) $(P1_BASE_RECORDS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_base_vs_census --output $@

DECOMP_BEFORE := $(wildcard experiments/outputs/rag_per_fuel/reconciliation_*.csv)
DECOMP_AFTER := $(wildcard experiments/outputs/rag_per_fuel_v2/reconciliation_*.csv)

$(GEN)/tab_decomposition_fix.tex: $(DECOMP_BEFORE) $(DECOMP_AFTER)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_decomposition_fix --output $@

$(GEN)/tab_self_consistency.tex $(GEN)/tab_per_run.tex &: $(MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_self_consistency \
	    --output $(GEN)/tab_self_consistency.tex \
	    --per-run-output $(GEN)/tab_per_run.tex

RAG_CSVS := $(wildcard experiments/outputs/rag_extract/*.csv)

$(GEN)/tab_coherence.tex: $(RAG_CSVS) src/aedist/tabulate_coherence.py src/aedist/coherence.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_coherence \
	    --input experiments/outputs/rag_extract --output $@

$(GEN)/fig_base_vs_census.pdf: $(MEASUREMENTS) $(P1_BASE_RECORDS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_base_vs_census --output $@

$(GEN)/macros.tex: $(MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_macros --output $@

$(GEN)/tab_relances.tex: $(MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_relances --output $@

$(GEN)/tab_comparaison.tex: $(MEASUREMENTS) derived/variance_decomposition.json
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_comparaison --output $@ --variance-json derived/variance_decomposition.json

EXPERT_REF := data/reference/vietnam_thermal_v1.csv
GEM_REF    := data/reference/gem_thermal.csv

$(GEN)/tab_reconciliation.tex: $(MEASUREMENTS) $(EXPERT_REF) $(GEM_REF)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_reconciliation --output $@ --expert-ref $(EXPERT_REF) --gem-ref $(GEM_REF)

derived/variance_decomposition.json: $(MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.variance_decomposition --output $@

$(GEN)/tab_variance.tex: derived/variance_decomposition.json
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_variance --input $< --output $@

CONVERTER_TEST := experiments/data/converter_test
CONVERTER_META := $(CONVERTER_TEST)/benchmark_meta.yaml
CONVERTER_DOCS := $(wildcard $(CONVERTER_TEST)/*/Decision-1509.md)

derived/verification/tradeoff.csv: $(wildcard derived/verification/*-run*.csv)
	uv run python -m aedist.tabulate_verification \
	    --input derived/verification --output $@

$(GEN)/tab_verification.tex: derived/verification/tradeoff.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_verification \
	    --input derived/verification --latex $@

$(GEN)/tab_converter_benchmark.tex: $(CONVERTER_META) $(CONVERTER_DOCS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.compare_converters \
	    --input $(CONVERTER_TEST) --meta $(CONVERTER_META) --output $@

# --- Chart data (report canonical; slides references ../report/inputs/generated/) ---

$(GEN)/census_bars.csv: $(MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_census --output $@

$(GEN)/fig_direct_cost_quality.pdf: $(MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_cost_quality \
	    --output $(GEN)/cost_quality.csv --figure $@

$(SLIDE_GEN)/regimes.csv: $(GEN)/regimes.csv
	@mkdir -p $(dir $@)
	cp $< $@

$(SLIDE_GEN)/fig_method_convergence.pdf: $(MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_method_convergence \
	    --output $@ --core-only

$(GEN)/fig_census_direct.pdf: $(MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_method_convergence \
	    --output $@ --methods direct --prompt-version census \
	    --output-macros $(dir $@)macros_census.tex

EXP1_BATCH2_RECORDS := $(wildcard experiments/outputs/exp1_batch2/*.record.json)

$(GEN)/fig_direct_p1_base.pdf: $(MEASUREMENTS) $(EXP1_BATCH2_RECORDS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_method_convergence \
	    --output $@ --methods direct \
	    --result-dir experiments/outputs/exp1_batch2/ \
	    --output-macros $(dir $@)macros_p1_base.tex

$(SLIDE_GEN)/fig_regimes_scatter.pdf: $(MEASUREMENTS) experiments/figures.toml
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_regimes_scatter \
	    --output $@

$(SLIDE_GEN)/fig_scaling_curve.pdf: $(MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_scaling_curve \
	    --output $@

$(GEN)/fig_ablation_strip.pdf: $(MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_ablation --strip $@

$(SLIDE_GEN)/fig_ablation_strip.pdf: $(GEN)/fig_ablation_strip.pdf
	@mkdir -p $(dir $@)
	cp $< $@

$(GEN)/fig_ablation_heatmap.pdf: $(MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_ablation --heatmap $@

$(GEN)/fig_capability_timeline.pdf: data/capability_timeline.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_capability_timeline \
	    --input $< --output $@

$(GEN)/fig_capability_dag.pdf: data/capability_timeline.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_capability_dag \
	    --input $< --output $@

$(SLIDE_GEN)/macros.tex: $(GEN)/census_bars.csv $(MEASUREMENTS)
	uv run python -m aedist.tabulate_macros --census-csv $< --output $@

# --- Publications -------------------------------------------------------------

report/report.pdf: report/report.tex report/refs.bib \
    $(GEN)/tab_census.tex $(GEN)/macros.tex \
	$(GEN)/tab_relances.tex $(GEN)/tab_exp2_arms.tex $(GEN)/tab_comparaison.tex \
    $(GEN)/tab_variance.tex $(GEN)/tab_verification.tex \
	$(GEN)/fig_quality_spider.pdf \
    $(GEN)/fig_census_direct.pdf \
    $(GEN)/tab_base_vs_census.tex $(GEN)/fig_base_vs_census.pdf \
    $(GEN)/tab_decomposition_fix.tex \
    $(GEN)/tab_self_consistency.tex $(GEN)/tab_per_run.tex \
    $(GEN)/tab_coherence.tex \
    $(GEN)/tab_reconciliation.tex \
    $(GEN)/fig_ablation_strip.pdf $(GEN)/fig_ablation_heatmap.pdf
	$(MAKE) -C report

slides/slides.pdf: slides/slides.tex \
    $(GEN)/census_bars.csv $(GEN)/fig_direct_cost_quality.pdf \
    $(SLIDE_GEN)/regimes.csv $(GEN)/fig_direct_p1_base.pdf \
    $(GEN)/macros_p1_base.tex \
    $(SLIDE_GEN)/fig_method_convergence.pdf \
    $(SLIDE_GEN)/fig_regimes_scatter.pdf \
    $(SLIDE_GEN)/fig_scaling_curve.pdf \
    $(SLIDE_GEN)/fig_ablation_strip.pdf \
    $(SLIDE_GEN)/macros.tex
	$(MAKE) -C slides

# --- Convenience aliases ------------------------------------------------------

.PHONY: report slides tables figures select

report: report/report.pdf
slides: slides/slides.pdf
tables: $(GEN)/tab_census.tex $(GEN)/macros.tex $(GEN)/tab_relances.tex $(GEN)/tab_exp2_arms.tex $(GEN)/tab_comparaison.tex $(GEN)/tab_converter_benchmark.tex $(GEN)/tab_variance.tex $(GEN)/tab_verification.tex $(GEN)/tab_base_vs_census.tex $(GEN)/tab_decomposition_fix.tex $(GEN)/tab_self_consistency.tex $(GEN)/tab_per_run.tex $(GEN)/tab_coherence.tex $(GEN)/tab_reconciliation.tex
figures: $(GEN)/census_bars.csv $(GEN)/fig_direct_cost_quality.pdf $(GEN)/fig_direct_p1_base.pdf $(GEN)/fig_census_direct.pdf $(SLIDE_GEN)/fig_method_convergence.pdf $(SLIDE_GEN)/fig_regimes_scatter.pdf $(SLIDE_GEN)/fig_scaling_curve.pdf $(GEN)/fig_base_vs_census.pdf $(SLIDE_GEN)/fig_ablation_strip.pdf $(GEN)/fig_ablation_strip.pdf $(GEN)/fig_ablation_heatmap.pdf
select: experiments/models_selected.yaml
census:
	$(MAKE) -C experiments census
