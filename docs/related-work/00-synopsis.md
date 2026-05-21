---
title: Synopsis — open energy modelling needs sourced/reproducible/auditable facts, not LLM opinions
author: Claude prompted by Ha-Duong Minh
date: 2026-05-21
paper: slides/manuscript/main.md
section: Synopsis (lines 1–7)
citation-budget: 10–15 (delivered 8 — see Methods)
---

## Relevance

The synopsis frames the paper's reason for existing: open energy-system models such as PyPSA-ASEAN need power-plant inventories that are complete, accurately dated, and traceable to primary sources; statistical work requires *facts that are sourced, reproducible, and auditable*, not "plausible-sounding outputs from a random words generator somewhere in the cloud." Two referee questions need anchors: (1) why are existing open inventories insufficient? — must cite the existing landscape (GPPD, GEM, powerplantmatching, PyPSA / PyPSA-Earth); (2) why is "facts not opinions" the right framing? — must anchor to data quality / official-statistics / philosophy-of-science literature. The synopsis is short, so the budget is tight; deeper anchors live in §2 (quality bar) and §5 (tailored solution).

## History of science context

The motivation rests on a tension between two trajectories.

On the open-modelling side, the European open-source energy-system community built first PyPSA (Brown et al. 2018), then PyPSA-Earth (Parzen et al. 2023) — extending the toolchain to under-documented regions. Their input-data layer depends on harmonised power-plant databases: the World Resources Institute Global Power Plant Database (Byers et al. 2018), Global Energy Monitor's tracker series (Shearer et al., continuous), and the powerplantmatching toolkit (Gotzens et al. 2019) that fuses them. These cover the world unevenly: ASEAN, and Vietnam in particular, falls below the granularity needed for plant-level scenario analysis because the upstream data quality varies by jurisdiction.

On the LLM side, since 2022 the "ask the chatbot" pattern has become the implicit baseline for any factual lookup task. Petroni et al. (2019) and Roberts et al. (2020) framed LLMs as parametric knowledge bases; the resulting practice is empirically attractive but epistemically suspect. The data-quality literature, from Wang & Strong (1996) to the IMF Data Quality Assessment Framework (2003) and the UN Fundamental Principles of Official Statistics (UN 2014), demands that statistical claims be sourced and auditable — properties parametric LLM outputs do not have. The synopsis stakes a claim that the open-energy-modelling community should not silently adopt parametric LLMs as a substitute for sourced data work.

The framing "science needs knowledge, not opinions" descends from the philosophy-of-science line on falsifiability (Popper 1959, treated in §2). The synopsis frames the paper as a constructive response: rather than rejecting LLMs entirely, it asks what architecture they need to wrap in to produce sourced-and-auditable outputs.

## Cited works — detailed

### Brown et al. 2018 — PyPSA
- **Reference.** Brown, T.; Hörsch, J.; Schlachtberger, D. *PyPSA: Python for Power System Analysis*. Journal of Open Research Software 6(1):4, 2018. arXiv:1707.09913.
- **What the work did.** Open-source Python toolbox for power-system simulation and optimisation across multi-period horizons.
- **Why this paragraph cites it.** Field-defining reference for the *PyPSA family* invoked by name in the synopsis ("open energy-system models such as PyPSA-ASEAN"). The reader must know what PyPSA is to understand the data-consumption use case.
- **Limitations or critiques.** Originally European-focused; data-quality issues outside Europe limit its reach without a powerplantmatching-style fusion step.

### Byers et al. 2018 — WRI Global Power Plant Database
- **Reference.** Byers, L.; Friedrich, J.; Hennig, R. et al. *A Global Database of Power Plants*. World Resources Institute technical note, 2018. (Existing key `Byers-Logan2018:wri-gppd`.)
- **What the work did.** Open dataset of ~30,000 power plants across 164 countries, with capacity, fuel, location, ownership.
- **Why this paragraph cites it.** Concrete instance of the "open inventories exist but are incomplete or stale" claim that motivates the work; one of the most-used baselines in the open-modelling stack.
- **Limitations or critiques.** Snapshot data, not continuously updated; coverage of proposed/planned/cancelled units is thin; status fields are limited.

