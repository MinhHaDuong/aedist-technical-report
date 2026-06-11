---
title: Tailored stateful-agentic solution — narrative inventory, per-cell provenance, KG-triple analogy
author: Claude prompted by Ha-Duong Minh
date: 2026-05-21
paper: slides/manuscript/main.tex
section: §5 Tailored solution (lines 56–62)
citation-budget: 12–15
---

## Relevance

The paragraph proposes a tailored stateful workflow as the constructive response to §4's "SOTA falls short" finding. Five claims need anchors: (a) algorithmic behaviour should be scripted in agentic systems (current best practice in the agent-design literature); (b) the primary representation is a narrative asset history, the table is a derived artefact (a knowledge-graph view); (c) per-cell provenance — each cell as a (source, date, confidence, conflict-history) tuple — connects to data-provenance literature; (d) the knowledge-graph triple analogy positions the problem as KG fusion / entity resolution; (e) the stateful incremental update with human-judgement memory connects to the LLM-agent memory architecture line (MemGPT, long-context memory). Closely-related projects (PyPSA-VN, powerplantmatching, GEM) must be cited unconditionally per `writing.md`.

## History of science context

The paragraph stands at the intersection of four sub-fields.

**Statistical workflow / asset-inventory engineering.** The PyPSA family (Brown et al. 2018, Parzen et al. 2023) and powerplantmatching (Gotzens et al. 2019) defined how the open-energy community builds inventories: heuristic fusion of multiple open databases, with limited per-cell provenance. The Global Energy Monitor tracker series operationalises a manual-curation-with-versioning approach at planetary scale. Our system is the LLM-augmented descendant: same primary representation, more sophisticated reconciliation.

**Knowledge-graph fusion / entity resolution.** The classical entity-matching line runs from Fellegi-Sunter 1969 through to the Deep Matcher / Ditto era (Li et al. 2020). The KG-LLM convergence is a 2023–2024 sub-literature: Pan et al. 2024 *Unifying LLMs and KGs* roadmap; Jin et al. 2024 *LLMs on Graphs* survey. Wikidata (Vrandečić & Krötzsch 2014) is the canonical open KG that proves source-cited triples can scale. Our claim "each cell maps to a KG triple" puts the manuscript squarely in this convergence.

**Stateful agentic memory.** MemGPT (Packer et al. 2023) framed long-running LLM agents as needing OS-like memory tiers. LoCoMo (Maharana et al. 2024) provides the long-conversation evaluation benchmark. The paragraph's "memory of human judgements is preserved and used to guide the updates" inherits this line directly.

**Per-cell / data-provenance literature.** Data provenance is older than LLMs: Buneman et al.'s database-provenance work in the early 2000s, the W3C PROV-O ontology, and the recent ALCE / Self-RAG / Chain-of-Note line in the LLM era. The four-dimensional bar's **Provenance** dimension (§2) is the abstract requirement; §5's per-cell tuple is the concrete instantiation.

The opposing view: a frontier deep-research agent + clever prompts will eventually be Pareto-optimal, removing the need for bespoke workflow scaffolding. The Anthropic / OpenAI deep-research products implicitly bet on this position. The manuscript explicitly bets the other way for this task class.

## Cited works — detailed

### Brown et al. 2018 — PyPSA
- **Reference.** Brown, T.; Hörsch, J.; Schlachtberger, D. *PyPSA: Python for Power System Analysis*. JORS 6(1):4, 2018. arXiv:1707.09913.
- **What the work did.** Field-defining open energy-system modelling framework.
- **Why this paragraph cites it.** Closely-related project; the downstream consumer of the inventories §5 builds. Unconditional citation per `writing.md`.
- **Limitations or critiques.** Already discussed in §0.

### Gotzens et al. 2019 — powerplantmatching
- **Reference.** Gotzens, F.; Heinrichs, H.; Hörsch, J.; Hofmann, F. *Performing energy modelling exercises in a transparent way — The issue of data quality in power plant databases*. Energy Strategy Reviews 23:1–12, 2019. doi:10.1016/j.esr.2018.11.004.
- **What the work did.** Toolkit + paper for fusing power-plant databases.
- **Why this paragraph cites it.** Closest peer system — heuristic fusion of open databases is what §5 augments with LLM-driven reasoning and per-cell provenance. Unconditional citation.
- **Limitations or critiques.** No per-cell provenance; static heuristics; Europe-centric.

### Byers et al. 2018 — WRI Global Power Plant Database
- **Reference.** Byers, L. et al. *A Global Database of Power Plants*. WRI, 2018. (Existing key `Byers-Logan2018:wri-gppd`.)
- **What the work did.** Open dataset of ~30,000 plants worldwide.
- **Why this paragraph cites it.** Concrete instance of the input-data ecosystem §5 fuses; closely-related project.

