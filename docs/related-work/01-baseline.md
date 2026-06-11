---
title: Parametric direct-query baseline for structured-table generation
author: Claude prompted by Ha-Duong Minh
date: 2026-05-21
paper: slides/manuscript/main.tex
section: §1 Baseline (lines 9–23)
citation-budget: 10–15
---

## Relevance

The manuscript opens its empirical case with a controlled experiment: sixteen LLMs are asked to produce a structured inventory of Vietnam's thermal power plants from parametric knowledge alone, no documents, no web. The paragraph claims a five-mode failure taxonomy — refusal, under-coverage, hallucination, within-model non-determinism at T=0, no cost–quality monotonicity — observable as descriptive statistics across 80 runs. A referee will ask: which of these failure modes are well-attested elsewhere, which are project-specific phenomena, and which are sharpening of known issues against a new task (open-world structured extraction of industrial assets)? This note lines up the anchors so each clause in the paragraph has at least one prior-art citation behind it.

## History of science context

Two threads converge on this paragraph.

The first thread is **closed-book / parametric knowledge extraction**. Petroni et al. (2019) framed pretrained language models as implicit knowledge bases — cloze probing of BERT for factual triples. Roberts et al. (2020) extended this to open-domain QA without retrieval, showing that knowledge "packing" scales with parameters but quickly saturates and remains brittle on tail entities. Carlini et al. (2021) gave the dark mirror image: parametric "knowledge" includes memorised training data, and is therefore not always principled retrieval but sometimes verbatim regurgitation. The 2023–2025 wave (Hendrycks et al. MMLU, Wu et al. TableBench, Tenckhoff et al. LLMStructBench, Ni et al. survey) shifts from "does the model know facts" to "can the model render structured outputs against a schema while keeping facts straight." Our baseline sits squarely in this thread, but on a task harder than any benchmark we found: open-world enumeration of an entire national asset class with cell-level attributes.

The second thread is **failure-mode characterisation in generative AI**. Lin et al. (2021) TruthfulQA showed that scaling alone does not buy truthfulness — the "Récalcitrant"/"Hallucinant" axis. Huang et al. (2023) and Ji et al. (2023) consolidated the hallucination taxonomy. Atil et al. (2024) characterised non-determinism even under deterministic decoding settings — directly relevant to our Non-déterministe mode. Sharma et al. (2023) on sycophancy is the inverse of refusal: trained-in compliance. Wang et al. (2022) self-consistency reframed within-run variance as a feature (sample many, vote) rather than a bug (sample once, hope) — useful counterpoint to our five-rep design.

The opposing view in the literature is "scale solves it" (the scaling-law programme of Kaplan et al. 2020 and successors): with enough parameters and data, parametric extraction will reach acceptable quality. Our results are a small data point against that view for this specific task class.

## Cited works — detailed

### Atil et al. 2024 — Non-determinism of deterministic LLM settings
- **Reference.** Atil, B.; Aykent, S.; Chittams, A. et al. *Non-Determinism of "Deterministic" LLM Settings*. arXiv:2408.04667, 2024.
- **What the work did.** Tested five LLMs across eight tasks with ten runs each at temperature 0; reports accuracy variations up to 15 % and total-agreement-rate metrics (TARr@N, TARa@N).
- **Why this paragraph cites it.** Direct anchor for the Non-déterministe failure mode. Provides the empirical norm against which our within-model F1 spreads (DeepSeek V4-Flash 0.01–0.65 across 5 reps) can be reported.
- **Limitations or critiques.** Their tasks are short-answer QA, not multi-row structured extraction; the magnitude of variance is not directly transferable. We extend the phenomenon to a larger output unit and a multimodal MoE-routing setting.

