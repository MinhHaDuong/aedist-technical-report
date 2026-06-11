---
title: Four-dimensional quality bar — accuracy, coherence, provenance, temporality
author: Claude prompted by Ha-Duong Minh
date: 2026-05-21
paper: slides/manuscript/main.tex
section: §2 Quality bar (lines 25–37)
citation-budget: 12–15
---

## Relevance

The manuscript proposes a four-dimensional quality framework — accuracy / coherence / provenance / temporality — and argues that any acceptable inventory must clear all four. This is the load-bearing methodological claim of the paper: it sets the bar against which §1 fails, §4 falls short, and §5 succeeds. Referees will press hardest here. The note must therefore (a) anchor each dimension to canonical literature, (b) name the philosophy-of-science framing (van Fraassen on empirical adequacy, Popper on falsifiability) without inflating it, (c) link to the operational data-quality tradition (Wang & Strong, IMF DQAF, ISO 8000), and (d) connect to recent LLM-evaluation work on each dimension (TruthfulQA, RAGAS, ALCE for citation accuracy, temporal-QA literature).

## History of science context

The four dimensions descend from three different traditions.

**Accuracy** is the oldest claim — the correspondence theory of truth in philosophy, operationalised in statistics as precision / recall / F1 (Salton's IR tradition, then ML evaluation). For LLMs, accuracy is the central topic of the benchmarking programme (MMLU, TableBench, TruthfulQA). The structured-extraction subfield specifies row-level and cell-level accuracy separately (LLMStructBench, Wu TableBench, Hofmann powerplantmatching's reconciliation metrics).

**Coherence** has two lineages: the philosophy of science programme on internal consistency of theories (van Fraassen 1980 empirical adequacy; Kuhn 1962 on paradigm-internal coherence) and the database-tradition control totals (Wang & Strong 1996 listed "consistency" among 15 dimensions; IMF DQAF lists "coherence" as a top-level cell). Our framework restricts the LLM-specific meaning to weak/internal consistency à la Wang et al. (2022) self-consistency decoding, distinguishing it from the structural-table coherence of `quality-grounding.md`.

**Provenance** is more recent for LLMs but old for science: every statistical claim should trace to a primary source. The UN Fundamental Principles (2014) make this an explicit duty. For LLMs, the operational literature is Gao et al. 2023 ALCE (Automatic LLM Citation Evaluation), Asai et al. 2024 Self-RAG, RAGAS (Es et al. 2023), and RAGTruth (Niu et al. 2023). Citation accuracy in the deep-research age has become a sub-benchmark of its own.

**Temporality** is the dimension least developed in the LLM literature and most explored in the database literature. Wang & Strong 1996 listed "currency"; ISO 8000 specifies temporal-validity metadata; the temporal-QA literature (Chen et al. TimeQA, Liska et al. StreamingQA) handles question-answering with time-stamped facts but does not extend to extraction with as-of dating per cell. The paragraph's claim that "temporality is part of the statistical fact" is closer to the database tradition than to current LLM eval practice.

The opposing view is that LLM outputs need only be useful, not auditable — the implicit position of every consumer-facing chatbot product. The manuscript explicitly takes the opposite position: for *statistical work*, the four-dimensional bar is non-negotiable. The framework's strength is that each dimension maps to a quantitative metric in `quality-grounding.md`, making "are we there yet?" measurable.

## Cited works — detailed

### Asai et al. 2024 — Self-RAG
- **Reference.** Asai, A.; Wu, Z.; Wang, Y.; Sil, A.; Hajishirzi, H. *Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection*. ICLR 2024. arXiv:2310.11511. (Existing key `Asai-Akari2024:self-rag`.)
- **What the work did.** Trained LLMs with "reflection tokens" to adaptively retrieve passages and self-evaluate outputs; improves both factuality and citation accuracy in long-form generation.
- **Why this paragraph cites it.** Recent frontier anchor for the **Provenance** dimension. The "citation accuracy" sub-result is precisely the strong-provenance requirement ("the cited source must actually support the value claimed").
- **Limitations or critiques.** Long-form QA, not structured extraction; their citation-accuracy gain is dataset-specific. Provides the metric definition but not directly the inventory-task instantiation.

