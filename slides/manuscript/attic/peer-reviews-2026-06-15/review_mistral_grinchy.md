# Peer review — mistral (mistralai/mistral-large-2512), persona: grinchy

**Recommendation: Major Revision**

This paper introduces a benchmark for evaluating AI systems' ability to reconstruct a national thermal power plant register, using Vietnam as a case study. While the topic is timely and the benchmark design is thoughtful, the paper suffers from several critical flaws that undermine its central claims. Below is a prioritized list of concrete objections, each tied to specific sections, figures, or tables, along with what would be required to address them.

---

### **1. Overclaiming the Benchmark’s Generality (Introduction, §2, §8)**
**Sections:** Introduction, §2 ("Related Work"), §8 ("Discussion")
**Figures/Tables:** Figure 1, Table 2
**Issue:**
The paper claims the benchmark is "reusable beyond the Vietnamese case" and positions it as a generalizable tool for evaluating AI systems on statistical register construction. However, the entire study is based on **N=1 dataset** (Vietnam’s thermal power fleet), and the methods (prompt templates, matcher parameters, quality bar) were developed *in-sample* for this specific case. The paper does not demonstrate that the benchmark transfers to other countries, asset classes, or regulatory contexts. The assertion that this is a "computable benchmark" is unsupported by evidence of out-of-distribution validity.

**What would fix it:**
- Replicate the study on at least one additional country (e.g., Indonesia, Thailand, or the Philippines) with a comparable thermal power fleet, using the *same* prompt templates, matcher parameters, and quality bar. Report whether the methods generalize without tuning.
- If replication fails, explicitly scope the benchmark to Vietnam and remove claims of generality.
- Acknowledge that the matcher’s similarity threshold (90) and capacity-weight (0.001) were fitted in-sample and may not apply elsewhere.

---

### **2. Methodological Hole: Self-Seeded Wikipedia Coverage (Experiment 1, §5)**
**Sections:** §5 ("Experiment 1: parametric baseline"), Annex B
**Figures/Tables:** Figure 3, Table 1, Annex B (Wikipedia coverage bar)
**Issue:**
The paper uses Wikipedia’s coverage of Vietnam’s thermal power plants (130/177 plants) as a "coverage bar" to evaluate models’ parametric recall. However, the author’s own group **deliberately seeded the reference dataset into Wikipedia in 2019**, creating a circular dependency: the benchmark’s reference list was used to populate Wikipedia, and now Wikipedia is used to evaluate models’ recall of that same list. This is not a neutral "coverage bar" but a **self-seeded contamination artifact**. The paper does not account for this circularity in its interpretation of results.

**What would fix it:**
- Remove the Wikipedia coverage bar as a benchmark. Replace it with an independent, pre-existing source (e.g., Global Energy Monitor’s 2018 snapshot) that was not derived from the reference list.
- If Wikipedia must be used, acknowledge the circularity and treat the coverage bar as an **upper bound** (not a neutral benchmark) for parametric recall.
- Disclose the exact revisions where the reference dataset was injected into Wikipedia (Annex B mentions "revision 902510278" but does not link to the diff).

---

### **3. Statistical Weakness: MoE Non-Determinism and Interday Drift (Experiment 1, §5, Annex B)**
**Sections:** §5, Annex B ("Post-fix top-up cohort and interday variability")
**Figures/Tables:** Figure 5, Annex B (interday variability table)
**Issue:**
The paper reports high within-model variance in Experiment 1 (e.g., DeepSeek V4-Flash’s F1 ranges from 0.07 to 0.52 across 5 identical runs). This is attributed to "sampling noise," but the paper does not account for **mixture-of-experts (MoE) non-determinism**, which persists even at temperature=0 and seed=42. Annex B reveals that three models (DeepSeek V4-Pro, Qwen3.6-27b, Qwen3.6-35b-a3b) exhibited **interday F1 drift of up to 0.289** between the baseline and top-up cohorts, despite identical call parameters. This undermines the claim that the experiments measure "prompt-driven variance" rather than provider-side instability (e.g., routing changes, checkpoint updates).

**What would fix it:**
- Characterize MoE non-determinism explicitly. Report the variance in F1 for MoE vs. dense models under identical deterministic settings (T=0, seed=42).
- Treat interday drift as a first-class variance source. Either:
  - Run all experiments in a single session to eliminate drift, or
  - Report drift as a separate error term in all figures/tables (e.g., error bars for interday variance).
