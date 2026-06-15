# Peer review — mistral (mistralai/mistral-large-2512), persona: student

Here is a detailed peer review of the paper, structured to highlight what is genuinely novel or useful, followed by incisive questions and constructive critiques.

---

### **What is Genuinely Novel or Useful?**
1. **Benchmark for AI-Generated Statistical Registers**
   The paper introduces a computable benchmark for reconstructing a national thermal power-plant register using LLMs. This is a novel contribution because:
   - It operationalizes the abstract idea of "research-grade statistical data" into a concrete, scorable task (Section 3).
   - It measures AI systems on four dimensions (accuracy, coherence, provenance, temporality) that are critical for policy-relevant datasets but rarely evaluated together in LLM benchmarks.
   - The benchmark is reusable beyond Vietnam, as it defines a frozen task, a public gold reference, and a computable metric (Section 1).

2. **Empirical Demonstration of the Gap**
   The paper shows that even frontier AI systems (as of mid-2026) cannot reliably produce a complete, well-sourced inventory of Vietnam’s thermal power plants. This is useful because:
   - It quantifies the gap between AI capabilities and the needs of energy policy models (e.g., PyPSA-ASEAN), which require asset-level data that are complete, current, and traceable to primary sources (Section 1).
   - It provides a baseline for future work, showing that neither model memory (Section 5) nor web access (Section 6) suffices to clear the quality bar.

3. **Reference-Free Quality Screening**
   The paper demonstrates that internal coherence metrics (e.g., variability in capacity or status columns) correlate with accuracy, allowing weak runs to be screened out without a reference (Figure 5). This is useful because:
   - It offers a cheap way to triage outputs when ground truth is expensive or unavailable (Section 7).
   - It separates the evaluation of *sources* (models) from *information* (runs), aligning with intelligence-evaluation frameworks like NATO’s STANAG 2511 (Section 7).

4. **Fusion as a Coverage Lever**
   The paper shows that pooling runs across models (simple union) more than doubles recall relative to the single-run mean (Section 7). This is useful because:
   - It provides a no-cost way to improve coverage without new data collection.
   - It highlights the value of multi-model diversity, which is often overlooked in favor of single-model scaling.

5. **Documents > Models**
   The paper finds that handing agents a curated document set equalizes performance across models (Section 6). This is useful because:
   - It shifts the focus from "better models" to "better sourcing," which is actionable for practitioners.
   - It suggests that the binding constraint for this task is document quality, not model capability.

---

### **Sharp, Incisive Questions and Critiques**

#### **1. Benchmark Design and Generalizability**
- **Section 3 (Quality Dimensions):**
  - The four dimensions (accuracy, coherence, provenance, temporality) are well-motivated, but the scoring formulas (Annex A) are opaque and seem arbitrary. For example:
    - Why is the coherence veto triggered when `cap_distinct ≤ 4` or `status_distinct ≤ 1`? How was this threshold chosen?
    - Why is source diversity scored as `min(d/20, 1)`? What is the justification for the 20-source cap?
    - The provenance scoring counts citations but does not verify them. This seems like a major limitation, given that fabricated citations are a known failure mode of LLMs. Why not include a verification step, even if it’s only sampled?
  - The benchmark is tested on only one country (Vietnam) and one asset class (thermal power plants). How generalizable are the findings? For example:
    - Would the same patterns hold for a country with a more transparent regulatory environment (e.g., the EU) or a less transparent one (e.g., Myanmar)?
    - Would the results differ for other asset classes (e.g., renewable energy, transmission lines)?
    - The paper acknowledges that the matcher’s similarity threshold (90) and capacity-difference weight (0.001) were tuned for Vietnam. How sensitive are the results to these parameters? Would the same thresholds work for other countries?

