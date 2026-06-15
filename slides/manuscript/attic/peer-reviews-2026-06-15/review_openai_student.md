# Peer review — openai (openai/gpt-5.5), persona: student

## Summary

This paper introduces a benchmark for an unusually concrete and policy-relevant LLM/RAG/agent task: reconstructing a national register of Vietnam’s thermal power plants, scored against a 177-row hand-compiled reference inventory. The main empirical findings are that memory-only LLMs recover far less than even Wikipedia coverage would suggest (§5, Figure 3), frontier web-enabled agents still fall well short (§6, Figure 6, Table 6), curated documents matter more than model choice (§6), simple multi-run fusion helps (§7), and a durable solution likely needs an auditable knowledge base rather than a one-shot or “deep research” prompt (§9).

I found the paper genuinely useful. The benchmark target is much more realistic than many QA/RAG benchmarks: it requires open-world enumeration, entity resolution, lifecycle-status distinctions, multilingual source discovery, and provenance. The paper’s strongest contribution is the framing of “statistical-register construction” as a computable LLM benchmark with accuracy, coherence, provenance, and temporality dimensions (§3). The long-tail characterization in Figure 1 and Table 1 is also valuable: it explains why the task is not just “ask for the famous plants.” The fusion results in §7 are especially promising and could become the basis for a practical semi-automated register-building workflow.

That said, I would recommend major revision before treating the paper as an archival benchmark paper. The central claims are compelling but sometimes stronger than the measurements support. The gold reference needs more independent validation; the “Wikipedia coverage bar” is conceptually shaky; the scoring mostly measures row-level recognition rather than the full four-dimensional quality bar; the multi-turn-agent result is heavily confounded by a particular harness; and several sections mix benchmark, empirical product comparison, and research-program argument in ways that make causal interpretation difficult.

---

## Strengths

1. **A real, high-value benchmark task.**  
   The task in §1–§3 is much closer to what analysts actually need than typical factoid QA: build an asset-level statistical table with source traceability and temporal status. The “researcher’s perimeter” discussion in §2 is particularly good: proposed, cancelled, and abandoned projects are not noise; they are analytically meaningful for energy-transition studies.

2. **Clear articulation of the long-tail problem.**  
   Figure 1 and Table 1 are among the strongest parts of the paper. They show that operational plants are relatively visible while proposed/cancelled/planned assets are sparse and volatile. This explains why naive web search or parametric recall underperforms.

3. **Good distinction between output quality and method quality.**  
   The three-level distinction in §8 — method quality, run quality, model quality — is useful. It avoids the common mistake of equating “one impressive table” with a reliable register-building method.

4. **Practical insight that documents matter more than model choice.**  
   The documents condition in §6 is important. Table 6 shows Qwen improving from F1 0.37 to 0.62 and Mistral from 0.49 to 0.59 when given documents, while Anthropic barely improves. This supports the paper’s main practical conclusion: invest in the evidence corpus and knowledge-engineering pipeline.

5. **Fusion as a concrete path forward.**  
   §7’s observation that union improves recall and two-model agreement improves precision is exactly the kind of “boring but useful” result that can move this from benchmark to system design. This is more convincing than the claims about agentic reasoning.

---

## Major concerns

### 1. The gold reference is central, but its independence and auditability are underdeveloped

The paper’s entire empirical structure depends on the 177-plant reference. §2 and Annex B say it is hand-compiled, per-cell sourced, and version-locked, but the main body gives relatively little evidence about its own error rate. Since many benchmark conclusions turn on missed proposed/cancelled projects, the weakest part of the gold set is exactly the part most important to the paper.

The paper is admirably transparent that the author compiled the reference and that the author’s group seeded some reference-derived content into Wikipedia (§5, Acknowledgements). But this creates three issues:

- **No independent adjudication.** There is no second annotator, expert audit, or blind reconciliation of a sample of rows/cells.
- **Reference/source circularity.** Wikipedia coverage partly originates from the reference group, then becomes a “coverage bar” for model memory (§5, Figure 3).
- **Granularity ambiguity.** The paper uses phase-level matching in some places and plant-level language elsewhere. Table 2 notes one GEM row can match several reference phase rows. This is a serious benchmark-design issue, not merely a matching detail.

A modest but important improvement would be an independent audit of, say, 30–50 randomly sampled reference rows stratified by status, with row-existence and key-cell agreement rates reported in the main text.

### 2. The “Wikipedia coverage bar” claim does not fully follow

§5 argues that because Wikipedia contains 130 of the 177 reference assets, models “could be expected” to recover this coverage from parametric memory. Figure 3 then uses the dotted Wikipedia line as a benchmark for memory-only models.

I am not convinced this is a valid ceiling or expectation without qualification. A model may not memorize long tables; training-data filtering may remove or downweight Wikipedia tables; cutoff dates vary; and the prompt demands primary-source-style inventories while simultaneously forbidding web search. More importantly, the paper itself says the proposed/planned tail partly postdates the 2019 Wikipedia injection. So “below Wikipedia = failure to retrieve known facts” is too strong.

A better framing would be:

- Wikipedia coverage is an **availability indicator**, not a recall expectation.
- Built-fleet Wikipedia coverage is a stronger contamination/availability check than pipeline coverage.
- The parametric experiment tests whether models can convert known public text into a structured inventory, not whether the facts were certainly in the weights.

The current text in §5 sometimes acknowledges this nuance, but Figure 3 and the surrounding rhetoric still overstate the inference.

### 3. The four-dimensional quality framework is stronger than the actual measurements

§3 defines accuracy, coherence, provenance, and temporality. This is conceptually strong. But the empirical sections mostly measure:

- row-level F1 against the reference;
- some matched-row attribute accuracy in §5;
- citation presence / Source 2 presence in §6;
- reference-free heuristics for degenerate outputs.

The paper explicitly says provenance is “verifiable rather than verified” (§3), and §6 says rubric-scored §3 dimensions are out of scope. This is fine as a limitation, but the abstract and conclusion sometimes imply the systems are “scored on data-quality dimensions” more comprehensively than they are. Citation presence is not provenance quality; a fabricated but well-formatted citation would pass much of the current q3 scoring.

This matters because the paper’s central object is “research-grade statistical data.” If provenance is not verified and temporality is only shallowly scored, then the benchmark currently evaluates **structured enumeration plus citation-format behavior**, not full statistical-register quality.

Concrete suggestion: rename the current score components as “proxy metrics” and reserve “research-grade provenance” for a future verified-citation layer.

### 4. The reference-free reliability result is promising but not yet validated

Figure 5 is intriguing: weak models cluster as unreliable and inaccurate. But the claim “internal coherence metrics correlate with accuracy” is not cleanly supported as written.

In §5, a “good run” is defined as having no zero on twelve reference-free dimensions. That includes provenance and temporality proxies, not just coherence. Later, §7 says capacity variability tracks F1, but also says “the internal-coherence indicators we already compute carry no such signal,” which seems to contradict the abstract/introduction claim that internal coherence correlates with accuracy.

I would like to see:

- a clear list of which reference-free features are used in Figure 5;
- a correlation table or regression: F1 vs each feature, not just good-run count;
- out-of-sample validation, e.g. tune on Experiment 1 and test on Experiment 2, or tune on a subset of models and test on held-out models;
- confidence intervals given only five repeats per model.

Right now Figure 5 is best described as an in-sample diagnostic finding, not a validated reference-free accuracy estimator.

### 5. Experiment 2 does not isolate “agentic” capability from harness and prompt effects

The finding that the multi-turn harness degrades performance for three of four agents (§6, Figure 6, Table 6) is interesting, but I would be careful not to generalize it to “agentic systems” broadly.

