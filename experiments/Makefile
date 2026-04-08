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

SHELL := /bin/bash
.SHELLFLAGS := -o pipefail -c

# --- Load API key from .env if not already set --------------------------------
ifeq ($(OPENROUTER_API_KEY),)
  OPENROUTER_API_KEY := $(shell grep '^OPENROUTER_API_KEY=' ../.env 2>/dev/null | cut -d= -f2-)
endif
export OPENROUTER_API_KEY

# Load Tavily API key from .env or ~/.claude/.env
ifeq ($(TAVILY_API_KEY),)
  TAVILY_API_KEY := $(shell grep '^TAVILY_API_KEY=' ../.env 2>/dev/null | cut -d= -f2-)
endif
ifeq ($(TAVILY_API_KEY),)
  TAVILY_API_KEY := $(shell grep '^TAVILY_API_KEY=' ~/.claude/.env 2>/dev/null | cut -d= -f2-)
endif
export TAVILY_API_KEY

# Guard: only require OPENROUTER_API_KEY for targets that actually need it.
# Workers inherit keys from the environment; the guard catches missing keys early.
_NEEDS_OPENROUTER := census census-run census-summary regimes regimes-run sourced sourced-run frontier frontier-run
ifneq ($(filter $(_NEEDS_OPENROUTER),$(MAKECMDGOALS)),)
  $(if $(OPENROUTER_API_KEY),,$(error OPENROUTER_API_KEY not set — export it or add to .env))
endif

_NEEDS_TAVILY := regimes-run
ifneq ($(filter $(_NEEDS_TAVILY),$(MAKECMDGOALS)),)
  $(if $(TAVILY_API_KEY),,$(error TAVILY_API_KEY not set — export it or add to .env))
endif

# --- Common -------------------------------------------------------------------
MANAGER := uv run --project .. python -m aedist.manager generate
WORKER  := uv run --project .. python -m aedist.worker
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

STRUCTURED_DIRS := census multiturn web rag \
                   decomposed sourced

OUTPUT_FILES := $(wildcard outputs/*/*.json) $(wildcard outputs/*/*.csv)

.PHONY: rebuild-measurements

# Force target: extract + full rebuild (ignores mtime)
rebuild-measurements:
	@for dir in $(STRUCTURED_DIRS); do \
	    uv run --project .. python -m aedist.extract \
	        --input outputs/$$dir --output outputs/$$dir; \
	done
	uv run --project .. python -m aedist.runner evaluate-all \
	    --outputs-dir outputs --measurements-output ../measurements.jsonl --full

# File target: incremental — Make skips when measurements.jsonl is newer than all outputs
../measurements.jsonl: $(OUTPUT_FILES)
	@for dir in $(STRUCTURED_DIRS); do \
	    uv run --project .. python -m aedist.extract \
	        --input outputs/$$dir --output outputs/$$dir; \
	done
	uv run --project .. python -m aedist.runner evaluate-all \
	    --outputs-dir outputs --measurements-output ../measurements.jsonl

# --- Analysis: self-consistency -----------------------------------------------

SC_INPUT  := outputs/rag
SC_OUTPUT := outputs/rag_consistency
SC_JSON   := $(SC_OUTPUT)/self_consistency_summary.json
SC_TEX    := ../report/inputs/generated/tab_self_consistency.tex
SC_PERRUN := ../report/inputs/generated/tab_per_run.tex

.PHONY: self-consistency

$(SC_JSON): $(wildcard $(SC_INPUT)/*.json) ../src/aedist/self_consistency.py
	uv run --project .. python -m aedist.self_consistency \
	    --input $(SC_INPUT) --output $(SC_OUTPUT) --measurements ../measurements.jsonl

$(SC_TEX) $(SC_PERRUN) &: ../measurements.jsonl ../src/aedist/tabulate_self_consistency.py
	uv run --project .. python -m aedist.tabulate_self_consistency \
	    --output $(SC_TEX) --per-run-output $(SC_PERRUN)

self-consistency: $(SC_TEX) $(SC_PERRUN)

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
CORPUS_VISION  ?= gemma4:26b
CORPUS_SCORER  ?= qwen3.5:9b
CORPUS_REF     ?= ../report/inputs/README.md

.PHONY: pdf2md build-corpus preflight help

pdf2md:
ifndef PDF
	$(error PDF variable is required. Usage: make pdf2md PDF=path/to/file.pdf)
endif
	uv run --project .. --extra pdf python -m aedist.pdf2md_openrouter $(PDF) \
	    --model $(MODEL) --dpi $(DPI)

build-corpus:
ifndef ZOTERO_API_KEY
	$(error ZOTERO_API_KEY not set — export it or add to .env)
endif
ifndef ITEMS
ifndef QUERY
	$(error Specify ITEMS=key1,key2 or QUERY="search terms")
endif
endif
	uv run --project .. --extra pdf python -m aedist.build_corpus \
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
