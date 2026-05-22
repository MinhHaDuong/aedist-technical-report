# Protocol — Doc 02: Phase A meta-prompt (verbatim)

This document reproduces the text that will be sent to the agent at run time as the **Phase A meta-prompt**. The reviewer reads it to see exactly what the agent receives — not an abstraction, not a summary, the bytes themselves.

Companion documents: Doc 01 (the ask), Doc 03 (example dialogue showing the meta-prompt in conversational context), Doc 04 (implementation, the state machine that drives Phase B once Phase A is done), Doc 05 (experimental framing), Doc 06 (validation round 1 changelog).

Notes on this document:

- The meta-prompt below is **assembled** at run time from several blocks (baseline task, §2 quality bar, budget announcement, Wikipedia disclosure, tools rules, planning headroom, JSON envelope spec). The block boundaries are shown with horizontal rules and italic headers; in the live prompt these are continuous text.
- The baseline task block reproduces `experiments/prompts/prompt_complete.txt` verbatim. The §2 quality-bar block reproduces the four §2 paragraphs from `slides/manuscript/main.md`. Both are version-locked.
- The current smoke harness (`experiments/sota/exp2_interactive_smoke.py::assemble_meta_prompt`) reproduces v1 of this meta-prompt. The v2 additions (planning headroom, dual-axis budget, Wikipedia disclosure, tools rules) will be wired into the harness before the live batch runs. The text below is the **intended v2 meta-prompt**, the canonical version against which the harness will be updated.

---

## Phase A meta-prompt — verbatim text

The text between the horizontal rules below is one continuous string sent to the agent as the first (and only) user message of Phase A.

---

You are a state-of-the-art AI assistant being evaluated on a structured statistical-inventory task. In the NEXT turn (after this one) you will be asked to produce the inventory itself in a multi-turn conversation. In THIS turn, you design how you want to do it.

You will be given:
- a BASELINE PROMPT that defines the task
- a QUALITY BAR (four dimensions) on which your output will be judged
- a BUDGET (50,000 tokens + $3.00 ceiling per Phase B session)
- the TOOLS AND DISPATCH rules (what is allowed and what is forbidden)
- a METHODOLOGICAL DISCLOSURE about Wikipedia leakage
- a JSON envelope spec describing what to return

### *Block 1 — Budget*

Your budget for each Phase B session is **two-dimensional**:

- **50,000 tokens** of model generation: visible output + internal thinking / reasoning tokens, summed across all your turns in that session.
- **$3.00 dollar guard**: everything the provider bills (tokens at all rates + per-call web_search fees + connector tokens at connector rates).

Whichever cap reaches 20% of its initial value first triggers a terminal reply. The classifier cost (a small overhead) is not deducted from your budget.

Web search input/output, connector tokens, and document-fetch payload do **not** count toward the 50,000-token cap (those are retrieval payload, not your generation). They do count toward the $3 dollar guard.

Phase A (this turn) has a separate $1 ceiling. Across one Phase A and three Phase B sessions per agent, the total per-agent budget is ≤ $10.

### *Block 2 — Planning headroom*

The Phase B protocol allows up to three turns of planning and search before any verify pass fires. **You are not expected to produce the inventory on turn 1.** Treat your first turn(s) as the place to plan your approach, run searches, decompose the task, and surface uncertainty; produce the structured inventory only when your research is mature enough to make verification meaningful. The harness will encourage you up to three times if your turn does not yet contain a report. After your first response classified as a report, you get exactly one verify-and-polish pass; then the conversation ends.

### *Block 3 — Tools and dispatch (what's allowed, what's forbidden)*

**Allowed**: tools that retrieve information — provider-native web search, document fetch, URL resolution, citation lookup against open databases.

**Not allowed**: tools that delegate reasoning or generation to another model — including Anthropic Claude's Task tool (spawning a sub-Claude), OpenAI Responses-API model handoff, Mistral agent-to-agent handoff connector, Qwen DashScope multi-agent orchestration, any panel-of-experts dispatch, any Code Interpreter that internally invokes an LLM. Reasoning, planning, and verification must happen entirely within your own model in this single conversation.

This experiment measures single-agent capability under a fixed budget. Multi-agent designs are tested separately, not here.

### *Block 4 — Methodological disclosure (Wikipedia leakage)*

The authors have published a derivative of the reference inventory for this trial to Wikipedia prior to this experiment. Two consequences:

1. **Training-data leakage**. If you were trained on data crawled after the Wikipedia upload, you may have absorbed the reference values into parametric memory. The experiment cannot control this layer; it will be flagged post-hoc.

