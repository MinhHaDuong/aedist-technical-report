# AEDIST P2 (score & consolidate) build phase.
#
# PHASE: P2 score & consolidate. This file extracts run outputs, scores them
# against the reference, and assembles the canonical outcomes: the mart v0
# (measurements.jsonl), the consolidated Exp2 mart (exp2_mart.jsonl), and the
# cross-eval CSVs. It lives in experiments/derived/ — next to the P2 derived
# data it produces. The P3 (render) phase that turns these outcomes into
# figures/tables/macros lives in experiments/render.mk (tracker 0406 S2); a
# figure build can no longer reach back into this scoring DAG. The P1 (acquire)
# sweeps that produce the raw model replies this file consumes live in
# experiments/acquire.mk.
#
# SOURCES (consumed, never produced here — they appear only as prerequisites,
# and score.mk carries NO rule able to (re)acquire them):
#   * experiments/outputs/**           (P1 raw model replies + flat arm dirs)
#   * data/reference/vietnam_thermal_plants_v2_classified.csv  (expert reference)
#
# OUTCOMES (produced):
#   * measurements.jsonl               (mart v0 — do NOT move or rename it,
#                                        transitional until ticket 0297)
#   * experiments/derived/exp2_mart.jsonl    (consolidated Exp2 mart)
#   * experiments/derived/sota_cross_eval.csv, .../exp1_cross_eval.csv
#                                            (per-run cross-eval CSVs)
#   * experiments/derived/rag_consistency/self_consistency_summary.json
#   * the *.record.json evaluation siblings under outputs/** and derived/**
#     (P2 scoring artifacts, NOT re-acquired raw replies)
#
# INVARIANT: score.mk declares NO rule for an upstream (P1) outcome. It never
#   fans out a worker/manager drain, runs a sweep, or calls an LLM adapter —
#   the only way to (re)acquire raw replies is experiments/acquire.mk's P1 sweep
#   verbs (which cost money). If a P1 source is missing, make MUST stop with
#   "No rule to make target", never silently re-acquire. Guarded by
#   tests/test_score_build_no_acquire.py.
#
# Path discipline: this file is invoked from the repo ROOT
#   (`make -f experiments/derived/score.mk <verb>`), so cwd = repo root, NOT
#   experiments/. Every path is anchored via the shared experiments/paths.mk
#   variables ($(ANALYSIS_*)) — no fragile cwd-relative `outputs/` or
#   `../measurements.jsonl`. Recursive `$(MAKE)` calls re-invoke THIS file by
#   absolute self-path so the default makefile (root ./Makefile) is never hit.
#
# Tracker 0406 step S3 (ticket 0410) consolidated the former P2 score makefile
# plus the P2 verbs from the P1 makefile (now experiments/acquire.mk) into this
# file.

# Self-path for recursive $(MAKE): captured BEFORE the include extends
# MAKEFILE_LIST, so it always points at this score.mk regardless of cwd.
SCORE_MK_SELF := $(abspath $(lastword $(MAKEFILE_LIST)))

include $(dir $(lastword $(MAKEFILE_LIST)))../paths.mk

# Atomicity: delete a target whose recipe fails mid-write. Without this, a
# crash partway through an append/stream write (e.g. score_exp1 appending to
# exp1_cross_eval.csv, or any --output writer here) leaves a PARTIAL file with
# a fresh mtime that Make treats as up-to-date — a silent stale-artifact
# hazard. This is the correctness guarantee that lets single-known-output
# recipes drop their .done sentinels and be plain-file rules (ticket 0460).
.DELETE_ON_ERROR:

# --- P2-local tooling -------------------------------------------------------
# Bare `uv run` (no --env-file): P2 scoring makes no API calls, so it needs no
# secrets. This mirrors the former P2 score makefile's convention and keeps
# the acquire-only ENV policy in experiments/common.mk.

