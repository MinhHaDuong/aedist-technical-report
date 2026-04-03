# aedist/Makefile — Reproducible experiment pipeline
#
# Each sweep is defined by a YAML config in sweeps/.
# Output files are Make targets: prompt or model list change → re-query.
#
# Usage:
#   make -j8 sweep1          # All models, 3 runs each (OpenRouter parallel, Padme sequential)
#   make sweep1-padme        # Padme local models only (always sequential)
#   make sweep1-summary      # Extract → evaluate → summarize
#
# Adding a model to models.yaml → `make sweep1` queries only the new model.

SHELL := /bin/bash
.SHELLFLAGS := -o pipefail -c

# --- Load API key from .env if not already set --------------------------------
ifeq ($(OPENROUTER_API_KEY),)
  OPENROUTER_API_KEY := $(shell grep '^OPENROUTER_API_KEY=' ../.env 2>/dev/null | cut -d= -f2-)
endif
export OPENROUTER_API_KEY
$(if $(OPENROUTER_API_KEY),,$(error OPENROUTER_API_KEY not set — export it or add to .env))

# --- Read sweep configs ------------------------------------------------------
cfg = $(shell python3 -c "import yaml; c=yaml.safe_load(open('sweeps/$(1).yaml')); print(c.get('$(2)',''))")

# --- Sweep 1: Model census ---------------------------------------------------

S1_PROMPT  := $(call cfg,sweep1_census,prompt)
S1_MODELS  := $(call cfg,sweep1_census,models)
S1_REPEAT  := $(call cfg,sweep1_census,repeat)
S1_BUDGET  := $(call cfg,sweep1_census,budget_usd)
S1_OUTPUT  := $(call cfg,sweep1_census,output)

S1P_MODELS := $(call cfg,sweep1_padme,models)

# Model short names → output file targets
S1_OR_SHORTS  = $(shell python3 -c "import yaml; ms=yaml.safe_load(open('$(S1_MODELS)')); print(' '.join(m['id'].split('/')[-1].replace(':','-') for m in ms))")
S1_PAD_SHORTS = $(shell python3 -c "import yaml; ms=yaml.safe_load(open('$(S1P_MODELS)')); print(' '.join(m['id'].replace(':','-') for m in ms))")

# Target: {output}/{model}-run{n}.json — one file per model per run
S1_OR_JSONS  = $(foreach m,$(S1_OR_SHORTS),$(foreach r,1 2 3,$(S1_OUTPUT)/$(m)-run$(r).json))
S1_PAD_JSONS = $(foreach m,$(S1_PAD_SHORTS),$(foreach r,1 2 3,$(S1_OUTPUT)/padme-$(m)-run$(r).json))

.PHONY: sweep1 sweep1-openrouter sweep1-padme sweep1-summary

sweep1: sweep1-openrouter sweep1-padme

sweep1-openrouter: $(S1_OR_JSONS)

# Padme: sequential — Ollama serves one model at a time
sweep1-padme:
	$(MAKE) -j1 $(S1_PAD_JSONS)

sweep1-summary:
	uv run --project .. python -m aedist.extract --input $(S1_OUTPUT) --output $(S1_OUTPUT)
	uv run --project .. python -m aedist.runner evaluate-all --outputs-dir $(S1_OUTPUT) --output ../results/summary
	uv run --project .. python -m aedist.summarize_sweep \
	    --metrics ../results/summary/all_metrics.json \
	    --queries $(S1_OUTPUT) \
	    --output ../results/summary/sweep1_summary.csv

# OpenRouter: query.py --repeat 3 produces all 3 run files in one call.
# Grouped target (GNU Make 4.3+): one recipe produces all 3 files.
define or_rule
$(S1_OUTPUT)/$(1)-run1.json $(S1_OUTPUT)/$(1)-run2.json $(S1_OUTPUT)/$(1)-run3.json &: $(S1_PROMPT) sweeps/sweep1_census.yaml
	$$(eval FULL_ID := $$(shell python3 -c "import yaml; ms=yaml.safe_load(open('$(S1_MODELS)')); hits=[m['id'] for m in ms if m['id'].split('/')[-1].replace(':','-')=='$(1)']; print(hits[0] if hits else '')"))
	@if [ -z "$$(FULL_ID)" ]; then echo "SKIP $(1)"; exit 0; fi
	uv run --project .. python -m aedist.query \
	    --prompt $(S1_PROMPT) --models $(S1_MODELS) \
	    --output $(S1_OUTPUT) --repeat $(S1_REPEAT) \
	    --budget-usd $(S1_BUDGET) --model $$(FULL_ID)
endef

$(foreach m,$(S1_OR_SHORTS),$(eval $(call or_rule,$(m))))