### Carlini et al. 2021 — Extracting training data from LLMs
- **Reference.** Carlini, N.; Tramèr, F.; Wallace, E. et al. *Extracting Training Data from Large Language Models*. USENIX Security, 2021. (Existing key `ATRGAC9J`.)
- **What the work did.** Demonstrated verbatim extraction of memorised training data from GPT-2 via targeted prompts.
- **Why this paragraph cites it.** Establishes that parametric "knowledge" can be memorised strings rather than abstracted facts — relevant to the Hallucinant mode and to the limits of closed-book extraction. Plant names and capacities appearing in our outputs may be verbatim memorisations of training-set documents rather than learned facts.
- **Limitations or critiques.** Focused on privacy / memorisation, not on factual correctness; their threat model is exfiltration, ours is extraction quality.

### Hendrycks et al. 2021 — MMLU
- **Reference.** Hendrycks, D.; Burns, C.; Basart, S. et al. *Measuring Massive Multitask Language Understanding*. ICLR 2021. (Existing key `Hendrycks-Dan2021:mmlu`.)
- **What the work did.** 57-subject multiple-choice benchmark for parametric knowledge in 0-shot / few-shot regimes.
- **Why this paragraph cites it.** Field-defining anchor for parametric-knowledge evaluation. Establishes the practice of grading "what the model knows" as a stratified score; our F1-on-Vietnam-plants is a domain-specific instance in the same evaluation paradigm, but with an open-set generation target rather than MCQA.
- **Limitations or critiques.** MMLU is closed-set, single-token answer. Does not reach the open-world structured-extraction setting where hallucination and over-generation become measurable separately from accuracy.

### Huang et al. 2023 — Survey on hallucination in LLMs
- **Reference.** Huang, L.; Yu, W.; Ma, W. et al. *A Survey on Hallucination in Large Language Models: Principles, Taxonomy, Challenges, and Open Questions*. ACM TOIS, 2024 (arXiv:2311.05232, 2023).
- **What the work did.** Comprehensive taxonomy of hallucination types in LLMs, detection methods, mitigation strategies, retrieval-augmentation limits.
- **Why this paragraph cites it.** Recent survey anchoring the Hallucinant failure mode in the broader hallucination literature; gives the referee a taxonomy lookup table for our specific case (fabricated plant names, fabricated source URLs).
- **Limitations or critiques.** Survey-level coverage; does not provide a benchmark we can compare against directly. Hallucination is treated mostly in free-text generation, not in structured-table generation where the unit of fabrication is a row.

### Lin et al. 2021 — TruthfulQA
- **Reference.** Lin, S.; Hilton, J.; Evans, O. *TruthfulQA: Measuring How Models Mimic Human Falsehoods*. ACL 2022 (arXiv:2109.07958, 2021).
- **What the work did.** 817-question benchmark on truthfulness; finds that scale does not monotonically improve truthfulness, larger models can be worse.
- **Why this paragraph cites it.** Direct anchor for the Non-monotone observation: no monotonic cost–F1 relationship in our data (Claude Opus 4.6 at $1.23 → F1=0.46; GPT-OSS-20B at $0.01 → F1=0.58). TruthfulQA is the field's canonical demonstration that paying more does not buy more truth.
- **Limitations or critiques.** Hand-crafted adversarial questions; the inverse-scaling effect is partly an artifact of the prompt design choices. We do not replicate inverse scaling — we report absence of monotonicity, weaker claim.

### Petroni et al. 2019 — Language Models as Knowledge Bases?
- **Reference.** Petroni, F.; Rocktäschel, T.; Lewis, P. et al. *Language Models as Knowledge Bases?*. EMNLP 2019 (arXiv:1909.01066).
- **What the work did.** Cloze-style probing of BERT and successors; baseline for LM-as-KB programme.
- **Why this paragraph cites it.** Field-defining older anchor — establishes the question "what does the model know parametrically?" that our baseline operationalises for the open-world energy-asset case.
- **Limitations or critiques.** Pre-instruction-tuned models; closed-vocabulary cloze. Modern LLMs queried through chat interfaces behave differently, but the underlying epistemic question is the same.

