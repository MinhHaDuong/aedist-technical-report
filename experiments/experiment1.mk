# experiment1.mk — Exp 1 parametric baseline (no web search)
#
# Run from the experiments/ directory:
#   make -f experiment1.mk exp1-batch2
#
# Parallelism: manager fans out 60 jobs (12 models × 5 reps) to jobs/pending/,
# then WORKERS worker processes drain the queue concurrently.
# Set WORKERS on the command line: make -f experiment1.mk WORKERS=12 exp1-batch2

include common.mk

SWEEP   := sweep_exp1_batch2
JOBS    := $(CURDIR)/jobs/exp1_batch2
WORKERS := 12

# ─── Batch 2 ──────────────────────────────────────────────────────────────────

.PHONY: exp1-batch2 exp1-generate exp1-drain exp1-status

exp1-batch2: exp1-generate exp1-drain

exp1-generate:
	$(UV_RUN_ROOTPATH) python -m aedist.manager generate \
	    --sweep $(SWEEP) \
	    --jobs-dir $(JOBS)

exp1-drain:
	seq $(WORKERS) | xargs -P $(WORKERS) -I{} \
	    $(UV_RUN_ROOTPATH) python -m aedist.worker openrouter --jobs-root $(JOBS) --drain

exp1-status:
	@echo "pending:  $$(ls $(JOBS)/pending/ 2>/dev/null | wc -l)"
	@echo "running:  $$(ls $(JOBS)/running/ 2>/dev/null | wc -l)"
	@echo "done:     $$(ls $(JOBS)/done/    2>/dev/null | wc -l)"
	@echo "failed:   $$(ls $(JOBS)/failed/  2>/dev/null | wc -l)"
