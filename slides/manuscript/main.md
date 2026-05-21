# Synopsis — Beyond RAG: Stateful-Agentic Architectures for Reliable Economic Statistics

Minh Ha-Duong, 2025-05-06

Economic and engineering analysis using open energy-system models such as PyPSA-ASEAN need power-plant inventories of industrial assets that are complete, accurately dated, and traceable to primary sources — enabling quasi-real-time support for policy analysis in countries where the data landscape changes faster than publication cycles. Yet across most of the world the relevant facts arrive late, incomplete, or under licences that forbid redistribution, even though the underlying information is already public — scattered across project documents, master plans, environmental assessments, operator reports, and press releases. The general problem behind the specific one is older than AI: science needs knowledge, not opinions. Statistical work requires facts that are sourced, reproducible, and auditable, not plausible-sounding outputs from a random words generator somewhere in the cloud.

This paper builds the argument in six steps.

## First, the baseline

Submitting a direct query to a large language model produces an inventory-shaped answer, but not one that meets statistical or scientific quality standards. Numbers shift between runs, citations are absent or fabricated, and there is no way to tell which cells one should trust.

**Experiment 1 — Parametric baseline.** We query sixteen language models from the *modelset_ablation_journal* set — spanning three language families (EN/FR/ZH) and five laboratories from mid-range through frontier-class systems — with a fixed structured table specification prompt (the locked `2_goal + 5_table` composition, reproduced in Annex A). No documents are provided; models draw exclusively on parametric knowledge and receive a system instruction forbidding web search. Each model is queried five times at temperature zero, yielding 80 runs against a 163-plant reference inventory of Vietnamese thermal power plants (coal and gas, all lifecycle statuses). Runs are evaluated by matching extracted plant names against the reference using fuzzy string matching, yielding row-level precision, recall, and F1; fuel type, operational status, and province accuracy are scored at the cell level for matched rows. Cost in USD and wall-clock time are recorded per run.

**Results.** Across 80 runs (16 models × 5 repeats), 77 produced usable tables and 3 were refusals (all GPT-5.5). Row-level F1 across the 77 usable runs ranges from 0.01 to 0.76, with a mean of 0.38. Within-model F1 variance is large: DeepSeek V4-Flash ranges from 0.01 to 0.65 across 5 identical runs, and GPT-OSS-20B from 0.23 to 0.76 — spreads wider than the gap between many adjacent model means. Even for correctly matched plants, attribute classification remains mediocre: mean fuel accuracy 0.53, mean status accuracy 0.53, mean province accuracy 0.61. No monotonic relationship between API cost and F1 is observed: Claude Opus 4.6 at \$1.23 total achieves mean F1 = 0.46, while GPT-OSS-20B at \$0.01 reaches 0.58. To our knowledge, this non-monotone cost-versus-F1 relationship for structured factual extraction has not been documented in prior literature. The total experiment cost is \$2.85. Five qualitative failure modes organise the model-by-run distribution: GPT-5.5 refuses the task on 3 of 5 runs (*Récalcitrant*), citing inability to produce sourced data from parametric knowledge; Claude Haiku consistently finds only 17 plants (*Incomplet*); Qwen 3.6-27B fabricates up to 268 false positives in a single run (*Hallucinant*); DeepSeek V4-Flash and GPT-OSS-20B exhibit the widest within-model variance (*Non-déterministe*); and no cost ordering predicts quality (*Non-monotone*).

![Figure 1](inputs/generated/fig_census_direct.pdf)

*Figure 1. Direct-query performance across 16 models and 80 runs on the 163-plant Vietnam thermal reference. Each bar is one run; blue segments are correctly identified plants (TP), orange segments are fabricated plants (FP). The dashed green line marks the 163-plant reference. Models are grouped on the vertical axis. Five qualitative failure modes are visible: Récalcitrant (refusal), Incomplet (systematic under-coverage), Hallucinant (fabricated plants), Non-déterministe (high within-model variance), Non-monotone (no cost–quality ordering).*

![Figure 2](inputs/generated/fig_pareto.pdf)
<!-- raw data: slides/inputs/generated/pareto.csv -->

*Figure 2. Accuracy–cost view across the Experiment 1 lineup. Each marker is one of the sixteen models from `modelset_ablation_journal`, plotted at its median row-level F1 across the five reps against its mean per-call API cost (USD, linear scale). Whiskers span the minimum and maximum F1 observed across the reps for that model — a direct view of within-model run-to-run variability rather than a confidence interval. Marker colour encodes language family: blue for EN labs (Anthropic, OpenAI), vermillion for FR (Mistral), bluish-green for ZH (Alibaba, DeepSeek), all from the colorblind-safe palette in `palette.toml`. No Pareto-efficient envelope is drawn; the figure is descriptive. Per-model numbers backing this figure are written to `slides/inputs/generated/pareto.csv` for audit.*

