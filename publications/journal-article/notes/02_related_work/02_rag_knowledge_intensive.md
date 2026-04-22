---
title: "Retrieval-Augmented Generation for knowledge-intensive tasks — RAG, its evaluation, and agentic/deep-research extensions"
author: Claude prompted by Ha-Duong Minh
date: 2026-04-20
paper: publications/journal-article/paper_benchmark_merged.md
section: §2 Related Work, paragraph 2
citation-budget: 4 (out of 15 total across four paragraphs; 5 used in P1, 10 remain for P2–P4)
---

## Relevance

This note supports paragraph 2 of §2. The paragraph must position our benchmark's use of RAG as a retrieval regime against the established RAG evaluation tradition, making the following specific claim: RAG and its successors — self-reflective RAG, corrective RAG, agentic deep-research systems — have been evaluated for QA accuracy and factual grounding, not for exhaustive dataset construction where recall of all real-world entities is the metric. Without this positioning, a referee familiar with the RAG literature could object that RAG has already been evaluated for "structured knowledge extraction," conflating QA-accuracy benchmarks with population-recall evaluation.

The intellectual stakes are two-fold. First, we must acknowledge that RAG is a standard and well-understood technique — we did not invent it — while explaining precisely how our use differs: RAG is a retrieval substrate in our benchmark, one axis of a six-axis experimental design, not the thing being evaluated per se. Second, the paragraph must draw a clean line between (a) the QA-accuracy evaluation tradition (NQ, TriviaQA, HotpotQA) and (b) our coverage evaluation tradition (recall of 163 plants against a gold standard), so that the gap paragraph (P4) can then say: this combination — RAG as substrate, coverage as metric, structured table as output — has not been benchmarked before.


## History of science context

**Pre-2020: Fixed parametric memory and its limits.** Early neural language models encoded knowledge in parametric weights during pre-training. GPT-2 (Radford et al. 2019) and T5 (Raffel et al. 2020) could answer factual questions from trained knowledge but suffered from hallucination, knowledge-cutoff brittleness, and poor performance on rare entities. The dominant paradigm for knowledge-intensive tasks was fine-tuning on closed-book QA datasets (Natural Questions, TriviaQA, HotpotQA).

**2020: Retrieval-Augmented Generation.** Lewis et al. (2020, NeurIPS) introduced RAG as an explicit combination of a parametric reader (seq2seq LM) and a non-parametric retriever (dense passage retrieval over Wikipedia). The key insight was end-to-end training of both components. Evaluated on Open-domain QA (NQ, TriviaQA, WebQuestions, CuratedTREC) and knowledge-intensive generation (MS-MARCO, Jeopardy, FEVER), RAG set state-of-the-art on three open-domain QA tasks. All evaluation metrics are accuracy on posed questions or factual verification — not population recall.

**2021–2023: RAG becomes standard practice; variants proliferate.** The RAG paradigm spread rapidly as a practical solution to LLM hallucination and knowledge-cutoff limitations. Variants addressed faithfulness (reducing hallucination in generated passages), efficiency (compressed retrieval), and multi-hop reasoning (iterative retrieval for HotpotQA-style questions). The evaluation canon remained QA-accuracy on fixed benchmarks; recall of real-world entity populations was not a concern because the task assumed a posed question, not an open enumeration.

**2023–2024: Self-reflective and corrective RAG.** Two key advances addressed quality beyond simple retrieval: (a) Self-RAG (Asai et al. 2024, ICLR Oral) trains the model to decide *when* to retrieve and to critique its own outputs via reflection tokens, evaluated on open-domain QA, fact verification, and long-form generation; (b) Corrective RAG (Yan et al. 2024, preprint) adds a lightweight retrieval evaluator and web-search fallback to correct low-quality retrieved documents, evaluated on NQ, TriviaQA, HotPotQA, and FEVER. Both frameworks improve QA accuracy and factual grounding — the metric is always answer accuracy or faithfulness, not population coverage.

**2024–2026: Agentic deep-research.** The agentic wave decoupled retrieval from a single retriever corpus. Systems such as OpenAI Deep Research (2025), Perplexity, and research agents (DeepResearcher, Zheng et al. 2025; W&D, various 2025 papers) perform multi-step web search, query decomposition, and synthesis to produce long-form reports. The GAIA benchmark (Mialon et al. 2024, ICLR) provides a key evaluation for this wave: 466 real-world questions requiring web browsing, multi-modality, and tool use — humans score 92%, GPT-4 with plugins 15%. Evaluation is factual accuracy (did the system find the correct answer?) or report quality (are the claims grounded?), not recall of a population of real-world entities.

