# Focused Exp2 analysis report artifacts
# Usage from repo root:
#   make -f report/exp2-analysis.mk exp2-analysis-report

GEN := report/inputs/generated
ARM_FIG_GEN := report/inputs/generated
MART_JSONL := $(GEN)/exp2_mart.jsonl
OLD_STAGE := $(GEN)/exp2-old-path
MART_STAGE := $(GEN)/exp2-mart-path

NAIVE_DIR    := experiments/outputs/sota_exp2_naive_arm
OPTIMISED_DIR := experiments/outputs/sota_exp2_brerun1

NAIVE_JSONS    := $(wildcard $(NAIVE_DIR)/*.json)
OPTIMISED_JSONS := $(wildcard $(OPTIMISED_DIR)/*.json)
NAIVE_MDS      := $(wildcard $(NAIVE_DIR)/*.md)
OPTIMISED_MDS  := $(wildcard $(OPTIMISED_DIR)/*.md)
PROBE_RAWS     := $(wildcard $(OPTIMISED_DIR)/probes/*/*.raw.json)
PROBE_CLSF     := $(wildcard $(OPTIMISED_DIR)/probes/*/*.classification.json)

# --- Canonical mart and mart-derived views ---------------------------------

$(MART_JSONL): $(NAIVE_JSONS) $(NAIVE_MDS) $(OPTIMISED_JSONS) $(OPTIMISED_MDS) \
        experiments/derived/sota_cross_eval.csv $(PROBE_RAWS) $(PROBE_CLSF)
	@mkdir -p $(dir $@)
	uv run python -m aedist.build_exp2_mart \
	    --naive-dir $(NAIVE_DIR) \
	    --optimised-dir $(OPTIMISED_DIR) \
	    --cross-eval-csv experiments/derived/sota_cross_eval.csv \
	    --output $@ \
	    --repo-root .

$(GEN)/tab_exp2_arms_runs_view.csv $(GEN)/tab_exp2_bib_quality_view.csv \
$(GEN)/exp2_turn_trajectory_view.csv $(GEN)/sota_cross_eval_view.csv: $(MART_JSONL)
	@mkdir -p $(dir $@)
	uv run python -m aedist.build_exp2_mart_views \
	    --mart-jsonl $(MART_JSONL) \
	    --output-dir $(GEN) \
	    --repo-root .

# --- Dual-run parity staging -------------------------------------------------

$(OLD_STAGE)/tab_exp2_arms_runs.csv: $(NAIVE_JSONS) $(NAIVE_MDS) $(OPTIMISED_JSONS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_arms_runs \
	    --naive-dir $(NAIVE_DIR) \
	    --optimised-dir $(OPTIMISED_DIR) \
	    --output $@

$(OLD_STAGE)/tab_exp2_bib_quality.csv: $(NAIVE_MDS) $(OPTIMISED_MDS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.extract_exp2_bib \
	    --naive-dir $(NAIVE_DIR) \
	    --optimised-dir $(OPTIMISED_DIR) \
	    --output $@

$(OLD_STAGE)/exp2_turn_trajectory.csv: $(PROBE_RAWS) $(PROBE_CLSF)
	@mkdir -p $(dir $@)
	uv run python -m aedist.export_exp2_turn_trajectory_csv \
	    --probes-dir $(OPTIMISED_DIR)/probes \
	    --output $@

$(OLD_STAGE)/sota_cross_eval.csv: experiments/derived/sota_cross_eval.csv
	@mkdir -p $(dir $@)
	cp $< $@

$(MART_STAGE)/tab_exp2_arms_runs_view.csv $(MART_STAGE)/tab_exp2_bib_quality_view.csv \
$(MART_STAGE)/exp2_turn_trajectory_view.csv $(MART_STAGE)/sota_cross_eval_view.csv: $(MART_JSONL)
	@mkdir -p $(dir $@)
	uv run python -m aedist.build_exp2_mart_views \
	    --mart-jsonl $(MART_JSONL) \
	    --output-dir $(MART_STAGE) \
	    --repo-root .

exp2-old-path: \
	$(OLD_STAGE)/tab_exp2_arms_runs.csv \
	$(OLD_STAGE)/tab_exp2_bib_quality.csv \
	$(OLD_STAGE)/exp2_turn_trajectory.csv \
	$(OLD_STAGE)/sota_cross_eval.csv

exp2-mart-path: \
	$(MART_STAGE)/tab_exp2_arms_runs_view.csv \
	$(MART_STAGE)/tab_exp2_bib_quality_view.csv \
	$(MART_STAGE)/exp2_turn_trajectory_view.csv \
	$(MART_STAGE)/sota_cross_eval_view.csv

check-mart-parity: exp2-old-path exp2-mart-path
	uv run python -m aedist.check_exp2_mart_parity \
	    --left-dir $(OLD_STAGE) \
	    --right-dir $(MART_STAGE)

# --- Table: per-model summary (reads from CSV) --------------------------------

$(GEN)/tab_exp2_arms.tex: $(GEN)/tab_exp2_arms_runs_view.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_arms \
	    --input $< \
	    --naive-dir $(NAIVE_DIR) \
	    --optimised-dir $(OPTIMISED_DIR) \
	    --output $@

# --- Figure: three-panel comparison (reads from CSV) -------------------------

$(ARM_FIG_GEN)/fig_exp2_arms_comparison.pdf: $(GEN)/tab_exp2_arms_runs_view.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp2_arms_comparison \
	    --input $< \
	    --output $@

# --- Figure: turn-by-turn trajectory for Arm 2 (reads from probes/) ---------

$(GEN)/fig_exp2_turn_trajectory.pdf: $(GEN)/exp2_turn_trajectory_view.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp2_turn_trajectory \
	    --input $< \
	    --output $@

# --- Bibliography quality CSV (reads markdown outputs) ----------------------

# --- Bibliography quality LaTeX table (reads from CSV) ----------------------

$(GEN)/tab_exp2_bib_quality.tex: $(GEN)/tab_exp2_bib_quality_view.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_bib_quality \
	    --input $< \
	    --output $@

# --- Figure: coverage vs. certainty scatter (reads from bib quality CSV) -----

$(GEN)/fig_exp2_coverage_certainty.pdf: $(GEN)/tab_exp2_bib_quality_view.csv \
		$(GEN)/tab_exp2_arms_runs_view.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_exp2_coverage_certainty \
	    --input $(GEN)/tab_exp2_bib_quality_view.csv \
	    --arms-input $(GEN)/tab_exp2_arms_runs_view.csv \
	    --output $@

# --- Figure: five-axis quality spider from cross-eval scores -----------------

$(GEN)/fig_quality_spider.pdf: $(GEN)/sota_cross_eval_view.csv experiments/quality_spider_config.yaml
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_quality_spider \
	    --input $< \
	    --config experiments/quality_spider_config.yaml \
	    --output $@

# --- Figure: Exp1 family spiders (reads from Exp1 cross-eval CSV) -----------

$(GEN)/fig_spider_exp1_families.pdf: experiments/derived/exp1_cross_eval.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_quality_spider_exp1 \
	    --input $< \
	    --output $@

# --- Figure: Claude-only single spider, 5 quality dims, FR criteria ---------

$(GEN)/fig_spider_exp1_claude.pdf: experiments/derived/exp1_cross_eval.csv
	@mkdir -p $(dir $@)
	uv run python -m aedist.plot_quality_spider_exp1 \
	    --input $< \
	    --family claude \
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
	$(GEN)/tab_exp2_arms_runs_view.csv \
	$(GEN)/tab_exp2_arms.tex \
	$(ARM_FIG_GEN)/fig_exp2_arms_comparison.pdf \
	$(GEN)/fig_exp2_turn_trajectory.pdf \
	$(GEN)/tab_exp2_bib_quality_view.csv \
	$(GEN)/tab_exp2_bib_quality.tex \
	$(GEN)/fig_exp2_coverage_certainty.pdf \
	$(GEN)/fig_quality_spider.pdf \
	$(GEN)/fig_spider_exp1_claude.pdf \
	$(EXP2_OUTLINE_ARTIFACTS)
