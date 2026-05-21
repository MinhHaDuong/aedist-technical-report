# aedist/Makefile — Reproducible experiment pipeline
#
# Sweep configs live in [sweeps.*] sections of experiments.toml.
# Job dispatch is handled by the manager + worker pipeline:
#   1. `make census-generate`  — fan out sweep config into per-model jobs
#   2. `make census-run`       — start workers to execute the jobs
#   3. `make census-summary`   — extract → evaluate → summarize
#
# Or simply: `make census` to generate + run in one step.
#
# Adding a model to models.yaml → re-run generate (idempotent) + run.
#
# --- ENV POLICY ---------------------------------------------------------------
# All API keys live in the PROJECT .env (../.env relative to this Makefile),
# not in ~/.claude/.env. Decision 2026-04-30:
#   - Project .env is the single source of truth for OPENROUTER_API_KEY,
#     TAVILY_API_KEY, HF_TOKEN, ZENODO_TOKEN, HAL_*, etc.
#   - Reproducibility: a fresh clone with .env populated runs end-to-end;
#     no dependence on user-level dotfiles. Avoids the stale-key confusion
#     we hit (~/.claude/.env had a stale OPENROUTER_API_KEY for weeks).
#   - User ~/.claude/.env stays for cross-project personal accounts
#     (Claude Code itself, Anthropic API outside this project, etc.) and
#     is no longer auto-injected into bash subprocesses by on-start.sh
#     because doing so leaked all keys via `ps -ef`.
# Loading mechanism: every `uv run` goes through $(UV_RUN), which uses
# `--env-file ../.env` so uv populates the env from the file directly.
# Do NOT `export KEY := $(shell grep ...)` from the Makefile — that puts
# values onto Make's command line and on into spawned process arguments,
# the same leak path we just closed.

SHELL := /bin/bash
.SHELLFLAGS := -o pipefail -c

# --- Sentinel: project .env exists for targets that need API keys -------------
# Targets in this list will fail fast with a readable message if .env is
# missing. Keys themselves are not read into Make variables — uv loads them
# at child-process spawn time via --env-file.
_NEEDS_ENV := census census-run census-summary regimes regimes-run \
              sourced sourced-run frontier frontier-run
ifneq ($(filter $(_NEEDS_ENV),$(MAKECMDGOALS)),)
  $(if $(wildcard ../.env),,$(error ../.env not found — copy ../.env.example and populate API keys))
endif