### Global Energy Monitor 2026 — Global Coal Plant Tracker
- **Reference.** Global Energy Monitor. *Global Coal Plant Tracker, January 2026 release*. URL.
- **What the work did.** Continuously maintained open inventory.
- **Why this paragraph cites it.** Closest external benchmark; the *manually-curated* analogue of what §5 attempts to assist with LLM augmentation. Closely-related project, unconditional citation.

### Pan et al. 2024 — Unifying LLMs and KGs
- **Reference.** Pan, S.; Luo, L.; Wang, Y. et al. *Unifying Large Language Models and Knowledge Graphs: A Roadmap*. IEEE TKDE 2024. arXiv:2306.08302.
- **What the work did.** Roadmap surveying three frameworks: KG-enhanced LLMs, LLM-augmented KGs, synergised LLMs+KGs.
- **Why this paragraph cites it.** Anchor for the **KG-triple analogy** claim. Their "LLM-augmented KGs" category is the closest formal description of what §5 builds.
- **Limitations or critiques.** Roadmap-style; no operational system at our task granularity.

### Jin et al. 2024 — LLMs on Graphs survey
- **Reference.** Jin, B.; Liu, G.; Han, C.; Jiang, M.; Ji, H.; Han, J. *Large Language Models on Graphs: A Comprehensive Survey*. IEEE TKDE 2024. arXiv:2312.02783.
- **What the work did.** Comprehensive survey across pure-graph, text-attributed, and text-paired graph settings.
- **Why this paragraph cites it.** Recent-survey anchor for the **KG / LLM convergence** sub-literature. Establishes the field-defining categorisation our work participates in.
- **Limitations or critiques.** Graph-centric framing; the manuscript's primary representation is narrative, KG triples are a derived view.

### Li et al. 2020 — Ditto (Deep Entity Matching)
- **Reference.** Li, Y.; Li, J.; Suhara, Y.; Doan, A.; Tan, W.-C. *Deep Entity Matching with Pre-Trained Language Models*. VLDB 2021. arXiv:2004.00584.
- **What the work did.** Used pretrained LMs (BERT, DistilBERT, RoBERTa) for entity matching; up to 29% F1 gains; 96.5% on a 789K × 412K company-record task.
- **Why this paragraph cites it.** Field-shaping anchor for the **entity resolution** sub-claim. Establishes the precedent for LLM-driven matching at scale; our per-cell reconciliation is its descendant problem.
- **Limitations or critiques.** Pairwise matching, not multi-source fusion with provenance; pre-instruction-tuned LMs.

### Packer et al. 2023 — MemGPT
- **Reference.** Packer, C.; Wooders, S.; Lin, K. et al. *MemGPT: Towards LLMs as Operating Systems*. arXiv:2310.08560, 2023.
- **What the work did.** Hierarchical memory architecture; virtual-context management for long-running LLM agents.
- **Why this paragraph cites it.** Direct anchor for **stateful agentic memory**. The manuscript's "memory of human judgements is preserved" maps directly to MemGPT's tiered-memory framing.
- **Limitations or critiques.** Conversation focus, not extraction-task focus; the persistence-of-judgements use case extends but does not contradict.

### Vrandečić & Krötzsch 2014 — Wikidata
- **Reference.** Vrandečić, D.; Krötzsch, M. *Wikidata: A Free Collaborative Knowledgebase*. Communications of the ACM 57(10):78–85, 2014. doi:10.1145/2629489.
- **What the work did.** Foundational paper on Wikidata's design: source-cited triples, multilingual labels, qualifiers for context.
- **Why this paragraph cites it.** Field-defining anchor for the **per-cell provenance + KG-triple** model. Wikidata operationalises "every fact has sources" at planetary scale, with mechanism for conflict (multiple statements, source-ranked).
- **Limitations or critiques.** Crowdsourced curation; sparse coverage on industrial assets in many jurisdictions. The model is right; the instance is incomplete for Vietnam thermal.

### Asai et al. 2024 — Self-RAG
- **Reference.** Asai, A. et al. *Self-RAG*. ICLR 2024. (Existing key `Asai-Akari2024:self-rag`.)
- **What the work did.** Reflection-token-driven retrieval and self-critique.
- **Why this paragraph cites it.** Anchor for the **automatic quality-dimension verification** clause ("The four quality dimensions are automatically verified, annotating the narratives"). Self-RAG's self-critique is the closest published precedent.
- **Limitations or critiques.** Long-form text, not table-cells; quality dimensions are not separated.