- Acknowledge that "deterministic" decoding does not guarantee reproducibility for MoE models.

---

### **4. Overclaiming the "Frontier" in Experiment 2 (§6, §8)**
**Sections:** §6 ("Experiment 2: frontier agents fall short"), §8 ("Discussion")
**Figures/Tables:** Figure 6, Table 6
**Issue:**
The paper claims to test "the commercial frontier of mid-2026" but only evaluates **four agents** (Anthropic, OpenAI, Mistral, Qwen) via direct APIs. It does not test:
- Browser-automated surfaces (e.g., ChatGPT.com, Claude.ai chat UI), which are the primary way analysts interact with these models.
- Local models or custom workflows (e.g., Llama 3.1 405B, DeepSeek V3), which may outperform cloud APIs on cost or provenance.
- Multi-agent systems (e.g., OpenHands, CrewAI), which are explicitly designed for multi-step tasks like inventory construction.
The paper also does not compare against **non-agentic baselines** (e.g., pure RAG with the same document set), making it impossible to isolate the contribution of "agentic" features (web search, reasoning, multi-turn).

**What would fix it:**
- Expand Experiment 2 to include:
  - Browser-automated surfaces (e.g., Playwright scripts for ChatGPT.com).
  - Local models (e.g., Llama 3.1 405B, DeepSeek V3) with the same document set.
  - A pure RAG baseline (no web search, no multi-turn) to isolate the agentic contribution.
- Clarify that the "frontier" claim is limited to direct-API cloud agents, not the broader ecosystem.

---

### **5. Missing Related Work on Multi-Source Truth Discovery (§7, §9)**
**Sections:** §7 ("Can runs be fused?"), §9 ("Future research")
**Figures/Tables:** Figure S4, Annex E
**Issue:**
The paper proposes fusing runs from multiple models to improve recall (§7) and frames this as a novel contribution. However, it does not cite or engage with the **multi-source truth discovery** literature (e.g., Zhao et al. 2012, Manrique-Vallier 2016), which addresses exactly this problem. The paper’s fusion methods (union, majority vote) are simplistic and do not account for **source correlation** (e.g., models trained on the same corpus may share errors). The claim that "fusing the lists from multiple runs more than doubles recall" is not novel and ignores established methods for latent-truth estimation.

**What would fix it:**
- Cite and compare against multi-source truth discovery methods (e.g., Bayesian approaches, capture-recapture models).
- Acknowledge that union/majority vote are baseline methods, not state-of-the-art.
- Address the source-correlation problem explicitly (e.g., "Models trained on the same corpus may share errors, biasing dark-figure estimates downward").

---

### **6. Shallow Treatment of Provenance (§3, §6, Annex C)**
**Sections:** §3 ("Provenance"), §6 ("Provenance: corroboration by a second source"), Annex C
**Figures/Tables:** Figure S2, Table 6
**Issue:**
The paper defines provenance as "verifiable" (citations present) rather than "verified" (citations checked), but it does not actually verify any citations. Experiment 2’s provenance analysis (Figure S2) shows that most agents fail to provide **two independent sources** for their claims, yet the paper does not:
- Audit a sample of citations to check if they actually support the claims.
- Address the **Wikipedia contamination** issue (Annex C notes that 5/20 multi-turn runs cited banned Wikipedia domains).
- Compare against **manual compilation methods** (e.g., Global Energy Monitor’s provenance standards).

**What would fix it:**
- Verify a random sample of citations (e.g., 10% of Source 1/Source 2 cells) to report the fraction that actually support the claims.
- Report the fraction of citations that are **inadmissible** (e.g., Wikipedia, mirrors, tertiary sources).
- Compare against a manual compilation baseline (e.g., "GEM’s provenance standards require X; our agents meet Y%").

---

### **7. Vague or Hand-Wavy Passages (§8, §9)**
**Sections:** §8 ("Discussion"), §9 ("Future research")
**Issue:**
Several key claims are asserted without evidence or are underspecified:
- **§8:** "Articulation — the gap between analyst intent and model query — shares a soft boundary with coverage." This is a critical confound, but the paper does not measure it. How much of the "missing" F1 is due to articulation failures vs. true coverage gaps?
- **§8:** "External coherence is harder to measure." The paper does not propose a method or cite prior work (e.g., ALCE, RAGAS, Self-RAG) that attempts to measure it.
- **§9:** "Fusing correlated evidence" is framed as an open problem, but the paper does not cite **any** methods for handling source correlation (e.g., hierarchical Bayesian models, Ising models for label aggregation).

