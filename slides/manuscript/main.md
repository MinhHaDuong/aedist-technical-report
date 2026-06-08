---
header-includes:
  - \usepackage{pdflscape}
  - \usepackage{newunicodechar}
  - \newunicodechar{✕}{\ensuremath{\times}}
  - \newunicodechar{≤}{\ensuremath{\leq}}
  - \newunicodechar{≥}{\ensuremath{\geq}}
  - \newunicodechar{≈}{\ensuremath{\approx}}
  - \newunicodechar{ρ}{\ensuremath{\rho}}
---

# Synopsis — Beyond RAG: Stateful-Agentic Architectures for Reliable Economic Statistics

Minh Ha-Duong, 2025-05-06

Economic and engineering analysis using open energy-system models such as PyPSA-ASEAN need power-plant inventories of industrial assets that are complete, accurately dated, and traceable to primary sources — enabling quasi-real-time support for policy analysis in countries where the data landscape changes faster than publication cycles. Yet across most of the world the relevant facts arrive late, incomplete, or under licences that forbid redistribution, even though the underlying information is already public — scattered across project documents, master plans, environmental assessments, operator reports, and press releases. The general problem behind the specific one is older than AI: science needs knowledge, not opinions. Statistical work requires facts that are sourced, reproducible, and auditable, not plausible-sounding outputs from a random words generator somewhere in the cloud.

This paper builds the argument in six steps.

## First, the baseline

Submitting a direct query to a large language model produces an inventory-shaped answer, but not one that meets statistical or scientific quality standards. Numbers shift between runs, citations are absent or fabricated, and there is no way to tell which cells one should trust.

**Experiment 1 — Parametric baseline.** We query sixteen language models from the *modelset_ablation_journal* set — spanning three language families (EN/FR/ZH) and five laboratories from mid-range through frontier-class systems — with a fixed structured table specification prompt (the locked `2_goal + 5_table` composition, reproduced in Annex B). No documents are provided; models draw exclusively on parametric knowledge and receive a system instruction forbidding web search. Each model is queried five times at temperature zero, yielding 80 runs against a 173-plant reference inventory of Vietnamese thermal power plants (coal and gas, all lifecycle statuses). Runs are evaluated by matching extracted plant names against the reference using fuzzy string matching, yielding row-level precision, recall, and F1; fuel type, operational status, and province accuracy are scored at the cell level for matched rows. Cost in USD and wall-clock time are recorded per run.

The table below decomposes the difficulty by status (library `aedist.exp1_recognition`; same data derivation as the per-plant recognition matrix in Annex E, Figure 7). The reference list is dominated by proposed plants — the largest share — which parametric memory cannot know; their mean recognition rate is far below that of operational plants. The low overall recognition is therefore structural, a property of the list's composition, not merely a model failure.

| Status | n | Share of list | Recognition rate |
|---|---:|---:|---:|
| Proposed | 67 | 38.7% | 8.0% |
| Planned | 21 | 12.1% | 29.6% |
| Under construction | 10 | 5.8% | 40.3% |
| Operational | 56 | 32.4% | 45.7% |
| Retired | 2 | 1.2% | 63.6% |
| Cancelled | 17 | 9.8% | 17.0% |
| **All** | **173** | **100.0%** | **26.2%** |

*Table: composition of the reference list by status, and mean recognition rate (Experiment 1, direct method: 14 models × 5 repetitions). The rate is the share of run × plant cells recognized among plants of that status.*

**Results.** Across 80 runs (16 models × 5 repeats), 77 produced usable tables and 3 were refusals (all GPT-5.5). Row-level F1 across the 77 usable runs ranges from 0.01 to 0.76, with a mean of 0.38. Within-model F1 variance is large: DeepSeek V4-Flash ranges from 0.01 to 0.65 across 5 identical runs, and GPT-OSS-20B from 0.23 to 0.76 — spreads wider than the gap between many adjacent model means. Even for correctly matched plants, attribute classification remains mediocre: mean fuel accuracy 0.53, mean status accuracy 0.53, mean province accuracy 0.61. No monotonic relationship between API cost and F1 is observed: Claude Opus 4.6 at \$1.23 total achieves mean F1 = 0.46, while GPT-OSS-20B at \$0.01 reaches 0.58. To our knowledge, this non-monotone cost-versus-F1 relationship for structured factual extraction has not been documented in prior literature. The total experiment cost is \$2.85. Five qualitative failure modes organise the model-by-run distribution: GPT-5.5 refuses the task on 3 of 5 runs (*Récalcitrant*), citing inability to produce sourced data from parametric knowledge; Claude Haiku consistently finds only 17 plants (*Incomplet*); Qwen 3.6-27B fabricates up to 268 false positives in a single run (*Hallucinant*); DeepSeek V4-Flash and GPT-OSS-20B exhibit the widest within-model variance (*Non-déterministe*); and no cost ordering predicts quality (*Non-monotone*).

![](../report/inputs/generated/fig_direct_p1_base.pdf)\

*Figure 1. Direct-query performance across 16 models and 80 runs on the 173-plant Vietnam thermal reference. Each bar is one run; family-coloured segments to the right are correctly identified plants (TP), red segments to the left are unrecognized plants (FP). The dashed green line marks the 173-plant reference. Models are grouped on the vertical axis. Five qualitative failure modes are visible: Récalcitrant (refusal), Incomplet (systematic under-coverage), Hallucinant (fabricated plants), Non-déterministe (high within-model variance), Non-monotone (no cost–quality ordering).*

![](../report/inputs/generated/fig_direct_cost_quality.pdf)\
<!-- raw data: report/inputs/generated/cost_quality.csv -->

*Figure 2. Plants correctly identified vs cost per call across the Experiment 1 lineup, split by architectural family across two panels with shared axes: **panel (a)** Claude, GPT, Mistral; **panel (b)** Qwen, DeepSeek. Each of the sixteen models from `modelset_ablation_journal` contributes: a **filled square** at the pooled median TP count, **unfilled circles** at every rep from the 2026-05-20 journal sweep, and **✕ markers** at every rep from the 2026-05-21 reasoning-token top-up (ticket 0198, pooled unconditionally — no canary gate, intra-day variability absorbed into the reported within-model spread). Each rep is plotted at its **own** per-call cost (cents USD, decimal, log scale) — within-model horizontal spread reflects the rep-to-rep variation in output-token counts. A thin polyline connects the reps for each model in cost order. The dashed reference line at 173 marks the full Vietnam thermal inventory and is repeated on both panels. The Y axis starts at -5 so that refusal markers at TP=0 sit visibly above the axis line. Marker colour encodes the architectural family: Claude (blue), GPT (vermillion), Mistral (bluish-green), Qwen (reddish-purple), DeepSeek (orange), all from the colorblind-safe palette in `palette.toml`. Per-model numbers backing this figure are written to `report/inputs/generated/cost_quality.csv` for audit.*

![](../report/inputs/generated/fig_quality_floor_heatmap_exp1.pdf)\

*Figure 2b. Quality-floor heatmap for Experiment 1 (parametric arm, 12 models × 5 runs). Rows are models in four architectural families (Claude, GPT, Mistral, Qwen); DeepSeek is excluded (no panel in the quality taxonomy). Columns are the ten sub-score criteria across four dimensions (Accuracy, Coherence, Provenance, Temporality). A cell is **red** iff a majority (≥ 3 of 5) of that model's runs scored zero on that criterion — indicating a systematic failure. Any red cell in a row disqualifies the model: it cannot clear the §2 quality bar, which is a conjunction — a zero on any criterion means the bar is not cleared. Model labels and family-separation lines help the reader isolate which families clear all criteria and which do not.*

## Second, the quality bar that any acceptable dataset must clear

Datasets can be assessed on four dimensions: accuracy, coherence, provenance, and temporality. The decomposition compresses three traditions: data-quality engineering [@Wang-Richard1996:beyond-accuracy], official-statistics governance [@IMF2003:dqaf; @UN2014:fundamental-principles], and philosophy-of-science empirical adequacy [@vanFraassen1980:scientific-image].