SCORE_EVAL      := uv run python -m aedist.evaluate
SCORE_REFERENCE := $(ANALYSIS_REPO_ROOT)/data/reference/vietnam_thermal_plants_v2_classified.csv
SCORE_SRC       := $(ANALYSIS_REPO_ROOT)/src/aedist
SCORE_OUTPUTS   := $(ANALYSIS_OUTPUTS_DIR)
SCORE_DERIVED   := $(ANALYSIS_DERIVED_DIR)
SCORE_ARCHIVE   := $(ANALYSIS_EXPERIMENTS_DIR)/archive/outputs

# === measurements.jsonl: materialized view of all outputs ===================
# (migrated from the P1 makefile (now experiments/acquire.mk), tracker 0406 S3)

# Dropped entries (0422): pre-0122 names and record-only dirs have no
# extractable JSON/CSV for extract to scan. Raw replies were moved to
# experiments/archive/outputs/ (edda724b); renamed dirs under
# $(SCORE_OUTPUTS) hold only .record.json pointers.
#   census, multiturn, web, frontier: dirs never created post-archive
#   rag (→ rag_extract): record-only after edda724b
#   decomposed (→ rag_per_fuel): record-only after edda724b
#   decomposed_v2 (→ rag_per_fuel_v2): record-only after edda724b
#   sourced (→ rag_cited): record-only after edda724b
#   ablation/direct/p1_base, p1_base.topup, p1_composite: record-only
SCORE_STRUCTURED_DIRS := exp1_batch2

SCORE_OUTPUT_FILES := $(filter-out %.record.json $(SCORE_DERIVED)/rag_consistency/%,\
                   $(wildcard $(SCORE_OUTPUTS)/*/*.json) $(wildcard $(SCORE_DERIVED)/*/*.json)) \
                $(filter-out $(SCORE_DERIVED)/rag_consistency/%,\
                   $(wildcard $(SCORE_OUTPUTS)/*/*.csv) $(wildcard $(SCORE_DERIVED)/*/*.csv))

# Extract structured outputs from LLM JSON responses into CSVs.
.PHONY: extract
extract:
	@for dir in $(SCORE_STRUCTURED_DIRS); do \
	    uv run python -m aedist.extract \
	        --input $(SCORE_OUTPUTS)/$$dir --output $(SCORE_OUTPUTS)/$$dir; \
	done

.PRECIOUS: $(SCORE_OUTPUTS)/%.record.json $(SCORE_DERIVED)/%.record.json $(SCORE_ARCHIVE)/%.record.json
$(SCORE_OUTPUTS)/%.record.json: $(SCORE_OUTPUTS)/%.csv $(SCORE_REFERENCE)
	@$(SCORE_EVAL) evaluate $< --reference $(SCORE_REFERENCE) --output $(dir $<)
$(SCORE_DERIVED)/%.record.json: $(SCORE_DERIVED)/%.csv $(SCORE_REFERENCE)
	@$(SCORE_EVAL) evaluate $< --reference $(SCORE_REFERENCE) --output $(dir $<)
$(SCORE_ARCHIVE)/%.record.json: $(SCORE_ARCHIVE)/%.csv $(SCORE_REFERENCE)
	@$(SCORE_EVAL) evaluate $< --reference $(SCORE_REFERENCE) --output $(dir $<)

# Recursive Make: extract may create CSVs, so the second invocation must
# re-scan to find them.  Orphan JSONs (qualitative, no CSV) need nullglob.
# Recurse re-invokes THIS file by absolute self-path (cwd is repo root, so a
# bare `$(MAKE) extract` would hit root ./Makefile and fail).
$(ANALYSIS_MEASUREMENTS): $(SCORE_OUTPUT_FILES)
	@$(MAKE) --no-print-directory -f $(SCORE_MK_SELF) extract
	@$(MAKE) --no-print-directory -f $(SCORE_MK_SELF) evaluate-all-records
	@$(SCORE_EVAL) assemble $$(find $(SCORE_OUTPUTS) $(SCORE_DERIVED) $(SCORE_ARCHIVE) -name '*.record.json' ! -path '*/_extracted/*' | sort) --output $@

