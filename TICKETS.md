# Sequenced Development Tickets — Workers Architecture Migration

> Gated phases: each phase's entry ticket blocks all subtasks in the next
> phase. Existing GitHub issue numbers are referenced where they exist;
> new tickets are marked **[NEW]**.

---

## Phase 1 — Econom'IA presentation (gate: April 11, 2026)

> **No Workers work here.** Ship on existing Makefile pipeline.

### P1.1 — Complete Sweep 2 (#10)
- [ ] P1.1a Build RAG corpus: `make build-corpus`
- [ ] P1.1b Run Sweep 2 RAG (`sweep2-rag`)
- [ ] P1.1c Run Sweep 2 web (`sweep2-web`)

### P1.2 — Cost data in Pareto chart (#59)
- [ ] P1.2a Merge cost + latency fields into `all_metrics.json`
- [ ] P1.2b Update `plot_pareto.py` to read cost column

### P1.3 — Tabulate results (#47, #48)
- [ ] P1.3a Tabulate relances (#47) — multiturn follow-up analysis
- [ ] P1.3b Tabulate comparison (#48) — method comparison table

### P1.4 — Fix API key guard (#75)
- [ ] P1.4a Guard `OPENROUTER_API_KEY` only for OpenRouter sweep targets
- [ ] P1.4b Padme / corpus targets must work without the key

### P1.5 — Slides: reframe methods not models
- [ ] P1.5a Update slides to multi-level evaluation framing

**Gate:** Phase 1 complete when Sweep 2 data is in, tables and charts
render, slides ready. All existing pipeline code stays as-is.

---

## Phase 2 — Measurements table **[NEW]**

> **Prerequisite for Workers.** Creates the unified data layer that
> Workers will write into. Start immediately after conference.

### P2.1 — Define RunRecord schema **[NEW]**
- [ ] P2.1a Define `RunRecord` Pydantic model in `src/aedist/schema.py`
  - Fields: `run_id`, `timestamp`, `method` (single/multiturn/rag/web),
    `method_params` (JSON), `resource_use` (JSON: wall_s, cost_usd,
    tokens_in, tokens_out), `result_file`, `result_summary` (JSON:
    status, n_plants, TP, FP, FN, F1), `justification` (JSON)
- [ ] P2.1b Add `Method` and `MethodParams` Pydantic models
- [ ] P2.1c Add serialization: RunRecord ↔ JSON lines file
- [ ] P2.1d Unit tests for schema round-trip

### P2.2 — Migrate existing results **[NEW]**
> Blocked by: P2.1
- [ ] P2.2a Write migration script: sweep 1 JSONs → RunRecord rows
- [ ] P2.2b Write migration script: sweep 2 JSONs → RunRecord rows
- [ ] P2.2c Validate: migrated table row count = expected run count
- [ ] P2.2d Commit `measurements.jsonl` as canonical data file

### P2.3 — Reporting reads from measurements **[NEW]**
> Blocked by: P2.2
- [ ] P2.3a Refactor `summarize_sweep.py` to read from measurements table
- [ ] P2.3b Refactor `tabulate_census.py` to read from measurements table
- [ ] P2.3c Refactor `plot_pareto.py` to read from measurements table
- [ ] P2.3d Refactor `plot_census.py` to read from measurements table
- [ ] P2.3e `runner.py evaluate-all` appends RunRecord rows (not `all_metrics.json`)

### P2.4 — Retire patchwork **[NEW]**
> Blocked by: P2.3 (all reporting works on new table)
- [ ] P2.4a Remove `all_metrics.json` generation path
- [ ] P2.4b Remove per-sweep summary CSV generation
- [ ] P2.4c Update `experiments/Makefile` summary targets

**Gate:** All report tables and charts derive from `measurements.jsonl`.
No code reads `all_metrics.json`. Old summary paths deleted.

---

## Phase 3 — Job board + Workers **[NEW]**

> The Workers architecture itself. Blocked by Phase 2 (needs RunRecord
> to write results into).

### P3.1 — Job spec format **[NEW]**
- [ ] P3.1a Define `JobSpec` Pydantic model in `src/aedist/schema.py`
  - Fields: `job_id`, `priority`, `mode` (single/multiturn/rag/web),
    `prompt`, `models_file`, `model_filter`, `corpus` (optional),
    `strategy` (optional), `repeat`, `budget_usd`, `output_dir`,
    `timeout_seconds`, `estimated_duration`, `worker_pool`
    (openrouter/padme)
- [ ] P3.1b Define `LeaseInfo` model: `job_id`, `worker_id`,
    `start_time`, `expiry_time`
- [ ] P3.1c Unit tests for JobSpec serialization

### P3.2 — Experiment manager **[NEW]**
> Blocked by: P3.1
- [ ] P3.2a `src/aedist/manager.py`: read sweep YAML, fan out one
    JobSpec per (model × run) into `jobs/pending/`
- [ ] P3.2b Priority-prefix filenames: `{priority:03d}-{job_id}.yaml`
- [ ] P3.2c Idempotent: skip if job file already exists in any state dir
- [ ] P3.2d CLI: `python -m aedist.manager generate sweeps/sweep2_rag.yaml`
- [ ] P3.2e Unit tests: correct fan-out count, idempotency

### P3.3 — Worker skeleton **[NEW]**
> Blocked by: P3.1, P2.1 (writes RunRecord)
- [ ] P3.3a `src/aedist/worker.py`: base `Worker` class
  - `poll()`: scan `jobs/pending/`, pick highest priority
  - `acquire(job)`: atomic rename to `jobs/running/{id}-lease-{ts}.yaml`
  - `execute(job)`: abstract — calls appropriate `query*.py` function
  - `complete(job, result)`: move to `jobs/done/`, append RunRecord
  - `fail(job, error)`: move to `jobs/failed/`, write error log
- [ ] P3.3b Timeout guard: kill execution if `timeout_seconds` exceeded
- [ ] P3.3c Lease expiry timestamp embedded in running filename
- [ ] P3.3d Integration test: job flows pending → running → done

### P3.4 — Padme worker **[NEW]**
> Blocked by: P3.3
- [ ] P3.4a Subclass `Worker` → `PadmeWorker`
- [ ] P3.4b Sequential execution (one model at a time via Ollama)
- [ ] P3.4c `--base-url http://localhost:11434/v1` passed to harness
- [ ] P3.4d CLI: `python -m aedist.worker padme`

### P3.5 — OpenRouter worker **[NEW]**
> Blocked by: P3.3
- [ ] P3.5a Subclass `Worker` → `OpenRouterWorker`
- [ ] P3.5b Parallel execution with configurable concurrency
- [ ] P3.5c Rate limiting + per-job and global budget tracking
- [ ] P3.5d CLI: `python -m aedist.worker openrouter --concurrency 8`

### P3.6 — Observer **[NEW]**
> Blocked by: P3.3
- [ ] P3.6a `src/aedist/observer.py`: scan `jobs/running/` for expired leases
- [ ] P3.6b Requeue expired jobs to `jobs/pending/`
- [ ] P3.6c Status report: counts per directory, stalled jobs, cost so far
- [ ] P3.6d CLI: `python -m aedist.observer [--requeue]`

### P3.7 — Retire Makefile sweep dispatch **[NEW]**
> Blocked by: P3.4, P3.5 (both workers operational)
- [ ] P3.7a Replace `experiments/Makefile` sweep targets with manager calls
- [ ] P3.7b Keep summary/reporting targets (they read measurements table)
- [ ] P3.7c Update `make help` text
- [ ] P3.7d #75 becomes moot — workers manage their own credentials

**Gate:** `python -m aedist.manager generate` + `python -m aedist.worker`
can execute a full sweep. Makefile sweep targets retired.

---

## Phase 4 — Run remaining sweeps on Workers infra

> Blocked by: Phase 3 gate. These existing tickets now run on the new
> infrastructure instead of the Makefile.

### P4.1 — Reasoning effort sweep (#11)
- [ ] P4.1a Write `sweeps/sweep3_reasoning.yaml`
- [ ] P4.1b Generate jobs, run on Padme worker (reasoning models)
- [ ] P4.1c Results land in measurements table automatically

### P4.2 — Verification sweep (#12)
- [ ] P4.2a Write `sweeps/sweep4_verification.yaml`
- [ ] P4.2b Define verification pass method (extends query pipeline)
- [ ] P4.2c Generate jobs, run on OpenRouter worker
- [ ] P4.2d First provenance data captured (sources, confidence)

### P4.3 — Sensitivity analysis (#13)
- [ ] P4.3a Write `sweeps/sweep5_sensitivity.yaml`
- [ ] P4.3b Parameter variations as separate job specs
- [ ] P4.3c Generate jobs, run, analyze variance across repeats

---

## Phase 5 — Output provenance (Level 3 evaluation)

> Blocked by: Phase 2 gate (measurements table). Can start alongside
> Phase 3-4. Depends on #12 for first data.

### P5.1 — Source attribution **[NEW]**
- [ ] P5.1a Extend query methods to request source citations
- [ ] P5.1b Parse and validate citations in extraction step
- [ ] P5.1c Add `sources_provided`, `sources_verified` to RunRecord.justification

### P5.2 — Uncertainty handling **[NEW]**
- [ ] P5.2a "I don't know" detection and scoring
- [ ] P5.2b Confidence interval estimation on capacity aggregates
- [ ] P5.2c Add confidence metrics to result_summary

---

## Phase 6 — Usability evaluation (Level 4)

> Blocked by: Phase 3 gate (Workers running). Can start alongside Phase 5.

### P6.1 — Scale test **[NEW]**
- [ ] P6.1a Test with second country (same pipeline, different reference)
- [ ] P6.1b Test with updated reference data (temporal stability)

### P6.2 — Pipeline intelligence **[NEW]** (#22)
- [ ] P6.2a Gap-filling from aggregate constraints
- [ ] P6.2b Incoherence detection and escalation
- [ ] P6.2c Source prioritization when references conflict

---

## Deferred / backlog (no phase assignment yet)

| Ticket | Description | Notes |
|--------|-------------|-------|
| #22 | Pipeline UX | Folded into P6.2 |
| #30 | Code quality | Independent, do anytime |
| #35 | Code quality | Independent, do anytime |
| #36 | Code quality | Independent, do anytime |

---

## Dependency graph

```
Phase 1 (conference)
    │
    v
Phase 2 (measurements table)
    │
    ├──────────────────┐
    v                  v
Phase 3 (workers)    Phase 5 (provenance)
    │                  │
    ├────────┐         │
    v        v         v
Phase 4    Phase 6   (merge into journal paper)
(sweeps)   (usability)
    │        │         │
    v        v         v
         Phase 7 (journal submission)
```