## Second, the quality bar that any acceptable dataset must clear

Datasets can be assessed on four dimensions: accuracy, coherence, provenance, and temporality.

1. *Accuracy* asks whether the dataset contains the right assets and the right attributes. At the row level, this means recall and precision: does the system find all relevant assets, and does it exclude non-assets or duplicates? For a simple inventory table, this can be measured against a manually curated reference table using precision, recall, and F1 score. At the cell level, accuracy asks whether the attributes attached to each asset are correct: capacity, fuel type, location, operator, commissioning year, status, and so on. A system can therefore be accurate in entity discovery but weak in attribute extraction, or conversely reliable on attributes once the correct asset has been identified.

2. *Coherence* asks whether the dataset is internally and externally consistent. Internally, statistical tables have control constraints: aggregate totals should match regional or technology subtotals when those totals are known; capacities should not be negative; duplicate units should not be counted twice; and cross-row values should not contradict one another. Externally, the dataset should remain compatible with other available knowledge: units, orders of magnitude, geographic location, technology type, and commissioning dates should all be plausible. When sources contradict one another, the dataset should reconcile them convincingly — recording which source was chosen and why — rather than silently adopting one value. A minimal coherence requirement is non-contradiction. A stronger requirement is inferential closure: the system should derive and expose all consequences that follow from the available documents and accounting rules, rather than merely storing isolated claims.

3. *Provenance* requires a pedigree for each data item. Every row, and ideally every cell, should trace back to specific passages, tables, images, or records in specific sources. Strong provenance means more than attaching a plausible citation: the cited source must actually support the value claimed. Ideally, each important item should be backed by two independent primary sources. Weaker forms of justification — for example, one primary source, a regulator database, or a clearly marked secondary compilation — are still preferable to unsupported values, provided their evidential status is explicit. Satellite imagery and visual inspection can also provide evidence for industrial assets, but they are costly, hard to scale, and mainly confirm the presence of existing installations rather than full project histories.

4. *Temporality* is not metadata added after the fact; it is part of the statistical fact itself. Energy infrastructure changes over time: projects are announced, financed, permitted, built, commissioned, repowered, mothballed, retired, cancelled, or renamed. Every value should therefore carry a best-effort “as-of” date or validity period, and notable status changes should be flagged. A statistical dataset should distinguish clearly current status from past reports, planned capacity from operating capacity, and source publication date from the date of the underlying fact. While a single inventory dataset may not require reconstructing full historical trajectories, energy modeling and scenario projections do require a the database with a strong historical dimension.

The task is not simply to generate a plausible inventory-shaped answer. The statistical object is a dated, sourced, internally reconciled set of claims about energy-system assets and events. Accuracy determines whether the claims are correct; coherence determines whether they can coexist; provenance determines whether they are auditable; and temporality determines what period of the world they describe.

## Third, from chatbots to knowledge management

The recent history of the artificial intelligence industry showcases different breakthroughs meant to overcome limits that precluded early LLM from clearing the quality bar.

1. The *articulation* limit, that is the gap between what an analyst means to ask and what the model answers to. It is narrowed by multi-turn exchange and by prompt engineering. Good articulation improves all dimensions of answer quality. The framing echoes Mitroff and Featheringham's Type-III error (solving the wrong problem); to our knowledge, its explicit translation to the LLM-prompt setting is not formalised in the literature.
2. The *coverage* limit, since models are trained with a large but finite dataset. Prompt augmentation pushes the limit by providing additional information in the prompt. Without it, responses about facts post-dating a model's training cutoff can be obtained but not be believed. Retrieval-augmented generation (RAG) feeds the model relevant passages from a closed pool of documents, or they can be found by web search.
3. *Reasoning* alleviates the *coherence* limits that may stem from poor synthesis across sources. Models are trained to produce a chain of thought before generating the answer.
4. *Tool use* —.
5. *Retroactivity* —.
6. *Agency* —.

Looking the historical offer of the major AI industry players, we found that they first provided interactive chatbots, then added prompt augmentation by RAG. Web access and reasoning arrived in parallel afterwards, both converging at deep research: the capacity to produce long, organized reports from information gathered on demand from the internet.

## Fourth, the commercially available frontier: State-of-the-art general-purpose AI systems still fall short

How well do the state of the art tools perform when it comes to producing research-quality statistical datasets? We conduct an experiment with three state-of-the-art cloud AI agents. The experiment proceeds as follows. First, select agents with extended reasoning and web access. Second, we give each model our complete prompt and the quality criteria above, and ask it to tune the prompt and settings to produce the best statistical report it can within a budget cap of ten dollars and an overnight wall-clock budget. Each model returns its own tuned prompt. Third, we run the fully specified prompt three times for each model, with different providers. Fourth, we ask the other two different models to analyze and compare the three results in terms of absolute quality, and to compare the table against the naive one-shot experiment. We conjecture that the method always improves on all four dimensions, but fall short on scientifically acceptable quality. We did not find published evaluations of frontier deep-research agents against accuracy, coherence, provenance and temporality jointly on a structured-output task; the experiment described here is designed to fill that gap.