1. *Accuracy* asks whether the dataset contains the right assets and the right attributes. At the row level, this means recall and precision: does the system find all relevant assets, and does it exclude non-assets or duplicates? For a simple inventory table, this can be measured against a manually curated reference table using precision, recall, and F1 score [@Hendrycks-Dan2021:mmlu; @Wu-Xianjie2025:tablebench; @Tenckhoff-Sonke2026:llmstructbench]. At the cell level, accuracy asks whether the attributes attached to each asset are correct: capacity, fuel type, location, operator, commissioning year, status, and so on. A system can therefore be accurate in entity discovery but weak in attribute extraction, or conversely reliable on attributes once the correct asset has been identified. Plausibility is not truth — confidently-stated fabrications are the failure mode this dimension polices [@Lin-Stephanie2022:truthfulqa].

2. *Coherence* asks whether the dataset is internally and externally consistent. Internally, statistical tables have control constraints: aggregate totals should match regional or technology subtotals when those totals are known; capacities should not be negative; duplicate units should not be counted twice; and cross-row values should not contradict one another. Externally, the dataset should remain compatible with other available knowledge: units, orders of magnitude, geographic location, technology type, and commissioning dates should all be plausible. A coherent dataset identifies conflicts between sources rather than silently overwriting them. A minimal coherence requirement is non-contradiction; a weak operational instantiation is sampling-level self-consistency [@Wang2022:self-consistency]. A stronger requirement is inferential closure: the system should derive and expose all consequences that follow from the available documents and accounting rules, rather than merely storing isolated claims. Coherence thus has two axes — *scope* (internal to the dataset vs. external against world knowledge) and *strength* (weak: no contradiction, vs. strong: inferential closure). This paper measures weak-internal coherence; the external axis is discussed in the Discussion section.

3. *Provenance* requires a pedigree for each data item. Every row, and ideally every cell, should trace back to specific passages, tables, images, or records in specific sources. Strong provenance means more than attaching a plausible citation: the cited source must actually support the value claimed [@Gao-Tianyu2023:alce; @Asai-Akari2024:self-rag; @Es-Shahul2023:ragas]. We distinguish *verifiable* provenance — a citation is present and could in principle be checked — from *verified* provenance — the citation was retrieved and confirmed to support the stated value. Verified provenance is the stronger standard; verifiable is the minimum floor. When sources contradict one another, the resolution — which source was preferred and why — should itself be documented as part of the provenance record. Ideally, each important item should be backed by two independent primary sources. Weaker forms of justification — for example, one primary source, a regulator database, or a clearly marked secondary compilation — are still preferable to unsupported values, provided their evidential status is explicit. Satellite imagery and visual inspection can also provide evidence for industrial assets, but they are costly, hard to scale, and mainly confirm the presence of existing installations rather than full project histories.

4. *Temporality* is not metadata added after the fact; it is part of the statistical fact itself. Energy infrastructure changes over time: projects are announced, financed, permitted, built, commissioned, repowered, mothballed, retired, cancelled, or renamed. Every value should therefore carry a best-effort “as-of” date or validity period, and notable status changes should be flagged. A statistical dataset should distinguish clearly current status from past reports, planned capacity from operating capacity, and source publication date from the date of the underlying fact. The currency / timeliness dimension is treated by Wang & Strong [-@Wang-Richard1996:beyond-accuracy] and by the IMF DQAF [-@IMF2003:dqaf] but largely absent from LLM-evaluation practice, which the present work positions as a gap. This paper scopes to snapshot currency: the table describes the fleet at a reference date, each value carries a best-effort as-of date, and notable status changes are flagged. The fuller requirement — supporting queries of the form "what was the installed fleet in 2018?" — applies to scenario-projection use cases; it is addressed structurally in §5 and discussed in Annex D.

The task is not simply to generate a plausible inventory-shaped answer. The statistical object is a dated, sourced, internally reconciled set of claims about energy-system assets and events. Accuracy determines whether the claims are correct; coherence determines whether they can coexist; provenance determines whether they are auditable; and temporality determines what period of the world they describe.

## Third, from chatbots to knowledge management

To compare general-purpose AI systems meaningfully, we separate four axes. *Post-training objective* — base, instruct, chat, reasoning — describes what the lab trained the model for on top of pretraining; "code" sits as a domain-specialisation tag orthogonal to this axis (a code-trained model can also be chat-tuned). *I/O modality* — text, vision, audio, video — describes which input and output channels the model handles; "multimodal" is the derived label for any combination, not a fifth level. *Tool affordance* — no tools, function calling, browser, code interpreter, computer-use — describes what external surfaces the runtime exposes to the model. *Product workflow* — simple chat, single-task agent, deep research, coding agent, autonomous task runner — describes the horizon and orchestration the product places around the model. The first two axes are model properties; the last two are framework properties. A model can be instruct-tuned but text-only and tool-less; it can be a multimodal reasoning model with tool use and long-horizon scaffolding. The cross-product is large, and any single comparison axis is a projection.

The figure below uses one such projection: a timeline of when each of eight named capability surfaces first shipped as a consumer-facing product. The launch-in-public-commercial-product date is the threshold at which a working analyst can rely on the capability; availability via API or privileged-partner testing is months earlier but not equivalent for end-user workflows. Tool affordance and product workflow define the eight features; the modality and training-objective axes — model properties — are not projected here. The projection is a pragmatic historical lens, not a complete description of the multi-axis space above.

Agent capabilities improve statistical-dataset quality, and the industry trajectory of the past three years operationalises that claim. The improvement is not a single staircase any one lab climbs. It is an envelope — the outer surface of commercially attainable capability — that the industry has pushed outward through a sequence of integrations rather than a sequence of inventions.

None of these integrations are model properties. Retrieval, web access, reasoning surfaces, code execution, tool use, and recursion all live in the runtime that wraps the model; the model just sees a longer prompt, a CoT trace it is generating, a structured tool call it is emitting, or a sub-agent invocation it cannot directly observe. What the model contributes is *conditioning*: a lab's investment in training on RAG-style contexts, tool-call traces, long-reasoning RL recipes, and subagent traces is what lets the model leverage each surface well when the framework exposes it. Feature 1 itself is the first such co-deployment: the raw pretrained base model is exposed only via a continuation API and is not a consumer product; what shipped to the public in 2022–2023 was a chat-tuned variant (RLHF for dialogue) wrapped in a chat UI — ChatGPT, Claude, Tongyi Qianwen, and the rest — with standalone "Instruct" checkpoints (Mistral 7B Instruct, Llama 2-Instruct, …) following as open-weights artifacts but not as standalone consumer products. A capability ships only when the framework × trained-model × product packaging line up — each marker in Figure 4 is the date that triple first appears in a publicly available commercial product, which can be months after internal availability and privileged-partner testing; availability via API is a parallel signal we did not adopt here.

Below these integrations sits *articulation* — the prompt-engineering practice that closes the gap between analyst intent and model query, the LLM-specific instantiation of the Type-III error of solving the wrong problem (Mitroff and Featheringham 1974); we did not find an explicit treatment of it in the LLM literature. The §1 baseline already exercises articulation through a structured four-section prompt.

The integrations are by now familiar. *Retrieval-augmented generation* [@Lewis-Patrick2020:rag; @Gao-Yunfan2024:rag-survey] answers the coverage limit: parametric memory is finite; document retrieval at inference time isn't. *Reasoning* — chain-of-thought elicited by prompting [@Wei-Jason2022:cot], later embedded as test-time compute in production models (OpenAI o1, Anthropic extended thinking, Magistral, R1, QwQ) — narrows the coherence and reasoning limits on long, multi-source synthesis. The *join* of retrieval and reasoning is the deep-research surface [@Wei-Jason2025:browsecomp], which lets the model decide what to read and how to read it. *Code execution* — a sandboxed Python / JS / shell interpreter exposed as a built-in tool — lets the model verify arithmetic, recompute statistics, and produce executable artefacts (plots, tables, scripts) inside the conversation. *External tool use* — exposing an MCP-like tool-use protocol (Anthropic's Model Context Protocol, OpenAI function calling, and equivalents) so the model can invoke arbitrary tools at inference time [@Yao-Shunyu2023:react] — generalises the code-execution sandbox to an extensible tool registry; benchmarks measure progress on coding [@Jimenez-Carlos2024:swe-bench], operating-system control [@Xie-Tianbao2024:osworld], and general-assistant tasks [@Mialon-Gregoire2024:gaia]. *Agency* is the closure of that surface: when the tool-use set includes the model itself, the model can recurse or dispatch peer agents rather than only call scripts or interface with programs. Each integration lifts one or more of the §2 quality limits at the margin; none of them lifts all four; their combinations exhibit ordering structure but not a strict performance hierarchy.

