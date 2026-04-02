---
title: "Can AI Produce Economic Statistics? A Benchmark on Energy Infrastructure Inventories"
author: "Minh Ha-Duong"
date: "2026"
format:
  pdf:
    documentclass: article
    papersize: a4
    fontsize: 11pt
    number-sections: true
    geometry: margin=2.5cm
abstract: |
  Economic statistics demand exhaustiveness, internal consistency, explicit provenance, and the ability to be updated over time. These requirements sharply contrast with the design objectives of large language models and Retrieval-Augmented Generation systems. This paper introduces a reproducible benchmark to evaluate whether AI systems can produce economic statistics, using the concrete task of inventorying thermal power plants in Vietnam. We define quantitative metrics—coverage, precision, and justification ability—and apply them to a range of model families, prompting strategies, and RAG configurations. Results show that multi-turn prompting triples the coverage of single-shot queries, and RAG doubles it further, but even the best configurations remain significantly incomplete relative to an expert-compiled reference of ~135 plants. Three persistent failure modes—enumeration errors, entity resolution failures, and temporal inconsistency—are not resolved by retrieval alone. We argue that economic statistics require stateful architectures treating data as first-class objects rather than text to be summarised, and release the benchmark as an open evaluation framework.
keywords:
  - economic statistics
  - large language models
  - retrieval-augmented generation
  - benchmark
  - energy transition
  - Vietnam
---

# 1. Introduction

<!-- ~1.5 pages -->

Economic statistics are a core infrastructure for applied economics, policy analysis, and quantitative modelling. Unlike question answering or summarisation, statistical production requires exhaustiveness, internal consistency, temporal coherence, explicit provenance, and updatability.

This paper asks: **can current AI systems—LLMs and RAG pipelines—produce economic statistics?**

We answer empirically, using a demanding test case: inventorying all thermal power plants in Vietnam (~135 documented plants, coal/gas, all statuses from retired to cancelled). An expert-compiled reference dataset exists, enabling quantitative evaluation.

**Contributions:**

1. A reproducible benchmark for evaluating AI systems on the production of structured economic statistics, with metrics capturing exhaustiveness, precision, and traceability.
2. A systematic comparison of direct LLM generation, multi-turn prompting, and several RAG configurations—within a unified evaluation framework.
3. An error analysis identifying three structural failure modes that persist across all approaches, demonstrating that RAG is necessary but insufficient.
4. An open-source evaluation pipeline and reference dataset.

<!-- Distinguish from standard NLP benchmarks (QA, reasoning, factual recall) -->
<!-- Motivate the energy transition modelling angle: outdated data → invalid PyPSA scenarios -->
<!-- Cite Gotzens et al. 2019 on data quality in power plant databases -->

**Outline.** Section 2 reviews related work. Section 3 defines the task, reference dataset, and metrics. Section 4 describes the experimental setup. Section 5 presents results. Section 6 analyses errors. Section 7 discusses implications. Section 8 concludes.


# 2. Related Work

<!-- ~1 page -->

## 2.1 LLM Evaluation

<!-- Standard benchmarks (MMLU, HellaSwag, etc.) focus on QA, reasoning, factual recall -->
<!-- Gap: no benchmark targets the generation of structured statistical tables against a gold standard -->
<!-- Mention data extraction benchmarks (e.g., information extraction, table understanding) as adjacent but distinct -->

## 2.2 RAG for Knowledge-Intensive Tasks

<!-- Lewis et al. 2021: RAG improves factual grounding -->
<!-- RAG optimised for answering questions, not constructing exhaustive datasets -->
<!-- Recent progress: agentic RAG, deep research systems -->

## 2.3 AI for Economic and Energy Data

<!-- In economics, evaluation typically concerns forecasting or numerical reasoning, not data compilation -->
<!-- Energy data quality: Gotzens et al. 2019 -->
<!-- Global Energy Monitor, WRI, S&P Platts — existing databases and their limitations -->
<!-- No prior benchmark for AI-assisted statistical table production -->


# 3. Benchmark Design

<!-- ~2.5 pages -->

## 3.1 Task Definition

The task is to generate a structured table listing all thermal power plants in Vietnam. Required attributes per plant:

| Attribute | Description | Example |
|-----------|-------------|---------|
| `name` | Canonical plant name (local script) | Phả Lại 2 |
| `fuel` | coal / local gas / imported LNG | coal |
| `status` | operational / retired / constructing / planned / proposed / cancelled | operational |
| `cod` | Connection date (realised or expected) | 2001 |
| `province` | Vietnamese province | Hải Dương |
| `capacity_mwe` | Installed capacity in MWe | 600 |

**Ambiguities inherent to the task:**

