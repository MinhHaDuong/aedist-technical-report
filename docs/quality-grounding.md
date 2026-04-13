# Quality grounding: what do we mean by "quality" for AI-produced statistics?

*Working document — supports ticket 0075 and the journal article.*

## Purpose

This document maps the project's operational metrics to two external
frameworks: philosophy of science and professional codes for statisticians.
The goal is to answer honestly: are our metrics measuring the right things,
and where are the gaps?

The project asks whether AI can produce structured energy statistics at
production quality. "Production quality" is not self-defining. Before
optimizing a prompt (ticket 0075), we need to know what we are optimizing
*for* in terms that a statistician or a philosopher of science would accept.

---

## 1. What we actually measure

The evaluation pipeline computes the following over plant-level
reconciliation between system output and a 164-plant expert-compiled
reference (`data/reference/vietnam_thermal_v1.csv`):

| Metric | Definition | Source |
|--------|-----------|--------|
| **Coverage (recall)** | n_matched / n_reference | `metrics.py:61` |
| **Precision** | n_matched / n_system | `metrics.py:62` |
| **F1** | Harmonic mean of coverage and precision | `metrics.py:63` |
| **Fuel/status/province accuracy** | Binary match rate on attributes, matched pairs only | `metrics.py:73-105` |
| **Capacity match rate** | Fraction of matches without capacity difference | `metrics.py:77` |
| **Evidence score (0–4)** | Per-plant source quality rubric | `verify.py:140-172` |
| **Error counts** | Hallucinated plants, missed plants, wrong attributes | `metrics.py:79-89` |

Matching uses global MILP assignment (`matching/lp.py`) with fuzzy name
similarity (threshold 90/100) and capacity-weighted costs, solved to
optimality by CBC.

Bootstrap 95% CIs (n=10,000 resamples, seed=42) are computed for F1
in table generation (`stats.py:11-36`). Two-way ANOVA decomposes F1
variance into model, method, and interaction terms
(`tabulate_variance.py`).

---

## 2. Philosophy of science grounding

### 2.1 Empirical adequacy (van Fraassen)

A theory is empirically adequate if it "saves the phenomena" — if its
observable consequences match reality. Our extracted inventory must match
the real power system.

**What we do well.** Reconciliation against a reference inventory is
exactly an empirical adequacy test: does the system's picture of reality
match an independently observed one?

**Gap: the reference itself is not independently verified.** The
164-plant reference is a single expert's compilation from government PDFs.
No second reviewer, no stated audit trail from source document to row,
no temporal snapshot date. We test empirical adequacy against one
observer's picture, not against reality.

*Fixable?* **Yes.** The GEM (Global Energy Monitor) database provides an
independent 153-plant inventory (`data/reference/gem_thermal.csv`). A
three-way reconciliation (system vs. expert vs. GEM) would measure
agreement between two independent references and identify where the
*reference* is wrong, not just the system. This is a bounded task.

### 2.2 Falsifiability and corroboration (Popper)

A claim is scientific if it can in principle be shown false. An extracted
datum is scientific if a source exists that could contradict it. The
evidence rubric operationalizes this:

| Score | Epistemic status |
|-------|-----------------|
| 0 | Fabricated — the source *was* checked and found false |
| 1 | Unfalsifiable — no source offered, nothing to check |
| 2 | Weakly falsifiable — one secondary source (may be derivative) |
| 3 | Falsifiable — one primary source identified by heuristic (domain, text pattern) |
| 4 | Confirmed — at least one primary source validated (HITL or factual cross-check) |
| 5 | Corroborated — two *independent* primary sources confirmed |

**Revised rubric (proposed).** The original 0–4 scale conflates two
distinct steps: identifying a source as "primary" (heuristic,
automatable) and confirming that two sources are *independent*
(requires domain knowledge, often HITL). The revised 0–5 scale
separates them. The pilot operates at levels 3–4; level 5 is a
long-term research goal. See `verification_methods.tex`
§source-independence for the full discussion.

**Why independence is hard.** In the Vietnamese energy sector, information
flows create hidden dependencies between sources:

- **MOIT → Energy Institute → PDP8**: The Ministry commissions the
  Energy Institute for technical analysis. PDP8 numbers come from IE.
  Citing both PDP8 and an IE report is *not* two independent sources.
- **EVN / gencos / EVNNPT**: The original source of operational data.
  Any document citing installed capacities ultimately traces back to EVN.
  EVN annual reports and PDP8 are not independent for existing plants.
- **Academic literature**: Papers on PyPSA-VN may be independent *if*
  they collected their own data. Many just cite PDP or EVN.
- **Legislature / Party**: National Assembly resolutions and Party
  documents may contain independent figures, especially for planned
  investments (separate decision chains from MOIT/IE).
- **GSO / Customs**: The General Statistics Office and customs collect
  data through distinct channels (fuel imports, declared production).
  Potentially independent for operational capacity but blind to planned.
- **International (GEM, IEA, IRENA)**: GEM does its own verification
  (satellite imagery, local reporting). IEA/IRENA may repackage
  national submissions.
- **Physical verification**: Satellite imagery and OpenStreetMap can
  confirm a plant *exists* but not its nominal capacity.

Reaching score 5 for every plant requires a dependency graph of the
sector's data producers — a research contribution in itself.

**What we do well.** The five-mode verification protocol (unverified →
tool → self → cross → web) is a systematic escalation of falsification
effort. The precision-coverage tradeoff at each threshold makes the cost
of corroboration visible.

**Gap 1: source citations are classified but not verified.** The pipeline
classifies sources by URL domain regex and text patterns
(`verify.py:66-96`) but never issues an HTTP request to check that the
URL exists, returns a 200, or contains the claimed content. A model that
cites "Decision 1509/QD-BCT" gets credit for a primary source even if
the decision number is fabricated, as long as the format matches.

*Fixable?* **Partially.** URL existence checks (HTTP HEAD) are trivial
to add. Content verification is harder but a spot-check on a random
sample is feasible (ticket 0079).

**Gap 2: "independent" is undefined.** The original score 4 says "two
independent primary sources" without defining independence. In practice,
most Vietnamese energy sources trace back to EVN or IE/MOIT. Automatic
independence assessment is not feasible without the dependency graph
described above. HITL validation at least by sampling is required for
honest score 4+ claims.

*Fixable?* **Partially.** The revised rubric (0–5) makes the gap
explicit. Score 4 (one confirmed primary) is achievable with HITL
spot-checks. Score 5 (two independent confirmed) requires the
dependency graph — out of scope for this pilot but mapped as a
research direction.

### 2.3 Reproducibility as intersubjective agreement

A result is robust if independent observers agree. In our context,
"observers" are LLM instances. The cross-model criterion (min-of-5)
from ticket 0075 formalizes this: if only one model produces a result,
it is not robust knowledge.

**What we do well.** Multiple models × multiple runs give a distribution,
not a point. Bootstrap CIs and paired tests quantify agreement.

**Gaps:**

1. **Temperature not controlled across all experiments.** Some runs use
   unspecified temperature, making "replication" ambiguous — is variance
   from the prompt or the sampling? *Fixable:* set temperature=0 for
   deterministic runs, or document and measure the temperature effect.

2. **Bootstrap seed documented in code but not in output tables.** A
   reader cannot reproduce exact CIs. *Fixable:* add seed to table
   metadata.

3. **Core metrics (precision, recall, F1) are point estimates in
   `metrics.py`.** CIs are only added downstream in tabulation.
   *Fixable:* already addressed by ticket 0042, but the per-plant
   attribute accuracies still lack intervals.

### 2.4 Theory-ladenness of observation (Kuhn, Hanson)

The prompt defines what counts as a "power plant," which attributes
matter, what schema to emit. The prompt *is* the theoretical lens.
Optimizing the prompt is optimizing the lens through which we observe
the power system.

**Gap: ontological drift under optimization.** If the optimizer changes
what counts as a "plant" — merging units to inflate recall, splitting
complexes to inflate precision, redefining "operational" to include
"under construction" — it games the metric while corrupting the data's
meaning.