![](../report/inputs/generated/fig_capability_timeline.pdf)\

*Figure 4. Empirical capability rollout across the five labs in Experiment 1. Each row is a capability feature (1 chat LLM → 8 multi-agent recursion); each marker places when the named lab first shipped that feature in a consumer-facing product. Markers are coloured by architectural model family (claude / gpt / mistral / qwen / deepseek) from the project palette, and shaped by lab. The horizontal spread within each row is the cross-lab emergence window; vertical neighbours that overlap in time (notably features 3 and 4) indicate parallel-not-sequential capability development. Source: `data/capability_timeline.csv`; per-lab primary announcements documented in `docs/capability-timeline.md`.*

<!-- editorial scaffolding (do not render): The figure is descriptive — no claim is made that any lab is "ahead" or that the order is forced. -->

Features 1 through 4 ship within ~24 months across the industry, with the first three (chat LLM, browsing, code execution) arriving at OpenAI between late 2022 and mid-2023 before retrieval followed in October 2023. Features 3 and 4 emerge in parallel across labs: the per-lab order varies (Anthropic shipped retrieval before code execution; OpenAI the reverse; Mistral the same day), and the *cross-lab* shipping windows overlap substantially. Feature 3 (code execution) was the earliest tool-use surface shipped as a built-in consumer feature, predating the general MCP-like surface of feature 6 by ~18 months at OpenAI. Feature 7 (deep research) draws on both features 2 and 5 — at every lab where it shipped as a product, deep research arrived within 1–5 months of having both browsing and reasoning in place. DeepSeek is the negative case that confirms the framework-not-model framing: it ships features 2 and 5 (Internet Search in V2.5; R1 reasoning) and the model components that would enter a deep-research loop (V3.1's search-agent claims, V3.2's thinking-in-tools), but has not packaged the composer as a public product within the cutoff.

<!-- editorial scaffolding (do not render): This is structural evidence that the order is observed in the data, not imposed by the framing. -->

![](../report/inputs/generated/fig_capability_dag.pdf)\

*Figure 5. Empirical capability transition matrix across N=5 labs. Each cell shows the fraction of labs where feature i (row) shipped before feature j (column), conditional on both being present; N per cell. Ties split as 0.5 so symmetric pairs sum to 100%. White = no lab made that transition; dark green = all labs did. Features 3 and 4 (code execution × retrieval) emerge in parallel. Feature 5 (reasoning) consistently follows features 1–3. Feature 7 (deep research) draws on features 2 and 5. Descriptive historical record, N=5 labs — no statistical inference.*

\newpage

The figure goes quiet after mid-2025 because leading labs had filled all eight features, not because development stalled: context length, shell-level execution, persistent agent scaffolds, and the modality axis — text to vision to real-time audio — all continued to advance outside the tool-affordance ladder this schema tracks. Two further dimensions are absent by construction. The constraint axis — refusal training, content policy, and red-teaming — shaped which requests these consumer products would serve, running alongside the capability expansion the figure shows but perpendicular to it. And the consumer-product methodology excludes the military and dual-use deployment track: a parallel trajectory operating at comparable capability levels, now routine front-page news, that the commercial-product framing does not capture and does not claim to.

The empirical envelope nonetheless leaves the §2 quality bar uncleared, which is what §4 (Experiment 2) tests directly.

## Fourth, the commercially available frontier: State-of-the-art general-purpose AI systems still fall short

How well do the state of the art tools perform when it comes to producing research-quality statistical datasets? The parametric ceiling of §1 is a deliberately handicapped baseline — no web, no tools, no reasoning budget beyond what each model carries internally. The commercially available frontier, by contrast, ships agents that combine extended reasoning, web search, document ingestion, and tool use into a single "deep research" surface. The question is whether removing the §1 handicaps suffices to clear the §2 quality bar.

**Experiment 2 — SOTA frontier (Annex C).** We conduct an experiment with four state-of-the-art cloud AI agents that have extended reasoning and web access, queried over direct vendor APIs (no browser automation): Anthropic Claude Opus 4.6 (US, web_search + adaptive thinking), OpenAI GPT-5.5 (US, Responses API + web_search + reasoning), Mistral Large 2512 (FR, Agents API + web_search connector), and Qwen3-Max via DashScope (CN, web_search inside thinking mode). The fourth slot is hypothesis-relevant rather than decorative: Chinese-language investor and trade documents on Vietnamese power assets are under-indexed by Western search. The experiment runs two arms over the same four agents (N=5 each). **Arm 1 (naive)** — a single-shot prompt (Doc-07) with no scaffolding, web on; the null comparator. **Arm 2 (optimised)** — a multi-turn protocol in which each agent first designs its own prompt and settings (Phase A), runs once as a smoke gate (Phase B-0), then runs N=5 against a single provider under a per-session cap of 50K tokens / $3 (Phase B). The naive-vs-optimised contrast isolates the protocol's contribution over raw model capability. Row-level F1 against the 173-plant reference is now scored for all four arms (see the 2×2 factorial table); cross-model judging on the four §2 dimensions remains reserved for post-conference analysis (Phase C, ticket 0171).

![](../report/inputs/generated/fig_exp2_arms_comparison.pdf)\

*Figure 3. Experiment 2 — naive (arm 1, single-shot) vs optimised (arm 2, multi-turn) comparison, N=5 per agent. Panel (a): Plants found — TP bars (blue, upward, matched against the 173-plant reference) and FP bars (red, downward, unrecognized plants), median over runs with scored outputs; left bar = arm 1, right bar = arm 2 per agent group. Grey bars indicate runs with no matched-row scores available. Panel (b): API cost per run (USD), individual runs as scatter points. Dashed green line marks the 173-plant reference count. Row-level F1 against the 173-plant reference is now scored for all 80 runs; the 2×2 factorial analysis of F1 and cost (query mode × documents) appears in the slides and Annex C. With N=4 agents as the blocking factor, effects are reported as directional consistency (k/n agents agreeing in sign) rather than significance tests, since the minimum attainable p at n=4 is 1/2⁴ = 0.0625.*

<!-- TODO(ticket-0307): Re-enable the turn-trajectory figure once probe-per-turn mart data is available. -->

**Observed results (operational metrics).** *Note: the earlier arm-2 extraction failures — Mistral's Agents-API format and Anthropic's non-canonical column headers — have since been resolved, so all four agents now yield scorable arm-2 tables (N=5 each) and the F1-based 2×2 analysis above supersedes this paragraph's coverage figures, which predate that recovery.* For agents with complete arm 2 data: OpenAI arm 2 median is 86 rows versus arm 1 median 83 rows (modest improvement; individual runs 79–96 vs 76–90); Qwen arm 2 median is 25 rows versus arm 1 median 42 rows (regression; Qwen's Phase A self-designed protocol imposed a strict dual-source admissibility filter that constrains coverage from Turn 1). Naive arm (arm 1) coverage: Anthropic median 77 rows (4/5 usable, one zero-row run); Mistral median 57 rows (all five usable, range 48–74); OpenAI median 83 rows (all five usable, range 76–90); Qwen median 42 rows (all five usable, range 33–45). The optimised protocol costs 2–4× more per run than naive across all agents; OpenAI's ratio is most extreme (median \$0.73 optimised vs \$0.27 naive). Arm 3 and arm 4 (with an evidence pack) are unscored at the time of writing but show higher row counts in Figure 3. We did not find published comparisons of frontier deep-research agents on structured-output coverage at this granularity; for the two agents with complete arm 2 data, the contrast is mixed — modest gain for OpenAI, regression for Qwen — while Anthropic and Mistral arm 2 failures preclude a clean comparison.

**Observed results (provenance quality).** Every Source 1, Source 2, and Notes cell across all 40 runs was parsed to measure citation coverage and corroboration. Figure 6 plots each run as inventory rows found (coverage) against rows where a second source was also cited (corroboration). The diagonal marks full double-sourcing. OpenAI optimised is the only agent to achieve both high coverage (79–96 rows) and near-complete corroboration (77–88 rows with Source 2 — approaching the full diagonal). Qwen clusters near the diagonal at low coverage (22–45 rows naive; 22–42 rows optimised), meaning nearly every plant it enumerates carries a second source. Mistral naive produces near-zero corroboration across all five runs (0 or 1 Source 2 citation per run) despite finding 48–74 rows; Anthropic arm 2 usable runs (50 and 90 rows) are pending corroboration scoring at time of writing. The most striking provenance gap is in the naive arm: all five Mistral runs and several Anthropic runs return tables with Source 1 citations but no Source 2. To our knowledge, per-row provenance analysis of this kind has not been published for frontier deep-research agents.

