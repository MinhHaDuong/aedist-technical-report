# Exp2 Analysis Report Outline (Protocol-First)

Status: outline rewrite for report construction
Date: 2026-05-23

This document defines where each piece of the Exp2 report goes.
Writing can be LLM-assisted after each artefact is generated and reviewed.

## 0) Inputs and constraints (fixed)

Primary protocol source:
- experiments/sota/protocol_05_experiment.md (especially section 3.5.1 and section 3.8)

Primary data sources for this report:
- experiments/outputs/sota_exp2_naive_arm/summary_20260522T2342Z.json
- experiments/outputs/sota_exp2_brerun1/summary.json

Explicit exclusion:
- experiments/outputs/sota_exp2_phase_b_full (README starts with "WEAK CLASSIFIER -- DO NOT USE")

## 1) Introduction

### Section title
Introduction

### What goes here
- Problem statement: can an optimized deep-research protocol improve structured energy-inventory extraction quality vs naive single-shot querying?
- Why Exp2 exists in the full report sequence.
- Scope boundaries: Exp2 claims only; no cross-experiment synthesis beyond explicit references.
- Epistemic framing from protocol section 3.3 (reference dataset is methodological artefact, not canonical truth).

### Placeholder artefacts
- Table placeholder: report/inputs/generated/tab_exp2_outline_dataset.tex
- Figure placeholder: report/inputs/generated/fig_exp2_outline_dataset.tex

### Placeholder test block
- No inferential test here; this section is framing only.

### Placeholder conclusion block
- 1 paragraph: what this experiment is designed to detect and what it is not designed to prove.

## 2) Context and protocol lock

### Section title
Context and Protocol Lock

### What goes here
- Two-arm design recap (naive vs optimized), N=5 per model per arm.
- Subject set and operational budget framing.
- Pre-registered analysis commitments H1-H6 (verbatim mapping to tests and falsifiers).
- Exclusion criteria and multiple-comparison correction (Bonferroni for H1-H3).

### Placeholder artefacts
- Table placeholder: report/inputs/generated/tab_exp2_outline_hypotheses_map.tex
- Table placeholder: report/inputs/generated/tab_exp2_outline_protocol_fidelity.tex

### Placeholder test block
- No statistical execution in this section; protocol lock only.

### Placeholder conclusion block
- 1 paragraph: what evidence is mandatory before claiming each hypothesis outcome.

## 3) Dataset and descriptive statistics

### Section title
Dataset and Descriptive Statistics

### What goes here
- Dataset provenance and run counts by arm and model.
- Descriptive statistics: report-rate, turns, cost, wall-time, and quality metric availability status.
- Data quality caveats and excluded run sets.

### Placeholder artefacts
- Table placeholder: report/inputs/generated/tab_exp2_outline_dataset.tex
- Figure placeholder: report/inputs/generated/fig_exp2_outline_dataset.tex

### Placeholder test block
- Descriptive only (no hypothesis test in this section).

### Placeholder conclusion block
- 1 paragraph: descriptive baseline used by all hypothesis sections.

## 4) H1

### Section title
H1 - Optimized arm has higher per-row F1 than naive arm

### Hypothesis to be verified
H1 from protocol section 3.5.1.

### Placeholder for visualisation or data table
- report/inputs/generated/tab_exp2_outline_h1.tex

### Placeholder for test
- Mann-Whitney U, two-tailed
- Effect size: rank-biserial r
- CI placeholder block

### Placeholder for conclusion
- 1 paragraph: supported / not supported / inconclusive with effect size framing.

## 5) H2

### Section title
H2 - Agents differ on per-row F1 ranks within optimized arm

### Hypothesis to be verified
H2 from protocol section 3.5.1.

### Placeholder for visualisation or data table
- report/inputs/generated/fig_exp2_outline_h2.tex

### Placeholder for test
- Friedman test (k=4, n=5 blocks)
- Effect size: Kendall W or eta-squared
- Post-hoc gate placeholder (only if global test passes)

### Placeholder for conclusion
- 1 paragraph: rank-difference interpretation and practical significance.

## 6) H3

### Section title
H3 - Verify pass improves per-row provenance rate (turn-3 >= turn-2)

### Hypothesis to be verified
H3 from protocol section 3.5.1.

### Placeholder for visualisation or data table
- report/inputs/generated/tab_exp2_outline_h3.tex

### Placeholder for test
- Paired Wilcoxon signed-rank
- Effect size: matched-pair d
- Agent-wise sensitivity placeholder

### Placeholder for conclusion
- 1 paragraph: whether verify step adds measurable provenance benefit.

## 7) H4

### Section title
H4 - At least one naive-arm bounce rate exceeds 50%

### Hypothesis to be verified
H4 from protocol section 3.5.1.

### Placeholder for visualisation or data table
- report/inputs/generated/tab_exp2_outline_h4.tex

### Placeholder for test
- Wilson upper bound per agent (binomial, n=5)

### Placeholder for conclusion
- 1 paragraph: which agents cross or do not cross the threshold.

## 8) H5

### Section title
H5 - Wikipedia and mirror citations are absent (compliance)

### Hypothesis to be verified
H5 from protocol section 3.5.1.

### Placeholder for visualisation or data table
- report/inputs/generated/tab_exp2_outline_h5.tex

### Placeholder for test
- Wilson upper bound on Wikipedia citation proportion
- Compliance threshold placeholder

### Placeholder for conclusion
- 1 paragraph: compliance verdict and implications for trust claims.

## 9) H6

### Section title
H6 - Phase C cross-eval ranks agree with mechanical metric ranks

### Hypothesis to be verified
H6 from protocol section 3.5.1.

### Placeholder for visualisation or data table
- report/inputs/generated/fig_exp2_outline_h6.tex

### Placeholder for test
- Spearman rho across 4-agent rank vectors per dimension
- Divergence interpretation placeholder for |rho| < 0.3

### Placeholder for conclusion
- 1 paragraph: agreement / divergence and what it means for evaluation validity.

## 10) Synthesis and limits

### Section title
Synthesis, limits, and next action

### What goes here
- Consolidated status of H1-H6 (supported / not supported / pending).
- Hard limits: unresolved quality layers, pending artefacts, or blocked tests.
- Explicit next action list feeding follow-up tickets.

### Placeholder artefacts
- Table placeholder: report/inputs/generated/tab_exp2_outline_hypothesis_status.tex

### Placeholder test block
- None; this is synthesis only.

### Placeholder conclusion block
- 1 paragraph: safe claims now, claims deferred, and release checklist.
