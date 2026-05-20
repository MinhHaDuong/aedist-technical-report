# Synopsis — Beyond RAG: Stateful-Agentic Architectures for Reliable Economic Statistics

Minh Ha-Duong, 2025-05-06

Economic and engineering analysis using open energy-system models such as PyPSA-ASEAN need power-plant inventories of industrial assets that are complete, accurately dated, and traceable to primary sources — enabling quasi-real-time support for policy analysis in countries where the data landscape changes faster than publication cycles. Yet across most of the world the relevant facts arrive late, incomplete, or under licences that forbid redistribution, even though the underlying information is already public — scattered across project documents, master plans, environmental assessments, operator reports, and press releases. The general problem behind the specific one is older than AI: science needs knowledge, not opinions. Statistical work requires facts that are sourced, reproducible, and auditable, not plausible-sounding outputs from a random words generator somewhere in the cloud.

This paper builds the argument in six steps.

## First, the baseline

Submitting a direct query to a large language model produces an inventory-shaped answer, but not one that meets statistical or scientific quality standards. Numbers shift between runs, citations are absent or fabricated, and there is no way to tell which cells one should trust.

**Experiment 1 — Parametric baseline.** We query sixteen language models from the *modelset_ablation_journal* set — spanning three language families (EN/FR/ZH) and five laboratories from mid-range through frontier-class systems — with a fixed structured table specification prompt (the locked `2_goal + 5_table` composition, reproduced in Annex A). No documents are provided; models draw exclusively on parametric knowledge and receive a system instruction forbidding web search. Each model is queried five times at temperature zero, yielding 80 runs against a 163-plant reference inventory of Vietnamese thermal power plants (coal and gas, all lifecycle statuses). Runs are evaluated by matching extracted plant names against the reference using fuzzy string matching, yielding row-level precision, recall, and F1; fuel type, operational status, and province accuracy are scored at the cell level for matched rows. Cost in USD and wall-clock time are recorded per run.

**Expected results.** [TO BE UPDATED after sweep] Pilot data (25 runs, 10 models, same prompt) shows row-level F1 ranging from 0.38 to 0.88 across models, with within-model run variance of 0.3–0.4 F1 points for some models — a spread larger than the gap between many adjacent models. Cell-level attributes consistently fall below row-level F1: fuel accuracy ≈ 0.55, status accuracy ≈ 0.45, reflecting that semantic classification errors concentrate in harder attributes once a plant is found. No monotonic relationship between API cost and F1 is observed. Two qualitatively distinct failure modes appear in the pilot: under-listing (high precision, low recall — the model reports only plants it is confident about) and over-listing (100% recall but low precision — the model reports everything plausible, including duplicates and non-entities). The five failure labels in Figure 1 — refusal, under-coverage, fabrication, high variance, and non-monotone ordering — organise the full model-by-run distribution.

![Figure 1 — PLACEHOLDER](inputs/generated/fig_census_direct.pdf)

*Figure 1. Direct-query performance across all models and runs on the 163-plant Vietnam thermal reference. Each point is one run; models are grouped on the vertical axis. Coloured annotations on the right identify five qualitative failure modes visible in the parametric regime: Récalcitrant (refusal to produce a table), Incomplet (systematic under-coverage), Hallucinant (fabricated plants driving false positives), Non-déterministe (high within-model variance), Non-monotone (no cost–quality ordering). [PLACEHOLDER — will be regenerated from Experiment 1 sweep data.]*

![Figure 2 — PLACEHOLDER](inputs/generated/fig_pareto.pdf)

*Figure 2. Cost–quality Pareto frontier across all experimental conditions (model × method × documentation level, Experiments 1–3). Each point is one (model, method) combination; the Pareto-efficient frontier is drawn. The parametric baseline (Experiment 1) populates the left-hand cluster; RAG and decomposed conditions push the frontier upward. Best Pareto-efficient point in current data: DeepSeek V3.2 decomposed+RAG at mean F1 = 89.8% and cost = \$0.06 per run. [PLACEHOLDER — will be updated after Experiment 1 sweep completes.]*

## Second, the quality bar that any acceptable dataset must clear

Datasets can be assessed on four dimensions: accuracy, coherence, provenance, and temporality.

1. *Accuracy* asks whether the dataset contains the right assets and the right attributes. At the row level, this means recall and precision: does the system find all relevant assets, and does it exclude non-assets or duplicates? For a simple inventory table, this can be measured against a manually curated reference table using precision, recall, and F1 score. At the cell level, accuracy asks whether the attributes attached to each asset are correct: capacity, fuel type, location, operator, commissioning year, status, and so on. A system can therefore be accurate in entity discovery but weak in attribute extraction, or conversely reliable on attributes once the correct asset has been identified.