![](../report/inputs/generated/fig_exp2_coverage_certainty.pdf)\

*Figure 6. Coverage vs. corroboration across 31 Exp2 runs (9 with zero parsed inventory rows excluded: Mistral arm 2 all 5 runs, Anthropic arm 2 runs 2/4/5, and Anthropic arm 1 run 4). X-axis: inventory rows enumerated. Y-axis: rows with a Source 2 citation present. The dashed diagonal marks full double-sourcing (every row corroborated). Filled diamonds: optimised arm (arm 2); open circles: naive arm (arm 1). Colours encode agents. OpenAI optimised alone sustains high values on both axes; Anthropic optimised shows a corroboration ceiling despite growing coverage; Qwen clusters near the diagonal at low volume.*

## Fifth, a tailored solution can work

The heroic single prompt to a frontier agent approach leaves a lot on the table. While agents are impressive generalists, it is generally acknowledged in agentic systems design that algorithmic behavior should be scripted. The §2 quality dimensions measure the *output* — accuracy, coherence, provenance, temporality. A tailored pipeline adds a second axis: *method quality* — whether the process is auditable, reproducible, and cost-predictable independent of which model runs it. We implement a statistical workflow to demonstrate the feasibility of achieving acceptable scientific quality at the row level. Such a system is stateful: it maintains a knowledge base as an inventory of narrative asset histories, fully sourced. The narrative layer carries the historical dimension deferred in §2: plant lifecycle events, PDP-cycle reclassifications, developer changes, and contested status periods are recorded as annotated history rather than as overwritten state. The statistical table is only a derived artefact — a snapshot projection at a reference date — of the narrative asset-level inventory. The inventory is initially generated with a deep research heroic prompt. The four quality dimensions are automatically verified, annotating the narratives. The narrative is then incrementally updated, corrected, and extended with new documents. A memory of human judgements is preserved and used to guide the updates. To our knowledge, no published benchmark or system targets open-world enumeration of a national asset class with per-cell provenance at this granularity.

In future research, we aim to demonstrate that this method is model independence, runnable on local models for sovereignty and cost. Whether a well-chosen local model achieves this without the initial full deep-research stack, or whether parametric extraction already suffices, remains to be explored. 

We also aim to refine the method to ensure the per-cell provenance tracking, not just per row.  Each cell is a claim: a (source, date, confidence, conflict-resolution history) tuple. To our knowledge, the conjunction of per-cell provenance with per-cell temporal validity in LLM-augmented inventories has not been published; demonstrating it is part of the contribution we aim for. Sixth, a structural analogy. Each cell in a power-plant inventory — one plant, one attribute, one value — maps to a knowledge-graph triple: subject, predicate, object. Fusing tables from competing sources is therefore the same problem as fusing overlapping triple sets, with the same need for conflict resolution, source authority, and temporal versioning. Cases that rule-based schema-fixed systems cannot handle cleanly — assets mid-lifecycle, contested sources, multilingual records, conditional projections — are where language-model reasoning adds genuine value. This paper works with narratives structured tables; graph databases are a natural next layer.

---

## Discussion

**F1 as an aggregate.** Row-level F1 is the primary metric in §1 and §4. It is a useful single-number summary but an opaque one: it collapses coverage (are the right assets present?), freshness (are the values current?), articulation (was the query well-specified?), and coherence (are the claims consistent?) into a single score. A system can achieve high F1 by excelling on one dimension while failing silently on others — a well-articulated prompt against a stale corpus, for example, can return complete, internally consistent, but outdated values. The §2 four-dimensional framework exists precisely because F1 cannot discriminate these failure modes. Readers should interpret F1 comparisons as aggregate capability rankings, not as diagnoses of where a system is strong or weak.

**Articulation as a confound in F1.** Articulation — the gap between analyst intent and model query — has a soft boundary with coverage. A model that retrieves the correct fact but paraphrases it in a form the downstream extractor does not recognise produces a missing value in the output table; the symptom is indistinguishable from a genuine coverage gap. F1 therefore conflates two distinct failure modes: facts the model never found, and facts the model found but failed to express in extractable form. The structured four-section prompt in §1 is designed to close the articulation gap; the residual F1 deficit is more likely to reflect true coverage and freshness limits than articulation failures. But this remains an assumption, not a measured separation.

**External coherence.** The §2 coherence criterion distinguishes internal consistency (within the dataset) from external consistency (against world knowledge). The experiments in this paper measure internal coherence. Measuring external coherence is harder for three compounding reasons. First, the reference knowledge base is undefined: checking whether a stated capacity is plausible requires specifying which knowledge pool to check against — the RAG corpus, the model's parametric memory, official statistics, or physical engineering constraints — and these pools overlap imperfectly and carry different reliability. Second, the checker's capability matters: a small model used as evaluator has poor recall of world knowledge and will miss genuine inconsistencies; a large frontier model has better recall but may introduce its own confabulations as apparent corrections. Third, the depth of reasoning required varies by claim: detecting that a 6000 MW gas plant in a province with no pipeline access is incoherent requires multi-step inference, not lookup. Phase C cross-evaluation (Exp 2) partially engages external coherence — the judging agents bring parametric world knowledge — but does so implicitly and unsystematically. A principled external-coherence metric remains future work.

**Internal coherence as a zero-reference screen.** The reference list grades runs from the outside; an exploratory analysis of the Experiment 1 outputs suggests the weakest runs can be rejected without any reference at all. Degenerate runs are template-like: near-constant capacity and status columns (one run emits 496 rows, every one 1200 MW and "Operating"). Within-run capacity variability — the number of distinct capacity values — correlates with reference-based F1 at Spearman ρ = 0.90 across the 70 runs, and the signal is not an output-length artifact: the partial correlation controlling for row count is ρ = 0.89, and at matched length the two ~84-row extremes span one distinct capacity value (F1 = 0.00) versus thirty-seven (F1 = 0.61). An in-sample threshold rule rejects 23 of the 26 weakest runs with no false rejection — an existence proof rather than a validated detector, as the cutoffs were tuned on the same 70 runs. Notably, the internal-coherence indicators we already compute carry no such signal: fabricated rows use impeccable controlled vocabulary and plausible dates. This points to a two-level scoring design. The run-level screen rates one output; above it, a model-level reliability grade aggregates the screen across repetitions — a model version whose five repetitions all fail is disqualified as a source, independently of any single run. In the vocabulary of intelligence evaluation (the NATO "Admiralty" grading of STANAG 2511), the run-level screen rates *information credibility* while the model-level grade rates *source reliability*. Making these scorers part of the standard pipeline is future work.

**From noisy runs to fused estimates.** The per-plant recognition matrix in Annex E prefigures the research programme this benchmark opens: each reference plant becomes a column observed by many noisy runs — precisely the input object of latent-truth discovery and capture–recapture estimation. Within-model and across-model coherence can be read directly from the column densities (famous plants form dense columns, obscure ones sparse), and the operational core separates visibly from the project-dominated tail. Fusing such incomplete, differently-reliable lists into a single estimate — and bounding the residual share of plants that no source mentions by linear programming against a control total, such as the regulator's installed capacity per fuel [@HaDuong2005] — is the axis of research these column densities invite.

---

## Annex A — Related-work due diligence: methodology and disclosure

The claims of the form *"to our knowledge"* and *"we did not find"* throughout this paper rest on a structured per-paragraph related-work review conducted in May 2026. We disclose the method here so that readers and referees can calibrate the strength of those negative claims.

**Scope and standard.** This is an author's due-diligence review, not a systematic literature review. For each major paragraph of the argument we sought to anchor every empirical claim or framing to prior work, applying the standard *"defensible under peer review of one paragraph"*: a referee's likely "why didn't you cite X?" should have a prepared answer, with the alternative either cited or explicitly justified as not-cited. The deliverable was one due-diligence note per paragraph plus a cross-paragraph aggregator, kept as project working files.