### Es et al. 2023 — RAGAS
- **Reference.** Es, S.; James, J.; Espinosa-Anke, L.; Schockaert, S. *Ragas: Automated Evaluation of Retrieval Augmented Generation*. arXiv:2309.15217, 2023.
- **What the work did.** Reference-free evaluation framework for RAG pipelines: retrieval-relevance, faithfulness, answer-relevance metrics.
- **Why this paragraph cites it.** The reference-free evaluation paradigm is what our four-dimensional bar will need at scale; RAGAS is the closest peer for **Provenance** + **Accuracy** measurement on retrieval pipelines. Used as proof that the field treats these dimensions separately and operationally.
- **Limitations or critiques.** RAG-specific; assumes a retrieval context. Does not address temporal validity or table-coherence directly.

### Gao et al. 2023 — ALCE
- **Reference.** Gao, T.; Yen, H.; Yu, J.; Chen, D. *Enabling Large Language Models to Generate Text with Citations*. EMNLP 2023. arXiv:2305.14627.
- **What the work did.** Introduced ALCE, "the first benchmark for Automatic LLMs' Citation Evaluation"; measures fluency / correctness / citation quality jointly.
- **Why this paragraph cites it.** Operationalises the **strong-provenance** claim — moves from "model offered a citation" to "the cited source actually supports the value." This is the field's clearest instantiation of the manuscript's distinction between weak and strong provenance.
- **Limitations or critiques.** Long-form QA, ASQA/QAMPARI/ELI5 datasets; not structured-extraction-shaped. Per-cell provenance still ahead.

### Hendrycks et al. 2021 — MMLU
- **Reference.** Hendrycks, D.; Burns, C. et al. *Measuring Massive Multitask Language Understanding*. ICLR 2021. (Existing key `Hendrycks-Dan2021:mmlu`.)
- **What the work did.** Field-defining LLM **Accuracy** benchmark across 57 subjects.
- **Why this paragraph cites it.** Field-defining anchor for accuracy-as-eval-target in the LLM era. Establishes that accuracy is the dimension with the most measurement infrastructure.
- **Limitations or critiques.** Closed-set MCQA; does not stress structured extraction or open-world enumeration.

### IMF 2003 — Data Quality Assessment Framework
- **Reference.** International Monetary Fund. *Data Quality Assessment Framework*. IMF, 2003. https://dsbb.imf.org/dqrs/DQAF
- **What the work did.** Five quality dimensions (prerequisites, assurances of integrity, methodological soundness, accuracy & reliability, serviceability, accessibility) with prerequisites and sub-dimensions including coherence and timeliness.
- **Why this paragraph cites it.** Authority anchor for the four-dimensional decomposition — particularly **Coherence** (DQAF dimension 2.3) and the timeliness/currency distinction the paragraph operationalises as **Temporality**.
- **Limitations or critiques.** Designed for macroeconomic statistics, not microeconomic asset inventories; the operational vocabulary needs translation. The DQAF URL is gated behind redirects but the framework is stable institutional reference.

### Lin et al. 2021 — TruthfulQA
- **Reference.** Lin, S.; Hilton, J.; Evans, O. *TruthfulQA: Measuring How Models Mimic Human Falsehoods*. ACL 2022. arXiv:2109.07958.
- **What the work did.** 817-question benchmark; truthfulness does not scale monotonically.
- **Why this paragraph cites it.** Recent frontier anchor for the **Accuracy** dimension in its strict form (truth as opposed to plausibility). Justifies why accuracy alone is not sufficient — model outputs can be confident and wrong.
- **Limitations or critiques.** Adversarial; the inverse-scaling effect is sometimes treated as artifact rather than result.

### UN 2014 — Fundamental Principles of Official Statistics
- **Reference.** UN General Assembly Resolution A/RES/68/261, 2014. https://unstats.un.org/unsd/dnss/gp/fundprinciples.aspx
- **What the work did.** 10 principles including impartiality, methodological transparency, source-citing, statistical confidentiality.
- **Why this paragraph cites it.** Authority anchor for the meta-claim that provenance and temporality are requirements, not options. The "sources must be cited" principle is the **Provenance** dimension at top-tier authority.
- **Limitations or critiques.** Aspirational; no operational metrics. The manuscript bridges aspirational principles to measurable quantities.

