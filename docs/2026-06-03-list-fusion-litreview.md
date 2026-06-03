# Fusing unreliable model runs into a statistical inventory — literature due-diligence

> Companion due-diligence note (per `.claude/rules/writing.md`: dropped candidates and
> background live here, **not** in the paper's bibliography). Date: 2026-06-03.
> Scope: how to fuse N runs from K LLMs enumerating an unknown list of ASEAN thermal
> power plants (multi-attribute entities: name / capacity-MW / fuel / lifecycle status),
> detect bad runs and non-credible models, with a **presence-only** anchor (OSM, Wikipedia,
> domain trackers) exhaustive only on the operational *easy core*, recall-priority and
> capacity-weighted, feeding a downstream verification step.

## Problem in one line

This is **truth discovery / latent-truth estimation from unreliable sources without gold**,
specialized by four features that jointly have, to our knowledge, no off-the-shelf solution:
**(multi-truth, two-sided-error truth discovery) × (presence-only / PU anchor) ×
(correlated LLM sources trained on the anchor) × (capture–recapture completeness on a
continuous magnitude, MW)**. Each axis is well-developed in isolation; the contribution
of this work is their composition for an energy inventory.

---

## 1. Truth discovery / multi-attribute, multi-truth fusion

Unifying principle: *a source is trustworthy if it agrees with the inferred truth; a value
is true if asserted by trustworthy sources* — solved by fixpoint / EM / optimization.
Two features dominate fit: **multi-truth** (a plant list is a *set*, not one value) and
**two-sided error** (an LLM both omits real plants = FN and hallucinates fake ones = FP).

- **Anchor (conceptual core):** LTM — Latent Truth Model. Zhao, Rubinstein, Gemmell (2012),
  *A Bayesian Approach to Discovering Truth from Conflicting Sources*, PVLDB 5(6):550–561.
  http://vldb.org/pvldb/vol5/p550_bozhao_vldb2012.pdf — splits each source's quality into
  **FP and FN rates**, native multi-truth. The model to build on.
- **Multi-attribute heterogeneous loss:** CRH. Li, Li, Gao, Zhao, Fan, Han (2014),
  *Resolving Conflicts in Heterogeneous Data*, SIGMOD 2014:1187–1198 — per-attribute loss
  (Gaussian for capacity-MW, categorical for fuel, string for name). Pair GTM (Zhao & Han
  2012, Gaussian Truth Model) for the numeric attribute.
- **Few-claim / long-tail sources (small LLM panel):** CATD. Li, Gao, et al. (2015),
  *A Confidence-Aware Approach for Truth Discovery on Long-Tail Data*, PVLDB 8(4):425–436
  — χ² confidence-interval weighting; the frequentist cousin of the imprecise-probability
  idea (wide intervals for sources with few observations).
- **Multi-truth frontier (the set-enumeration neighborhood):** MBM (Wang et al., CIKM 2015);
  SmartMTD/SmartVote (arXiv:1708.02018; WWW 22, 2019) — FP/FN reliability + mutual exclusion
  + **malicious/correlated-source agreement**. Most recent: Wang et al. (2024),
  *Generalizing truth discovery by incorporating multi-truth features*, Computing 106.
- **Surveys / positioning:** Li et al. (2016), *A Survey on Truth Discovery*, SIGKDD
  Explorations 17(2) (arXiv:1505.02463); 2025 update in IEEE TBD,
  DOI 10.1109/TBDATA.2024.3423677. Eval **without** gold: Tang et al. (2020), ACM TIST 11(6).

## 2. Crowdsourcing label aggregation with worker quality

- **Anchor:** Dawid & Skene (1979), *MLE of Observer Error-Rates Using EM*, JRSS-C 28(1):20–28
  — per-source **confusion matrix**; right abstraction for categorical attributes (fuel).
  Key assumption (conditional independence given truth) is *violated* by correlated LLMs.
- **Modern variants:** GLAD (Whitehill et al. 2009, item difficulty — obscure plants are
  harder); spectral+EM provably optimal (Zhang et al., JMLR 17, 2016); variational-Bayes DS.
- **Budget allocation:** Karger, Oh, Shah (2014), *Budget-Optimal Task Allocation*,
  Operations Research 62(1) — calls-per-query economics.
- **Spammer detection:** Raykar & Yu (2012), *Eliminating Spammers and Ranking Annotators*,
  JMLR 13:491–518 — label-independence **spammer score**; transplant to flag a cheap LLM
  whose plant list is uncorrelated with reality. Maps to a "constant column" intrinsic check.
- **2024–2026 LLM-as-annotator frontier (anchor the framing here):**
  - Gilardi et al. (2023), PNAS 120(30) — LLMs as annotators.
  - **SkillAggregation** — Sun et al. (2025), ACL 2025 (arXiv:2410.10215): reference-free,
    learns each LLM judge's skill **with no ground truth**. Closest existing method to our need.
  - **Dependence-aware (the load-bearing 2026 caveat):** Balasubramanian et al. (2026),
    *Dependence-Aware Label Aggregation for LLM-as-a-Judge via Ising Models*, arXiv:2601.22336
    — proves vanilla DS/majority is **strictly suboptimal** for LLM judges because errors
    correlate. CARE (arXiv:2603.00039) — confounder-aware aggregation.

## 3. Positive-Unlabeled (PU) learning — the presence-only anchor

"Absent from OSM/Wikipedia" ≠ "does not exist" → positives + unlabeled, no negatives.
Statistically identical to ecology's presence-only / presence-background problem.

- **Anchor:** Elkan & Noto (2008), *Learning Classifiers from Only Positive and Unlabeled
  Data*, KDD 2008 — under **SCAR**, the learned `g(x)=p(s=1|x)=c·p(y=1|x)`; recover truth by
  dividing by the **coverage frequency `c`** (estimable from a validated positive subset).
- **Deep PU:** Kiryo et al. (2017), nnPU, NeurIPS 2017 — needs class prior π.
- **Prior/frequency estimation:** Ramaswamy et al. (2016) KM1/KM2; du Plessis/Christoffel
  (2015); Jain et al. (2016) AlphaMax. Survey: Bekker & Davis (2020), Machine Learning.
- **Drop SCAR (matches our bias):** **PULSNAR** — Shrestha & Saul (2024/2025), PeerJ CS /
  arXiv:2303.08269 — labeling propensity varies by instance (**SNAR**). Registry inclusion is
  *not* uniform (large/notorious plants over-represented) → SNAR fits OSM/Wikipedia.
- **Ecology equivalence:** Ward et al. (2009), *Presence-Only Data and the EM Algorithm*,
  Biometrics 65:554–563 (needs a prevalence anchor); Fithian & Hastie (2013) finite-sample
  equivalence of MaxEnt / Poisson-process / logistic. Same identifiability gap: no absolute
  rate without an external prevalence anchor.

## 4. Source dependence / copy detection — anchor contamination

Because OSM/Wikipedia are provably in LLM training data, agreement-with-anchor is
**regurgitation, not independent corroboration**, and multiple LLMs agreeing is **correlated
failure**.

- **Anchor:** Dong, Berti-Équille, Srivastava (2009), *Integrating Conflicting Data: The Role
  of Source Dependence*, PVLDB 2(1):550–561 — copied agreement must not count as independent;
  joint estimation of dependence and truth. Companion: copy detection in a dynamic world
  (PVLDB 2(1):562–573); knowledge fusion (Dong et al. 2014, arXiv:1503.00302).
- **LLM memorization / contamination:** Carlini et al. (2023), *Quantifying Memorization*,
  ICLR 2023 (arXiv:2202.07646) — memorization grows with scale, **duplication**, context;
  web-duplicated facts (Wikipedia/OSM) are the most memorized. Surveys arXiv:2406.04244,
  arXiv:2502.14425.
- **Geospatial-specific proof:** **GeoLLM** — Manvi et al. (2024), ICLR 2024
  (arXiv:2310.06213) — OSM knowledge demonstrably resides in LLM weights. Geospatial
  hallucination: arXiv:2507.19586 (2025).
- **Correlation-aware LLM fusion:** *Correlated Errors in LLMs* (2025, arXiv:2506.07962) —
  LLMs more correlated with each other than with ground truth, highest within developer/
  architecture family. *Auditing behavioral entanglement & reweighting verifier ensembles*
  (2026, arXiv:2604.07650). *Information-theoretic LLM ensemble selection* (2026,
  arXiv:2602.08003) — adding a correlated model contributes little/negative info.

## 5. Capture–recapture / multiple-systems estimation (completeness, missed MW)

Each inventory (OSM, Wikipedia, tracker, LLM-fusion) is a "list"; overlap identifies capture
probability; the all-zero cell is the **dark figure** of plants present in none.

- **Anchors:** Lincoln–Petersen + **Chapman (1951)** bias correction; **log-linear** for ≥3
  lists — Fienberg (1972), Biometrika 59(3):591–603; Bishop, Fienberg, Holland (1975).
  Heterogeneity-robust **lower bound:** Chao (1987), Biometrics 43:783–791.
- **Best entry point / review:** Bird & King (2018), *Multiple Systems Estimation to Inform
  Public Policy*, Annual Review of Statistics 5:95–118 (PMC6055983).
- **Off-the-shelf for 4 sparse lists:** **LCMCR** — Manrique-Vallier (2016), Biometrics
  72(4):1246–1254 (R package) — Dirichlet-process latent classes, handles "small plants
  missed by everyone" (heterogeneity). Bayesian model averaging: Lum, Price, Banks (2010).
- **Identifiability caveats (must cite):** Manrique-Vallier (2024), *The central role of the
  identifying assumption*, Biometrics 80(1):ujad028 — extrapolation to the unobserved cell
  rests on an **untestable** assumption. Chan, Silverman, Vincent (2020/2021), JASA —
  non-overlapping list pairs make N̂ unbounded. Linkage error: Sadinle (2018), AoAS 12(2).
- **Modern ML CR:** doubly-robust — Das et al. (arXiv:2104.14091); many-lists+heterogeneity
  conditional log-linear (arXiv:2407.03539, 2024). Software-defect analogue (inspectors =
  lists): Briand et al. (2000), IEEE TSE; warning — **few detectors ⇒ all CR underestimate**.
- **Missed MW (the genuine gap):** standard CR estimates a *count*. Do **not** use
  count × mean-MW (missingness is size-correlated: big plants on every list). Recommendation:
  **stratify by capacity class, run CR (Chao lower bound + LCMCR) within each stratum, sum the
  per-stratum missed MW, bootstrap the interval**; report as a lower bound. This step is
  under-served by the literature and is where the paper's methodological novelty lives.

## 6. Imprecise probability / evidence fusion (sparse, conflicting channels)

- **Anchors:** Dempster–Shafer (Shafer 1976); Walley (1991) imprecise probabilities / credal
  sets (honest intervals when one source has too few observations for a point posterior);
  possibility theory (Dubois & Prade) — clean conjunctive (trust all) vs disjunctive (trust
  at-least-one) knob; **Subjective Logic** (Jøsang 2016) — explicit **uncertainty mass** that
  shrinks with evidence (Beta/Dirichlet count semantics), with trust-fusion & discounting.
- **Load-bearing caveat:** normalized **Dempster's rule misbehaves under high conflict**
  (Zadeh counterexample). For a **veto** channel prefer **Yager** (conflict mass → ignorance),
  **Dubois–Prade disjunctive**, or **Subjective-Logic discounting**. Robust-rules synthesis:
  Destercke & Burger, Information Fusion (2010).
- **Recent evidential fusion w/ learned reliability:** CAEFN (arXiv:2408.13123, 2024) —
  learnable per-view **discount factors**; deep evidential fusion w/ reliability learning,
  Information Fusion (2024, hal-04681852). Evidential semi-supervised label aggregation:
  Abassi & Boukhris (2019). Design pattern for our **two independent channels** (intrinsic
  model-free veto + consensus): reliability-discounting before fusion (no named paper does
  exactly this two-channel-with-veto setup, to our knowledge).

## 7. Active / sequential source selection under cost (diminishing marginal info)

- **VoI / Bayesian experimental design:** Lindley (1956), Ann. Math. Stat. 27(4); review
  Chaloner & Verdinelli (1995), Statistical Science 10(3). Modern amortized: Foster et al.,
  VBOED (NeurIPS 2019, arXiv:1903.05480), **DAD** (ICML 2021, arXiv:2103.02438) — a learned
  policy that picks the next design (which model to run) in one forward pass.
- **The right backbone:** **Adaptive submodularity** — Golovin & Krause (2011), JAIR
  42:427–486 — greedy "highest VoI-per-cost next source" is **(1−1/e)-competitive** under
  diminishing returns; cost-benefit / submodular-cover variant gives the stopping target.
- **Cold-start an un-run model's reliability (hierarchical):** Hierarchical Knowledge Gradient
  — Mes, Powell, Frazier (2011), JMLR 12; **LRMF** (lineage, arXiv:2504.19811, 2025) and
  **Sloth** (size/compute scaling-law covariates, arXiv:2412.06540, 2024) — predict a never-run
  variant's quality from **family / size / version**.
- **Stopping:** *Optimal Stopping for Sequential Bayesian Experimental Design* (arXiv:2509.21734,
  2025) — MDP; stop when expected info gain no longer covers marginal cost. Tie to
  estimated remaining missed MW (§5). Budgeted best-arm: combinatorial pure exploration
  (Chen et al. 2014; arXiv:2310.15681).

## 8. Domain / application — must-cite related work

- **Fusion spine:** GEM **Global Integrated Power Tracker** (116k multi-fuel units) + GEM
  **Global Coal Plant Tracker** (coal ≥30 MW, bi-annual). WRI **Global Power Plant Database
  v1.3** — Byers et al. (2018), WRI Technical Note (CC BY 4.0; **frozen ~2018**, a coverage-
  bias / staleness argument for an LLM refresh).
- **Prior art of database fusion (cite & contrast):** **powerplantmatching** — Gotzens et al.
  (2019), *Energy Strategy Reviews* 23:1–12 (DOI 10.1016/j.esr.2018.11.004; arXiv:1809.00974)
  — "appears in ≥2 sources" matching rule = the dedup/corroboration problem LLMs extend.
- **Downstream consumers (closely-related projects — cite unconditionally):** **PyPSA-Earth**
  — Parzen et al. (2023), *Applied Energy* 341:121096; **PyPSA-VN** — Schlott et al. (2020),
  IEEE (doc 9303096).
- **Emissions/asset cross-check:** Climate TRACE (arXiv:2511.19277, 2025); independent
  assessment Gurney et al. (2024), ERL 19(11):114062 — non-AI estimates off by −50%.
- **OSM coverage bias:** Arderne et al. (2020), *Predictive mapping of the global power
  system*, Scientific Data 7:19 — open coverage degrades in developing regions (much of ASEAN).
- **ASEAN recency bias:** GEM *Boom and Bust Coal 2025* — Vietnam fleet very young (88% of
  units <10 yr) → systematically missed by 2018-frozen GPPD. State with epistemic humility
  ("we did not find a dedicated ASEAN-completeness study").
- **LLMs for energy inventories:** energy-policy extraction (arXiv:2403.12924, ~85–90%);
  HalluLens (ACL 2025, arXiv:2504.17550) — extrinsic fabrication = fabricated facility entries;
  KG-construction failure modes (PMC12237976).

---

## The 5 most load-bearing references to cite first

1. **LTM** — Zhao, Rubinstein, Gemmell (2012), PVLDB 5(6) — the multi-truth two-sided-error backbone.
2. **Dependence-aware LLM aggregation** — Balasubramanian et al. (2026), arXiv:2601.22336 — proves
   naive DS over correlated LLMs is suboptimal; the must-cite caveat. (+ GeoLLM, ICLR 2024, as the
   evidence that the anchor is in the training data.)
3. **PULSNAR** — Shrestha & Saul (2024/2025), arXiv:2303.08269 — PU under non-uniform (SNAR)
   anchor coverage; the right frame for the presence-only registry. (+ Elkan & Noto 2008 anchor.)
4. **LCMCR** — Manrique-Vallier (2016), Biometrics 72(4) — completeness / missed-capacity estimation
   for the 4 sparse, heterogeneous lists. (+ Manrique-Vallier 2024 identifiability caveat.)
5. **Adaptive submodularity** — Golovin & Krause (2011), JAIR 42 — the near-optimality license for
   greedy VoI-per-cost active model selection with a principled stopping rule.

## Verification caveats

Publisher pages (Wiley/ScienceDirect/IOP/arXiv-abs/Nature) returned HTTP 403 to automated fetch;
load-bearing items were cross-confirmed against ≥2 independent sources. Re-check exact volume/page
and full author lists before typesetting for: the 2024–2026 arXiv preprints (LRMF 2504.19811, Sloth
2412.06540, the dependence-aware/CARE papers, optimal-stopping 2509.21734), GTM/QDB-2012, the
Computing-2024 multi-truth paper, PyPSA-VN (IEEE doc 9303096), and powerplantmatching page range.