- **Section 5 (Experiment 1):**
  - The "coverage bar" (Wikipedia’s coverage of the reference) is a clever way to measure training-data contamination, but it assumes that Wikipedia is a superset of the reference. This is not true for the forward-looking pipeline (proposed/planned plants), which is the reference’s unique contribution (Section 5). How does this affect the interpretation of the results?
  - The paper notes that the status vocabulary in the prompt does not include "Proposed," which mechanically depresses status accuracy (Section 5). Why not align the prompt’s vocabulary with the reference’s status definitions? This seems like an avoidable source of error.
  - The paper reports that GPT-5.5 declined the task on 3 of 5 reps in an archived baseline sweep, refusing to fabricate citations (Section 5). This is framed as a principled refusal, but it could also reflect prompt sensitivity. How robust are the results to prompt variations? For example, would a prompt that explicitly allows "Source = not found" change the refusal rate?

- **Section 6 (Experiment 2):**
  - The multi-turn protocol (Phase B) is described as a "simple harness," but it relies on a DeepSeek classifier to decide whether the agent has "produced a report" (Annex C). This introduces a dependency on a third-party model, which could bias the results. For example:
    - How sensitive are the results to the classifier’s performance? Would a different classifier (e.g., Mistral Small) change the outcomes?
    - The paper notes that the classifier was switched from Nemotron to DeepSeek to avoid same-vendor self-evaluation. Why not use a non-LLM classifier (e.g., a rule-based system) to eliminate this source of bias?
  - The paper reports that Claude’s multi-turn arm produced unparseable bibliographies in 0 of 5 runs (Section 6). This is treated as a bibliography-parsability issue, but it could also reflect a deeper problem with the agent’s output format. How was parseability defined? Was it a strict structural requirement (e.g., JSON) or a looser one (e.g., Markdown)?
  - The paper finds that the multi-turn protocol degraded performance for 3 of 4 agents (Section 6). This is surprising, given that multi-turn reasoning is often assumed to improve performance. What explains this? For example:
    - Did the agents get stuck in loops or waste tokens on meta-commentary?
    - Did the VERIFY prompt (which asks for a "focused pass") inadvertently truncate the output?

#### **2. Experimental Design and Validity**
- **Section 5 (Experiment 1):**
  - The paper reports interday drift in F1 scores for some models (e.g., Qwen3.6-27b: +0.289 over 24 hours) (Annex B). This is a major threat to validity, as it suggests that the results are sensitive to silent provider-side changes (e.g., routing, checkpoint updates). How was this addressed in the analysis? For example:
    - Were the runs from different days pooled unconditionally, or was there a canary gate?
    - How does this drift compare to the within-model variance? Is it a first-order effect or a second-order one?
  - The paper uses temperature = 0 and seed = 42 to isolate prompt-driven variance from sampling noise (Section 5). However, MoE models (e.g., Mistral Large, Qwen3.6-35b) exhibit residual non-determinism even at these settings (Annex B). How does this affect the interpretation of the results? For example:
    - Is the within-model variance in Figure 3 driven by prompt sensitivity or by MoE non-determinism?
    - Would the results change if the experiments were repeated with a different seed or temperature?

- **Section 6 (Experiment 2):**
  - The paper uses a dual-axis budget cap (50K tokens or $3) to control for cost (Section 6). However, the realized costs vary widely across agents (e.g., Anthropic: $2.02/run vs. Qwen: $0.06/run) (Table 6). This makes it hard to compare agents fairly. For example:
    - Is Anthropic’s higher cost justified by its better performance, or is it a sign of inefficiency?
    - Would the results change if the budget cap were adjusted to equalize cost across agents?
  - The paper reports that the multi-turn protocol increased cost variability (Figure 7). This is expected, but it raises questions about cost predictability. For example:
    - How much of the cost variability is driven by the agent’s self-designed prompt vs. the harness’s fixed prompts?
    - Would prompt caching or context reuse reduce this variability?

- **Section 7 (Extensions):**
  - The paper shows that fusion (union or vote gate) improves coverage or precision (Section 7). However, the fusion recipes are simple and ad hoc. For example:
    - The union recipe is a naive set union, which could include false positives. Why not use a more sophisticated fusion method (e.g., weighted voting, capture-recapture)?
    - The vote gate requires agreement from 2 of 4 models. Why not test other thresholds (e.g., 3 of 4) or weights (e.g., confidence-weighted)?
  - The paper suggests that the binding constraint is document quality, not model capability (Section 6). However, the document set used in Experiment 2 is curated by the authors. How generalizable is this finding? For example:
    - Would the same pattern hold for a less curated document set (e.g., web search results)?
    - Would the results change if the document set were expanded to include more sources (e.g., Vietnamese-language documents)?