### van Fraassen 1980 — The Scientific Image
- **Reference.** van Fraassen, B.C. *The Scientific Image*. Oxford University Press, 1980. ISBN 0-19-824427-4.
- **What the work did.** Introduced constructive empiricism — a theory is *empirically adequate* iff everything it says about observables is true.
- **Why this paragraph cites it.** Philosophy-of-science anchor for the **Coherence** + **Accuracy** pair. Empirical adequacy is the project's epistemological standard; the four dimensions decompose what would have to be true for a dataset to be empirically adequate to the energy-asset domain.
- **Limitations or critiques.** Constructive empiricism is one position among many; we adopt it without engaging anti-realist debates that are not on the critical path.

### Wang & Strong 1996 — Beyond Accuracy
- **Reference.** Wang, R.Y.; Strong, D.M. *Beyond Accuracy: What Data Quality Means to Data Consumers*. JMIS 12(4):5–33, 1996.
- **What the work did.** Empirical taxonomy of 15 data-quality dimensions including accuracy, currency, completeness, consistency, believability.
- **Why this paragraph cites it.** Field-defining historical anchor — the four-dimensional decomposition is a deliberate compression of Wang & Strong's 15 (and DAMA-DMBOK's adaptation thereof) into the cells most binding for LLM-driven extraction.
- **Limitations or critiques.** Pre-LLM; pre-internet. Successor frameworks (DQAF, ISO 8000) inherit but operationalise differently.

### Wang et al. 2022 — Self-consistency
- **Reference.** Wang, X.; Wei, J.; Schuurmans, D. et al. *Self-Consistency Improves Chain of Thought Reasoning in Language Models*. arXiv:2203.11171, 2022. (Existing key `Wang2022:self-consistency`.)
- **What the work did.** Sample multiple chain-of-thought traces and majority-vote; reduces inconsistency.
- **Why this paragraph cites it.** Anchors the *weak/internal* sense of the **Coherence** dimension — sampling-level self-consistency, as distinct from structural-table coherence. Directly cited in `docs/framework-grounding-map.md` for this purpose.
- **Limitations or critiques.** Reasoning, not extraction; voting reduces variance but does not guarantee provenance.

### Wu et al. 2025 — TableBench
- **Reference.** Wu, X.; Yang, J. et al. *TableBench*. AAAI 2025. (Existing key `Wu-Xianjie2025:tablebench`.)
- **What the work did.** Comprehensive benchmark for table QA across 18 task categories with cell-level scoring.
- **Why this paragraph cites it.** Anchors the **Accuracy** dimension at the row/cell granularity our task requires. Most recent peer to our evaluation scheme.
- **Limitations or critiques.** Table-QA, not table-generation; does not measure provenance or temporality.

### Tenckhoff et al. 2026 — LLMStructBench
- **Reference.** Tenckhoff, S.; Koddenbrock, M.; Rodner, E. *LLMStructBench*. arXiv:2602.14743, 2026. (Existing key `Tenckhoff-Sonke2026:llmstructbench`.)
- **What the work did.** Benchmark for structured-data extraction from text by LLMs.
- **Why this paragraph cites it.** Most recent frontier work on the accuracy/coherence pair for structured outputs.
- **Limitations or critiques.** Inputs are documents; ours is mixed.

## Related but not cited — justified

### Popper 1959 — The Logic of Scientific Discovery
The deepest historical anchor for falsifiability. We delegate to §3 (capability ladder) where the falsifiability ↔ citation argument is made directly. In §2 the operational instantiation (Wang & Strong + IMF DQAF + ALCE) carries more measurement weight than the philosophical foundation.

### Kuhn 1962 — Structure of Scientific Revolutions
The classical pair to van Fraassen on paradigm-internal coherence. Cited in `docs/quality-grounding.md`; redundant here once van Fraassen anchors the philosophy line.