### Roberts et al. 2020 — Closed-book QA
- **Reference.** Roberts, A.; Raffel, C.; Shazeer, N. *How Much Knowledge Can You Pack Into the Parameters of a Language Model?*. EMNLP 2020 (arXiv:2002.08910).
- **What the work did.** Fine-tuned T5 for open-domain QA without retrieval; established the closed-book QA paradigm and its scaling.
- **Why this paragraph cites it.** Conceptual anchor for our experiment: ours is structured closed-book extraction, an extension of their setting to multi-row tabular outputs.
- **Limitations or critiques.** Their target is single-fact QA. Multi-row extraction multiplies the chances of failure and exposes coverage/precision separately, which their setting cannot.

### Singhania et al. 2022 — LM-KBC
- **Reference.** Singhania, S.; Gashteovski, K.; Szarvas, G.; Lawrence, C. *LM-KBC: Knowledge Base Construction from Pre-Trained Language Models*. ISWC 2022. (Existing key `Singhania-Sneha2022:lm-kbc`.)
- **What the work did.** Shared task on building knowledge bases by probing pre-trained LMs.
- **Why this paragraph cites it.** Directly relevant ancestry — the experiment we run is the same problem class (extract structured facts from parametric knowledge) on a more open task (open enumeration over a national asset class, not subject–predicate probing over a closed schema).
- **Limitations or critiques.** Their schema is fixed and triples are short. Our schema is wider (13 columns, free-form values).

### Tenckhoff et al. 2026 — LLMStructBench
- **Reference.** Tenckhoff, S.; Koddenbrock, M.; Rodner, E. *LLMStructBench: Benchmarking Large Language Model Structured Data Extraction*. arXiv:2602.14743, 2026. (Existing key `Tenckhoff-Sonke2026:llmstructbench`.)
- **What the work did.** Benchmark for structured-data extraction from text by LLMs.
- **Why this paragraph cites it.** Recent frontier work on the structured-extraction quality measurement problem; nearest peer to our evaluation methodology.
- **Limitations or critiques.** Inputs are documents; ours is parametric (no input documents). Their benchmark is the closest available, but it measures a different cell of the design space.

### Wu et al. 2025 — TableBench
- **Reference.** Wu, X.; Yang, J.; Chai, L. et al. *TableBench: A Comprehensive and Complex Benchmark for Table Question Answering*. AAAI 2025. (Existing key `Wu-Xianjie2025:tablebench`.)
- **What the work did.** Benchmark for table-QA spanning 18 task categories.
- **Why this paragraph cites it.** Provides a baseline complexity scale for table-related LLM evaluation; our task is table-*generation*, not table-QA, but the same scoring instruments (cell accuracy, row-level F1) apply.
- **Limitations or critiques.** Table-QA assumes the table is given; we measure table generation. Different epistemic situation.

### Ni et al. 2025 — LLM benchmark survey
- **Reference.** Ni, S.; Chen, G.; Li, S. et al. *A Survey on Large Language Model Benchmarks*. arXiv:2508.15361, 2025. (Existing key `Ni-Shiwen2025:llm-benchmark-survey`.)
- **What the work did.** Recent survey of LLM benchmarks across knowledge, reasoning, and structured tasks.
- **Why this paragraph cites it.** Provides the recent-survey anchor and validates that no off-the-shelf benchmark covers open-world structured asset extraction.
- **Limitations or critiques.** General survey; no domain-specific guidance on energy or industrial assets.

## Related but not cited — justified

### Kaplan et al. 2020 — Scaling laws for neural language models
The "scale solves it" reference our Non-monotone claim implicitly opposes. We do not cite it because the claim is about training compute and loss, not about cost-per-API-call vs. downstream task accuracy on a held-out domain. Adding it would require a separate methodological footnote we do not have room for. Recorded here for completeness.

### Wang et al. 2022 — Self-consistency decoding
Existing key `Wang2022:self-consistency`. The paper proposes treating within-run variance as a feature (vote across samples). Our five-rep design is conceptually adjacent but used to characterise variance, not to reduce it. We deliberately do not aggregate via voting — the spread itself is the measurement. Worth citing in the *experimental design* methods section rather than in the baseline-results paragraph.