**Opposing view: RAG for entity discovery.** Some work uses RAG-like retrieval for knowledge-base population (entity extraction from web corpora). This literature (REALM, Atlas, KG-RAG variants) operates in a different paradigm: it builds knowledge bases incrementally, with precision/recall defined over a curated ontology. Our work is closer to this paradigm than to QA-RAG in its use of recall, but we benchmark AI assistants applied to a pre-existing tabular domain, not propose a new KG construction technique.


## Cited works — detailed

### Lewis et al. 2020 — RAG original paper
*(existing key in refs.bib: ULQGRISS)*

- **Reference.** Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W., Rocktäschel, T., Riedel, S., and Kiela, D. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. *Advances in Neural Information Processing Systems 33 (NeurIPS 2020)*, pp. 9459–9474. arXiv:2005.11401. DOI: https://doi.org/10.48550/arXiv.2005.11401
- **What the work did.** Proposes RAG as an end-to-end trainable combination of a Dense Passage Retriever (DPR) over a Wikipedia index with a BART-based sequence-to-sequence reader. At inference, for each input, relevant passages are retrieved and concatenated to the input; the seq2seq model generates the output conditioned on both the input and retrieved context. Two variants: RAG-Sequence (retrieves once per output) and RAG-Token (retrieves per output token). Achieves state-of-the-art on NQ, TriviaQA, WebQuestions, and CuratedTREC (open-domain QA) and on Jeopardy question generation and FEVER fact verification.
- **Why this paragraph cites it.** Lewis 2020 is the foundational RAG paper and the reference all subsequent RAG work builds on. Citing it establishes that the RAG paradigm is evaluated for QA accuracy and factual grounding — the evaluation benchmarks (NQ, TriviaQA, WebQuestions, FEVER) all pose *specific questions*, not *enumeration tasks*. The contrast with our benchmark is concrete: we do not ask "when was Plant X built?" but "enumerate all thermal plants in Vietnam."
- **Limitations or critiques.** The non-parametric store (Wikipedia) is static; the retriever and reader are jointly optimized on QA datasets, making the approach less robust to domain shift (e.g., Vietnamese power sector documents). The evaluation benchmarks are all English-language, Western-world knowledge. The paper does not address the problem of incomplete retrieval when no single document covers all instances of an entity class.
- **Role in citation mix.** Seminal. The founding paper of the RAG paradigm.

### Gao et al. 2024 — RAG survey
*(new key: Gao-Yunfan2024:rag-survey)*

- **Reference.** Gao, Y., Xiong, Y., Gao, X., Jia, K., Pan, J., Bi, Y., Dai, Y., Sun, J., Wang, M., and Wang, H. (2024). Retrieval-Augmented Generation for Large Language Models: A Survey. arXiv:2312.10997. DOI: https://doi.org/10.48550/arXiv.2312.10997. (Preprint, submitted December 2023, revised March 2024.)
- **What the work did.** Surveys the RAG field as of early 2024. Organizes RAG variants into three paradigms — Naive RAG (basic retrieve-then-read), Advanced RAG (query rewriting, re-ranking, iterative retrieval), and Modular RAG (flexible pipelines with tool use, multi-step reasoning). Reviews over 100 papers; covers retrieval granularity, indexing strategies, embedding methods, and evaluation frameworks. Documents the standard evaluation benchmarks (NQ, TriviaQA, HotpotQA, MS-MARCO) and metrics (EM, F1, BLEU, faithfulness scores) used across the field.
- **Why this paragraph cites it.** The Gao survey is the canonical 2024 reference for the state of the RAG field. It supports the claim that RAG evaluation is organized around QA-accuracy benchmarks — NQ, TriviaQA, HotpotQA — and faithfulness/grounding metrics, not population-recall evaluation. A referee who asks "where do you show RAG is evaluated for QA, not entity enumeration?" can be directed to this survey's evaluation section.
- **Limitations or critiques.** Preprint only; no peer-reviewed journal publication confirmed as of 2026-04-20. The survey's "Advanced RAG" and "Modular RAG" categories blur together at the edges (some modular systems could be classified either way). The survey predates the agentic deep-research wave (2025+) and thus does not cover the most recent systems.
- **Role in citation mix.** Review/survey. Standard reference for the RAG landscape, covering the evaluation tradition.

