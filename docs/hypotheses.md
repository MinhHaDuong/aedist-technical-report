# Hypotheses — AEDIST benchmark

*Updated 2026-05-06. Previous H1–H7 structure retired in favour of four
confirmatory hypotheses (H1–H4) aligned with the paper synopsis. Old
operational detail preserved below under the new numbering.*

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

### H1 — Method ladder rung 1: Articulation (direct → multiturn)

- **Argument anchor:** §The four limits (Articulation row); §Narrative arc,
  Part 2
- **Claim:** Direct → multiturn adds measurable F1 via the Articulation
  mechanism (multi-turn clarification closes the gap between what the user
  means and what the model answers).
- **Operational definition:** F1 macro on coal-only dev subset (Vietnam
  thermal v1 reference), `prompt_extract` prompt, 5 matched models × 3
  reps each. Condition A = direct; Condition B = multiturn.
- **Sweep:** `sweep_regimes_direct_*` vs `sweep_regimes_multiturn_*`,
  `repeat` = 3, matched model panel.
- **Decision rule:**
  - *Supported:* Paired mean F1 difference (multiturn − direct) ≥ 0.03,
    p < 0.05 by one-sided paired permutation test across 5 models.
  - *Falsified:* Mean difference ≤ 0 (direct outperforms or ties).
  - *Inconclusive:* Positive difference < 0.03 or p ≥ 0.05.
- **Current evidence:** By-method means from 330 records (mixed models,
  not paired): direct 0.419, multiturn 0.625. Direction consistent;
  paired test not yet run.
- **Status:** Confirmatory (matched-model sweeps needed).

---

### H2 — Method ladder rung 2: Coverage (multiturn → RAG)

- **Argument anchor:** §The four limits (Coverage row); §Narrative arc,
  Part 2
- **Claim:** Multiturn → RAG adds measurable F1 via the Coverage mechanism
  (document provision closes facts the model never saw in training).
- **Operational definition:** Same as H1. Condition A = multiturn;
  Condition B = RAG. Same 5 matched models × 3 reps.
- **Sweep:** `sweep_regimes_multiturn_*` vs `sweep_regimes_rag_*`,
  `repeat` = 3, matched model panel.
- **Decision rule:** Same as H1 (paired ΔF1 ≥ 0.03, p < 0.05,
  one-sided, direction: RAG ≥ multiturn).
- **Current evidence:** multiturn 0.625, RAG 0.684 (unpaired means).
  Direction consistent; paired test not yet run.
- **Status:** Confirmatory (matched-model sweeps needed).

---

### H3 — Accuracy–provenance incompatibility in single parametric prompts

- **Argument anchor:** §Method quality: verifiable vs. verified;
  §Narrative arc, Part 3
- **Claim:** A frontier model given a single prompt without document
  provision cannot simultaneously achieve full recall and verifiable
  per-row attribution. Asking for source citations causes the model to
  report only what it can justify — collapsing recall. Not asking for
  citations produces high recall but no provenance. The two requirements
  are incompatible in the single-prompt parametric regime.
- **Why this matters:** If the incompatibility is real, no prompt
  engineering fixes it — a multi-step or retrieval-based architecture is
  necessary. This is the paper's central structural motivation.
- **Operational definition:**
  - *Condition A:* `prompt_extract` (attribution not requested), frontier
    model, parametric (no web, no RAG).
  - *Condition B:* `prompt_complete` (per-row source columns + bibliography
    required), same model, parametric (no web, no RAG).
  - *Primary measure:* ΔF1 = F1(B) − F1(A). A large negative delta
    confirms recall collapse.
  - *Secondary measure:* citation validity rate on Condition B outputs
    (fraction of cited sources that resolve and contain the claim).
- **Sweep:** Matched 5-model panel, `repeat` = 3, parametric only.
  `sweep_regimes_direct_extract` (Condition A, reuse existing) vs new
  `sweep_direct_complete_no_web` (Condition B, no web access).
- **Decision rule:**
  - *Supported:* Mean ΔF1 < −0.10 across matched models AND Condition B
    citation validity rate < 0.50 — recall collapses when attribution is
    requested, and the citations are not trustworthy anyway.
  - *Falsified:* Mean ΔF1 > −0.05 AND citation validity ≥ 0.50 — both
    accuracy and provenance are achievable in a single prompt.
  - *Inconclusive:* ΔF1 between −0.05 and −0.10, or citation validity
    mixed (0.50–0.90).
- **Precondition:** Parser fix for `prompt_complete` output (ticket 0163,
  Done 2026-05-05).
- **Current evidence:** Indirect only. `prompt_complete` best F1 = 0.557
  (GLM-5 Turbo, n=1, with web access) vs `prompt_extract` best F1 = 0.988
  (DeepSeek V3.2, RAG). Controlled parametric comparison not yet run;
  confounds (web, reasoning, regime) prevent attribution of the gap.
- **Status:** Confirmatory (new `sweep_direct_complete_no_web` needed).

---

### H4 — Local model approaches cloud frontier result quality

- **Argument anchor:** §Narrative arc, Part 2 (lines 262–264)
- **Claim:** A curated retrieval pipeline on a local open-weight model
  running on a single workstation GPU (≤16 GB VRAM, e.g. A4000)
  approaches cloud frontier result quality, with auditability arriving as
  a structural property of the setup. Whether this requires the full
  deep-research stack or whether parametric extraction on a well-chosen
  model already suffices remains to be determined.
