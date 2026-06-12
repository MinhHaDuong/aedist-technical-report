# Beamer slides and manuscript handout
#
# The writing build compiles from committed handoff artifacts only — no uv run,
# no data access. To regenerate figures/tables, run the render (P3) workpackage:
#   make -f experiments/render.mk exp2-analysis-report

# Atomicity: delete a target whose recipe crashes mid-write — a tectonic run
# killed partway leaves a truncated slides/manuscript PDF with a fresh mtime
# that Make would treat as up-to-date (ticket 0461, generalising 0460).
.DELETE_ON_ERROR:

ROOT_REPORT_GEN := report/inputs/generated
LOCAL_ROOT_REPORT_GEN := ../report/inputs/generated

# The unsuffixed spider/coverage PDFs are English (used by slides-en.tex and
# the manuscript/main.tex preprint); the _fr variants carry French labels for slides.tex
# (ticket 0455). Both decks share this list, so both languages are listed.
SLIDE_ASSETS := \
	$(LOCAL_ROOT_REPORT_GEN)/fig_direct_p1_base.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_spider_exp1_claude.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_spider_exp1_claude_fr.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_spider_exp1_families.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_spider_exp1_families_fr.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_capability_timeline.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_exp2_coverage.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_exp2_cost.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_exp2_coverage_certainty.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_exp2_coverage_certainty_fr.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/macros_slides.tex \
	$(LOCAL_ROOT_REPORT_GEN)/tab_exp2_2x2_fr.tex \
	$(LOCAL_ROOT_REPORT_GEN)/macros_p1_base.tex

# Exactly the files main.tex pulls in via \includegraphics/\includepdf/\input —
# reconciled against the source (PR #969 review): no ghost prerequisites
# (cost_quality.csv was prose-only -> spurious rebuilds), no missing ones
# (fig_fusion_mvp.pdf was included but unlisted -> stale PDFs).
MANUSCRIPT_ASSETS := \
	$(LOCAL_ROOT_REPORT_GEN)/fig_longtail_recognition.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_direct_p1_base.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_direct_cost_quality.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_exp1_reliability.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_quality_floor_heatmap_exp1.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/tab_exp1_reliability_sensitivity.tex \
	$(LOCAL_ROOT_REPORT_GEN)/tab_source_concordance.tex \
	$(LOCAL_ROOT_REPORT_GEN)/tab_exp2_2x2_agents.tex \
	$(LOCAL_ROOT_REPORT_GEN)/tab_status_difficulty_en.tex \
	$(LOCAL_ROOT_REPORT_GEN)/fig_capability_timeline.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_capability_dag.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_exp2_arms_comparison.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_exp2_coverage_certainty.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_fusion_mvp.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_exp1_recognition_matrix_portrait.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/macros_manuscript.tex

.PHONY: all clean manuscript translate-slides

all: slides.pdf slides-en.pdf manuscript/main.pdf

# Convenience entry point only. slides.tex stays a committed source file, so
# this is deliberately NOT a prerequisite of slides.pdf — a non-deterministic
# network LLM call has no place inside the build DAG. Pure stdlib, no uv.
# Pass flags via ARGS, e.g. `make translate-slides ARGS="--dry-run"`.
translate-slides:
	python3 ../scripts/translate_slides.py $(ARGS)

slides.pdf: slides.tex $(SLIDE_ASSETS)
	tectonic $<

# English deck. Shares all SLIDE_ASSETS; it includes the unsuffixed (English)
# spider/coverage PDFs, while slides.tex includes the _fr variants (0455).
slides-en.pdf: slides-en.tex $(SLIDE_ASSETS)
	tectonic $<

manuscript: manuscript/main.pdf

# Hand-curated LaTeX source, tectonic-built like slides.tex (ticket 0524
# dropped the pandoc/pandoc-crossref toolchain). Asset paths inside main.tex
# are relative to manuscript/ (tectonic resolves against the input file's
# directory), hence ../../report/... there vs ../report/... here.
# -r 2 caps the engine at 3 passes: tectonic's change detection trips on a
# byte-identical bibtex .bbl rewrite ("internal consistency problem"), looping
# to its 6-pass ceiling. Convergence at 3 passes is verified (stable .aux/.bbl
# hashes, zero undefined references in the log).
manuscript/main.pdf: manuscript/main.tex $(MANUSCRIPT_ASSETS) ../report/refs.bib
	tectonic -r 2 $<

clean:
	rm -f slides.pdf slides-en.pdf manuscript/main.pdf *.aux *.log *.nav *.out *.snm *.toc
