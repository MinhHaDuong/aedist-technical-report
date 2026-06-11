---
title: Capability ladder — articulation, coverage, reasoning, tool-use, retroactivity, agency
author: Claude prompted by Ha-Duong Minh
date: 2026-05-21
paper: slides/manuscript/main.tex
section: §3 Capability ladder (lines 39–50)
citation-budget: 12–15
---

## Relevance

The paragraph narrates the recent capability progression of LLM systems through six limits — articulation, coverage, reasoning, tool-use, retroactivity, agency — and the corresponding industry trajectory from interactive chatbots through RAG + web access + reasoning to deep-research agents. It is the historical chassis of the manuscript: a referee who reads this paragraph must come away with anchors for *each* named capability layer. The citation budget is therefore overcommitted — the task brief lists ~15 topic areas alone, before related-but-not-cited. The note prioritises one canonical paper per named capability, plus one or two recent benchmarks per evaluation cluster (reasoning, deep-research, agentic).

## History of science context

The recent history compresses three earlier traditions.

**Prompting and articulation.** The "prompt engineering" practice descends from the IR query-formulation problem and from human–computer interaction studies of intent-elicitation. The contemporary form is documented in Brown et al. 2020 GPT-3 + few-shot prompting, refined by Wei et al. 2022 chain-of-thought, and operationalised by Khattab et al. 2023 DSPy (programmatic prompt optimisation). The articulation limit links conceptually to the Type-III error in statistics — "solving the wrong problem" (Kimball 1957; Mitroff & Featheringham 1974) — though the LLM-specific instantiation is not formalised in those terms in the published literature.

**Coverage and retrieval-augmented generation.** Lewis et al. 2020 introduced RAG as a paradigm; the field has since exploded through evaluation benchmarks (RAGAS, RAGTruth), variants (Self-RAG, Chain-of-Note), and surveys (Gao et al. 2024). The "coverage" framing maps to the canonical retrieval-recall metric.

**Reasoning.** Chain-of-thought (Wei et al. 2022) and self-consistency (Wang et al. 2022) opened the practice; the recent reasoning-model wave (OpenAI o1, DeepSeek R1) is measured against MATH (Hendrycks et al. 2021), GPQA (Rein et al. 2023), and ARC (Chollet 2019).

**Tool-use, retroactivity, agency.** ReAct (Yao et al. 2022) framed reasoning + acting; the benchmarks SWE-Bench (Jimenez et al. 2024), HumanEval (Chen et al. 2021), GAIA (Mialon et al. 2024), BrowseComp (Wei et al. 2025), and OSWorld (Xie et al. 2024) measure progress from coding through web-browsing to GUI manipulation. Recent surveys (Wang et al. 2023, Minaee et al. 2024) consolidate.

The opposing view: capability progress is uneven, benchmark-driven, and prone to gaming. Critics argue that benchmark improvements do not translate to real-world task performance — the gap between SWE-Bench and a working software-engineering deployment, between GAIA and a working general assistant. The manuscript implicitly accepts this critique by running its own task-specific experiments in §1 and §4.

## Cited works — detailed

### Wei et al. 2022 — Chain-of-Thought prompting
- **Reference.** Wei, J.; Wang, X.; Schuurmans, D. et al. *Chain-of-Thought Prompting Elicits Reasoning in Large Language Models*. NeurIPS 2022. arXiv:2201.11903.
- **What the work did.** Demonstrated that prepending reasoning steps to in-context examples elicits multi-step reasoning in large models.
- **Why this paragraph cites it.** Field-defining anchor for the **Reasoning** capability ("Models are trained to produce a chain of thought before generating the answer").
- **Limitations or critiques.** Works best on large models; downstream reasoning models embed this implicitly via training rather than prompting.

### Lewis et al. 2020 — RAG
- **Reference.** Lewis, P.; Perez, E.; Piktus, A. et al. *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. NeurIPS 2020. arXiv:2005.11401.
- **What the work did.** Introduced RAG: parametric seq2seq + non-parametric vector index over Wikipedia.
- **Why this paragraph cites it.** Field-defining anchor for the **Coverage** capability ("Retrieval-augmented generation (RAG) feeds the model relevant passages from a closed pool of documents").
- **Limitations or critiques.** Static index; the modern "web access" variant generalises by allowing dynamic retrieval. The paragraph notes both.

