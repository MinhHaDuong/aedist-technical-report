# Argument-wide related work

Aggregator for ticket 0151. One section per paragraph-unit of
`slides/manuscript/main.md`. Per-paragraph notes in
`docs/related-work/` are the source of truth; this document gives a
reader the overview and aggregates the bibliography for a future
`/bib-merge` run.

Generated 2026-05-21.

## Methodology and provenance — what kind of review this is

This is an **author's due-diligence review**, not a systematic
review. The standard adopted is *"defensible under peer review of one
paragraph"*: for each major claim in `slides/manuscript/main.md`, a
referee's likely "why didn't you cite X?" should have a prepared
answer, with the alternatives either cited or explicitly justified as
not-cited.

**Authorship and assistance.** The per-paragraph notes were drafted by
an LLM agent (Claude, via the `related-work-note` skill, single
pass, 2026-05-21) under the author's direction. The author has not yet
read each primary source end-to-end; the candidate set, summaries,
and "why-cite / why-not-cite" justifications are LLM-generated and
require an author verification pass before the references move from
this working file into manuscript prose. The seven-section template,
biblatex format, and the "related but not cited" requirement come
from the project's `related-work-note` skill specification.

**Search and identifier resolution.** Candidates were assembled by
agent-side recall (parametric knowledge plus targeted web fetches),
not by a structured database query (no Web of Science / Scopus /
Semantic Scholar export). Every DOI, arXiv eprint, and URL in the
bibliographies was resolved via `WebFetch` at generation time; three
identifiers did not resolve cleanly and are flagged for re-resolution
at submission (IMF DQAF page — 403, URL canonical; CACM Wikidata
DOI — verified via DBLP fallback; VLDB Ditto PDF — arXiv version
used, PVLDB volume / issue / pages stripped).

**Citation budget.** Target 10–15 anchors per paragraph per the
project's `writing.md` rule, with a tier mix of one field-defining
anchor + one recent survey + two-to-three frontier works (≤2 years
old). §0 (synopsis) delivered 8 anchors by design — synopsis-level
overlap with §2 and §5 meant deeper anchors live in the downstream
notes. §3 (capability ladder) was the budget's tightest point: the
brief listed ~15 candidate topics for one paragraph; cuts are
documented per-note.

**What this review did not do.** No systematic database query.
No exhaustive coverage. No author re-read of primary sources yet (per
per-note Verification checklists). No preprint→peer-reviewed-update
sweep. No reproduction of cited methods. The "related but not cited"
sections are LLM-judged and may miss closely-adjacent work the author
would catch.

**Disclosure for the eventual paper.** When the manuscript adds a
formal Related Work section, this review's LLM-assisted provenance
should be carried into the paper's Methods or acknowledgements as a
single explicit sentence — following emerging community norms for AI
assistance disclosure in academic writing.

## §0 Synopsis

Open energy-system models (PyPSA family) require sourced/auditable
plant-level inventories; the open-data ecosystem (GPPD, GEM,
powerplantmatching) covers the world unevenly and Vietnam falls below
the granularity scenario analysis needs. The synopsis frames "science
needs knowledge, not opinions" against the implicit alternative of
parametric LLM extraction (Roberts et al. 2020) and anchors the
authority for "facts must be sourced" in the UN Fundamental Principles
of Official Statistics (2014) and the data-quality programme (Wang &
Strong 1996). 8 anchors, 5 not-cited.

See: `docs/related-work/00-synopsis.md`.

## §1 Baseline

The parametric direct-query experiment maps to two literatures:
closed-book QA / parametric memorisation (Petroni 2019, Roberts 2020,
Carlini 2021) and failure-mode characterisation (TruthfulQA, Huang
hallucination survey, Atil non-determinism). Each of the five named
failure modes (Récalcitrant, Incomplet, Hallucinant, Non-déterministe,
Non-monotone) gets at least one anchor; modern structured-extraction
benchmarks (TableBench, LLMStructBench, LM-KBC) anchor the methodology.
11 anchors, 6 not-cited.

See: `docs/related-work/01-baseline.md`.

## §2 Quality bar

Four-dimensional accuracy / coherence / provenance / temporality bar.
Anchored to philosophy of science (van Fraassen 1980 empirical
adequacy), data-quality canon (Wang & Strong 1996; IMF DQAF 2003),
official-statistics authority (UN 2014), and the LLM evaluation
sub-literature per dimension (TruthfulQA for accuracy; Wang
self-consistency for weak coherence; ALCE + Self-RAG + RAGAS for
provenance; LLMStructBench + TableBench for structured-extraction
accuracy at cell level). Temporality is the dimension most weakly
covered in the LLM literature — gap flagged. 12 anchors, 6 not-cited.

