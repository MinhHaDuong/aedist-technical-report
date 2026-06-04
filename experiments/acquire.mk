# experiments/acquire.mk — P1 ACQUIRE phase (tracker 0406, step S4 / ticket 0411)
#
# Phase:    P1 acquire. Run API sweeps against models; (re)acquire raw replies.
# Sources:  experiments.toml ([sweeps.*] sections), the RAG corpus, models.yaml.
# Outcomes: raw model replies under experiments/outputs/**, experiments/archive/**
#           (tracked by the 0405 policy). The worker pipeline writes these; they
#           are NOT make file targets.
# Invariant: EVERY target is .PHONY. P1 produces no file a downstream phase may
#           depend on — nothing in score.mk (P2) or render.mk (P3) may depend on
#           a P1 target as a file, or an ordinary timestamp rebuild could trigger
#           a money-costing re-acquisition. Enforced by
#           tests/test_acquire_all_phony.py.
#
# MONEY GATE: the sweep verbs below (census, regimes, decomposed, verification,
#   sourced, frontier) make real, paid OpenRouter API calls. NEVER run them on a
#   hunch. Test one before blasting: dry-run
#   (`make -C experiments -f acquire.mk -n census`) to inspect prompt assembly,
#   then one real call per regime, inspect tokens/cost/quality, then launch the
#   full batch. (The `-C experiments` is mandatory — the env contract resolves
#   ../.env / experiments.toml / jobs/ relative to experiments/; a bare
#   `-f experiments/acquire.mk` from repo root trips the .env sentinel.)
#
# Sweep configs live in [sweeps.*] sections of experiments.toml.
# Job dispatch is handled by the manager + worker pipeline:
#   1. `make census-generate`  — fan out sweep config into per-model jobs
#   2. `make census-run`       — start workers to execute the jobs
#
# Or simply: `make census` to generate + run in one step.
# Score & consolidate (P2) is a separate phase — see experiments/derived/score.mk.
#
# Invocation: per-phase .mks are the dev path. From the repo root, preserve the
# experiments/ cwd (the env/relative-path contract: ../.env, experiments.toml,
# jobs/) with `make -C experiments -f acquire.mk <sweep>`. After this rename,
# `make -C experiments` finds no default Makefile — that is intended.
#
# Adding a model to models.yaml → re-run generate (idempotent) + run.
#
# --- ENV POLICY ---------------------------------------------------------------
# All API keys live in the PROJECT .env (../.env relative to acquire.mk),
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
# Do NOT `export KEY := $(shell grep ...)` from acquire.mk — that puts
# values onto Make's command line and on into spawned process arguments,
# the same leak path we just closed.

# cwd-independent include: resolve common.mk relative to THIS makefile, not the
# caller's cwd, so the clean-room gate (`make -f experiments/acquire.mk -n ...`
# from repo root) parses without a "no such file" error.
include $(dir $(lastword $(MAKEFILE_LIST)))common.mk

# --- Sentinel: project .env exists for targets that need API keys -------------
# Targets in this list will fail fast with a readable message if .env is
# missing. Keys themselves are not read into Make variables — uv loads them
# at child-process spawn time via --env-file.
_NEEDS_ENV := census census-run regimes regimes-run \
						 sourced sourced-run frontier frontier-run
ifneq ($(filter $(_NEEDS_ENV),$(MAKECMDGOALS)),)
  $(if $(wildcard ../.env),,$(error ../.env not found — copy ../.env.example and populate API keys))
endif

# --- Common -------------------------------------------------------------------
# UV_RUN / UV_RUN_ROOTPATH / MANAGER / WORKER / OR_* / OR_DRAIN are defined in
# experiments/common.mk (included above) — the single source of truth shared
# with experiment1.mk and experiment2.mk.

# Read a single field from a sweep config in experiments.toml.
cfg = $(shell python3 -c "import tomllib; c=tomllib.load(open('experiments.toml','rb')); print(c['sweeps']['$(1)'].get('$(2)',''))")

# --- Census: model census -----------------------------------------------------

.PHONY: census census-generate census-run

census: census-generate census-run

census-generate:
	$(MANAGER) --sweep census --experiments experiments.toml
	$(MANAGER) --sweep census_local --experiments experiments.toml

census-run:
	$(OR_DRAIN); $(WORKER) padme --drain & wait

# Score & consolidate (P2) lives in experiments/derived/score.mk, invoked from
# the repo root: `make -f experiments/derived/score.mk rebuild-measurements`.
# (The former `census-summary` alias that delegated there was dropped in S4 /
# ticket 0411 — P1 acquire may not carry a cross-phase delegation edge.)

# --- Regimes: information regimes ---------------------------------------------

.PHONY: regimes regimes-generate regimes-run

regimes: regimes-generate regimes-run

regimes-generate:
	$(MANAGER) --sweep multiturn --experiments experiments.toml
	$(MANAGER) --sweep rag --experiments experiments.toml
	$(MANAGER) --sweep web --experiments experiments.toml

regimes-run:
	$(OR_DRAIN); wait

# --- Decomposed: task decomposition by fuel type -----------------------------

.PHONY: decomposed decomposed-generate decomposed-run

decomposed: decomposed-generate decomposed-run

decomposed-generate:
	$(MANAGER) --sweep decomposed --experiments experiments.toml

decomposed-run:
	$(OR_DRAIN); wait

# --- Verification: verification regimes --------------------------------------

.PHONY: verification verification-generate verification-run

verification: verification-generate verification-run

verification-generate:
	$(MANAGER) --sweep verification --experiments experiments.toml

verification-run:
	$(OR_DRAIN); wait

# --- Sourced: sourced extraction (citations upfront) -------------------------

.PHONY: sourced sourced-generate sourced-run

sourced: sourced-generate sourced-run

sourced-generate:
	$(MANAGER) --sweep sourced --experiments experiments.toml

sourced-run:
	$(OR_DRAIN); wait

# --- Frontier: deep-research models ------------------------------------------

.PHONY: frontier frontier-generate frontier-run

frontier: frontier-generate frontier-run

frontier-generate:
	$(MANAGER) --sweep frontier --experiments experiments.toml
	$(MANAGER) --sweep frontier_scenarios --experiments experiments.toml
	$(MANAGER) --sweep frontier_skill --experiments experiments.toml

frontier-run:
	$(OR_DRAIN); wait

# --- Score & consolidate (P2) and render (P3) now live elsewhere -------------
# extract / evaluate / measurements.jsonl / rebuild-measurements / the
# self-consistency scorer (the P2 score & consolidate phase) moved to
# experiments/derived/score.mk (tracker 0406 S3, ticket 0410). The
# self-consistency / exp1-cost-summary / exp1-reasoning-topup LaTeX tables (the
# P3 render half) moved to experiments/render.mk. Both are invoked from the
# repo root:
#     make -f experiments/derived/score.mk rebuild-measurements
#     make -f experiments/render.mk self-consistency
# acquire.mk is now pure P1 acquire (sweeps) + corpus utilities.

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
	@echo ""
	@echo "Score & render (run from repo root):"
	@echo "  make -f experiments/derived/score.mk rebuild-measurements  Extract + evaluate → measurements.jsonl (P2)"
	@echo "  make -f experiments/render.mk self-consistency             Majority/union vote LaTeX tables (P3)"
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
