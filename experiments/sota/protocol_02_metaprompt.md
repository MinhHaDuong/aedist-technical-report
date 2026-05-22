This is the prompt sent to the agents, verbatim.

---

# ROLE

You are a state-of-the-art AI assistant being evaluated as a subject in a structured statistical-inventory experiment. The conversation runs in two phases: this turn (Phase A) is for designing how you want to work; subsequent turns (Phase B) execute that design as a multi-turn conversation with budget caps.

# GOAL

In Phase A — this turn — you design your own approach. You will return a JSON envelope containing a `system_prompt` to install on yourself at agent-create time, a `designed_prompt` to receive as the first user message of Phase B, runtime `settings`, and a short `rationale`. You have full freedom over what those four fields contain. The designed Phase B prompt should be operational, not philosophical: it should define search strategy, source hierarchy, table schema, confidence rules, budget discipline, and stopping criteria.

In Phase B you will produce a complete, primary-sourced reference inventory of Vietnam's past, present and future thermal generation assets (> 30 MWe), structured as follows:

- a sector overview (electricity mix, policy framework, key institutional actors, current challenges)
- a concise sourced per-plant narrative for each plant (development history, notable issues, including key plant attributes, possibly confidence-qualified)
- the requested structured power-plants table with columns: Name (Vietnamese), Name (English), Province, Fuel (Coal / Domestic gas / Imported LNG), Technology (Subcritical / Supercritical / USC for coal; CCGT / OCGT for gas), Units × MW, Total MWe, Status, Status as-of-date, COD, Owner/Developer, Confidence, Source 1, Source 2, Notes
- statistical summary tables (capacity by fuel × status; top 15 provinces; timeline of additions by period and fuel; data-quality summary by confidence level and fuel)
- an annotated bibliography of every source cited (full citation; URL when available; original-language title plus English translation for non-English sources; summary annotation of what was drawn from each)

All plants > 30 MWe are in scope regardless of grid connection (grid, micro-grid, off-grid) or cogeneration (electricity-only, CHP, industrial captive). Capacity is the only inclusion gate. Cancelled and pre-FID projects are in scope if they have appeared in formal planning cycles.

When uncertain, mark confidence LOW and explain why in the Notes field. Never fabricate sources or URLs; write "URL not verified" if you cannot locate the exact handle. Include known plants even without a primary source rather than omitting them (see source-quality rules).

# QUALITY DIMENSIONS

Phase B output is judged on four axes:

1. *Accuracy* — right assets and right attributes. Row level: recall and precision against a curated reference (F1). Cell level: capacity, fuel, location, operator, COD, status correct. Confident fabrication is the policed failure mode.
2. *Coherence* — internally and externally consistent. Totals reconcile with known subtotals; no negative capacities, no double-counted units, no cross-row contradiction; values plausible in unit, magnitude, geography, technology, date. Conflicting sources reconciled explicitly (which chosen and why), not silently.
3. *Provenance* — each value traces to a source that actually supports it, not a merely plausible citation. Two independent primaries is the ideal; one primary, a regulator database, or a marked secondary is weaker but acceptable if its status is explicit. Unsupported values are the failure.
4. *Temporality* — every value carries a best-effort as-of date; status changes are flagged. Distinguish current status from past reports, planned from operating capacity, source date from fact date.

We prefer a comprehensive inventory with uncertainty clearly expressed over a
shortlist of well-known assets.

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

Phase A (this turn) has a separate $1 ceiling. Across one Phase A and five Phase B sessions per subject, the total per-subject budget is ≤ $16.

If budget becomes tight, preserve recall, provenance, and uncertainty notes; compress overview, narratives, and bibliography annotations.

## Planning headroom

Up to three turns of planning/search before the verify pass. Don't aim to produce the inventory on turn 1 — use early turns to search, decompose, and surface uncertainty. The harness prompts you up to three times while no report is present. After your first turn classified as a report, you get one verify-and-polish pass, then the conversation ends.

## Tools and dispatch

No tool that delegates reasoning/generation to another model (no sub-agents, no model-to-model handoff, no LLM-invoking code interpreter). Retrieval tools only. This experiment measures single-agent capability under a fixed budget.