### Yao et al. 2023 — ReAct
- **Reference.** Yao, S. et al. *ReAct*. ICLR 2023.
- **What the work did.** Interleaved reasoning + acting; foundational scaffold for tool-using LLM agents.
- **Why this paragraph cites it.** Anchor for the **scripted-behaviour-in-agentic-systems** claim. The manuscript's "algorithmic behavior should be scripted" inherits the design principle ReAct (and successors like AutoGen) operationalise.
- **Limitations or critiques.** Already discussed in §3 / §4.

### Maharana et al. 2024 — LoCoMo (long-term conversational memory)
- **Reference.** Maharana, A.; Lee, D.-H.; Tulyakov, S. et al. *Evaluating Very Long-Term Conversational Memory of LLM Agents*. arXiv:2402.17753, 2024.
- **What the work did.** Benchmark for long-context memory in LLM agents; ~35 sessions, 9000 tokens each; question-answering + event-summarisation + multimodal evaluation.
- **Why this paragraph cites it.** Recent frontier anchor for the **incremental updates over time** clause. Provides the closest published evaluation of the memory-persistence property §5 needs.
- **Limitations or critiques.** Conversation-shaped; not extraction-shaped. Identifies the LLM weakness on temporal dynamics that motivates our explicit memory layer.

## Related but not cited — justified

### Petroni et al. 2019 — LM as KB
Cited in §1. The KG-triple analogy traces back to LMs-as-KBs but the manuscript's claim is constructive (build a real KG from LLM outputs), not the LM-IS-the-KB framing.

### Lewis et al. 2020 — RAG
Cited in §3. The "initially generated with a deep research heroic prompt" clause is RAG-flavoured but the citation belongs in §3 where RAG is the named capability.

### Gao et al. 2023 — ALCE
Cited in §2 (provenance). The per-cell provenance claim is the §2 dimension instantiated; ALCE measures the dimension and is cited there.

### Niu et al. 2023 — RAGTruth
arXiv:2401.00396. Hallucination-detection benchmark for RAG. Adjacent to the "quality dimensions are automatically verified" clause but Self-RAG is the more directly architectural precedent.

### Hofstadter / Mitchell / Marcus
The "narrative as primary, table as derived" framing has a deeper philosophical heritage (Mitchell on analogy-making, Marcus on hybrid symbolic-neural). Cited via the KG-LLM survey line; direct citations would inflate the budget.

### Wang et al. 2023 — LLM-agent survey
arXiv:2308.11432. Comprehensive but the agentic-design specifics here are anchored more tightly by ReAct + MemGPT.

### Zhang et al. 2024 — RAFT
arXiv:2403.10131. Domain-specific RAG fine-tuning. The "model independence" / "local model" line in §5 paragraph 2 hints at RAFT's territory; saved for the future-research section if the experimental case lands.

## Methods

- **Search seeds.** Manuscript paragraph; existing `refs.bib` (PyPSA, Asai Self-RAG already present); the closely-related-project list from `writing.md` (PyPSA-VN, powerplantmatching); the KG-LLM convergence line (Pan, Jin); entity-resolution canonical anchor (Li Ditto).
- **Databases.** arXiv (primary), DOI resolver, JOSS, GitHub (project pages), Wikipedia (for Wikidata + powerplantmatching pointers), Global Energy Monitor.
- **Stop condition.** 12 entries cited + 7 in not-cited. Budget pressure was real here: 5 distinct sub-claims each deserving 1–2 anchors leaves no slack.
- **Inclusion rule.** Anchor must (a) be a closely-related project (writing.md unconditional rule), (b) name a specific architectural pattern (KG fusion, entity resolution, stateful memory) called out in the paragraph, or (c) provide the empirical precedent for an as-yet-undemonstrated claim (Self-RAG for automatic quality verification).
- **Exclusion rule.** General architecture surveys without a specific binding to §5's claims; pre-LLM entity-matching that doesn't carry into the LM era.
- **Freshness cutoff.** 2026-05-21.
- **Preprint policy.** MemGPT and LoCoMo are arXiv-only; Pan et al. and Jin et al. published in TKDE.
- **Grey-literature policy.** GEM is grey-literature data; unavoidable as a closely-related project. WRI is similar. Wikidata is cited via the canonical CACM paper, not the project URL.
- **Identifier resolution log.** WebFetched and resolved: 2306.08302 (Pan ✓); 2312.02783 (Jin ✓); 2004.00584 (Li Ditto arXiv ✓ — VLDB venue confirmed, exact PVLDB volume/issue/pages not resolvable via WebFetch on the VLDB PDF; entry stripped of unverified page numbers, note flags for re-resolution at submission); 2310.08560 (MemGPT ✓); 2402.17753 (LoCoMo ✓); Vrandecic CACM DOI 10.1145/2629489 re-verified via DBLP record `journals/cacm/VrandecicK14` — confirms CACM 57(10):78–85, 2014, DOI matches. Brown et al. PyPSA DOI 10.5334/jors.188 re-verified via JORS metajnl page — JORS 6(1), Article 4. Existing keys reused.
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
  doi          = {10.48550/arXiv.2310.11511},
  eprint       = {2310.11511},
  eprinttype   = {arxiv},
}