*Fixable?* **Yes.** Lock the CSV schema (column names, enum values for
fuel/status) and the reconciliation parameters *before* optimization.
The optimizer may change instruction text and structure, but not the
output ontology. Add a schema-validation gate to the evaluation loop.

### 2.5 Measurement theory (Tal, Mari)

Our metrics are measurements of measurement quality. They need defined
measurands, stated uncertainties, and calibration.

**What we do well.** F1, precision, recall have clear mathematical
definitions. Bootstrap CIs provide uncertainty estimates. ANOVA
decomposes variance sources.

**Gaps:**

1. **No multiple comparison correction.** With ~256 conditions
   (32 models × 8 methods), no family-wise error control (Bonferroni,
   FDR) is applied. *Fixable:* add to `stats.py`.

2. **ANOVA assumptions not tested.** Normality of residuals and
   homogeneity of variance are assumed, not checked. With n=2–3 per
   cell, tests have very low power. *Fixable:* add diagnostic plots
   or switch to non-parametric alternatives (Kruskal-Wallis).

3. **Headline result F1=98.8% based on n=1.** The best decomposition
   result (DeepSeek V3.2) has no CI at time of reporting. *Fixable:*
   run more replicates.

---

## 3. Professional conduct grounding

### 3.1 UN Fundamental Principles of Official Statistics (A/RES/68/261)

The project explicitly frames itself as producing economic statistics
for countries with weak statistical offices (report.tex:56). This
activates the UN Fundamental Principles:

| Principle | Requirement | Our status |
|-----------|------------|------------|
| 1. Relevance | Statistics serve the community impartially | **Met:** open pipeline, open data, open models |
| 2. Professional standards | Scientific methods, transparency | **Partially met:** methods documented, but temperature uncontrolled, ANOVA assumptions unchecked |
| 3. Accountability | Methods presented transparently | **Met:** code and data are open-source |
| 4. Misuse prevention | Comment on erroneous interpretation | **Gap:** no guidance on how to interpret AI-produced statistics vs. official statistics |
| 5. Data sources | May include non-statistical sources | **Directly relevant:** this is literally what we do — extracting statistics from planning documents |
| 6. Confidentiality | Individual data protected | N/A (public infrastructure data) |
| 7. Legal framework | Statistical laws govern | **Gap:** no discussion of legal status of AI-produced statistics |
| 8. Coordination | Avoid duplication | **Partial:** reference comparison with GEM exists but not formalized |
| 9. International standards | Use international classifications | **Gap:** no mapping to ISIC, ISCO, or UN energy commodity codes |
| 10. International cooperation | Bilateral and multilateral | **Future:** PyPSA-ASEAN framing implies regional cooperation |

### 3.2 IMF Data Quality Assessment Framework (DQAF)

The DQAF defines quality along six dimensions. Mapping to our metrics:

| DQAF dimension | Our metric | Status |
|---------------|-----------|--------|
| **Accuracy** | Precision, evidence score, hallucination count | **Measured.** But source citations are classified, not verified. |
| **Completeness** | Recall against 164-plant reference | **Measured.** But only for thermal/Vietnam. |
| **Timeliness** | Wall-clock time (#5) | **Recorded but not optimized.** |
| **Coherence** | *Internal consistency* | **Measured** (`coherence.py` + `tabulate_coherence.py`): row-level (schema/business rules), cross-row (dedup), aggregate (control totals). Coherence rate reported per model in `tab_coherence.tex`. See §4.1 below. |
| **Comparability** | Cross-model (#1), cross-country (future) | **Partially measured.** Cross-model exists; cross-country is ticket 0075 Phase 3. |
| **Accessibility** | Cost (#6), open pipeline | **Measured and met.** |

### 3.3 ASA Ethical Guidelines for Statistical Practice

> "Be transparent about the basis of any inferences... report findings
> and interpretations that reflect the data accurately."

**Gap: selective reporting risk.** The headline F1=98.8% comes from the
best model on the best method with n=1. The report does present the full
model×method matrix (good), but the abstract and perspectives foreground
the best case. If the optimizer produces a prompt that achieves high F1
by ignoring hard cases (small plants, ambiguous status), we must report
that, not just the headline.

*Fixable?* **Yes.** Report the *distribution* of per-plant evidence
scores, not just the aggregate. Flag which plants consistently fail
across models. Make the error analysis a first-class output alongside
the accuracy table.

### 3.4 ISI Declaration on Professional Ethics

> "Pursue objectivity... acknowledge limitations... make the data
> available for independent analysis."

**What we do well.** Code, data, and reference are open-source. The
report explicitly lists limitations (single domain, limited sample size,
temperature uncontrolled, reference not error-free).

**Gap: the "not error-free" reference is not quantified.** Acknowledging
the reference has errors without estimating the error rate is honest but
incomplete.

*Fixable?* **Yes.** The three-way reconciliation (system vs. expert
vs. GEM) would estimate reference disagreement rate.

---

## 4. Coherence: data model and scope

### 4.1 Pilot data model (v1, this paper)

One row per asset. One snapshot in time. No scenarios, no temporal
panel. The reference dataset (`vietnam_thermal_v1.csv`) is a single
PDP8-vintage inventory.

Coherence verification is **per-document**: take one source document,
check that the extracted rows attributable to that document are
internally consistent and sum to what the document states. Deviations
must be explained in notes, not silently absorbed.

Three levels (`src/aedist/coherence.py`):

- **Row-level:** each row passes schema and business rules (capacity
  > 0, known fuel, known province, no retired plant with future COD).
- **Cross-row:** no duplicates (same name + same province).
- **Aggregate:** extracted capacity sums match control totals from
  the same document, within tolerance. Control totals = known
  macro-aggregates that micro-data must sum to (official statistics
  term).

### 4.2 Target data model (v2+, production / PyPSA-ASEAN)

One master table. Each row is one asset × one year × (for future
years) one scenario. Rows are sourced but not conditioned on source
— the table is the best-known state of the world, not a mirror of
one document.

```
name, year, scenario, capacity_mw, fuel, status, province, source_ref, notes
Pha Lai, 2023, -, 440, coal, operational, Hai Duong, EVN AR 2023,
Song Hau 2, 2025, PDP8, 0, -, cancelled, Hau Giang, PDP8, "coal→cancelled in PDP8"
Song Hau 2, 2025, PDP7A, 2000, coal, constructing, Hau Giang, PDP7A, "still in PDP7A"
```

Coherence verification is still per-document (filter the master
table to one document's rows, check sums against that document's
control totals), but the master table carries the full history.

**Out of scope for v1:**
- **Cross-document fusion.** PDP7 lists a coal plant at 1200 MW;
  PDP8 changes it to gas at 900 MW. The master table carries both
  rows (different year/scenario). The v1 pilot sees only the PDP8
  snapshot.
- **Measurand ambiguity.** A plant authorized at 1000 MW may be
  built at 1100 MW (within administrative tolerance). The
  `capacity_mw` column in v1 does not distinguish planned vs
  as-built vs nameplate vs net. This is a metrology problem: the
  measurand is undefined. The article should state which capacity
  concept the reference uses.
- **Temporal reconciliation.** Tracking status changes across
  document versions (planned → constructing → operational →
  retired) requires the year dimension in the master table.

The v1 coherence checks (`coherence.py`) are designed to work
unchanged on a single-year slice of the v2+ master table.

---

## 5. Gaps revealed — summary and fixability

### Non-negotiable gaps (must fix for the article)

| # | Gap | Framework | Fix | Effort |
|---|-----|-----------|-----|--------|
| G1 | **Internal consistency** — **measured** (`coherence.py` + `tabulate_coherence.py`): row-level, cross-row, aggregate checks run on all RAG extractions; coherence rate reported per model in the journal paper (table `tab_coherence.tex`). Control totals from PDP8 still pending for aggregate checks. | DQAF: coherence | Populate ControlTotal instances from PDP8 aggregates | Small — data entry |
| G2 | **Source citations classified but not verified** — no URL existence check, no content check | Popper: falsifiability | Add HTTP HEAD checks; spot-check content on random sample | Small (HEAD) / Medium (content) |
| G3 | **Tool verification threshold mismatch** — paper says 70/100, code uses 90/100 | Scientific integrity | Fix the code or fix the paper — they must match | Trivial |
| G4 | **Headline F1=98.8% based on n=1** | Measurement theory | Run 2 more replicates of DeepSeek V3.2 decomposition | Small — one API call |

### Important gaps (should fix, strengthen the article)

| # | Gap | Framework | Fix | Effort |
|---|-----|-----------|-----|--------|
| G5 | **Reference not independently verified** — single expert, no audit trail | Empirical adequacy | Three-way reconciliation with GEM | Medium — needs careful matching |
| G6 | **No multiple comparison correction** | Measurement theory | Add FDR/Bonferroni to stats.py | Small |
| G7 | **ANOVA assumptions not tested** | Measurement theory | Add residual normality test, or switch to rank-based | Small |
| G8 | **Temperature not controlled** across experiments | Reproducibility | Document which runs used which temperature; set t=0 for future deterministic runs | Small |
| G9 | **No mapping to international classifications** (ISIC, UN energy codes) | UN Principle 9 | Add classification column to reference CSV | Medium |

### Acknowledged but out-of-scope for current article

| # | Gap | Framework | Why out of scope |
|---|-----|-----------|-----------------|
| G10 | **Temporal coherence** — no versioned reference, no tracking of status changes over time | DQAF: coherence | Requires longitudinal data (multi-year extractions) |
| G11 | **Ontological drift under optimization** | Theory-ladenness | Becomes relevant only when optimizer (ticket 0075) runs; mitigated by schema-lock |
| G12 | **Legal status of AI-produced statistics** | UN Principle 7 | Policy question, not a measurement question |
| G13 | **Cross-country / multilingual transfer** | Comparability | Ticket 0075 Phases 2–3; requires corpora we don't have yet |

---

## 6. Verdict

Grounding in these frameworks reveals **four gaps that must be fixed**
(G1–G4) and **five that should be fixed** (G5–G9). None are fatal to the
project. All are bounded, concrete tasks — not architectural redesigns.

The honest picture:

- **What we do well:** open pipeline, explicit metrics with clear
  definitions, five-mode verification protocol, variance decomposition,
  bootstrap CIs (albeit late), acknowledgment of limitations in the
  report text. The evidence rubric is a genuine operationalization of
  epistemic status.

- **What we must fix:** the coherence dimension (G1) is entirely missing
  and easy to add. The source verification gap (G2) undermines the
  evidence rubric that anchors the whole quality argument. The threshold
  mismatch (G3) is embarrassing but trivial. The headline result
  without a CI (G4) is a reviewer magnet.

- **What makes the article stronger:** the three-way reference
  reconciliation (G5) would transform a weakness ("our reference is
  one person's work") into a contribution ("we quantify inter-annotator
  agreement for energy infrastructure inventories"). The international
  classification mapping (G9) connects the work to the official
  statistics community that is the natural audience.

The core claim — that AI can produce structured energy statistics at
production quality — survives the grounding. But "production quality"
must be stated with caveats: production quality *for a feasibility
pilot*, not production quality in the sense of a national statistical
office. The article should be explicit about which DQAF dimensions are
satisfied and which are future work.

---

## 7. References

- van Fraassen, B.C. (1980). *The Scientific Image*. Oxford.
- Popper, K. (1959). *The Logic of Scientific Discovery*. Routledge.
- Kuhn, T.S. (1962). *The Structure of Scientific Revolutions*. Chicago.
- Tal, E. (2017). "Measurement in Science." *Stanford Encyclopedia of Philosophy*.
- Mari, L. et al. (2012). "Measurement, Models, and Uncertainty." *IEEE T-IM*.
- Wang, R.Y. & Strong, D.M. (1996). "Beyond Accuracy: What Data Quality Means to Data Consumers." *JMIS* 12(4).
- United Nations (2014). *Fundamental Principles of Official Statistics*. A/RES/68/261.
- IMF (2003). *Data Quality Assessment Framework*.
- ASA (2022). *Ethical Guidelines for Statistical Practice*.
- ISI (2010). *Declaration on Professional Ethics*.