### Niu et al. 2023 — RAGTruth
arXiv:2401.00396. RAGTruth is the hallucination-detection benchmark for RAG. Strong for the **Provenance** dimension but RAGAS + ALCE + Self-RAG already cover the territory at the budget cap. Recorded for the aggregator.

### Maharana et al. 2024 — LoCoMo (long-term conversational memory)
arXiv:2402.17753. Long-conversation memory benchmark. Out of scope here — relevant to §5 (stateful systems) rather than the quality bar.

### Yu et al. 2024 — Chain-of-Note
arXiv:2311.09210. Retrieval-robustness method. Operational, not a measurement framework. Out of scope for §2.

### Sharma et al. 2023 — Sycophancy
arXiv:2310.13548. Trained-in agreement compromises truthfulness (anti-accuracy). Adjacent but the manuscript does not engage sycophancy directly. Recorded for completeness.

## Methods

- **Search seeds.** The four named dimensions; the manuscript paragraph itself; `docs/quality-grounding.md` (which already lists van Fraassen, Popper, Wang & Strong, IMF DQAF, UN principles); the task brief's anchor list.
- **Databases.** arXiv, DOI resolver, JOSS, ACL Anthology (via arXiv), Wikipedia (for van Fraassen citation form), IMF / UN institutional sites.
- **Stop condition.** 12 entries cited + 6 in related-but-not-cited. Budget filled by one anchor per dimension at field-defining tier + one recent frontier tier per dimension; all four covered.
- **Inclusion rule.** Anchor must (a) define a specific dimension or its operational metric, or (b) be the canonical authority for a top-level claim about what statistics requires.
- **Exclusion rule.** Tangential measurement papers that do not name one of the four dimensions.
- **Freshness cutoff.** 2026-05-21.
- **Preprint policy.** TruthfulQA cited with ACL venue + arXiv ID; RAGAS via arXiv (no venue yet); ALCE via EMNLP + arXiv.
- **Grey-literature policy.** UN resolution and IMF framework are institutional grey literature, unavoidable given the topic.
- **Identifier resolution log.** WebFetched and resolved: 2305.14627 (Gao ALCE ✓); 2309.15217 (RAGAS ✓); 2310.11511 (Self-RAG ✓); IMF DQAF URL 403 — kept the URL with `note` field because the resource is institutional and stable; van Fraassen 1980 has no DOI but is canonically citable by ISBN; existing keys re-used from refs.bib without re-resolution.
- **LLM-assist disclosure.** Drafted by Claude (Opus 4.7) under ticket 0151. WebFetch used for identifier resolution.

## Author verification checklist

- [ ] Read each cited primary source (not just abstract)
- [ ] Confirmed claim-to-citation mapping
- [ ] Checked preprints for peer-reviewed updates
- [ ] Agreed with "related but not cited" justifications
- [ ] No in-repo docs cited in place of primary sources

## Bibliography