#### **3. Related Work and Missing Context**
- **Section 2 (Related Work):**
  - The paper surveys open power-plant databases (e.g., WRI GPPD, GEM, OSM, Wikipedia) but does not discuss how these databases are compiled. For example:
    - How do these databases handle provenance, temporality, and coherence? Are there lessons from their methodologies that could inform the benchmark?
    - How do these databases handle multilingual sources (e.g., Vietnamese-language documents)? The paper notes that the reference includes Vietnamese-language sources, but the experiments do not test multilingual capabilities.
  - The paper cites truth-discovery literature (e.g., Zhao et al., 2012) but does not discuss how it applies to LLMs. For example:
    - Truth discovery assumes source errors are conditionally independent given the latent truth. This is violated for LLMs trained on the same corpus, which share correlated errors. How does this affect the fusion results (Section 7)?
    - The paper notes that source reliability and latent-truth estimation are jointly determined (Section 9). How does this interact with the reference-free screening (Section 7)?

- **Section 4 (AI Capability Landscape):**
  - The paper describes the AI capability frontier as an "industry-wide envelope" (Section 4), but it does not discuss how this envelope is shaped by commercial incentives. For example:
    - Why do labs prioritize certain features (e.g., web search, reasoning) over others (e.g., provenance, temporality)?
    - How do product decisions (e.g., ChatGPT vs. API) affect the availability of these features?
  - The paper cites RAG (Lewis et al., 2020) and Self-RAG (Asai et al., 2024) but does not discuss how these methods handle provenance and temporality. For example:
    - How do RAG systems ensure that citations are verifiable and verified?
    - How do RAG systems handle temporal supersession (e.g., a 2019 source vs. a 2024 source)?

#### **4. Naive-but-Pointed Questions**
- **Why is the task hard?**
  - The paper attributes the difficulty to the long-tail distribution of the reference (Table 1), but this seems circular. Why is the long tail hard for LLMs? For example:
    - Is it because the long-tail plants are under-documented (few sources) or because they are recent (post-training cutoff)?
    - Is it because the long-tail plants are in Vietnamese, or because they are proposed/planned (not yet built)?
  - The paper notes that the operational core is well-covered by Wikipedia, but the forward-looking pipeline is not (Section 5). Why is this? For example:
    - Is it because Wikipedia’s coverage is biased toward built infrastructure?
    - Is it because proposed/planned plants are inherently more volatile (e.g., status changes, cancellations)?

- **Why do agents fail?**
  - The paper reports that agents with web access still miss many plants (Section 6). Why is this? For example:
    - Is it because the agents cannot find the right sources (coverage gap)?
    - Is it because the agents cannot extract the right information from the sources (extraction gap)?
    - Is it because the agents cannot reconcile conflicting sources (coherence gap)?
  - The paper reports that the multi-turn protocol degraded performance for 3 of 4 agents (Section 6). Why is this? For example:
    - Is it because the agents wasted tokens on meta-commentary?
    - Is it because the VERIFY prompt truncated the output?
    - Is it because the agents got stuck in loops?

- **Why does fusion work?**
  - The paper shows that fusion improves coverage or precision (Section 7), but it does not explain why. For example:
    - Is it because different models have complementary strengths (e.g., one model finds proposed plants, another finds operational ones)?
    - Is it because fusion reduces variance (e.g., by averaging out random errors)?
    - Is it because fusion exploits source diversity (e.g., different models draw on different training data)?

---