### Global Energy Monitor 2026 — Global Coal Plant Tracker
- **Reference.** Global Energy Monitor. *Global Coal Plant Tracker, January 2026 release*. https://globalenergymonitor.org/projects/global-coal-plant-tracker/
- **What the work did.** Continuously updated open database of coal-fired power units worldwide (≥30 MW), with lifecycle status across 108 countries.
- **Why this paragraph cites it.** Closest external benchmark for the experimental reference inventory. The synopsis claim that public information is "scattered" but the resulting datasets are still incomplete is anchored by GEM's coverage maps, which acknowledge per-country quality variance.
- **Limitations or critiques.** Grey-literature dataset, not peer-reviewed; coverage of gas/LNG and forward-looking units is improving but uneven outside coal.

### Gotzens et al. 2019 — powerplantmatching
- **Reference.** Gotzens, F.; Heinrichs, H.; Hörsch, J.; Hofmann, F. *Performing energy modelling exercises in a transparent way — The issue of data quality in power plant databases*. Energy Strategy Reviews 23: 1–12, 2019. doi:10.1016/j.esr.2018.11.004.
- **What the work did.** Toolkit + paper for cleaning, standardising, and fusing multiple open power-plant databases.
- **Why this paragraph cites it.** Closest peer in spirit — explicitly takes "data quality in power-plant databases" as its problem statement and uses heuristic fusion across open sources. Our work extends the agenda to LLM-driven extraction with per-cell provenance, which is what powerplantmatching does not attempt.
- **Limitations or critiques.** Heuristic matching, Europe-first; no provenance tracking for individual cells; no native ASEAN coverage.

### Parzen et al. 2023 — PyPSA-Earth
- **Reference.** Parzen, M.; Abdel-Khalek, H.; Fedorova, E. et al. *PyPSA-Earth. A New Global Open Energy System Optimization Model Demonstrated in Africa*. Applied Energy 341: 121096, 2023. (Existing key `Parzen-Maximilian2023:pypsa-earth`.)
- **What the work did.** Extended PyPSA to a global open energy-system modelling framework, with Africa as first demonstration.
- **Why this paragraph cites it.** Concrete operationalisation of the open-modelling stack at country granularity outside Europe — the trajectory PyPSA-ASEAN follows. The paper explicitly documents the input-data challenge.
- **Limitations or critiques.** Africa-first; ASEAN coverage in PyPSA-VN style is still nascent; relies on upstream open databases whose Vietnam coverage is precisely what motivates our work.

### Roberts et al. 2020 — Closed-book QA
- **Reference.** Roberts, A.; Raffel, C.; Shazeer, N. *How Much Knowledge Can You Pack Into the Parameters of a Language Model?*. EMNLP 2020. arXiv:2002.08910.
- **What the work did.** Established the closed-book QA paradigm — LLMs answering factual questions without retrieval.
- **Why this paragraph cites it.** Anchors the implicit alternative the synopsis dismisses ("plausible-sounding outputs from a random words generator"). Roberts et al. is the constructive version of the practice; we invoke it to mark what we are arguing against, not who we are arguing against.
- **Limitations or critiques.** Their setting is short-answer QA, not structured table generation; their critique of brittleness on tail entities is precisely what our work measures empirically.

### UN 2014 — Fundamental Principles of Official Statistics
- **Reference.** United Nations General Assembly. *Fundamental Principles of Official Statistics*. Resolution A/RES/68/261, 2014. https://unstats.un.org/unsd/dnss/gp/fundprinciples.aspx
- **What the work did.** Codified 10 principles for official statistics: impartiality, sources to be cited, methodology disclosed, etc.
- **Why this paragraph cites it.** Highest-authority anchor for the "facts should be sourced and auditable" claim. Frames what *statistical quality* means in a way that LLM outputs need to meet, not redefine.
- **Limitations or critiques.** Aspirational rather than operational; needs domain-specific instantiation, which §2 of the manuscript provides.

### Wang & Strong 1996 — Beyond Accuracy
- **Reference.** Wang, R.Y.; Strong, D.M. *Beyond Accuracy: What Data Quality Means to Data Consumers*. Journal of Management Information Systems 12(4): 5–33, 1996. doi:10.1080/07421222.1996.11518099.
- **What the work did.** Empirical study identifying 15 data-quality dimensions; established the field-shaping taxonomy still used today.
- **Why this paragraph cites it.** Field-defining historical anchor for the *data quality* programme the synopsis implicitly invokes (accuracy/coherence/provenance/temporality is a four-dimensional descendant).
- **Limitations or critiques.** Pre-internet, business-data context; subsequent work (DQAF, ISO 8000) builds out the operational layer.

