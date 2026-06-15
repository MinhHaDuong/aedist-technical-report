# Peer review — openai (openai/gpt-5.5), persona: grinchy

## Review

### Summary

The paper proposes a benchmark for evaluating whether LLMs and “agentic” systems can reconstruct a Vietnam thermal-power-plant register, using a 177-row hand-compiled reference and row-level F1 plus auxiliary quality dimensions: accuracy, coherence, provenance, and temporality. It reports two experiments: memory-only prompting of 14 models (§5) and web-enabled frontier agents under a 2×2 design with/without documents and single-shot/multi-turn protocols (§6), followed by post-hoc screening and fusion analyses (§7). The central conclusion is that current AI systems cannot produce a research-grade statistical register unaided; curated documents and fusion help, but an auditable knowledge-engineering pipeline is required.

The topic is worthwhile, but the submitted paper does not yet meet the methodological or evidentiary standard for a top-tier venue. The benchmark is built, tuned, interpreted, and partially contaminated by the same group; the experiments are small, weakly controlled, and often confounded; several headline claims exceed what the data support; and the “four-dimensional” quality score is only partially implemented in the main experiments. The paper is also too willing to turn limitations into findings.

### Recommendation: Reject

A substantially revised version could become a useful dataset/benchmark paper, but only after independent reference validation, cleaner experimental design, proper statistical treatment, and a much more restrained claim set.

---

## Major objections

### 1. The “gold” reference is single-author, self-validated, and not independently audited (§1, §2, Figure 1; §8)

The entire benchmark rests on the 177-row reference list, but the main body gives no serious evidence that this reference is actually “gold,” “fully sourced,” or “comprehensive.” §2 and Figure 1 assert that it is more comprehensive than GEM, Wikipedia, and OSM, but the comparison is not an independent validation. The author compiled the reference, selected the perimeter, seeded part of the content into Wikipedia, defined the matching procedure, and interprets disagreements with GEM as evidence that the reference is better.

This is a fatal circularity for a benchmark paper. A benchmark reference cannot simply be “hand-compiled by the benchmark author” and then treated as ground truth without external adjudication. The paper acknowledges in §8 that this is “one case study,” but the abstract, §1, and conclusion still sell it as a reusable benchmark and research programme.

**What would fix it:**  
At minimum:

- Provide an independent audit of a stratified sample of reference rows by domain experts not involved in compilation.
- Report inter-annotator agreement on inclusion/exclusion, plant grain, lifecycle status, capacity, and source adequacy.
- Include a formal error budget for the reference: likely omissions, disputed assets, ambiguous phase/unit splits, and stale statuses.
- Treat GEM/reference conflicts as unresolved cases unless independently adjudicated, not as presumed GEM misses.
- Release a “benchmark card” documenting reference construction, inclusion rules, known uncertainties, and revision policy.

Without this, row-level F1 against the reference is not a reliable accuracy metric.

---

### 2. The Wikipedia “coverage bar” is badly compromised by self-seeding and is overinterpreted (§5, Figure 3)

§5 argues that models should recover up to Wikipedia’s 130-asset coverage because the author’s group seeded reference-derived content into Wikipedia in 2019. This is presented as a “coverage bar” that models “ought” to pass. This is not a clean contamination analysis; it is self-induced contamination.

The paper says grading recall against Wikipedia is “not circular, because it measures retrieval, not justification.” That is unconvincing. The benchmark creators placed reference-derived content into a high-probability training source and then use failure to recall that content as evidence of model weakness. This confounds:

- training cutoff,
- whether the page revision was actually in a model’s training data,
- model memorization versus retrieval,
- page later edits/removals,
- prompt articulation,
- source language,
- and the fact that many pipeline rows postdate the 2019 injection.

The paper admits per-model cutoff dates are not recorded, yet still draws strong conclusions: “far less complete than Wikipedia pages already in their training data” (§10) and “the coverage bar’s validity is not in doubt” (§5). That is too strong.

**What would fix it:**

- Remove “ought to recover” language unless per-model training inclusion is documented.
- Separate built-fleet rows known to be on Wikipedia before likely cutoffs from post-2019/pipeline rows.
- Provide exact Wikipedia revision coverage at multiple dates and map each reference row to whether/when it appeared.
- Run a control task on a country where the authors did not edit Wikipedia.
- Treat Wikipedia as one noisy public source, not a “parametric ceiling.”

As written, Figure 3’s dotted Wikipedia line is not a valid upper bound.

---

### 3. The paper claims a four-dimensional benchmark, but the experiments mostly report row-level F1 and weak proxies (§3, §5, §6, Annex A)