**Authorship and assistance.** The per-paragraph notes were drafted by a large language model (Claude, using a structured `related-work-note` skill, single pass, 2026-05-21) under author direction. We have not yet read each primary source end-to-end; the candidate set, summaries, and "why cite / why not cite" justifications are LLM-generated and remain subject to author verification before they migrate into manuscript prose. References already cited in this paper have been spot-checked; the long tail of bibliography candidates in the working notes has not.

**Search procedure.** Candidates were assembled by agent recall — the model's parametric knowledge of the relevant literatures — plus targeted web fetches. We did not export from Web of Science, Scopus, Google Scholar, or Semantic Scholar. Every DOI, arXiv eprint, and URL referenced in the per-paragraph bibliographies was resolved at generation time via the agent's WebFetch tool, and unresolvable identifiers were dropped or replaced. Three identifiers did not resolve cleanly and are flagged for re-resolution at submission: the IMF Data Quality Assessment Framework page (403, URL is the canonical entry), one CACM Wikidata-overview DOI (verified via a DBLP fallback record), and the publisher PDF for the VLDB Ditto paper (the arXiv version was used as substitute, with publisher volume / issue / pages intentionally omitted from the entry).

**Citation budget.** Following project conventions we targeted 10–15 anchors per paragraph, with a tier mix of one field-defining anchor (often older), one recent survey, and two-to-three frontier works less than two years old. Two paragraphs deviated. The synopsis delivered eight anchors because its sub-literatures largely repeat those of the four-dimensional quality bar (§2) and of the tailored-solution paragraph (§5), so deeper coverage lives downstream. The capability-ladder paragraph (§3) was the tightest fit at the upper bound, as the brief covered six distinct sub-literatures — RAG, reasoning, deep research, agentic systems, tool use, agency — in a single paragraph.

**What this review did not do.** We did not perform a systematic database search. We did not re-read primary sources end-to-end before drafting. We did not run a preprint-to-peer-review update sweep, so a small number of arXiv entries may have a more recent venue-of-record we have not yet incorporated. We did not reproduce any cited result. The "related but not cited" justifications are LLM-judged and may miss closely-adjacent work that an expert reader would catch. The strength of every *"to our knowledge"* and *"we did not find"* claim in this paper should be read against these limits.

---

## Annex B — Experiment 1: Technical specification

*[Design locked by ticket 0175 (2026-05-20). This annex describes the experiment as it will be run.]*

### Task

Identify all thermal power plants in Vietnam from parametric model knowledge alone. The target population is defined by the reference inventory `data/reference/vietnam_thermal_plants_v2_classified.csv`: 173 plant-level records covering coal (81) and gas/gas-oil (92), across all lifecycle statuses (operational, under construction, proposed, planned, cancelled, retired). The reference was compiled by the author from primary sources (PDP7, PDP7A, PDP8 annexes, EVN annual reports, MOIT decisions) and is version-locked for this experiment.

### Reference dataset provenance

The reference inventory was assembled by single-author manual compilation, cross-referenced against the 18 source documents snapshotted in `data/rag_corpus/` (PDP7, PDP7A and PDP8 annex tables, EVN annual reports, Report_32, Report_58, Study E542 unit tables) plus a small number of MOIT decisions consulted off-corpus by the author. The broader quality framework that motivates the design is documented in `docs/quality-grounding.md`. The dataset is frozen at commit `85a0e6c` (2026-05-20) for Experiments 1–3; per-row source priority, the full file inventory, and MOIT decision identifiers are recorded in `data/reference/PROVENANCE.md`.

Residual uncertainty concentrates in the 62 "proposed" and 21 "planned" rows: these forward-looking statuses carry the highest volatility across PDP cycles. The three cases most likely to shift status, capacity, or developer between the freeze date and any downstream use are LNG Cái Mép Hạ (Bà Rịa-Vũng Tàu, 6000 MWe), LNG Hà Tĩnh (6000 MWe), and Dung Quat SEZ J-Power Phase I (Quảng Ngãi, 2400 MWe coal). To our knowledge, no independent per-plant audit-trail dataset exists for Vietnam's thermal fleet, and we did not find a second human-curated reference at comparable granularity; the planned three-way reconciliation with Global Energy Monitor (see §2) is the closest available external check and is deferred.

### Prompt

The baseline prompt is the locked composition of two modules from `experiments/prompts/modules/`: `2_goal.txt` (task declaration) and `5_table.txt` (structured table specification). These are the implicit "always" pair — every sweep includes them; ablations opt in to additional modules. The assembled prompt is the concatenation in filename lex order, joined by a blank line:

> **## Goal**
>
> Produce a complete, primary-sourced reference inventory of Vietnam's past, present and future thermal generation assets (> 30MWe) structured as follows:
>
> **## Structured power plants table**
>
> Tabulate for every thermal power plant in Vietnam:
>
> | Name (Vietnamese) | Name (English) | Province | Fuel | Technology | Units × MW | Total MWe | Status | COD | Owner/Developer | Source 1 | Source 2 | Notes |
>
> Where:
> - Fuel: Coal / Domestic gas / Imported LNG
> - Technology (coal): Subcritical / Supercritical / USC
> - Technology (gas): CCGT / OCGT
> - Status: Approved / Planned / Operational / Under construction / Suspended / Cancelled / Retired
> - Total MWe: Include units > 30MWe.
> - COD: Actual or expected commercial operation date
> - Sources: specify where in the document, include URL
>
> Output format: Markdown.

No persona, no narratives, no quality bullets — those land in ablation sweeps, not the baseline. Every API call carries a system instruction explicitly forbidding web search: *"You have no web search capability. Do not claim to perform searches, do not invoke tools, do not fabricate URLs. Answer from parametric knowledge only."*

### Models

Sixteen models from `modelset_ablation_journal` (v2, defined in `experiments/experiments.toml`), organised around three language families with multiple labs per family:

| Model | Lab | Family | Size class | Reasoning tokens* |
|---|---|---|---|---|
| claude-opus-4.6 | Anthropic | EN | frontier | 0 |
| claude-sonnet-4.6 | Anthropic | EN | frontier | 0 |
| claude-haiku-4.5 | Anthropic | EN | mid | 0 |
| gpt-5.5 | OpenAI | EN | frontier | 1,537 |
| gpt-oss-120b | OpenAI | EN | large | 35 |
| gpt-oss-20b | OpenAI | EN | mid | 18 |
| mistral-small-2603 | Mistral | FR | mid | 0 |
| mistral-medium-3-5 | Mistral | FR | mid | 0 |
| mistral-large-2512 | Mistral | FR | frontier | 0 |
| qwen3.6-27b | Alibaba | ZH | mid | 5,735 |
| qwen3.6-35b-a3b | Alibaba | ZH | mid | 8,143 |
| qwen3.6-flash | Alibaba | ZH | mid | 7,971 |
| qwen3.6-plus | Alibaba | ZH | frontier | 6,677 |
| qwen3-max-thinking | Alibaba | ZH | frontier | 0 |
| deepseek-v4-pro | DeepSeek | ZH | frontier | 16,774 |
| deepseek-v4-flash | DeepSeek | ZH | mid | 775 |

\* Median over 3 runs.

