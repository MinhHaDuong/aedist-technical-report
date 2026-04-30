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
7. Information conditions

These seven are not peers. **Three are axes of variation** (factors in the
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
- **Information condition.** Parametric / +docs / +web / +tools — but this is *colinear* with the regime axis. Flag the redundancy in prose; do not double-count.

## The history of AI - statistical limits mapping

We can roughly map recent AI-history stage to a statistical-quality limit. Each is the next bottleneck once the previous one is relaxed.

| AI stage | Statistical limit | What it is |
|---|---|---|
| **Engineer prompt** | **Articulation** | Asking what you meant to ask. Speaking clearly across the human-model language barrier.|
| **Provide documents** | **Coverage** | Facts the model never saw in training. |
| **Web** | **Freshness** | Facts moved on since training cutoff. |
| **Reason** | **Coherence** (internal) | Facts present, combined inconsistently. |
| **Agent** | **?** | ? |

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
- **Coherence.** Three independent textbook anchors that all reinforce
  the right intuition:
  - Bayesian: de Finetti's coherence (a credence set is coherent iff the
    betting prices it implies admit no Dutch book).
  - Philosophy of knowledge: BonJour's coherentism — beliefs justified by
    mutual support.
  - ML/NLP: self-consistency as a decoding strategy (Wang et al. 2022)
    targets exactly this failure mode.
- **Freshness.** Data-engineering observability metric (dbt, Snowflake,
  Bigtable freshness checks); information retrieval freshness ranking
  signals; ML feature-store freshness SLOs. *Drift* is broader (covariate
  shift, concept drift, any distributional change); freshness is
  specifically temporal staleness — exactly what stage-4 closes.
  *Currency* was rejected for the money / wide-circulation collisions.

### Why the order is a real capability evolution
%J AI INVERSE 2 et 3 dans l'historique + AJOUTE AGENTS + TEAMS

You cannot substitute one stage's fix for another's:
- Articulation error is not closed by handing over more documents.
- Coverage gaps are not closed by reasoning harder over what you have.
- Coherence failures are not closed by web search alone (search results still need correct synthesis).
- Freshness gaps are not closed by anything internal to a static model.

Each stage is the minimal fix for the next limit.

### Disambiguations to pin down in the prose

- **"Internal coherence" on first use.** Coherence can mean (a) the
  model's output is self-consistent or (b) the output is consistent with
  provided documents. We mean (a). External coherence belongs to
  Coverage / grounding, and conflating them blurs the decomposition.
- **"Articulation" briefly defined on first use** to head off the
  ML-reader instinct to read it as *AI alignment*. One sentence is enough.

### Awkward cases worth flagging in prose

- **Multiturn does not cleanly add to any of the four.** It is a weak
  Coherence proxy (forces revision without exposing the reasoning trace),
  not a Reason-stage capability. Name it as the awkward case rather than
  slotting it into one of the four.
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
5. **Joint ceiling.** The frontier deep-research arm uses `prompt_complete`
   plus reasoning plus agent. The gap between the regimes-scatter ceiling
   and the deep-research result is the joint contribution of stages 3–4
   (Coherence + Freshness) over stages 1–2 (Articulation + Coverage).
6. **Provenance overlay.** Source-grounding is orthogonal — not "did the
   model find the plant" but "can we trace each fact". Layered over any
   cell of the matrix.

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
