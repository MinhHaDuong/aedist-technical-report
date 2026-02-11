# AEDIST Technical Report
# ======================

export UV_CACHE_DIR := /scratch/uv

.PHONY: all query tables clean cleaner

all: report.pdf

# Query LLMs via OpenRouter (expensive, run manually)
query:
	uv run --project aedist aedist/src/query.py \
	    --prompt aedist/src/prompts/prompt1.txt \
	    --models aedist/src/models.yaml --output Results/1_simply_ask/

# Generate LaTeX tables and macros from results (cheap, run before build)
tables:
	uv run --project aedist aedist/src/convert.py --output inputs/generated/

report.pdf: report.tex refs.bib $(wildcard inputs/generated/*.tex)
	tectonic $<

# Intermediate files
clean:
	rm -f *.log *.bbl *.blg *.run.xml report.synctex.gz

# Also the output
cleaner: clean
	rm -f report.pdf
