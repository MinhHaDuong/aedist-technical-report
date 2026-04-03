# AEDIST Technical Report — Root Makefile
#
# Complete DAG: `make report` or `make slides` pulls all dependencies.
#
#   report.pdf ← tab_census.tex, macros.tex ← metrics.json ← sweep1-summary
#   slides.pdf ← census_bars.csv, pareto.csv ← metrics.json ← sweep1-summary

METRICS   := results/summary/all_metrics.json
GEN       := report/inputs/generated
SLIDE_GEN := slides/inputs/generated

.PHONY: test check-fast check sweep1 sweep1-summary

# --- Tests --------------------------------------------------------------------

test:
	uv run pytest

check-fast: test

check: test

# --- Metrics (root of the DAG) -----------------------------------------------

$(METRICS):
	$(MAKE) -C experiments sweep1-summary

# --- Model selection ----------------------------------------------------------

experiments/models_sweep2.yaml: $(METRICS) experiments/models.yaml experiments/models_padme.yaml
	uv run python -m aedist.select_sweep2 \
	    --input $< --registry experiments/models.yaml \
	    --padme experiments/models_padme.yaml \
	    --output $@ --n 1

# --- Tables for report --------------------------------------------------------

$(GEN)/tab_census.tex: $(METRICS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_census --input $< --output $@

$(GEN)/macros.tex: $(METRICS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_macros --input $< --output $@

# --- Chart data for slides ---------------------------------------------------

$(SLIDE_GEN)/census_bars.csv: $(METRICS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_census --input $< --output $@

SWEEP1_SUMMARY := results/summary/sweep1_summary.csv

$(SLIDE_GEN)/pareto.csv: $(METRICS) $(SWEEP1_SUMMARY)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_pareto --input $< --costs $(SWEEP1_SUMMARY) --output $@

# --- Publications -------------------------------------------------------------

report/report.pdf: report/report.tex report/refs.bib $(GEN)/tab_census.tex $(GEN)/macros.tex
	$(MAKE) -C report

slides/slides.pdf: slides/slides.tex $(SLIDE_GEN)/census_bars.csv $(SLIDE_GEN)/pareto.csv
	$(MAKE) -C slides

# --- Convenience aliases ------------------------------------------------------

.PHONY: report slides tables figures select

report: report/report.pdf
slides: slides/slides.pdf
tables: $(GEN)/tab_census.tex $(GEN)/macros.tex
figures: $(SLIDE_GEN)/census_bars.csv $(SLIDE_GEN)/pareto.csv
select: experiments/models_sweep2.yaml
sweep1:
	$(MAKE) -C experiments sweep1