### Asai et al. 2024 — Self-RAG (ICLR 2024 Oral)
*(new key: Asai-Akari2024:self-rag)*

- **Reference.** Asai, A., Wu, Z., Wang, Y., Sil, A., and Hajishirzi, H. (2024). Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection. *Proceedings of the Twelfth International Conference on Learning Representations (ICLR 2024)*. OpenReview: https://openreview.net/forum?id=hSyW5go0v8. arXiv:2310.11511. DOI: https://doi.org/10.48550/arXiv.2310.11511
- **What the work did.** Trains a single LM to (a) adaptively decide when to retrieve (not every token/query needs retrieval), (b) generate text conditioned on retrieved passages, and (c) critique its own output via four types of "reflection tokens" (IsRel, IsSup, IsUse, Retrieve). The model is trained end-to-end on data with these tokens. Evaluated on PopQA, TriviaQA, ARC challenge, ASQA (long-form QA), FactScore (factuality), and PubHealth (fact verification). Outperforms ChatGPT and RAG-augmented Llama2 on most tasks. Named an ICLR 2024 Oral (top 1%).
- **Why this paragraph cites it.** Self-RAG exemplifies the "quality/faithfulness improvement" direction: it enhances RAG by making retrieval selective and outputs self-critiqued. All evaluation benchmarks are QA or fact-verification tasks. The paper is an ideal counterpoint: it is the most sophisticated non-agentic RAG variant and yet still does not address entity enumeration — it improves *how* RAG generates answers, not *whether* a system has found all entities.
- **Limitations or critiques.** Self-RAG requires fine-tuning with reflection-token annotations; it is not a drop-in improvement for arbitrary LLMs. The reflection-token framework is specific to generation models (seq2seq or decoder); it does not transfer directly to retrieval pipelines over structured outputs. The selective retrieval heuristic is calibrated for QA tasks; whether it generalizes to an enumeration task (retrieve-all-relevant) is unexamined.
- **Role in citation mix.** Recent (2024, peer-reviewed at ICLR). Represents the state-of-the-art RAG quality frontier; its QA-only evaluation scope underscores the gap.

### Mialon et al. 2024 — GAIA benchmark (ICLR 2024)
*(new key: Mialon-Gregoire2024:gaia)*

- **Reference.** Mialon, G., Fourrier, C., Swift, C., Wolf, T., LeCun, Y., and Scialom, T. (2024). GAIA: a benchmark for General AI Assistants. *Proceedings of the Twelfth International Conference on Learning Representations (ICLR 2024)*. URL: https://proceedings.iclr.cc/paper_files/paper/2024/hash/25ae35b5b1738d80f1f03a8713e405ec-Abstract-Conference.html. arXiv:2311.12983. DOI: https://doi.org/10.48550/arXiv.2311.12983
- **What the work did.** Proposes 466 real-world questions that require multi-step reasoning, web browsing, multi-modality handling, and tool use. Questions are conceptually simple for humans (92% accuracy) but hard for advanced AI systems (GPT-4 with plugins: 15%). Evaluation metric is correctness of the final answer — whether the system retrieved and synthesized the right information. Three difficulty levels based on number of steps and modalities required. Provides a live leaderboard on Hugging Face. The benchmark represents the agentic evaluation frontier: systems must search the web and compose information, but correctness is still judged by single-answer accuracy.
- **Why this paragraph cites it.** GAIA represents the 2024 agentic deep-research evaluation tradition — the hardest general QA evaluation for web-browsing agents. Citing it lets us show that even the most demanding agentic benchmarks evaluate answer correctness (did the system find the right answer?), not population recall (did the system find *all* instances of an entity class?). GAIA questions like "what is the population of X?" or "who won Y?" are structurally different from our task "list all 163 thermal plants with capacity, fuel type, and commissioning year." The distinction is single-answer vs. population-enumeration.
- **Limitations or critiques.** GAIA is a curated benchmark with fixed questions and answers; the leaderboard introduces an implicit contamination risk (systems may be trained on GAIA-like tasks). It does not cover the open-enumeration task class. The 15% GPT-4 performance suggests the benchmark is genuinely hard for current systems, which makes it a useful comparator but also shows that the agentic frontier has not yet converged on easy-to-solve general tasks.
- **Role in citation mix.** Recent (2024, peer-reviewed at ICLR). Represents the agentic/deep-research evaluation frontier; its single-answer accuracy scope underscores the gap from our population-recall task.


