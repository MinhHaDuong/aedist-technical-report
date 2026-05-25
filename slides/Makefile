# Beamer slides and manuscript handout
#
# This Makefile is intentionally self-sufficient: building from slides/
# triggers required figure/table artifacts in the repo root DAG.

GENERATED := inputs/generated
ROOT_SLIDE_GEN := slides/inputs/generated
ROOT_REPORT_GEN := report/inputs/generated
LOCAL_ROOT_REPORT_GEN := ../report/inputs/generated

SLIDE_ASSETS := \
	$(LOCAL_ROOT_REPORT_GEN)/census_bars.csv \
	$(LOCAL_ROOT_REPORT_GEN)/fig_direct_cost_quality.pdf \
	$(GENERATED)/regimes.csv \
	$(LOCAL_ROOT_REPORT_GEN)/fig_direct_p1_base.pdf \
	$(GENERATED)/fig_method_convergence.pdf \
	$(GENERATED)/fig_regimes_scatter.pdf \
	$(GENERATED)/fig_scaling_curve.pdf \
	$(GENERATED)/fig_ablation_strip.pdf \
	$(GENERATED)/macros.tex \
	$(LOCAL_ROOT_REPORT_GEN)/macros_p1_base.tex

MANUSCRIPT_ASSETS := \
	$(LOCAL_ROOT_REPORT_GEN)/fig_direct_p1_base.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_direct_cost_quality.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/cost_quality.csv \
	$(LOCAL_ROOT_REPORT_GEN)/fig_capability_timeline.pdf \
	$(LOCAL_ROOT_REPORT_GEN)/fig_capability_dag.pdf \
	$(GENERATED)/fig_exp2_arms_comparison.pdf \
	$(GENERATED)/fig_exp2_turn_trajectory.pdf \
	$(GENERATED)/fig_exp2_coverage_certainty.pdf

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

# Slides-only assets generated under slides/inputs/generated.
$(GENERATED)/regimes.csv: ; $(MAKE) -C .. $(ROOT_SLIDE_GEN)/regimes.csv
$(GENERATED)/fig_method_convergence.pdf: ; $(MAKE) -C .. $(ROOT_SLIDE_GEN)/fig_method_convergence.pdf
$(GENERATED)/fig_regimes_scatter.pdf: ; $(MAKE) -C .. $(ROOT_SLIDE_GEN)/fig_regimes_scatter.pdf
$(GENERATED)/fig_scaling_curve.pdf: ; $(MAKE) -C .. $(ROOT_SLIDE_GEN)/fig_scaling_curve.pdf
$(GENERATED)/fig_ablation_strip.pdf: ; $(MAKE) -C .. $(ROOT_SLIDE_GEN)/fig_ablation_strip.pdf
$(GENERATED)/macros.tex: ; $(MAKE) -C .. $(ROOT_SLIDE_GEN)/macros.tex

# Report-canonical assets — trigger generation under report/inputs/generated.
$(LOCAL_ROOT_REPORT_GEN)/census_bars.csv: ; $(MAKE) -C .. $(ROOT_REPORT_GEN)/census_bars.csv
$(LOCAL_ROOT_REPORT_GEN)/fig_direct_cost_quality.pdf: ; $(MAKE) -C .. $(ROOT_REPORT_GEN)/fig_direct_cost_quality.pdf
$(LOCAL_ROOT_REPORT_GEN)/fig_direct_p1_base.pdf: ; $(MAKE) -C .. $(ROOT_REPORT_GEN)/fig_direct_p1_base.pdf
$(LOCAL_ROOT_REPORT_GEN)/macros_p1_base.tex: ; $(MAKE) -C .. $(ROOT_REPORT_GEN)/macros_p1_base.tex
$(LOCAL_ROOT_REPORT_GEN)/cost_quality.csv: ; $(MAKE) -C .. $(ROOT_REPORT_GEN)/cost_quality.csv
$(LOCAL_ROOT_REPORT_GEN)/fig_capability_timeline.pdf: ; $(MAKE) -C .. $(ROOT_REPORT_GEN)/fig_capability_timeline.pdf
$(LOCAL_ROOT_REPORT_GEN)/fig_capability_dag.pdf: ; $(MAKE) -C .. $(ROOT_REPORT_GEN)/fig_capability_dag.pdf

# Exp2 manuscript figures are generated under report/inputs/generated.
$(GENERATED)/fig_exp2_arms_comparison.pdf: $(LOCAL_ROOT_REPORT_GEN)/fig_exp2_arms_comparison.pdf
	cp $< $@

$(GENERATED)/fig_exp2_turn_trajectory.pdf: $(LOCAL_ROOT_REPORT_GEN)/fig_exp2_turn_trajectory.pdf
	cp $< $@

$(GENERATED)/fig_exp2_coverage_certainty.pdf: $(LOCAL_ROOT_REPORT_GEN)/fig_exp2_coverage_certainty.pdf
	cp $< $@

$(LOCAL_ROOT_REPORT_GEN)/fig_exp2_arms_comparison.pdf: ; $(MAKE) -C .. $(ROOT_REPORT_GEN)/fig_exp2_arms_comparison.pdf
$(LOCAL_ROOT_REPORT_GEN)/fig_exp2_turn_trajectory.pdf: ; $(MAKE) -C .. $(ROOT_REPORT_GEN)/fig_exp2_turn_trajectory.pdf
$(LOCAL_ROOT_REPORT_GEN)/fig_exp2_coverage_certainty.pdf: ; $(MAKE) -C .. $(ROOT_REPORT_GEN)/fig_exp2_coverage_certainty.pdf

clean:
	rm -f slides.pdf manuscript/main.pdf *.aux *.log *.nav *.out *.snm *.toc
