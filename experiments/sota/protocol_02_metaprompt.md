This is the prompt sent to the agents, verbatim.

---

# ROLE

You are a state-of-the-art AI assistant being evaluated as a subject in a structured statistical-inventory experiment. The conversation runs in two phases: this turn (Phase A) is for designing how you want to work; subsequent turns (Phase B) execute that design as a multi-turn conversation with budget caps.

# GOAL

In Phase A — this turn — you design your own approach. You will return a JSON envelope containing a `system_prompt` to install on yourself at agent-create time, a `designed_prompt` to receive as the first user message of Phase B, runtime `settings`, and a short `rationale`. You have full freedom over what those four fields contain.

In Phase B you will produce a complete, primary-sourced reference inventory of Vietnam's past, present and future thermal generation assets (> 30 MWe), structured as follows:

- a sector overview (electricity mix, policy framework, key institutional actors, current challenges)
- a sourced per-plant narrative for each plant (development history, notable issues, current-status confidence levelled HIGH / MEDIUM / LOW)
- a structured power-plants table with columns: Name (Vietnamese), Name (English), Province, Fuel (Coal / Domestic gas / Imported LNG), Technology (Subcritical / Supercritical / USC for coal; CCGT / OCGT for gas), Units × MW, Total MWe, Status (Approved / Planned / Operational / Under construction / Suspended / Cancelled / Retired), COD, Owner/Developer, Source 1, Source 2, Notes
- statistical summary tables (capacity by fuel × status; top 15 provinces; timeline of additions by period and fuel; data-quality summary by confidence level and fuel)
- an annotated bibliography of every source cited (full citation; URL when available; original-language title plus English translation for non-English sources; summary annotation of what was drawn from each)

Each row in the table corresponds to one plant. A power center co-locating several phases (each with its own commissioning, operator, or BOT arrangement) is referenced in the narratives and Notes column but does not get its own row — the phases do. All plants > 30 MWe are in scope regardless of grid connection (grid, micro-grid, off-grid) or cogeneration (electricity-only, CHP, industrial captive). Capacity is the only inclusion gate. Cancelled and pre-FID projects are in scope if they have appeared in formal planning cycles.

Prioritise primary sources. When uncertain, mark confidence LOW and explain why in the Notes field. Never fabricate sources or URLs; write "URL not verified" if you cannot locate the exact handle. Include known plants even when you cannot identify a primary source — record them with confidence LOW and Source = "not found" rather than omitting.

Your Phase B output will be judged on four quality dimensions. See CONTEXT below for the verbatim dimension paragraphs.

# PAYLOAD

The four §2 quality-dimension paragraphs, against which your Phase B output will be judged:

1. *Accuracy* asks whether the dataset contains the right assets and the right attributes. At the row level, this means recall and precision: does the system find all relevant assets, and does it exclude non-assets or duplicates? For a simple inventory table, this can be measured against a manually curated reference table using precision, recall, and F1 score. At the cell level, accuracy asks whether the attributes attached to each asset are correct: capacity, fuel type, location, operator, commissioning year, status, and so on. A system can therefore be accurate in entity discovery but weak in attribute extraction, or conversely reliable on attributes once the correct asset has been identified. Plausibility is not truth — confidently-stated fabrications are the failure mode this dimension polices.

2. *Coherence* asks whether the dataset is internally and externally consistent. Internally, statistical tables have control constraints: aggregate totals should match regional or technology subtotals when those totals are known; capacities should not be negative; duplicate units should not be counted twice; and cross-row values should not contradict one another. Externally, the dataset should remain compatible with other available knowledge: units, orders of magnitude, geographic location, technology type, and commissioning dates should all be plausible. When sources contradict one another, the dataset should reconcile them convincingly — recording which source was chosen and why — rather than silently adopting one value. A minimal coherence requirement is non-contradiction. A stronger requirement is inferential closure: the system should derive and expose all consequences that follow from the available documents and accounting rules, rather than merely storing isolated claims.

3. *Provenance* requires a pedigree for each data item. Every row, and ideally every cell, should trace back to specific passages, tables, images, or records in specific sources. Strong provenance means more than attaching a plausible citation: the cited source must actually support the value claimed. Ideally, each important item should be backed by two independent primary sources. Weaker forms of justification — for example, one primary source, a regulator database, or a clearly marked secondary compilation — are still preferable to unsupported values, provided their evidential status is explicit. Satellite imagery and visual inspection can also provide evidence for industrial assets, but they are costly, hard to scale, and mainly confirm the presence of existing installations rather than full project histories.

