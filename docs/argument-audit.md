# Argument audit — multi-LLM critique

*Generated 2026-05-01T17:38Z by `scripts/audit_argument.py` (ticket 0148).*

**Orchestrator:** Claude Sonnet 4.6 (claude-sonnet-4-6) via Claude Code.

**Panel:** 7 models queried via OpenRouter.

| Model | Tokens | Wall time |
|---|---|---|
| `anthropic/claude-opus-4.6` | 779 | 21.9s |
| `deepseek/deepseek-r1-0528` | 889 | 33.8s |
| `deepseek/deepseek-v3.2` | 463 | 21.8s |
| `google/gemini-3-flash-preview` | 554 | 4.3s |
| `openai/gpt-5.4` | 727 | 13.0s |
| `mistralai/mistral-large-2512` | 399 | 8.2s |
| `qwen/qwen3-max-thinking` | 408 | 13.3s |

**Source document:** `docs/argument.md`

**Limitation:** Models cannot follow relative links (`capability-timeline.md`) or verify cited references. This audit targets the argument's internal logic, not citation accuracy.

## (a) Strongest internal inconsistency

### claude-opus-4.6

Strongest internal inconsistency

The narrative arc in Part 2 asserts that the deep-research cell "caps both data quality (inputs are now complete) and answer quality (reasoning over `prompt_complete` saturates)" and hypothesizes "F1 → 1 on cloud × capable models × 3 reps." Yet the "Empirical caveat (2026-04-30)" section reports the best deep-research-cell F1 is **0.557**, with a cell mean of **≈ 0.35**, sitting *below* the regimes-scatter ceiling rather than above it. The document simultaneously presents the saturation claim as the organizing thesis of Part 2 ("each step relaxes one limit… deep-research step bundles two deltas") and then concedes "the paper should mark it as such rather than asserting the saturation." These two positions cannot coexist: the entire four-limit ladder narrative depends on monotonic improvement culminating at deep research, but the only data available shows a *decrease* in F1 at that stage.

### deepseek-r1-0528

Strongest internal inconsistency  
**Contradiction between narrative arc and empirical data.** The narrative arc (Part 2) claims deep research (prompt_complete + reasoning + web) "saturates both data and answer quality" with F1 → 1. However, the empirical caveat states: "Best deep-research-cell F1 = 0.557", with three models at 0.000 and mean ≈0.35. This directly contradicts the saturation hypothesis.

### deepseek-v3.2

Strongest internal inconsistency  
The document states that the deep-research cell (with `prompt_complete`, reasoning, and web) “caps both data quality … and answer quality” and that “F1 → 1” is the hypothesis. However, in the **Empirical caveat** section, it reports that the best deep-research-cell F1 is 0.557, with three frontier models scoring 0.000, and the mean across the cell is ~0.35. This directly contradicts the claim that deep research saturates quality; the data shows it currently *lowers* F1 relative to simpler methods.

### gemini-3-flash-preview

Strongest internal inconsistency

The document defines **"Deep Research"** (Stage 5) as the pinnacle of the capability ladder that "closes all four limits simultaneously" and "saturates" both data and answer quality. However, the **Empirical caveat (2026-04-30)** reveals that the Deep Research cell currently "sits *below* the regimes-scatter ceiling" with a mean F1 of 0.35, compared to 0.898 for simpler RAG methods. The text asserts a "near-mechanical join" of capabilities while simultaneously admitting the data shows "the opposite of the narrative."

### gpt-5.4

Strongest internal inconsistency

The biggest contradiction is between the core thesis that the ladder is an *observed* improvement structure and the later admission that the key upper-stage condition performs worse than simpler methods.

- In **“Three qualities the paper measures”** and **“Part 2 — Data and answer quality up to the deep-research ceiling”**, you claim deep research “**closes all four limits simultaneously**,” “**caps both data quality and answer quality**,” and hypothesize “**F1 → 1**.”
- But in **“Empirical caveat (2026-04-30)”** you state the opposite: “**The data on disk today does not yet support that hypothesis**,” “**Best deep-research-cell F1 = 0.557**,” and “**Stages 3 + 4 … appear to lower F1 … the opposite of the narrative**.”

