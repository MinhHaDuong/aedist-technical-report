# AEDIST Technical Report — Root Makefile
#
# The root holds the DEVELOPER LOOP (tests, lint, coverage, prompt inspection)
# plus the writing-side (P4) verbs CI invokes, and exposes the full data
# pipeline through EXACTLY TWO cross-phase entries:
#
#   make staleness   Dry-run report: what WOULD rebuild across P2 + P3 (+ P4).
#                    Touches nothing — safe to run anytime.
#   make world       Deliberate, full re-run of P2 + P3 + P4. Runs P2 scoring
#                    for REAL, which (re)writes committed scored data (the 0383
#                    mart-staleness hazard). REVIEW the result via `git diff`
#                    before committing. This is ticket 0360's reproducibility
#                    oracle: `make world && git diff --exit-code`.
#
# The four phases each own a makefile; per-phase dev work invokes them directly
# (README "Build pipeline" documents the conventions):
#
#   P1 Acquire  experiments/acquire.mk   make -C experiments -f acquire.mk <verb>
#               (money-gated API sweeps — cwd contract needs -C experiments)
#   P2 Score    experiments/derived/score.mk   make -f experiments/derived/score.mk <verb>
#   P3 Render   experiments/render.mk          make -f experiments/render.mk <verb>
#   P4 Write    report/Makefile, slides/Makefile   make report / make slides
#
# MECHANISM (tracker 0406 S5, ticket 0415): the two entries delegate to the
# phase makefiles by RECURSIVE $(MAKE) -f/-C, not literal `include`. A literal
# include would merge the P2 scoring rules into the root namespace, defeating
# the clean-room phase isolation the split exists to enforce (a P4 `make report`
# could then reach the scoring DAG) and risking default-goal hijack. Recursive
# delegation keeps each phase's namespace sealed and matches how every phase is
# already invoked (`-f <phase>.mk`). Tradeoff: `make world -n` is a sequence of
# per-phase dry-runs, so a clean checkout's P2→P3 chain only fully resolves once
# P2 outputs exist on disk; that is acceptable because `world` is a deliberate
# full re-run, not an incremental build.
#
# P1 (acquire) is EXCLUDED from world/staleness — it makes paid API calls, and a
# full re-run must never trigger a money-costing re-acquisition. Re-acquire raw
# replies only by explicitly invoking experiments/acquire.mk.

.PHONY: test test-fast test-slow coverage lint check-fast check show-prompts \
	report slides staleness world

# --- Tests --------------------------------------------------------------------

# Single source of truth for the fast/slow split. test-slow is the exact
# complement (negation), so the partition stays coherent if this expression
# changes — no second list to keep in sync.
FAST_MARKERS := not integration and not slow

test-fast:
	uv run pytest -m "$(FAST_MARKERS)"

test:
	uv run pytest

# Integration/slow complement of the fast suite, derived by negation so the
# two targets together run the full suite exactly once (no duplication, no
# gap). `make check` runs this after `coverage`.
test-slow:
	uv run pytest -m "not ($(FAST_MARKERS))"

# Coverage gate on the fast suite (the suite the floor was measured against:
# 73% on 2026-05-29). Floor starts at 70% — just under baseline — and ratchets
# up as new tests land. Kept off test-fast/check-fast so the dev loop stays
# quick; enforced via `make check` (and thus in CI through docs-build's
# `make check` step).
coverage:
	uv run pytest -m "$(FAST_MARKERS)" \
		--cov=src/aedist --cov-report=term-missing --cov-fail-under=70

lint:
	uv run ruff check src/ tests/ scripts/
	uv run python scripts/check_ticket_structure.py

check-fast: test-fast lint

check: coverage test-slow lint

# --- Prompt inspection -------------------------------------------------------

show-prompts:
	@uv run python -c "\
	from aedist.harness import assemble_prompt; \
	from pathlib import Path; \
	d = Path('experiments/prompts/modules'); \
	ALL = ['persona','overview','sourcing','narratives','bibliography','statistics']; \
	configs = [('base', []), ('composite', ALL)] + [(m, [m]) for m in ALL]; \
	[print(f'=== {n} ({len(assemble_prompt(d,ms).split(chr(10)))} lines) ===\n{assemble_prompt(d,ms)}\n') for n,ms in configs]"

# --- Publications (P4 write — pure clean-room delegations) --------------------
#
# `report` and `slides` compile the PDFs from COMMITTED P3 handoff artifacts
# (report/inputs/generated/**). They carry NO generated-file prerequisites: the
# writing build is clean-room (no `uv run`, no data pipeline), guarded by
# tests/test_report_build_clean_room.py and tests/test_slides_build_clean_room.py.
# To (re)generate the artifacts they consume, run the P3 render phase
# (`make -f experiments/render.mk <verb>`) or the full `make world`.

report:
	$(MAKE) -C report

slides:
	$(MAKE) -C slides

# --- Cross-phase entries: staleness (dry-run) and world (full re-run) ---------
#
# The full pipeline DAG behind two recursive entries. Phase legs, in order:
#   P2 score   experiments/derived/score.mk all-outcomes
#              → measurements.jsonl, exp2_mart.jsonl, both cross-eval CSVs, SC
#   P3 render  experiments/render.mk all   (every committed handoff artifact)
#   P4 write   -C report, -C slides        (the PDFs)
# P1 acquire is excluded (money gate — see header).

SCORE_MK := experiments/derived/score.mk
RENDER_MK := experiments/render.mk

# staleness: dry-run every phase leg, prefixed so the output reads as one
# report. Each leg is a `-n` (dry-run) sub-make, so staleness touches nothing
# and is always safe to run. P1 (acquire) is omitted — the money gate.
staleness:
	@echo '=== P2 score (experiments/derived/score.mk all-outcomes) ==='
	@$(MAKE) -n -f $(SCORE_MK) all-outcomes
	@echo '=== P3 render (experiments/render.mk all) ==='
	@$(MAKE) -n -f $(RENDER_MK) all
	@echo '=== P4 write (report) ==='
	@$(MAKE) -n -C report
	@echo '=== P4 write (slides) ==='
	@$(MAKE) -n -C slides

# world: DELIBERATE full re-run. The P2 leg runs scoring for real and REWRITES
# committed scored data (0383 mart staleness) — its OUTPUT MUST BE REVIEWED via
# `git diff` BEFORE COMMITTING. Cheap guard: refuse to start on a dirty working
# tree, so a re-score never silently mixes with unrelated uncommitted edits.
world:
	@git diff --quiet && git diff --cached --quiet || { \
		echo 'make world: working tree is dirty (unstaged or staged changes).'; \
		echo 'world rewrites committed scored data (0383) — commit or stash first,'; \
		echo 'then review the re-run via `git diff` before committing the result.'; \
		exit 1; }
	$(MAKE) -f $(SCORE_MK) all-outcomes
	$(MAKE) -f $(RENDER_MK) all
	$(MAKE) -C report
	$(MAKE) -C slides
