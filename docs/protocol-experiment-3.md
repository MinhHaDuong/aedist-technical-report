---
title: Protocol for Experiment 3
date: 2026-05-23
status: DRAFT
---

# Protocol for Experiment 3

## Research question

Can a fixed, prompt-side evidence pack improve the four-subject Vietnam thermal inventory task when it is added to the two existing baseline protocol surfaces?

## Scientific aim

Experiment 3 is a method experiment. It asks whether the evidence-pack intervention changes output quality in a way that is detectable on the same four-subject frame used elsewhere in the project.

The object of study is the intervention, not the model ladder and not weak-model rescue. The four subject systems are held constant so the protocol can compare arms cleanly.

## Design summary

This is a 4-arm factorial comparison on the four subject systems already used in the benchmark.

- Arm 1: baseline protocol surface A, no evidence pack
- Arm 2: baseline protocol surface B, no evidence pack
- Arm 3: baseline protocol surface A, with evidence pack
- Arm 4: baseline protocol surface B, with evidence pack

Baseline protocol surface A is the single deep research prompt.
Baseline protocol surface B is the multiturn design: plan, execute, verify, with web search.

Arm 1 is a frozen historical baseline reused from the archived `experiments/outputs/sota_exp2_naive_arm/` result set. Arm 2 is a frozen historical baseline reused from the archived `experiments/outputs/sota_exp2_brerun1/` result set. This experiment only runs Arms 3 and 4 and compares them to those archived controls.

The evidence pack is assembled application-side from [experiments/evidence_packs/all18tables.yaml](/home/haduong/aedist-technical-report/experiments/evidence_packs/all18tables.yaml) and the canonical corpus under [data/rag_corpus](/home/haduong/aedist-technical-report/data/rag_corpus).

The study compares Arm 3 vs Arm 1 and Arm 4 vs Arm 2. Arms 1 and 2 are the baselines; arms 3 and 4 are the intervention conditions.

## Hypotheses

### H1 — Evidence pack improves baseline surface A

On the first baseline protocol surface, Arm 3 yields higher row-level F1 than Arm 1.

- Supported: paired mean $\Delta F1 \ge 0.05$ and one-sided paired permutation test $p < 0.05$
- Falsified: paired mean $\Delta F1 \le 0$
- Inconclusive: positive improvement below $0.05$, or $p \ge 0.05$

### H2 — Evidence pack improves baseline surface B

On the second baseline protocol surface, Arm 4 yields higher row-level F1 than Arm 2.

- Supported: paired mean $\Delta F1 \ge 0.05$ and one-sided paired permutation test $p < 0.05$
- Falsified: paired mean $\Delta F1 \le 0$
- Inconclusive: positive improvement below $0.05$, or $p \ge 0.05$

### H3 — Evidence-pack outputs remain auditable

For the evidence-pack arms, the model must cite the pack in a way that can be checked against the underlying source text.

- Supported: citation-validity rate $\ge 0.80$ and source-id citation coverage $\ge 0.90$ on non-empty rows
- Falsified: citation-validity rate $< 0.50$
- Inconclusive: intermediate values

The intervention is scientifically useful only if H1, H2, and H3 are all supported.

## Subject panel

The confirmatory panel contains the same four subject systems throughout the run.

Panel rule:

- four subjects only
- selected before dispatch
- frozen before the first confirmatory run
- no substitution after dispatch begins

If the four-subject panel changes, the protocol must be rewritten before any further confirmatory analysis.

## Repetition plan

- default `repeat = 5` per subject per arm
- do not reduce repetitions for a specific subject once the panel is frozen
- if a subject is known to exhibit MoE-style variance, retain the same repeat count

## Task and output contract

The task is the AEDIST thermal inventory task: identify thermal power plants in Vietnam across lifecycle statuses and emit a structured inventory.

The output contract is unchanged except for provenance handling in the evidence-pack arms.

Required properties:

- one inventory row per plant
- the usual evaluator-facing plant fields
- at least one `source_id` citation for each non-empty row in Arms 3 and 4
- explicit uncertainty or omission when the evidence pack does not support a claim

## Evidence-pack construction

The evidence pack is not a new corpus. It is a deterministic rendering of the existing 18 markdown extracts in `data/rag_corpus` with metadata drawn from the manifest.

Assembly rules:

- preserve manifest order
- include the same header fields for every source
- keep source bodies verbatim
- attach the manifest `source_id` to each source block
- do not depend on vendor file-upload or hosted retrieval features

The pack must be rendered identically for all four subjects.

## Outcomes

### Primary outcome

- row-level F1 against the fixed reference inventory

### Secondary outcomes

- citation-validity rate
- source-id citation coverage
- empty-row or refusal rate
- truncation rate

### Descriptive outcomes

- fuel accuracy
- status accuracy
- province accuracy
- cross-tab coherence checks if aggregate tables are present

The descriptive outcomes are not confirmatory endpoints.

## Analysis plan

### H1 test

For each subject system:

1. Compute the mean F1 over repeated runs in Arm 1.
2. Compute the mean F1 over repeated runs in Arm 3.
3. Compute the paired difference $\Delta F1 = F1_{A3} - F1_{A1}$.

Test the paired mean difference with a one-sided paired permutation test.

### H2 test

For each subject system:

1. Compute the mean F1 over repeated runs in Arm 2.
2. Compute the mean F1 over repeated runs in Arm 4.
3. Compute the paired difference $\Delta F1 = F1_{A4} - F1_{A2}$.

Test the paired mean difference with a one-sided paired permutation test.

### H3 audit

For each evidence-pack output in Arms 3 and 4:

1. Extract every `source_id` reference.
2. Resolve each `source_id` to the manifest item.
3. Check whether the cited source text supports the row-level claim.

Report citation-validity rate and source-id citation coverage per subject and pooled across the four subjects.

## Exclusion and failure rules

- Harness crash before any model output: rerun the slot.
- API timeout after partial output: keep the artifact and score what is present.
- Empty response or refusal with no inventory substance: count as a failed run; F1 = 0 by convention.
- Malformed citation syntax: the row can still count for F1, but the citation fails H3.

No subject is dropped post hoc for poor performance.

## Validity boundaries

Experiment 3 does not test hosted retrieval.
Experiment 3 does not test vendor-native file attachments.
Experiment 3 does not compare the four subjects to each other as the scientific endpoint.
Experiment 3 does not prove that the 18-file pack is optimal.

The claim is narrower: one fixed, curated pack should improve the four-subject benchmark under the tested conditions.

If the full pack does not fit within a subject's usable context window, that subject is not eligible for the confirmatory panel. Any truncated-pack variant is a new experiment.

## Interpretation grid

| Outcome | Interpretation |
|---|---|
| H1 supported, H2 supported, H3 supported | The intervention improves both protocol surfaces and remains auditable. |
| H1 supported, H2 supported, H3 not supported | The pack improves recall but fails the provenance bar. |
| H1 not supported, H2 not supported | The pack does not move either baseline surface under the tested conditions. |

## Relation to the roadmap

This protocol deliberately replaces the earlier local-vs-cloud reading of Experiment 3.

If this draft is adopted, the roadmap should be updated so that Experiment 3 names the four-arm evidence-pack study and any local-vs-cloud comparison moves to a separate experiment.

## Preregistration state

Not yet preregistered.

Before confirmatory dispatch, freeze:

- four-subject panel membership
- exact prompt text
- exact response schema
- citation-audit rubric
- commit SHA containing this protocol and the manifest

## Implementation consequence

The runtime only needs to load the manifest, render the evidence pack deterministically, and append it to the prompt in Arms 3 and 4.
