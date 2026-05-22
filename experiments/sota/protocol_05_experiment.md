# Protocol — Doc 05: Experiment

The broader experimental framing: subject selection, design rationale, what's measured, what's out of scope, future work. The task-semantics FAQ lives at §3.6.

Companion documents:
- Doc 01 — The ask (review framing + verdict format)
- Doc 02 — Phase A meta-prompt verbatim
- Doc 03 — Example dialogue
- Doc 04 — Implementation
- Doc 06 — Validation round 1 (per-reservation changelog)

---

## 3.1. Trial instance (this run)

The trial-instance task for this run is **an inventory of thermal power plants > 30 MWe in Vietnam, all lifecycle statuses** (operational, under construction, planned, cancelled, retired). Schema columns: Vietnamese name, English name, province, fuel, technology, units × MW, total MWe, status, COD, owner/developer, Source 1, Source 2, notes. Output is a Markdown document containing a sector overview, per-plant narratives, the structured table, cross-tabulation summary tables, and an annotated bibliography.

The protocol itself is sector- and country-neutral; for a different domain (e.g. Indonesia solar, France hydrogen electrolysers), Parts B and the task-FAQ in §3.6 are substituted; everything else stays.

---

## 3.2. Subjects: the four agents

| Vendor | Model | Country | API surface |
|---|---|---|---|
| Anthropic | Claude Opus 4.6 | US | Anthropic API, `web_search_20250305`, adaptive thinking |
| OpenAI | GPT-5.5 | US | Responses API, `web_search`, reasoning |
| Mistral | Mistral Large 2512 | FR | Agents API, `web_search` connector |
| Alibaba | Qwen3-Max | CN | DashScope, `web_search` inside thinking mode |

**Selection rationale**:
- Geographic / corpus spread: US × 2 + FR + CN. Vendor independence; mixed training-data corpora; under-indexed local-language (Vietnamese, Chinese-investor) sources reachable by at least one of the four.
- Direct vendor APIs only (no OpenRouter routing) so web-search billing is transparent and per-vendor behaviour is isolated.
- One representative of each "deep-research" surface variant — adaptive thinking, reasoning effort, agent connectors, thinking with search.

**Excluded by design**: browser-automated surfaces (ChatGPT.com, Claude.ai chat UI), specialised research products (OpenAI deep-research, Google deep-research), open-weight local models. Those are §5 / tailored-solution territory (separate experiment), not §4.

### 3.2.1. Phase B-0 gate before the full Phase B batch

The N=3 replication described in Doc 04 §2.9 is administered in two waves. **Phase B-0** is the first wave: one Phase B session per agent (N=1 per agent), end-to-end. The experimenters review the four B-0 outputs together — checking that each adapter produced valid records, that parsed tables are non-empty, that costs sit within the per-session envelope. Only if all four B-0 outputs clear this human review does **Phase B-full** launch the remaining two Phase B sessions per agent. This is the project's *test one before blasting* rule applied at the experiment level: a single agent's pathological behaviour does not silently consume 12 sessions of budget. From the agent's perspective the rule is invisible — each Phase B session looks identical and is governed by the same protocol; the gating happens between sessions, not during one.

---

## 3.3. Reference dataset — epistemic status

The experimenters maintain a 163-entry reference inventory for the trial, compiled by single-author manual curation from primary sources (Vietnamese government planning documents, ministerial decisions, utility annual reports). Row-level precision / recall / F1 are computed against this reference.

The reference is **not** a published canonical truth. It is a methodological artifact — a curated approximation that allows experimental comparison. F1 against it measures **concordance with the reference**, not **correctness in the world**. Cases where an agent's inventory diverges materially in count or coverage are reported separately, not auto-graded as failure. The reference is version-locked for this experiment.

---

## 3.4. Wikipedia leakage disclosure

**The authors have published a derivative of the reference inventory to Wikipedia prior to this experiment.** Two consequences:

1. **Training-data leakage.** Any model trained on data crawled after the Wikipedia upload may have absorbed the reference values into parametric memory. The experiment cannot control this layer; we name it as a known limitation. Post-hoc analysis flags suspicious parametric-recall fingerprints — claims close to the reference without supporting search.

2. **Web-search leakage (operational rule).** Wikipedia and Wikipedia-derived sources are **not admissible** as Source 1 or Source 2 on any row. This includes `en.wikipedia.org`, `vi.wikipedia.org`, Wikidata, DBpedia, Wikipedia mirrors, and aggregator sites that re-syndicate Wikipedia content without independent verification. The agent must trace to the primary source Wikipedia cites and use that instead.

