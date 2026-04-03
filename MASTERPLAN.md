# MASTERPLAN — AEDIST Methods Benchmark

## Vision

Demonstrate — with reproducible quantitative evidence — what AI methods can
and cannot do for statistical production. Not which model is best, but which
**method** produces a trustworthy statistical table from open sources.

A method is the whole pipeline: prompt design, information regime, extraction
logic, reconciliation strategy, verification pass. A model is one parameter.

The benchmark is also a feasibility study. The code that measures methods
*becomes* the production pipeline. The measurements table becomes the audit
log. The evaluation metrics become quality monitoring.

## Why this matters

Statistical offices need infrastructure inventories and cannot always
produce them: Vietnam's thermal power plants, Sub-Saharan grid assets,
industrial emissions sources. The data exists in fragments across
languages, formats, and jurisdictions.

The question is not "can GPT-5 list power plants?" but "what method
reliably produces a publishable statistical table, at what cost, with
what justification?"

### Use cases that drive different quality requirements

| Use case | Needs | Tolerance |
|----------|-------|-----------|
| Integrated assessment models | Complete coverage, capacity accuracy | Can accept aggregates |
| Infrastructure mapping | Geolocation, status, commissioning dates | Tolerates gaps if flagged |
| Business intelligence | Timeliness, ownership, planned capacity | Needs update pipeline |
| Military targeting | Zero hallucination, source provenance | No tolerance for fabrication |
| Legal defense | Auditable trail, confidence intervals | Needs "I don't know" |

One pipeline, different quality bars. The benchmark measures all levels.

## Multi-level evaluation framework

### Level 1 — Resources (measured now)
Wall time, API cost, token counts, CO₂ estimate.
Every run has a price tag.

### Level 2 — Document quality (measured now)
Benchmark against gold standard: coverage, precision, F1, attribute
accuracy, capacity error, hallucination rate.
The table either matches reality or it doesn't.

### Level 3 — Findings justification (to build)
The table comes with sources and notes. Claims are attributed.
The method says "I don't know" when uncertain.
Confidence intervals on counts and capacities.
Statistical quality, not just accuracy.

### Level 4 — System usability (to build)
Can the method scale to other countries? Update when plants change status?
Fill gaps from totals? Resolve incoherences or escalate them?
Prioritize sources when they conflict?

## Final desired state

### The measurements table

One table of truth. One row per run.

```
run_id
timestamp
method                    -- single-shot, multiturn, rag-wholesale, web, ...
method_params             -- JSON: model, endpoint, prompt hash, regime, ...
resource_use              -- JSON: wall_s, cost_usd, tokens_in, tokens_out
result_file               -- path to raw output
result_summary            -- JSON: status, n_plants, TP, FP, FN, F1, ...
justification             -- JSON: sources_provided, sources_verified, ...
```

Methods and models have their own description tables (static metadata).
Each repeat is a row. Tables for the report are views.

### The job board

Workers on a shared filesystem, not microservices. One node.

```
jobs/
  pending/    ← experiment manager writes job specs (priority-prefixed)
  running/    ← worker takes a lease (rename, expiry timestamp)
  done/       ← completed job + result row for measurements table
  failed/     ← with error log, eligible for retry
```

Experiment manager: reads YAML experiment spec, writes job files.
Workers (technicians): examine job, estimate duration, run with timeout
guard. The running slot is a lease with an expiration date — if the
worker dies, the lease expires and the job returns to pending.

Padme worker: sequential (one GPU). Remote worker: parallel (rate-limited).
Each worker logs independently. Observer is external.

### The pipeline

The benchmark pipeline *is* the production pipeline with a test harness
bolted on. In production:
- Input: "produce table of thermal plants in Vietnam"
- Method: best method from benchmark (e.g. RAG-wholesale + verification)
- Output: statistical table + quality report + audit trail
- Monitoring: new rows in measurements table, anomaly detection on metrics

## How we get there

### Phase 1: Econom'IA presentation (April 3–10, 2026)

Present "methods benchmark" with data from sweeps 1–2.

**Work remaining:**
- Run sweep 2: 5 models × 3 methods × 3 runs (#10)
- Merge cost/latency into metrics (#59)
- Tabulate relances (#47) and comparison (#48)
- Reframe slides: methods not models, multi-level evaluation vision

**What we show:**
- Level 1 (resources): Pareto chart, cost table
- Level 2 (quality): census results, method comparison
- Levels 3–4: vision slide, not data yet

**Deferred:** pipeline UX (#22), reasoning sweep (#11), verification
sweep (#12), sensitivity (#13), code quality (#30, #35, #36)

### Phase 2: Measurements table (post-conference)

Replace `all_metrics.json` with a proper schema.

- Pydantic model for run records
- Migration: existing sweep 1 + sweep 2 JSONs → measurements table
- All report tables derived from measurements (single source of truth)
- Retire the patchwork of `all_metrics.json` + per-sweep summaries

### Phase 3: Job board (post-conference)

Replace Makefile sweeps with file-based job execution.

- Job spec format (YAML)
- Experiment manager script
- Timeout-guarded worker with lease semantics
- Padme worker (sequential) and OpenRouter worker (parallel)
- Resume = re-scan pending + check lease expiry on running
- Run sweeps 3–5 (#11, #12, #13) on the new infrastructure

### Phase 4: Justification layer

Level 3 evaluation.

- Extend query methods to request source attribution
- Parse and validate source citations
- "I don't know" detection and scoring
- Confidence interval estimation on aggregates
- Verification sweep (#12) produces the first justification data

### Phase 5: Usability evaluation

Level 4 evaluation.

- Test with second country (scale)
- Test with updated reference data (temporal stability)
- Gap-filling from aggregate constraints
- Incoherence detection and escalation protocol
- Source prioritization when references conflict

### Phase 6: Journal submission

Package phases 1–5 into a paper.

- Methods benchmark results (sweeps 1–5)
- Multi-level evaluation framework with data at all levels
- Architecture: from benchmark to production pipeline
- Reproducibility: the code *is* the evidence
