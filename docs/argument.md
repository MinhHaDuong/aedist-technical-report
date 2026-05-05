# The argument: axes, lenses, four limits

*Working note — this is the central argument the AEDIST paper makes.
Renamed from `measurement-framework.md` once the framing matured from
scaffold into thesis.*

## The dimensions in play

Brain dump of what this paper has to track:

1. Model quality scale
2. Data quality scale
3. Method quality scale
4. Statistical limits
5. What can be illustrated in the census figure
6. Ablation dimensions

These six are not peers. **Three are axes of variation** (factors in the
experimental matrix); **four are lenses** (interpretations / measurements
applied to the matrix).

### Axes — what changes between cells of the design

- **Method** direct → multiturn → RAG → web → reasoning → general agent → custom team.
  Linearity is a convenience simplification of recent AI history.
- **Model.** Scale × architecture (dense / MoE) × provenance × cost × license (open /
  closed). Registry's `size_class` field (edge → frontier). The scale is a proxy for model capacity, but rapid technical progress and specialization must be considered.
- **Prompt.** Prompts are text, therefore not ordered, but the ablation study provides a modular structure.

### Lenses — how you read the matrix

- **Quality of the input data.** Training cutoff, RAG corpus completeness, web freshness.
- **Quality of extracted output.** Recall / precision / sourcing / calibration.
- **Statistical-limit attribution.** Which of the statistical limits do this method relax?
- **Epistemic-limit attribution.** Which of the epistemic (scientific knowledge) limits do this method relax?

(*Information condition* — parametric / +docs / +web / +tools — was
considered but is colinear with the method axis; treat it as a property
of the method, not a separate lens.)

## Three qualities the paper measures

The paper carves measurement-from-LLM into three quality types. The
four limits split 2/2 between *data* (properties of the inputs) and
*answer* (properties of the output given the inputs); method quality
is a third, perpendicular axis.

| Quality | Question | Limits | Closed by |
|---|---|---|---|
| **Data quality** | Are the input facts present, complete, and current? | Coverage, Freshness | RAG + web |
| **Answer quality** | Did the model produce the correct output given the inputs? | Articulation, Coherence | Prompts + reasoning |
| **Method quality** | Can we trust the process that produced the answer? | (separate axis — see §Method quality) | Agentic + multi-agent teams |

Data and answer quality are conceptually orthogonal but **bundled by
the F1 metric on AEDIST.** "Did the model have the facts?" (Coverage
/ Freshness) and "did the model state them correctly?" (Articulation
/ Coherence) collapse into a single F1 number on extracted
inventories. The two qualities saturate together at
deep-research-with-`prompt_complete` not because they happen to
coincide but because that condition closes all four limits
simultaneously.

**Method quality is a different axis.** Once the four data- and
answer-quality limits are closed, the question becomes whether we
can audit the process — verify that each emitted fact has a valid
citation, cross-check via independent re-extraction, surface
disagreement honestly. This is what agentic and multi-agent systems
contribute, and it is not the same axis as the four limits.

The Agent row in the limits table below is therefore not a fifth
limit but a pointer to the separate axis treated in §Method quality.

## The four limits: two on data, two on the answer

Recent AI-history stages map onto a sequence of measurement limits.
Two are properties of the *inputs* (Coverage, Freshness — data-quality
limits); two are properties of the *output given the inputs*
(Articulation, Coherence — answer-quality limits). Each is the next
bottleneck once the previous one is relaxed.

| AI stage | Limit | Quality | What it is |
|---|---|---|---|
| **Engineer prompt / clarify in multiturn** | **Articulation** | answer | Asking what you meant to ask. Speaking clearly across the human-model language barrier. Multiturn clarification is a second mechanism for the same limit. |
| **Provide documents** | **Coverage** | data | Facts the model never saw in training. |
| **Web** | **Freshness** | data | Facts moved on since training cutoff. |
| **Reason** | **Coherence** (weak, internal) | answer | Facts present, combined inconsistently. |
| **Agent** | (separate axis) | method | The Agent stage closes a perpendicular axis: *method quality* (auditability, verified provenance, cross-checking). The four data- and answer-quality limits end at deep research; Agent and Team systems open a different question, treated in §Method quality below. |

