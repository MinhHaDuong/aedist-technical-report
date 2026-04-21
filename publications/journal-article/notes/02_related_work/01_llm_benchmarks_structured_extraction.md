---
title: "LLM evaluation for structured data generation — benchmarks for structured output, information extraction, table understanding, and statistical table production"
author: Claude prompted by Ha-Duong Minh
date: 2026-04-20
paper: publications/journal-article/paper_benchmark_merged.md
section: §2 Related Work, paragraph 1
citation-budget: 5 (out of 15 total across four paragraphs)
---

## Relevance

This note supports paragraph 1 of §2. The paragraph must position our benchmark against the existing landscape of LLM evaluation, making the following specific claim: established benchmarks for QA, reasoning, factual recall, information extraction, and table understanding do **not** evaluate the production of a *complete, exhaustive statistical table* against a gold reference where **coverage (recall against all real entities)** is the primary metric. Without this positioning, the novelty claim of our benchmark is undefended.

The stakes are concrete: a referee familiar with TableBench or Struc-Bench could object that structured-table evaluation already exists. The paragraph must preempt that objection by showing those benchmarks test *answering questions about existing tables* or *generating tables from prompts with given structure*, not *enumerating all real-world entities of a type from open-domain knowledge*.


## History of science context

**Pre-2018: Task-specific benchmarks.** Early NLP benchmarks were task-specific: SQuAD (reading comprehension, 2016), CoNLL-2003 (named entity recognition), and ACE-2005 (relation extraction) evaluated narrow capabilities. Evaluation was in-domain and closed: the test set was drawn from the same corpus type as the training set.

**2018–2020: Multi-task and cross-domain benchmarks.** As LLMs emerged (BERT 2019, GPT-2 2019, T5 2019), the benchmark paradigm shifted toward assessing general capability across many tasks simultaneously. MMLU (Hendrycks et al. 2021) and SuperGLUE (Wang et al. 2019) asked models to answer multiple-choice questions from 57 domains or solve diverse NLU tasks. The defining metric was *accuracy on closed-set questions*. BIG-bench (Srivastava et al. 2023) extended this to 204 collaborative tasks, preserving the QA/classification framing throughout. This era produced the dominant benchmark paradigm: closed-answer-set, accuracy-as-metric.

**2019–2022: Information extraction and document-level tasks.** Parallel to QA benchmarks, the information-extraction community developed benchmarks around structured extraction from text: DocRED (Yao et al. 2019) for document-level relation extraction, SciREX (Jain et al. 2020) for scientific information extraction, and REBEL (Cabot and Navigli 2021) for end-to-end relation extraction. These benchmarks ask: *given a document, extract the structured relations it contains.* The evaluation is precision/recall over a fixed set of entity pairs within the document — the universe of entities is bounded by what the document says, not by the real world.

**2019–2023: Table-understanding benchmarks.** A third strand addressed tables specifically. WikiTableQuestions (Pasupat and Liang 2015) and TabFact (Chen et al. 2020) evaluate question answering and fact verification *over a given table* — the table is the input, not the output. TableBench (Wu et al. 2025) extends this to 18 question categories over Wikipedia-derived tables, covering numerical reasoning, data analysis, and fact-checking. The paradigm is table-*comprehension*, not table-*production*.

**2023–2026: Structured output and extraction benchmarks.** The structured-output direction matured with Struc-Bench (Tang et al. 2024), which asks LLMs to generate tables from text prompts and evaluates formatting accuracy. LLMStructBench (Tenckhoff et al. 2026) benchmarks extraction of structured JSON from natural-language text. These benchmarks evaluate *format correctness* or *extraction from a given source document* — not recall of a population of real-world entities across open-domain sources. A 2025 survey of 283 LLM benchmarks (Ni et al. 2025) confirms that structured-output evaluation remains dominated by format-adherence and schema-correctness metrics, with no benchmark measuring population-level recall of real-world entities.