### Sharma et al. 2023 — Sycophancy in language models
Sycophancy is the opposite failure of refusal — trained-in agreement. Our GPT-5.5 refusals are arguably the principled inverse (refuse rather than fabricate). Citing this would broaden the paragraph beyond its budget; saved for the §4 discussion of model-as-epistemic-agent if needed.

### Ji et al. 2023 — Hallucination survey
ACM Computing Surveys 2023 hallucination survey (DOI 10.1145/3571730). Predates Huang et al. 2023 by months and overlaps heavily. Huang et al. is fresher and broader; Ji et al. earns its place only if a referee asks for "the original survey." We keep one of two.

### Dziri et al. 2023 — Faith and Fate
arXiv:2305.18654. Limits of compositional reasoning in transformers. Relevant if we framed our task as compositional reasoning over a schema; we frame it as factual extraction, so this is a parallel rather than direct anchor.

### TabFact (Chen et al. 2020)
Existing key `Chen-Wenhu2020:tabfact`. Verification of facts against tables — adjacent but inverted setting (verification vs. generation). Skipped to keep the budget.

## Methods

- **Search seeds.** The manuscript paragraph itself (claims to anchor), the project's `docs/quality-grounding.md` and `docs/framework-grounding-map.md` (philosophy-of-science background), the existing `report/refs.bib` (already-validated keys), and the task brief's explicit anchor topics.
- **Databases.** arXiv (via WebFetch on canonical IDs), DOI resolver (10.x prefixes), ACL Anthology (resolved via arXiv IDs of ACL papers).
- **Stop condition.** 11 entries cited + 6 in related-but-not-cited (covers each of the five failure modes with at least one anchor, plus the two field-defining historical anchors). Budget hit.
- **Inclusion rule.** (a) Directly supports one or more clauses in the paragraph, (b) resolved cleanly via WebFetch, (c) reusable from `refs.bib` or compact enough to mint a new key under the Author-NameYEAR:slug scheme.
- **Exclusion rule.** Marketing / press releases, in-repo `*.md` documents, broken / paywalled DOIs without OA mirror.
- **Freshness cutoff.** 2026-05-21.
- **Preprint policy.** arXiv preprints accepted when they are the canonical reference (Huang et al. 2023 had an ACM TOIS revision in 2024 — we cite the arXiv ID with a journaltitle note). When a paper has a peer-reviewed venue, we record it.
- **Grey-literature policy.** None used; all anchors are peer-reviewed or arXiv preprints by named authors.
- **Identifier resolution log.** WebFetched: 2311.05232 (Huang ✓), 2109.07958 (Lin ✓), 2408.04667 (Atil ✓), 2310.13548 (Sharma — used in not-cited), 2401.05566 (Hubinger — not used, off-topic), 2403.04893 (Longpre — not used, off-topic), 2002.08910 (Roberts ✓), 2001.08361 (Kaplan — used in not-cited), 2305.16291 (Voyager — not used), 1909.01066 (Petroni ✓). Existing-key entries (`Hendrycks-Dan2021:mmlu`, `Tenckhoff-Sonke2026:llmstructbench`, `Wu-Xianjie2025:tablebench`, `Ni-Shiwen2025:llm-benchmark-survey`, `ATRGAC9J` for Carlini, `Singhania-Sneha2022:lm-kbc`, `Wang2022:self-consistency`, `Chen-Wenhu2020:tabfact`) were trusted from refs.bib without re-resolution per SKILL guidance.
- **LLM-assist disclosure.** This note was drafted by Claude (Opus 4.7) operating under instructions in tickets/0151. WebFetch was used for identifier resolution. The author (Ha-Duong Minh) is expected to read each primary source before submission.

## Author verification checklist

- [ ] Read each cited primary source (not just abstract)
- [ ] Confirmed claim-to-citation mapping
- [ ] Checked preprints for peer-reviewed updates
- [ ] Agreed with "related but not cited" justifications
- [ ] No in-repo docs cited in place of primary sources