The paper’s stated contribution is a computable benchmark over accuracy, coherence, provenance, and temporality (§1, §3). But in the main experiments, the meaningful quantitative results are overwhelmingly row-level F1. Provenance is mostly “citation presence,” not citation correctness. Temporality is mostly date-field presence/plausibility. Coherence is mostly controlled-vocabulary and degeneracy checks. §6 explicitly says rubric-scored §3 dimensions requiring a judging model are out of scope.

This creates a gap between the benchmark advertised and the benchmark actually used. A system could cite nonexistent or irrelevant URLs and receive provenance credit. A system could put an “as-of” date everywhere and score temporality. A table could be internally plausible but factually unsupported. The paper itself says in §3 that “the cited source must actually support the value claimed,” then later says the scorer does not verify this. That is not a minor implementation detail; it undercuts the claimed statistical-quality evaluation.

**What would fix it:**

- Rename the implemented measures honestly: e.g., “citation-field coverage,” “date-field coverage,” “controlled-vocabulary compliance,” not provenance/temporality/coherence in the strong sense.
- Add source-support verification on a sampled or full set of rows/cells.
- Report per-cell attribute accuracy beyond province/fuel/status, especially capacity, COD, owner/developer, and status-as-of.
- Define a composite score only after validating that the components measure the intended constructs.
- In §6, actually score all four dimensions or do not claim the frontier agents were evaluated on them.

The paper’s central “statistical register quality” framing is currently much stronger than its metrics.

---

### 4. The entity matching is tuned in-sample and may dominate the results (§3, §5, §8; Annex A/B)

The LP matcher uses a rapidfuzz partial-ratio threshold and capacity penalty chosen against this Vietnam reference. The paper admits in §9 that the matcher’s similarity threshold and status vocabulary were fitted in-sample. That is a serious issue because the headline F1 scores depend directly on the matcher.

The main body also notes several grain mismatches: power center vs plant vs unit, combined rows such as “Kiên Giang 1 & 2,” phase-level mismatches with GEM, and Vietnamese diacritic/name variants. These are not edge cases; power-sector registers are full of exactly these ambiguities. If the matcher converts true-but-differently-grained reports into FP/FN pairs, the benchmark is partly evaluating formatting compliance, not factual asset recovery.

The paper waves this away with a post-hoc audit (“0 such false matches”), but that does not address false non-matches or systematic penalties for valid alternative grains.

**What would fix it:**

- Provide a manually adjudicated evaluation subset comparing LP matcher output to human matching.
- Report precision/recall of the matcher itself.
- Allow hierarchical matching: complex/site/plant/unit/phase, with partial credit for correct aggregation or disaggregation.
- Pre-register matching parameters or validate them on a separate country/reference.
- Report sensitivity of F1 to threshold, capacity weight, and Vietnamese normalization choices.

Until then, F1 is not a clean measure of model performance.

---

### 5. Experiment 1 is confounded by an impossible prompt: “primary-sourced” inventory from memory with web search forbidden (§5; Annex B)

The memory-only prompt asks models to produce a “complete, primary-sourced reference inventory,” with Source 1 and Source 2 columns, while the system instruction forbids web search and tells models not to fabricate URLs. This task is structurally contradictory: the model is asked to provide primary-source provenance without consulting sources. The paper then scores outputs partly on provenance fields and treats refusals as F1=0, while later praising refusal as correct in §8.

This design conflates:

- asset recall,
- willingness to hallucinate citations,
- instruction-following,
- refusal policy,
- parametric memory,
- and output formatting.

The archived GPT-5.5 refusals are not just an anecdote; they expose a flaw in the task design. A model that refuses to fabricate sources may be more aligned with the stated quality bar than a model that emits a plausible but unverifiable table.

**What would fix it:**

- Split Experiment 1 into two tasks:
  1. asset-name recall only, with no provenance requirement;
  2. provenance-grounded construction with documents/web.
- Score refusals separately from empty outputs.
- Do not require Source 1/Source 2 in a no-retrieval condition unless “unknown/not available from memory” is permitted and rewarded.
- Report hallucinated citation rates, not merely citation presence.

As designed, Experiment 1 penalizes epistemic caution and rewards inventory-shaped hallucination.

---

### 6. The reliability/coherence screen is in-sample, arbitrary, and overclaimed (§5, Figure 5; §7)

The paper claims that “reference-free coherence correlates with accuracy” and that weak runs can be screened out without a reference (§1, §5, §7, Figure 5). But the actual screen is tuned on the same 70 Experiment 1 runs and uses crude degeneracy signals such as distinct capacity count and status-column variability. §7 admits: “an in-sample threshold rule rejects 23 of the 26 weakest runs with no false rejection.”

