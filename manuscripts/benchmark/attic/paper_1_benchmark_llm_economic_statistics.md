---
title: "Benchmarking Large Language Models for the Generation of Economic Statistics"
author: "Minh Ha-Duong"
date: "2025-12-17"
format:
  pdf:
    documentclass: article
    papersize: a4
    fontsize: 11pt
    number-sections: true
    geometry: margin=2.5cm
abstract: |
  This paper introduces a reproducible benchmark to evaluate the ability of large language models (LLMs) to generate economic statistics. Using the concrete task of enumerating thermal power plants in Vietnam, we compare model outputs against an expert-compiled reference dataset. We define quantitative indicators capturing precision, coverage, and the ability to justify generated figures. The benchmark is implemented as open, executable code and applied to a range of model sizes, tuning styles, and prompting strategies. Results show that current LLMs systematically under-produce statistical tables and trade coverage against hallucination, even at large scale. The benchmark highlights structural limits of prompt-based approaches and provides a diagnostic tool for future AI-assisted statistical systems.
---

## 1. Introduction

Economic statistics require exhaustiveness, internal consistency, correct units, and traceability. These properties sharply contrast with the design objectives of conversational large language models (LLMs), which prioritise brevity and plausibility. Recent progress has raised expectations that LLMs could automate parts of statistical production, especially in data-scarce contexts. This paper evaluates that expectation empirically.

We propose a benchmark focused on a realistic and technically demanding task: producing a complete table of thermal power plants in Vietnam. An expert-made reference list exists, making it possible to quantify performance. Our contribution is methodological: we define a benchmark, metrics, and evaluation pipeline that can be reused for other economic domains.

## 2. Related Work

LLM evaluation has focused on question answering, reasoning, and factual recall. Benchmarks rarely address the generation of structured statistical tables against a gold standard. In economics, evaluation typically concerns forecasting or numerical reasoning rather than data compilation. Our work fills this gap by targeting statistical completeness and reliability.

## 3. Task Definition

The task is to generate a table listing all thermal power plants in Vietnam, with one plant per row. Required attributes include:

- Plant name (canonical)
- Fuel type (coal, local gas, imported LNG)
- Status (operational, retired, under construction, planned, cancelled)
- Connection date (realised or expected COD)
- Province
- Installed capacity (MWe)

The task involves ambiguity (plants vs units, projects vs realised assets) and domain-specific knowledge (fuel cycles, naming conventions).

## 4. Reference Dataset

The reference dataset was compiled manually by the author from official planning documents, utility reports, open databases, and long-term expert monitoring. It represents the best available open-source approximation of a national inventory. While not error-free, it provides a consistent benchmark against which model outputs can be compared.

## 5. Benchmark Design

### 5.1 Metrics

We define three core indicators:

- **Coverage (Recall):** share of reference plants identified by the model.
- **Precision:** share of model-generated plants that correspond to real entries.
- **Justification ability:** proportion of sampled rows for which the model can provide a plausible source reference.

Errors are further classified (hallucinated plants, wrong fuel, wrong status).

### 5.2 Formalisation

The benchmark is implemented in Python. Model outputs are normalised to a canonical schema and compared to the reference using exact and fuzzy matching on names and capacities. The pipeline produces reconciliation tables and summary statistics.

## 6. Experimental Setup

We test multiple families of models:

- Large proprietary models
- Open-weight models around 70B parameters
- Reasoning-oriented variants

Prompting strategies include single-shot queries, structured prompts, and multi-turn conversational elicitation. All outputs are requested in CSV format and processed identically.

## 7. Results

Single-shot prompts typically recover only 25–40% of the reference list. Larger and more recent models perform better but remain far from exhaustive. Multi-turn prompting increases coverage substantially, at the cost of more errors and longer responses. Precision decreases as coverage increases, revealing a structural trade-off.

## 8. Discussion

The results show that LLMs do not behave like statistical instruments. They possess partial knowledge but lack mechanisms to ensure completeness or systematic enumeration. Prompt engineering improves recall but cannot guarantee reliability. These limits are not model-specific but structural.

## 9. Conclusion

We introduce a benchmark for evaluating AI systems on the generation of economic statistics. Applied to thermal power plants in Vietnam, it reveals persistent limitations of current LLMs. The benchmark provides a foundation for evaluating more advanced architectures, including document-augmented and knowledge-based systems, which are explored in the companion paper.