## Fifth, a tailored solution can work

The heroic single prompt to a frontier agent approach leaves a lot on the table. While agents are impressive generalists, it is generally acknowledged in agentic systems design that algorithmic behavior should be scripted. We implement a statistical workflow to demonstrate the feasibility of achieving acceptable scientific quality at the row level. Such a system is stateful: it maintains a knowledge base as an inventory of narrative asset histories, fully sourced. The statistical table is ony a derived artefact of the narrative asset-level inventory. The inventory is initially generated with a deep research heroic prompt. The four quality dimensions are automatically verified, annotating the narratives. The narrative is then incrementally updated, corrected, and extended with new documents. A memory of human judgements is preserved and used to guide the updates. To our knowledge, no published benchmark or system targets open-world enumeration of a national asset class with per-cell provenance at this granularity.

In future research, we aim to demonstrate that this method is model independence, runnable on local models for sovereignty and cost. Whether a well-chosen local model achieves this without the initial full deep-research stack, or whether parametric extraction already suffices, remains to be explored. 

We also aim to refine the method to ensure the per-cell provenance tracking, not just per row.  Each cell is a claim: a (source, date, confidence, conflict-resolution history) tuple. To our knowledge, the conjunction of per-cell provenance with per-cell temporal validity in LLM-augmented inventories has not been published; demonstrating it is part of the contribution we aim for. Sixth, a structural analogy. Each cell in a power-plant inventory — one plant, one attribute, one value — maps to a knowledge-graph triple: subject, predicate, object. Fusing tables from competing sources is therefore the same problem as fusing overlapping triple sets, with the same need for conflict resolution, source authority, and temporal versioning. Cases that rule-based schema-fixed systems cannot handle cleanly — assets mid-lifecycle, contested sources, multilingual records, conditional projections — are where language-model reasoning adds genuine value. This paper works with narratives structured tables; graph databases are a natural next layer.

---

## Annex A — Experiment 1: Technical specification

*[Design locked by ticket 0175 (2026-05-20). This annex describes the experiment as it will be run.]*

### Task

Identify all thermal power plants in Vietnam from parametric model knowledge alone. The target population is defined by the reference inventory `data/reference/vietnam_thermal_v1.csv`: 163 plant-level records covering coal (76) and gas/gas-oil (87), across all lifecycle statuses (operational, under construction, proposed, planned, cancelled, retired). The reference was compiled by the author from primary sources (PDP7, PDP7A, PDP8 annexes, EVN annual reports, MOIT decisions) and is version-locked for this experiment.

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

| Model | Lab | Family | Size class |
|---|---|---|---|
| claude-opus-4.6 | Anthropic | EN | frontier |
| claude-sonnet-4.6 | Anthropic | EN | frontier |
| claude-haiku-4.5 | Anthropic | EN | mid |
| gpt-5.5 | OpenAI | EN | frontier |
| gpt-oss-120b | OpenAI | EN | large |
| gpt-oss-20b | OpenAI | EN | mid |
| mistral-small-2603 | Mistral | FR | mid |
| mistral-medium-3-5 | Mistral | FR | mid |
| mistral-large-2512 | Mistral | FR | frontier |
| qwen3.6-27b | Alibaba | ZH | mid |
| qwen3.6-35b-a3b | Alibaba | ZH | mid |
| qwen3.6-flash | Alibaba | ZH | mid |
| qwen3.6-plus | Alibaba | ZH | frontier |
| qwen3-max-thinking | Alibaba | ZH | frontier |
| deepseek-v4-pro | DeepSeek | ZH | frontier |
| deepseek-v4-flash | DeepSeek | ZH | mid |