# Padme: aedist.query with --base-url for Ollama, --output-prefix padme.
define padme_rule
$(S1_OUTPUT)/padme-$(1)-run1.json $(S1_OUTPUT)/padme-$(1)-run2.json $(S1_OUTPUT)/padme-$(1)-run3.json &: $(S1_PROMPT) sweeps/sweep1_padme.yaml
	$$(eval OLLAMA_ID := $$(shell python3 -c "import yaml; ms=yaml.safe_load(open('$(S1P_MODELS)')); hits=[m['id'] for m in ms if m['id'].replace(':','-')=='$(1)']; print(hits[0] if hits else '')"))
	@if [ -z "$$(OLLAMA_ID)" ]; then echo "SKIP padme/$(1)"; exit 0; fi
	uv run --project .. python -m aedist.query \
	    --prompt $(S1_PROMPT) --models $(S1P_MODELS) \
	    --output $(S1_OUTPUT) --repeat $(S1_REPEAT) \
	    --model $$(OLLAMA_ID) \
	    --base-url http://localhost:11434/v1 \
	    --output-prefix padme
endef

$(foreach m,$(S1_PAD_SHORTS),$(eval $(call padme_rule,$(m))))

# --- Sweep 2: Information regimes ---------------------------------------------

S2MT_PROMPT := $(call cfg,sweep2_multiturn,prompt)
S2MT_FOLLOW := $(call cfg,sweep2_multiturn,followups)
S2MT_MODELS := $(call cfg,sweep2_multiturn,models)
S2MT_REPEAT := $(call cfg,sweep2_multiturn,repeat)
S2MT_BUDGET := $(call cfg,sweep2_multiturn,budget_usd)
S2MT_OUTPUT := $(call cfg,sweep2_multiturn,output)

S2R_PROMPT  := $(call cfg,sweep2_rag,prompt)
S2R_CORPUS  := $(call cfg,sweep2_rag,corpus)
S2R_STRAT   := $(call cfg,sweep2_rag,strategy)
S2R_MODELS  := $(call cfg,sweep2_rag,models)
S2R_REPEAT  := $(call cfg,sweep2_rag,repeat)
S2R_BUDGET  := $(call cfg,sweep2_rag,budget_usd)
S2R_OUTPUT  := $(call cfg,sweep2_rag,output)

S2W_PROMPT  := $(call cfg,sweep2_web,prompt)
S2W_MODELS  := $(call cfg,sweep2_web,models)
S2W_REPEAT  := $(call cfg,sweep2_web,repeat)
S2W_BUDGET  := $(call cfg,sweep2_web,budget_usd)
S2W_OUTPUT  := $(call cfg,sweep2_web,output)

.PHONY: sweep2 sweep2-multiturn sweep2-rag sweep2-web

sweep2: sweep2-multiturn sweep2-rag sweep2-web

sweep2-multiturn:
	uv run --project .. python -m aedist.query_multiturn \
	    --prompt $(S2MT_PROMPT) --followups $(S2MT_FOLLOW) \
	    --models $(S2MT_MODELS) --output $(S2MT_OUTPUT) \
	    --repeat $(S2MT_REPEAT) --budget-usd $(S2MT_BUDGET)

sweep2-rag:
	uv run --project .. python -m aedist.query_rag \
	    --prompt $(S2R_PROMPT) --corpus $(S2R_CORPUS) \
	    --strategy $(S2R_STRAT) --models $(S2R_MODELS) \
	    --output $(S2R_OUTPUT) --repeat $(S2R_REPEAT) \
	    --budget-usd $(S2R_BUDGET)

sweep2-web:
	uv run --project .. python -m aedist.query_web \
	    --prompt $(S2W_PROMPT) --models $(S2W_MODELS) \
	    --output $(S2W_OUTPUT) --repeat $(S2W_REPEAT) \
	    --budget-usd $(S2W_BUDGET)

# --- Utility -----------------------------------------------------------------

# Convert a PDF to Markdown for the RAG corpus.
# Usage: make pdf2md PDF=path/to/file.pdf [MODEL=gpt-4o] [DPI=300]
MODEL ?= gpt-4o
DPI   ?= 300

.PHONY: pdf2md help

pdf2md:
ifndef PDF
	$(error PDF variable is required. Usage: make pdf2md PDF=path/to/file.pdf)
endif
	uv run --project .. --extra pdf python -m aedist.pdf2md $(PDF) \
	    --model $(MODEL) --dpi $(DPI)

help:
	@echo "Sweeps:"
	@echo "  make -j8 sweep1           Census (OpenRouter parallel, Padme sequential)"
	@echo "  make sweep1-padme         Padme local models (always sequential)"
	@echo "  make sweep1-summary       Extract + evaluate + summarize"
	@echo "  make sweep2               All information regimes"
	@echo ""
	@echo "Tools:"
	@echo "  make pdf2md PDF=file.pdf  Convert PDF to Markdown (for RAG corpus)"
	@echo ""
	@echo "Config files in sweeps/*.yaml"