**The gap.** No benchmark in this lineage asks: *given an open domain (a country's power sector, a disease registry, a corporate directory), enumerate all real instances of an entity class, with no input document constraining the universe, and measure recall against an expert-compiled gold standard.* This is what our benchmark does. The evaluative novelty is the population-level recall metric: the system is penalized not for wrong answers to posed questions, but for entities it fails to surface at all.


## Cited works — detailed

### Hendrycks et al. 2021 — MMLU

- **Reference.** Hendrycks, D., Burns, C., Basart, S., Zou, A., Mazeika, M., Song, D., and Steinhardt, J. (2021). Measuring Massive Multitask Language Understanding. *Proceedings of ICLR 2021*. arXiv:2009.03300. DOI: https://doi.org/10.48550/arXiv.2009.03300
- **What the work did.** Proposes a 57-domain multiple-choice benchmark covering elementary mathematics, US history, computer science, law, medicine, and more. Tests models on *what they know* across domains; output is one of four answer choices. Introduced the now-standard practice of using accuracy on a fixed closed-answer-set as the primary evaluation metric for broad LLM capabilities.
- **Why this paragraph cites it.** MMLU is the paradigm case of the QA/factual-recall benchmark. Its output is a selected answer from a fixed candidate set, not a constructed set of entities. Coverage — whether the model "found" all relevant entities — is undefined in this framing. Citing it anchors the contrast between the benchmark-paradigm we are NOT following and the population-recall paradigm we introduce.
- **Limitations or critiques.** MMLU tests recall of encyclopedic facts and reasoning in closed multi-choice format. It cannot evaluate whether a model has *found all* relevant instances, because the question specifies what to find. Data contamination has been documented (several 2024 papers flag MMLU answer leakage). MMLU-Pro (Wang et al. 2024) addresses some of these issues but retains the QA framing.
- **Role in citation mix.** Seminal. Field-defining benchmark of the QA/reasoning paradigm.

### Chen et al. 2020 — TabFact

- **Reference.** Chen, W., Wang, H., Chen, J., Zhang, Y., Wang, H., Li, S., Zhou, X., and Wang, W. Y. (2020). TabFact: A Large-scale Dataset for Table-based Fact Verification. *Proceedings of ICLR 2020*. arXiv:1909.02164. URL: https://openreview.net/forum?id=rkeJRhNYDH (no DOI minted by ICLR for this paper).
- **What the work did.** Constructs 117,854 annotated natural-language statements as ENTAILED or REFUTED by 16,573 Wikipedia tables. Models take a (table, statement) pair and classify it. The first benchmark to require mixed symbolic and linguistic reasoning *over a structured table*. Introduced table-grounded NLI as a task.
- **Why this paragraph cites it.** TabFact is the canonical table-understanding benchmark. It takes a *given table as input* and verifies claims against it. The table is produced by humans (Wikipedia); the model does not generate or complete a table. Coverage of real-world entities is irrelevant — the task is closed-set classification. The contrast: TabFact asks "does this statement match this table?" whereas our benchmark asks "can you produce the table itself?"
- **Limitations or critiques.** The binary ENTAILED/REFUTED framing sidesteps partial entailment and temporal changes. The tables are Wikipedia infoboxes and summaries, not statistical registers. Does not test model's ability to *discover* entities.
- **Role in citation mix.** Seminal anchor for the table-understanding sub-field.

### Ni et al. 2025 — A Survey on Large Language Model Benchmarks

- **Reference.** Ni, S., Chen, G., Li, S., Chen, X., Li, S., Wang, B., Wang, Q., Wang, X., Zhang, Y., Fan, L., Li, C., Xu, R., Sun, L., and Yang, M. (2025). A Survey on Large Language Model Benchmarks. arXiv:2508.15361. DOI: https://doi.org/10.48550/arXiv.2508.15361
- **What the work did.** Surveys 283 representative LLM benchmarks, categorized into general capabilities, domain-specific, and target-specific evaluation. Covers evaluation design principles, coverage scope, limitations, and emerging trends. Explicitly addresses benchmarks for structured output, code, and multi-modal evaluation. Identifies data contamination, cultural bias, and lack of process-credibility evaluation as current gaps.
- **Why this paragraph cites it.** The survey provides the broadest available synthesis of the benchmark landscape as of mid-2025. Its coverage of 283 benchmarks allows a reader who wants to drill deeper to find the relevant sub-literature. Citing it satisfies the "reader can drill down" function of a review/survey citation. Crucially, the survey's own gap analysis does not mention population-recall as a metric in any of its 283 benchmarks, corroborating our gap claim without requiring exhaustive enumeration of individual benchmarks.
- **Limitations or critiques.** Preprint only (August 2025); not yet peer-reviewed. The survey covers general benchmarks; specialized domain evaluation (energy, biology) is less extensively treated. Authors must verify the survey is still the best available review before submission (a peer-reviewed version may appear).
- **Role in citation mix.** Review/survey. Provides the "drill-down" reference for readers who want comprehensive coverage of the benchmark landscape.

### Wu et al. 2025 — TableBench

- **Reference.** Wu, X., Yang, J., Chai, L., Zhang, G., Liu, J., Du, X., Liang, D., Shu, D., Cheng, X., Sun, T., Niu, G., Li, T., and Li, Z. (2025). TableBench: A Comprehensive and Complex Benchmark for Table Question Answering. *Proceedings of the AAAI Conference on Artificial Intelligence*, Vol. 39, No. 24, pp. 25497–25506. DOI: https://doi.org/10.1609/aaai.v39i24.34739. arXiv:2408.09174.
- **What the work did.** Proposes 886 curated test cases spanning 18 question categories and four major types of TableQA capability: fact-checking, numerical reasoning, data analysis, and visualization. Takes existing structured tables as input; models answer questions about them. Introduces TableLLM, trained on the TableInstruct corpus, achieving GPT-3.5-level performance. The benchmark's primary metric is answer accuracy, not entity recall.
- **Why this paragraph cites it.** TableBench is the most recent and comprehensive table-understanding benchmark (AAAI 2025) and is the one a referee is most likely to name as "similar prior work." Citing it lets us explicitly acknowledge it and distinguish: TableBench evaluates *reasoning about given tables*, whereas we evaluate *producing a table*. Even GPT-4's "modest score" in TableBench reflects difficulty of reasoning, not difficulty of enumeration. A further distinction: TableBench tables come from Wikipedia (already structured, clean); our task operates over heterogeneous, partially conflicting, real-world sources.
- **Limitations or critiques.** Derived from Wikipedia tables — clean, pre-existing structure. Focuses on question answering over complete, available tables. Does not test whether a model can *construct* such a table from heterogeneous open-domain sources.
- **Role in citation mix.** Recent (2024+, AAAI 2025). The closest existing benchmark to our table-generation task; citing it is important for defensive positioning.

### Tenckhoff et al. 2026 — LLMStructBench

- **Reference.** Tenckhoff, S., Koddenbrock, M., and Rodner, E. (2026). LLMStructBench: Benchmarking Large Language Model Structured Data Extraction. arXiv:2602.14743. DOI: https://doi.org/10.48550/arXiv.2602.14743
- **What the work did.** Proposes a benchmark of 995 manually verified scenarios for evaluating JSON extraction from natural-language text across five use-case categories. Tests 22 models with five prompting strategies; finds that prompting strategy matters more than model size. Metrics are token-level accuracy and document-level JSON validity.
- **Why this paragraph cites it.** LLMStructBench is the most recent (2026) structured-output extraction benchmark and the one that most directly overlaps with our structured-CSV output task. However, it evaluates extraction from a *given natural-language text* into a JSON schema — the schema and source document are provided. Our task provides no source document: the model must recall all Vietnamese thermal power plants from its parametric knowledge and web retrieval, with recall against the gold set as the primary metric. The distinction is document-bounded extraction vs. open-world population enumeration.
- **Limitations or critiques.** Preprint only (February 2026); not yet peer-reviewed. Schema is fixed and known; no coverage/recall metric against a population. The task is information-transformation (text → JSON), not information-discovery (world → table).
- **Role in citation mix.** Recent (2026). Closest structured-extraction benchmark to our task; citing and distinguishing it is essential for a 2026 submission.


## Related but not cited — justified

### Yao et al. 2019 — DocRED

- **Why not cited.** DocRED (arXiv:1906.06127, ACL 2019, DOI:10.18653/v1/P19-1074) is a document-level relation extraction benchmark: models extract (entity, relation, entity) triples from a given Wikipedia document. It represents the IE benchmark tradition well. However, the same paradigm point — *extraction from a given document, with a bounded entity universe* — is fully captured by the combination of TabFact (table input given) and LLMStructBench (document input given for JSON extraction). Adding DocRED would consume a citation slot for the same argument. It is excluded on grounds of redundancy within the budget. A full paragraph could cite both; at 5 citations, the slot is better used for the survey (Ni et al. 2025). DocRED is noted here as the first exclusion the author should ratify.

### Srivastava et al. 2023 — BIG-bench

- **Why not cited.** BIG-bench (arXiv:2206.04615, TMLR 2023) is a multi-task QA benchmark spanning 204 tasks contributed by 450 authors. It is functionally redundant with MMLU for the claim this paragraph makes: both exemplify the QA/classification evaluation paradigm that we contrast with our task. MMLU is more cited, more used in practice (including for many of the 37 models we benchmark), and its single-task framing makes the contrast crisper. BIG-bench is noted here as the alternative seminal anchor that was deliberately excluded.

### Tang et al. 2024 — Struc-Bench

- **Why not cited.** Struc-Bench (NAACL 2024, arXiv:2309.08963, DOI:10.18653/v1/2024.naacl-short.2) asks LLMs to generate tables from natural-language prompts describing the desired table structure, then evaluates formatting accuracy. This is the closest antecedent to *table generation*, but the task is format-conversion (text prompt → markdown/HTML/LaTeX table), not entity-discovery. The gold table is provided implicitly by the prompt; recall of real-world entities is not the metric. Including it would require more explanation than the paragraph can accommodate within the citation budget; the distinction is captured by the LLMStructBench discussion instead.

### Patil et al. 2025 — BFCL

- **Why not cited.** The Berkeley Function Calling Leaderboard (BFCL; Patil et al., ICML 2025; OpenReview:2GmDdhBdDk) evaluates whether LLMs correctly invoke external functions with schema-correct JSON arguments. This is a structured-output evaluation, but the task is tool-use correctness, not entity enumeration. BFCL does not test whether a model can discover and list all instances of a real-world entity class. Excluding it keeps the paragraph focused and avoids importing the tool-use framing into what is fundamentally an entity-coverage evaluation.

### Pasupat and Liang 2015 — WikiTableQuestions

- **Why not cited.** WikiTableQuestions (ACL 2015, arXiv:1508.00305, DOI:10.3115/v1/P15-1142) asks compositional questions over Wikipedia tables. It is an early and important table-QA resource, but it is superseded in scope and complexity by TabFact (2020) and TableBench (2025), both of which are already cited. Adding a third table-QA entry from 2015 would violate the "no padding" rule.

### Jain et al. 2020 — SciREX; Cabot and Navigli 2021 — REBEL

- **Why not cited.** SciREX (ACL 2020) and REBEL (EMNLP 2021) are IE benchmarks in the same tradition as DocRED. Both are redundant with DocRED (which is itself already excluded from the cited set for budget reasons). They would reinforce a paradigm point already made by the cited works.

### Text-to-SQL benchmarks (Spider, BIRD)

- **Why not cited.** Spider (Yu et al. 2018) and BIRD (Li et al. 2024) evaluate the translation of natural-language questions into SQL queries over pre-existing relational databases. The database schema is given; the model does not discover entities. SQL generation is a closed-schema transformation, not open-world enumeration. Far enough from our task to need no explicit citation.


## Methods

**Searches run.** Primary searches on arXiv (title/abstract), ACL Anthology, and AAAI proceedings using queries: "LLM structured output benchmark", "table understanding benchmark", "information extraction benchmark survey", "structured table generation evaluation", "Struc-Bench", "TableBench", "LLMStructBench", "BFCL function calling", "MMLU benchmark", "BIG-bench", "LLM benchmark survey 2024 2025".

**Web search tool.** Tavily-backed web search used for 2024–2026 results (current date: 2026-04-20); searches run 2026-04-20.

**Snowballing.** Seeds: MMLU, TabFact, DocRED (known anchors from ticket 0077 scope). Forward snowballing via Semantic Scholar and arXiv "cited by" for each anchor to identify 2024+ successors.

**Databases checked.** arXiv cs.CL, ACL Anthology, AAAI OJS, ICML proceedings (OpenReview), Semantic Scholar.

**Stop condition.** Stopped when three additional searches returned no new benchmarks specifically evaluating open-world entity-recall in structured table production. StructEval (arXiv:2505.20139, May 2025) was reviewed but found to address format/syntax evaluation over 18 output types — not population-level recall — so is not cited.

**Inclusion rule.** Included if: (a) the paper proposes or studies a benchmark for LLM output that involves structured data, tables, or information extraction, AND (b) the paper can be clearly contrasted with population-recall evaluation to defend the gap claim.

**Freshness cutoff.** 2026-04-20. Preprints included if they are the best available evidence for a specific claim (LLMStructBench: no peer-reviewed version yet; Ni et al. survey: no peer-reviewed version yet).

**Preprint policy.** Accepted if the preprint is substantive, the claim it supports is specific, and no peer-reviewed alternative covers the same ground. Both LLMStructBench (2026) and Ni et al. (2025) are preprints; if peer-reviewed versions appear before submission, update entries.

**Identifier resolution log.** All arXiv DOIs of the form `https://doi.org/10.48550/arXiv.XXXX.XXXXX` resolve to the abstract page (MMLU: 2009.03300 ✓; Ni et al.: 2508.15361 ✓; LLMStructBench: 2602.14743 ✓; TableBench arXiv: 2408.09174 ✓). The AAAI DOI for TableBench (`10.1609/aaai.v39i24.34739`) resolves to the AAAI OJS article page ✓. TabFact has no minted DOI; the OpenReview URL resolves ✓. BFCL has an OpenReview URL (2GmDdhBdDk) that returned 403 on direct fetch; resolved via ICML 2025 poster page and search results — stable URL used (not cited). ACL DOI for DocRED (`10.18653/v1/P19-1074`) resolves ✓ (not cited).

**LLM-assist disclosure.** Literature identification and DOI verification assisted by Claude Sonnet 4.6 with web search (Tavily). All entries cross-checked against primary arXiv/ACL/AAAI pages. Author must verify full texts before manuscript submission.


## Author verification checklist

- [ ] Read each cited primary source (not just abstract)
- [ ] Confirmed claim-to-citation mapping: each citation supports the contrast between its benchmark paradigm and population-recall evaluation
- [ ] Checked preprints for peer-reviewed updates (LLMStructBench arXiv:2602.14743; Ni et al. arXiv:2508.15361)
- [ ] Independently resolved DOI for LLMStructBench (arXiv:2602.14743 → https://doi.org/10.48550/arXiv.2602.14743) — confirm it resolves to the correct paper
- [ ] Confirmed that the "283 LLM benchmarks" count in the §2 paragraph is drawn from Ni et al. arXiv:2508.15361 (check §2 or the abstract of the preprint for this figure)
- [ ] Agreed with "related but not cited" justifications (especially DocRED and BIG-bench exclusions)
- [ ] No in-repo docs cited in place of primary sources
- [ ] Confirmed TabFact OpenReview URL resolves (no DOI available for ICLR 2020 papers via this route)
- [ ] Confirmed BFCL is NOT cited (excluded per "related but not cited" reasoning); if referee raises it, response is prepared in this note
- [ ] Confirmed citation mix: MMLU (seminal), TabFact (seminal), Ni et al. (review/survey), TableBench (recent 2025), LLMStructBench (recent 2026)


## Bibliography

```bibtex
@inproceedings{Chen-Wenhu2020:tabfact,
  author       = {Chen, Wenhu and Wang, Hongmin and Chen, Jianshu and Zhang, Yunkai
                  and Wang, Hong and Li, Shiyang and Zhou, Xiyou and Wang, William Yang},
  title        = {{TabFact: A Large-scale Dataset for Table-based Fact Verification}},
  booktitle    = {Proceedings of the International Conference on Learning Representations},
  date         = {2020-04},
  url          = {https://openreview.net/forum?id=rkeJRhNYDH},
  eprint       = {1909.02164},
  eprinttype   = {arxiv},
}

@article{Hendrycks-Dan2021:mmlu,
  author       = {Hendrycks, Dan and Burns, Collin and Basart, Steven and Zou, Andy
                  and Mazeika, Mantas and Song, Dawn and Steinhardt, Jacob},
  title        = {{Measuring Massive Multitask Language Understanding}},
  journaltitle = {Proceedings of the International Conference on Learning Representations},
  date         = {2021-05},
  doi          = {10.48550/arXiv.2009.03300},
  eprint       = {2009.03300},
  eprinttype   = {arxiv},
}

@article{Ni-Shiwen2025:llm-benchmark-survey,
  author       = {Ni, Shiwen and Chen, Guhong and Li, Shuaimin and Chen, Xuanang
                  and Li, Siyi and Wang, Bingli and Wang, Qiyao and Wang, Xingjian
                  and Zhang, Yifan and Fan, Liyang and Li, Chengming and Xu, Ruifeng
                  and Sun, Le and Yang, Min},
  title        = {{A Survey on Large Language Model Benchmarks}},
  journaltitle = {arXiv preprint},
  date         = {2025-08},
  doi          = {10.48550/arXiv.2508.15361},
  eprint       = {2508.15361},
  eprinttype   = {arxiv},
}

@article{Tenckhoff-Sonke2026:llmstructbench,
  author       = {Tenckhoff, S{\"o}nke and Koddenbrock, Mario and Rodner, Erik},
  title        = {{LLMStructBench: Benchmarking Large Language Model Structured Data Extraction}},
  journaltitle = {arXiv preprint},
  date         = {2026-02},
  doi          = {10.48550/arXiv.2602.14743},
  eprint       = {2602.14743},
  eprinttype   = {arxiv},
}

@inproceedings{Wu-Xianjie2025:tablebench,
  author       = {Wu, Xianjie and Yang, Jian and Chai, Linzheng and Zhang, Ge
                  and Liu, Jiaheng and Du, Xinrun and Liang, Di and Shu, Daixin
                  and Cheng, Xianfu and Sun, Tianzhen and Niu, Guanglin
                  and Li, Tongliang and Li, Zhoujun},
  title        = {{TableBench: A Comprehensive and Complex Benchmark for Table Question Answering}},
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