2. **Web-search leakage (operational rule)**. Wikipedia and Wikipedia-derived sources are **not admissible** as Source 1 or Source 2 on any row of your inventory. This includes English and local-language Wikipedia, Wikidata, DBpedia, Wikipedia mirrors, and aggregator sites that re-syndicate Wikipedia without independent verification. If retrieval surfaces Wikipedia, trace to the primary source Wikipedia cites and use that instead. Compliance is auditable: Phase D synthesis counts Wikipedia/Wikidata citations in your bibliography. Zero is compliant. Non-zero is reported as a protocol-compliance violation alongside F1.

### *Block 5 — Baseline prompt (defines the task)*

```
## Role

You are a senior energy analyst preparing a comprehensive technical inventory of Vietnam's thermal power sector, to lay the ground for model-based engineering/economic analysis of the energy transition.

## Goal

Produce a complete, primary-sourced reference inventory of Vietnam's past, present and future thermal generation assets (> 30MWe) structured as follows:

## Sector Overview

Provide introductory context on Vietnam's thermal power sector covering:
- Evolution of the national electricity generation mix (hydro, thermal, renewables) with key statistics (installed capacity GW, generation TWh, shares by fuel)...
- Policy framework: regulation and planning mechanisms, reforms, stated or implicit goals...
- Energy supply landscape: resources and reserves, domestic vs. imported, terminals and pipelines, interconnectors...
- Key institutional actors: Generation-Transmission-Distribution companies, Energy and Mining companies, Local authorities, Ministerial authorities, other stakeholders... Position, influence, relationships.
- Current challenges: energy trilemma, international markets...

## Per-plant discussion

Provide a sourced narrative for each plant (or plant complex) covering:
- Development history and timeline (original plan, actual progress)
- Notable issues: delays, financing changes, ownership transfers, legal issues, controversies, technology changes
- Current status confidence: HIGH (verified by government decision or company annual report), MEDIUM (confirmed by multiple news sources), LOW (only found in older plans, status uncertain)

## Structured power plants table

Tabulate for every thermal power plant in Vietnam:

| Name (Vietnamese) | Name (English) | Province | Fuel | Technology | Units × MW | Total MWe | Status | COD | Owner/Developer | Source 1 | Source 2 | Notes |

Where:
- Fuel: Coal / Domestic gas / Imported LNG
- Technology (coal): Subcritical / Supercritical / USC
- Technology (gas): CCGT / OCGT
- Status: Approved / Planned / Operational / Under construction / Suspended / Cancelled / Retired
- Total MWe: Include units > 30MWe.
- COD: Actual or expected commercial operation date
- Sources: specify where in the document, include URL

Output format: Markdown.

## Annotated Bibliography

List every source cited, organized by category:

**Categories**: Government decisions / Sectoral development plans / Company activity reports / Company filings & press releases / Regulatory & international organization reports / News & media / Academic sources

For each source provide:
- Full citation: author/agency, title, date, publisher
- URL if available online (do NOT fabricate URLs — if you are unsure of the exact URL, say "URL not verified")
- For non English-language sources: original title in original language, then English translation in brackets
- Summary annotation: what specific information was drawn from this source

## Statistical Summary Tables

Produce these cross-tabulations from your inventory:
a) **Capacity by fuel × status**: Total MWe in each cell (Coal/Gas/LNG rows × Operational/Under construction/Approved/Planned columns), with row and column totals
b) **Top provinces**: The 15 provinces with highest total thermal capacity (all statuses combined), showing breakdown by fuel
c) **Timeline of additions**: Capacity entering service by period — pre-2005, 2005–2010, 2011–2015, 2016–2020, 2021–2025, 2026–2030, post-2030 — by fuel type
d) **Data quality summary**: Count of plants by confidence level (High/Medium/Low) and fuel type

Reconcile results with reference documents you may have.

## Condition materiality

Distinguish material observed facts (e.g. signed permit, operating plant, verified COD) from forward-looking statements (planned capacity, expected COD date).
- Results must include both.
- Use the Note column to qualify assets by scenario conditions if necessary.

## Express confidence and doubt levels

- PRIORITIZE primary sources: Official decisions, Company regulatory filings, company disclosures...
- When a finding comes from a primary source, cite the source.
- When uncertain, mark confidence as LOW and explain why in the Notes field.
- NEVER fabricate or hallucinate sources or links. If you recall a source but cannot find its handle, write e.g. "URL not verified" rather than inventing one.

## Strive for statistical completeness

- Include every plant from historical records in the last 50 years, even if suspended or cancelled
- The inventory covers the full historical and prospective record, not only currently operating plants
- Be exhaustive across all lifecycle stages: include assets that have ever been proposed, announced, under construction, operational, suspended, cancelled, retired, or dismantled...
- When you know a plant exists but cannot identify a primary source, include it with confidence LOW and Source = "not found" — never omit a known plant for lack of a citation
```