### Gao et al. 2024 — RAG survey
- **Reference.** Gao, Y.; Xiong, Y.; Gao, X. et al. *Retrieval-Augmented Generation for Large Language Models: A Survey*. arXiv:2312.10997, 2024. (Existing key `Gao-Yunfan2024:rag-survey`.)
- **What the work did.** Comprehensive RAG survey covering Naive, Advanced, and Modular variants.
- **Why this paragraph cites it.** Recent-survey anchor for the **Coverage** capability layer.
- **Limitations or critiques.** Pre-deep-research wave; agentic RAG variants underrepresented.

### Yao et al. 2023 — ReAct
- **Reference.** Yao, S.; Zhao, J.; Yu, D. et al. *ReAct: Synergizing Reasoning and Acting in Language Models*. ICLR 2023. arXiv:2210.03629.
- **What the work did.** Interleaved reasoning traces with action calls (Wikipedia / web search); reduced hallucination via tool grounding.
- **Why this paragraph cites it.** Anchor for the **Tool-use** capability and the conjunction of reasoning + web access that the paragraph names as the "deep research" predecessor.
- **Limitations or critiques.** Small-task focus (HotpotQA, ALFWorld); the contemporary deep-research agent stack is heavier.

### Mialon et al. 2024 — GAIA
- **Reference.** Mialon, G.; Fourrier, C.; Swift, C. et al. *GAIA: a benchmark for General AI Assistants*. ICLR 2024. arXiv:2311.12983. (Existing key `Mialon-Gregoire2024:gaia`.)
- **What the work did.** 466-question benchmark for AI assistants requiring tool use, multimodality, and multi-hop reasoning.
- **Why this paragraph cites it.** Anchor for the **Tool-use** and **Agency** evaluation cluster — the deep-research-era benchmark for general assistant capability.
- **Limitations or critiques.** Tasks are diverse but not statistically grounded — does not measure quality of structured outputs in the way our task requires.

### Wei et al. 2024 — SimpleQA
- **Reference.** Wei, J.; Nguyen, K.; Chung, H.W. et al. *Measuring Short-Form Factuality in Large Language Models*. arXiv:2411.04368, 2024.
- **What the work did.** Adversarial benchmark of short-answer factuality grades models on correct / incorrect / not-attempted.
- **Why this paragraph cites it.** Anchor for the **Coverage** + **Articulation** evaluation point — measures whether models "know what they know" without retrieval.
- **Limitations or critiques.** Short-form only; complementary to BrowseComp and GAIA which test the agentic side.

### Wei et al. 2025 — BrowseComp
- **Reference.** Wei, J.; Sun, Z.; Papay, S. et al. *BrowseComp: A Simple Yet Challenging Benchmark for Browsing Agents*. arXiv:2504.12516, 2025.
- **What the work did.** 1266 questions requiring persistent web-browsing to find hard-to-locate, entangled information.
- **Why this paragraph cites it.** Recent frontier anchor for the **Agency** + **Coverage** combined capability — the deep-research benchmark that operationalises the paragraph's "deep research" claim.
- **Limitations or critiques.** Short-answer outputs; does not measure structured-table generation.

### Hendrycks et al. 2021 — MATH
- **Reference.** Hendrycks, D.; Burns, C.; Kadavath, S. et al. *Measuring Mathematical Problem Solving With the MATH Dataset*. NeurIPS 2021. arXiv:2103.03874.
- **What the work did.** 12,500 competition math problems with step-by-step solutions; widely-used reasoning benchmark.
- **Why this paragraph cites it.** Anchor for the **Reasoning** capability layer's measurement — the canonical hard-reasoning benchmark cited by every reasoning-model release.
- **Limitations or critiques.** Math-specific; reasoning-model claims need GPQA + ARC to span the breadth.

### Rein et al. 2023 — GPQA
- **Reference.** Rein, D.; Hou, B.L.; Cooper Stickland, A. et al. *GPQA: A Graduate-Level Google-Proof Q&A Benchmark*. arXiv:2311.12022.
- **What the work did.** 448 expert-curated graduate-level science questions, deliberately resistant to web-search.
- **Why this paragraph cites it.** Anchor for the **Reasoning** capability under no-retrieval conditions — directly relevant to our parametric baseline (§1 also runs no-web).
- **Limitations or critiques.** Multiple-choice format; the open-world generation case our task represents is harder.

