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

## Method traits

Beyond the four evaluation levels, certain architectural properties shape whether a method can scale from one country × one component class to 60 extraction campaigns (Auto-PyPSA ASEAN). These are *traits of the fusion primitive*, not quality scores.

### Incrementality

**Definition.** The fusion primitive operates as `master + fragment → master'`, one source at a time — not `{all_fragments} → master` in a single shot.

**Why it matters.** Vietnam thermal alone has ~18 regulatory and utility tables; ASEAN × 6 components is O(hundreds). A non-incremental method re-runs the whole fusion for every new source — cost scales with N×S, not N. Incremental methods also give auditability: each step has an inspectable diff.

**Fusion order (v0).** Chronological with authority as tie-breaker. PDP7 → 7A → 8 → 8-revised → EVN annual reports → ERAV dispatch. Cancellations and amendments only make sense under chronological sequencing.

**Commutativity.** Not assumed. Order-independence belongs to a formal fusion framework (v3/v4 — defeasible reasoning with closure), not to LLM convenience fusion. The v0 pipeline is explicitly chronological.

**Empirical limits.** Characterize order-sensitivity experimentally: fuse the same corpus under *k* permutations; report inter-run F1 variance. The probe tells us where LLM fusion diverges from the chronological reference — the boundary beyond which a formal framework becomes necessary.

## Data model (v0 table fusion)

Scope: the table-fusion prototype that answers the v0 question — *does LLM convenience fusion work well enough, or do we need formal knowledge graphs?* Event fusion with defeasible reasoning and closure is the v3/v4 dream. Scalar and multi-scalar fragment fusion are deferred.

### Fragment taxonomy

Three fragment types, distinct extraction and fusion mechanics:

| Type | Where it lives | Fusion mechanic |
|---|---|---|
| **Serial** | Tables (PDP annexes, EVN reports) | Schema align + record linkage — defines the skeleton |
| **Multi-scalar** | Prose lists (*"province has projects A–E"*) | Entity existence check — confirms or adds rows |
| **Scalar** | Isolated prose facts (*"Vinh Tan 1 commissioned 2018"*) | Attribute update on matched entity |

v0 prototype handles **serial only**. Multi-scalar and scalar are deferred: they need scalar/multi-scalar extraction into the RAG corpus, which doesn't exist yet.

### Master + provenance sidecar

Two CSVs kept in lockstep:

- `master.csv` — one row per entity, current-state snapshot. Covers operating plants, authorizations, propositions, and scenario-conditional rows.
- `master_provenance.csv` — same schema, same rows, same primary key. Every cell holds exactly one source ID (the authoritative source for that cell's value).

**Invariants (enforced by validator, not convention):**

1. **Schema lockstep.** `schema(master) ≡ schema(master_provenance)`. Column add/drop/rename is a dual operation.
2. **Null parity.** `master[i,j]` null ⟺ `provenance[i,j]` null. No cell without attribution; no attribution without a cell.
3. **Single atomic writer.** Only the fusion primitive mutates the pair, always together. No ad-hoc edits, no one-file updates.
4. **Canonical source IDs.** Values drawn from the corpus source registry (below). LLM-emitted source names parsed against the registry; unknown IDs rejected.
5. **Fusion step log.** Every fusion step appends one row to `fusion_log.csv`: `{step_id, timestamp, source_id, rows_added, rows_updated, cells_changed, conflicts_resolved, confirmations}`. This log carries history and concordance — the sidecar itself stays scalar.

**Multi-source rule.** Scalar: one source ID per cell, chosen by authority. Sources that confirm an existing value are recorded in the fusion step log's `confirmations` field, not in the sidecar. This keeps sidecar shape simple and pushes concordance discovery into the audit trail, where history belongs.

### Source registry

The registry lives in corpus metadata, not in a standalone YAML. A document is registered as a source *iff* it passes the Source triage (HITL) step of the pipeline — registration and validation are the same action. The registry grows incrementally, one entry per accepted document.

Required fields per source:

- `source_id` — canonical short ID used in the sidecar (e.g. `PDP8R`, `EVN2024`)
- `publisher`, `publication_date`, `authority_rank`, `type` (regulatory / utility / dispatch / news / ...)
- `language`, `format`, `local_path`, original URL

The source registry is the sealed vocabulary of `master_provenance.csv`. This is where the "stateful" architecture begins: the set of trusted sources, grown by HITL, is state that persists across fusion runs.

### Three-tier verification with audit-verified HITL memory

Source-grounding of the master table is verified per cell via a three-tier chain (trait verification, ticket 0097):

```
changed cell (diff audit filter)
   → tier 1: string match against source table
       ├─ match    → verified
       └─ no match → tier 2: LLM adjudication
                       ├─ LLM + HITL ratifies → emit typed rule → memory
                       └─ rejected           → flag: hallucination / fusion error
```

A diff audit is applied before tier 1 as a pre-filter: unchanged cells inherit their previous verification status and do not re-enter the chain.

**Four rule categories** in the memory (each with a distinct fire point in the chain):

| Category | Encodes | Example | Fires at |
|---|---|---|---|
| **Alias** | entity identity | `"VT1" ≡ "Vinh Tan 1"` | after string-match fails |
| **Unit/format** | value shape | `"1,200 MW" → 1200` | before string match |
| **Source-local term** | prose vocabulary | `"Nhóm" in PDP8 = "Group"` | inside LLM adjudication |
| **Attribute synonym** | column → schema | `"Công suất lắp đặt" → capacity_mw` | at table load |

**Audit trail per rule** — five fields, committed to git, spot-checkable by a second witness: `{source_llm_suggestion, ratifying_human, timestamp, evidence_cell, witness}`. HITL ratification is mandatory; LLM adjudications never auto-accept.

**Rules are annotated, not mechanical** (ADR-6). Each YAML rule carries `pattern`, `replacement`, plus `rationale`, `edge_cases`, `ratified_by`, and full `evidence` (passage + document + line). A human statistician taking on the job should read the memory as a field notebook and understand *why* each rule exists — not just what substitution it performs. The verification engine reads `pattern`/`replacement`; humans read the rest. This shapes the audit experience and the trust story.

**Metrics** added to `measurements.jsonl`: `escalation_rate_per_step`, `rule_count_growth` (per taxonomy), `ratification_acceptance_rate`.

## Milestone DAG

Milestones are not sequential phases. They form a dependency graph.
Work on independent milestones proceeds in parallel. Publications
crystallize whenever milestones converge — they are side effects,
not gates.

```
  Presentation ────→ Hygiene ───────────────┐
  (done)               ↓                     ↓
  Measurements ───→ Pipeline ──→ Provenance ──→ Auto-PyPSA ASEAN
  (done)              ↓              ↓
                    Scale ───────────┘
```

### Econom'IA 2026 (in flight — Cergy, 2026-05-27)

Conference talk at Thema/Cergy. Homepage: https://economia.sciencesconf.org/
Title: *Beyond RAG: Graph-Based Architectures for Reliable Economic Statistics with Agentic Systems*.
Abstract: `docs/HaDuong-2026-EconomIA-Abstract.md`.

Argues that stateless generation, iterative prompting, and RAG fail on exhaustivity, internal coherence, temporal management, and traceability — the benchmark is the evidence. Proposes a paradigm shift to stateful, agentic, graph-based architectures that organize collection, human validation, temporal accumulation, and statistic derivation as a controlled knowledge production process.

Deliverable: slides (French, Beamer) in `slides/`. Consumes current state (census, ablation, hygiene results).

**Sync status (2026-04-17):**
- Slides synced to the v0 pipeline design (fusion reframe, fragment taxonomy, incrementality, master + sidecar, 3-tier verification, 4-category HITL memory, agents anchored on data-model concerns).
- Technical report carries warning boxes in Ch. 3 RAG intro, Ch. 6 Architecture proposée, and `inputs/verification_methods.tex`. Full rewrite tracked in tickets 0098 (Ch. 6 + Ch. 3 reframe) and 0099 (verification_methods.tex). Both blocked by 0097 (source-grounding Phase 1 results feed the rewrites).

### Presentation (done)

Present the methods benchmark pilot.

**Delivered:**
- Level 1 (resources): Pareto chart, cost table
- Level 2 (quality): census results (37 models), method comparison
  (6 conditions), best F1 98.8% (DeepSeek V3.2 + RAG)
- Levels 3-4: vision slide — the pipeline, not data yet
- RAG local sweep: 2B/4B/9B scaling curve

### Measurements (done)

`measurements.jsonl` is the single data source. All report tables are
views derived from it. `all_metrics.json` retired. Completed via #157.

### Hygiene (ready — depends on: Presentation, Measurements)

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

**Publication:** Pilot results + Hygiene = the first publishable article.

### Pipeline (ready — depends on: Measurements)

The 5-step extraction chain that produces PyPSA-Earth-ready datasets
from primary government documents. Includes worker infrastructure
(absorbed from former "Job board" milestone).

**The extraction chain (LLM-seeded, human-filtered, RAG-extracted):**

Justification is front-loaded: validate the *inputs* (which documents
to trust), not the *outputs* (which rows have citations). Post-hoc LLM
verification doesn't produce reproducible provenance (ticket 0059:
multi-agent panel achieves 0-10% inter-verifier agreement even after
bugfix).

