# AEDIST Technical Report — Root Makefile
#
# Complete DAG: `make report` or `make slides` pulls all dependencies.
#
#   report.pdf ← tab_census.tex, macros.tex ← measurements.jsonl
#   slides.pdf ← census_bars.csv, pareto.csv ← measurements.jsonl

MEASUREMENTS := measurements.jsonl
GEN          := report/inputs/generated
SLIDE_GEN    := slides/inputs/generated

.PHONY: test check-fast check census census-summary show-prompts

# --- Tests --------------------------------------------------------------------

test:
	uv run pytest

check-fast: test

check: test

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

$(GEN)/macros.tex: $(MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_macros --output $@

$(GEN)/tab_relances.tex: $(MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_relances --output $@

$(GEN)/tab_comparaison.tex: $(MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_comparaison --output $@

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

# --- Chart data for slides ---------------------------------------------------

$(SLIDE_GEN)/census_bars.csv: $(MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_census --output $@

$(SLIDE_GEN)/pareto.csv: $(MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_pareto --output $@

$(SLIDE_GEN)/regimes.csv: $(GEN)/regimes.csv
	@mkdir -p $(dir $@)
	cp $< $@

$(SLIDE_GEN)/fig_method_convergence.pdf: $(MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_method_convergence \
	    --output $@ --core-only

$(SLIDE_GEN)/fig_scaling_curve.pdf: $(MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_scaling_curve \
	    --output $@

$(SLIDE_GEN)/macros.tex: $(SLIDE_GEN)/census_bars.csv $(MEASUREMENTS)
	uv run python -m aedist.tabulate_macros --census-csv $< --output $@

# --- Publications -------------------------------------------------------------

report/report.pdf: report/report.tex report/refs.bib \
    $(GEN)/tab_census.tex $(GEN)/macros.tex \
    $(GEN)/tab_relances.tex $(GEN)/tab_comparaison.tex \
    $(GEN)/tab_variance.tex $(GEN)/tab_verification.tex
	$(MAKE) -C report

slides/slides.pdf: slides/slides.tex \
    $(SLIDE_GEN)/census_bars.csv $(SLIDE_GEN)/pareto.csv \
    $(SLIDE_GEN)/regimes.csv $(SLIDE_GEN)/fig_method_convergence.pdf \
    $(SLIDE_GEN)/fig_scaling_curve.pdf \
    $(SLIDE_GEN)/macros.tex
	$(MAKE) -C slides

# --- Convenience aliases ------------------------------------------------------

.PHONY: report slides tables figures select

report: report/report.pdf
slides: slides/slides.pdf
tables: $(GEN)/tab_census.tex $(GEN)/macros.tex $(GEN)/tab_relances.tex $(GEN)/tab_comparaison.tex $(GEN)/tab_converter_benchmark.tex $(GEN)/tab_variance.tex $(GEN)/tab_verification.tex
figures: $(SLIDE_GEN)/census_bars.csv $(SLIDE_GEN)/pareto.csv $(SLIDE_GEN)/fig_method_convergence.pdf $(SLIDE_GEN)/fig_scaling_curve.pdf
select: experiments/models_selected.yaml
census:
	$(MAKE) -C experiments census
