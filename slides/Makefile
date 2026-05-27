# Beamer slides and manuscript handout
#
# The writing build compiles from committed handoff artifacts only — no uv run,
# no data access. To regenerate figures/tables, run the analysis workpackage:
#   make -f experiments/analysis.mk exp2-analysis-report

GENERATED := inputs/generated
ROOT_SLIDE_GEN := slides/inputs/generated
ROOT_REPORT_GEN := report/inputs/generated
LOCAL_ROOT_REPORT_GEN := ../report/inputs/generated

SLIDE_ASSETS := \
	$(LOCAL_ROOT_REPORT_GEN)/fig_direct_p1_base.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_spider_exp1_claude.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_spider_exp1_families.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_capability_timeline.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_exp2_coverage.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_exp2_cost.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_exp2_coverage_certainty.pdf \
	$(GENERATED)/macros.tex \
	$(GENERATED)/tab_exp2_2x2.tex \
	$(LOCAL_ROOT_REPORT_GEN)/macros_p1_base.tex

MANUSCRIPT_ASSETS := \
	$(LOCAL_ROOT_REPORT_GEN)/fig_direct_p1_base.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_direct_cost_quality.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_spider_exp1_families.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/cost_quality.csv \
	$(LOCAL_ROOT_REPORT_GEN)/fig_capability_timeline.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_capability_dag.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_exp2_arms_comparison.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_exp2_coverage_certainty.pdf

.PHONY: all clean manuscript

all: slides.pdf slides-en.pdf manuscript/main.pdf

slides.pdf: slides.tex $(SLIDE_ASSETS)
	tectonic $<

# English deck. Shares all SLIDE_ASSETS; figures keep their generated-language
# labels (regenerating figures in English is a separate analysis-side task).
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
