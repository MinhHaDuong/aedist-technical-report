# AEDIST Technical Report — Root Makefile
#
# Dispatches to sub-Makefiles:
#   make test       Run all Python tests
#   make report     Build report.pdf
#   make slides     Build slides.pdf
#   make tables     Generate LaTeX tables from experiment results
#   make sweep1     Run model census (cd experiments/)
#   make check-fast Unit tests + lint (< 30s)
#   make check      Full test suite

.PHONY: test check-fast check report slides tables sweep1 sweep1-summary

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

tables:
	uv run python -m aedist.convert --output report/inputs/generated/

# --- Experiments --------------------------------------------------------------

sweep1:
	$(MAKE) -C experiments sweep1

sweep1-summary:
	$(MAKE) -C experiments sweep1-summary