- **Operational definition:** F1 macro on coal-only dev subset.
  Best local model (qwen3.5:122b or qwen3.5:9b) vs. best cloud frontier
  model, both at n=3. "Approaches" = within 0.05 F1 of cloud frontier
  mean.
- **Sweep:** `sweep_direct_complete_local` (local model, `repeat` = 3)
  + comparison against cloud frontier best (H3 sweep).
- **Decision rule:**
  - *Supported:* Local mean F1 ≥ cloud frontier mean F1 − 0.05,
    bootstrap 95% CI lower bound ≥ 0.90.
  - *Falsified:* Local mean F1 < cloud frontier mean F1 − 0.10.
  - *Inconclusive:* Gap between 0.05 and 0.10.
- **Current evidence:** qwen3.5:9b F1 = 0.984 on direct extraction (n=1,
  `prompt_extract`, no RAG). No local `prompt_complete` runs. Parametric
  extraction may already suffice without deep-research infrastructure.
- **Status:** Confirmatory.

---

## Exploratory hypotheses

### X1 — Method-quality metrics discriminate verification levels

*(Previously H4)*

- **Argument anchor:** §Method quality: verifiable vs. verified
  (lines 184–221)
- **Claim:** Method-quality metrics (citation validity rate,
  re-extraction agreement) statistically discriminate between
  single-agent (verifiable) and multi-agent (verified) runs, even when
  both achieve comparable F1.
- **Operational definition:**
  - *Citation validity rate:* fraction of emitted citations whose URL
    resolves and whose linked content contains the claimed fact.
  - *Re-extraction agreement:* Cohen's kappa between the original
    extractor and an independent re-extraction agent.
  - Comparison: single-agent vs. multi-agent runs.
- **Sweep:** `sweep_rag_verification` + `sweep_rag_verification_multi`.
- **Status:** Exploratory. Requires new metric infrastructure.

---

### X2 — Prompt-module composition effects

*(Previously H5)*

- **Argument anchor:** §Narrative arc, Part 2 (lines 254–257)
- **Claim:** Prompt modules contribute differentially to F1 — the
  composite prompt outperforms the base prompt, and individual module
  contributions are non-uniform across regimes.
- **Sweep:** `sweep_ablation_*` family.
- **Status:** Exploratory (threshold-setting informed by existing data).

---

## Observational claims (not preregistered)

### O1 — Capability DAG structure

- **Argument anchor:** §Why the order is observed, not forced
- **Claim:** The capability ladder follows a DAG: LLM → RAG →
  {web ∥ reason} → deep research → agent → team. Stages 3 and 4 are
  parallel branches, not strictly sequential.
- **Evidence type:** Historical observation from four labs' product-release
  timelines (documented in `capability-timeline.md`).
- **Status:** Observational. Not preregistered.

### O2 — Information-condition collinearity

- **Argument anchor:** §The dimensions in play
- **Claim:** Information condition (parametric / +docs / +web / +tools)
  is colinear with the method axis; it is a property of the method, not
  a separate lens.
- **Status:** Observational. Route to 0153 for potential promotion.

### O3 — Weak-internal coherence scoping

- **Argument anchor:** §Provenance of each term, Coherence
- **Claim:** The paper measures weak-internal coherence only (no
  contradiction among extracted claims). Strong coherence and external
  coherence are out of scope.
- **Status:** Observational (scoping decision).

---

## Summary table

| ID | Short name | Type | Precondition | Sweep |
|----|-----------|------|--------------|-------|
| H1 | Ladder rung 1: Articulation | Confirmatory | None | `sweep_regimes_direct/multiturn` (repeat→3) |
| H2 | Ladder rung 2: Coverage | Confirmatory | None | `sweep_regimes_multiturn/rag` (repeat→3) |
| H3 | Frontier fails provenance bar | Confirmatory | Parser fix (done) | `sweep_direct_complete` (×12, ×3) + audit |
| H4 | Local approaches frontier | Confirmatory | None | `sweep_direct_complete_local` (repeat→3) |
| X1 | Method-quality discrimination | Exploratory | Metric infra | `sweep_rag_verification*` |
| X2 | Prompt-module composition | Exploratory | Temperature control | `sweep_ablation_*` |
| O1 | Capability DAG | Observational | — | — |
| O2 | Info-condition collinearity | Observational | — | Route to 0153 |
| O3 | Weak-internal coherence scope | Observational | — | — |

---

## Preregistration workflow rule

Once the confirmatory hypotheses (H1, H2, H3, H4) are submitted to
OSF Registries and timestamped, they are **frozen**. Any modification to
a registered hypothesis — threshold, decision rule, sweep configuration,
or operational definition — requires a registered amendment on OSF before
the modified sweep is run. Exploratory hypotheses (X1, X2) and
observational claims (O1–O3) are not subject to this constraint.

OSF registration draft: `docs/preregistration-osf.md`.
Registry DOI: *to be filled after submission.*

---

## Confirmatory / exploratory split for preregistration (ticket 0150)

**Preregisterable (confirmatory):** H1, H2, H3, H4. These have sharp
predictions testable by new sweeps not yet run, with pre-committed
thresholds and decision rules.

**Declared exploratory:** X1, X2. These are informed by existing data
patterns, require new metric infrastructure, or have thresholds that
cannot be set without prior data.

**Not preregistered:** O1, O2, O3. Structural framings, not empirical
predictions within the paper's experimental scope.