Compliance is auditable: Phase D synthesis counts Wikipedia/Wikidata citations in each output's bibliography. Zero is compliant. Non-zero is reported as a protocol-compliance violation alongside F1.

---

## 3.5. Design choice rationales (one per round-1 reviewer concern)

### Single-agent, no subagents
This experiment measures **single-agent** capability under a fixed budget. Subagent dispatch (Claude `Task` tool, OpenAI handoff, panel-of-experts patterns) would externalise cost to vendors and accounts the experimenters do not control, confound the per-agent Phase C comparison, and silently turn an agent's "output" into the integration of sub-LLMs' outputs. Multi-agent designs are tested in §5 / IDH ticket 0224, not here.

### N=3 replication
Limited statistical power, acknowledged. Trade-off is total batch cost vs effect-size detectability. N=3 keeps the batch under ~$48 hard ceiling (4 × $12) while providing enough variance estimation for the qualitative findings the paper claims. Future replications at higher N are welcome.

### Dual-axis budget (50K tokens + $3 guard)
Per round-1 review: dollar-only caps disadvantage models with expensive output tokens. The 50K-token cap binds reasoning capacity comparably; the $3 guard binds total bill. Whichever fires first triggers TERMINAL. See Doc 04 §2.3.

### Third-party classifier (Nemotron)
Per round-1 review: same-vendor classifier creates self-evaluation pairs. Nemotron is open-weight, NVIDIA, not affiliated with any of the four subject vendors. Calibration is gated (ticket 0226) before the live batch.

### Planning headroom in Phase A
Per round-1 review: the state machine biases toward early-but-shallow first reports. Phase A meta-prompt now explicitly tells the agent the three-encouragement budget is planning space. See Doc 04 §2.4.1.

### Wikipedia disclosure + citation ban + audit
Per author addition: the reference dataset's existence on Wikipedia is a contamination risk for both training-data and web-search leakage. Disclosed; cited Wikipedia is disqualified at Source 1/2; compliance is post-hoc audited.

### Reference-dataset epistemic-status framing
Per round-1 review: the reference shouldn't be presented as canonical truth. §3.3 names it as a methodological artifact.

### Cross-evaluation transparency commitment
Per round-1 review: the Phase C rubric (ticket 0171) and raw inter-rater scores will be published with the manuscript.

---

## 3.6. FAQ on the ask (task semantics)

The trial domain (here, Vietnam thermal) determines what counts as an "entity", a "primary source", a "lifecycle status". The questions below answer the ones round-1 reviewers asked.

**Q3.6.1. What counts as one "plant"? What about a "power center"?**

A *power center* typically co-locates several power plants — for example, several phases commissioned in succession, sometimes under different operators or BOT arrangements, at the same site. **Each plant gets one entry in the inventory and one row in the table.** The power center itself is referenced in the narratives and the Notes column but does not get its own row.

**Q3.6.2. Are CHP and industrial captive plants in scope?**

Yes. **All plants > 30 MWe are in scope** — grid-connected, micro-grid, or off-grid; electricity-only or cogenerating heat; utility-owned or industrial captive. Capacity is the only inclusion gate.

**Q3.6.3. Are cancelled and pre-FID projects in scope?**

Yes. The inventory covers the full historical and prospective record. A project announced and cancelled is a valid row with the appropriate status. Pre-FID projects that have appeared in formal planning cycles count; pure rumour does not.

**Q3.6.4. Source-quality hierarchy (method-general)?**

In descending order of preference for Source 1 / Source 2:

1. **Primary government documents** — formal planning cycle documents, ministerial decisions, signed power-purchase agreements.
2. **Regulator-aggregated official data** — published utility yearbooks, regulator reports.
3. **Operator filings and press releases** — generation-company annual reports, BOT-consortium statements.
4. **International institution reports** — IEA, World Bank, regional energy-cooperation secretariats.
5. **Reputable trade press** — named-author bylines from established sectoral outlets.
6. **Industry trackers** — credible if they cite primaries; otherwise treat as below tier 6.

Below tier 6 (general news aggregators, unsourced blogs, opinion pieces) → not admissible as Source 1 or 2. The protocol deliberately does not name specific tier-1 documents for the trial — identifying them is part of the task.

**Q3.6.5. How to resolve conflicting source values?**

Cite the higher-tier source as Source 1; cite the lower-tier or contradicting source as Source 2 with a Notes entry explaining the discrepancy. If two equal-tier sources disagree, cite the more recent as Source 1 and note the discrepancy.

**Q3.6.6. Are secondary aggregators acceptable for the strong-citation test?**