.PHONY: evaluate-all-records
evaluate-all-records:
	@$(MAKE) --no-print-directory -f $(SCORE_MK_SELF) -j$$(nproc) \
	    $$(find $(SCORE_OUTPUTS) $(SCORE_DERIVED) $(SCORE_ARCHIVE) -name '*.csv' ! -name 'reconciliation_*' ! -name '*_audit.csv' ! -path '*/_extracted/*' | sed 's/\.csv$$/.record.json/')
	@shopt -s nullglob; \
	for f in $(SCORE_OUTPUTS)/*/*-run*.json $(SCORE_OUTPUTS)/*/*/*-run*.json $(SCORE_DERIVED)/*/*-run*.json $(SCORE_ARCHIVE)/*/*-run*.json; do \
	    [[ "$$f" == *.record.json ]] && continue; \
	    [ -f "$${f%.json}.csv" ] && continue; \
	    rec="$${f%.json}.record.json"; \
	    [ -f "$$rec" ] && [ "$$rec" -nt "$$f" ] && continue; \
	    $(SCORE_EVAL) evaluate "$$f" --output "$$(dirname $$f)"; \
	done

# rebuild-measurements is a DELIBERATE, REVIEWED destructive protocol (0383
# mart-staleness lesson): it DELETES every committed *.record.json under
# outputs/ and derived/, then re-evaluates from scratch. ALWAYS review the
# resulting `git diff` on measurements.jsonl before committing — a silent
# re-score with a changed scorer or a missing input would corrupt the mart.
# Never run as a side effect; run it intentionally and inspect the diff.
.PHONY: rebuild-measurements
rebuild-measurements:
	find $(SCORE_OUTPUTS) $(SCORE_DERIVED) $(SCORE_ARCHIVE) -name '*.record.json' ! -path '*/_extracted/*' -delete
	$(MAKE) --no-print-directory -f $(SCORE_MK_SELF) $(ANALYSIS_MEASUREMENTS)

# === Full-phase aggregate (P2 outcomes) =====================================
# all-outcomes builds every P2 outcome a downstream phase consumes, in one
# target, so the root `world`/`staleness` entries (tracker 0406 S5, ticket 0415)
# can drive the whole P2 surface through a single recursive `-f score.mk`
# delegation instead of enumerating P2 paths in the root Makefile. Members:
#   * measurements.jsonl                  (mart v0)
#   * exp2_mart.jsonl                     (consolidated Exp2 mart; transitively
#                                          pulls $(ANALYSIS_EXP2_CROSS_EVAL_CSV)
#                                          = sota_cross_eval.csv + the arm .done
#                                          stamps)
#   * exp1_cross_eval.csv                 (Exp1 cross-eval; a plain-file rule —
#                                          single known output, no stamp)
#   * self_consistency_summary.json       (P2 SC outcome; no current P3 consumer
#                                          but part of a full P2 re-run)
# This rule runs P2 for REAL (extract → evaluate → assemble): it (re)writes
# committed scored data. It is only ever reached deliberately via `make world`
# (reviewed by git diff) — never as an incidental dependency, because the root
# carries no prereq edge into this DAG. Self-path recurse keeps cwd = repo root.
.PHONY: all-outcomes
all-outcomes:
	@$(MAKE) --no-print-directory -f $(SCORE_MK_SELF) $(ANALYSIS_MEASUREMENTS)
	@$(MAKE) --no-print-directory -f $(SCORE_MK_SELF) $(ANALYSIS_EXP2_MART_JSONL)
	@$(MAKE) --no-print-directory -f $(SCORE_MK_SELF) $(ANALYSIS_EXP1_CROSS_EVAL_CSV)
	@$(MAKE) --no-print-directory -f $(SCORE_MK_SELF) $(SCORE_SC_JSON)

# === Self-consistency scorer (archive rag_extract → derived/rag_consistency)
# (migrated from the P1 makefile (now experiments/acquire.mk), tracker 0406 S3
#  — P2 score half only; the tabulate→report/inputs/generated/ render half is in
#  render.mk.)
# Path was doubly stale: renamed rag→rag_extract (026f0e72), then archived
# (edda724b, ticket 0421). WARNING: this rule writes measurements.jsonl
# (--measurements) — do not run casually (0383).

SCORE_SC_INPUT  := $(ANALYSIS_EXPERIMENTS_DIR)/archive/outputs/rag_extract
SCORE_SC_OUTPUT := $(SCORE_DERIVED)/rag_consistency
SCORE_SC_JSON   := $(SCORE_SC_OUTPUT)/self_consistency_summary.json

$(SCORE_SC_JSON): $(wildcard $(SCORE_SC_INPUT)/*.json) $(SCORE_SRC)/self_consistency.py
	uv run python -m aedist.self_consistency \
	    --input $(SCORE_SC_INPUT) --output $(SCORE_SC_OUTPUT) --measurements $(ANALYSIS_MEASUREMENTS)

# === Exp2 analysis DAG (consolidated into this P2 score makefile) ===========
# extract → score → assemble the Exp2 mart and cross-eval CSVs.

# --- P2-local input wildcards -----------------------------------------------

ANALYSIS_EXP2_NAIVE_DIR ?= $(ANALYSIS_DERIVED_DIR)/arm1_flat
ANALYSIS_EXP2_OPTIMISED_DIR ?= $(ANALYSIS_DERIVED_DIR)/arm2_flat
ANALYSIS_EXP2_ARM3_DIR ?= $(ANALYSIS_DERIVED_DIR)/arm3_flat
ANALYSIS_EXP2_ARM4_DIR ?= $(ANALYSIS_DERIVED_DIR)/arm4_flat

ANALYSIS_EXP1_INPUT_CSVS := $(wildcard $(ANALYSIS_EXPERIMENTS_DIR)/outputs/exp1_batch2/*.csv)

ANALYSIS_EXP2_NAIVE_JSONS := $(wildcard $(ANALYSIS_EXP2_NAIVE_DIR)/*.json)
ANALYSIS_EXP2_OPTIMISED_JSONS := $(wildcard $(ANALYSIS_EXP2_OPTIMISED_DIR)/*.json)
ANALYSIS_EXP2_ARM3_JSONS := $(wildcard $(ANALYSIS_EXP2_ARM3_DIR)/*.json)
ANALYSIS_EXP2_ARM4_JSONS := $(wildcard $(ANALYSIS_EXP2_ARM4_DIR)/*.json)
ANALYSIS_EXP2_NAIVE_MDS := $(wildcard $(ANALYSIS_EXP2_NAIVE_DIR)/*.md)
ANALYSIS_EXP2_OPTIMISED_MDS := $(wildcard $(ANALYSIS_EXP2_OPTIMISED_DIR)/*.md)
ANALYSIS_EXP2_ARM3_MDS := $(wildcard $(ANALYSIS_EXP2_ARM3_DIR)/*.md)
ANALYSIS_EXP2_ARM4_MDS := $(wildcard $(ANALYSIS_EXP2_ARM4_DIR)/*.md)
ANALYSIS_EXP2_PROBE_RAWS := $(wildcard $(ANALYSIS_EXP2_OPTIMISED_DIR)/probes/*/*.raw.json)
ANALYSIS_EXP2_PROBE_CLSF := $(wildcard $(ANALYSIS_EXP2_OPTIMISED_DIR)/probes/*/*.classification.json)

# --- Extraction stamps -------------------------------------------------------
# Each arm stamp depends on a committed sentinel (.dataset) in its input
# directory rather than on a $(wildcard run*/*.json) expansion.
#
# Rationale (ticket 0462): $(wildcard) evaluates at parse time.  When .done
# is newer than all matched files (e.g. after a git checkout sets all mtimes
# to "now" while .done was already committed), make treats the stamp as
# up-to-date and silently skips extraction.  A committed sentinel decouples
# the rebuild trigger from file-mtime races: whenever the dataset changes
# (new run committed, existing run re-processed), touch or update .dataset
# and the next `make` will re-run extraction.
#
# Scope note: the remaining $(wildcard) expansions in this file (P2-local
# input wildcards for arm*_flat/ derived dirs, SCORE_OUTPUT_FILES,
# ANALYSIS_EXP1_INPUT_CSVS) feed P2→P2 rules whose inputs are produced by
# *this* phase.  Those patterns expand AFTER extraction runs (the derived
# dirs are built here), so the parse-time expansion is correct in practice.
# The armN_flat/.done stamps were the only rules consuming raw P1 committed
# data — the only place the bug manifested.