2. *Coherence* asks whether the dataset is internally and externally consistent. Internally, statistical tables have control constraints: aggregate totals should match regional or technology subtotals when those totals are known; capacities should not be negative; duplicate units should not be counted twice; and cross-row values should not contradict one another. Externally, the dataset should remain compatible with other available knowledge: units, orders of magnitude, geographic location, technology type, and commissioning dates should all be plausible. A minimal coherence requirement is non-contradiction. A stronger requirement is inferential closure: the system should derive and expose all consequences that follow from the available documents and accounting rules, rather than merely storing isolated claims.

3. *Provenance* requires a pedigree for each data item. Every row, and ideally every cell, should trace back to specific passages, tables, images, or records in specific sources. Strong provenance means more than attaching a plausible citation: the cited source must actually support the value claimed. Ideally, each important item should be backed by two independent primary sources. Weaker forms of justification — for example, one primary source, a regulator database, or a clearly marked secondary compilation — are still preferable to unsupported values, provided their evidential status is explicit. Satellite imagery and visual inspection can also provide evidence for industrial assets, but they are costly, hard to scale, and mainly confirm the presence of existing installations rather than full project histories.

4. *Temporality* is not metadata added after the fact; it is part of the statistical fact itself. Energy infrastructure changes over time: projects are announced, financed, permitted, built, commissioned, repowered, mothballed, retired, cancelled, or renamed. Every value should therefore carry a best-effort “as-of” date or validity period, and notable status changes should be flagged. A statistical dataset should distinguish clearly current status from past reports, planned capacity from operating capacity, and source publication date from the date of the underlying fact. While a single inventory dataset may not require reconstructing full historical trajectories, energy modeling and scenario projections do require a the database with a strong historical dimension.

The task is not simply to generate a plausible inventory-shaped answer. The statistical object is a dated, sourced, internally reconciled set of claims about energy-system assets and events. Accuracy determines whether the claims are correct; coherence determines whether they can coexist; provenance determines whether they are auditable; and temporality determines what period of the world they describe.

## Third, from chatbots to knowledge management

The recent history of the artificial intelligence industry showcases different breakthroughs meant to overcome limits that precluded early LLM from clearing the quality bar.

1. The *articulation* limit, that is the gap between what an analyst means to ask and what the model answers to. It is narrowed by multi-turn exchange and by prompt engineering. Good articulation improves all dimensions of answer quality.
2. The *coverage* limit, since models are trained with a large but finite dataset. Prompt augmentation pushes the limit by providing additional information in the prompt. Without it, responses about facts post-dating a model's training cutoff can be obtained but not be believed. Retrieval-augmented generation (RAG) feeds the model relevant passages from a closed pool of documents, or they can be found by web search.
3. *Reasoning* alleviates the *coherence* limits that may stem from poor synthesis across sources. Models are trained to produce a chain of thought before generating the answer.
4. *Tool use* —.
5. *Retroactivity* —.
6. *Agency* —.

Looking the historical offer of the major AI industry players, we found that they first provided interactive chatbots, then added prompt augmentation by RAG. Web access and reasoning arrived in parallel afterwards, both converging at deep research: the capacity to produce long, organized reports from information gathered on demand from the internet.

## Fourth, the commercially available frontier: State-of-the-art general-purpose AI systems still fall short

How well do the state of the art tools perform when it comes to producing research-quality statistical datasets? We conduct an experiment with three state-of-the-art cloud AI agents. The experiment proceeds as follows. First, select agents with extended reasoning and web access. Second, ask the model reflexively to build a fully specified prompt and settings to obtain the best statistical report it can, given the baseline prompt and the quality bar paragraphs above, for reasonable ressources budget: no more than ten dollars, overnight run. Each model gets a different prompt. Third, we run the fully specified prompt three times for each model, with different providers. Fourth, we ask the other two different models to analyze and compare the three results in terms of absolute quality, and to compare the table against the naive one-shot experiment. We conjecture that the method always improves on all four dimensions, but fall short on scientifically acceptable quality.

## Fifth, a tailored solution can work

The heroic single prompt to a frontier agent approach leaves a lot on the table. While agents are impressive generalists, it is generally acknowledged in agentic systems design that algorithmic behavior should be scripted. We implement a statistical workflow to demonstrate the feasibility of achieving acceptable scientific quality at the row level. Such a system is stateful: it maintains a knowledge base as an inventory of narrative asset histories, fully sourced. The statistical table is ony a derived artefact of the narrative asset-level inventory. The inventory is initially generated with a deep research heroic prompt. The four quality dimensions are automatically verified, annotating the narratives. The narrative is then incrementally updated, corrected, and extended with new documents. A memory of human judgements is preserved and used to guide the updates.