## Related but not cited — justified

### IMF 2003 — Data Quality Assessment Framework
The DQAF is the operationalisation of UN principles for IMF-supervised statistics. Cited in §2 where the four-quality framework is built; redundant in the synopsis where UN principles already anchor the family.

### Popper 1959 — The Logic of Scientific Discovery
The deepest historical anchor for "knowledge, not opinions." Belongs in §2 (quality bar) where the falsifiability link is explicit; in the synopsis it would be ornamental.

### Petroni et al. 2019 — LM as KB
The conceptual ancestor of Roberts et al. 2020. We keep one of two — Roberts is the more directly applicable closed-book version. Cited in §1 where parametric extraction is the primary subject.

### Lewis et al. 2020 — RAG
The natural counterpoint to closed-book QA. Belongs in §3 (capability ladder), where RAG is one of the named steps; redundant in the synopsis.

### Asai et al. 2024 — Self-RAG
A frontier RAG variant. Out of scope at synopsis level; belongs in §3 / §5.

## Methods

- **Search seeds.** Manuscript paragraph itself; existing `refs.bib` (Parzen, Byers, plus the Petroni/Roberts pair pre-resolved in §1).
- **Databases.** arXiv, DOI resolver, JOSS, sciencedirect (Elsevier, gave 403), Global Energy Monitor website, WRI website, UN statistics portal.
- **Stop condition.** 8 entries cited + 5 in related-but-not-cited. Synopsis budget is intentionally lower than 10–15 because the synopsis surfaces only the highest-authority anchors; deeper sub-literatures are spread across §1–§5.
- **Inclusion rule.** (a) Names a specific work/system mentioned by name in the synopsis (PyPSA, Vietnam thermal landscape), or (b) is a top-level authority for the "facts not opinions" framing.
- **Exclusion rule.** Lower-tier anchors that belong inside a downstream section.
- **Freshness cutoff.** 2026-05-21.
- **Preprint policy.** Accepted for canonical references (Brown 2018 paper has arXiv preprint identifier).
- **Grey-literature policy.** GEM and WRI are grey-literature data products; both are unavoidable citations given that the synopsis names the inventory landscape. Both have stable institutional URLs.
- **Identifier resolution log.** WebFetched and resolved: PyPSA arxiv 1707.09913 ✓; powerplantmatching JOSS DOI 10.21105/joss.04240 returned a different paper, but the canonical paper Gotzens et al. 2019 resolved via the project's README description (DOI 10.1016/j.esr.2018.11.004); the Elsevier DOI gave 403 — the article is widely indexed and the DOI is stable. GEM and WRI URLs resolved. UN A/RES/68/261 is a standing resolution. Roberts 2020 ✓ in §1 batch.
- **LLM-assist disclosure.** Drafted by Claude (Opus 4.7) under ticket 0151. WebFetch used for identifier resolution.

## Author verification checklist

- [ ] Read each cited primary source (not just abstract)
- [ ] Confirmed claim-to-citation mapping
- [ ] Checked preprints for peer-reviewed updates
- [ ] Agreed with "related but not cited" justifications
- [ ] No in-repo docs cited in place of primary sources

## Bibliography

```bibtex
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

@article{Parzen-Maximilian2023:pypsa-earth,
  author       = {Parzen, Maximilian and Abdel-Khalek, Hazem and Fedorova, Ekaterina
                  and Mahmood, Matin and Frysztacki, Martha Maria and Hampp, Johannes
                  and Franken, Lukas and Schumm, Leon and Neumann, Fabian
                  and Poli, Davide and Kiprakis, Aristides and Fioriti, Davide},
  title        = {{PyPSA-Earth. A New Global Open Energy System Optimization Model
                  Demonstrated in Africa}},
  journaltitle = {Applied Energy},
  date         = {2023},
  volume       = {341},
  pages        = {121096},
  doi          = {10.1016/j.apenergy.2023.121096},
  eprint       = {2209.04663},
  eprinttype   = {arxiv},
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

@misc{UN2014:fundamental-principles,
  author       = {{United Nations General Assembly}},
  title        = {{Fundamental Principles of Official Statistics}},
  date         = {2014-01},
  url          = {https://unstats.un.org/unsd/dnss/gp/fundprinciples.aspx},
  note         = {Resolution A/RES/68/261},
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
```
