# Hypotheses — AEDIST benchmark

*Extracted from `docs/argument.md` on 2026-05-02. Each hypothesis has an
operational definition, decision rule, and sweep reference. Decision rules
are pre-specified before any new data is read.*

*Existing data (327 records as of 2026-04-30) is referenced for context
but does not determine thresholds — thresholds are grounded in operational
sufficiency for downstream use (PyPSA-ASEAN pipeline) or in pre-committed
effect sizes.*

## Status key

- **Confirmatory** — testable by new sweeps not yet run; preregisterable
  (route to ticket 0150).
- **Exploratory** — informed by existing data patterns or requiring new
  infrastructure; declared as exploratory per best practice.
- **Observational** — structural framing or design assertion; not
  falsifiable within this paper's experimental design.

---

### H1 — Deep-research saturation (cloud)

- **Argument anchor:** §Narrative arc, Part 2 (lines 257–264); §Empirical
  caveat (lines 279–318)
- **Claim:** Deep research (reasoning + web + `prompt_complete`) on cloud
  frontier models saturates both data and answer quality, reaching F1
  comparable to or exceeding the current decomposed-RAG ceiling.
- **Precondition:** The evaluator-artifact diagnosis (STATE.md priority 2)
  must be resolved first. Three frontier models (GPT-5.4, Grok 4.20,
  Ernie 4.5 Thinking) returned F1 = None on `prompt_complete` output —
  almost certainly a parser failure on structured-document format. H1 is
  untestable until the parser handles `prompt_complete` output correctly.
- **Operational definition:** F1 macro on the coal-only dev subset
  (Vietnam thermal v1 reference), evaluated by the standard
  `evaluate_extraction()` pipeline after parser fix.
- **Sweep:** `sweep_direct_complete` — modify: `repeat` 1→3,
  `model_set` → `modelset_frontier_10labs` (12 models). Re-run after
  parser fix.
- **Decision rule:**
  - *Supported:* Mean F1 ≥ 0.95 across ≥3 frontier models at n=3,
    with bootstrap 95% CI lower bound ≥ 0.90.
  - *Falsified:* No model achieves mean F1 ≥ 0.90 at n=3 after parser
    fix confirmed.
  - *Inconclusive:* 1–2 models reach ≥0.95 but the majority do not, or
    CI straddles 0.90.
