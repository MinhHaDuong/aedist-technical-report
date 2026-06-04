# AEDIST Technical Report — Root Makefile
#
# Complete DAG: `make report` or `make slides` pulls all dependencies.
#
#   report.pdf ← tab_census.tex, macros.tex ← measurements.jsonl
#   slides.pdf ← fig_direct_p1_base.pdf, cost_quality.csv ← measurements.jsonl

MEASUREMENTS := measurements.jsonl
GEN          := report/inputs/generated

.PHONY: test test-fast test-slow coverage lint check-fast check census census-summary show-prompts

# --- Tests --------------------------------------------------------------------

# Single source of truth for the fast/slow split. test-slow is the exact
# complement (negation), so the partition stays coherent if this expression
# changes — no second list to keep in sync.
FAST_MARKERS := not integration and not slow

test-fast:
	uv run pytest -m "$(FAST_MARKERS)"

test:
	uv run pytest

# Integration/slow complement of the fast suite, derived by negation so the
# two targets together run the full suite exactly once (no duplication, no
# gap). `make check` runs this after `coverage`.
test-slow:
	uv run pytest -m "not ($(FAST_MARKERS))"

# Coverage gate on the fast suite (the suite the floor was measured against:
# 73% on 2026-05-29). Floor starts at 70% — just under baseline — and ratchets
# up as new tests land. Kept off test-fast/check-fast so the dev loop stays
# quick; enforced via `make check` (and thus in CI through docs-build's
# `make check` step).
coverage:
	uv run pytest -m "$(FAST_MARKERS)" \
		--cov=src/aedist --cov-report=term-missing --cov-fail-under=70

lint:
	uv run ruff check src/ tests/ scripts/
	uv run python scripts/check_ticket_structure.py

check-fast: test-fast lint

check: coverage test-slow lint

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

# Report-side tables (tab_census, macros, macros_census, tab_relances,
# tab_comparaison, tab_variance, tab_verification, tab_decomposition_fix,
# tab_coherence, tab_reconciliation, tab_converter_benchmark) and the
# intermediate derived/*.json|csv artifacts they consume are produced by the
# analysis workpackage. To regenerate:
#     make -f experiments/analysis.mk report-tables
# tab_self_consistency.tex and tab_per_run.tex come from
# experiments/Makefile `self-consistency` (single producer, 0354).

# --- Publications -------------------------------------------------------------

report/report.pdf: report/report.tex report/refs.bib \
    $(GEN)/tab_census.tex $(GEN)/macros.tex $(GEN)/macros_census.tex \
	$(GEN)/tab_relances.tex $(GEN)/tab_exp2_2x2.tex $(GEN)/tab_comparaison.tex \
    $(GEN)/tab_variance.tex $(GEN)/tab_verification.tex \
		$(GEN)/fig_spider_exp1_families.pdf \
    $(GEN)/tab_decomposition_fix.tex \
    $(GEN)/tab_self_consistency.tex $(GEN)/tab_per_run.tex \
    $(GEN)/tab_coherence.tex \
    $(GEN)/tab_reconciliation.tex \
    $(GEN)/tab_converter_benchmark.tex
	$(MAKE) -C report

slides/slides.pdf: slides/slides.tex \
    $(GEN)/fig_direct_p1_base.pdf \
    $(GEN)/fig_spider_exp1_claude.pdf \
    $(GEN)/fig_spider_exp1_families.pdf \
    $(GEN)/fig_spider_cross_exp.pdf \
    $(GEN)/fig_capability_timeline.pdf \
    $(GEN)/fig_capability_dag.pdf \
    $(GEN)/fig_exp2_coverage.pdf \
    $(GEN)/fig_exp2_cost.pdf \
    $(GEN)/fig_exp2_coverage_certainty.pdf \
    $(GEN)/macros_slides.tex \
    $(GEN)/tab_exp2_2x2_fr.tex \
    $(GEN)/macros_p1_base.tex
	$(MAKE) -C slides

# --- Convenience aliases ------------------------------------------------------

.PHONY: report slides tables figures select

report: report/report.pdf
slides: slides/slides.pdf
# Report-side tables, figures, and slide chart data are produced by the
# analysis workpackage. tab_self_consistency.tex and tab_per_run.tex live in
# experiments/Makefile under `self-consistency` (single producer, 0354), so
# the `tables:` alias chains both to preserve the pre-0352 UX.
tables:
	$(MAKE) -f experiments/analysis.mk report-tables
	$(MAKE) -C experiments self-consistency
figures:
	$(MAKE) -f experiments/analysis.mk chart-figures
select: experiments/models_selected.yaml
census:
	$(MAKE) -C experiments census
