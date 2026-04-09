# MASTERPLAN — AEDIST Methods Benchmark

> This document is the long-term vision. STATE.md tracks the current
> milestone's operational checkboxes. When they overlap, STATE.md governs
> what to do this week; MASTERPLAN governs why.

## North star

**Auto-PyPSA ASEAN** — a complete, auditable, reproducible database of
power system components across 10 ASEAN countries, built by AI extraction
from primary government documents and ready for direct use in PyPSA-Earth
models. 10 countries x 6 component classes = 60 extraction campaigns.
At ~$0.06 per campaign, a regional power system database for less than
one frontier model call.

Research-quality data isn't correct data. It's data whose errors are
**locatable**.

## Why this matters

Statistical offices need infrastructure inventories and cannot always
produce them: Vietnam's thermal power plants, Sub-Saharan grid assets,
industrial emissions sources. The data exists in fragments across
languages, formats, and jurisdictions.

The question is not "can GPT-5 list power plants?" but "what method
reliably produces a publishable statistical table, at what cost, with
what justification?"

A method is the whole pipeline: prompt design, information regime,
extraction logic, reconciliation strategy, verification pass. A model
is one parameter.

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

### Level 1 — Resources (measured)
Wall time, API cost, token counts.
CO2 estimate aspirational (requires CodeCarbon or provider-reported data).
Every run has a price tag.

### Level 2 — Document quality (measured)
Benchmark against gold standard: coverage, precision, F1, attribute
accuracy, capacity error, hallucination rate.
The table either matches reality or it doesn't.

### Level 3 — Output provenance (milestone: Provenance)
The table comes with sources and notes. Claims are attributed.
The method says "I don't know" when uncertain.
Confidence intervals on counts and capacities.
Statistical quality, not just accuracy.

### Level 4 — System usability (milestone: Scale)
Can the method scale to other countries? Update when plants change status?
Fill gaps from totals? Resolve incoherences or escalate them?
Prioritize sources when they conflict?

## Milestone DAG

Milestones are not sequential phases. They form a dependency graph.
Work on independent milestones proceeds in parallel. Publications
crystallize whenever milestones converge — they are side effects,
not gates.

```
  Conference ─────→ Hygiene ───────────────┐
  (60%)               ↓                     ↓
  Measurements ───→ Pipeline ──→ Provenance ──→ Auto-PyPSA ASEAN
  (done)              ↓              ↓
                    Scale ───────────┘
```

### Conference (active, 60%)

Present the methods benchmark pilot at Econom'IA 2026 (April 11).

**What we show:**
- Level 1 (resources): Pareto chart, cost table
- Level 2 (quality): census results (37 models), method comparison
  (6 conditions), best F1 98.8% (DeepSeek V3.2 + RAG)
- Levels 3-4: vision slide — the pipeline, not data yet

**What remains:**
- Visual PDF review of slides
- RAG local sweep: 2B/4B/9B scaling curve

**Data:** 238 measurement rows, 574 tests passing, $0.82 total cost.

### Measurements (done)

`measurements.jsonl` is the single data source. All report tables are
views derived from it. `all_metrics.json` retired. Completed via #157.

### Hygiene (ready — depends on: Conference, Measurements)

Statistical rigor on existing data. Zero new API calls needed — mine
the 238 existing measurements for honest uncertainty quantification.

- **Variance decomposition** (ticket 0029): two-way ANOVA on F1 by
  model x method. Report eta-squared. Are reported differences signal
  or noise?
- **Method-vs-model proof** (ticket 0031): prove the "method dominates
  model" claim with statistics, not assertion. Cost-F1 scatter by regime.
  Investigate Gemini Flash Lite RAG degradation anomaly.
- **Matching sensitivity** (ticket 0035): store similarity scores in
  ReconciliationEntry. Post-hoc threshold sweep without MILP re-runs.
- **Prompt ablation** (ticket 0038): isolate which prompt components
  help vs hurt structured extraction. Existing data shows elaborate
  prompts *degrade* F1 (Opus: 0.64 single-shot vs 0.54 frontier).