**What would fix it:**
- Measure articulation failures by:
  - Manually auditing a sample of false negatives to check if they were "found but misarticulated."
  - Reporting the fraction of false negatives that are name-variant mismatches (e.g., "Cà Mau I" vs. "Ca Mau 1").
- Propose a concrete method for measuring external coherence (e.g., "We will use RAGAS’s faithfulness metric, adapted for temporal supersession").
- Cite prior work on source correlation (e.g., Balasubramanian et al. 2026 for LLM-as-a-judge correlation).

---

### **8. Figures/Tables That Do Not Earn Their Space**
**Figures/Tables:** Figure 2, Figure 4, Figure 7, Table 1
**Issue:**
- **Figure 2 ("AI timeline")** is a descriptive timeline with no direct link to the experiments. It does not test any hypothesis or inform the benchmark design.
- **Figure 4 ("Cost vs. Coverage")** plots cost on a log scale but does not normalize for model size or capability. The claim that "paying more does not reliably buy a better inventory" is confounded by model architecture (e.g., MoE vs. dense).
- **Figure 7 ("Costs, Experiment 2")** shows cost variability but does not explain it (e.g., why does OpenAI’s multi-turn cost vary so widely?).
- **Table 1 ("Detection likelihood")** is redundant with Figure S3 (per-plant recognition matrix) and does not add new insight.

**What would fix it:**
- Remove Figure 2 (or move to an appendix).
- Normalize Figure 4 by model size (e.g., cost per billion parameters) or capability (e.g., MMLU score).
- Explain the cost variability in Figure 7 (e.g., "OpenAI’s multi-turn cost varies due to X").
- Remove Table 1 or merge with Figure S3.

---

### **9. Gap Between Claimed and Shown (§1, §10)**
**Sections:** §1 ("Introduction"), §10 ("Conclusion")
**Issue:**
The paper claims:
- "We introduce a computable benchmark for this task" (§1).
- "The computable metric is a four-dimension quality score" (§1).
- "We conclude that an evergreen statistical-quality register requires deliberate knowledge engineering" (§10).

However:
- The benchmark is **not computable** for other countries without manual tuning (e.g., matcher parameters, status vocabulary).
- The four-dimension score is **not fully implemented** (provenance and temporality are only partially scored; external coherence is not measured).
- The "knowledge engineering" conclusion is **not demonstrated** (the paper does not build or evaluate a knowledge base).

**What would fix it:**
- Clarify that the benchmark is **Vietnam-specific** unless replicated elsewhere.
- Implement the full four-dimension score (e.g., verify citations, measure external coherence).
- Demonstrate the "knowledge engineering" approach by building a prototype knowledge base and evaluating it against the benchmark.

---

### **Top 3 Threats to the Paper’s Central Claim**
The paper’s central claim is that **AI systems cannot yet produce research-grade statistical registers**, and that **deliberate knowledge engineering** is required. The three biggest threats to this claim are:

1. **Circularity in the Wikipedia Coverage Bar (Experiment 1, §5)**
   - The reference dataset was used to seed Wikipedia, and now Wikipedia is used to evaluate models’ recall of that same dataset. This inflates the apparent difficulty of the task by understating the models’ true parametric knowledge.

2. **MoE Non-Determinism and Interday Drift (Experiment 1, Annex B)**
   - The high within-model variance and interday drift undermine the claim that the experiments measure "prompt-driven variance." The results may reflect provider-side instability rather than model capability.

3. **Lack of Generalizability (Introduction, §8)**
   - The benchmark is developed and evaluated on **N=1 dataset** (Vietnam). Without replication on other countries, the claim that AI systems "cannot yet produce research-grade statistical registers" is overgeneralized.

---

### **Final Notes**
- The paper’s **strengths** are its clear task definition, thoughtful quality dimensions, and detailed technical annexes. These could form the basis of a strong benchmark if the above issues are addressed.
- The **weaknesses** are overclaiming generality, circularity in the evaluation, and methodological gaps (MoE non-determinism, provenance verification, multi-source truth discovery).
- **Recommendation:** Major revision, with a focus on:
  1. Replicating the study on a second country to test generalizability.
  2. Addressing the Wikipedia circularity and MoE non-determinism.
  3. Engaging with the multi-source truth discovery literature.
  4. Implementing the full four-dimension quality score.
