# Focused Exp2 analysis report artifacts
# Usage from repo root:
#   make -f report/exp2-analysis.mk exp2-analysis-report

GEN := report/inputs/generated

EXP2_OUTLINE_ARTIFACTS := \
	$(GEN)/tab_exp2_outline_dataset.tex \
	$(GEN)/fig_exp2_outline_dataset.tex \
	$(GEN)/tab_exp2_outline_hypotheses_map.tex \
	$(GEN)/tab_exp2_outline_protocol_fidelity.tex \
	$(GEN)/tab_exp2_outline_h1.tex \
	$(GEN)/fig_exp2_outline_h2.tex \
	$(GEN)/tab_exp2_outline_h3.tex \
	$(GEN)/tab_exp2_outline_h4.tex \
	$(GEN)/tab_exp2_outline_h5.tex \
	$(GEN)/fig_exp2_outline_h6.tex \
	$(GEN)/tab_exp2_outline_hypothesis_status.tex

.PHONY: exp2-analysis-report

exp2-analysis-report: $(EXP2_OUTLINE_ARTIFACTS)

$(GEN)/tab_exp2_outline_dataset.tex:
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_outline_dataset --output $@

$(GEN)/fig_exp2_outline_dataset.tex:
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp2_outline_dataset --output $@

$(GEN)/tab_exp2_outline_hypotheses_map.tex:
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_outline_hypotheses_map --output $@

$(GEN)/tab_exp2_outline_protocol_fidelity.tex:
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_outline_protocol_fidelity --output $@

$(GEN)/tab_exp2_outline_h1.tex:
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_outline_h1 --output $@

$(GEN)/fig_exp2_outline_h2.tex:
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp2_outline_h2 --output $@

$(GEN)/tab_exp2_outline_h3.tex:
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_outline_h3 --output $@

$(GEN)/tab_exp2_outline_h4.tex:
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_outline_h4 --output $@

$(GEN)/tab_exp2_outline_h5.tex:
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_outline_h5 --output $@

$(GEN)/fig_exp2_outline_h6.tex:
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp2_outline_h6 --output $@

$(GEN)/tab_exp2_outline_hypothesis_status.tex:
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_outline_hypothesis_status --output $@