See: `docs/related-work/02-quality-bar.md`.

## §3 Capability ladder

Six-limit historical narrative: articulation, coverage, reasoning,
tool-use, retroactivity, agency. Anchored to canonical method papers
(Chain-of-Thought, RAG, ReAct, DSPy) and the benchmark cluster per
named capability (MATH, GPQA, ARC, SimpleQA, BrowseComp, GAIA,
SWE-Bench, OSWorld, HumanEval/Codex). Citation budget over-pressured
— the task brief listed ~15 anchor topics and the paragraph names six
capabilities; cuts documented in Methods of the per-note. The
"retroactivity" and "agency" sub-claims are placeholders in the
manuscript itself (lines 47–48: `5. Retroactivity —. 6. Agency —.`);
those bullets need authorial completion before final review. 13
anchors, 6 not-cited.

See: `docs/related-work/03-capability-ladder.md`.

## §4 SOTA frontier

Three-agent deep-research comparison with cross-model pairwise
judgement and tuned-prompt-per-model. Anchored to BrowseComp / GAIA
(deep-research benchmarks), LLM-as-a-Judge / Agent-as-a-Judge
(judgement protocols), AutoGen / Mixture-of-Agents (multi-agent
methodology), DSPy / BetterTogether (per-model prompt tuning), and the
ancestor architectures (ReAct, Agentic Reasoning). Product-page
references for OpenAI / Anthropic / Google deep-research offerings
are grey literature — recorded in not-cited per the writing.md rule.
10 anchors, 6 not-cited.

See: `docs/related-work/04-sota-frontier.md`.

## §5 Tailored solution

Stateful agentic workflow with narrative-asset-inventory primary
representation and per-cell provenance. Anchored to closely-related
projects (PyPSA, powerplantmatching, GPPD, GEM — all four cited
unconditionally per writing.md), KG-LLM convergence (Pan 2024
roadmap; Jin 2024 LLMs-on-Graphs survey; Wikidata canonical Vrandečić
& Krötzsch 2014), entity resolution (Li 2020 Ditto), stateful agent
memory (MemGPT, LoCoMo), automatic quality verification (Self-RAG),
and scripted-behaviour-in-agents (ReAct). 12 anchors, 7 not-cited.

See: `docs/related-work/05-tailored-solution.md`.

## Gaps (epistemic-humility flags)

Claims in `main.md` for which no prior literature was found at the
level of specificity required. Use "to our knowledge" / "we did not
find" language — never "nobody has done."

1. **Open-world structured extraction of an entire national asset
   class with per-cell provenance.** §1 / §5. The TableBench /
   LLMStructBench line covers table-QA and structured-extraction from
   documents; the LM-KBC line covers triple-level extraction. *To our
   knowledge*, no published benchmark or system targets open-world
   enumeration of a national power-plant fleet with per-cell
   provenance. (Manuscript line 78 already uses "we did not find"
   language for the cognate per-plant audit-trail claim — pattern to
   replicate.)

2. **Non-monotone cost-vs-F1 relationship for structured factual
   extraction.** §1. TruthfulQA established non-monotone scale-vs-truth
   for short-answer factuality. *To our knowledge*, no published study
   has reported the analogous non-monotone relationship for *API cost*
   vs *structured-extraction F1* across labs. Our 16-model panel may
   be the first such observation in this format.