The multi-turn condition differs from single-shot in several ways:

- agents design their own prompt and settings;
- an external classifier decides whether a report has been produced;
- the harness sends fixed ENCOURAGE/VERIFY/TERMINAL strings;
- budgets and status prefixes are introduced;
- some agents self-impose restrictive rules, e.g. Qwen’s dual-source filter (§6);
- prompts apparently changed during the run history, with single-shot sessions using an earlier shorter prompt according to Annex C.

Thus the result is more precisely: **this particular self-prompting multi-turn harness did not improve row-level F1 under these budgets.** That is still useful! But the current wording sometimes reads as a broader indictment of multi-step agentic workflows.

A stronger design would compare:

1. single-shot;
2. human-authored multi-step prompt;
3. self-designed multi-step prompt;
4. fixed retrieval/decomposition pipeline;
5. same pipeline with/without VERIFY pass.

### 6. The documents condition may be too close to the answer

§6 says handing agents a curated document set improves coverage and equalizes performance. This is one of the most important findings. But the main body should describe the document pack more concretely. Is it the 18-source corpus used to build the reference? Does it include PDP annex tables where most target rows are directly listed? Does it include any derived or near-derived reference artifacts? How many pages/tokens? Which source types? Vietnamese vs English?

If the document pack is essentially the evidence base from which the reference was constructed, the result becomes: “LLMs extract better when handed the right source documents.” That is still valuable, but it is different from showing that agents can discover and curate such documents themselves.

The phrase “curated reference pack” risks ambiguity: it could sound like the reference answer is being supplied. Please define it in §6, not only in annexes.

### 7. Matching and granularity choices may materially affect F1

The paper is appropriately aware of entity-resolution problems (§8), but I think they deserve more prominence in the main empirical claims. The LP matcher excludes province and fuel from matching, uses a rapidfuzz threshold tuned on this dataset, and struggles with combined-unit rows. Table 2 also admits phase/grain mismatches with GEM.

Because the task is plant-register construction, entity resolution is not a peripheral implementation detail; it is part of the scientific task. A model that reports “Kiên Giang 1 & 2” as one row rather than two may be wrong for the benchmark schema but not hallucinating. Conversely, fuzzy matching can hide distinct plants if names are similar.

I would like the main body to report sensitivity of headline F1 to:

- strict vs relaxed name matching;
- allowing one-to-many phase aggregation;
- excluding proposed/planned projects;
- built-fleet-only evaluation;
- manually adjudicated sample of false positives/false negatives.

### 8. Cost comparisons are suggestive but not yet methodologically stable

Figure 4 and Figure 7 are useful, but several cost claims need caveats. Vendor API prices, hidden reasoning tokens, search billing, prompt length, caching, and output verbosity differ substantially. Figure 4’s caption says “More expensive models discover more assets and return more stable results,” while §5 says “no monotonic relationship between API cost and F1 holds.” Those statements can both be locally true, but the paper should reconcile them.

Similarly, Table 6 shows Mistral single-shot with documents costing less than without documents, which is counterintuitive unless adapter billing/caching/search behavior explains it. The paper should avoid overinterpreting cost until the experimental cost surface is normalized.

---

## Section-specific comments

### §1 Introduction

The motivation is strong. The paragraph distinguishing fluent unsourced text from statistical facts is excellent. However, the contribution statement says “public gold reference” and “computable metric” but the benchmark is vulnerable to future training contamination because the gold is public. The paper says it treats contamination as a parametric ceiling rather than preventing it, which is an interesting design choice, but this makes it less like a reusable benchmark and more like a dated capability audit. I would state that tradeoff directly in §1.

### §2 Related work / empirical landscape

The open power-plant database discussion is useful but a bit narrow. Since the paper is about register construction, I expected more engagement with:

- statistical business registers and official-statistics quality frameworks;
- data integration / entity-resolution literature beyond powerplantmatching;
- truth discovery and data fusion literature earlier than §9;
- RAG evaluation and citation faithfulness benchmarks;
- web-agent benchmarks for open-ended collection tasks;
- Wikidata/OSM completeness literature.

Also, the comparison to GEM needs more precision. The paper references the GEM Coal Plant Tracker, but the target includes both coal and gas/LNG. Does the GEM comparison include GEM gas trackers or only coal? Figure 1 says GEM covers 157 thermal plants, which seems broader than coal. Please clarify.

### §3 Quality dimensions

This is one of the best sections. I especially like the separation of verifiable vs verified provenance and the treatment of temporality as part of the fact, not metadata.

But the scoring implementation does not yet meet the conceptual standard. I would explicitly label the current q3/q4 metrics as proxies. For example, “Source 2 present” is not corroboration unless the source is actually checked and independent.

### §4 AI capability landscape

Figure 2 is interesting but feels somewhat detached from the benchmark. The historical capability rollout does not directly explain the experimental design except to justify which systems are tested. I would shorten this section or move more of it to annex. The “Type-III error” articulation discussion is more relevant and should stay.

Also, some terminology is loose: “agency is the closure of that surface, when the tool-use set includes the model itself” is evocative but not operational. For the experiments, “agent” seems to mean vendor API with web search and reasoning plus, in one condition, a harness. I would define the operational condition more plainly.

### §5 Experiment 1

The experiment is valuable, but the prompt creates a potential impossibility: no web search, yet asks for a “primary-sourced” inventory and says “Never fabricate sources or URLs.” Refusals may be the epistemically correct behavior, as §8 notes. This means F1 = 0 for refusals mixes task compliance with epistemic caution.

The status-vocabulary mismatch is also important: the reference’s largest class is “Proposed,” but the prompt does not allow “Proposed.” This mechanically depresses status accuracy, and possibly row recall if models avoid uncertain planned assets. This should be treated as a design bug, not only a caveat.

Figure 3 is visually effective. I would add model-level means and confidence intervals or a table in the main text, because the figure is hard to read for exact values.

### §6 Experiment 2

The 2×2 design is promising, and Table 6 is central. I would bring Table 6 earlier and make it the anchor for the section. The narrative currently mixes coverage counts, medians, F1 means, costs, and provenance in a way that is hard to follow.

The documents condition deserves more detail in the main text. The multi-turn condition should be described more conservatively as a tested harness, not as “agency” in general.

The provenance discussion is useful, especially Figure S2, but Source 2 presence is not necessarily corroboration. The paper should say “second citation field present” unless independence/support has been verified.

### §7 Extensions

This section contains some of the paper’s most interesting ideas but reads like three mini-papers: difficulty analysis, reference-free screening, fusion, and system architecture. I would consider moving the validated quantitative pieces earlier and leaving architecture for §9.

Table 1 is important enough to appear before the experimental results, perhaps in §2 or §5, because it explains the benchmark composition.

The fusion result is strong. I would like to see the two-model agreement result in the main body with exact TP/FP/F1, not mostly annexed.

### §8 Discussion

This is thoughtful and unusually honest. The discussion of articulation vs coverage, matcher artifacts, refusal as evidence, and N=1 dataset limitation is exactly what the paper needs.

However, some limitations in §8 undercut stronger claims made earlier. For example, if articulation and matcher artifacts can materially affect F1, then §5–§6 should not treat F1 as cleanly measuring model knowledge or web-agent capability.

The “one case study, not a benchmark suite” paragraph is essential. I would move a shorter version of it into the introduction.

### §9 Future research

The knowledge-base architecture proposal is compelling. I agree with the central conclusion: an evergreen register should be a dated snapshot from an auditable claim log / knowledge base, not a direct model output.

The truth-discovery discussion is good, but I would cite more classic and recent data fusion/entity-resolution work. The paper currently jumps from Zhao et al. to LLM-correlated errors; that is right, but the broader literature on data fusion, source dependence, and capture-recapture should be more fully represented.

