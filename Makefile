# AEDIST Technical Report — Root Makefile
#
# Dispatches to sub-Makefiles:
#   make test       Run all Python tests
#   make report     Build report.pdf
#   make slides     Build slides.pdf
#   make tables     Generate LaTeX tables from experiment results
#   make figures    Generate chart data CSVs for slides
#   make sweep1     Run model census (cd experiments/)
#   make check-fast Unit tests + lint (< 30s)
#   make check      Full test suite

.PHONY: test check-fast check report slides tables figures sweep1 sweep1-summary

# --- Python -------------------------------------------------------------------

test:
	uv run pytest

check-fast: test

check: test
	cd experiments && $(MAKE) --dry-run sweep1

# --- Publications -------------------------------------------------------------

report:
	$(MAKE) -C report

slides:
	$(MAKE) -C slides

# --- Generated tables and figures ---------------------------------------------

tables: report/inputs/generated/tab_census.tex report/inputs/generated/macros.tex

report/inputs/generated/tab_census.tex: results/summary/all_metrics.json
	uv run python -m aedist.tabulate_census --input $< --output $@

report/inputs/generated/macros.tex: results/summary/all_metrics.json
	uv run python -m aedist.tabulate_macros --input $< --output $@

figures: slides/inputs/generated/census_bars.csv slides/inputs/generated/pareto.csv

slides/inputs/generated/census_bars.csv: results/summary/all_metrics.json
	uv run python -m aedist.plot_census --input $< --output $@

slides/inputs/generated/pareto.csv: results/summary/all_metrics.json
	uv run python -m aedist.plot_pareto --input $< --output $@

# --- Experiments --------------------------------------------------------------

sweep1:
	$(MAKE) -C experiments sweep1

sweep1-summary:
	$(MAKE) -C experiments sweep1-summary