# --- Common -------------------------------------------------------------------
# UV_RUN: canonical macro for every uv invocation. --env-file injects the
# project .env directly into the spawned process; nothing transits Make
# variables or process command lines.
UV_RUN  := uv run --project .. --env-file ../.env
MANAGER := $(UV_RUN) python -m aedist.manager generate
WORKER  := $(UV_RUN) python -m aedist.worker
# Cap concurrent OpenRouter workers at API rate limit (default 8).
# Override: make census-run OR_MAX=16
OR_MAX  ?= 8
OR_PENDING = $(words $(wildcard jobs/pending/*.yaml))
OR_JOBS = $(shell python3 -c "print(min($(OR_PENDING), $(OR_MAX)))")

# Read a single field from a sweep config in experiments.toml.
cfg = $(shell python3 -c "import tomllib; c=tomllib.load(open('experiments.toml','rb')); print(c['sweeps']['$(1)'].get('$(2)',''))")

# --- Census: model census -----------------------------------------------------

S1_OUTPUT  := $(call cfg,census,output)

.PHONY: census census-generate census-run census-summary

census: census-generate census-run

census-generate:
	$(MANAGER) --sweep census --experiments experiments.toml
	$(MANAGER) --sweep census_local --experiments experiments.toml

census-run:
	for i in $$(seq 1 $(OR_JOBS)); do $(WORKER) openrouter --drain & done; \
	$(WORKER) padme --drain & \
	wait

census-summary: rebuild-measurements

# --- Regimes: information regimes ---------------------------------------------

.PHONY: regimes regimes-generate regimes-run

regimes: regimes-generate regimes-run

regimes-generate:
	$(MANAGER) --sweep multiturn --experiments experiments.toml
	$(MANAGER) --sweep rag --experiments experiments.toml
	$(MANAGER) --sweep web --experiments experiments.toml

regimes-run:
	for i in $$(seq 1 $(OR_JOBS)); do $(WORKER) openrouter --drain & done; \
	wait

# --- Decomposed: task decomposition by fuel type -----------------------------

.PHONY: decomposed decomposed-generate decomposed-run

decomposed: decomposed-generate decomposed-run

decomposed-generate:
	$(MANAGER) --sweep decomposed --experiments experiments.toml

decomposed-run:
	for i in $$(seq 1 $(OR_JOBS)); do $(WORKER) openrouter --drain & done; \
	wait

# --- Verification: verification regimes --------------------------------------

.PHONY: verification verification-generate verification-run

verification: verification-generate verification-run

verification-generate:
	$(MANAGER) --sweep verification --experiments experiments.toml

verification-run:
	for i in $$(seq 1 $(OR_JOBS)); do $(WORKER) openrouter --drain & done; \
	wait

# --- Sourced: sourced extraction (citations upfront) -------------------------

.PHONY: sourced sourced-generate sourced-run

sourced: sourced-generate sourced-run

sourced-generate:
	$(MANAGER) --sweep sourced --experiments experiments.toml

sourced-run:
	for i in $$(seq 1 $(OR_JOBS)); do $(WORKER) openrouter --drain & done; \
	wait

# --- Frontier: deep-research models ------------------------------------------

.PHONY: frontier frontier-generate frontier-run

frontier: frontier-generate frontier-run

frontier-generate:
	$(MANAGER) --sweep frontier --experiments experiments.toml
	$(MANAGER) --sweep frontier_scenarios --experiments experiments.toml
	$(MANAGER) --sweep frontier_skill --experiments experiments.toml

frontier-run:
	for i in $$(seq 1 $(OR_JOBS)); do $(WORKER) openrouter --drain & done; \
	wait

# --- Rebuild measurements (materialized view of all outputs) -----------------

EVAL      := $(UV_RUN) python -m aedist.evaluate
REFERENCE := ../data/reference/vietnam_thermal_v1.csv

STRUCTURED_DIRS := census multiturn web rag \
                   decomposed decomposed_v2 sourced frontier \
                   ablation/direct/p1_base ablation/direct/p1_base.topup \
                   ablation/direct/p1_composite

OUTPUT_FILES := $(filter-out %.record.json,$(wildcard outputs/*/*.json) $(wildcard derived/*/*.json)) \
                $(wildcard outputs/*/*.csv) $(wildcard derived/*/*.csv)

# Extract structured outputs from LLM JSON responses into CSVs.
.PHONY: extract
extract:
	@for dir in $(STRUCTURED_DIRS); do \
	    $(UV_RUN) python -m aedist.extract \
	        --input outputs/$$dir --output outputs/$$dir; \
	done

.PRECIOUS: outputs/%.record.json derived/%.record.json
outputs/%.record.json: outputs/%.csv $(REFERENCE)
	@$(EVAL) evaluate $< --reference $(REFERENCE) --output $(dir $<)
derived/%.record.json: derived/%.csv $(REFERENCE)
	@$(EVAL) evaluate $< --reference $(REFERENCE) --output $(dir $<)

# Recursive Make: extract may create CSVs, so the second invocation must
# re-scan to find them.  Orphan JSONs (qualitative, no CSV) need nullglob.
../measurements.jsonl: $(OUTPUT_FILES)
	@$(MAKE) --no-print-directory extract
	@$(MAKE) --no-print-directory evaluate-all-records
	@$(EVAL) assemble $$(find outputs derived -name '*.record.json' ! -path '*/_extracted/*' | sort) --output $@

.PHONY: evaluate-all-records
evaluate-all-records:
	@$(MAKE) --no-print-directory -j$$(nproc) \
	    $$(find outputs derived -name '*.csv' ! -name 'reconciliation_*' ! -path '*/_extracted/*' | sed 's/\.csv$$/.record.json/')
	@shopt -s nullglob; \
	for f in outputs/*/*-run*.json outputs/*/*/*-run*.json derived/*/*-run*.json; do \
	    [ -f "$${f%.json}.csv" ] && continue; \
	    rec="$${f%.json}.record.json"; \
	    [ -f "$$rec" ] && [ "$$rec" -nt "$$f" ] && continue; \
	    $(EVAL) evaluate "$$f" --output "$$(dirname $$f)"; \
	done

.PHONY: rebuild-measurements
rebuild-measurements:
	find outputs derived -name '*.record.json' ! -path '*/_extracted/*' -delete
	$(MAKE) --no-print-directory ../measurements.jsonl

# --- Analysis: self-consistency -----------------------------------------------

SC_INPUT  := outputs/rag
SC_OUTPUT := derived/rag_consistency
SC_JSON   := $(SC_OUTPUT)/self_consistency_summary.json
SC_TEX    := ../report/inputs/generated/tab_self_consistency.tex
SC_PERRUN := ../report/inputs/generated/tab_per_run.tex

.PHONY: self-consistency

$(SC_JSON): $(wildcard $(SC_INPUT)/*.json) ../src/aedist/self_consistency.py
	$(UV_RUN) python -m aedist.self_consistency \
	    --input $(SC_INPUT) --output $(SC_OUTPUT) --measurements ../measurements.jsonl

$(SC_TEX) $(SC_PERRUN) &: ../measurements.jsonl ../src/aedist/tabulate_self_consistency.py
	$(UV_RUN) python -m aedist.tabulate_self_consistency \
	    --output $(SC_TEX) --per-run-output $(SC_PERRUN)

self-consistency: $(SC_TEX) $(SC_PERRUN)

# --- Experiment 1 cost summary ----------------------------------------------

EXP1_COST_TEX := ../report/inputs/generated/tab_exp1_cost_summary.tex

$(EXP1_COST_TEX): ../measurements.jsonl ../src/aedist/tabulate_exp1_cost_summary.py
	$(UV_RUN) python -m aedist.tabulate_exp1_cost_summary \
	    --measurements ../measurements.jsonl --output $(EXP1_COST_TEX)

.PHONY: exp1-cost-summary
exp1-cost-summary: $(EXP1_COST_TEX)

EXP1_TOPUP_TEX := ../report/inputs/generated/tab_exp1_reasoning_topup.tex

$(EXP1_TOPUP_TEX): ../measurements.jsonl ../src/aedist/tabulate_exp1_reasoning_topup.py
	$(UV_RUN) python -m aedist.tabulate_exp1_reasoning_topup \
	    --measurements ../measurements.jsonl --output $(EXP1_TOPUP_TEX)

.PHONY: exp1-reasoning-topup
exp1-reasoning-topup: $(EXP1_TOPUP_TEX)

# --- Utility -----------------------------------------------------------------

# Convert a PDF to Markdown for the RAG corpus.
# Usage: make pdf2md PDF=path/to/file.pdf [MODEL=gpt-4o] [DPI=300]
MODEL ?= gpt-4o
DPI   ?= 300

# Load Zotero API key from .env or ~/.claude/.env
ifeq ($(ZOTERO_API_KEY),)
  ZOTERO_API_KEY := $(shell grep '^ZOTERO_API_KEY=' ../.env 2>/dev/null | cut -d= -f2-)
endif
ifeq ($(ZOTERO_API_KEY),)
  ZOTERO_API_KEY := $(shell grep '^ZOTERO_API_KEY=' ~/.claude/.env 2>/dev/null | cut -d= -f2-)
endif
export ZOTERO_API_KEY

# Build RAG corpus configuration
CORPUS_OUTPUT  ?= data/rag_corpus
CORPUS_WORKDIR ?= data/rag_work
CORPUS_CONVERT ?= grobid
CORPUS_VISION  ?= gemma4:31b
CORPUS_SCORER  ?= qwen3.5:9b
CORPUS_REF     ?= ../report/inputs/README.md

.PHONY: pdf2md build-corpus preflight help

pdf2md:
ifndef PDF
	$(error PDF variable is required. Usage: make pdf2md PDF=path/to/file.pdf)
endif
	$(UV_RUN) --extra pdf python -m aedist.pdf2md_openrouter $(PDF) \
	    --model $(MODEL) --dpi $(DPI)

build-corpus:
ifndef ITEMS
ifndef QUERY
	$(error Specify ITEMS=key1,key2 or QUERY="search terms")
endif
endif
	@grep -q '^ZOTERO_API_KEY=' ../.env || { echo "ZOTERO_API_KEY missing from ../.env — copy from ~/.claude/.env if you have one"; exit 1; }
	$(UV_RUN) --extra pdf python -m aedist.build_corpus \
	    $(if $(ITEMS),--items $(ITEMS),--query "$(QUERY)") \
	    --reference $(CORPUS_REF) \
	    --output $(CORPUS_OUTPUT) --work-dir $(CORPUS_WORKDIR) \
	    --converter $(CORPUS_CONVERT) --local-vision-model $(CORPUS_VISION) \
	    --scorer-model $(CORPUS_SCORER)

preflight:
	@echo "=== AEDIST Preflight Checks ==="
	@ok=true; \
	if [ -n "$(OPENROUTER_API_KEY)" ]; then \
	    printf "  ✓ OPENROUTER_API_KEY is set\n"; \
	else \
	    printf "  ✗ OPENROUTER_API_KEY not set\n"; ok=false; \
	fi; \
	if [ -n "$(ZOTERO_API_KEY)" ]; then \
	    printf "  ✓ ZOTERO_API_KEY is set\n"; \
	else \
	    printf "  ✗ ZOTERO_API_KEY not set (needed for build-corpus)\n"; \
	fi; \
	if [ -n "$(TAVILY_API_KEY)" ]; then \
	    printf "  ✓ TAVILY_API_KEY is set\n"; \
	else \
	    printf "  ✗ TAVILY_API_KEY not set (needed for web)\n"; \
	fi; \
	if command -v uv >/dev/null 2>&1; then \
	    printf "  ✓ uv found: $$(uv --version)\n"; \
	else \
	    printf "  ✗ uv not found on PATH\n"; ok=false; \
	fi; \
	if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then \
	    printf "  ✓ Ollama is running\n"; \
	else \
	    printf "  ✗ Ollama not reachable at localhost:11434\n"; \
	fi; \
	if curl -sf http://localhost:8070/api/isalive >/dev/null 2>&1; then \
	    printf "  ✓ GROBID is running\n"; \
	else \
	    printf "  ✗ GROBID not reachable at localhost:8070\n"; \
	fi; \
	if [ "$$ok" = "false" ]; then \
	    echo ""; echo "FAIL: critical checks failed"; exit 1; \
	else \
	    echo ""; echo "All critical checks passed."; \
	fi

help:
	@echo "Sweeps (manager + worker pipeline):"
	@echo "  make census               Generate jobs + run workers (model census)"
	@echo "  make census-generate      Fan out sweep config into per-model jobs"
	@echo "  make census-run           Drain queue (1 worker per pending job + 1 Padme)"
	@echo "  make regimes              Generate + run all information regimes"
	@echo "  make decomposed           Generate + run decomposition sweep"
	@echo "  make verification         Generate + run verification sweep"
	@echo "  make sourced              Generate + run sourced extraction sweep"
	@echo "  make frontier             Generate + run frontier deep-research (3 prompts)"
	@echo "  make rebuild-measurements Extract + evaluate all outputs → measurements.jsonl"
	@echo "  make self-consistency     Majority/union vote analysis + LaTeX tables"
	@echo ""
	@echo "Tools:"
	@echo "  make pdf2md PDF=file.pdf  Convert PDF to Markdown (for RAG corpus)"
	@echo "  make build-corpus ITEMS=SSRTCPP8,44XYCWMC  Build corpus from Zotero PDFs"
	@echo "  make build-corpus QUERY='thermal power'     Build corpus from Zotero search"
	@echo ""
	@echo "  make preflight             Check env vars and services before long jobs"
	@echo ""
	@echo "Config in experiments.toml [sweeps.*] sections"
	@echo "Job board in jobs/{pending,running,done,failed}/"