As written, the paper simultaneously treats the four-limit ladder as the central explanatory structure and concedes that the current evidence contradicts its predicted ordering.

### mistral-large-2512

Strongest internal inconsistency
The document claims that **data and answer quality are "conceptually orthogonal"** (under "Three qualities the paper measures") but later states they are **"bundled by the F1 metric on AEDIST"** and saturate together in the deep-research condition. These cannot both be true: if they are orthogonal, they should not collapse into a single metric or saturate in lockstep.

### qwen3-max-thinking

Strongest internal inconsistency  
The document asserts that the “deep-research cell caps both data quality (inputs are now complete) and answer quality (reasoning over `prompt_complete` saturates)” (Part 2), yet the “Empirical caveat (2026-04-30)” explicitly states: “The deep-research cell currently sits *below* the regimes-scatter ceiling, not above it… the opposite of the narrative.” These cannot both be true: saturation implies a performance ceiling, but the data show deep research underperforms prior stages.

## (b) Weakest empirical claim

### claude-opus-4.6

Weakest empirical claim

The claim that **qwen3.5:9b achieves F1 = 0.984 on direct extraction** and that this might collapse the need for a deep-research stack rests on **n=1, on what appears to be a single dev subset (coal-only)**. No confidence interval, no repeated runs, no cross-subset validation is reported. To defend this claim the authors would need: (i) multiple repetitions (≥5) showing stable performance, (ii) evaluation on the full benchmark rather than a single sector subset, and (iii) comparison against the same evaluator pipeline used for other models to rule out scoring asymmetries. As stated, a single draw from a stochastic system is indistinguishable from a lucky parse.

### deepseek-r1-0528

Weakest empirical claim  
**"Deep research saturates data/answer quality (F1 → 1)".** Current data shows mean F1 ≈0.35 for this cell, with models scoring 0.000. Evidence needed:  
- Fix evaluator artifacts (e.g., validate if `.record.json` extraction fails due to output formatting).  
- Demonstrate F1 ≥0.95 across multiple models/reps after fixes, or provide domain justification for lower F1 as acceptable.

### deepseek-v3.2

Weakest empirical claim  
“The deep-research step is the only one that bundles two deltas, which is why ticket 0144’s intermediate cell matters for clean attribution.” This claim about the necessity of an intermediate cell for attribution is presented without evidence. To defend it, the authors would need to show that without that intermediate step, the contributions of `prompt_complete` vs. reasoning+web cannot be disentangled—requiring an ablation study that isolates each factor.

### gemini-3-flash-preview

Weakest empirical claim

The claim that **"Stage 5 (deep research) is forced once 3 and 4 are present"** lacks sufficient evidence. The document cites a "2–7 month" window across four labs as proof of a "near-mechanical join," but this is a correlation of product release cycles, not a proof of technical necessity or performance synergy. To defend this, the author would need to prove that the *integration* of web and reasoning provides a non-linear performance gain that neither can achieve alone, which the current F1 scores (0.35) explicitly fail to do.

### gpt-5.4

Weakest empirical claim

The weakest empirical claim is in **“Why the order is observed, not forced”**:

> “**Stage 5 (deep research) is forced once 3 and 4 are present.** Every lab ships deep research within 2–7 months … **not a separate product decision but a near-mechanical join**.”

This is a very strong causal claim from a tiny, endogenous sample (“four labs”), with ambiguous stage definitions and obvious confounds (branding, release strategy, safety, product packaging). “Within 2–7 months” is not evidence of necessity.

To defend it, you would need:
- a transparent coding of stages across labs/products,
- a larger comparative sample,
- evidence that no counterexamples exist,
- and some model distinguishing “mechanical composition” from ordinary product sequencing.

### mistral-large-2512