### Chollet 2019 — On the Measure of Intelligence (ARC)
- **Reference.** Chollet, F. *On the Measure of Intelligence*. arXiv:1911.01547, 2019.
- **What the work did.** Introduced ARC (Abstraction and Reasoning Corpus); proposed an intelligence definition grounded in algorithmic information theory.
- **Why this paragraph cites it.** Field-defining anchor for the broadest sense of **Reasoning** capability — establishes the generalisation-from-priors metric that ARC-AGI continues to operationalise.
- **Limitations or critiques.** ARC is a specific format; reasoning-model claims on ARC are partial evidence at best.

### Jimenez et al. 2024 — SWE-Bench
- **Reference.** Jimenez, C.E.; Yang, J.; Wettig, A. et al. *SWE-bench: Can Language Models Resolve Real-World GitHub Issues?* ICLR 2024. arXiv:2310.06770.
- **What the work did.** 2,294 real GitHub issues from 12 Python repos; resolution rate of the best 2023 model: 1.96%.
- **Why this paragraph cites it.** Anchor for the **Agency** capability — coding-as-evaluation for autonomous software-engineering agents.
- **Limitations or critiques.** Coding-domain-specific; gameable through training-data contamination.

### Xie et al. 2024 — OSWorld
- **Reference.** Xie, T.; Zhang, D.; Chen, J. et al. *OSWorld: Benchmarking Multimodal Agents for Open-Ended Tasks in Real Computer Environments*. arXiv:2404.07972, 2024.
- **What the work did.** 369 tasks in real OS environments (Linux/Windows/macOS); humans 72%, best AI 12%.
- **Why this paragraph cites it.** Anchor for the **Agency** capability at full GUI/OS scope — measures the operational gap between agentic claims and working systems.
- **Limitations or critiques.** Recent; results will move quickly.

### Khattab et al. 2023 — DSPy
- **Reference.** Khattab, O.; Singhvi, A.; Maheshwari, P. et al. *DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines*. arXiv:2310.03714, 2023.
- **What the work did.** Programming framework for compiling LM pipelines; treats prompts as optimisable artifacts.
- **Why this paragraph cites it.** Operationalisation of the **Articulation** limit — automated prompt optimisation makes the limit measurable and partially closable.
- **Limitations or critiques.** Programming-language-shaped; not a free-form articulation aid.

## Related but not cited — justified

### Brown et al. 2020 — GPT-3 / few-shot prompting
arXiv:2005.14165. The ancestor of prompting practice. Implicit throughout the paragraph; citing it would dilute the budget without naming a specific capability the paragraph identifies. Saved for any future "prompting as paradigm" footnote.

### Wang et al. 2022 — Self-consistency
Cited in §1 and §2; redundant here.

### Es et al. 2023 — RAGAS / Niu et al. 2023 — RAGTruth / Asai et al. 2024 — Self-RAG
All cited in §2 (provenance dimension). The paragraph names RAG and reasoning as capability layers; the RAG-evaluation sub-literature is more specific than the paragraph claims and belongs in §2.

### Wang et al. 2023 — LLM-agent survey
arXiv:2308.11432. Comprehensive but the survey-as-anchor budget is filled by Gao et al. 2024 (RAG) and the GAIA/BrowseComp pair for agency. Saved for further reading.

### Mitroff & Featheringham 1974 — Type-III error
Pre-print-era; no clean DOI. The Type-III link to Articulation is conceptually correct but not load-bearing for the paragraph. Worth a footnote, not a citation in the budget.

### Mixture-of-Agents (Wang et al. 2024) / Agent-as-a-Judge (Zhuge et al. 2024) / MT-Bench (Zheng et al. 2023)
These belong in §4 (SOTA comparison protocols) where multi-agent and judge methodologies are load-bearing.

## Methods