## Related but not cited — justified

### Yan et al. 2024 — CRAG (Corrective Retrieval Augmented Generation)

- **Why not cited.** CRAG (arXiv:2401.15884) proposes a lightweight retrieval evaluator that triggers web-search fallback when retrieved documents are low-quality, plus a decompose-then-recompose algorithm for filtering noise. Evaluated on NQ, TriviaQA, HotPotQA, and FEVER — all QA tasks. CRAG is a close relative of Self-RAG in the quality-improvement direction and makes the same point (QA evaluation, not entity enumeration). Citing both Self-RAG and CRAG would be redundant for the specific claim this paragraph makes. Self-RAG is preferred because it is (a) the more complete methodological innovation (not just a plug-in corrector but a trained reflective model), (b) published at a top peer-reviewed venue (ICLR 2024 Oral vs. CRAG which remains a preprint), and (c) more cited in the field. CRAG is noted here as the primary excluded close relative; if a referee raises it, the response is that the QA-evaluation limitation it shares with Self-RAG is the point, and one representative citation suffices.

### Yao et al. 2023 — ReAct (Synergizing Reasoning and Acting in Language Models)

- **Why not cited.** ReAct (ICLR 2023, arXiv:2210.03629) introduces interleaved reasoning traces and tool-use actions for language models, evaluated on HotpotQA (QA) and FEVER (fact verification), plus interactive decision-making (ALFWorld, WebShop). ReAct is the intellectual predecessor of agentic deep-research systems and is widely cited as the paradigm for tool-augmented LLMs. However, it occupies an awkward position for this paragraph: it is neither purely a RAG paper nor a fully agentic deep-research paper. Its evaluation is pure QA/decision-making — which supports our claim — but citing ReAct in addition to the four selected references would exceed the citation budget without adding a new argument. The agentic line from ReAct to GAIA is implicit; the paragraph does not need to trace the full lineage. A referee who asks "what about ReAct?" can be directed to the agentic deep-research direction represented by GAIA.

### Izacard and Grave 2021 — Fusion-in-Decoder (FiD)

- **Why not cited.** FiD (arXiv:2007.01282, EACL 2021) extends RAG-style retrieval by independently encoding retrieved passages and fusing them in the decoder. It improves Open-domain QA (NQ, TriviaQA) significantly over the Lewis 2020 RAG baseline. FiD confirms the QA-evaluation paradigm but adds no new dimension to the claim this paragraph makes. Including it would pad the citation list with a second-tier technical variant when the point is already made by Lewis 2020 (seminal) and Gao 2024 (survey).

### Shi et al. 2023 — REPLUG (Retrieve and Plug)

- **Why not cited.** REPLUG (arXiv:2301.12652) treats the LM as a black box and plugs in retrieval as an external module, evaluated on language modeling perplexity and NQ. Still QA/perplexity evaluation. Same reasons as FiD — reinforces the existing claim without adding a new dimension.

### OpenAI Deep Research (2025) — commercial system

- **Why not cited.** OpenAI's Deep Research (2025) is a flagship commercial implementation of agentic web-search synthesis. It is referenced informally in the History section above as the leading system in the agentic wave, but it has no stable peer-reviewed publication to cite. The Y95UBRJ9 key in refs.bib points to a blog post. For a journal paper, the citation should be to a peer-reviewed evaluation that characterizes this class of system — GAIA serves that purpose. If a referee asks about the most advanced commercial systems, GAIA's leaderboard (which includes such systems) is the appropriate pointer.

### RAG-Fusion and HyDE

- **Why not cited.** RAG-Fusion (query rewriting + reciprocal rank fusion; various 2024 blog/tech reports) and Hypothetical Document Embeddings (HyDE; Gao et al. 2022, arXiv:2212.10496) are retrieval-improvement techniques evaluated on QA tasks. Both support the general claim (QA evaluation) but are technical variants, not field-defining papers. The Gao 2024 survey covers them as part of "Advanced RAG"; citing the survey makes individual technique citations redundant.