Weakest empirical claim
**"Hypothesis: F1 → 1 on cloud × capable models × 3 reps"** (in "Part 2 — Data and answer quality"). The empirical caveat section reveals the best deep-research-cell F1 is only **0.557**, with a mean of **0.35**, directly contradicting the hypothesis. No evidence is provided to suggest this is a transient or fixable issue (e.g., prompt engineering, evaluator tweaks).

### qwen3-max-thinking

Weakest empirical claim  
The claim that “F1 → 1 on cloud × capable models × 3 reps” in the deep-research cell lacks empirical support. Current data show a mean F1 ≈ 0.35 for that cell, with three frontier models scoring 0.000. To defend it, the authors would need replicated runs across multiple models showing consistent high F1 *after* ruling out evaluator artefacts (e.g., by verifying that valid tables were extracted but misparsed).

## (c) Most likely methodological objection

### claude-opus-4.6

Most likely methodological objection from a peer reviewer

A reviewer would immediately challenge the **confounding between the evaluator/parser and the treatment**. The document itself flags this under "Evaluator artefact": `prompt_complete` returns structured documents with narrative paragraphs and multiple tables, and three frontier models score exactly 0.000 — which almost certainly reflects extraction-pipeline failure rather than model failure. This means the dependent variable (F1) is not measuring model capability but rather the interaction between output format and a downstream parser. Until the evaluation pipeline is shown to be invariant to output formatting, **every comparison across the method axis is potentially invalid**, and the entire regimes-scatter is uninterpretable. Any energy-economics or NLP reviewer would flag this as a fatal threat to internal validity before engaging with the theoretical framework.

### deepseek-r1-0528

Most likely methodological objection from a peer reviewer  
**Energy economist objection:** The framework lacks domain-specific validation. No evidence shows energy infrastructure extraction (e.g., plant inventories) uniquely stresses the four limits versus other domains. Reviewer would demand:  
> *"Why is this task a critical test case? Demonstrate that Coverage/Freshness gaps in energy data are distinct from, say, healthcare or finance."*

### deepseek-v3.2

Most likely methodological objection from a peer reviewer  
A statistics or energy-economics reviewer would object to the conflation of **data quality** and **answer quality** into a single F1 metric on extracted inventories. The document admits they are “conceptually orthogonal but bundled by the F1 metric on AEDIST.” This bundling makes it impossible to distinguish whether a low score is due to missing input facts (coverage/freshness) or faulty reasoning (articulation/coherence), undermining the paper’s core claim of decomposing limits.

### gemini-3-flash-preview

Most likely methodological objection from a peer reviewer

A reviewer in **NLP or Statistics** will object to the **"Linearity" of the Method axis** and the collapsing of variables. The document admits that "Information condition... is colinear with the method axis" and that "Stages overlap empirically." By treating "Method" as a single linear progression (Direct → RAG → Agent), the author conflates *architectural* changes (retrieval) with *computational* changes (reasoning tokens) and *interface* changes (multiturn). A reviewer will demand a proper factorial design that separates the retrieval mechanism from the model's cognitive strategy to avoid confounded results.

### gpt-5.4

Most likely methodological objection from a peer reviewer

A reviewer will object first to identification: the paper claims stage-specific effects while changing multiple things at once and using a metric that “**bundles**” the constructs.

Three places make this acute:
- **“Data and answer quality are conceptually orthogonal but bundled by the F1 metric on AEDIST.”**
- **“The deep-research step is the only one that bundles two deltas.”**
- **“The deep-research cell extends the ladder with `prompt_complete`, reasoning, and web.”**

So the design cannot cleanly attribute changes in F1 to **Coverage**, **Freshness**, **Articulation**, or **Coherence**. An energy economist or statistician will say the constructs are not identified; an NLP reviewer will say the benchmark/evaluator may be mis-scoring richer outputs; all three will note the n’s are tiny and uneven (“**n=1**,” “**n=4 mean**”).

