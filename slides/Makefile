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
# main.md preprint); the _fr variants carry French labels for slides.tex
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

MANUSCRIPT_ASSETS := \
	$(LOCAL_ROOT_REPORT_GEN)/fig_direct_p1_base.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_direct_cost_quality.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_spider_exp1_families.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/cost_quality.csv \
	$(LOCAL_ROOT_REPORT_GEN)/fig_capability_timeline.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_capability_dag.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_exp2_arms_comparison.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_exp2_coverage_certainty.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_exp1_recognition_matrix_portrait.pdf

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

manuscript/main.pdf: manuscript/main.md $(MANUSCRIPT_ASSETS) ../report/refs.bib
	pandoc manuscript/main.md \
		-o $@ \
		--pdf-engine=tectonic \
		--resource-path=. \
		--citeproc \
		--bibliography=../report/refs.bib

clean:
	rm -f slides.pdf slides-en.pdf manuscript/main.pdf *.aux *.log *.nav *.out *.snm *.toc