- **Search seeds.** Manuscript paragraph; task brief enumeration of capability layers and benchmark anchors; existing `refs.bib` (Gao RAG survey, GAIA, Self-RAG, MMLU already present).
- **Databases.** arXiv (primary), DOI resolver, ACL/NeurIPS/ICLR proceedings via arXiv IDs.
- **Stop condition.** 13 entries cited + 6 in related-but-not-cited. The task brief listed 15+ anchor topics; cuts documented above. Each named capability has at least one anchor.
- **Inclusion rule.** Must (a) define a named capability on the ladder, or (b) be the canonical evaluation benchmark for one of them.
- **Exclusion rule.** Foundational papers without a capability-layer mapping (e.g., GPT-3 the *model*) are saved for future footnotes.
- **Freshness cutoff.** 2026-05-21.
- **Preprint policy.** BrowseComp is arXiv-only (April 2025) — too new for venue; cited as preprint. SimpleQA likewise. Acceptable per `writing.md` since both are recent frontier-anchor work.
- **Grey-literature policy.** No grey literature cited here — the capability-ladder anchors are all peer-reviewed or canonically-citable preprints.
- **Identifier resolution log.** WebFetched and resolved: 2201.11903 (CoT ✓); 2005.11401 (RAG ✓); 2210.03629 (ReAct ✓); 2103.03874 (MATH ✓); 2311.12022 (GPQA ✓); 1911.01547 (Chollet ARC ✓); 2310.06770 (SWE-Bench ✓); 2404.07972 (OSWorld ✓); 2310.03714 (DSPy ✓); 2411.04368 (SimpleQA ✓); 2504.12516 (BrowseComp ✓); 2308.11432 (LLM-agent survey, not-cited ✓); existing keys (Gao-Yunfan2024:rag-survey, Mialon-Gregoire2024:gaia, Hendrycks-Dan2021:mmlu) reused without re-resolution. Codex / HumanEval (2107.03374) was resolved but dropped — the paragraph names HumanEval at a clause level that does not warrant its own detailed cited-works block within the budget; if the manuscript pulls HumanEval to a binding clause, re-add then.
- **LLM-assist disclosure.** Drafted by Claude (Opus 4.7) under ticket 0151. WebFetch used for identifier resolution.

## Author verification checklist

- [ ] Read each cited primary source (not just abstract)
- [ ] Confirmed claim-to-citation mapping
- [ ] Checked preprints for peer-reviewed updates
- [ ] Agreed with "related but not cited" justifications
- [ ] No in-repo docs cited in place of primary sources

## Bibliography

