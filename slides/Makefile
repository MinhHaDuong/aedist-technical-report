# Beamer slides and manuscript handout
#
# This Makefile is intentionally self-sufficient: building from slides/
# triggers required figure/table artifacts in the repo root DAG.

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

all: slides.pdf manuscript/main.pdf

slides.pdf: slides.tex $(SLIDE_ASSETS)
	tectonic $<

manuscript: manuscript/main.pdf

manuscript/main.pdf: manuscript/main.md $(MANUSCRIPT_ASSETS) ../report/refs.bib
	pandoc manuscript/main.md \
		-o $@ \
		--pdf-engine=tectonic \
		--resource-path=. \
		--citeproc \
		--bibliography=../report/refs.bib

# Slides-only asset generated under slides/inputs/generated.
$(GENERATED)/macros.tex: ; $(MAKE) -C .. $(ROOT_SLIDE_GEN)/macros.tex

# Report-canonical assets — trigger generation under report/inputs/generated.
$(LOCAL_ROOT_REPORT_GEN)/fig_direct_p1_base.pdf: ; $(MAKE) -C .. $(ROOT_REPORT_GEN)/fig_direct_p1_base.pdf
$(LOCAL_ROOT_REPORT_GEN)/fig_spider_exp1_claude.pdf: ; $(MAKE) -C .. $(ROOT_REPORT_GEN)/fig_spider_exp1_claude.pdf
$(LOCAL_ROOT_REPORT_GEN)/fig_spider_exp1_families.pdf: ; $(MAKE) -C .. $(ROOT_REPORT_GEN)/fig_spider_exp1_families.pdf
$(LOCAL_ROOT_REPORT_GEN)/macros_p1_base.tex: ; $(MAKE) -C .. $(ROOT_REPORT_GEN)/macros_p1_base.tex
$(LOCAL_ROOT_REPORT_GEN)/cost_quality.csv: ; $(MAKE) -C .. $(ROOT_REPORT_GEN)/cost_quality.csv
$(LOCAL_ROOT_REPORT_GEN)/fig_capability_timeline.pdf: ; $(MAKE) -C .. $(ROOT_REPORT_GEN)/fig_capability_timeline.pdf
$(LOCAL_ROOT_REPORT_GEN)/fig_capability_dag.pdf: ; $(MAKE) -C .. $(ROOT_REPORT_GEN)/fig_capability_dag.pdf
$(LOCAL_ROOT_REPORT_GEN)/fig_exp2_coverage.pdf $(LOCAL_ROOT_REPORT_GEN)/fig_exp2_cost.pdf &: ; \
	$(MAKE) -C .. $(ROOT_REPORT_GEN)/fig_exp2_coverage.pdf
$(LOCAL_ROOT_REPORT_GEN)/fig_exp2_coverage_certainty.pdf: ; $(MAKE) -C .. $(ROOT_REPORT_GEN)/fig_exp2_coverage_certainty.pdf

clean:
	rm -f slides.pdf manuscript/main.pdf *.aux *.log *.nav *.out *.snm *.toc