- Plant vs. unit vs. complex (e.g., Phú Mỹ 1–4: one complex, six plants, multiple units)
- Project vs. realised asset (e.g., Phú Mỹ 3.1 proposed in draft PDP8 but not retained)
- Naming conventions (diacritics, transliteration variants, abbreviations)
- Temporal evolution of status (planned → constructing → operational; or planned → cancelled)

## 3.2 Reference Dataset

<!-- Expert-compiled from official planning documents (PDP7, PDP7A, PDP8), utility reports (EVN annual reports), open databases (Wikipedia, GEM), and long-term expert monitoring -->
<!-- ~135 plants, 6 attributes -->
<!-- Not error-free but consistent; represents the best available open-source approximation -->
<!-- Versioned; available as CSV in the benchmark repository -->
<!-- Discuss limitations: some small captive plants may be missing; operational dates approximate -->

## 3.3 Metrics

**Coverage (Recall):** Share of reference plants correctly identified by the system.

$$\text{Coverage} = \frac{|\text{Reference} \cap \text{System}|}{|\text{Reference}|}$$

**Precision:** Share of system-generated plants that correspond to real entries.

$$\text{Precision} = \frac{|\text{Reference} \cap \text{System}|}{|\text{System}|}$$

**Justification Rate:** Proportion of sampled rows for which the system provides a verifiable source reference.

**Error Taxonomy:**

- Hallucinated plant (no corresponding reference entry)
- Wrong fuel type
- Wrong status
- Duplicate (same plant listed multiple times under different names)
- Wrong capacity (>20% deviation)
- Missing plant (in reference but not in system output)

## 3.4 Matching Pipeline

<!-- Normalisation: Unicode, diacritics, common abbreviations -->
<!-- Exact match on canonical name -->
<!-- Fuzzy match (rapidfuzz, threshold to specify) -->
<!-- Capacity tolerance (±X%) for disambiguation -->
<!-- Rules for plant-vs-unit disambiguation -->
<!-- Output: reconciliation table with match type per entry -->
<!-- Implemented in Python; reproducible; open-source -->


# 4. Experimental Setup

<!-- ~2 pages -->

## 4.1 Systems Under Evaluation

### 4.1.1 Direct LLM Generation (Prompt 1)

<!-- Single-shot CSV generation -->
<!-- Models: Claude 3.5 Sonnet, GPT-4o, DeepSeek-R1, Llama 3.3 70B, Qwen 2.5 72B, o3-mini, Perplexity Pro -->
<!-- Same standardised prompt across all models -->

### 4.1.2 Multi-Turn Prompting (Prompt 2 + Relances)

<!-- Structured prompt with expert role, schema, sorting, sourcing instructions -->
<!-- Three successive "try harder" follow-ups -->
<!-- Tests on: Claude 3.5 Sonnet, DeepSeek-R1, GPT-4o, Llama 3.3 70B, Qwen 2.5 72B, o3-mini -->

### 4.1.3 RAG Configurations

<!-- Curated RAG: 15 manually selected authoritative documents (PDP7/7A/8, EVN reports, GEM) -->
<!-- Total: 138.6 kB Markdown, ~63.5k tokens + 3.5k tokens bibliographic references -->
<!-- Extended RAG: curated + EVN annual reports 2010-2018 -->
<!-- Multi-turn RAG: RAG + iterative follow-ups -->
<!-- Models: Claude 3.5 Sonnet, DeepSeek-R1, GPT-4o, o3-mini (medium and high) -->

## 4.2 Evaluation Protocol

<!-- All outputs requested in CSV format -->
<!-- Normalised through the same pipeline -->
<!-- Each configuration run once (feasibility study; discuss variance) -->
<!-- Temperature not controlled (discuss as limitation) -->


# 5. Results

<!-- ~2 pages -->

## 5.1 Direct Generation

<!-- TABLE: Model | Prompt 1 (single-shot) | After 4 multi-turn relances -->
<!-- Key finding: single-shot = 25-40% coverage; multi-turn = up to 65-80% -->
<!-- Models reveal only ~1/3 of their knowledge on first response -->
<!-- Correlation between model recency and coverage -->
<!-- Reasoning models (o3-mini) do NOT perform better; may perform worse due to token allocation -->

## 5.2 Effect of RAG

<!-- TABLE: Model | Without documents | With documents -->
<!-- Key finding: RAG improves coverage (e.g., Claude: 63→101 with extended RAG + relance) -->
<!-- RAG and multi-turn are complementary -->
<!-- Best config: RAG + relance on reasoning model (o3-mini high: 78; DeepSeek-R1: 65) -->

## 5.3 Reconciliation Analysis

<!-- TABLE: Configuration | Exact matches | Approximate | Incorrect | Missing -->
<!-- From Table 5.2 in report -->
<!-- Claude baseline: 25 exact, 135 missing -->
<!-- Claude + RAG + relance: 61 exact, 12 approx, 9 incorrect, 72 missing -->
<!-- Even best config misses ~45% of reference -->

