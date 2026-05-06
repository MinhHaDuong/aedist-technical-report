# OSF Preregistration — AEDIST Benchmark

*Draft prepared for submission to [OSF Registries](https://osf.io/registries).
Template: OSF Standard Pre-Data Collection Registration.
Source document: `docs/hypotheses.md` (ticket 0149, PR #316).
Operational definitions are reproduced verbatim — do not edit between
this document and the registry form.*

---

## 1. Study information

### Title

Beyond RAG: Stateful-Agentic Architectures for Reliable Economic
Statistics — Confirmatory Hypotheses for the AEDIST Benchmark

### Authors

Minh Ha-Duong

### Description

The AEDIST benchmark evaluates LLM-based methods for extracting
structured energy infrastructure data (power plant inventories) from
open sources. It measures the method axis — from direct parametric
extraction through RAG, reasoning, and deep-research architectures —
on a fixed reference dataset (Vietnam thermal power, coal-only dev
subset).

This preregistration covers four confirmatory hypotheses (H1, H2, H3,
H4) derived from the project's argument document
(`docs/argument.md`). Each hypothesis tests a specific prediction about
how method complexity, model provenance, or prompt structure affects
extraction quality (F1 macro). Decision rules, thresholds, and sweep
configurations are pre-specified before any new experimental data is
collected.

Existing data (327 records as of 2026-04-30) informed the experimental
design and hypothesis formulation but does not determine confirmatory
thresholds. Thresholds are grounded in operational sufficiency for the
downstream use case (PyPSA-ASEAN pipeline input) or in pre-committed
effect sizes.

Two additional analyses (method-quality metrics; prompt-module
composition) are declared exploratory and are not included in this
registration.

### Hypotheses

**H1 — Method ladder rung 1: Articulation.** Direct → multiturn adds
measurable F1 via the Articulation mechanism. Claim: paired mean
ΔF1 ≥ 0.03, p < 0.05, one-sided permutation test across 5 matched
models × 3 reps.

**H2 — Method ladder rung 2: Coverage.** Multiturn → RAG adds
measurable F1 via the Coverage mechanism. Decision: same as H1.

**H3 — Accuracy–provenance incompatibility in single parametric prompts.**
A frontier model given a single prompt without document provision cannot
simultaneously achieve full recall and verifiable per-row attribution.
Asking for source citations collapses recall; not asking yields no
provenance. Test: compare F1(`prompt_complete`, no web) vs
F1(`prompt_extract`, no web) on a matched 5-model panel. Supported if
mean ΔF1 < −0.10 AND citation validity rate on `prompt_complete` < 0.50.
Falsified if ΔF1 > −0.05 AND citation validity ≥ 0.50.

**H4 — Local model approaches cloud frontier result quality.** A local
open-weight model on a single workstation GPU (≤16 GB VRAM) approaches
cloud frontier result quality; auditability arrives as a structural
property. "Approaches" = within 0.05 F1 of cloud frontier mean.

---

## 2. Design plan

### Study type

Computational experiment (benchmark evaluation). Not a human-subjects
study.

### Blinding

Not applicable. The evaluation pipeline is deterministic: model outputs
are scored against a fixed reference dataset by `cmd_evaluate()`.
There is no subjective judgment in scoring.

### Study design

Factorial benchmark design. The experimental matrix crosses:
- **Method** (4 levels): direct, multiturn, RAG, deep research
  (reasoning + web + `prompt_complete`).
- **Model** (variable): frontier cloud models (12, from 10 labs), local
  open-weight models (2–4), matched 5-model panels for paired tests.
- **Prompt**: `prompt_extract` for H1/H2; `prompt_complete` (with
  reasoning and web search) for H3 and H4.
- **Repetitions**: n=3 per cell (MoE models also n=3 minimum per project rule).

Fixed factors: reference dataset (Vietnam thermal v1, coal-only dev
subset), evaluation function (`cmd_evaluate()`), seed=42.

---

## 3. Sampling plan

### Existing data

Yes. 327 experimental records exist as of 2026-04-30. These were used
to formulate hypotheses and select the experimental design. No
confirmatory threshold was set by inspecting existing effect sizes.
Existing data is referenced for context only.

### Explanation of existing data

The 327 records cover 57 model×method×prompt combinations across
direct, multiturn, RAG, and deep-research regimes. Key observations
from existing data:
- Best F1 = 0.988 (DeepSeek V3.2, decomposed RAG, n=4).
- Deep-research (`prompt_complete`) results were previously degraded:
  best n=1 F1 = 0.557, with 3/12 models returning parser failures.
  A parser artifact (evaluator could not parse structured-document
  output) was fixed before H3 sweeps can run (ticket 0163, Done
  2026-05-05).
- qwen3.5:9b achieved F1 = 0.984 on direct extraction (n=1), providing
  a data point for local model capability.

### Data collection procedures

Each experimental run:
1. Assemble the prompt from modular components (`prompt_extract` or
   `prompt_complete`).
2. Call the LLM API (cloud via OpenRouter, local via Ollama) with
   fixed parameters: `seed=42`, `temperature=0.0` (when supported),
   `max_tokens` per model spec.
3. Parse the model response into a structured power-plant inventory.
4. Score against the reference dataset using `cmd_evaluate()`,
   which computes per-plant precision, recall, and F1 macro.
5. Record all parameters and results to `measurements.jsonl` via
   `records_to_metrics()`.

### Sample size

Per hypothesis:
- **H1:** 5 matched models × 2 conditions (direct, multiturn) × 3 reps
  = 30 runs.
- **H2:** 5 matched models × 2 conditions (multiturn, RAG) × 3 reps
  = 30 runs (multiturn baseline shared with H1).
- **H3:** 5 matched models × 2 conditions (prompt_extract, prompt_complete no-web) × 3 reps = 30 runs (Condition A baseline shared with H1/H2).
- **H4:** 2–4 local models × 3 reps = 6–12 runs.

Total new runs: approximately 75–85 (after accounting for shared
baselines).

### Sample size rationale

n=3 repetitions per cell provides sufficient data for bootstrap 95%
confidence intervals on F1. For paired comparisons (H1, H2), 5 models
× 3 reps gives 15 paired observations per rung, adequate for
permutation tests at α=0.05.

MoE models (DeepSeek V3.2, deepseek-v3) use n=3 minimum (project rule:
non-deterministic even with seed pinning due to tensor parallelism).

---

## 4. Variables

### Measured variables

**Primary outcome:** F1 macro on the coal-only dev subset (Vietnam
thermal v1 reference). Computed by `cmd_evaluate()` as the
harmonic mean of precision and recall, macro-averaged across plants.

**Secondary (recorded but not used for confirmatory decisions):**
- Per-plant precision and recall.
- Completion tokens, wall time, cost.
- Finish reason (stop, length, tool_calls).
- Raw model response (archived as `.record.json`).

### Indices

No composite indices. F1 macro is the sole confirmatory metric.
Bootstrap 95% CI computed by resampling across repetitions (n=3)
within each model.

---

## 5. Analysis plan

### Statistical models

**H1 (Articulation rung):** Paired permutation test. For the
direct → multiturn rung, compute the paired mean F1 difference
(multiturn minus direct) across 5 matched models (using per-model
mean of n=3 reps on `prompt_extract`). Test statistic: mean paired
difference. P-value: proportion of 10,000 permutations (sign flips)
yielding a test statistic ≥ observed. One-sided test (predicted
direction: multiturn ≥ direct).

**H2 (Coverage rung):** Same paired permutation test as H1, applied to
the multiturn → RAG rung on `prompt_extract`.

**H3 (parametric incompatibility):** Paired permutation test. For each
of 5 matched models, compute mean F1 under `prompt_extract` (Condition A)
and `prompt_complete` without web (Condition B), both parametric. Test
statistic: mean paired ΔF1 = F1(B) − F1(A). P-value: proportion of
10,000 sign-flip permutations with test statistic ≤ observed. One-sided
test (predicted direction: B < A). Also compute citation validity rate on
Condition B outputs; report as descriptive (no significance test on
citation validity). If citation-validity instrumentation is not complete,
the ΔF1 test still runs; only the secondary measure is missing.

**H4 (local vs. cloud):** Compute mean F1 and bootstrap 95% CI for
2–4 local models. Compare local mean F1 against the cloud frontier
mean from H3 runs. Gap = cloud frontier mean − local mean. The
"auditability as structural property" claim is interpretive and is not
part of the test statistic; it will be argued in prose based on the
model's deployment characteristics.

### Transformations

None. F1 is bounded [0, 1] and approximately normally distributed in
the range of interest (0.4–1.0). No transformation needed.

### Inference criteria

- **Significance threshold:** α = 0.05 (one-sided) for permutation
  tests (H1, H2).
- **Bootstrap CI:** 95%, bias-corrected and accelerated (BCa), 10,000
  resamples.
- **No multiple-comparison correction** across hypotheses. Each
  hypothesis tests a distinct, pre-specified prediction. The four
  hypotheses are not a family of tests on the same null.

### Data exclusion

- Runs where the model produces unparseable output (e.g., empty
  response, timeout, API error) are excluded from analysis and reported
  separately as "parser failures" with count and reason.
- No post-hoc exclusion of models or runs based on outcome values.
- If H3's parser-fix precondition is not verified (parser still fails
  on `prompt_complete` output for ≥3 models), H3 is declared untestable
  and the precondition failure is reported.

### Missing data

- Missing F1 values (parser failure, API timeout) are not imputed.
  Analysis proceeds on complete cases. The count and identity of
  missing runs are reported.
- If a model produces output for fewer than 3 reps, that model is
  excluded from the per-model mean and CI calculation but reported.

### Exploratory analyses (not preregistered)

The following analyses will be reported as exploratory:
- **Method-quality metrics** (citation validity, re-extraction
  agreement) discriminating verification levels. Requires new metric
  infrastructure not yet built.
- **Prompt-module composition effects.** Ablation sweep analysis
  with thresholds informed by existing data.
- Cost-effectiveness analysis (F1 per dollar).
- Model-family clustering and architecture effects (dense vs. MoE).
- Temperature sensitivity (if controlled-temperature sweeps are run).

---

## 6. Decision rules (summary)

| Hypothesis | Supported | Falsified | Inconclusive |
|------------|-----------|-----------|--------------|
| H1 (Articulation) | Paired ΔF1 ≥ 0.03, p < 0.05 | Paired ΔF1 < 0 (reversed) | Positive Δ < 0.03 or p ≥ 0.05 |
| H2 (Coverage) | Paired ΔF1 ≥ 0.03, p < 0.05 | Paired ΔF1 < 0 (reversed) | Positive Δ < 0.03 or p ≥ 0.05 |
| H3 (parametric incompatibility) | Mean ΔF1 < −0.10, p < 0.05, AND citation validity < 0.50 | Mean ΔF1 > −0.05 AND citation validity ≥ 0.50 | ΔF1 between −0.05 and −0.10, or citation validity mixed |
| H4 (local vs. cloud) | Local mean F1 ≥ cloud mean − 0.05, CI lb ≥ 0.90 | Gap > 0.10 | Gap between 0.05 and 0.10 |

---

## 7. Preconditions and timeline

Several hypotheses have preconditions that must be resolved before
their sweeps can run:

| Hypothesis | Precondition | Status |
|------------|-------------|--------|
| H1 | None | Ready |
| H2 | None | Ready |
| H3 | Parser fix for `prompt_complete` output (ticket 0163) | Done (2026-05-05) |
| H4 | None (compares local model against H1/H2 baseline, not H3) | Ready |

The preregistration timestamp must precede any new sweep runs for the
confirmatory hypotheses. Existing data (327 records, collected before
this registration) is declared as prior.

---

## 8. Source traceability

- Hypotheses extracted from: `docs/argument.md`
- Hypothesis list: `docs/hypotheses.md` (ticket 0149, PR #316)
- Experimental design: `experiments.toml` (sweep configurations)
- Evaluation code: `src/aedist/evaluate.py` (`cmd_evaluate()`)
- Metrics pipeline: `src/aedist/measurements.py` (`records_to_metrics()`)
- Repository: [AEDIST on GitHub](https://github.com/MinhHaDuong/aedist-technical-report)

---

*Registry DOI:* `[TO BE FILLED AFTER SUBMISSION]`
*Registration date:* `[TO BE FILLED AFTER SUBMISSION]`