### mistral-large-2512

Most likely methodological objection from a peer reviewer
A reviewer in **energy economics** would object to the **lack of ground-truth validation** for extracted infrastructure statistics. The document assumes F1 on AEDIST is a sufficient proxy for "correctness," but no independent verification (e.g., cross-checking against regulatory filings or satellite imagery) is mentioned. The claim that "deep research saturates" is meaningless without external validation.

### qwen3-max-thinking

Most likely methodological objection from a peer reviewer  
A reviewer would object that bundling data and answer quality into a single F1 metric conflates distinct error sources (coverage/freshness vs. articulation/coherence), violating the paper’s own claim of orthogonality. This undermines attribution of performance gains to specific “limits” and invalidates the staged narrative unless ablation shows independent contributions.

## (d) One claim to drop if forced

### claude-opus-4.6

One claim you would drop if forced

Drop the **method-quality axis (Part 3) and its associated metrics** (citation validity rate, re-extraction agreement, self-audit pass rate, adversarial robustness). The document admits no empirical results for any of these metrics; they are entirely prospective. Meanwhile, the paper already struggles to empirically support its core data/answer-quality claims. Including an unmeasured "third axis" dilutes the argument, forces the awkward disclaimer that stages 6–7 "enter the paper through this section" without data, and invites reviewers to dismiss the framework as speculative. The four-limit ladder is already a complete contribution if it can be validated; the trust-frontier material belongs in a future-work paragraph, not a structural pillar of the argument.

### deepseek-r1-0528

One claim you would drop if forced  
**Drop the capability-timeline DAG** (`1 → 2 → {3 ∥ 4} → 5 → 6 → 7`). It is non-essential to the core argument (four limits + three qualities), and the document admits inversions (e.g., Anthropic shipped reasoning before web). Retaining it invites tangential debates about AI progress timelines, distracting from the measurement framework.

### deepseek-v3.2

One claim you would drop if forced  
Drop the claim that “The four-step ladder visits each limit” in the regimes-scatter, specifically that moving from RAG to RAG+reasoning closes **Coherence**. The empirical caveat shows that adding reasoning currently *lowers* F1, and the document’s own 2×2 coherence framework notes that only “weak, internal” coherence is measured—which may not align with the operational definition used in the task. This step is not empirically supported and muddies the narrative.

### gemini-3-flash-preview

One claim you would drop if forced

Drop the claim that **"Articulation" is the equivalent of a "Type-III error in classical statistics."** While Kimball (1957) is a prestigious citation, the document later admits Articulation is the "leakiest case" and is "often disambiguated... incidentally" by RAG. Linking a model's failure to follow a prompt to the profound statistical error of "giving the right answer to the wrong question" is an over-intellectualization that adds terminological bloat without improving the measurement of the F1 score. Removing it simplifies the "Four Limits" into more defensible engineering constraints.

### gpt-5.4

One claim you would drop if forced

Drop the claim that:

> “**Stage 5 (deep research) is forced once 3 and 4 are present.**”

Why this one:
- It is not needed for the main paper about extraction quality.
- It is the most speculative causal statement.
- It invites avoidable reviewer pushback on platform history rather than your benchmark.
- It is especially awkward given **“Empirical caveat”**, where the deep-research cell currently underperforms. Even if the product-history claim were true, it does not help the paper’s substantive argument.

### mistral-large-2512

One claim you would drop if forced
**"The four limits split 2/2 between *data* and *answer*."** This framing is overly neat and obscures the messy reality that **Articulation** (an "answer" limit) is often addressed incidentally by RAG (a "data" method). The soft boundary between Articulation and Coverage (acknowledged in "Disambiguations") undermines the binary split. Dropping this claim would simplify the argument without losing core insights.

### qwen3-max-thinking

One claim you would drop if forced  
Drop the claim that “the deep-research step… bundles two deltas” (closing both Freshness and a second Articulation lift). The empirical caveat shows this step *lowers* F1, and the bundled improvement is speculative. Removing it tightens the argument to only what the data support: that stages 1–4 may relax limits incrementally, but deep research’s role remains unproven.