@article{Brown-Tom2018:pypsa,
  author       = {Brown, Tom and H{\"o}rsch, Jonas and Schlachtberger, David},
  title        = {{PyPSA: Python for Power System Analysis}},
  journaltitle = {Journal of Open Research Software},
  date         = {2018},
  volume       = {6},
  number       = {1},
  pages        = {4},
  doi          = {10.5334/jors.188},
  eprint       = {1707.09913},
  eprinttype   = {arxiv},
}

@techreport{Byers-Logan2018:wri-gppd,
  author       = {Byers, Logan and Friedrich, Johannes and Hennig, Roman
                  and Kressig, Aaron and Li, Xinyue and {Malaguzzi Valeri}, Laura
                  and McCormick, Colin},
  title        = {{A Global Database of Power Plants}},
  institution  = {World Resources Institute},
  date         = {2018},
  url          = {https://www.wri.org/research/global-database-power-plants},
}

@misc{GEM2026:gcpt,
  author       = {{Global Energy Monitor}},
  title        = {{Global Coal Plant Tracker}},
  date         = {2026-01},
  url          = {https://globalenergymonitor.org/projects/global-coal-plant-tracker/},
  note         = {January 2026 release},
}

@article{Gotzens-Fabian2019:powerplantmatching,
  author       = {Gotzens, Fabian and Heinrichs, Heidi and H{\"o}rsch, Jonas
                  and Hofmann, Fabian},
  title        = {{Performing energy modelling exercises in a transparent way
                   — The issue of data quality in power plant databases}},
  journaltitle = {Energy Strategy Reviews},
  date         = {2019},
  volume       = {23},
  pages        = {1--12},
  doi          = {10.1016/j.esr.2018.11.004},
}

@article{Jin-Bowen2024:llms-on-graphs,
  author       = {Jin, Bowen and Liu, Gang and Han, Chi and Jiang, Meng
                  and Ji, Heng and Han, Jiawei},
  title        = {{Large Language Models on Graphs: A Comprehensive Survey}},
  journaltitle = {IEEE Transactions on Knowledge and Data Engineering},
  date         = {2024},
  doi          = {10.48550/arXiv.2312.02783},
  eprint       = {2312.02783},
  eprinttype   = {arxiv},
}

@article{Li-Yuliang2020:ditto,
  author       = {Li, Yuliang and Li, Jinfeng and Suhara, Yoshihiko
                  and Doan, AnHai and Tan, Wang-Chiew},
  title        = {{Deep Entity Matching with Pre-Trained Language Models}},
  journaltitle = {Proceedings of the VLDB Endowment},
  date         = {2020},
  eprint       = {2004.00584},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.2004.00584},
  note         = {PVLDB volume 14; exact issue/pages to be re-verified at submission},
}

@misc{Maharana-Adyasha2024:locomo,
  author       = {Maharana, Adyasha and Lee, Dong-Ho and Tulyakov, Sergey
                  and Bansal, Mohit and Barbieri, Francesco and Fang, Yuwei},
  title        = {{Evaluating Very Long-Term Conversational Memory of LLM Agents}},
  date         = {2024-02},
  eprint       = {2402.17753},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.2402.17753},
}

@misc{Packer-Charles2023:memgpt,
  author       = {Packer, Charles and Wooders, Sarah and Lin, Kevin and Fang, Vivian
                  and Patil, Shishir G. and Stoica, Ion and Gonzalez, Joseph E.},
  title        = {{MemGPT: Towards LLMs as Operating Systems}},
  date         = {2023-10},
  eprint       = {2310.08560},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.2310.08560},
}

@article{Pan-Shirui2024:unifying-llm-kg,
  author       = {Pan, Shirui and Luo, Linhao and Wang, Yufei and Chen, Chen
                  and Wang, Jiapu and Wu, Xindong},
  title        = {{Unifying Large Language Models and Knowledge Graphs: A Roadmap}},
  journaltitle = {IEEE Transactions on Knowledge and Data Engineering},
  date         = {2024},
  doi          = {10.48550/arXiv.2306.08302},
  eprint       = {2306.08302},
  eprinttype   = {arxiv},
}

@article{Vrandecic-Denny2014:wikidata,
  author       = {Vrande{\v{c}}i{\'c}, Denny and Kr{\"o}tzsch, Markus},
  title        = {{Wikidata: A Free Collaborative Knowledgebase}},
  journaltitle = {Communications of the ACM},
  date         = {2014},
  volume       = {57},
  number       = {10},
  pages        = {78--85},
  doi          = {10.1145/2629489},
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
