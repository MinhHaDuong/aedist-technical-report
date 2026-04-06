# MASTERPLAN — AEDIST Methods Benchmark

> This document is the long-term vision. STATE.md tracks the current
> milestone's operational checkboxes. When they overlap, STATE.md governs
> what to do this week; MASTERPLAN governs why.

## Vision

Demonstrate — with reproducible quantitative evidence — what AI methods can
and cannot do for statistical production. Not which model is best, but which
**method** produces a trustworthy statistical table from open sources.

A method is the whole pipeline: prompt design, information regime, extraction
logic, reconciliation strategy, verification pass. A model is one parameter.

The benchmark converges toward the production pipeline. Its measurements
table becomes the audit log. Its evaluation metrics become quality monitoring.
Design decisions are made with this convergence in mind.

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
| Regulatory compliance | Zero hallucination, source provenance | No tolerance for fabrication |
| Legal defense | Auditable trail, confidence intervals | Needs "I don't know" |

One pipeline, different quality bars. The benchmark measures all levels.

## Multi-level evaluation framework

### Level 1 — Resources (measured now)
Wall time, API cost, token counts.
CO₂ estimate aspirational (requires CodeCarbon or provider-reported data).
Every run has a price tag.

### Level 2 — Document quality (measured now)
Benchmark against gold standard: coverage, precision, F1, attribute
accuracy, capacity error, hallucination rate.
The table either matches reality or it doesn't.

### Level 3 — Output provenance (to build)
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
- Run sweep 2 (#10): 5 models × 3 information regimes (multi-turn,
  RAG-wholesale, web-augmented) × 3 runs = 45 calls
- Merge cost/latency into metrics (#59)
- Tabulate relances (#47) and comparison (#48)
- Reframe slides: methods not models, multi-level evaluation vision

**What we show:**
- Level 1 (resources): Pareto chart, cost table
- Level 2 (quality): census results, method comparison
- Levels 3–4: vision slide, not data yet

**Deferred:** pipeline UX (#22), reasoning sweep (#11), verification
sweep (#12), sensitivity (#13), code quality (#30, #35, #36)

### Phase 2: Measurements table ✓

Completed (#157). `measurements.jsonl` is the single data source.
All report tables derived from it. `all_metrics.json` retired.

### Phase 3: Primary-source pipeline (#98)

Apply the best benchmarked method (RAG-wholesale + query decomposition,
F1=99%, $0.06) to primary Vietnamese government documents. The benchmark
and pipeline are mutually reinforcing: the pipeline produces a better gold
standard, the benchmark evaluates pipeline quality.

**5-step prompt chain:**

1. **PDP8 annexes** — Retrieve Decision 1509/QĐ-BCT annexes: thermal
   project tables (coal pipeline, LNG 2025–2030/2031–2035, domestic gas).
   Extract: name, province, capacity MW, timeline, investor, status.
2. **Operational stock** — Reconstruct the fleet in operation from EVN
   annual report and ERAV data. Columns: plant name (Vietnamese + English),
   province, fuel, capacity, units, COD, owner, PDP reference.
3. **Decisional chronology** — For each plant (batched by 10–15), trace
   the administrative history from primary sources: PDP inscription,
   modifications across successive PDPs, investment certificate,
   environmental licence, construction start, COD (planned vs actual),
   cancellation if applicable. Rule: if no primary source, write
   "[source primaire non localisée]" — never substitute with GEM or
   Wikipedia.
4. **Historico-prospective analysis** — Periodization by PDP (PDP6 pre-2006,
   PDP7 2006–2016, PDP7R→PDP8 2016–2023, PDP8→PDP8 revised 2023–2025,
   post-2030 exit scenarios). Realization rates per PDP, cancellation
   dynamics, GNL pivot, nuclear return.
5. **Assembly** — Citable report with provenance chain. Each datum traces
   to an identified primary document; gaps are flagged honestly.

**Practical constraints:**
- PDP annexes are in Vietnamese, published on thuvienphapluat.vn or
  government portal — some are scanned PDF images, not text
- EVN annual reports not always freely accessible in full
- Per-project decisions (investment certificates, ĐTM) are dispersed
- Token budget: 10+ batches of 15 plants may overflow multi-turn context

**Infrastructure from benchmark that serves this phase:**

| Pipeline step | Benchmark infrastructure | Status |
|---|---|---|
| Step 1 (PDP annexes) | PDF→MD converters + RAG wholesale | Converters benchmarked (#85, #167) |
| Step 2 (EVN stock) | Web-augmented queries | sweep2-web done |
| Step 3 (chronologies) | Multi-turn conversations | sweep2-multiturn done |
| Step 5 (assembly) | Reconciliation LP + evaluation | Done, 423 tests |

### Phase 4: Job board (post-conference)

Replace Makefile sweeps with file-based job execution.

- Job spec format (YAML)
- Experiment manager script
- Timeout-guarded worker with lease semantics
- Padme worker (sequential) and OpenRouter worker (parallel)
- Resume = re-scan pending + check lease expiry on running
- Run sweeps 3–5 (#11, #12, #13) on the new infrastructure

### Phase 5: Output provenance (depends on phases 2, 3)

Level 3 evaluation. Can start alongside phase 4.

- Extend query methods to request source attribution
- Parse and validate source citations
- "I don't know" detection and scoring
- Confidence interval estimation on aggregates
- Verification sweep (#12) produces the first provenance data

### Phase 6: Usability evaluation (depends on phase 4)

Level 4 evaluation. Can start alongside phase 5.

- Test with second country (scale)
- Test with updated reference data (temporal stability)
- Gap-filling from aggregate constraints
- Incoherence detection and escalation protocol
- Source prioritization when references conflict

### Phase 7: Journal submission (depends on phases 5 + 6)

Package phases 1–6 into a paper.

- Methods benchmark results (sweeps 1–5)
- Primary-source pipeline: first application and lessons learned
- Multi-level evaluation framework with data at all levels
- Architecture: from benchmark toward production pipeline
- Reproducibility: the code *is* the evidence

## Non-goals

- **Real-time serving.** This is a batch benchmark, not an API.
- **Model training or fine-tuning.** We evaluate off-the-shelf models.
- **Full factorial design.** Sweeps are targeted, not exhaustive.
- **GUI or dashboard.** Tables and charts are LaTeX artifacts.

## Reproducibility strategy

- Model IDs pinned in YAML registries (OpenRouter IDs, Ollama tags)
- Temperature 0.0 as default; stochasticity measured via 3-run repeats
- All prompts versioned in `experiments/prompts/`
- Raw JSON outputs committed (or retrievable via sweep config + model ID)
- Evaluation code deterministic: MILP solver, string matching thresholds