### §10 Conclusion

The conclusion is mostly well aligned with the evidence, especially the statement that sourcing matters more than stronger models. I would soften “agents with web access and extended reasoning enumerate at best around half the fleet” because OpenAI with documents reaches F1 0.77 and the metric is F1 rather than pure enumeration; also the “at best” depends on no-doc vs docs condition.

---

## Missing or underdeveloped related work

I would expect at least brief engagement with:

- **Data integration / truth discovery / source dependence:** Dong & Srivastava’s data fusion work; Galland et al. on corroboration; more on correlated-source truth discovery beyond the one cited item.
- **Entity resolution:** Fellegi-Sunter, Christen, Magellan/DeepMatcher-style entity matching, and recent LLM-based entity resolution.
- **RAG evaluation:** ARES, TruLens, DeepEval, RAGChecker, KILT-style grounded evaluation, FactScore/Attributable QA, citation precision/recall work beyond ALCE/RAGAS/Self-RAG.
- **Web-agent benchmarks:** WebArena, Mind2Web, BrowseComp, GAIA; the paper cites some but could better connect why this benchmark differs.
- **Official statistics/register production:** statistical business registers, Generic Statistical Business Process Model, DQAF beyond IMF, UN National Quality Assurance Framework.
- **Energy infrastructure datasets:** OpenInfraMap/OpenStreetMap power tagging, Global Energy Observatory if relevant, GEM gas/oil trackers if used, WRI GPPD limitations, national PDP datasets.

---

## Minor clarity and consistency issues

1. §5 says fourteen models; Annex B lists sixteen, then says the 14-model cohort drops two. The main text should explain this without requiring annex reading.
2. The bibliography appears to cite Balasubramanian et al. as 2020 in §9 but 2026 in the references.
3. Figure 4 caption and §5 text appear to disagree about whether cost correlates with coverage.
4. “PyPSA-ASEAN” in §1 and bibliography entry “PyPSA-ME” should be harmonized.
5. The paper sometimes uses “coverage,” “recall,” “recognized assets,” and “F1” interchangeably. Please keep them distinct.
6. “Corroboration” should be reserved for verified independent support, not merely a non-empty Source 2 cell.
7. The status taxonomy mismatch (“Proposed” absent from the prompt) should be fixed in future runs and noted more prominently as affecting cell-level status results.
8. Some figures are hard to read in the PDF extraction, especially Figures 3–5. Tables with model-level means would help.

---

## Numbered questions I would ask the authors

1. **Gold reference validation:** Has any independent domain expert audited the 177-row reference? If not, can you report a stratified audit of row existence and key attributes, especially for proposed/cancelled assets?

2. **Granularity:** What exactly is the unit of evaluation: plant, phase, project, unit group, or power center? How often do reference rows split what external sources report as one plant?

3. **Wikipedia bar:** Why should Wikipedia coverage be interpreted as an expected parametric-recall ceiling rather than merely public availability? Can you report results separately for the built fleet, where the contamination argument is strongest?

4. **Prompt impossibility:** In Experiment 1, how should a model satisfy “primary-sourced” and “never fabricate URLs” with web access disabled? Should refusals be scored separately from empty/incompetent outputs?

5. **Status vocabulary:** How much would status accuracy change if the prompt included the reference labels “Proposed” and “Planned”? Could this also affect row recall?

6. **Provenance verification:** Among cited Source 1/Source 2 cells in Experiment 2, what fraction actually support the row claim when manually checked on a sample?

7. **Document pack:** What exactly was in the curated document set in §6? Did it include the same source tables used to compile the reference? How many tokens/pages and what languages?

8. **Search behavior:** Do you have logs of which web pages each agent retrieved? If not, how can we distinguish search failure from extraction/synthesis failure?

9. **Multi-turn conclusion:** How much of the multi-turn degradation is due