Mistral's per-tier branding (Small 4 / Medium 3.5 / Large 3) is the lab's own scheme and does not denote a generation order; we adopt their naming verbatim. All sixteen models received identical call parameters (T=0, seed=42, max_tokens=32768, no-web system instruction). The only reasoning-related signal sent was `reasoning_effort = "minimal"` for the two `gpt-oss-*` entries, declared in the registry. Per-call reasoning-token counts are not reported here: the harness stripped `usage.completion_tokens_details` from records before writing them to disk, a bug discovered post-run and fixed in PR #379 (ticket 0195). A 2026-05-21 probe with the same prompt against four of the panel models found `reasoning_tokens = 0` whenever no `reasoning_effort` was sent, including `qwen3-max-thinking` (the lab's explicit thinking variant via OpenRouter), `mistral-small-2603`, and `claude-opus-4.6`; we therefore do not characterise within-panel reasoning intensity until a post-fix rerun. For `qwen3-max-thinking`, an early minimal-effort smoke produced 5/5 refusals; the no-effort lineup recovered 5/5 usable rows after a parser fix that handles markdown section dividers inside structured-output tables. The four Wave-2 SOTA labs (Anthropic, OpenAI, Mistral, Alibaba) each contribute their journal-pinned flagship — Opus 4.6, GPT-5.5, Mistral Large 2512, Qwen 3 Max Thinking — so Experiment 2's "deep research vs parametric" claim can be tested within-model (qwen3-max via OpenRouter here, qwen3-max-2026-01-23 via DashScope in Experiment 2). Opus 4.6 is preferred over the newer 4.7 for the parametric baseline because 4.7's verbosity exceeds the `max_tokens` budget on the full Vietnam plant table. **GPT-5.5 declines this task on 3 of 5 reps**, opening with "I can't honestly produce a complete, primary-sourced inventory..." and refusing to fabricate URLs or source citations from parametric knowledge alone. We retain the declined responses as data — a model viewpoint on the request's epistemic standard, not extraction noise.

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

### Evaluation

Each run is evaluated against the reference by `src/aedist/evaluate.py` using fuzzy plant-name matching (`matching_threshold = 0.85`). Metrics recorded per run:

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

### What this experiment does and does not test

This experiment establishes the *parametric ceiling*: the best row-level quality achievable from model memory alone with a well-specified prompt and no external information. It leaves three of the four quality limits open: Coverage (facts absent from training data), Freshness (facts post-dating training cutoff), and Coherence (synthesis errors across the table). Only Articulation — the gap between intent and prompt — is partially addressed by the structured prompt. The gap between this ceiling and the quality bar defined in §2 motivates the subsequent experiments.

---

## Annex B — Related-work due diligence: methodology and disclosure

The claims of the form *"to our knowledge"* and *"we did not find"* throughout this paper rest on a structured per-paragraph related-work review conducted in May 2026. We disclose the method here so that readers and referees can calibrate the strength of those negative claims.

**Scope and standard.** This is an author's due-diligence review, not a systematic literature review. For each major paragraph of the argument we sought to anchor every empirical claim or framing to prior work, applying the standard *"defensible under peer review of one paragraph"*: a referee's likely "why didn't you cite X?" should have a prepared answer, with the alternative either cited or explicitly justified as not-cited. The deliverable was one due-diligence note per paragraph plus a cross-paragraph aggregator, kept as project working files.

**Authorship and assistance.** The per-paragraph notes were drafted by a large language model (Claude, using a structured `related-work-note` skill, single pass, 2026-05-21) under author direction. We have not yet read each primary source end-to-end; the candidate set, summaries, and "why cite / why not cite" justifications are LLM-generated and remain subject to author verification before they migrate into manuscript prose. References already cited in this paper have been spot-checked; the long tail of bibliography candidates in the working notes has not.

**Search procedure.** Candidates were assembled by agent recall — the model's parametric knowledge of the relevant literatures — plus targeted web fetches. We did not export from Web of Science, Scopus, Google Scholar, or Semantic Scholar. Every DOI, arXiv eprint, and URL referenced in the per-paragraph bibliographies was resolved at generation time via the agent's WebFetch tool, and unresolvable identifiers were dropped or replaced. Three identifiers did not resolve cleanly and are flagged for re-resolution at submission: the IMF Data Quality Assessment Framework page (403, URL is the canonical entry), one CACM Wikidata-overview DOI (verified via a DBLP fallback record), and the publisher PDF for the VLDB Ditto paper (the arXiv version was used as substitute, with publisher volume / issue / pages intentionally omitted from the entry).

**Citation budget.** Following project conventions we targeted 10–15 anchors per paragraph, with a tier mix of one field-defining anchor (often older), one recent survey, and two-to-three frontier works less than two years old. Two paragraphs deviated. The synopsis delivered eight anchors because its sub-literatures largely repeat those of the four-dimensional quality bar (§2) and of the tailored-solution paragraph (§5), so deeper coverage lives downstream. The capability-ladder paragraph (§3) was the tightest fit at the upper bound, as the brief covered six distinct sub-literatures — RAG, reasoning, deep research, agentic systems, tool use, agency — in a single paragraph.

**What this review did not do.** We did not perform a systematic database search. We did not re-read primary sources end-to-end before drafting. We did not run a preprint-to-peer-review update sweep, so a small number of arXiv entries may have a more recent venue-of-record we have not yet incorporated. We did not reproduce any cited result. The "related but not cited" justifications are LLM-judged and may miss closely-adjacent work that an expert reader would catch. The strength of every *"to our knowledge"* and *"we did not find"* claim in this paper should be read against these limits.