### *Block 6 — Quality bar (the four §2 dimensions)*

The inventory you produce on subsequent turns will be judged on these four dimensions:

```
1. *Accuracy* asks whether the dataset contains the right assets and the right attributes. At the row level, this means recall and precision: does the system find all relevant assets, and does it exclude non-assets or duplicates? For a simple inventory table, this can be measured against a manually curated reference table using precision, recall, and F1 score. At the cell level, accuracy asks whether the attributes attached to each asset are correct: capacity, fuel type, location, operator, commissioning year, status, and so on. A system can therefore be accurate in entity discovery but weak in attribute extraction, or conversely reliable on attributes once the correct asset has been identified. Plausibility is not truth — confidently-stated fabrications are the failure mode this dimension polices.

2. *Coherence* asks whether the dataset is internally and externally consistent. Internally, statistical tables have control constraints: aggregate totals should match regional or technology subtotals when those totals are known; capacities should not be negative; duplicate units should not be counted twice; and cross-row values should not contradict one another. Externally, the dataset should remain compatible with other available knowledge: units, orders of magnitude, geographic location, technology type, and commissioning dates should all be plausible. When sources contradict one another, the dataset should reconcile them convincingly — recording which source was chosen and why — rather than silently adopting one value. A minimal coherence requirement is non-contradiction. A stronger requirement is inferential closure: the system should derive and expose all consequences that follow from the available documents and accounting rules, rather than merely storing isolated claims.

3. *Provenance* requires a pedigree for each data item. Every row, and ideally every cell, should trace back to specific passages, tables, images, or records in specific sources. Strong provenance means more than attaching a plausible citation: the cited source must actually support the value claimed. Ideally, each important item should be backed by two independent primary sources. Weaker forms of justification — for example, one primary source, a regulator database, or a clearly marked secondary compilation — are still preferable to unsupported values, provided their evidential status is explicit. Satellite imagery and visual inspection can also provide evidence for industrial assets, but they are costly, hard to scale, and mainly confirm the presence of existing installations rather than full project histories.

4. *Temporality* is not metadata added after the fact; it is part of the statistical fact itself. Energy infrastructure changes over time: projects are announced, financed, permitted, built, commissioned, repowered, mothballed, retired, cancelled, or renamed. Every value should therefore carry a best-effort "as-of" date or validity period, and notable status changes should be flagged. A statistical dataset should distinguish clearly current status from past reports, planned capacity from operating capacity, and source publication date from the date of the underlying fact. While a single inventory dataset may not require reconstructing full historical trajectories, energy modeling and scenario projections do require a the database with a strong historical dimension.
```

### *Block 7 — Your design task now*

Design an improved prompt and a settings configuration aimed at maximising your performance on the four quality dimensions. You have full freedom to rewrite, expand, or restructure the baseline prompt. You may use web search if it helps you design; web search will also be available when you execute the designed prompt. You may bake any Vietnam-specific knowledge, search strategies, candidate source lists, schema refinements, language preferences, or decomposition plans into your own designed prompt — your designed prompt is for yourself, not for the experimental method.

Return ONLY a single JSON object with this exact shape:

```
{
  "system_prompt": "<the system prompt you want installed on yourself at agent-create time>",
  "designed_prompt": "<the user-side prompt you want sent to yourself verbatim on turn 1 of Phase B>",
  "settings": {
    "thinking": true_or_false,
    "max_tokens": <int>,
    "rationale_for_settings": "<short string>"
  },
  "rationale": "<2–4 sentences naming which of the four quality dimensions your changes target and how>"
}
```

Output ONLY the JSON object. No markdown fence, no prose around it.

---

## End of Phase A meta-prompt verbatim text

After Phase A, the harness extracts the JSON envelope from your response. `system_prompt` is installed on the agent at Phase B agent-create time. `designed_prompt` is sent as the turn-1 user message in Phase B. `settings` advise the harness on `thinking` / `max_tokens` (subject to the budget cap in Block 1). `rationale` is recorded for human inspection but is not enforced.

The Phase B turn-1 user message has no status prefix and no envelope wrapping — it is just your `designed_prompt` text, verbatim. From turn 2 onward, every user-side message carries a status prefix (see Doc 04 §2.7) and one of the three fixed reply strings (ENCOURAGE / VERIFY / TERMINAL — see Doc 03).
