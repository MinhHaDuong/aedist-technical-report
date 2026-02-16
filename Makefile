# AEDIST Technical Report
# ======================

export UV_CACHE_DIR := /scratch/uv

AEDIST       := aedist
RESULTS      := Results/1_simply_ask
GENERATED    := inputs/generated

.PHONY: all query evaluate tables clean cleaner

all: report.pdf

# ---------------------------------------------------------------------------
# Data pipeline (run manually, costs money / time)
# ---------------------------------------------------------------------------

# Query LLMs via OpenRouter (~$5 per full run)
query:
	uv run --project $(AEDIST) python -m aedist.query \
	    --prompt $(AEDIST)/prompts/prompt_1_singleshot.txt \
	    --models $(AEDIST)/models.yaml \
	    --output $(RESULTS)/

# Evaluate all system outputs against reference → JSON metrics
evaluate:
	uv run --project $(AEDIST) python -m aedist.runner evaluate-all \
	    --outputs-dir $(AEDIST)/outputs \
	    --output $(AEDIST)/results/summary

# ---------------------------------------------------------------------------
# LaTeX generation (cheap, run before build)
# ---------------------------------------------------------------------------

# Generate LaTeX tables and macros from results
tables:
	uv run --project $(AEDIST) python -m aedist.convert \
	    --output $(GENERATED)/

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

report.pdf: report.tex refs.bib $(wildcard $(GENERATED)/*.tex)
	tectonic $

# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------

clean:
	rm -f *.log *.bbl *.blg *.run.xml report.synctex.gz

cleaner: clean
	rm -f report.pdf