**Publication:** Conference proceedings paper — pilot results + Hygiene
= the first publishable article.

### Pipeline (ready — depends on: Measurements)

The 5-step extraction chain that produces PyPSA-Earth-ready datasets
from primary government documents. Includes worker infrastructure
(absorbed from former "Job board" milestone).

**The extraction chain:**

1. **Regulatory corpus** — Retrieve official planning documents and
   annexes. Convert PDF to MD using benchmarked converters.
2. **Operational stock** — Reconstruct current fleet from utility annual
   reports and regulator data.
3. **Decisional chronology** — Per facility, trace administrative
   history from primary sources. Rule: no primary source = flag the gap.
4. **Analytical synthesis** — Periodization, realization rates, technology
   transitions.
5. **Assembly** — Citable report with provenance chain. Each datum traces
   to an identified document; gaps are flagged honestly.

**First application: Vietnam thermal plants.**
Regulatory corpus = PDP7/7A/8/8 revised (Decisions 428, 500, 768, 1509).
Utility = EVN annual reports, ERAV dispatch data. ~163 facilities.

**Worker infrastructure** (tickets 0023, 0044, 0045):
- Fix mode dispatch bug (workers currently ignore `job.mode`)
- Shared `iter_model_replies()` whitelist for file discovery
- Handle empty CSVs as data (F1=0), not crashes
- File-based job execution with lease semantics

**Infrastructure from benchmark:**

| Pipeline step | Benchmark component | Status |
|---|---|---|
| Regulatory corpus | PDF to MD converters + RAG wholesale | Converters benchmarked |
| Operational stock | Web-augmented queries | Done |
| Chronologies | Multi-turn conversations | Done |
| Assembly | Reconciliation LP + evaluation | Done, 574 tests |

**Deliverable:** one PyPSA-Earth-ready Vietnam thermal dataset with
full provenance chain.

### Provenance (depends on: Pipeline)

Level 3 evaluation. The table comes with receipts.

- **Sourced extraction** (ticket 0025): fix `extract.py` to preserve
  provenance columns (`source_1`, `source_2`, `note`) that already
  exist in 3 Claude Opus runs but are silently destroyed during CSV
  canonicalization.
- **Verification** (ticket 0030): "cost of trust" — precision-coverage
  trade-off across verification modes. Compare upfront citation
  (sourced extraction) vs post-hoc verification (LLM + web checks).
- "I don't know" detection and scoring
- Confidence interval estimation on aggregates

**Publication:** Methods paper — Hygiene (statistical rigor) +
Provenance (epistemic accountability) = journal article on the
benchmark methodology.

### Scale (depends on: Pipeline)

Level 4 evaluation. Can proceed in parallel with Provenance.

- Test with second country (e.g., Indonesia coal) or second component
  class (e.g., Vietnam renewables from PDP8 annexes)
- Validate that the pipeline is parameterized by corpus, not hardcoded
  for Vietnam thermal
- Test with updated reference data (temporal stability)
- Gap-filling from aggregate constraints
- Incoherence detection and escalation protocol

### Auto-PyPSA ASEAN (north star — depends on: Provenance, Scale)

10 ASEAN countries x 6 component classes (thermal, renewables, hydro,
storage, transmission, interconnections). Same method, different corpus.
Each country publishes power development plans in its own language and
regulatory framework.

The pipeline is parameterized by country and component class.
The benchmark's evaluation metrics become the quality monitoring layer.
The measurements table becomes the audit log.

**Component classes:**
- Thermal generators (validated by benchmark)
- Renewables (solar, wind — present in PDP8 annexes)
- Hydroelectricity
- Storage (batteries, pumped hydro — emerging in PDP8 revised)
- Transmission network (lines, substations, from EVN expansion plans)
- Interconnections (ASEAN Power Grid links)

**Publication:** Data paper + full journal article describing the
complete framework from benchmark to production database.

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
