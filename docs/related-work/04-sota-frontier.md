---
title: SOTA frontier — three-agent deep-research comparison, cross-model pairwise evaluation
author: Claude prompted by Ha-Duong Minh
date: 2026-05-21
paper: slides/manuscript/main.md
section: §4 SOTA frontier (lines 52–54)
citation-budget: 10–12
---

## Relevance

The paragraph proposes the second empirical experiment: select three state-of-the-art cloud AI agents with extended reasoning + web access, let each tune its own prompt within a $10 / overnight budget, run the tuned prompt three times per model with different providers, and have each non-author model judge the other two's outputs (cross-model pairwise comparison) plus the §1 naive baseline. The conjecture is that SOTA improves all four quality dimensions but falls short of scientific quality. The note must anchor (a) the deep-research agent literature (OpenAI, Anthropic, Google offerings; recent academic deep-research benchmarks), (b) LLM-as-a-judge / agent-as-a-judge evaluation protocols, (c) multi-agent comparison methodologies, and (d) the frontier-eval limitations literature that justifies running the experiment at all. The paragraph is three sentences; the note's risk is over-citing.

## History of science context

Three converging strands.

**Deep-research as a product category.** Late 2024 / early 2025 saw simultaneous launches of "deep research" agents by OpenAI, Anthropic, and Google. The product-side documentation is grey literature; the academic benchmarks that catch up are BrowseComp (Wei et al. 2025) and the academic deep-research methodology papers (Wu et al. 2025 Agentic Reasoning). Earlier ancestor frameworks include ReAct (Yao et al. 2023), AutoGen (Wu et al. 2023), and the Mixture-of-Agents stack (Wang et al. 2024).

**Cross-model judgement.** The "let model X judge model Y's output" paradigm starts with Zheng et al. 2023 (MT-Bench / Chatbot Arena LLM-as-a-Judge), establishing that GPT-4 achieves >80% agreement with crowdsourced human preferences. Zhuge et al. 2024 extended this to agent-as-a-judge, with intermediate feedback through task-solving rather than only endpoint scoring. Known biases (position, verbosity, self-enhancement) are catalogued in MT-Bench and have shaped the design space.

**Tuned-prompt-per-model comparison.** Allowing each model to tune its own prompt is closer to the DSPy programme (Khattab et al. 2023, Soylu et al. 2024) than to standard benchmarking, where the prompt is held fixed. The rationale is fairness: comparing models on the same prompt advantages the prompt's natural recipient. The trade-off is that "model + prompt" is the unit of comparison, not "model" alone.

The opposing view: capability-frontier evaluation is gameable, leak-prone, and not generalisable. Critics argue that public deep-research benchmarks (GAIA, BrowseComp) are already feeding back into model training, and that single-task evaluations like ours are necessary precisely because they are not pre-anticipated by the labs. Our experiment positions itself in that gap.

## Cited works — detailed

### Mialon et al. 2024 — GAIA
- **Reference.** Mialon, G.; Fourrier, C. et al. *GAIA: a benchmark for General AI Assistants*. ICLR 2024. (Existing key `Mialon-Gregoire2024:gaia`.)
- **What the work did.** Benchmark of 466 questions requiring tool use, multimodality, and multi-hop reasoning for AI assistants.
- **Why this paragraph cites it.** Closest in spirit to the §4 task — measures general-assistant capability that includes the kind of multi-hop, multi-source synthesis our power-plant census requires.
- **Limitations or critiques.** Question-answering format; does not measure structured-output quality. The complement, not the competitor.

### Wei et al. 2025 — BrowseComp
- **Reference.** Wei, J.; Sun, Z. et al. *BrowseComp: A Simple Yet Challenging Benchmark for Browsing Agents*. arXiv:2504.12516, 2025.
- **What the work did.** 1,266 questions requiring deep browsing for entangled information.
- **Why this paragraph cites it.** Reference benchmark for the **deep-research / web-access** capability axis tested in §4. Our task is structurally similar (find dispersed information online) but produces a structured artefact rather than a short answer.
- **Limitations or critiques.** Short-answer outputs; cannot evaluate provenance accuracy at scale.