```bibtex
@misc{Chollet-Francois2019:arc,
  author       = {Chollet, Fran{\c{c}}ois},
  title        = {{On the Measure of Intelligence}},
  date         = {2019-11},
  eprint       = {1911.01547},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.1911.01547},
}

@article{Gao-Yunfan2024:rag-survey,
  author       = {Gao, Yunfan and Xiong, Yun and Gao, Xinyu and Jia, Kangxiang
                  and Pan, Jinliu and Bi, Yuxi and Dai, Yi and Sun, Jiawei
                  and Wang, Meng and Wang, Haofen},
  title        = {{Retrieval-Augmented Generation for Large Language Models: A Survey}},
  journaltitle = {arXiv preprint},
  date         = {2024},
  doi          = {10.48550/arXiv.2312.10997},
  eprint       = {2312.10997},
  eprinttype   = {arxiv},
}

@inproceedings{Hendrycks-Dan2021:math,
  author       = {Hendrycks, Dan and Burns, Collin and Kadavath, Saurav and Arora, Akul
                  and Basart, Steven and Tang, Eric and Song, Dawn and Steinhardt, Jacob},
  title        = {{Measuring Mathematical Problem Solving With the MATH Dataset}},
  booktitle    = {Proceedings of the 35th Conference on Neural Information Processing
                  Systems Track on Datasets and Benchmarks},
  date         = {2021},
  eprint       = {2103.03874},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.2103.03874},
}

@inproceedings{Jimenez-Carlos2024:swe-bench,
  author       = {Jimenez, Carlos E. and Yang, John and Wettig, Alexander
                  and Yao, Shunyu and Pei, Kexin and Press, Ofir
                  and Narasimhan, Karthik},
  title        = {{SWE-bench: Can Language Models Resolve Real-World GitHub Issues?}},
  booktitle    = {Proceedings of the Twelfth International Conference on Learning
                  Representations},
  date         = {2024},
  eprint       = {2310.06770},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.2310.06770},
}

@misc{Khattab-Omar2023:dspy,
  author       = {Khattab, Omar and Singhvi, Arnav and Maheshwari, Paridhi
                  and Zhang, Zhiyuan and Santhanam, Keshav and Vardhamanan, Sri
                  and Haq, Saiful and Sharma, Ashutosh and Joshi, Thomas T.
                  and Moazam, Hanna and Miller, Heather and Zaharia, Matei
                  and Potts, Christopher},
  title        = {{DSPy: Compiling Declarative Language Model Calls into
                  Self-Improving Pipelines}},
  date         = {2023-10},
  eprint       = {2310.03714},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.2310.03714},
}

@inproceedings{Lewis-Patrick2020:rag,
  author       = {Lewis, Patrick and Perez, Ethan and Piktus, Aleksandra
                  and Petroni, Fabio and Karpukhin, Vladimir and Goyal, Naman
                  and K{\"u}ttler, Heinrich and Lewis, Mike and Yih, Wen-tau
                  and Rockt{\"a}schel, Tim and Riedel, Sebastian and Kiela, Douwe},
  title        = {{Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks}},
  booktitle    = {Proceedings of the 34th International Conference on Neural
                  Information Processing Systems},
  date         = {2020},
  eprint       = {2005.11401},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.2005.11401},
}

@inproceedings{Mialon-Gregoire2024:gaia,
  author       = {Mialon, Gr{\'e}goire and Fourrier, Cl{\'e}mentine
                  and Swift, Craig and Wolf, Thomas and LeCun, Yann
                  and Scialom, Thomas},
  title        = {{GAIA: a benchmark for General AI Assistants}},
  booktitle    = {Proceedings of the Twelfth International Conference on Learning
                  Representations},
  date         = {2024},
  url          = {https://proceedings.iclr.cc/paper_files/paper/2024/hash/25ae35b5b1738d80f1f03a8713e405ec-Abstract-Conference.html},
  doi          = {10.48550/arXiv.2311.12983},
  eprint       = {2311.12983},
  eprinttype   = {arxiv},
}

@misc{Rein-David2023:gpqa,
  author       = {Rein, David and Hou, Betty Li and Cooper Stickland, Asa
                  and Petty, Jackson and Pang, Richard Yuanzhe and Dirani, Julien
                  and Michael, Julian and Bowman, Samuel R.},
  title        = {{GPQA: A Graduate-Level Google-Proof Q\&A Benchmark}},
  date         = {2023-11},
  eprint       = {2311.12022},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.2311.12022},
}

@inproceedings{Wei-Jason2022:cot,
  author       = {Wei, Jason and Wang, Xuezhi and Schuurmans, Dale and Bosma, Maarten
                  and Ichter, Brian and Xia, Fei and Chi, Ed and Le, Quoc and Zhou, Denny},
  title        = {{Chain-of-Thought Prompting Elicits Reasoning in Large Language Models}},
  booktitle    = {Proceedings of the 36th Conference on Neural Information Processing
                  Systems},
  date         = {2022},
  eprint       = {2201.11903},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.2201.11903},
}

@misc{Wei-Jason2024:simpleqa,
  author       = {Wei, Jason and Nguyen, Karina and Chung, Hyung Won and Jiao, Yunxin Joy
                  and Papay, Spencer and Glaese, Amelia and Schulman, John and Fedus, William},
  title        = {{Measuring short-form factuality in large language models}},
  date         = {2024-11},
  eprint       = {2411.04368},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.2411.04368},
}

@misc{Wei-Jason2025:browsecomp,
  author       = {Wei, Jason and Sun, Zhiqing and Papay, Spencer and McKinney, Scott
                  and Han, Jeffrey and Fulford, Isa and Chung, Hyung Won
                  and Tachard Passos, Alex and Fedus, William and Glaese, Amelia},
  title        = {{BrowseComp: A Simple Yet Challenging Benchmark for Browsing Agents}},
  date         = {2025-04},
  eprint       = {2504.12516},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.2504.12516},
}

@misc{Xie-Tianbao2024:osworld,
  author       = {Xie, Tianbao and Zhang, Danyang and Chen, Jixuan and Li, Xiaochuan
                  and Zhao, Siheng and Cao, Ruisheng and Hua, Toh Jing and Cheng, Zhoujun
                  and Shin, Dongchan and Lei, Fangyu and Liu, Yitao and Xu, Yiheng
                  and Zhou, Shuyan and Savarese, Silvio and Xiong, Caiming
                  and Zhong, Victor and Yu, Tao},
  title        = {{OSWorld: Benchmarking Multimodal Agents for Open-Ended Tasks in
                   Real Computer Environments}},
  date         = {2024-04},
  eprint       = {2404.07972},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.2404.07972},
}

@inproceedings{Yao-Shunyu2023:react,
  author       = {Yao, Shunyu and Zhao, Jeffrey and Yu, Dian and Du, Nan
                  and Shafran, Izhak and Narasimhan, Karthik and Cao, Yuan},
  title        = {{ReAct: Synergizing Reasoning and Acting in Language Models}},
  booktitle    = {Proceedings of the Eleventh International Conference on Learning
                  Representations},
  date         = {2023},
  eprint       = {2210.03629},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.2210.03629},
}
```
