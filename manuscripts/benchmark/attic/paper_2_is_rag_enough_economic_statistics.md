---
title: "Is Retrieval-Augmented Generation Enough to Produce Economic Statistics?"
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
  Retrieval-Augmented Generation (RAG) is often presented as a solution to the unreliability of large language models when producing factual information. This paper evaluates whether RAG is sufficient to generate economic statistics, using the same benchmark and case study as a companion paper: the inventory of thermal power plants in Vietnam. We compare direct LLM generation with several RAG configurations, measuring coverage, precision, and traceability. While RAG substantially improves performance, significant gaps remain. We show that document augmentation alone cannot ensure statistical completeness or consistency, and argue for hybrid architectures combining RAG with explicit data models, entity resolution, and accumulation over time.
---

## 1. Introduction

Economic statistics demand not only factual correctness but also completeness, stability over time, and explicit sourcing. While Retrieval-Augmented Generation (RAG) improves grounding by providing documents to LLMs, it remains unclear whether this is sufficient for statistical production. This paper addresses that question empirically.

Using the same benchmark as our companion paper, we isolate the effect of RAG on statistical performance and analyse its remaining limitations.

## 2. Background

RAG combines information retrieval with text generation by injecting relevant documents into the model context. It has shown strong results in knowledge-intensive tasks. However, RAG systems are typically optimised for answering questions, not for constructing exhaustive datasets.

## 3. Benchmark and Metrics

We reuse the benchmark introduced in the companion paper, including:

- the expert reference dataset,
- coverage and precision metrics,
- reconciliation-based error analysis.

This ensures comparability between LLM-only and RAG-based approaches.

## 4. RAG Configurations

We evaluate several RAG styles:

- **Curated RAG:** a small, manually selected set of authoritative documents.
- **Extended RAG:** curated documents plus open databases and encyclopaedic sources.
- **Multi-turn RAG:** iterative prompting with document context retained.

Retrieval is performed at document or table level, and generation is constrained to structured CSV outputs.

## 5. Experimental Protocol

For each configuration, we run the same prompts as in the LLM-only setting, adding retrieved documents to the context. Outputs are normalised and evaluated using the same pipeline. This design isolates the marginal contribution of RAG.

## 6. Results

RAG consistently improves coverage relative to direct generation, in some cases doubling the number of correctly identified plants. Precision generally improves as well, with fewer hallucinated entries. However, even the best configurations remain significantly incomplete relative to the reference.

Models frequently omit plants that are present in the provided documents, misinterpret tables, or conflate units and complexes. Source citation improves but is often superficial.

## 7. Error Analysis

Three persistent failure modes emerge:

1. **Enumeration failure:** models fail to systematically traverse tables.
2. **Entity resolution errors:** multiple names for the same plant are mishandled.
3. **Temporal inconsistency:** retired or cancelled projects are inconsistently treated.

These errors are not solved by retrieval alone.

## 8. Beyond RAG

Our results suggest that RAG is a necessary but insufficient component of a statistical system. Additional layers are required:

- explicit data models and ontologies,
- entity resolution and data fusion,
- provenance tracking at the row level,
- accumulation and revision over time.

These features lie outside the scope of standard RAG pipelines.

## 9. Conclusion

RAG significantly improves the ability of LLMs to generate economic statistics, but it does not close the gap to expert-level datasets. Economic statistics require systems that treat data as first-class objects rather than as text to be summarised. RAG should be seen as one component in a broader hybrid architecture, not as a complete solution.