Can we have columns in the report to name the limits from the point of view of a
- Philosopher of Science
- Statistican
- Economist (guéguerre économètres vs. statisticiens)
- Journalist
- Energy System Modeler
- Business Intelligence Analyst
- Military Intelligence Analyst
- IT researcher

### Provenance of each term

- **Articulation.** Type-III error in classical statistics (Kimball 1957, *On the Errors of the Third Kind*; Mosteller 1948); echoes philosophy-of-science discussions of "articulating a question". Chosen over *Specification* (cold), *Alignment* (AI-safety baggage), *Intent* (loose), and *Clarity* (too soft) for active-process framing and lack of terminological collision.
- **Coverage.** Standard sampling/selection-bias literature (Cochran, *Sampling Techniques*; Kish, *Survey Sampling*). In ML: dataset bias, training-data lacunae.
- **Coherence.** Coherence factors along two axes: *weak* (no
  contradiction among extracted claims) vs. *strong* (closure under
  entailment), and *internal* (within the model's output) vs. *external*
  (against provided documents). The four cells:
  - **Weak / internal** — what the regimes-scatter actually measures, and
    what self-consistency decoding (Wang et al. 2022) targets.
  - **Weak / external** — RAG faithfulness; whether output contradicts
    the retrieved corpus.
  - **Strong / internal** — closure under entailment of the extracted
    table. Knowledge-graph territory; out of scope here, called out in
    the conclusion as future work.
  - **Strong / external** — symbolic verification against ground-truth
    data; out of scope.

  Stronger philosophical anchors exist (de Finetti's no-Dutch-book
  coherence for credences; BonJour's coherentism in epistemology) but
  target stricter notions than what is testable on extracted tables.
  Cite them as upper bounds, not as the present operational definition.
- **Freshness.** Data-engineering observability metric (dbt, Snowflake,
  Bigtable freshness checks); information retrieval freshness ranking
  signals; ML feature-store freshness SLOs. *Drift* is broader (covariate
  shift, concept drift, any distributional change); freshness is
  specifically temporal staleness — exactly what stage-4 closes.
  *Currency* was rejected for the money / wide-circulation collisions.

### Why the order is observed, not forced

Two empirical findings, dated and sourced in
[capability-timeline.md](capability-timeline.md):

1. **Stages 1 → 2 are sequential per lab**, but stages 3 (web) and 4
   (reasoning) are parallel branches. Anthropic shipped extended
   thinking (2025-02-24) *before* consumer web search (2025-03-20) — a
   per-product inversion of 3 and 4 that would be impossible if the
   chain were strict. Across the four labs, the stage-4 emergence
   window (Sept 2024 – June 2025) is compressed enough that at any
   given month some labs are in stage 3 and others in stage 4.
2. **Stage 5 (deep research) is forced once 3 and 4 are present.**
   Every lab ships deep research within 2–7 months of having both
   prerequisites — a window short enough that the composition is not a
   separate product decision but a near-mechanical join.

The DAG that fits the data:

```
1 (LLM) → 2 (RAG) → { 3 (web)  ∥  4 (reason) } → 5 (deep research)
                                              → 6 (general agent) → 7 (agent teams)
```

Stages 2 vs. 3 also swap in some labs — OpenAI shipped Browse with
Bing (May 2023) before consumer file upload (Oct 2023) — but the swap
is per-product, not industry-level. The conservative DAG above keeps 2
sequential.

Within the four limits, substitutability is still constrained:

- Coverage gaps are not closed by reasoning over what you have.
- Freshness gaps are not closed by anything internal to a static
  model.
- Coherence failures are not closed by web search alone — search
  results still need correct synthesis.
- Articulation is the leakiest case — RAG often disambiguates the
  question incidentally — so we mark it as a soft, not strict,
  boundary with Coverage.

### Disambiguations to pin down in the prose

- **"Coherence" needs the qualifier "weak, internal" on first use** to
  head off the broader senses (strong / external) summarised in the 2×2
  above. We measure the weak-internal cell only.
- **"Articulation" briefly defined on first use** to head off the
  ML-reader instinct to read it as *AI alignment*. One sentence is enough.

### Awkward cases worth flagging in prose

- **Stages overlap empirically.** A reasoning model with web access
  (3 + 4) often does retrieval (2). A strong-prompt + RAG setup (1 + 2)
  sometimes mimics structured reasoning (3) by forcing structured output.
  The four-tuple is a logical decomposition, not always cleanly
  observable in any single sweep.

## Method quality: verifiable vs. verified

Method quality has two layers, increasing in cost and audit value:

- **Verifiable** — the model emits a citation alongside each
  extracted fact. Cheap; automatable; binary (present / absent). A
  single agent with the right prompt can hit this floor.
- **Verified** — the citation is checked: the linked source resolves
  and contains the claim. Expensive; audit-driven. Requires either
  human review or a second system that re-reads the source. **This is
  the natural job of a multi-agent / team system** — extractor agent
  produces verifiable claims, auditor agent re-reads the cited
  sources and flags mismatches.

Method quality is not subsumed by the four limits. A run can be
right-on-output (correct answer) but low-method-quality (no
traceable provenance), or wrong-on-output (incorrect answer) but
high-method-quality (every claim has a verifiable citation that
turns out to be honestly wrong). The two axes vary independently;
the paper measures both.

Candidate AEDIST method-quality metrics:

- **Citation validity rate** — fraction of emitted citations whose
  URL resolves and whose linked content contains the claimed fact.
- **Re-extraction agreement** — second agent re-extracts
  independently; measure inter-agent agreement on the plant
  inventory.
- **Self-audit pass rate** — agent flags its own LOW-confidence
  claims and the flag matches ground truth.
- **Adversarial robustness** — claim survives "are you sure? show me
  a contradicting source" without unnecessary backpedalling.

The verifiable-vs-verified distinction subsumes the earlier
"provenance overlay" framing: provenance is not a separate dimension
bolted onto answer quality, it *is* method quality. Stages 6 (general
agent) and 7 (agent teams) of the capability ladder enter the paper
through this section, not through the answer-quality ladder.

## Narrative arc — three parts

The paper presents three quality stories in sequence:

### Part 1 — Methods

Set up the capability ladder (LLM → RAG → {web ∥ reason} → deep
research → agent → team) and the four limits — two on data
(Coverage, Freshness) and two on the answer (Articulation,
Coherence). State scope explicitly: the four limits govern data and
answer quality; method quality is a separate axis, treated in
Part 3.

### Part 2 — Data and answer quality up to the deep-research ceiling

The census figure plots cost vs. quality across all (model, method)
cells — the noisy floor set by the *model* axis.

The regimes-scatter (fixed prompt = `prompt_extract`) varies only
the method axis. Each step relaxes one limit, alternating between
data and answer quality:

- direct → multiturn — closes **Articulation** (answer)
- → RAG — closes **Coverage** (data)
- → RAG + reasoning — closes **Coherence** (answer); ticket 0144
- → deep research — closes **Freshness** (data), bundled with the
  `prompt_complete` switch (a second Articulation lift)

The four-step ladder visits each limit; the deep-research step is
the only one that bundles two deltas, which is why ticket 0144's
intermediate cell matters for clean attribution.

The ablation (fixed method = RAG) holds the method constant and
decomposes the prompt-structure axis into modules — which prompt
elements contribute what.

The deep-research cell extends the ladder with `prompt_complete`,
reasoning, and web. **Hypothesis:** F1 → 1 on cloud × capable models
× 3 reps. *Decent* if it holds for cloud; *interesting* if it also
holds for a sovereign / open-weight model. The deep-research cell
caps both data quality (inputs are now complete) and answer quality
(reasoning over `prompt_complete` saturates).

### Part 3 — Method quality and the trust frontier

Once data and answer quality saturate, the open question is process
trustworthiness: can each fact be audited? Single-agent runs add
citations (verifiable); multi-agent / team runs add re-extraction
and audit (verified). The method-quality figure is distinct from
the regimes-scatter — y-axis becomes citation validity,
re-extraction agreement, self-audit pass rate, or adversarial
robustness, not F1 on the inventory.

This is where capability stages 6 and 7 enter: not as another column
on the data-quality ladder, but as a different axis of progress.

## Empirical caveat (2026-04-30)

The narrative arc above assumes the deep-research cell ceilings the
regimes scatter — that *prompt_complete* + reasoning + web saturates
both data and answer quality. **The data on disk today does not yet
support that hypothesis.** Scan of 327 record files:

- **Best benchmark-wide F1 = 0.988** — DeepSeek V3.2 on decomposed
  RAG (Phase 4 cell), n=4 mean ≈ 0.898.
- **Best deep-research-cell F1 = 0.557** — GLM-5 Turbo on
  `prompt_complete` + reasoning. n=1 across 12 frontier models;
  two refusals (GPT-5.4, Grok 4.20) and one format failure (Ernie
  4.5 Thinking: returned aggregate capacity tables and per-plant
  prose in `**Field**: value` format, not a parseable inventory
  table); mean across n=9 successful attempts ≈ 0.46 (≈ 0.35 if
  non-attempts are counted as zero).
- The deep-research cell currently sits *below* the regimes-scatter
  ceiling, not above it. Stages 3 + 4 (Coherence + Freshness) appear
  to *lower* F1 over stages 1 + 2 in our measurement — the opposite
  of the narrative.

**Diagnosis: the evaluator artefact interpretation is
ruled out.** `_classify_orphan()` in `evaluate.py` correctly returns
`status=refusal` for GPT-5.4 and Grok 4.20 (no tables in their
responses) and `status=error` for Ernie 4.5 Thinking (aggregate
pipe tables present, but no per-plant inventory table with a plant
name column). Regression tests in
`tests/test_evaluator_robustness.py` pin this behaviour.

The remaining open interpretation is genuine over-exploration: deep
research really does over-cover and dilute precision against a fixed
reference. The arc would need rewriting to say stages 3 + 4 trade
F1 for completeness or sourcing rather than raising F1.

The deep-research-ceiling claim in Part 2 is **a hypothesis the
present data does not corroborate**, and the paper should mark it as
such rather than asserting the saturation.

A related local-side surprise: **qwen3.5:9b** at **F1 = 0.984** on
direct extraction (n=1). A 9B local model on the parametric regime,
without RAG / web / reasoning, sits within 0.004 of the
benchmark-wide best. If this reproduces under repeats on the
coal-only dev subset, the local-model question for the deep-research
arm collapses — you may not need a deep-research stack on this task
at all, just a well-suited small model.

## Why we want one canonical naming page

Today the codebase has at least three names for the same thing:
*method*, *regime*, *mode*. Sweep filenames mix axes —
`direct_extract`, `direct_multiturn`, `rag_extract` collapse the regime
axis into the filename, making it ambiguous whether a result varies by
regime, by prompt, or by both.

Before more sweeps land, the recommendation is: pick one canonical name
per axis, fix vocabulary in code (sweep keys, output dirs, plot scripts,
table headers) and prose, and map each existing sweep to the
(model × regime × prompt-structure) cell it occupies. The cost is roughly
half a day of mechanical rename; the return is consistent figure
captions and lower confusion in code review for months.