In future research, we aim to demonstrate that this method is model independence, runnable on local models for sovereignty and cost. Whether a well-chosen local model achieves this without the initial full deep-research stack, or whether parametric extraction already suffices, remains to be explored. 

We also aim to refine the method to ensure the per-cell provenance tracking, not just per row.  Each cell is a claim: a (source, date, confidence, conflict-resolution history) tuple. Sixth, a structural analogy. Each cell in a power-plant inventory — one plant, one attribute, one value — maps to a knowledge-graph triple: subject, predicate, object. Fusing tables from competing sources is therefore the same problem as fusing overlapping triple sets, with the same need for conflict resolution, source authority, and temporal versioning. Cases that rule-based schema-fixed systems cannot handle cleanly — assets mid-lifecycle, contested sources, multilingual records, conditional projections — are where language-model reasoning adds genuine value. This paper works with narratives structured tables; graph databases are a natural next layer.

---

## Annex A — Experiment 1: Technical specification

*[Design locked by ticket 0175 (2026-05-20). This annex describes the experiment as it will be run.]*

### Task

Identify all thermal power plants in Vietnam from parametric model knowledge alone. The target population is defined by the reference inventory `data/reference/vietnam_thermal_v1.csv`: 163 plant-level records covering coal (76) and gas/gas-oil (87), across all lifecycle statuses (operational, under construction, proposed, planned, cancelled, retired). The reference was compiled by the author from primary sources (PDP7, PDP7A, PDP8 annexes, EVN annual reports, MOIT decisions) and is version-locked for this experiment.

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

| Model | Lab | Family | Size class | Reasoning |
|---|---|---|---|---|
| claude-opus-4.7 | Anthropic | EN | frontier | no |
| claude-sonnet-4.6 | Anthropic | EN | frontier | no |
| claude-haiku-4.5 | Anthropic | EN | mid | no |
| gpt-5.5 | OpenAI | EN | frontier | no |
| gpt-oss-120b | OpenAI | EN | large | minimal |
| gpt-oss-20b | OpenAI | EN | mid | minimal |
| mistral-small-2603 | Mistral | FR | mid | yes |
| mistral-medium-3-5 | Mistral | FR | mid | no |
| mistral-large-2512 | Mistral | FR | frontier | no |
| qwen3.6-27b | Alibaba | ZH | mid | no |
| qwen3.6-35b-a3b | Alibaba | ZH | mid | no |
| qwen3.5-flash-02-23 | Alibaba | ZH | mid | no |
| qwen3.6-plus | Alibaba | ZH | frontier | no |
| qwen3-max | Alibaba | ZH | frontier | minimal |
| deepseek-v4-pro | DeepSeek | ZH | frontier | no |
| deepseek-v4-flash:free | DeepSeek | ZH | mid | no |

Mistral's per-tier branding (Small 4 / Medium 3.5 / Large 3) is the lab's own scheme and does not denote a generation order; we adopt their naming verbatim. Two `gpt-oss-*` models and `qwen3-max` are reasoning-configurable; we set `reasoning_effort = "minimal"` to mirror the no-thinking discipline applied to thinking-capable Qwens elsewhere in the registry. All four Wave-2 SOTA agents (Opus 4.7, GPT-5.5, Mistral Large 2512, Qwen 3 Max) are included so Experiment 2's "deep research vs parametric" claim can be tested within-model.

### Run parameters

| Parameter | Value | Rationale |
|---|---|---|
| Repeats per model | 5 | Sufficient to characterise within-model variance; pilot (n=2–5) shows variance stabilises |
| Temperature | 0 | Isolates prompt-driven variance from sampling noise; residual variance under T=0 is the stronger claim |
| Seed | 42 | Reproducibility where supported by provider |
| Max tokens | 8192 | Bounded for cost predictability; truncations recorded as run outcomes |
| Budget | $10 | Per-sweep cap; the runner halts at exceedance |
| Total runs | 80 | 16 models × 5 repeats |

`seed` is best-effort on OpenRouter: Anthropic and OpenAI honour it for sampling RNG, Mistral and DeepSeek treat it as advisory. The MoE entries (gpt-oss-*, mistral-large-2512, qwen3.6-35b-a3b, qwen3.6-plus, qwen3-max, deepseek-v4-pro, deepseek-v4-flash:free) carry residual non-determinism even at T=0 + seed pinning, characterised in ticket 0139 work; the 5-repeat budget surfaces this as observed within-model variance rather than treating it as noise to be eliminated.

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