## Consensus clusters

### Cluster 1 — Deep-research saturation contradicts empirical data (7/7 models)

The dominant finding. Every model flags the tension between the narrative
arc (deep research caps data + answer quality, F1 → 1) and the empirical
caveat (best deep-research F1 = 0.557, mean ≈ 0.35, three models at 0.000).
Six models name it as (a) the strongest inconsistency; four also name it
as (b) the weakest claim; three would drop the deep-research ladder step.

**Sections:** (a) claude-opus, deepseek-r1, deepseek-v3.2, gemini, gpt-5.4,
qwen3; (b) deepseek-r1, mistral, qwen3; (d) deepseek-v3.2, qwen3.

### Cluster 2 — F1 bundles orthogonal qualities, confounding attribution (5/7)

The paper claims data quality and answer quality are "conceptually orthogonal"
but measures them with a single F1. Five models flag this as a methodological
threat: the bundled metric makes it impossible to attribute F1 changes to
specific limits (Coverage vs. Articulation vs. Coherence vs. Freshness),
undermining the ladder's explanatory power.

**Sections:** (c) deepseek-v3.2, gpt-5.4, qwen3, gemini (partial); (a) mistral.

### Cluster 3 — "Stage 5 forced" is speculative causal overclaim (3/7)

The claim that deep research is a "near-mechanical join" once web + reasoning
exist rests on 4 labs over a 2–7 month window — a tiny, endogenous sample
with confounds (branding, release strategy, safety gating). Two models flag
it as (b) weakest claim; two would drop it.

**Sections:** (b) gemini, gpt-5.4; (d) gpt-5.4, deepseek-r1.

### Cluster 4 — Evaluator/parser confound threatens internal validity (2/7)

Three frontier models scoring exactly 0.000 on deep-research almost certainly
reflects parser failure on structured-document output, not model failure.
Until the evaluator is shown to be format-invariant, all cross-method
comparisons are potentially invalid.

**Sections:** (c) claude-opus (strongest statement — "fatal threat to internal
validity"); gpt-5.4 (partial).

### Cluster 5 — Part 3 (method quality) is unmeasured and speculative (1/7)

Claude Opus alone flags that the entire third axis — citation validity,
re-extraction agreement, self-audit pass rate, adversarial robustness — has
zero empirical results. Including it as a structural pillar invites dismissal.
Recommendation: demote to future work.

**Sections:** (d) claude-opus.

### Cluster 6 — Minor / unique objections

- **qwen3.5:9b F1=0.984 from n=1** — unreliable (claude-opus, (b)).
- **Articulation ≈ Type-III error** — over-intellectualized (gemini, (d)).
- **2/2 data-answer split** — too neat given soft Articulation/Coverage
  boundary (mistral, (d)).
- **Domain specificity** — why energy, not healthcare or finance?
  (deepseek-r1, (c)).

## Disposition

*For the author to fill. Recommended template:*

| # | Cluster | Objection summary | Action | Justification |
|---|---|---|---|---|
| 1 | Deep-research saturation | Narrative claims F1→1; data shows 0.35 | | The document already flags this as a hypothesis; the question is whether to restructure the narrative arc or keep it conditional |
| 2 | F1 bundles qualities | Single metric confounds 4 limits | | Could add per-limit proxy metrics or explicitly scope the ladder as conceptual, not identified |
| 3 | Stage-5-forced | Causal overclaim from 4 labs | | Could soften to "observed pattern" or drop the causal language entirely |
| 4 | Parser confound | 0.000 rows = evaluator failure | | Already flagged in STATE.md priority 2; resolution precedes any narrative revision |
| 5 | Part 3 unmeasured | Method-quality axis has no data | | Demote to future work or frame as "proposed" not "measured" |
| 6 | Minor | Various single-model objections | | Address individually if tightening prose |
