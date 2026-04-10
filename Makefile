# AEDIST Technical Report — Root Makefile
#
# Complete DAG: `make report` or `make slides` pulls all dependencies.
#
#   report.pdf ← tab_census.tex, macros.tex ← measurements.jsonl
#   slides.pdf ← census_bars.csv, pareto.csv ← measurements.jsonl

MEASUREMENTS := measurements.jsonl
GEN          := report/inputs/generated
SLIDE_GEN    := slides/inputs/generated

.PHONY: test check-fast check census census-summary

# --- Tests --------------------------------------------------------------------

test:
	uv run pytest

check-fast: test

check: test

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

$(SLIDE_GEN)/method_convergence.csv: $(MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_method_convergence --output $@

$(SLIDE_GEN)/macros.tex: $(SLIDE_GEN)/census_bars.csv $(MEASUREMENTS)
	uv run python -m aedist.tabulate_macros --census-csv $< --output $@

# --- Publications -------------------------------------------------------------

report/report.pdf: report/report.tex report/refs.bib \
    $(GEN)/tab_census.tex $(GEN)/macros.tex \
    $(GEN)/tab_relances.tex $(GEN)/tab_comparaison.tex \
    $(GEN)/tab_variance.tex
	$(MAKE) -C report

slides/slides.pdf: slides/slides.tex \
    $(SLIDE_GEN)/census_bars.csv $(SLIDE_GEN)/pareto.csv \
    $(SLIDE_GEN)/regimes.csv $(SLIDE_GEN)/method_convergence.csv \
    $(SLIDE_GEN)/macros.tex
	$(MAKE) -C slides

# --- Convenience aliases ------------------------------------------------------

.PHONY: report slides tables figures select

report: report/report.pdf
slides: slides/slides.pdf
tables: $(GEN)/tab_census.tex $(GEN)/macros.tex $(GEN)/tab_relances.tex $(GEN)/tab_comparaison.tex $(GEN)/tab_converter_benchmark.tex $(GEN)/tab_variance.tex
figures: $(SLIDE_GEN)/census_bars.csv $(SLIDE_GEN)/pareto.csv
select: experiments/models_selected.yaml
census:
	$(MAKE) -C experiments census