1. **Source survey** — Ask the LLM for a full report: framing, asset
   list, bibliography. The LLM proposes candidate documents from
   parametric knowledge.
2. **Source triage (HITL)** — Filter by publisher authority. Government
   decisions, utility reports = primary; newsletters, compilations =
   discard. Human validates the source list before any extraction.
3. **Corpus construction** — Crawl primary sources, get PDFs, convert
   to Markdown (benchmarked converters), index, archive.
4. **RAG extraction** — Extract the asset list from the validated
   corpus. The LLM's parametric list from step 1 serves as a stopping
   criterion (coverage check), not as data.
5. **Per-asset enrichment** — RAG per asset + news search to fill gaps
   and update status. Each cell traces to a passage in a specific
   corpus document.
6. **Assembly** — Final table with provenance chain. Every cell
   traceable to a source document; gaps flagged honestly.

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
| Source survey | Frontier deep-research sweep (15 models) | Done |
| Source triage | HITL prompt design | Validated |
| Corpus construction | PDF to MD converters | Benchmarked (6 backends) |
| RAG extraction | RAG wholesale sweep | Done, F1=89.8% mean |
| Per-asset enrichment | Web-augmented queries | Done |
| Assembly | Reconciliation LP + evaluation | Done, 574 tests |

**Deliverable:** one PyPSA-Earth-ready Vietnam thermal dataset with
full provenance chain.

**Trait-verification tickets attached (ADR-5):**
- 0101 — incrementality × method (k-permutation order-sensitivity probe)
- 0104 — conflict-resolution × method (chrono + authority policy under conflicting sources)

### Provenance (depends on: Pipeline)

Level 3 evaluation. The table comes with receipts.

- **Sourced extraction** (ticket 0025): fix `extract.py` to preserve
  provenance columns (`source_1`, `source_2`, `note`) that already
  exist in 3 Claude Opus runs but are silently destroyed during CSV
  canonicalization.
- **Post-hoc verification: dead end** (ticket 0059, PR #246): multi-agent
  panel (3 models, 3 runs) achieves 0-10% inter-verifier agreement.
  Root cause: the 0-4 rubric asks models to recall citations from
  parametric knowledge, producing opinions not provenance. Conclusion:
  post-hoc LLM verification does not produce reproducible provenance
  scores. The production pipeline front-loads justification at source
  triage (step 2), not at output verification.
- **Source grounding rate**: measure what fraction of extracted rows
  can be traced to a specific passage in the RAG corpus by string
  matching alone (no LLM needed). Preliminary: 79% of 167 plants
  found in corpus; the 21% not found are parametric-knowledge
  additions — a direct hallucination signal.
- **Verification** (ticket 0030): "cost of trust" — precision-coverage
  trade-off. The meaningful comparison is now upfront citation (sourced
  extraction) vs corpus grounding (string matching), not LLM panels.
- "I don't know" detection and scoring
- Confidence interval estimation on aggregates

**Publication:** Methods paper — Hygiene (statistical rigor) +
Provenance (epistemic accountability) = journal article on the
benchmark methodology.

**Trait-verification tickets attached (ADR-5):**
- 0097 — source-grounding × table (3-tier, audit-verified; Phase 1 shipped as PR #261)
- 0103 — internal coherence × table (extends 0078's levels to master + sidecar)

### Scale (depends on: Pipeline)

Level 4 evaluation. Can proceed in parallel with Provenance.

- Test with second country (e.g., Indonesia coal) or second component
  class (e.g., Vietnam renewables from PDP8 annexes)
- Validate that the pipeline is parameterized by corpus, not hardcoded
  for Vietnam thermal
- Test with updated reference data (temporal stability)
- Gap-filling from aggregate constraints
- Incoherence detection and escalation protocol

**Trait-verification tickets attached (ADR-5):**
- 0102 — escalation-rate decay × system (HITL memory amortization across runs)

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