### **Constructive Suggestions**
1. **Ablation Study for the Benchmark**
   - Test the sensitivity of the results to the benchmark’s design choices. For example:
     - Vary the matcher’s similarity threshold (e.g., 80 vs. 90 vs. 95) and capacity-difference weight (e.g., 0.0001 vs. 0.001 vs. 0.01).
     - Vary the coherence veto thresholds (e.g., `cap_distinct ≤ 3` vs. `≤ 4` vs. `≤ 5`).
     - Test alternative provenance scoring (e.g., verified vs. verifiable citations).

2. **Multilingual Experiment**
   - Test whether the results hold for Vietnamese-language sources. For example:
     - Provide the agents with Vietnamese-language documents and prompts.
     - Compare the results to the English-only baseline.

3. **Temporal Experiment**
   - Test whether the results hold for historical queries (T2 requirement). For example:
     - Ask the agents to reconstruct the fleet as of 2018 (pre-PDP8).
     - Compare the results to the snapshot currency baseline (T1).

4. **Fusion Experiment**
   - Test more sophisticated fusion methods. For example:
     - Weighted voting (e.g., by model confidence or cost).
     - Capture-recapture estimation (e.g., to estimate the unobserved share of plants).
     - Truth discovery (e.g., to handle correlated errors across models).

5. **Cost-Performance Trade-off**
   - Test whether the results hold under a fixed cost budget. For example:
     - Allocate a fixed dollar budget (e.g., $10) and let the agents spend it as they see fit (e.g., more runs, more tokens, more web searches).
     - Compare the results to the fixed-token baseline.

---

### **List of Questions for the Authors**
1. **Benchmark Design:**
   - How were the scoring formulas (Annex A) chosen? For example, why is source diversity scored as `min(d/20, 1)`?
   - How sensitive are the results to the matcher’s parameters (similarity threshold, capacity-difference weight)?
   - Why not include a verification step for provenance scoring?

2. **Generalizability:**
   - How would the results differ for other countries or asset classes?
   - How would the results differ for multilingual sources (e.g., Vietnamese-language documents)?

3. **Experimental Validity:**
   - How was interday drift addressed in the analysis? For example, were the runs from different days pooled unconditionally?
   - How does MoE non-determinism affect the interpretation of the results? For example, is the within-model variance in Figure 3 driven by prompt sensitivity or by MoE non-determinism?

4. **Agent Performance:**
   - Why did the multi-turn protocol degrade performance for 3 of 4 agents?
   - Why did Claude’s multi-turn arm produce unparseable bibliographies?

5. **Fusion:**
   - Why does fusion work? For example, is it because different models have complementary strengths?
   - How would more sophisticated fusion methods (e.g., weighted voting, capture-recapture) compare to the simple union and vote gate?

6. **Documents vs. Models:**
   - How generalizable is the finding that documents > models? For example, would the same pattern hold for a less curated document set?

7. **Future Work:**
   - How would you prioritize the five open questions in Section 9? For example, which is the most critical for closing the gap?
   - What is the next experiment you would run to advance this research program?

---

### **One Experiment to Run Next**
**Experiment: Multilingual RAG for Vietnamese Power Plants**
- **Goal:** Test whether providing Vietnamese-language documents improves coverage and provenance for the forward-looking pipeline (proposed/planned plants).
- **Design:**
  - Curate a document set that includes Vietnamese-language sources (e.g., PDP8 annexes, MOIT decisions, press releases).
  - Run the same 2×2 factorial as Experiment 2 (query mode × documents), but with the Vietnamese-language document set.
  - Compare the results to the English-only baseline (Experiment 2).
- **Metrics:**
  - Row-level F1 (coverage and precision).
  - Provenance (verifiable and verified citations).
  - Temporality (as-of dates and status-change flags).
- **Hypothesis:**
  - The Vietnamese-language document set will improve coverage for the forward-looking pipeline, as these plants are often documented only in Vietnamese.
  - The Vietnamese-language document set will improve provenance, as the agents will be able to cite primary sources directly.
- **Why This Experiment?**
  - It tests a key assumption of the paper: that the forward-looking pipeline is under-documented in English but well-documented in Vietnamese.
  - It provides actionable insights for practitioners: should they invest in multilingual sourcing?
  - It advances the research program by addressing one of the five open questions (transfer across regulatory contexts).
