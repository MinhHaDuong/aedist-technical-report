# Measurement framework: axes, lenses, and the four limits

*Working note — captures the intellectual framing for the AEDIST benchmark
discussion. This is the conceptual scaffold the paper hangs from.*

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

## The history of AI - statistical limits mapping

We can roughly map recent AI-history stage to a statistical-quality limit. Each is the next bottleneck once the previous one is relaxed.

| AI stage | Statistical limit | What it is |
|---|---|---|
| **Engineer prompt / clarify in multiturn** | **Articulation** | Asking what you meant to ask. Speaking clearly across the human-model language barrier. Multiturn clarification is a second mechanism for the same limit. |
| **Provide documents** | **Coverage** | Facts the model never saw in training. |
| **Web** | **Freshness** | Facts moved on since training cutoff. |
| **Reason** | **Coherence** (weak, internal) | Facts present, combined inconsistently. |
| **Agent** | **?** | Open question: the Agent stage may close a limit *outside* the four (e.g. *closure* — the answer-vs-action gap), in which case the four-limits frame ends at deep research and Agent is the next regime. Pending the capability-timeline review. |

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

## Narrative arc

1. **Setup.** Measurement-from-LLM is hard. Four statistical limits
   (Articulation / Coverage / Coherence / Freshness).
2. **Model floor.** The census figure plots cost vs. quality across all
   (model, regime) combinations — the noisy floor set by the *model* axis.
3. **Regime ladder.** The regimes scatter (fixed prompt = `prompt_extract`)
   varies *only* the regime — direct / multiturn / RAG. Each step relaxes
   one statistical limit.
4. **Prompt decomposition.** The ablation (fixed regime = RAG) holds the
   regime constant and decomposes the *prompt-structure* axis into modules.
   This tells us which prompt elements contribute what.
5. **Joint ceiling, with a missing link.** The frontier deep-research arm
   uses `prompt_complete` plus reasoning plus web — the meet of the two
   parallel branches that emerged after RAG (web for Freshness, reasoning
   for Coherence). The gap between the regimes-scatter ceiling and the
   deep-research result is therefore *three* deltas glued together: the
   web branch, the reasoning branch, and the prompt-structure switch from
   `prompt_extract` to `prompt_complete`. We cannot attribute the gap to
   any single limit without an intermediate cell (e.g., RAG + reasoning,
   no web) that isolates the Coherence contribution. Either we add that
   cell, or we present deep research as an upper-bound demonstration of
   the joint capability and refuse to decompose the gap.
6. **Provenance overlay — verifiable vs. verified.** Source-grounding has
   two layers. *Verifiable* means the model emitted a citation; cheap,
   automatable, present-or-absent. *Verified* means a human or tool
   confirmed the citation actually supports the claim; expensive,
   audit-driven. The verified layer is precisely a Coherence diagnostic
   — citations that exist but mis-attribute facts are weak-internal-
   coherence failures with an external pointer attached, which folds
   provenance back into the four-limits frame instead of leaving it as
   a separate overlay. We measure verifiable; we flag verified as
   future work.

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