Mistral's per-tier branding (Small 4 / Medium 3.5 / Large 3) is the lab's own scheme and does not denote a generation order; we adopt their naming verbatim. All sixteen models received identical call parameters (T=0, seed=42, max_tokens=32768, no-web system instruction). The only reasoning-related signal sent was `reasoning_effort = "minimal"` for the two `gpt-oss-*` entries, declared in the registry. The "Reasoning tokens" column reports the median `completion_tokens_details.reasoning_tokens` field over the post-fix top-up cohort (ticket 0198, 2026-05-21, $N{\leq}3$ per model). The original baseline cohort (2026-05-20) ran on a harness that stripped `usage.completion_tokens_details` before writing records to disk, a bug fixed in PR #379 (ticket 0195); the top-up sweep was issued post-fix with identical call shape to recover the column. Two regimes are visible: Anthropic and Mistral models report 0 reasoning tokens across all reps; DeepSeek V4, all Qwen3.6 entries that we could run, GPT-OSS, and GPT-5.5 allocate between dozens and 16,774 tokens to internal reasoning. `qwen3-max-thinking` reports 0 despite the explicit naming: OpenRouter does not expose reasoning tokens for this model in the absence of an explicit `reasoning_effort` flag. `qwen3.6-flash` retains $N{=}1$ post-fix because Alibaba's free-tier upstream rate-limited additional attempts. For `qwen3-max-thinking`, an early minimal-effort smoke produced 5/5 refusals; the no-effort lineup recovered 5/5 usable rows after a parser fix that handles markdown section dividers inside structured-output tables. The four Wave-2 SOTA labs (Anthropic, OpenAI, Mistral, Alibaba) each contribute their journal-pinned flagship — Opus 4.6, GPT-5.5, Mistral Large 2512, Qwen 3 Max Thinking — so Experiment 2's "deep research vs parametric" claim can be tested within-model (qwen3-max via OpenRouter here, qwen3-max-2026-01-23 via DashScope in Experiment 2). Opus 4.6 is preferred over the newer 4.7 for the parametric baseline because 4.7's verbosity exceeds the `max_tokens` budget on the full Vietnam plant table. **GPT-5.5 declines this task on 3 of 5 reps**, opening with "I can't honestly produce a complete, primary-sourced inventory..." and refusing to fabricate URLs or source citations from parametric knowledge alone. We retain the declined responses as data — a model viewpoint on the request's epistemic standard, not extraction noise.

### Run parameters

| Parameter | Value | Rationale |
|---|---|---|
| Repeats per model | 5 | Sufficient to characterise within-model variance; pilot (n=2–5) shows variance stabilises |
| Temperature | 0 | Isolates prompt-driven variance from sampling noise; residual variance under T=0 is the stronger claim |
| Seed | 42 | Reproducibility where supported by provider |
| Max tokens | 32768 | Sized to accommodate verbose frontier models (Opus, GPT-5.5) on the full Vietnam thermal-plant table; an 8k cap truncated Opus 4.6/4.7 mid-table during pilot |
| Budget | $15 | Per-sweep cap; the runner halts at exceedance |
| Total runs | 80 | 16 models × 5 repeats |

`seed` is best-effort on OpenRouter: Anthropic and OpenAI honour it for sampling RNG, Mistral and DeepSeek treat it as advisory. The MoE entries (gpt-oss-*, mistral-large-2512, qwen3.6-35b-a3b, qwen3.6-plus, qwen3-max-thinking, deepseek-v4-pro, deepseek-v4-flash) carry residual non-determinism even at T=0 + seed pinning, characterised in ticket 0139 work; the 5-repeat budget surfaces this as observed within-model variance rather than treating it as noise to be eliminated. To our knowledge, MoE non-determinism specifically for multi-row structured outputs at deterministic decoding settings has not been characterised in prior literature; the present discipline is informed by in-project measurement rather than external benchmarks.

### Post-fix top-up cohort and interday variability