### Wu et al. 2025 — Agentic Reasoning
- **Reference.** Wu, J.; Zhu, J.; Liu, Y.; Xu, M.; Jin, Y. *Agentic Reasoning: A Streamlined Framework for Enhancing LLM Reasoning with Agentic Tools*. ACL 2025. arXiv:2502.04644.
- **What the work did.** Framework integrating reasoning, web-search, code-execution, and a Mind-Map memory; achieves "comparable to OpenAI's Deep Research" on public-model baselines.
- **Why this paragraph cites it.** Recent frontier work that explicitly benchmarks against OpenAI's deep-research product; relevant to the conjecture that tailored stacks can approach SOTA. Bridges §4 and §5.
- **Limitations or critiques.** Synthetic benchmarks; no extraction-of-structured-data evaluation.

### Wu et al. 2023 — AutoGen
- **Reference.** Wu, Q.; Bansal, G. et al. *AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation*. arXiv:2308.08155, 2023.
- **What the work did.** Open-source multi-agent conversation framework; reference architecture for the three-agent experimental setup.
- **Why this paragraph cites it.** Methodological anchor for the **three-agent** experimental design. Provides the conversational-agent stack our cross-model comparison can be cast against.
- **Limitations or critiques.** Software framework rather than evaluation; we adopt the pattern, not the implementation.

### Wang et al. 2024 — Mixture-of-Agents
- **Reference.** Wang, J.; Wang, J.; Athiwaratkun, B.; Zhang, C.; Zou, J. *Mixture-of-Agents Enhances Large Language Model Capabilities*. arXiv:2406.04692, 2024.
- **What the work did.** Layered multi-LLM architecture; combining open-source LLMs outperforms GPT-4 Omni on AlpacaEval 2.0 (65.1% vs 57.5%).
- **Why this paragraph cites it.** Recent frontier anchor for the **multi-agent comparison** methodology — when agents stack, the unit of analysis is the ensemble. Justifies why our cross-model judging is interesting rather than redundant.
- **Limitations or critiques.** Open-ended conversation tasks; not extraction-shaped.

### Zheng et al. 2023 — LLM-as-a-Judge (MT-Bench)
- **Reference.** Zheng, L.; Chiang, W.-L. et al. *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*. NeurIPS 2023 Datasets and Benchmarks. arXiv:2306.05685.
- **What the work did.** Established GPT-4-as-judge with >80% agreement with humans; catalogued position, verbosity, self-enhancement biases.
- **Why this paragraph cites it.** Field-defining anchor for the **cross-model judgement** methodology. Provides the bias taxonomy our protocol needs to control.
- **Limitations or critiques.** Chat-quality preferences, not factual correctness. Our §4 setup needs additional safeguards on factual evaluation.

### Zhuge et al. 2024 — Agent-as-a-Judge
- **Reference.** Zhuge, M.; Zhao, C. et al. *Agent-as-a-Judge: Evaluate Agents with Agents*. arXiv:2410.10934, 2024.
- **What the work did.** Extended LLM-as-judge to evaluate intermediate agent behaviour; DevAI benchmark for development tasks; outperforms LLM-as-judge.
- **Why this paragraph cites it.** Recent frontier anchor for the **agent-judging** methodology. Closer to our use case than text-output judging because deep-research agents produce intermediate artefacts (search traces, draft tables) that benefit from process evaluation.
- **Limitations or critiques.** Software-development domain; our domain (asset inventories) is unstudied.

### Soylu et al. 2024 — BetterTogether (DSPy weights + prompts)
- **Reference.** Soylu, D.; Potts, C.; Khattab, O. *Fine-Tuning and Prompt Optimization: Two Great Steps that Work Better Together*. EMNLP 2024. arXiv:2407.10930.
- **What the work did.** DSPy extension co-optimising prompts and weights; reports 60% / 6% gains.
- **Why this paragraph cites it.** Closest peer for the **let-each-model-tune-its-own-prompt** design point. Justifies that fairness across models requires per-model prompt adaptation.
- **Limitations or critiques.** Their setup co-optimises weights — we let prompts adapt only.