That is not evidence of a validated reference-free quality metric. It is an exploratory classifier fit to one dataset, one prompt, and one scoring pipeline. The heatmap/gate sensitivity in Annex B does not solve this; it varies thresholds within the same data. The claim that the “inaccurate models are also the unreliable ones” may simply reflect that the worst outputs are obviously malformed.

**What would fix it:**

- Train/tune the screen on one dataset and test on another country or asset class.
- Predefine the screen before evaluation.
- Report ROC/PR curves, confidence intervals, and calibration.
- Compare against trivial baselines: row count, number of distinct plant names, number of nonempty source cells.
- Avoid saying the screen can “stand in” for accuracy until external validation exists.

Figure 5 currently supports only: “some bad outputs are visibly degenerate in this experiment.”

---

### 7. Experiment 2 does not cleanly isolate “agentic” capability (§6, Figure 6, Figure 7; Annex C)

The 2×2 design is described as single-shot vs multi-turn and documents vs no documents, but the implementation introduces multiple confounds:

- The single-shot prompt differs from the multi-turn design prompt and, according to Annex C, the file was revised after some runs.
- The multi-turn arm includes a Phase A self-designed prompt, a separate DeepSeek classifier harness, fixed reply strings, budget status messages, and a verify pass.
- The single-shot no-doc condition lacks some methodology present in the multi-turn prompt.
- The “documents” condition uses a “curated reference pack,” but the paper is not clear enough in the main body about whether this pack contains documents used to build the gold reference and how close it comes to giving away the answer.
- The harness classifier is a model, not a deterministic controller, and its errors are not quantified.
- Web search behavior is opaque and vendor-dependent.

Therefore, when multi-turn degrades performance, the paper cannot attribute degradation to “agentic systems” or “planning and execution.” It may be a bad harness, a budget artifact, a prompt mismatch, a parser artifact, or a classifier failure. The paper sometimes acknowledges “the protocol’s contribution,” but the abstract and conclusion phrase the result more broadly: “a harness giving them the opportunity to plan and execute … degraded the results.”

**What would fix it:**

- Use identical task instructions across arms except for the isolated manipulation.
- Freeze and archive the exact prompt per run in the main experimental record.
- Replace the LLM classifier with deterministic criteria or manually audit its decisions.
- Include a strong hand-written multi-step baseline rather than letting each model invent a protocol.
- Report token budgets consumed, search calls, number of retrieved documents, and stopping reasons per run.
- Treat results as “this harness failed,” not “agentic planning fails.”

The current design cannot support general claims about agentic systems.

---

### 8. The documents condition may leak the benchmark and is not sufficiently characterized (§6, Figure 6; §7)

The paper repeatedly states that curated documents improve coverage and “equalise” agents (§6, §10). But the document pack is described only vaguely in the main body as “curated reference documents” / “reference document set.” If the pack consists of the same PDP annexes, EVN reports, and MOIT decisions used to compile the reference, then the experiment is no longer an open-world discovery task; it is a document extraction task over a hand-selected corpus likely containing the answer.

That may be a useful condition, but it must be framed correctly. It tests extraction from a curated corpus, not whether agents can discover and build a register. The phrase “which documents it is handed” is correct; the stronger suggestion that this identifies the binding constraint as “document quality rather than model capability” is not established. It may identify that the human curator already did most of the difficult source discovery.

**What would fix it:**

- Describe the document pack in the main body: number of documents, source types, languages, dates, whether all reference rows are supported inside it, and whether row names appear verbatim.
- Report document-pack coverage of the gold reference independent of models.
- Distinguish source discovery from source extraction.
- Add conditions with:
  - raw web only,
  - broad harvested corpus,
  - curated corpus excluding the exact reference-building documents,
  - and oracle corpus.
- Measure whether citations point to the provided documents and whether cited passages support the claims.

Right now the documents result is unsurprising and underspecified.

---

### 9. Statistical treatment is inadequate for the claims (§5, §6, §7; Figures 4–7; Table 1)

The paper uses N=5 repetitions per model and N=1 dataset, with no serious uncertainty quantification. It reports ranges and medians in places, but the claims are often categorical: “only one improved,” “documents equalise,” “fusion nearly eliminates false positives,” “more expensive models discover more assets,” etc.

Specific problems:

