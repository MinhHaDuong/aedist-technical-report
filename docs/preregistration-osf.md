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

This preregistration covers five confirmatory hypotheses (H1, H2, H3,
H6, H7) derived from the project's argument document
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

Two additional hypotheses (H4: method-quality metrics, H5: prompt-module
composition) are declared exploratory and are not included in this
registration.

### Hypotheses

**H1 — Deep-research saturation (cloud).** Deep research (reasoning +
web search + `prompt_complete` prompt) on cloud frontier models
saturates both data and answer quality, reaching F1 comparable to or
exceeding the current decomposed-RAG ceiling (F1 = 0.988).

**H2 — Deep-research saturation (local / sovereign).** At least one
open-weight model runnable locally (e.g., Magistral, Qwen 3.5 122B)
achieves deep-research saturation on the same task.

**H3 — Method ladder closes named limits measurably.** Each step on the
method ladder produces a measurable F1 improvement attributable to the
named limit via the mechanism each step adds. The ladder is a partial
order (DAG), not a strict linear chain. Four rungs: direct → multiturn
(Articulation), multiturn → RAG (Coverage), RAG → RAG+reasoning
(Coherence), RAG+reasoning → deep research (Freshness).

**H6 — Small-model direct extraction reproduces.** The qwen3.5:9b
F1 = 0.984 result on direct extraction (n=1) reproduces under repeated
runs (n=3) on the coal-only dev subset.

**H7 — Intermediate cell isolates Coherence.** The RAG + reasoning cell
(no web access) achieves higher F1 than RAG-only, isolating the
Coherence contribution from the Freshness contribution bundled in deep
research.

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
- **Method** (5 levels): direct, multiturn, RAG, RAG+reasoning, deep
  research.
- **Model** (variable): frontier cloud models (12, from 10 labs), local
  open-weight models (2–4), matched 5-model panels for paired tests.
- **Prompt** (fixed per hypothesis): `prompt_extract` for H3/H6/H7,
  `prompt_complete` for H1/H2.
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
- Deep-research (`prompt_complete`) results are currently degraded:
  best n=1 F1 = 0.557, with 3/12 models returning parser failures.
  A parser artifact (evaluator cannot parse structured-document output)
  must be fixed before H1 sweeps can run.
- qwen3.5:9b achieved F1 = 0.984 on direct extraction (n=1), flagged
  as requiring confirmation.
- RAG+reasoning cell does not exist in existing data.

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
- **H1:** 12 frontier models × 3 reps = 36 runs.
- **H2:** 2–4 local models × 3 reps = 6–12 runs.
- **H3:** 5 matched models × 4 rungs × 3 reps = 60 runs (20 per rung,
  shared baselines across adjacent rungs).
- **H6:** 1 model (qwen3.5:9b) × 3 reps = 3 runs.
- **H7:** 5 matched models × 2 conditions (RAG, RAG+reasoning) × 3
  reps = 30 runs (RAG baseline shared with H3 rung 2).

Total new runs: approximately 105–135 (after accounting for shared
baselines).

### Sample size rationale

n=3 repetitions per cell provides sufficient data for bootstrap 95%
confidence intervals on F1. For paired comparisons (H3, H7), 5 models
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

**H1 (cloud saturation):** Descriptive. For each of 12 frontier
models, compute mean F1 and bootstrap 95% CI across n=3 reps.
Decision: count how many models achieve mean F1 ≥ 0.95 with CI lower
bound ≥ 0.90.

**H2 (local saturation):** Same as H1, applied to 2–4 local models.
Decision: at least one model achieves mean F1 ≥ 0.95, CI lower bound
≥ 0.90.

**H3 (method ladder):** Paired permutation test per rung. For each
rung, compute the paired mean F1 difference (higher-method minus
lower-method) across 5 matched models (using per-model mean of n=3
reps). Test statistic: mean paired difference. P-value: proportion of
10,000 permutations (sign flips) yielding a test statistic ≥ observed.
One-sided test (predicted direction: higher method ≥ lower method).