$(ANALYSIS_DERIVED_DIR)/arm1_flat/.done: $(ANALYSIS_EXPERIMENTS_DIR)/outputs/sota_exp3_arm1_batch1/.dataset
	uv run python -m aedist.extract_arm_single_turn \
	    --input-dir $(ANALYSIS_EXPERIMENTS_DIR)/outputs/sota_exp3_arm1_batch1 \
	    --output-dir $(ANALYSIS_DERIVED_DIR)/arm1_flat
	touch $@

$(ANALYSIS_DERIVED_DIR)/arm2_flat/.done: $(ANALYSIS_EXPERIMENTS_DIR)/outputs/sota_exp3_arm2_batch1/.dataset
	uv run python -m aedist.extract_arm_multi_turn \
	    --input-dir $(ANALYSIS_EXPERIMENTS_DIR)/outputs/sota_exp3_arm2_batch1 \
	    --output-dir $(ANALYSIS_DERIVED_DIR)/arm2_flat
	touch $@

# exp1_cross_eval.csv is a single known output (score_exp1 writes exactly one
# file and mkdirs its own parent), so it is a plain-file rule — no .done stamp,
# no dedicated holding directory. score_exp1 appends, hence the rm -f; the
# .DELETE_ON_ERROR above makes a crashed write self-clean (ticket 0460).
$(ANALYSIS_EXP1_CROSS_EVAL_CSV): $(ANALYSIS_EXP1_INPUT_CSVS) $(ANALYSIS_EXPERIMENTS_DIR)/../src/aedist/score_exp1.py
	rm -f $@
	uv run python -m aedist.score_exp1 \
	    --input-dir $(ANALYSIS_EXPERIMENTS_DIR)/outputs/exp1_batch2 \
	    --output $@

