# AEDIST Technical Report — Root Makefile
#
# Pipeline stages:
#   make sweep1           Query all models (cd experiments/)
#   make sweep1-summary   Extract → evaluate → metrics.json
#   make select           Compute top N cloud + N local models
#   make tables           Generate LaTeX tables from metrics
#   make figures          Generate chart data CSVs for slides
#   make report           Build report.pdf
#   make slides           Build slides.pdf
#   make test             Run all Python tests

METRICS  := results/summary/all_metrics.json
GEN      := report/inputs/generated
SLIDE_GEN := slides/inputs/generated

.PHONY: test check-fast check report slides tables figures select sweep1 sweep1-summary

# --- Python -------------------------------------------------------------------

test:
	uv run pytest

check-fast: test

check: test
	cd experiments && $(MAKE) --dry-run sweep1

# --- Pipeline: experiments → metrics → tables/figures → publications ---------

# Stage 1-3: query → extract → evaluate (delegated to experiments/Makefile)
sweep1:
	$(MAKE) -C experiments sweep1

sweep1-summary:
	$(MAKE) -C experiments sweep1-summary

# Stage 4a: model selection (computed from census, not hardcoded)
experiments/models_sweep2.yaml: $(METRICS) experiments/models.yaml experiments/models_padme.yaml
	uv run python -m aedist.select_sweep2 \
	    --input $< --registry experiments/models.yaml \
	    --padme experiments/models_padme.yaml \
	    --output $@ --n 1

select: experiments/models_sweep2.yaml

# Stage 4b: tables for report
tables: $(GEN)/tab_census.tex $(GEN)/macros.tex

$(GEN)/tab_census.tex: $(METRICS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_census --input $< --output $@

$(GEN)/macros.tex: $(METRICS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_macros --input $< --output $@

# Stage 4c: chart data for slides
figures: $(SLIDE_GEN)/census_bars.csv $(SLIDE_GEN)/pareto.csv

$(SLIDE_GEN)/census_bars.csv: $(METRICS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_census --input $< --output $@

$(SLIDE_GEN)/pareto.csv: $(METRICS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_pareto --input $< --output $@

# Stage 5: publications
report: tables
	$(MAKE) -C report

slides: figures
	$(MAKE) -C slides