- No confidence intervals or bootstrap intervals for F1, recall, precision, or differences between arms.
- No paired analysis where appropriate.
- No correction for multiple comparisons across many models/arms/metrics.
- Interday drift is observed but not modeled (§8).
- Provider-side routing/checkpoint changes are acknowledged but then pooled.
- MoE nondeterminism is discussed but not experimentally isolated.
- Table 1 mixes all 14 Experiment 1 models to compute detection likelihood, which makes “task difficulty” partly a model-cohort artifact.
- The fusion analyses in §7 are post-hoc and evaluated on the same reference used to motivate them.

**What would fix it:**

- Use bootstrap intervals over runs and plants.
- Report paired per-model changes between no-doc/doc and single/multi-turn.
- Use hierarchical models or at least mixed-effects summaries: plant status, model family, run, condition.
- Separate within-run, within-day, interday, and provider variation.
- Pre-register post-hoc fusion rules or validate them out-of-sample.
- Avoid deterministic language when sample sizes are this small.

The current statistics are descriptive, not inferential.

---

### 10. Some figure captions and narrative claims contradict the reported results (Figures 4, 6, 7; §5–§6)

There are several internal inconsistencies or at least careless framings:

- §5 says “no monotonic relationship between API cost and F1 holds,” but Figure 4’s caption says “More expensive models discover more assets and return more stable results.” Which is it? A log-cost scatter with 14 models and heavy family effects does not justify the caption.
- §6 says “Coverage: the best agent enumerates barely half the fleet” in the no-doc single-shot arm, but later the documents condition reaches F1 0.77 for OpenAI (Table 6). The text needs to be explicit about which arm each headline refers to.
- Figure 6 caption says “Opus worked better” in Experiment 1, but Experiment 1 and Experiment 2 use different routing, APIs, prompts, web settings, and perhaps different model variants. That comparison is not clean.
- Figure 7 cost discussion says multi-turn costs 2–4× more, but Table 6 shows Anthropic multi-turn no-doc mean cost lower than single-shot no-doc, and Mistral docs single-shot cheaper than no-doc. If these are due to billing quirks, explain them.
- The main body alternates between 14 and 16 models; Annex B lists 16, §5 reports 14. The exclusion of two models is not sufficiently visible in the main text.

**What would fix it:**

- Audit all captions and claims against the tables.
- State precisely which cohort and arm each number refers to.
- Avoid cross-experiment comparisons unless call path, prompt, model, and provider are held fixed.
- Put Table 6 or an equivalent in the main body; hiding the factorial results in an annex while discussing them in §6 is poor practice.

---

### 11. Related work is too shallow and selectively framed (§2, §4)

§2 covers a few power-plant databases, and §4 gives a broad AI feature timeline, but the related work is not adequate for a benchmark paper on AI-assisted register construction.

Missing or underdeveloped areas include:

- entity resolution and record linkage for infrastructure datasets;
- data integration/truth discovery beyond a couple of citations in §9;
- dataset construction and benchmark contamination literature;
- web-agent evaluation and browsing benchmarks beyond BrowseComp/GAIA;
- LLM-based information extraction from long documents and tables;
- citation faithfulness and provenance verification benchmarks;
- statistical register methodology from official statistics;
- energy asset databases beyond WRI/GEM/Wikipedia/OSM, including national/operator registries where relevant;
- multilingual information extraction and Vietnamese document processing.

Figure 2’s AI capability rollout is not a substitute for related work. It consumes space while contributing little to the empirical claims. The product-timeline framing is also fragile and will date immediately.

**What would fix it:**

- Replace much of §4/Figure 2 with a focused review of LLMs for structured data extraction, web research agents, data provenance, entity resolution, and statistical registers.
- Clarify what is genuinely novel: the dataset? the scoring? the agent evaluation? the fusion analysis?
- Stop claiming “to our knowledge, first…” without a broader and systematic search.

---

### 12. The paper overclaims “benchmark reusable beyond the Vietnamese case” while admitting no transfer validation (§1, §8, §9)

The introduction says the contribution is a benchmark “reusable beyond the Vietnamese case.” §8 later says N=1 at dataset level means the findings are “existence proofs” and that transfer is a replication study. These cannot both be true in the strong sense.

The scoring code may be reusable, but the benchmark is a single frozen task: Vietnam thermal plants, one reference, one perimeter, one status mapping, one matcher threshold, one prompt family, and one source ecosystem. The conclusion generalizes to “many countries whose statistical systems cannot yet supply machine-readable asset inventories,” which is not supported.

**What would fix it:**

- Present this as a case-study benchmark, not a general benchmark.
- Add at least one additional country or asset class, preferably with independent reference data.
- Demonstrate that the matcher, prompts, quality gates, and fusion rules transfer without retuning.
- Separate “software reusable” from “empirical conclusions generalizable.”

---

### 13. The status vocabulary mismatch contaminates attribute accuracy (§5; Annex B)

