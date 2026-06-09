# experiments/common.mk — shared plumbing for the experiment makefiles.
#
# Single source of truth for the canonical uv invocation, the manager/worker
# entry points, OpenRouter concurrency, and the worker-drain loop. Included by
# experiments/acquire.mk and the experiment*.mk runners so they cannot drift.
#
# ENV POLICY (see experiments/acquire.mk header): the project ../.env is the only
# source of API keys; never ~/.claude/.env. UV_RUN injects it via --env-file at
# child-process spawn time, so no secret transits a Make variable or argv.

SHELL := /bin/bash
.SHELLFLAGS := -o pipefail -c

# Atomicity: delete a target whose recipe crashes mid-write so Make never sees a
# partial file with a fresh mtime as up-to-date. Set here as the single source
# for the three invocation roots that include this file (acquire.mk +
# experiment1.mk + experiment2.mk); a special target in an included file is
# honoured for the whole invocation (ticket 0461).
.DELETE_ON_ERROR:

# Canonical uv invocation: project venv + project .env.
UV_RUN := uv run --project .. --env-file ../.env

# Runners that execute `python sota/...` scripts importing `experiments.sota`
# need the repo root on PYTHONPATH (running a script file, not `python -m`).
UV_RUN_ROOTPATH := env PYTHONPATH=.. $(UV_RUN)

MANAGER := $(UV_RUN) python -m aedist.manager generate
WORKER  := $(UV_RUN) python -m aedist.worker

# Cap concurrent OpenRouter workers at the API rate limit (default 8).
# Override: make census-run OR_MAX=16
OR_MAX  ?= 8
OR_PENDING = $(words $(wildcard jobs/pending/*.yaml))
OR_JOBS = $(shell python3 -c "print(min($(OR_PENDING), $(OR_MAX)))")

# Fan out OR_JOBS OpenRouter workers in the background. Callers append any
# extra workers (e.g. Padme) and a final `wait`.
OR_DRAIN = for i in $$(seq 1 $(OR_JOBS)); do $(WORKER) openrouter --drain & done