## Bibliography

```bibtex
@misc{Atil-Berk2024:nondeterminism,
  author       = {Atil, Berk and Aykent, Sarp and Chittams, Alexa and Fu, Lisheng
                  and Passonneau, Rebecca J. and Radcliffe, Evan and Rajagopal, Guru Rajan
                  and Sloan, Adam and Tudrej, Tomasz and Ture, Ferhan and Wu, Zhe
                  and Xu, Lixinyu and Baldwin, Breck},
  title        = {{Non-Determinism of "Deterministic" LLM Settings}},
  date         = {2024-08},
  eprint       = {2408.04667},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.2408.04667},
}

@inproceedings{ATRGAC9J,
  author       = {Carlini, N. and Tramèr, F. and Wallace, E. and Jagielski, M.
                  and Herbert-Voss, A. and Lee, K. and Roberts, A. and Brown, T.
                  and Song, D. and Erlingsson, Ú. and Oprea, A. and Raffel, C.},
  title        = {{Extracting Training Data from Large Language Models}},
  booktitle    = {Proceedings of the 30th USENIX Security Symposium},
  date         = {2021},
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

@article{Huang-Lei2023:hallucination-survey,
  author       = {Huang, Lei and Yu, Weijiang and Ma, Weitao and Zhong, Weihong
                  and Feng, Zhangyin and Wang, Haotian and Chen, Qianglong
                  and Peng, Weihua and Feng, Xiaocheng and Qin, Bing and Liu, Ting},
  title        = {{A Survey on Hallucination in Large Language Models:
                   Principles, Taxonomy, Challenges, and Open Questions}},
  journaltitle = {ACM Transactions on Information Systems},
  date         = {2024},
  eprint       = {2311.05232},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.2311.05232},
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

@article{Ni-Shiwen2025:llm-benchmark-survey,
  author       = {Ni, Shiwen and Chen, Guhong and Li, Shuaimin and Chen, Xuanang
                  and Li, Siyi and Wang, Bingli and Wang, Qiyao and Wang, Xingjian
                  and Zhang, Yifan and Fan, Liyang and Li, Chengming and Xu, Ruifeng
                  and Sun, Le and Yang, Min},
  title        = {{A Survey on Large Language Model Benchmarks}},
  journaltitle = {arXiv preprint},
  date         = {2025},
  doi          = {10.48550/arXiv.2508.15361},
  eprint       = {2508.15361},
  eprinttype   = {arxiv},
}

@inproceedings{Petroni-Fabio2019:lm-as-kb,
  author       = {Petroni, Fabio and Rockt{\"a}schel, Tim and Lewis, Patrick
                  and Bakhtin, Anton and Wu, Yuxiang and Miller, Alexander H.
                  and Riedel, Sebastian},
  title        = {{Language Models as Knowledge Bases?}},
  booktitle    = {Proceedings of the 2019 Conference on Empirical Methods in
                  Natural Language Processing},
  date         = {2019},
  eprint       = {1909.01066},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.1909.01066},
}

@inproceedings{Roberts-Adam2020:closed-book-qa,
  author       = {Roberts, Adam and Raffel, Colin and Shazeer, Noam},
  title        = {{How Much Knowledge Can You Pack Into the Parameters of a
                   Language Model?}},
  booktitle    = {Proceedings of the 2020 Conference on Empirical Methods in
                  Natural Language Processing},
  date         = {2020},
  eprint       = {2002.08910},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.2002.08910},
}

@inproceedings{Singhania-Sneha2022:lm-kbc,
  author       = {Singhania, Sneha and Gashteovski, Kiril and Szarvas, Gy{\"o}rgy
                  and Lawrence, Carolin},
  title        = {{LM-KBC: Knowledge Base Construction from Pre-Trained Language Models}},
  booktitle    = {Proceedings of the ISWC 2022 Posters, Demos and Industry Tracks},
  series       = {CEUR Workshop Proceedings},
  volume       = {3254},
  date         = {2022},
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