The prompt’s controlled status vocabulary omits “Proposed” and “Planned,” while the reference contains 68 Proposed and 21 Planned rows—half the dataset. §5 admits this mechanically depresses status accuracy. This is not a small artifact; lifecycle status is central to the register and to the long-tail difficulty argument.

If the model is not allowed to output the reference labels, then status accuracy is partly measuring prompt-label mismatch. Conversely, if the reference labels are not aligned with GEM-style labels, then the benchmark’s status taxonomy needs a mapping.

**What would fix it:**

- Use a status vocabulary identical to the reference or define a many-to-one mapping before evaluation.
- Re-run status accuracy with a corrected prompt.
- Report confusion matrices.
- Do not interpret status accuracy as model weakness until the label space is coherent.

---

### 14. The fusion results are promising but post-hoc and too favorably framed (§7; Annex E)

§7 says pooling runs more than doubles recall and that requiring two models to agree nearly eliminates false positives. This is post-hoc analysis on the same dataset, using the same matcher and reference. The “0 false positives” result in Experiment 1 is especially likely to be brittle: model errors are correlated through shared training data and shared prompts, a problem the paper itself discusses in §9.

Also, the union result is not as strong as the abstract/conclusion suggest. Annex E says union improves recall but precision falls and F1 remains below the best individual run. That nuance is largely lost in the main body.

**What would fix it:**

- Move fusion to a clearly exploratory subsection.
- Report precision/recall/F1 trade-offs in the main body, not just recall multipliers.
- Validate vote thresholds on another dataset.
- Analyze correlated errors empirically by model family and source.
- Avoid “nearly eliminates false positives” as a general claim.

---

### 15. The paper’s narrative repeatedly upgrades limitations into conclusions (§6–§10)

Several claims are rhetorically stronger than the evidence:

- “The task is hard for today’s AI systems” is supported for this task under these prompts and conditions, but not broadly.
- “Web access and extended reasoning improved only one of four agents” is not clean because §5 and §6 differ in API path, prompt, provider routing, and search availability.
- “The investment that pays is sourcing, not a stronger or costlier model” is plausible but not established; only four agents and one curated corpus were tested.
- “External coherence remains future work” means the claimed quality bar is not implemented, not merely incomplete.
- “Evergreen statistical-quality register requires deliberate knowledge engineering” is a reasonable hypothesis, but the experiments do not evaluate an evergreen update setting.

**What would fix it:**

- Rephrase conclusions as conditional and empirical: “In this Vietnam thermal-plant case, under our prompts and scoring…”
- Separate demonstrated findings from design recommendations.
- Move speculative architecture material in §9 into a shorter future-work section unless experimentally evaluated.

---

## Minor and presentation issues

1. **Figure 1 is underexplained.** The “plants sorted by visibility” concept is not operationalized in the main text. If visibility is derived from layers, say so; otherwise it is impressionistic.

2. **Figure 2 is not earned.** A commercial AI timeline is peripheral to a benchmark paper and consumes space better spent on methodology and validation.

3. **Figure 3 is visually dense and hard to interpret.** The left/right TP/FP bar design is clever but not self-explanatory. Include model-level precision/recall/F1 table in the main body.

4. **Figure 5 lacks uncertainty.** Five runs per model are too few for a clean scatter. Add intervals or show all run-level points behind model means.

5. **Table 1 detection likelihood should not average over all models equally.** Weak and strong models are mixed; this table conflates plant difficulty with model cohort composition. Report by strong-model subset and with-doc/no-doc separately.

6. **Terminology drifts.** “Agent,” “deep research,” “multi-turn,” “harness,” “RAG,” and “documents” are used loosely. Define experimental conditions more tightly in the main text.

7. **The bibliography has inconsistencies.** For example, Balasubramanian et al. is cited as 2020 in §9 but listed as 2026. The reference list formatting also degrades midway.

8. **“Computable benchmark” is underspecified.** The paper should define what inputs/outputs are frozen, what is executable, and what parts require manual review.

9. **Costs are not normalized.** Comparing API dollar costs across providers without accounting for search billing, output verbosity, and caching makes cost-efficiency conclusions weak.

10. **Claims about “frontier of mid-2026” are fragile.** Product names and capabilities shift. A benchmark paper should emphasize archived model IDs, exact dates, and reproducible artifacts, not frontier rhetoric.

---

## What would be needed for a publishable revision

A credible revision would need to do more than polish exposition. I would expect:

1. **Independent reference validation.** At least a stratified expert audit and conflict log, ideally a second country/reference.

2. **Clean task decomposition.** Separate asset recall, source discovery, document extraction