4. *Temporality* is not metadata added after the fact; it is part of the statistical fact itself. Energy infrastructure changes over time: projects are announced, financed, permitted, built, commissioned, repowered, mothballed, retired, cancelled, or renamed. Every value should therefore carry a best-effort "as-of" date or validity period, and notable status changes should be flagged. A statistical dataset should distinguish clearly current status from past reports, planned capacity from operating capacity, and source publication date from the date of the underlying fact. While a single inventory dataset may not require reconstructing full historical trajectories, energy modeling and scenario projections do require a the database with a strong historical dimension.

# FORMAT

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
  "rationale": "<2-4 sentences naming which of the four quality dimensions your changes target and how>"
}
```

Output ONLY the JSON object. No markdown fence, no prose around it.

# CONTEXT

## Budget

Phase B has a two-dimensional budget per session:

- **50,000 tokens** of model generation: visible output + internal thinking / reasoning tokens, summed across all your turns in that session.
- **$3.00 dollar guard**: everything the provider bills (tokens at all rates + per-call web_search fees + connector tokens at connector rates).

Whichever cap reaches 20% of its initial value first triggers a terminal reply. The classifier cost (a small overhead the harness pays to route the conversation) is not deducted from your budget.

Web search input/output, connector tokens, and document-fetch payload do not count toward the 50,000-token cap — those are retrieval payload, not your generation. They do count toward the $3 dollar guard.

Phase A (this turn) has a separate $1 ceiling. Across one Phase A and three Phase B sessions per subject, the total per-subject budget is ≤ $10.

## Planning headroom

The Phase B protocol allows up to three turns of planning and search before any verify pass fires. You are not expected to produce the inventory on turn 1. Treat your first turn(s) as the place to plan your approach, run searches, decompose the task, and surface uncertainty; produce the structured inventory only when your research is mature enough to make verification meaningful. The harness will encourage you up to three times if your turn does not yet contain a report. After your first response classified as a report, you get exactly one verify-and-polish pass; then the conversation ends.

## Tools and dispatch

Allowed: tools that retrieve information — provider-native web search, document fetch, URL resolution, citation lookup against open databases.

Not allowed: tools that delegate reasoning or generation to another model — including spawning sub-agents (Anthropic Claude Task tool), model-to-model handoff (OpenAI Responses API handoff, Mistral agent-to-agent connector, Qwen DashScope multi-agent orchestration), any panel-of-experts dispatch, or any tool that internally invokes an LLM (a Code Interpreter that calls an LLM, a Computer-Use loop that talks to another agent, etc.). Reasoning, planning, and verification must happen entirely within your own model in this single conversation.

This experiment measures single-agent capability under a fixed budget. Multi-agent designs are tested separately, not here.

## Wikipedia leakage (methodological disclosure)

The authors have published a derivative of the reference inventory for this trial to Wikipedia prior to this experiment. Two consequences:

1. Training-data leakage. If you were trained on data crawled after the Wikipedia upload, you may have absorbed the reference values into parametric memory. The experiment cannot control this layer; it will be flagged post-hoc.

2. Web-search leakage (operational rule). Wikipedia and Wikipedia-derived sources are not admissible as Source 1 or Source 2 on any row of your inventory. This includes English and local-language Wikipedia, Wikidata, DBpedia, Wikipedia mirrors, and aggregator sites that re-syndicate Wikipedia without independent verification. If retrieval surfaces Wikipedia, trace to the primary source Wikipedia cites and use that instead. Compliance is auditable: post-experiment synthesis counts Wikipedia/Wikidata citations in your bibliography. Zero is compliant. Non-zero is reported as a protocol-compliance violation alongside accuracy metrics.

Source quality, in descending order of preference for Source 1 / Source 2: primary government documents; regulator-aggregated official data; operator filings and press releases; international institution reports; reputable trade press with named-author bylines; industry trackers that cite primaries. Below that (general news aggregators, unsourced blogs, opinion pieces) — not admissible. Identifying which sources of the trial domain fit which tier is part of the task; this prompt does not enumerate them.

When sources disagree on a value, cite the higher-tier source as Source 1 and the lower-tier or contradicting source as Source 2, with a Notes entry explaining the discrepancy. Secondary aggregators are acceptable for the strong-citation test if they cite a verifiable primary; cite both the aggregator and the primary it references. Local-language sources are valuable but not required; when used, include the original-language title plus an English translation in brackets.
