# AEDIST Technical Report — Root Makefile
#
# Complete DAG: `make report` or `make slides` pulls all dependencies.
#
#   report.pdf ← tab_census.tex, macros.tex ← measurements.jsonl
#   slides.pdf ← census_bars.csv, pareto.csv ← measurements.jsonl

MEASUREMENTS := measurements.jsonl
GEN          := report/inputs/generated
SLIDE_GEN    := slides/inputs/generated

.PHONY: test check-fast check sweep1 sweep1-summary

# --- Tests --------------------------------------------------------------------

test:
	uv run pytest

check-fast: test

check: test

# --- Measurements (single source of truth) ------------------------------------
#
# measurements.jsonl is the canonical store of all experiment results.
# Each sweep appends/replaces its own entries (merge by label).
#
# Update flow:
#   Sweep 1 (census):     make measurements   (calls experiments/sweep1-summary)
#   Sweep 2+ (regimes):   migrate_to_measurements.py --append (from query JSONs)
#   Sweep 4 (verify):     query_verification.py (appends directly)
#   Analysis:             self_consistency.py (replaces analysis entries)
#
# Worker architecture (future):
#   Workers produce RunRecords in memory → write to measurements.jsonl
#   via runner evaluate-all or direct append.

$(MEASUREMENTS): $(wildcard experiments/outputs/sweep1_census/*.csv)
	$(MAKE) -C experiments sweep1-summary

.PHONY: measurements
measurements: $(MEASUREMENTS)

# --- Model selection ----------------------------------------------------------

experiments/models_sweep2.yaml: $(MEASUREMENTS) experiments/models.yaml
	uv run python -m aedist.select_sweep2 \
	    --measurements $< --registry experiments/models.yaml \
	    --output $@ --n 1

# --- Tables for report --------------------------------------------------------

$(GEN)/tab_census.tex: $(MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_census --measurements $< --output $@

$(GEN)/macros.tex: $(MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_macros --measurements $< --output $@

$(GEN)/tab_relances.tex: $(MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_relances --measurements $< --output $@

$(GEN)/tab_comparaison.tex: $(MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_comparaison --measurements $< --output $@

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
	uv run python -m aedist.plot_census --measurements $< --output $@

$(SLIDE_GEN)/pareto.csv: $(MEASUREMENTS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_pareto --measurements $< --output $@

$(SLIDE_GEN)/sweep2_regimes.csv: $(GEN)/sweep2_regimes.csv
	@mkdir -p $(dir $@)
	cp $< $@

$(SLIDE_GEN)/macros.tex: $(SLIDE_GEN)/census_bars.csv $(MEASUREMENTS)
	uv run python -m aedist.tabulate_macros \
	    --measurements $(MEASUREMENTS) --census-csv $< --output $@

# --- Publications -------------------------------------------------------------

report/report.pdf: report/report.tex report/refs.bib \
    $(GEN)/tab_census.tex $(GEN)/macros.tex \
    $(GEN)/tab_relances.tex $(GEN)/tab_comparaison.tex
	$(MAKE) -C report

slides/slides.pdf: slides/slides.tex \
    $(SLIDE_GEN)/census_bars.csv $(SLIDE_GEN)/pareto.csv \
    $(SLIDE_GEN)/sweep2_regimes.csv $(SLIDE_GEN)/macros.tex
	$(MAKE) -C slides

# --- Convenience aliases ------------------------------------------------------

.PHONY: report slides tables figures select

report: report/report.pdf
slides: slides/slides.pdf
tables: $(GEN)/tab_census.tex $(GEN)/macros.tex $(GEN)/tab_relances.tex $(GEN)/tab_comparaison.tex $(GEN)/tab_converter_benchmark.tex
figures: $(SLIDE_GEN)/census_bars.csv $(SLIDE_GEN)/pareto.csv
select: experiments/models_sweep2.yaml
sweep1:
	$(MAKE) -C experiments sweep1