The original 16-model × 5-rep baseline was executed on 2026-05-20 against a harness that silently dropped `usage.completion_tokens_details` (PR #379, ticket 0195). To recover the reasoning-token signal without re-running the full sweep, ticket 0198 added a post-fix top-up: $N{\leq}3$ additional reps per model on 2026-05-21, identical call shape (same `model_set` IDs — recorded as the frozen `modelset_exp1_baseline`, since two journal-set IDs had been edited between the two days; same prompt, temperature, seed, max_tokens, system instruction). Outcome metrics (F1, coverage, fuel/status/province accuracy) pool both cohorts; reasoning_tokens are reported from the post-fix cohort only. Three models (qwen3.6-flash on Alibaba's rate-limited free tier; gpt-5.5 with refusals on principled grounds; deepseek-v4-pro with provider-side `null` content errors) yielded fewer than 3 post-fix reps; the per-model N is shown in the topup-results table (`tab_exp1_reasoning_topup` in the report).

A canary rep per model was compared against the original 5-rep range before launching the top-up. Three models showed $|\Delta\text{F1}| > 2\sigma_{\text{baseline}}$ between cohorts at fixed call shape and seed: deepseek-v4-pro ($-0.185$), qwen3.6-27b ($+0.289$), qwen3.6-35b-a3b ($+0.165$). We pool all reps regardless and surface this as an interday-variability finding rather than excluding the drift models: $T{=}0$ and `seed=42` do not neutralise silent provider-side movement (routing changes, checkpoint updates) for these labs over a 24-hour window. To our knowledge, day-scale F1 drift at fixed deterministic call parameters has not been quantified for production LLM APIs on structured extraction tasks.

### Evaluation

Each run is evaluated against the reference by `src/aedist/evaluate.py`. Plant pairs are matched by mixed-integer linear programming (MILP) — the LP matcher in `src/aedist/matching/lp.py` (ADR-2) — minimising a cost that combines (i) rapidfuzz `partial_ratio` name similarity, with candidate pairs requiring `similarity_threshold ≥ 90` (integer 0–100 scale), and (ii) a small capacity-difference term (`capacity_weight · |Δcapacity_MWe|`, default weight 0.001). Province and fuel are deliberately not part of the matching cost (ADR-3); they are scored separately as cell-level attribute accuracy on the matched pairs. The optimal one-to-one assignment is then solved globally rather than picked greedily. Metrics recorded per run:

| Metric | Level | Description |
|---|---|---|
| `n_plants` | run | Number of rows extracted |
| `tp`, `fp`, `fn` | run | True/false positives, false negatives against reference |
| `f1` | run | Row-level F1 = 2·P·R / (P+R) |
| `fuel_accuracy` | cell | Fraction of matched rows with correct fuel classification |
| `status_accuracy` | cell | Fraction of matched rows with correct lifecycle status |
| `province_accuracy` | cell | Fraction of matched rows with correct province |
| `cost_usd` | run | API cost in USD |
| `wall_s` | run | Wall-clock time in seconds |
| `tokens_out` | run | Output tokens consumed |

Run outcomes other than `ok` (refusal, empty, parse error) are recorded with `f1 = 0` and flagged in `status`.

### Sweep configuration

The sweep is defined in `experiments/experiments.toml` as `sweep_ablation_p1_direct_base` (model_set = `modelset_ablation_journal`, repeat = 5, T = 0, seed = 42, budget_usd = 10, max_tokens = 8192, prompt_modules = []). Outputs land in `experiments/outputs/ablation/direct/p1_base/`; the prior pilot runs are preserved under `p1_base.pilot/` (ticket 0175 renamed the directory to keep journal and pilot data separate). Results are ingested into `measurements.jsonl` via `make rebuild-measurements`.

Experiment 1 was run as 5 reps per model on 2026-05-20 and topped up with 3 additional reps per model on 2026-05-21 after a harness fix (PR #379) restored capture of `reasoning_tokens`. The top-up reps land in `experiments/outputs/ablation/direct/p1_base.topup_canary/` and `p1_base.topup/`; we pool them with the original five unconditionally — no canary gate. Intra-day variability across the two acquisition windows is absorbed into the reported within-model spread rather than filtered out.

### What this experiment does and does not test

This experiment establishes the *parametric ceiling*: the best row-level quality achievable from model memory alone with a well-specified prompt and no external information. It leaves three of the four quality limits open: Coverage (facts absent from training data), Freshness (facts post-dating training cutoff), and Coherence (synthesis errors across the table). Only Articulation — the gap between intent and prompt — is partially addressed by the structured prompt. The gap between this ceiling and the quality bar defined in §2 motivates the subsequent experiments.

---

## Annex C — Experiment 2: Technical specification

*This annex describes Experiment 2 as actually run. The registered batch (protocol locked before dispatch) ran two arms — naive and optimised — over the four agents below, N=5 per agent per arm, for 40 production sessions. Two further unregistered, exploratory conditions (the same naive and optimised surfaces with a reference document pack attached) were added during execution, bringing the corpus to 80 runs and forming the 2×2 factorial (query mode × documents) reported in §4's Figure 3 and below. Row-level F1 against the reference was scored for all 80 runs (40 registered + 40 exploratory). Phase C cross-evaluation on the four §2 dimensions is deferred to post-conference analysis. The full registered-report write-up — registration, the H1–H6 analysis plan, execution deviations, and the descriptive statistics — lives in the technical report's Experiment 2 chapter; this annex pins only the as-run specification and references that chapter for the inferential analysis.*

### Task

Identify all thermal power plants in Vietnam using four SOTA cloud agents with extended reasoning and web access. Same target population as Experiment 1: the 173-plant version-locked reference inventory at `data/reference/vietnam_thermal_plants_v2_classified.csv`.

### Agents

Four direct-API agents, ordered by ascending baseline smoke cost. API keys live at `~/.config/keys/`. OpenRouter is not used here — vendor-direct invocation keeps web-search billing transparent.

| # | Vendor | Model | Country | Surface | Ticket |
|---|---|---|---|---|---|
| 1 | Mistral | Mistral Large 2512 | FR | Agents API + `web_search` connector | 0169 |
| 2 | Alibaba | Qwen3-Max | CN | DashScope, `web_search` inside thinking mode | 0173 |
| 3 | OpenAI | GPT-5.5 | US | Responses API + `web_search` + reasoning | 0168 |
| 4 | Anthropic | Claude Opus 4.6 | US | Anthropic API + `web_search_20250305` + adaptive thinking | 0167 |

Anthropic is pinned to Opus 4.6 (not 4.7) per the 2026-05-20 compose decision: identical call shape, ~40% lower per-call cost on the verified probe. Kimi K2.6 is disqualified — vendor docs document `thinking` and `$web_search` as mutually exclusive, fatal for §4's "extended reasoning AND web access" requirement. Geographic / corpus spread (US × 2 + FR + CN) is hypothesis-relevant: Chinese-language investor and trade documents on Vietnamese power assets are under-indexed by Western search.

### Baseline reference for cross-comparison

The naive one-shot baseline that §4 compares against is **not** §1's `modelset_ablation_journal` sweep. It is the pre-existing `experiments/outputs/direct_complete/` artifact from `sweep_direct_complete` over `modelset_frontier_10labs` — a wider lab survey at a single rep per model. Phase C will read from it directly; it is not re-run.

### Phase structure

**Phase A — Reflexive prompt design (optimised arm).** Each agent receives the baseline prompt (`experiments/prompts/prompt_complete.txt`), the four §2 quality-dimension paragraphs verbatim, the task statement, a JSON envelope spec, and the per-session budget cap (announced upfront — see "Phase B dialogue policy" below). The agent is asked to return a fully-specified design — `system_prompt` (threaded into the provider's system field at agent creation), `designed_prompt` (the user-side prompt sent on turn 1 of Phase B), `settings` (`thinking`, `max_tokens`), and `rationale` — that maximises the quality of the report it will produce within the dual-axis session cap (below) and an overnight wall-clock. Outputs land as `<agent>_phase_a.json` with the four envelope fields. Harness: tickets 0170, 0213.

**Phase B-0 — Single-rep smoke (optimised arm).** Each designed prompt runs once (N=1) end-to-end through the multi-turn auto-reply loop (see "Phase B dialogue policy"). This is *Test one before blasting* applied at the experiment level: four outputs surface adapter parser bugs, prompt failures, refusals, and real per-session cost before committing the full N=5 batch. Gate to Phase B is a human review confirming (i) all four adapters produced valid `RunRecord` instances, (ii) parsed tables are non-empty, (iii) costs sit within the dual-axis session cap empirically.

#### Phase B dialogue policy (locked by tickets 0207 + 0214; fixed experimental condition)

After the Phase A design call, Phase B was a multi-turn conversation against the same agent, driven by a small state machine. The author-side reply was one of three fixed strings; the choice was made after each agent response by a one-shot LLM classifier deciding whether the agent had "produced a report" or not. The classifier's cost was harness overhead and was *not* deducted from the SOTA agent's session budget. The as-run classifier was `deepseek/deepseek-v4-pro`; the registered — and earlier-run — choice was `nvidia/nemotron-nano-9b-v2`, with `mistral-small-latest` confined to the pilot. DeepSeek is a third-party vendor distinct from all four subjects (Anthropic, OpenAI, Mistral, Alibaba), so the classifier never formed a same-vendor self-evaluation pair with the agent it judged — the cross-vendor independence the registration sought when it moved off the original same-vendor classifier (protocol_05 §3.5, "Third-party classifier").

Three reply strings, verbatim:

- **ENCOURAGE** (sent up to three times before forcing terminal): *"Proceed as you think is best in autonomous agentic mode."*
- **VERIFY** (sent exactly once after the first agent response classified as a report): *"Thank you for the inventory. Please now verify and polish it in ONE focused pass, prioritising: (a) per-row provenance — every Source 1 and Source 2 cell must point to a specific URL from your bibliography; (b) coverage — any plant present in your bibliography but absent from the table; (c) temporality — every row has an as-of date or status-change note; (d) internal consistency — capacity totals reconcile across the table and the statistical summary. Return the corrected inventory only — no meta-commentary on what you changed."*
- **TERMINAL** (sent when remaining budget ≤ 20% of the cap, or after three consecutive `no_report` classifications — ENCOURAGE on the first two, TERMINAL on the third): *"I have no additional directive to give you. Please proceed to generating the report without further asking. If you cannot, we would appreciate to know why, but the discussion will stop here in any case. Thanks for your understanding."*

Every user-side message after turn 1 carries a chat-text status prefix — *"Status: remaining X.XK of 50K tokens, \$X.XX of \$3.00. Wall-clock elapsed Ys. Verify <state>."* — exposing both budget axes to the agent, and, where the provider exposes a metadata surface, a structured metadata field carrying `cap_tokens` and `cap_usd`. After VERIFY's response is captured (or after TERMINAL's response), the loop terminates.

**Phase B — Execution (N=5).** Gated on a clean B-0 review. Each designed prompt runs five times against a single provider per agent (closed-weight SOTA agents have one vendor each; the cross-provider variance reported for MoE models in Annex B does not apply). The four Phase B-0 sessions are the first reps of these five.

### Arms and budget

The registered design has two arms over the same four agents, five reps each (40 production sessions):

- **Naive arm** — Doc-07 (`experiments/sota/protocol_07_naive_prompt.md`) sent verbatim as the sole user message, no system prompt, web search on, one model response per session. This carries the v2 task statement and quality criteria but none of the optimised arm's methodology (budget rules, planning headroom, source admissibility, calibrated confidence vocabulary). It is the null comparator: the contrast between arms isolates the protocol scaffolding's contribution.
- **Optimised arm** — Phase A design call followed by the Phase B multi-turn state machine above (Phase B-0 then Phase B-full).

Both arms share one **dual-axis per-session budget cap: 50 000 tokens *or* a \$3 dollar guard, whichever fires first triggers TERMINAL.** Per protocol_05, dollar-only caps disadvantage models with expensive output tokens; the token cap binds reasoning capacity comparably across vendors while the dollar guard binds total bill. The cap is the experimental condition — no session is dropped for cost or wall-time reasons. The realised per-session and per-batch costs are reported in §4's Figure 3 and the technical report chapter, not pinned here.

### As-run deviations from the registration

The experiment was pre-registered (protocol locked before the production batch, with an H1–H6 analysis plan). Execution deviated from the registration in three headline ways, all reported candidly rather than hidden:

- **A documents axis was added.** Beyond the two registered arms, two further *unregistered, exploratory* conditions — the same naive and optimised surfaces with a reference document pack attached — were run, expanding the corpus from 40 to 80 sessions and forming the 2×2 factorial (query mode × documents) of §4's Figure 3. These two conditions are exploratory by construction: they are never aggregated with the two registered arms.
- **Claude's optimised arm is excluded from the bibliography-quality table (0 of 5 runs).** None of Claude's five optimised-arm sessions yielded a bibliography parseable by the structure analyser, so the cell is blank in the bibliography-quality table. This is a *bibliography-parsability* exclusion only: those same five sessions remain row-level-F1-scorable (N=5) via the LP matcher, and they are present in the 2×2 F1 table. The 0/5 must not be read as the runs failing outright.
- **Phase C cross-evaluation is deferred.** The four-dimension peer cross-evaluation (ticket 0171) was reserved for post-conference analysis; the as-run results below and in §4 are the operational and F1-based metrics, not the §2-dimension cross-eval scores.

The registered-report treatment of these — the locked H1–H6 plan, per-arm validity and exclusion criteria, and the descriptive F1/cost statistics — is in the technical report's Experiment 2 chapter; this annex does not reproduce those statistics.

### Harness

This experiment is script-based, not sweep-based. No `sweep_exp2_*` block exists in `experiments/experiments.toml`. Implementation surface:

- `src/aedist/adapter_mistral.py` — Mistral Agents API adapter (multi-turn continuation + 5xx retry per tickets 0208/0215).
- `src/aedist/adapter_qwen_dashscope.py` — DashScope adapter (multi-turn continuation per ticket 0208).
- `src/aedist/adapter_openai_responses.py` — OpenAI Responses adapter (multi-turn continuation per ticket 0208).
- `src/aedist/query_anthropic.py` — Anthropic adapter (multi-turn continuation per ticket 0208).
- `experiments/sota/exp2_interactive_smoke.py` — author-side harness running Phase A + Phase B state machine.
- `experiments/sota/dialogue_classifier.py` — one-shot LLM classifier deciding `report` vs `no_report` per ticket 0214.
- `experiments/outputs/sota_smoke/` and `sota_exp2_smoke/` — artifact directories. Each Phase B turn writes `<agent>_turn_NN.{user.txt,raw.json,record.json,cost.json,classification.json,report.md,citations.json}`.
- `experiments/derived/tab_exp2_2x2.csv`, `report/inputs/generated/tab_exp2_bib_quality.tex` — as-run derived tables (2×2 F1/cost factorial; per-arm bibliography quality). The `experiments/derived/sota_cross_eval.csv` Phase C target is reserved for the deferred cross-evaluation.

### Evaluation

Phase B outputs are evaluated against the 173-plant reference using the same `src/aedist/evaluate.py` machinery as §1 (LP matcher, ADR-2/3, `similarity_threshold = 90`, `capacity_weight = 0.001`), yielding row-level F1 and per-attribute accuracies. Phase C cross-evaluation — peer scoring of each output on the four §2 dimensions using the rubric in ticket 0171 — is deferred to post-conference analysis; the as-run results are the F1-based and operational metrics of §4, not the §2-dimension cross-eval scores.

### What this experiment does and does not test

This experiment tests whether removing the §1 handicaps (no web, no tools, no documents) — by handing the task to a commercially available deep-research surface — clears the §2 quality bar. It does not test custom workflows or local models; that is §5. It does not test how the four dimensions trade off under a fixed budget; that is §5 + ticket 0201 once the composite-quality scorers exist. It does not test browser-automated surfaces (ChatGPT.com, Claude.ai chat UI) — only direct vendor APIs.

**Wikipedia/Wikidata compliance.** Because a derivative of the reference dataset was published on Wikipedia before the experiment, Protocol §3.4 bans Wikipedia, Wikidata, DBpedia, and mirrors as admissible sources — the risk is both training-data and web-search contamination. We audited compliance mechanically: URL-domain matching over every Source 1 and Source 2 cell and every bibliography entry of all 40 registered runs. We detected banned-domain citations in 5 of the 20 optimised-arm runs, concentrated in Mistral (runs 1–4) and OpenAI (run 1); we did not detect banned-domain citations in the Anthropic or Qwen optimised runs. In the naive arm, where the prompt carries no source ban, 1 of the 20 runs (OpenAI run 5) cited a banned domain. This audit is mechanical only: paraphrased Wikipedia content without a URL is not detected.

---

## Annex D — Temporality: state representations vs. event representations

The temporality dimension in §2 measures *snapshot currency*: whether each value carries a best-effort "as-of" date and whether notable status changes are flagged. This is a deliberately scoped definition; a richer requirement exists and is worth naming precisely.

**The underlying philosophical tension.**
Parmenides held that reality is Being — stable and fully described by its current state; a snapshot suffices. Heraclitus held that reality is Becoming — flux is primary, "you cannot step into the same river twice"; the event is the fundamental unit and states are temporary arrests of a process. Aristotle deferred the tension rather than dissolving it: *substance* (what a thing is, state) vs. *accident* (what happens to it, event). Process philosophy (Whitehead, 20th c.) revives the Heraclitean position — events are ontologically primary; objects are abstractions over event-streams. No absolute resolution has been reached; the choice remains use-conditional.

**Accounting practice.**
Double-entry bookkeeping is the classical practical reconciliation: the *journal* records events (transactions); the *balance sheet* reports state (period-end snapshot); the *income statement* reports flows (events aggregated over an interval). All three representations are necessary. IFRS debates about recognition timing — when does an event become a balance-sheet state change? — are exactly this tension made regulatory (e.g., IFRS 15 revenue recognition, IFRS 16 lease capitalisation).

**Statistics.**
Stock variables (capital, population) are measured at a point in time — state. Flow variables (investment, births) are measured over an interval — events. The distinction matters for unit-root tests, cointegration, and error-correction models. Survival analysis and event-history models take the Heraclitean stance explicitly: the observation is a time-to-event, not a snapshot. The Markov property is the Parmenidean assumption: current state is sufficient, history beyond it adds nothing — an empirical bet, not a theorem.

**Integrated Assessment Model practice.**
IAMs (REMIND, MESSAGE, TIMES/MARKAL, GCAM) reconcile the tension via *capacity vintaging*: every installation event creates a stock unit tagged with a birthdate and a lifetime. System state at time T is the integral of all past installation events minus retirements. IAMs are therefore formally event-sourced but query-optimised for state snapshots. This architecture implies that a database feeding an IAM should, in principle, support reconstruction of system state at *any* reference date — not only the most recent snapshot.

**Two distinct quality requirements.**
This distinction yields two separable temporality criteria for an energy-asset database:

- **T1 — Snapshot currency**: each value carries a source-publication date and a best-effort "as-of" validity period; status changes since that date are flagged. This is what §2 requires and what the experiments measure.
- **T2 — Historical reconstructability**: the database supports queries of the form "what was the installed fleet as of 2018?" This requires logging the events (commissioning, retirement, capacity revision, status reclassification) that change state over time — the approach taken by Global Energy Monitor rather than the Global Powerplant Database snapshot model.

The present paper scopes to T1. T2 is acknowledged as the stronger requirement for IAM and scenario-projection use cases; it is not in scope here. A GEM-style event log may become necessary when implementing the verified-provenance layer (§5, future work) — each verification act is itself a timestamped event — but that design choice is deferred to a subsequent paper.

The narrative inventory component of §5 handles longitudinal aspects pragmatically: plant histories, PDP-cycle reclassifications, and developer-name changes appear as free-text annotations rather than as structured event records. This is a deliberate scoping decision, not an architectural commitment.

*See ticket 0245 for extension of this note to international energy statistics methodology guidebooks (IEA, UNSD, Eurostat, IRENA).*

---

## Annex E — Experiment 1: per-plant recognition matrix

Figure 7 aligns each of the 173 reference plants on a fixed column, for the 70 Experiment 1 runs (14 models × 5 repetitions, ordered as in Figure 1: by architectural family, then by decreasing effective parameter count). A blue cell marks a recognized plant (true positive); an empty cell, a miss. Reference columns are ordered by status group, then by decreasing capacity, so the status bands align with the difficulty table in §1. The left panel shows the 40 most frequent false positives across all runs, sorted by decreasing occurrence; red follows the paper's false-positive convention (unrecognized — possibly real, not necessarily fabricated). Unlike Figure 1, which packs recognized plants leftward, the fixed-column alignment reveals *which* plants each model misses: famous plants form dense columns, obscure ones sparse columns.

```{=latex}
\begin{landscape}
```

![](../report/inputs/generated/fig_exp1_recognition_matrix.pdf){width=100% height=85%}\

*Figure 7. Experiment 1 recognition matrix: 173 reference plants (columns, ordered by status then decreasing capacity) against 70 runs (rows, one label per model, 5 repetitions each). Blue = plant recognized; left panel: the 40 most frequent false positives (red).*

```{=latex}
\end{landscape}
```

The status-composition difficulty table (same data derivation: library `aedist.exp1_recognition`) appears in §1.

---

## Bibliography

*[PLACEHOLDER. Cite keys throughout this document follow the pandoc-citeproc `[@key]` convention and resolve against `report/refs.bib`. To render with citations: `pandoc slides/manuscript/main.md -o slides/manuscript/main.pdf --pdf-engine=tectonic --resource-path=slides --citeproc --bibliography=report/refs.bib`. A Makefile target for the manuscript with citeproc wired in is not yet in place; the current pandoc invocation in this worktree omits citeproc, so `[@key]` markers render verbatim. Until the build is wired, the full bibliographic entries live in `docs/related-work/*.md` (per-paragraph notes) and in `report/refs.bib`.]*