### Yao et al. 2023 — ReAct
- **Reference.** Yao, S.; Zhao, J. et al. *ReAct: Synergizing Reasoning and Acting*. ICLR 2023.
- **What the work did.** Interleaved reasoning + acting; foundational for deep-research-style agents.
- **Why this paragraph cites it.** Ancestor architecture for the deep-research agents §4 evaluates. Cited to give the historical line from ReAct → AutoGen → deep-research products.
- **Limitations or critiques.** Already discussed in §3.

### Khattab et al. 2023 — DSPy
- **Reference.** Khattab, O.; Singhvi, A. et al. *DSPy*. arXiv:2310.03714, 2023.
- **What the work did.** Programming framework for compiling LM pipelines.
- **Why this paragraph cites it.** Anchors the **prompt-as-program** view that motivates per-model prompt tuning in our protocol.
- **Limitations or critiques.** Already discussed in §3.

## Related but not cited — justified

### OpenAI / Anthropic / Google deep-research product pages
The product-side documentation (OpenAI Deep Research launch post, Anthropic's Computer Use, Google Deep Research) is grey literature without DOIs. WebFetch returned 403 on the OpenAI page. Cited in slides via URL when needed; not appropriate for the paper's bibliography per `writing.md` ("no in-repo doc references").

### Wang et al. 2023 — LLM-agent survey
arXiv:2308.11432. Comprehensive but too broad; the agent-as-a-judge sub-literature is more directly relevant here than the agent-architecture survey.

### Minaee et al. 2024 — LLM survey
arXiv:2402.06196. General LLM survey; cited in §3 not-cited. Not load-bearing for §4.

### Maharana et al. 2024 — LoCoMo
arXiv:2402.17753. Long-term conversational memory benchmark. Relevant to §5 stateful systems; not to the SOTA comparison protocol.

### Tenckhoff et al. 2026 — LLMStructBench
Cited in §1 and §2. Structured-extraction benchmark; relevant to the *quality measurement* of §4 outputs, not to the SOTA comparison design itself.

### Hubinger et al. 2024 — Sleeper Agents
arXiv:2401.05566. Deceptive backdoors persist through safety training. Relevant if §4 discusses adversarial reliability; the manuscript stays factual-quality-focused, so out of scope.

## Methods

- **Search seeds.** Manuscript paragraph; the §3 capability-ladder anchors (BrowseComp, GAIA, ReAct, DSPy) carry over; the agent-as-judge sub-literature was added from MT-Bench → Agent-as-a-Judge.
- **Databases.** arXiv (primary), DOI resolver. Product pages (OpenAI, Anthropic, Google) blocked at WebFetch.
- **Stop condition.** 10 entries cited + 6 in not-cited. Short paragraph; deeper anchors live in §3 and §5.
- **Inclusion rule.** Must (a) anchor a deep-research agent system, (b) anchor a judgement-protocol methodology, or (c) anchor the multi-agent comparison paradigm.
- **Exclusion rule.** Surveys of generic agent capability without an evaluation contribution.
- **Freshness cutoff.** 2026-05-21.
- **Preprint policy.** Several anchors are arXiv-only (AutoGen, Mixture-of-Agents, Agent-as-a-Judge, Agentic Reasoning, Soylu DSPy, BrowseComp). Acceptable per recency.
- **Grey-literature policy.** No grey-literature citations in this note. Product-page deep-research references are noted in not-cited and will be cited inline via URL in the manuscript if necessary, not in the bibliography.
- **Identifier resolution log.** WebFetched and resolved: 2308.08155 (AutoGen ✓); 2502.04644 (Agentic Reasoning ✓); 2406.04692 (Mixture-of-Agents ✓); 2410.10934 (Agent-as-a-Judge ✓); 2306.05685 (MT-Bench ✓); 2407.10930 (BetterTogether ✓); existing keys (Mialon, BrowseComp from §3 batch, ReAct from §3 batch, DSPy from §3 batch) reused without re-resolution.
- **LLM-assist disclosure.** Drafted by Claude (Opus 4.7) under ticket 0151. WebFetch used for identifier resolution.

## Author verification checklist

- [ ] Read each cited primary source (not just abstract)
- [ ] Confirmed claim-to-citation mapping
- [ ] Checked preprints for peer-reviewed updates
- [ ] Agreed with "related but not cited" justifications
- [ ] No in-repo docs cited in place of primary sources

## Bibliography

```bibtex
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

@inproceedings{Mialon-Gregoire2024:gaia,
  author       = {Mialon, Gr{\'e}goire and Fourrier, Cl{\'e}mentine
                  and Swift, Craig and Wolf, Thomas and LeCun, Yann
                  and Scialom, Thomas},
  title        = {{GAIA: a benchmark for General AI Assistants}},
  booktitle    = {Proceedings of the Twelfth International Conference on Learning
                  Representations},
  date         = {2024},
  doi          = {10.48550/arXiv.2311.12983},
  eprint       = {2311.12983},
  eprinttype   = {arxiv},
}

@inproceedings{Soylu-Dilara2024:better-together,
  author       = {Soylu, Dilara and Potts, Christopher and Khattab, Omar},
  title        = {{Fine-Tuning and Prompt Optimization: Two Great Steps that Work
                  Better Together}},
  booktitle    = {Proceedings of the 2024 Conference on Empirical Methods in
                  Natural Language Processing},
  date         = {2024},
  eprint       = {2407.10930},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.2407.10930},
}

@misc{Wang-Junlin2024:moa,
  author       = {Wang, Junlin and Wang, Jue and Athiwaratkun, Ben and Zhang, Ce
                  and Zou, James},
  title        = {{Mixture-of-Agents Enhances Large Language Model Capabilities}},
  date         = {2024-06},
  eprint       = {2406.04692},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.2406.04692},
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

@misc{Wu-Junde2025:agentic-reasoning,
  author       = {Wu, Junde and Zhu, Jiayuan and Liu, Yuyuan and Xu, Min and Jin, Yueming},
  title        = {{Agentic Reasoning: A Streamlined Framework for Enhancing LLM
                  Reasoning with Agentic Tools}},
  date         = {2025-02},
  eprint       = {2502.04644},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.2502.04644},
}

@misc{Wu-Qingyun2023:autogen,
  author       = {Wu, Qingyun and Bansal, Gagan and Zhang, Jieyu and Wu, Yiran
                  and Li, Beibin and Zhu, Erkang and Jiang, Li and Zhang, Xiaoyun
                  and Zhang, Shaokun and Liu, Jiale and Awadallah, Ahmed Hassan
                  and White, Ryen W. and Burger, Doug and Wang, Chi},
  title        = {{AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent
                  Conversation}},
  date         = {2023-08},
  eprint       = {2308.08155},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.2308.08155},
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

@inproceedings{Zheng-Lianmin2023:llm-as-judge,
  author       = {Zheng, Lianmin and Chiang, Wei-Lin and Sheng, Ying and Zhuang, Siyuan
                  and Wu, Zhanghao and Zhuang, Yonghao and Lin, Zi and Li, Zhuohan
                  and Li, Dacheng and Xing, Eric P. and Zhang, Hao
                  and Gonzalez, Joseph E. and Stoica, Ion},
  title        = {{Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena}},
  booktitle    = {Proceedings of the 37th Conference on Neural Information Processing
                  Systems Track on Datasets and Benchmarks},
  date         = {2023},
  eprint       = {2306.05685},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.2306.05685},
}

@misc{Zhuge-Mingchen2024:agent-as-judge,
  author       = {Zhuge, Mingchen and Zhao, Changsheng and Ashley, Dylan
                  and Wang, Wenyi and Khizbullin, Dmitrii and Xiong, Yunyang
                  and Liu, Zechun and Chang, Ernie and Krishnamoorthi, Raghuraman
                  and Tian, Yuandong and Shi, Yangyang and Chandra, Vikas
                  and Schmidhuber, J{\"u}rgen},
  title        = {{Agent-as-a-Judge: Evaluate Agents with Agents}},
  date         = {2024-10},
  eprint       = {2410.10934},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.2410.10934},
}
```