- **Current evidence:** Best n=1 F1 = 0.557 (GLM-5 Turbo); mean across
  cell ≈ 0.35; 3/12 models at None (parser failure). **Currently
  contradicted** — 6/6 audit models flagged this (audit finding #1).
- **Status:** Confirmatory, conditional on parser fix.

---

### H2 — Deep-research saturation (local / sovereign)

- **Argument anchor:** §Narrative arc, Part 2 (lines 262–264: "decent if
  cloud; interesting if sovereign / open-weight")
- **Claim:** At least one open-weight model runnable locally (e.g.,
  Magistral, Qwen 3.5 122B) achieves deep-research saturation on the
  same task.
- **Operational definition:** Same as H1 — F1 macro on coal-only dev
  subset, `prompt_complete` prompt, local inference via Ollama.
- **Sweep:** New sweep needed — `sweep_direct_complete_local` with
  `model_set` → local models capable of reasoning + long context
  (≥32k tokens). Candidate: qwen3.5:122b, magistral (when available).
  `repeat` = 3.
- **Decision rule:**
  - *Supported:* At least one local model achieves mean F1 ≥ 0.95 at
    n=3, bootstrap 95% CI lower bound ≥ 0.90.
  - *Falsified:* No local model exceeds mean F1 = 0.80 at n=3.
  - *Inconclusive:* Best local model between 0.80 and 0.95.
- **Current evidence:** No local `prompt_complete` runs exist. Best
  local result overall: qwen3.5:9b at F1 = 0.984 on direct extraction
  (n=1, `prompt_extract` not `prompt_complete`).
- **Status:** Confirmatory.

---

### H3 — Method ladder closes named limits measurably

- **Argument anchor:** §The four limits (lines 74–87); §Narrative arc,
  Part 2 (lines 243–253)
- **Claim:** Each step on the method ladder produces a measurable F1
  improvement, and the improvement is attributable to the named limit
  via the mechanism each step adds. The ladder is a partial order (DAG),
  not a strict linear chain — per audit finding #6 and the admitted
  stage-3/4 parallelism.
- **Operational definition:** F1 macro on coal-only dev subset, same
  model × same prompt (`prompt_extract`), varying only the method.
  Five models, 3 reps each. Ladder rungs:
  1. direct → multiturn (mechanism: clarification → Articulation)
  2. multiturn → RAG (mechanism: document provision → Coverage)
  3. RAG → RAG + reasoning (mechanism: chain-of-thought → Coherence;
     ticket 0144's intermediate cell)
  4. RAG + reasoning → deep research (mechanism: web access → Freshness,
     bundled with `prompt_complete` switch)
- **Sweep:** `sweep_regimes_*` family (direct, multiturn, RAG) + new
  sweep for RAG + reasoning (ticket 0144) + `sweep_direct_complete`
  (deep research). All at `repeat` = 3, matched models.
- **Decision rule (per rung):**
  - *Supported:* Paired mean F1 difference ≥ 0.03 in the predicted
    direction (higher-method ≥ lower-method), significant at p < 0.05
    by paired permutation test across 5 models.
  - *Falsified:* Mean difference ≤ 0 (lower method outperforms or ties).
  - *Inconclusive:* Positive difference < 0.03 or p ≥ 0.05.
  - *Overall:* H3 supported if ≥3 of 4 rungs are individually supported.
    H3 falsified if ≥2 rungs are falsified or show reversed direction.
- **Current evidence:** Partial. By-method means from 330 records (mixed
  models, not paired): direct 0.419, direct+multiturn 0.625, rag 0.684.
  Direction is consistent for rungs 1–2. Rung 3 (intermediate cell) and
  rung 4 (deep research after parser fix) have no paired data yet.
- **Status:** Confirmatory for rungs 1–2 (new matched-model sweeps
  needed); confirmatory for rung 3 (ticket 0144, cell does not exist
  yet); confirmatory for rung 4 (conditional on H1 parser fix).

---

### H4 — Method-quality metrics discriminate verification levels

- **Argument anchor:** §Method quality: verifiable vs. verified
  (lines 184–221)
- **Claim:** Method-quality metrics (citation validity rate,
  re-extraction agreement) statistically discriminate between
  single-agent (verifiable) and multi-agent (verified) runs, even when
  both achieve comparable F1 on the inventory extraction task.
- **Operational definition:**
  - *Citation validity rate:* fraction of emitted citations whose URL
    resolves and whose linked content contains the claimed fact.
    Measured by the `sweep_rag_verification` pipeline.
  - *Re-extraction agreement:* Cohen's kappa between the original
    extractor and an independent re-extraction agent on the same
    corpus.
  - Comparison: single-agent (`verification_modes = ["unverified"]`)
    vs. multi-agent (`verification_modes = ["cross", "multi_cross"]`).
- **Sweep:** `sweep_rag_verification` + `sweep_rag_verification_multi`.
  Base config: DeepSeek V3.2 decomposed RAG (F1 = 0.988).
- **Decision rule:**
  - *Supported:* Multi-agent runs show citation validity rate ≥ 0.10
    higher than single-agent, OR re-extraction agreement (kappa) ≥ 0.15
    higher, significant at p < 0.05 by bootstrap comparison, n=3 reps.
  - *Falsified:* Neither metric shows a difference > 0.05 at p < 0.10.
  - *Inconclusive:* One metric significant, the other not; or effect
    sizes between 0.05 and 0.10.
- **Current evidence:** Proof-of-concept only
  (`sweep_rag_verification_poc`, n=1, unverified vs. tool). Full
  factorial not yet run. Multi-agent verification (ticket 0059) was
  a negative result for F1 discrimination — but method-quality metrics
  were not measured in that run.
- **Status:** Exploratory. Requires new metric infrastructure (citation
  resolution, re-extraction pipeline) and full verification sweeps.

---

### H5 — Prompt-module composition effects

- **Argument anchor:** §Narrative arc, Part 2 (lines 254–257: "ablation
  decomposes the prompt-structure axis into modules")
- **Claim:** Prompt modules contribute differentially to F1 — the
  composite prompt significantly outperforms the base prompt, and
  individual module contributions are non-uniform across regimes.
- **Operational definition:** F1 macro on coal-only dev subset.
  Three conditions: base (no modules), composite (all 10 modules),
  single-module additions and single-module removals. Three regimes
  (direct, RAG, livesearch). Measured by the ablation sweep family.
- **Sweep:** `sweep_ablation_*` family — Phase 1 (base vs. composite
  across 3 regimes) and Phase 2 (single-module addition/removal).
  `modelset_ablation_phase2` (4 reasoning models), `repeat` = 3.
- **Decision rule:**
  - *Supported:* Composite mean F1 > base mean F1 by ≥ 0.05,
    significant at p < 0.05 by paired test across models, in ≥2 of 3
    regimes. AND at least 2 individual modules show |ΔF1| ≥ 0.02.
  - *Falsified:* Composite ≤ base in ≥2 regimes, or no individual
    module exceeds |ΔF1| = 0.02.
  - *Inconclusive:* Composite > base in 1 regime only, or all modules
    contribute uniformly (no module stands out).
- **Current evidence:** Phase 1 and Phase 2 ablation data exist (mixed
  temperature caveat — Phase 1 runs at T=null, invalidated; Phase 2
  re-run with controlled temperature). Data partially available but not
  yet analyzed for this specific decision rule.
- **Status:** Exploratory (threshold-setting informed by existing data).

---

### H6 — Small-model direct extraction reproduces

- **Argument anchor:** §Empirical caveat (lines 320–326: "qwen3.5:9b at
  F1 = 0.984 on direct extraction, n=1")
- **Claim:** The qwen3.5:9b F1 = 0.984 result on direct extraction
  reproduces under repeated runs on the coal-only dev subset.
- **Operational definition:** F1 macro on coal-only dev subset,
  `prompt_extract`, local Ollama inference, `seed` = 42, `no_think` =
  true.
- **Sweep:** `sweep_direct_extract_local` — filter to qwen3.5:9b only,
  `repeat` = 3. Or dedicated single-model sweep.
- **Decision rule:**
  - *Supported:* Mean F1 ≥ 0.95 at n=3, bootstrap 95% CI lower bound
    ≥ 0.90.
  - *Falsified:* Mean F1 < 0.90, indicating the n=1 result was a
    lucky draw.
  - *Inconclusive:* Mean F1 between 0.90 and 0.95.
- **Current evidence:** n=1, F1 = 0.984. Flagged by audit (finding #5)
  as too weak to draw conclusions. STATE.md priority 3.
- **Status:** Confirmatory (repeats not yet run).

---

### H7 — Intermediate cell isolates Coherence

- **Argument anchor:** §Narrative arc, Part 2 (lines 246–253: "the
  four-step ladder visits each limit; the deep-research step bundles two
  deltas, which is why ticket 0144's intermediate cell matters")
- **Claim:** The RAG + reasoning cell (no web access) achieves higher F1
  than RAG-only, isolating the Coherence contribution from the
  Freshness contribution bundled in deep research.
- **Operational definition:** F1 macro on coal-only dev subset. Same
  model × same prompt (`prompt_extract`), RAG mode + reasoning model
  vs. RAG mode + non-reasoning model (or same model with/without
  extended thinking). Five matched models, 3 reps.
- **Sweep:** New sweep needed (ticket 0144). RAG mode with reasoning
  enabled, no web. Compare against `sweep_regimes_rag_*` baseline.
- **Decision rule:**
  - *Supported:* RAG+reasoning mean F1 > RAG-only mean F1 by ≥ 0.02,
    paired permutation test p < 0.05 across 5 models.
  - *Falsified:* RAG+reasoning ≤ RAG-only (reasoning adds nothing or
    hurts when web is absent).
  - *Inconclusive:* Positive difference < 0.02 or p ≥ 0.05.
- **Current evidence:** Cell does not exist. This is the "missing link"
  identified in argument.md and audit finding #2.
- **Status:** Confirmatory (cell not yet run).

---

## Observational claims (not preregistered)

The following structural claims from `argument.md` are design assertions
or historical observations. They frame the experimental matrix but are
not falsifiable within this paper's design.

### O1 — Capability DAG structure

- **Argument anchor:** §Why the order is observed, not forced
  (lines 128–167)
- **Claim:** The capability ladder follows a DAG: LLM → RAG →
  {web ∥ reason} → deep research → agent → team. Stages 3 and 4 are
  parallel branches, not strictly sequential.
- **Evidence type:** Historical observation from four labs'
  product-release timelines (documented in `capability-timeline.md`).
- **Audit qualification:** "Stage 5 forced" weakened to observational
  language per audit finding #3 (3/6 consensus).
- **Status:** Observational. Not preregistered.

### O2 — Information-condition collinearity

- **Argument anchor:** §The dimensions in play (lines 37–39)
- **Claim:** Information condition (parametric / +docs / +web / +tools)
  is colinear with the method axis; it is a property of the method, not
  a separate lens.
- **Note:** Testing collinearity would require a sweep that varies
  information condition independently of method — e.g., a RAG run
  without document provision, or a direct run with web access disabled.
  The current experimental design does not include such cells. If
  ticket 0153 (redesign experiments) introduces them, this could be
  promoted to an exploratory hypothesis.
- **Status:** Observational. Route to 0153 for potential promotion.

### O3 — Weak-internal coherence scoping

- **Argument anchor:** §Provenance of each term, Coherence
  (lines 103–121)
- **Claim:** The paper measures weak-internal coherence only (no
  contradiction among extracted claims). Strong coherence (closure
  under entailment) and external coherence (against source documents)
  are out of scope.
- **Audit qualification:** Mistral flagged this as a limitation (audit
  finding #7). Accepted as a scoping decision, documented in the paper's
  limitations section.
- **Status:** Observational (scoping decision, not a testable claim).

---

## Summary table

| ID | Short name | Type | Precondition | Sweep |
|----|-----------|------|--------------|-------|
| H1 | Deep-research saturation (cloud) | Confirmatory* | Parser fix | `sweep_direct_complete` (repeat→3) |
| H2 | Deep-research saturation (local) | Confirmatory | None | New: `sweep_direct_complete_local` |
| H3 | Method ladder closes limits | Confirmatory | Ticket 0144 cell | `sweep_regimes_*` + new RAG+reasoning |
| H4 | Method-quality discrimination | Exploratory | Metric infra | `sweep_rag_verification*` |
| H5 | Prompt-module composition | Exploratory | Temperature control | `sweep_ablation_*` |
| H6 | Small-model reproduces | Confirmatory | None | `sweep_direct_extract_local` (qwen3.5:9b ×3) |
| H7 | Intermediate cell (Coherence) | Confirmatory | Ticket 0144 | New: RAG+reasoning sweep |
| O1 | Capability DAG | Observational | — | — |
| O2 | Info-condition collinearity | Observational | — | Route to 0153 |
| O3 | Weak-internal coherence scope | Observational | — | — |

\* Conditional on evaluator-artifact resolution (STATE.md priority 2).

---

## Preregistration workflow rule

Once the confirmatory hypotheses (H1, H2, H3, H6, H7) are submitted to
OSF Registries and timestamped, they are **frozen**. Any modification to
a registered hypothesis — threshold, decision rule, sweep configuration,
or operational definition — requires a registered amendment on OSF before
the modified sweep is run. Exploratory hypotheses (H4, H5) and
observational claims (O1–O3) are not subject to this constraint.

OSF registration draft: `docs/preregistration-osf.md`.
Registry DOI: *to be filled after submission.*

---

## Confirmatory / exploratory split for preregistration (ticket 0150)

**Preregisterable (confirmatory):** H1, H2, H3, H6, H7. These have
sharp predictions testable by new sweeps not yet run, with pre-committed
thresholds and decision rules.

**Declared exploratory:** H4, H5. These are informed by existing data
patterns, require new metric infrastructure, or have thresholds that
cannot be set without prior data. They will be reported as exploratory
analyses with appropriate caveats.

**Not preregistered:** O1, O2, O3. Structural framings, not empirical
predictions within the paper's experimental scope.