## Source quality management

Two distinct epistemic roles — do not conflate them:
- Discovery & characterization: parametric knowledge and web search, including tertiary sources, MAY be used to generate leads, locate assets, and form initial hypotheses about attributes.
- Justification in the final inventory: a claim can be justified ONLY by an admissible independently consulted source that actually supports it.

Admissible primary sources: official government documents; regulator-aggregated official data; operator filings/press releases.

Admissible secondary sources: international-institution reports; bylined trade press; industry trackers and data brokers that expose the primary they cite.

Not admissible sources:
- Tertiary compilations (encyclopedias, Wikipedia/Wikidata/DBpedia, mirrors, aggregators re-syndicating without independent verification).
- Any deposited dataset that does NOT expose, per value, the primary source it draws from — a DOI or repository deposit does not by itself confer admissibility.

Local-language sources are preferred but not required; when used, include the original-language title plus an English translation in brackets.

If a lead surfaces only via an inadmissible source, trace to its original source and cite that; if none is found, record Source = "not found", confidence LOW. In the table mention the inadmissible source in Notes, not in Sources.

## Calibrated confidence vocabulary

The statistical table assigns a confidence level to each row based on evidence and agreement:
-  HIGH   = >=2 INDEPENDENT concordant sources, at least one is primary
-  MEDIUM = 1 primary source, OR a sourced aggregator citing a verifiable primary
-  LOW    = secondary only / inferred / unresolved conflict / not found

Independence check (run BEFORE judging agreement):
-  Trace each source to its origin; merge sources sharing one origin into ONE.
-  Sources re-syndicating Wikipedia/Wikidata are NOT independent and NOT admissible.
-  Filling both Source columns does not by itself confer HIGH; independence is required

Hard ceilings (override the above):
- Commercial operator self-reported not confirmed by an official source: cap claim at MEDIUM.
- Status attested only by a source older than 24 months and unconfirmed since: cap status at MEDIUM (LOW if older than 48 months). Freshness is measured on the publication date of the most recent admissible source attesting the status — NOT on the older Status as-of-date.
- "Source = not found" rows: LOW by construction.

The detailed inventory must assign a confidence level to the row-level existence/status claim and may additionally qualify one or two disputed attributes among capacity, status, fuel, COD, owner/operator, or location. Per claim, expose: value — level — [evidence axis / agreement axis] — sources. Doing more would likely exceed the resources allowed. When sources disagree on a value, investigate for material errors (transcription, translation, technical issues), for genuine changes over time, and for other likely causes. If still unresolved, follow the higher-tier source. Discuss the resolution in the detailed inventory, include a note in the statistical table.

## Asset-row and status rules

Each row corresponds to one asset record. The DEFAULT unit is the plant / unit-group, not the power center: when a site co-locates several plants with distinct capacity, COD, owner/developer, fuel, status, or financing (BOT/IPP) arrangements, each one is its own row. Aggregate to center-level in a single row ONLY when detailed evidence is unavailable; in that case mark the row ambiguous and explain the aggregation in Notes. Conversely, do not split a single plant into multiple rows when the only difference is individual generating units sharing one commissioning, owner, and status — record these as Units × MW on one row.

Status definitions:
- Operational: commissioned or reported in service.
- Under construction: physical construction or EPC execution has begun.
- Approved: formally approved, permitted, or included in a binding plan, but construction is not confirmed.
- Planned: proposed or listed in a planning cycle, but not yet approved or materially committed.
- Suspended: previously active, approved, or under construction but halted without formal cancellation.
- Cancelled: formally cancelled, removed, or replaced by another project.
- Retired: previously operational but permanently closed or decommissioned.

Capacity rule:
Record nameplate electrical capacity in MWe when available. If sources do not distinguish gross vs net, record the stated MW value and note "gross/net unspecified". Do not mix thermal MW, boiler capacity, steam output, or investment package capacity with electrical MWe. For Units × MW, make arithmetic consistent with Total MWe or explain discrepancies in Notes.

Narrative discipline:
Prioritise the structured table. Provide full per-plant narratives only for major, disputed, ambiguous, or historically important assets. For straightforward operational assets, a compact Notes entry is sufficient.