Yes, *if* they cite a primary source the agent can verify. Cite the aggregator AND the primary it references. An aggregator that does not name its primary source is below tier 6 — not admissible.

**Q3.6.7. Are non-English / local-language sources required?**

Not required, but valuable. Local-language government documents are tier 1; their English translations are tier 1 only if officially published. When citing local-language sources, include the original-language title plus an English translation in brackets.

---

## 3.7. Baseline reference for cross-comparison (Phase C only)

The naive single-shot baseline that Phase C compares the deep-research outputs against is **not** the §1 parametric sweep (the multi-rep ablation at temperature 0). It is a separate pre-existing artefact: `experiments/outputs/direct_complete/` from `sweep_direct_complete` over a wider lab survey (`modelset_frontier_10labs`), single rep per model. Phase C reads this directly; it is not re-run. This is a methodological choice — comparing against a *one-shot frontier* (the level any user gets typing the prompt once) rather than against the parametric ceiling (the best-of-five aggregate that requires repeated sampling). Either choice is defensible; the experimenters picked the one-shot frontier because it represents the realistic deployment baseline.

## 3.8. Evaluation methodology (post-hoc, after the batch)

Phase D — synthesis — runs after all 16 sessions complete. Three measurements are taken:

### 3.8.1. Row-level F1 against the reference
Each polished Phase B output is compared against the reference inventory (§3.3) using a mixed-integer linear-programming (MILP) matcher (`src/aedist/matching/lp.py`, ADR-2). Candidate pairs require `rapidfuzz partial_ratio` name similarity ≥ 90 (integer 0–100); the matcher minimises a cost combining (i) the similarity and (ii) a small capacity-difference term (`capacity_weight · |Δcapacity_MWe|`, default 0.001). Province and fuel are deliberately *not* part of the matching cost (ADR-3); they are scored separately as cell-level attribute accuracies on the matched pairs. The optimal one-to-one assignment is solved globally rather than picked greedily.

Metrics recorded per session: `n_plants`, `tp`, `fp`, `fn`, `f1`, `fuel_accuracy`, `status_accuracy`, `province_accuracy`, `cost_usd`, `wall_s`, `tokens_out`. Session outcomes other than `ok` (refusal, empty, parse error) are recorded with `f1 = 0` and flagged in `status`.

### 3.8.2. Cross-evaluation on the four §A1 quality dimensions
Each of the 12 Phase-B outputs (4 agents × 3 reps) is scored on the four dimensions by the other three subject agents using a pinned rubric (ticket 0171). Self-evaluation is excluded. The classifier is not used for scoring; Phase C uses the subject models as evaluators. The rubric and raw inter-rater scores will be published with the manuscript.

### 3.8.3. Protocol-compliance audit
For each output: Wikipedia / Wikidata / mirror citation count (§3.4); whether subagent dispatch was attempted (logged from provider traces); session-by-session `terminal_sent` rate; classifier-misclassification cases identified by manual review.

## 3.9. What this experiment does NOT do

- Score outputs during the multi-turn conversation. Scoring is post-hoc (Phase C cross-evaluation by the three peer agents on the four §A1 quality dimensions, using the pinned rubric in ticket 0171).
- Interrupt mid-response or rewrite outputs.
- Feed other agents' designs or outputs to a subject (the four are blind to each other during their runs).
- Control parametric-recall leakage from training data (acknowledged in §3.4).
- Compare deep-research vs custom workflows. That is §5 / Tailored Solution territory.

---

## 3.10. Future work and known limitations

- **Multi-step verification (IDH cycle)** — bibliographic scoping + plan generation + self-verify + panel of expert verifiers + per-row/per-source swarm verifier. Ticket 0224.
- **Confidence vocabulary** — equipping verifiers (and subjects) with IPCC-style confidence bands, alleviating the ambiguity-vs-recall trade-off. Ticket 0225.
- **Cross-trial generalization** — the protocol is sector- and country-neutral. Replication on other domains (Indonesia solar, France hydrogen, etc.) is future work.
- **Higher N replication** — to detect smaller effect sizes than the qualitative findings claimed at N=3.
- **Subagent / panel architectures** — fair comparison of multi-agent systems vs single-agent vs human-curated workflows. Requires a different protocol; out of scope here.
- **Blind human adjudicator panel** — round-1 reviewer suggestion. Desirable; out of scope for this run.
- **Energy / CO₂ instrumentation** — dollar cap is a proxy for what the experimenters actually care about (the inference footprint). Vendors do not expose energy or CO₂ at call time. The paper calls for standardised disclosure.