### REALM and Atlas — retrieval-augmented pre-training

- **Why not cited.** REALM (Guu et al. 2020, arXiv:2002.08909) and Atlas (Izacard et al. 2023, JMLR) embed retrieval into pre-training rather than inference only, evaluated on NQ and FEVER. These are alternative architectural choices for knowledge-intensive learning, not evaluation papers. They confirm the QA-evaluation paradigm but the paragraph's point is about evaluation tradition, not pre-training architecture. The survey covers them; citing individual papers would import unnecessary technical detail.


## Methods

**Searches run.** Primary searches on arXiv (title/abstract, cs.CL and cs.AI), ACL Anthology, NeurIPS/ICLR proceedings, and Semantic Scholar using queries: "Retrieval-Augmented Generation knowledge-intensive", "RAG survey 2024", "Self-RAG", "Corrective RAG", "CRAG retrieval", "GAIA benchmark AI assistant", "agentic deep research evaluation 2025", "deep research benchmark", "BrowseComp".

**Web search tool.** Tavily-backed web search used for 2024–2026 results (current date: 2026-04-20); searches run 2026-04-20.

**Snowballing.** Seeds: Lewis 2020 (ULQGRISS, known anchor from ticket 0077 scope); Gao 2024 survey (known anchor from ticket scope). Forward snowballing via Semantic Scholar and arXiv "cited by" for Lewis 2020 to identify canonical quality variants (Self-RAG, CRAG, FiD) and the agentic deep-research wave (GAIA, DeepResearcher, BrowseComp).

**Databases checked.** arXiv cs.CL and cs.AI, ACL Anthology, NeurIPS 2020 proceedings, ICLR 2024 proceedings (OpenReview), Semantic Scholar, ICLR virtual poster pages.

**Stop condition.** Stopped when three additional searches for "agentic RAG benchmark population recall" and "RAG entity enumeration evaluation" returned no papers evaluating RAG for exhaustive entity-population recall. The closest papers found (REALM, Atlas, KG-RAG) address knowledge-base population as a training objective, not as a benchmarking task.

**Inclusion rule.** Included if: (a) the paper proposes or defines an evaluation of RAG or agentic retrieval systems, AND (b) the paper's evaluation framing (QA accuracy, factual grounding, or report quality) can be clearly contrasted with population-recall evaluation.

**Freshness cutoff.** 2026-04-20. Agentic deep-research papers (2025–2026 wave) reviewed but not cited individually beyond GAIA because no single paper in this wave introduces a peer-reviewed benchmark that is both widely recognized and distinctly different from GAIA's framing. BrowseComp (OpenAI 2025) noted but not cited (blog post / technical report, no stable DOI).

**Preprint policy.** Gao 2024 survey is a preprint with no peer-reviewed journal version confirmed; included because it is the canonical community reference (thousands of citations, the standard survey for the RAG field). All other cited works have peer-reviewed conference versions (NeurIPS 2020, ICLR 2024×2).

**Identifier resolution log.**
- Lewis 2020: arXiv DOI `10.48550/arXiv.2005.11401` resolves to arXiv abstract; NeurIPS proceedings URL `https://proceedings.neurips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html` resolves. No separate NeurIPS DOI minted for this paper.
- Gao 2024: arXiv DOI `10.48550/arXiv.2312.10997` resolves to arXiv abstract. No journal DOI.
- Asai 2024: arXiv DOI `10.48550/arXiv.2310.11511` resolves. ICLR OpenReview URL `https://openreview.net/forum?id=hSyW5go0v8` confirmed via search (direct fetch returned 403, confirmed via ICLR virtual page at `https://iclr.cc/virtual/2024/oral/19736`). Proceedings PDF confirmed at `https://proceedings.iclr.cc/paper_files/paper/2024/file/25f7be9694d7b32d5cc670927b8091e1-Paper-Conference.pdf`.
- Mialon 2024: arXiv DOI `10.48550/arXiv.2311.12983` resolves. ICLR proceedings URL `https://proceedings.iclr.cc/paper_files/paper/2024/hash/25ae35b5b1738d80f1f03a8713e405ec-Abstract-Conference.html` confirmed via search result.

**LLM-assist disclosure.** Literature identification and DOI verification assisted by Claude Sonnet 4.6 with web search (Tavily). All entries cross-checked against primary arXiv, NeurIPS, and ICLR pages. Author must verify full texts before manuscript submission.