3. **MoE non-determinism at T=0 + seed pinning for structured
   outputs.** §1. Atil et al. 2024 characterised non-determinism for
   short-answer tasks. *To our knowledge*, no published work
   characterises MoE non-determinism specifically for multi-row
   structured outputs at deterministic decoding settings — the
   manuscript's `repeat=3` discipline for MoE models is informed by
   in-project measurement (ticket 0139 / PR #278) more than by prior
   literature.

4. **Per-cell provenance + temporal validity for LLM-built
   inventories.** §2 / §5. Per-cell provenance is well-developed for
   databases (W3C PROV-O); citation accuracy for LLM long-form is
   handled by ALCE. *To our knowledge*, the conjunction — per-cell
   provenance *with* temporal validity per cell, in an LLM-augmented
   inventory — has not been published. This is the §5 contribution.

5. **Frontier deep-research agent quality against the four-dimensional
   bar.** §4. BrowseComp, GAIA, and Agentic Reasoning measure
   short-answer or task-completion outcomes. *We did not find*
   published evaluations of OpenAI / Anthropic / Google deep-research
   products against accuracy/coherence/provenance/temporality jointly
   on a structured-output task. The §4 experiment fills this gap.

6. **Type-III error / Articulation in the LLM context.** §3. The
   Type-III error programme (Kimball 1957; Mitroff & Featheringham
   1974) was developed for statistical methodology. *To our knowledge*,
   the explicit translation to "the prompt does not articulate the
   right question" — what the manuscript labels the Articulation
   limit — is not formalised in the LLM literature; the framing is a
   contribution of the paper itself.

## Bibliography candidates for refs.bib

Aggregated and de-duplicated across all six notes, biblatex format.
Entries with existing keys in `report/refs.bib` are marked
`[existing key]` and should not be re-added. New entries to be
considered by a future `/bib-merge` run are marked `[new]`.

### Existing keys to reuse (no action for /bib-merge)

- `Asai-Akari2024:self-rag` — Self-RAG. Used in §2, §5.
- `ATRGAC9J` — Carlini et al. 2021 *Extracting Training Data from LLMs*. Used in §1.
- `Byers-Logan2018:wri-gppd` — WRI GPPD. Used in §0, §5.
- `Chen-Wenhu2020:tabfact` — TabFact. Cited in §1 not-cited.
- `Gao-Yunfan2024:rag-survey` — Gao et al. RAG survey. Used in §3.
- `Hendrycks-Dan2021:mmlu` — MMLU. Used in §1, §2.
- `Mialon-Gregoire2024:gaia` — GAIA. Used in §3, §4.
- `Ni-Shiwen2025:llm-benchmark-survey` — Ni et al. LLM-benchmark survey. Used in §1.
- `Parzen-Maximilian2023:pypsa-earth` — PyPSA-Earth. Used in §0, §5 (via Brown).
- `Singhania-Sneha2022:lm-kbc` — LM-KBC. Used in §1.
- `Tenckhoff-Sonke2026:llmstructbench` — LLMStructBench. Used in §1, §2.
- `Wang2022:self-consistency` — Self-consistency. Used in §1, §2.
- `Wu-Xianjie2025:tablebench` — TableBench. Used in §1, §2.

### New entries proposed (input for /bib-merge)

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

@misc{Chollet-Francois2019:arc,
  author       = {Chollet, Fran{\c{c}}ois},
  title        = {{On the Measure of Intelligence}},
  date         = {2019-11},
  eprint       = {1911.01547},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.1911.01547},
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

@misc{IMF2003:dqaf,
  author       = {{International Monetary Fund}},
  title        = {{Data Quality Assessment Framework}},
  date         = {2003},
  url          = {https://dsbb.imf.org/dqrs/DQAF},
  note         = {Five quality dimensions; institutional standard},
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

@misc{Wang-Junlin2024:moa,
  author       = {Wang, Junlin and Wang, Jue and Athiwaratkun, Ben and Zhang, Ce
                  and Zou, James},
  title        = {{Mixture-of-Agents Enhances Large Language Model Capabilities}},
  date         = {2024-06},
  eprint       = {2406.04692},
  eprinttype   = {arxiv},
  doi          = {10.48550/arXiv.2406.04692},
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

## Next steps (for the author)

1. Read each cited primary source per the verification checklist in
   each note before finalising the §1–§5 prose.
2. Run `/bib-merge` to merge the new-entries block above into
   `report/refs.bib`. The merge tool will dedupe against existing
   keys.
3. Resolve the empty bullets at `slides/manuscript/main.md` lines
   47–48 (Retroactivity, Agency) before §3's literature anchors can
   be fully tied to clauses.
4. Decide which of the six gap statements deserves explicit
   "to our knowledge" language in the manuscript prose vs which can
   stay implicit.
5. Re-resolve at submission time:
   - **IMF DQAF URL** (https://dsbb.imf.org/dqrs/DQAF): blocked with
     403 during this review; institutional resource, no DOI; URL is
     canonical but should be re-fetched closer to publication.
   - **Li et al. 2020 Ditto** (`Li-Yuliang2020:ditto`): arXiv version
     resolved; the PVLDB volume 14 issue/pages were not extractable
     via WebFetch on the VLDB PDF — strip-and-flagged in the bib
     entry. Look up PVLDB 14 directly (e.g., DBLP, ACM DL) for exact
     issue and pages.
   - **Tenckhoff et al. 2026 LLMStructBench**: arXiv ID 2602.14743 is
     unusual (suggests submission year 2026); confirmed via WebFetch
     to refer to the LLMStructBench paper. The existing refs.bib
     entry pre-dates this note.
   - **Brown et al. 2018 PyPSA DOI** (10.5334/jors.188) and
     **Vrandecic & Krötzsch 2014 Wikidata DOI** (10.1145/2629489):
     both re-verified during the review's follow-up pass (JORS
     metajnl page; DBLP `journals/cacm/VrandecicK14`).
6. The IMF DQAF URL gave 403 during identifier resolution but the
   five-dimensions framework is institutionally canonical;
   re-resolve at submission time.
