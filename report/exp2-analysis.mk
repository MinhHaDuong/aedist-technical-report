# Focused Exp2 analysis report artifacts
# Usage from repo root:
#   make -f report/exp2-analysis.mk exp2-analysis-report

GEN := report/inputs/generated

NAIVE_DIR    := experiments/outputs/sota_exp2_naive_arm
OPTIMISED_DIR := experiments/outputs/sota_exp2_brerun1

NAIVE_JSONS    := $(wildcard $(NAIVE_DIR)/*.json)
OPTIMISED_JSONS := $(wildcard $(OPTIMISED_DIR)/*.json)
NAIVE_MDS      := $(wildcard $(NAIVE_DIR)/*.md)
PROBE_RAWS     := $(wildcard $(OPTIMISED_DIR)/probes/*/*.raw.json)
PROBE_CLSF     := $(wildcard $(OPTIMISED_DIR)/probes/*/*.classification.json)

# --- Intermediate: flat per-run CSV ------------------------------------------

$(GEN)/tab_exp2_arms_runs.csv: $(NAIVE_JSONS) $(NAIVE_MDS) $(OPTIMISED_JSONS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_arms_runs \
	    --naive-dir $(NAIVE_DIR) \
	    --optimised-dir $(OPTIMISED_DIR) \
	    --output $@

# --- Table: per-model summary (reads from CSV) --------------------------------

$(GEN)/tab_exp2_arms.tex: $(GEN)/tab_exp2_arms_runs.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_arms \
	    --input $< \
	    --naive-dir $(NAIVE_DIR) \
	    --optimised-dir $(OPTIMISED_DIR) \
	    --output $@

# --- Figure: three-panel comparison (reads from CSV) -------------------------

$(GEN)/fig_exp2_arms_comparison.pdf: $(GEN)/tab_exp2_arms_runs.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp2_arms_comparison \
	    --input $< \
	    --output $@

# --- Figure: turn-by-turn trajectory for Arm 2 (reads from probes/) ---------

$(GEN)/fig_exp2_turn_trajectory.pdf: $(PROBE_RAWS) $(PROBE_CLSF)
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp2_turn_trajectory \
	    --probes-dir $(OPTIMISED_DIR)/probes \
	    --output $@

# --- Outline placeholder artifacts (post-conference skeleton) ----------------

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

# --- Top-level target --------------------------------------------------------

.PHONY: exp2-analysis-report

exp2-analysis-report: \
	$(GEN)/tab_exp2_arms_runs.csv \
	$(GEN)/tab_exp2_arms.tex \
	$(GEN)/fig_exp2_arms_comparison.pdf \
	$(GEN)/fig_exp2_turn_trajectory.pdf \
	$(EXP2_OUTLINE_ARTIFACTS)