$(ANALYSIS_DERIVED_DIR)/arm3_flat/.done: $(ANALYSIS_EXPERIMENTS_DIR)/outputs/sota_exp3_arm3_batch1/.dataset
	uv run python -m aedist.extract_arm_single_turn \
	    --input-dir $(ANALYSIS_EXPERIMENTS_DIR)/outputs/sota_exp3_arm3_batch1 \
	    --output-dir $(ANALYSIS_DERIVED_DIR)/arm3_flat
	touch $@

$(ANALYSIS_DERIVED_DIR)/arm4_flat/.done: $(ANALYSIS_EXPERIMENTS_DIR)/outputs/sota_exp3_arm4_batch1/.dataset
	uv run python -m aedist.extract_arm_multi_turn \
	    --input-dir $(ANALYSIS_EXPERIMENTS_DIR)/outputs/sota_exp3_arm4_batch1 \
	    --output-dir $(ANALYSIS_DERIVED_DIR)/arm4_flat
	touch $@

# --- Cross-eval CSV (scored per-run, both arms) ----------------------------

$(ANALYSIS_EXP2_CROSS_EVAL_CSV): $(ANALYSIS_DERIVED_DIR)/arm1_flat/.done \
		$(ANALYSIS_DERIVED_DIR)/arm2_flat/.done \
		$(ANALYSIS_DERIVED_DIR)/arm3_flat/.done \
		$(ANALYSIS_DERIVED_DIR)/arm4_flat/.done
	@mkdir -p $(dir $@)
	rm -f $@
	@for f in $(ANALYSIS_EXP2_NAIVE_DIR)/*.json; do \
		read m r < <(python3 -c "import json,sys; d=json.load(open('$$f')); print(d['model'], d['run'])"); \
		[ "$$m" = "None" ] && { echo "skip (model=None): $$f"; continue; }; \
		uv run python -m aedist.score_mechanical --arm naive --model "$$m" --run "$$r" \
		    --naive-dir $(ANALYSIS_EXP2_NAIVE_DIR) --optimised-dir $(ANALYSIS_EXP2_OPTIMISED_DIR) \
		    --output-csv $@ || true; \
	done
	@for f in $(ANALYSIS_EXP2_OPTIMISED_DIR)/*.json; do \
		read m r < <(python3 -c "import json,sys; d=json.load(open('$$f')); print(d['model'], d['run'])"); \
		[ "$$m" = "None" ] && { echo "skip (model=None): $$f"; continue; }; \
		uv run python -m aedist.score_mechanical --arm optimised --model "$$m" --run "$$r" \
		    --naive-dir $(ANALYSIS_EXP2_NAIVE_DIR) --optimised-dir $(ANALYSIS_EXP2_OPTIMISED_DIR) \
		    --output-csv $@ || true; \
	done
	@for f in $(ANALYSIS_EXP2_ARM3_DIR)/*.json; do \
		read m r < <(python3 -c "import json,sys; d=json.load(open('$$f')); print(d['model'], d['run'])"); \
		[ "$$m" = "None" ] && { echo "skip (model=None): $$f"; continue; }; \
		uv run python -m aedist.score_mechanical --arm arm3 --model "$$m" --run "$$r" \
		    --arm3-dir $(ANALYSIS_EXP2_ARM3_DIR) --arm4-dir $(ANALYSIS_EXP2_ARM4_DIR) \
		    --output-csv $@ || true; \
	done
	@for f in $(ANALYSIS_EXP2_ARM4_DIR)/*.json; do \
		read m r < <(python3 -c "import json,sys; d=json.load(open('$$f')); print(d['model'], d['run'])"); \
		[ "$$m" = "None" ] && { echo "skip (model=None): $$f"; continue; }; \
		uv run python -m aedist.score_mechanical --arm arm4 --model "$$m" --run "$$r" \
		    --arm3-dir $(ANALYSIS_EXP2_ARM3_DIR) --arm4-dir $(ANALYSIS_EXP2_ARM4_DIR) \
		    --output-csv $@ || true; \
	done

# --- Canonical mart ---------------------------------------------------------
# The mart-derived VIEW projections (*_view.csv) are render-time shaping (P3)
# and live in experiments/render.mk. This file produces only the mart itself.

$(ANALYSIS_EXP2_MART_JSONL): $(ANALYSIS_DERIVED_DIR)/arm1_flat/.done \
		$(ANALYSIS_DERIVED_DIR)/arm2_flat/.done \
		$(ANALYSIS_DERIVED_DIR)/arm3_flat/.done \
		$(ANALYSIS_DERIVED_DIR)/arm4_flat/.done \
		$(ANALYSIS_EXP2_NAIVE_JSONS) $(ANALYSIS_EXP2_NAIVE_MDS) \
		$(ANALYSIS_EXP2_OPTIMISED_JSONS) $(ANALYSIS_EXP2_OPTIMISED_MDS) \
		$(ANALYSIS_EXP2_ARM3_JSONS) $(ANALYSIS_EXP2_ARM3_MDS) \
		$(ANALYSIS_EXP2_ARM4_JSONS) $(ANALYSIS_EXP2_ARM4_MDS) \
		$(ANALYSIS_EXP2_CROSS_EVAL_CSV) $(ANALYSIS_EXP2_PROBE_RAWS) $(ANALYSIS_EXP2_PROBE_CLSF)
	@mkdir -p $(dir $@)
	uv run python -m aedist.build_exp2_mart \
	    --naive-dir $(ANALYSIS_EXP2_NAIVE_DIR) \
	    --optimised-dir $(ANALYSIS_EXP2_OPTIMISED_DIR) \
	    --arm3-dir $(ANALYSIS_EXP2_ARM3_DIR) \
	    --arm4-dir $(ANALYSIS_EXP2_ARM4_DIR) \
	    --cross-eval-csv $(ANALYSIS_EXP2_CROSS_EVAL_CSV) \
	    --output $@ \
	    --repo-root $(ANALYSIS_REPO_ROOT)

# --- Dual-run parity staging -------------------------------------------------
# P2 mart-validation scratch. Staged under the P2-owned derived/ tree (NOT the
# P3 handoff tree report/inputs/generated/) so this P2 file never writes a
# render artifact — the score.mk/render.mk seam stays clean (ticket 0409).
# Transient: untracked, consumed only by check-mart-parity below.

ANALYSIS_EXP2_OLD_STAGE := $(ANALYSIS_DERIVED_DIR)/parity/exp2-old-path
ANALYSIS_EXP2_MART_STAGE := $(ANALYSIS_DERIVED_DIR)/parity/exp2-mart-path

$(ANALYSIS_EXP2_OLD_STAGE)/tab_exp2_arms_runs.csv: $(ANALYSIS_EXP2_NAIVE_JSONS) $(ANALYSIS_EXP2_NAIVE_MDS) $(ANALYSIS_EXP2_OPTIMISED_JSONS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.tabulate_exp2_arms_runs \
	    --naive-dir $(ANALYSIS_EXP2_NAIVE_DIR) \
	    --optimised-dir $(ANALYSIS_EXP2_OPTIMISED_DIR) \
	    --output $@

$(ANALYSIS_EXP2_OLD_STAGE)/tab_exp2_bib_quality.csv: $(ANALYSIS_EXP2_NAIVE_MDS) $(ANALYSIS_EXP2_OPTIMISED_MDS)
	@mkdir -p $(dir $@)
	uv run python -m aedist.extract_exp2_bib \
	    --naive-dir $(ANALYSIS_EXP2_NAIVE_DIR) \
	    --optimised-dir $(ANALYSIS_EXP2_OPTIMISED_DIR) \
	    --output $@

$(ANALYSIS_EXP2_OLD_STAGE)/exp2_turn_trajectory.csv: $(ANALYSIS_EXP2_PROBE_RAWS) $(ANALYSIS_EXP2_PROBE_CLSF)
	@mkdir -p $(dir $@)
	uv run python -m aedist.export_exp2_turn_trajectory_csv \
	    --probes-dir $(ANALYSIS_EXP2_OPTIMISED_DIR)/probes \
	    --output $@

$(ANALYSIS_EXP2_OLD_STAGE)/sota_cross_eval.csv: $(ANALYSIS_EXP2_CROSS_EVAL_CSV)
	@mkdir -p $(dir $@)
	cp $< $@

$(ANALYSIS_EXP2_MART_STAGE)/tab_exp2_arms_runs_view.csv $(ANALYSIS_EXP2_MART_STAGE)/tab_exp2_bib_quality_view.csv \
$(ANALYSIS_EXP2_MART_STAGE)/exp2_turn_trajectory_view.csv $(ANALYSIS_EXP2_MART_STAGE)/sota_cross_eval_view.csv: $(ANALYSIS_EXP2_MART_JSONL)
	@mkdir -p $(dir $@)
	uv run python -m aedist.build_exp2_mart_views \
	    --mart-jsonl $(ANALYSIS_EXP2_MART_JSONL) \
	    --output-dir $(ANALYSIS_EXP2_MART_STAGE) \
	    --repo-root $(ANALYSIS_REPO_ROOT)

exp2-old-path: \
	$(ANALYSIS_EXP2_OLD_STAGE)/tab_exp2_arms_runs.csv \
	$(ANALYSIS_EXP2_OLD_STAGE)/tab_exp2_bib_quality.csv \
	$(ANALYSIS_EXP2_OLD_STAGE)/exp2_turn_trajectory.csv \
	$(ANALYSIS_EXP2_OLD_STAGE)/sota_cross_eval.csv

exp2-mart-path: \
	$(ANALYSIS_EXP2_MART_STAGE)/tab_exp2_arms_runs_view.csv \
	$(ANALYSIS_EXP2_MART_STAGE)/tab_exp2_bib_quality_view.csv \
	$(ANALYSIS_EXP2_MART_STAGE)/exp2_turn_trajectory_view.csv \
	$(ANALYSIS_EXP2_MART_STAGE)/sota_cross_eval_view.csv

check-mart-parity: exp2-old-path exp2-mart-path
	uv run python -m aedist.check_exp2_mart_parity \
	    --left-dir $(ANALYSIS_EXP2_OLD_STAGE) \
	    --right-dir $(ANALYSIS_EXP2_MART_STAGE)
