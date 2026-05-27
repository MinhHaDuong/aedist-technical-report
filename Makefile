# AEDIST Technical Report — Root Makefile
#
# Complete DAG: `make report` or `make slides` pulls all dependencies.
#
#   report.pdf ← tab_census.tex, macros.tex ← measurements.jsonl
#   slides.pdf ← fig_direct_p1_base.pdf, cost_quality.csv ← measurements.jsonl

MEASUREMENTS := measurements.jsonl
GEN          := report/inputs/generated
SLIDE_GEN    := slides/inputs/generated

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

DECOMP_BEFORE := $(wildcard experiments/outputs/rag_per_fuel/reconciliation_*.csv)
DECOMP_AFTER := $(wildcard experiments/outputs/rag_per_fuel_v2/reconciliation_*.csv)

$(GEN)/tab_decomposition_fix.tex: $(DECOMP_BEFORE) $(DECOMP_AFTER)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_decomposition_fix --output $@

# tab_self_consistency.tex / tab_per_run.tex are produced by the analysis
# workpackage (experiments/Makefile `self-consistency`) and consumed here as
# committed handoff artifacts — single producer, see ticket 0354.

RAG_CSVS := $(wildcard experiments/outputs/rag_extract/*.csv)

$(GEN)/tab_coherence.tex: $(RAG_CSVS) src/aedist/tabulate_coherence.py src/aedist/coherence.py
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_coherence \
	    --input experiments/outputs/rag_extract --output $@

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

# Produces macros_census.tex (consumed by slides via \NumCensusModels); the
# census figure itself was retired with the ablation thread (ticket 0361).
# Full producer migration is 0352.
$(GEN)/fig_census_direct.pdf $(GEN)/macros_census.tex &: $(MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_method_convergence \
	    --output $(GEN)/fig_census_direct.pdf --methods direct --prompt-version census \
	    --output-macros $(GEN)/macros_census.tex

EXP1_BATCH2_RECORDS := $(wildcard experiments/outputs/exp1_batch2/*.record.json)

$(GEN)/fig_direct_p1_base.pdf $(GEN)/macros_p1_base.tex &: $(MEASUREMENTS) $(EXP1_BATCH2_RECORDS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_method_convergence \
	    --output $(GEN)/fig_direct_p1_base.pdf --methods direct \
	    --label-x 100 --label-ha left \
	    --xlabel "Assets identified (1 dot = 1 power plant / project)" \
	    --title "How do models recall Vietnam's thermal power assets? Not well." \
	    --ui-scale 1.35 \
	    --fig-width 12 --fig-height-min 8 --fig-height-per-run 0.06 --fig-height-per-method 0.35 \
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

$(GEN)/fig_capability_timeline.pdf: data/capability_timeline.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_capability_timeline \
	    --input $< --output $@

$(GEN)/fig_capability_dag.pdf: data/capability_timeline.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_capability_dag \
	    --input $< --output $@

$(GEN)/fig_spider_cross_exp.pdf: experiments/derived/exp1_cross_eval.csv experiments/derived/sota_cross_eval.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_spider_cross_exp \
	    --exp1 experiments/derived/exp1_cross_eval.csv \
	    --exp2 experiments/derived/sota_cross_eval.csv \
	    --output $@

# --- Publications -------------------------------------------------------------

report/report.pdf: report/report.tex report/refs.bib \
    $(GEN)/tab_census.tex $(GEN)/macros.tex \
	$(GEN)/tab_relances.tex $(GEN)/tab_exp2_2x2.tex $(GEN)/tab_comparaison.tex \
    $(GEN)/tab_variance.tex $(GEN)/tab_verification.tex \
		$(GEN)/fig_spider_exp1_families.pdf \
    $(GEN)/tab_decomposition_fix.tex \
    $(GEN)/tab_self_consistency.tex $(GEN)/tab_per_run.tex \
    $(GEN)/tab_coherence.tex \
    $(GEN)/tab_reconciliation.tex
	$(MAKE) -C report

slides/slides.pdf: slides/slides.tex \
    $(GEN)/fig_direct_p1_base.pdf \
    $(GEN)/fig_spider_exp1_claude.pdf \
    $(GEN)/fig_spider_exp1_families.pdf \
    $(GEN)/fig_spider_cross_exp.pdf \
    $(GEN)/fig_capability_timeline.pdf \
    $(GEN)/fig_exp2_coverage.pdf \
    $(GEN)/fig_exp2_cost.pdf \
    $(GEN)/fig_exp2_coverage_certainty.pdf \
    $(SLIDE_GEN)/macros.tex \
    $(SLIDE_GEN)/tab_exp2_2x2.tex \
    $(GEN)/macros_p1_base.tex
	$(MAKE) -C slides

# --- Convenience aliases ------------------------------------------------------

.PHONY: report slides tables figures select

report: report/report.pdf
slides: slides/slides.pdf
tables: $(GEN)/tab_census.tex $(GEN)/macros.tex $(GEN)/macros_census.tex $(GEN)/tab_relances.tex $(GEN)/tab_exp2_2x2.tex $(GEN)/tab_comparaison.tex $(GEN)/tab_converter_benchmark.tex $(GEN)/tab_variance.tex $(GEN)/tab_verification.tex $(GEN)/tab_decomposition_fix.tex $(GEN)/tab_self_consistency.tex $(GEN)/tab_per_run.tex $(GEN)/tab_coherence.tex $(GEN)/tab_reconciliation.tex
figures: $(GEN)/census_bars.csv $(GEN)/fig_direct_cost_quality.pdf $(GEN)/fig_direct_p1_base.pdf $(GEN)/fig_spider_exp1_families.pdf $(SLIDE_GEN)/fig_method_convergence.pdf $(SLIDE_GEN)/fig_regimes_scatter.pdf $(SLIDE_GEN)/fig_scaling_curve.pdf
select: experiments/models_selected.yaml
census:
	$(MAKE) -C experiments census