## Author verification checklist

- [ ] Read each cited primary source (not just abstract): Lewis 2020, Gao 2024 survey, Asai 2024 Self-RAG, Mialon 2024 GAIA
- [ ] Confirmed claim-to-citation mapping: each citation supports the distinction between QA-accuracy evaluation and population-recall evaluation
- [ ] Checked preprints for peer-reviewed updates (especially Gao 2024 survey, arXiv:2312.10997 — no journal version confirmed as of 2026-04-20)
- [ ] Agreed with "related but not cited" justifications (especially CRAG excluded in favor of Self-RAG; ReAct excluded as covered by GAIA's lineage)
- [ ] No in-repo docs cited in place of primary sources
- [ ] Confirmed ICLR 2024 Oral status for Self-RAG via `https://iclr.cc/virtual/2024/oral/19736`
- [ ] Confirmed ICLR 2024 conference paper status for GAIA via proceedings URL
- [ ] Verified Lewis 2020 key `ULQGRISS` matches existing refs.bib entry — reused, not duplicated


## Bibliography

```bibtex
@inproceedings{Asai-Akari2024:self-rag,
  author       = {Asai, Akari and Wu, Zeqiu and Wang, Yizhong and Sil, Avirup
                  and Hajishirzi, Hannaneh},
  title        = {{Self-RAG: Learning to Retrieve, Generate, and Critique through
                  Self-Reflection}},
  booktitle    = {Proceedings of the Twelfth International Conference on Learning
                  Representations},
  date         = {2024-05},
  url          = {https://openreview.net/forum?id=hSyW5go0v8},
  doi          = {10.48550/arXiv.2310.11511},
  eprint       = {2310.11511},
  eprinttype   = {arxiv},
}

@article{Gao-Yunfan2024:rag-survey,
  author       = {Gao, Yunfan and Xiong, Yun and Gao, Xinyu and Jia, Kangxiang
                  and Pan, Jinliu and Bi, Yuxi and Dai, Yi and Sun, Jiawei
                  and Wang, Meng and Wang, Haofen},
  title        = {{Retrieval-Augmented Generation for Large Language Models: A Survey}},
  journaltitle = {arXiv preprint},
  date         = {2024-03},
  doi          = {10.48550/arXiv.2312.10997},
  eprint       = {2312.10997},
  eprinttype   = {arxiv},
}

@article{Lewis-Patrick2020:rag,
  author       = {Lewis, Patrick and Perez, Ethan and Piktus, Aleksandra
                  and Petroni, Fabio and Karpukhin, Vladimir and Goyal, Naman
                  and K{\"u}ttler, Heinrich and Lewis, Mike and Yih, Wen-tau
                  and Rockt{\"a}schel, Tim and Riedel, Sebastian and Kiela, Douwe},
  title        = {{Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks}},
  journaltitle = {Advances in Neural Information Processing Systems},
  date         = {2020-12},
  volume       = {33},
  pages        = {9459--9474},
  doi          = {10.48550/arXiv.2005.11401},
  eprint       = {2005.11401},
  eprinttype   = {arxiv},
  note         = {Existing refs.bib key: ULQGRISS — reuse that key, do not add
                  this entry to refs.bib},
}

@inproceedings{Mialon-Gregoire2024:gaia,
  author       = {Mialon, Gr{\'e}goire and Fourrier, Cl{\'e}mentine
                  and Swift, Craig and Wolf, Thomas and LeCun, Yann
                  and Scialom, Thomas},
  title        = {{GAIA: a benchmark for General AI Assistants}},
  booktitle    = {Proceedings of the Twelfth International Conference on Learning
                  Representations},
  date         = {2024-05},
  url          = {https://proceedings.iclr.cc/paper_files/paper/2024/hash/25ae35b5b1738d80f1f03a8713e405ec-Abstract-Conference.html},
  doi          = {10.48550/arXiv.2311.12983},
  eprint       = {2311.12983},
  eprinttype   = {arxiv},
}
```

**Note on Lewis 2020:** The existing refs.bib entry uses key `ULQGRISS` and has `@article` type with the NeurIPS year 2021 (the proceedings volume was published in 2021). Reuse that key in the manuscript. The bibliography entry above is for reference completeness; do **not** add a duplicate entry to refs.bib.