**H6 (small-model reproduces):** Descriptive. Compute mean F1 and
bootstrap 95% CI for qwen3.5:9b across n=3 reps of direct extraction.

**H7 (intermediate cell):** Same paired permutation test as H3,
comparing RAG+reasoning vs. RAG-only across 5 matched models.

### Transformations

None. F1 is bounded [0, 1] and approximately normally distributed in
the range of interest (0.4–1.0). No transformation needed.

### Inference criteria

- **Significance threshold:** α = 0.05 (one-sided) for permutation
  tests (H3, H7).
- **Bootstrap CI:** 95%, bias-corrected and accelerated (BCa), 10,000
  resamples.
- **No multiple-comparison correction** across hypotheses. Each
  hypothesis tests a distinct, pre-specified prediction. The five
  hypotheses are not a family of tests on the same null.

### Data exclusion

- Runs where the model produces unparseable output (e.g., empty
  response, timeout, API error) are excluded from analysis and reported
  separately as "parser failures" with count and reason.
- No post-hoc exclusion of models or runs based on outcome values.
- If H1's parser-fix precondition is not met (parser still fails on
  `prompt_complete` output for ≥3 models), H1 is declared untestable
  and the precondition failure is reported.

### Missing data

- Missing F1 values (parser failure, API timeout) are not imputed.
  Analysis proceeds on complete cases. The count and identity of
  missing runs are reported.
- If a model produces output for fewer than 3 reps, that model is
  excluded from the per-model mean and CI calculation but reported.

### Exploratory analyses (not preregistered)

The following analyses will be reported as exploratory:
- **H4 — Method-quality metrics** (citation validity, re-extraction
  agreement) discriminate verification levels. Requires new metric
  infrastructure not yet built.
- **H5 — Prompt-module composition effects.** Ablation sweep analysis
  with thresholds informed by existing data.
- Cost-effectiveness analysis (F1 per dollar).
- Model-family clustering and architecture effects (dense vs. MoE).
- Temperature sensitivity (if controlled-temperature sweeps are run).

---

## 6. Decision rules (summary)

| Hypothesis | Supported | Falsified | Inconclusive |
|------------|-----------|-----------|--------------|
| H1 (cloud) | Mean F1 ≥ 0.95 for ≥3 models, CI lb ≥ 0.90 | No model F1 ≥ 0.90 after parser fix | 1–2 models reach ≥0.95, or CI straddles 0.90 |
| H2 (local) | ≥1 model F1 ≥ 0.95, CI lb ≥ 0.90 | No model F1 > 0.80 | Best between 0.80 and 0.95 |
| H3 (ladder) | ≥3/4 rungs: paired ΔF1 ≥ 0.03, p < 0.05 | ≥2 rungs falsified or reversed | Positive Δ < 0.03 or p ≥ 0.05 |
| H6 (small) | Mean F1 ≥ 0.95, CI lb ≥ 0.90 | Mean F1 < 0.90 | Mean F1 between 0.90 and 0.95 |
| H7 (coherence) | RAG+reasoning > RAG by ≥ 0.02, p < 0.05 | RAG+reasoning ≤ RAG | Positive Δ < 0.02 or p ≥ 0.05 |

---

## 7. Preconditions and timeline

Several hypotheses have preconditions that must be resolved before
their sweeps can run:

| Hypothesis | Precondition | Status |
|------------|-------------|--------|
| H1 | Parser fix for `prompt_complete` output (ticket 0163) | Done (2026-05-05) |
| H2 | None (but benefits from H1 parser fix) | Ready |
| H3 rungs 1–2 | None | Ready |
| H3 rungs 3–4 | Ticket 0144 (RAG+reasoning cell) | Pending |
| H6 | None | Ready |
| H7 | Ticket 0144 (RAG+reasoning cell) | Pending |

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