```bibtex
@inproceedings{Asai-Akari2024:self-rag,
  author       = {Asai, Akari and Wu, Zeqiu and Wang, Yizhong and Sil, Avirup
                  and Hajishirzi, Hannaneh},
  title        = {{Self-RAG: Learning to Retrieve, Generate, and Critique through
                  Self-Reflection}},
  booktitle    = {Proceedings of the Twelfth International Conference on Learning
                  Representations},
  date         = {2024},
  url          = {https://openreview.net/forum?id=hSyW5go0v8},
  doi          = {10.48550/arXiv.2310.11511},
  eprint       = {2310.11511},
  eprinttype   = {arxiv},
}

@misc{Es-Shahul2023:ragas,
  author       = {Es, Shahul and James, Jithin and Espinosa-Anke, Luis
                  and Schockaert, Steven},
  title        = {{Ragas: Automated Evaluation of Retrieval Augmented Generation}},
  date         = {2023-09},
  eprint       = {2309.15217},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.2309.15217},
}

@inproceedings{Gao-Tianyu2023:alce,
  author       = {Gao, Tianyu and Yen, Howard and Yu, Jiatong and Chen, Danqi},
  title        = {{Enabling Large Language Models to Generate Text with Citations}},
  booktitle    = {Proceedings of the 2023 Conference on Empirical Methods in
                  Natural Language Processing},
  date         = {2023},
  eprint       = {2305.14627},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.2305.14627},
}

@article{Hendrycks-Dan2021:mmlu,
  author       = {Hendrycks, Dan and Burns, Collin and Basart, Steven and Zou, Andy
                  and Mazeika, Mantas and Song, Dawn and Steinhardt, Jacob},
  title        = {{Measuring Massive Multitask Language Understanding}},
  journaltitle = {Proceedings of the International Conference on Learning Representations},
  date         = {2021},
  doi          = {10.48550/arXiv.2009.03300},
  eprint       = {2009.03300},
  eprinttype   = {arxiv},
}

@misc{IMF2003:dqaf,
  author       = {{International Monetary Fund}},
  title        = {{Data Quality Assessment Framework}},
  date         = {2003},
  url          = {https://dsbb.imf.org/dqrs/DQAF},
  note         = {Five quality dimensions; institutional standard},
}

@inproceedings{Lin-Stephanie2022:truthfulqa,
  author       = {Lin, Stephanie and Hilton, Jacob and Evans, Owain},
  title        = {{TruthfulQA: Measuring How Models Mimic Human Falsehoods}},
  booktitle    = {Proceedings of the 60th Annual Meeting of the Association for
                  Computational Linguistics (Volume 1: Long Papers)},
  date         = {2022},
  eprint       = {2109.07958},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.2109.07958},
}

@article{Tenckhoff-Sonke2026:llmstructbench,
  author       = {Tenckhoff, S{\"o}nke and Koddenbrock, Mario and Rodner, Erik},
  title        = {{LLMStructBench: Benchmarking Large Language Model Structured Data Extraction}},
  journaltitle = {arXiv preprint},
  date         = {2026},
  doi          = {10.48550/arXiv.2602.14743},
  eprint       = {2602.14743},
  eprinttype   = {arxiv},
}

@misc{UN2014:fundamental-principles,
  author       = {{United Nations General Assembly}},
  title        = {{Fundamental Principles of Official Statistics}},
  date         = {2014-01},
  url          = {https://unstats.un.org/unsd/dnss/gp/fundprinciples.aspx},
  note         = {Resolution A/RES/68/261},
}

@book{vanFraassen1980:scientific-image,
  author       = {van Fraassen, Bas C.},
  title        = {{The Scientific Image}},
  publisher    = {Oxford University Press},
  date         = {1980},
  isbn         = {0-19-824427-4},
}

@misc{Wang2022:self-consistency,
  author       = {Wang, Xuezhi and Wei, Jason and Schuurmans, Dale and Le, Quoc
                  and Chi, Ed and Narang, Sharan and Chowdhery, Aakanksha and Zhou, Denny},
  title        = {{Self-Consistency Improves Chain of Thought Reasoning in Language Models}},
  date         = {2022},
  eprint       = {2203.11171},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.2203.11171},
}

@article{Wang-Richard1996:beyond-accuracy,
  author       = {Wang, Richard Y. and Strong, Diane M.},
  title        = {{Beyond Accuracy: What Data Quality Means to Data Consumers}},
  journaltitle = {Journal of Management Information Systems},
  date         = {1996},
  volume       = {12},
  number       = {4},
  pages        = {5--33},
  doi          = {10.1080/07421222.1996.11518099},
}

@inproceedings{Wu-Xianjie2025:tablebench,
  author       = {Wu, Xianjie and Yang, Jian and Chai, Linzheng and Zhang, Ge
                  and Liu, Jiaheng and Du, Xinrun and Liang, Di and Shu, Daixin
                  and Cheng, Xianfu and Sun, Tianzhen and Niu, Guanglin
                  and Li, Tongliang and Li, Zhoujun},
  title        = {{TableBench: A Comprehensive and Complex Benchmark for Table
                   Question Answering}},
  booktitle    = {Proceedings of the AAAI Conference on Artificial Intelligence},
  date         = {2025},
  volume       = {39},
  number       = {24},
  pages        = {25497--25506},
  doi          = {10.1609/aaai.v39i24.34739},
  eprint       = {2408.09174},
  eprinttype   = {arxiv},
}
```