## 5.4 Coverage–Precision Trade-off

<!-- As coverage increases, precision decreases -->
<!-- Multi-turn pushes models to generate more, including more errors -->
<!-- Structural trade-off, not model-specific -->


# 6. Error Analysis

<!-- ~1.5 pages -->

## 6.1 Enumeration Failure

<!-- Models fail to systematically traverse tables provided in context -->
<!-- They summarise rather than enumerate -->
<!-- Even with explicit instructions, omit plants present in provided documents -->
<!-- Output length limits compound the problem (4K-8K token responses for a task requiring ~28K tokens) -->

## 6.2 Entity Resolution Errors

<!-- Multiple names for the same plant (Phú Mỹ complex example) -->
<!-- Transliteration variants not handled -->
<!-- Plants vs. units vs. complexes conflated -->
<!-- Double-counting or under-counting -->

## 6.3 Temporal Inconsistency

<!-- Retired plants inconsistently included/excluded -->
<!-- Cancelled projects from draft plans treated as active -->
<!-- No mechanism to track status evolution over time -->
<!-- COD dates from different planning documents contradictory and unreconciled -->

## 6.4 Additional Failure Modes

<!-- Confusion between capacity and production (kW vs kWh) -->
<!-- Hydroelectric plants listed as thermal (misunderstanding TĐ abbreviation) -->
<!-- Sourcing: either absent, self-referential ("from provided docs"), or hallucinated -->


# 7. Discussion

<!-- ~1.5 pages -->

## 7.1 RAG is Necessary but Insufficient

<!-- RAG addresses knowledge recency and traceability -->
<!-- But does not solve enumeration, entity resolution, or temporal consistency -->
<!-- RAG optimised for QA, not for dataset construction -->
<!-- The gap between "can find information" and "can produce statistics" is structural -->

## 7.2 What Economic Statistics Require

<!-- Statefulness: accumulate knowledge over time, not regenerate from scratch -->
<!-- Entity resolution and data fusion as explicit pipeline stages -->
<!-- Provenance tracking at the row/cell level, not just document-level citation -->
<!-- Ontological alignment (Open Energy Ontology) for consistency -->
<!-- Human-in-the-loop validation before data enters the knowledge base -->

## 7.3 Implications for AI-Assisted Statistical Systems

<!-- The benchmark reveals that current AI systems do not behave as statistical instruments -->
<!-- Prompt engineering cannot overcome structural limits -->
<!-- Need hybrid architectures: LLM for extraction and drafting, structured pipelines for accumulation and validation -->
<!-- Pointer to agentic architectures (Ha-Duong, 2026 Econom'IA paper; AIRLET project) -->

## 7.4 Limitations of This Study

<!-- Single domain (thermal power plants, Vietnam) — generalisability to be tested -->
<!-- No repeated runs / variance analysis (feasibility study) -->
<!-- Temperature not controlled -->
<!-- Reference dataset itself not error-free -->
<!-- Models tested in Jan-Feb 2025; rapid progress since then -->
<!-- Cost and latency not analysed -->


# 8. Conclusion

<!-- ~0.5 page -->

We introduced a benchmark for evaluating AI systems on the production of economic statistics. Applied to the inventory of thermal power plants in Vietnam, it reveals:

1. LLMs possess substantial latent knowledge but release only a fraction in single-shot queries.
2. Multi-turn prompting and RAG are complementary and both improve coverage substantially.
3. Even the best configurations remain ~45% incomplete relative to an expert reference.
4. Three structural failure modes—enumeration errors, entity resolution failures, and temporal inconsistency—persist across all approaches.

These results demonstrate that **RAG is a necessary but insufficient component** of a statistical system. Economic statistics require architectures that treat data as first-class objects subject to accumulation, revision, and provenance tracking.

The benchmark is released as open-source code and data to support the evaluation of future AI-assisted statistical systems, including agentic and knowledge-graph-based approaches.

<!-- Code and data: https://github.com/[repo] -->


# References

<!-- Key references to include: -->
<!-- Lewis et al. 2021 — RAG -->
<!-- Gotzens et al. 2019 — Data quality in power plant databases -->
<!-- Ha-Duong 2025 — AEDIST technical report (HAL preprint) -->
<!-- Ha-Duong 2026 — Econom'IA paper (Beyond RAG) -->
<!-- Ha-Duong 2022 — Wind power dataset Vietnam -->
<!-- Ha-Duong 2019 — Coal power dataset Vietnam -->
<!-- Booshehri et al. 2021 — Open Energy Ontology -->
<!-- GEM 2024 — Global Energy Monitor -->
<!-- Carlini et al. 2021 — Extracting training data -->
<!-- Khattab et al. 2023 — DSPy -->
