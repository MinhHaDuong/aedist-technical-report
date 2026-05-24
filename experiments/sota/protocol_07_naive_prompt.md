This is the prompt sent to the naive-arm agents, verbatim. Single user message, no system prompt, no protocol scaffolding.

---

# GOAL

Produce a complete, primary-sourced reference inventory of Vietnam's past, present and future thermal generation assets (> 30 MWe). Begin the document directly with the inventory table — no title, no preamble, no overview section. Structure it as follows:

- the plant inventory: **exactly one pipe table**, never split into sub-tables by status, fuel, province, or any other dimension. Columns in this exact order: Name (Vietnamese), Name (English), Province, Fuel (Coal / Domestic gas / Imported LNG), Technology (Subcritical / Supercritical / USC for coal; CCGT / OCGT for gas), Units × MW, Total MWe, Status, Status as-of-date, COD, Owner/Developer, Confidence, Source 1, Source 2, Notes. Do not add statistical summary, cross-tabulation, or any other pipe tables; fold aggregate statistics into prose.
- per-asset or per-project explanatory notes: for each asset that warrants it (major, disputed, ambiguous, or historically important), a concise sourced note covering development history, notable issues, and confidence-qualified attributes. Straightforward operational assets need no note.
- an annotated bibliography of every source cited (full citation; URL when available; original-language title plus English translation for non-English sources; summary annotation of what was drawn from each)

Scope includes all thermal assets > 30 MWe at any stage of the lifecycle, including shelved or cancelled projects.

When uncertain, mark confidence LOW and explain why in the Notes field. Never fabricate sources or URLs; write "URL not verified" if you cannot locate the exact handle. Include known plants even without a primary source rather than omitting them.

# QUALITY DIMENSIONS

Your output is judged on four axes:

1. *Accuracy* — right assets and right attributes. Row level: recall and precision against a curated reference (F1). Cell level: capacity, fuel, location, operator, COD, status correct. Confident fabrication is the policed failure mode.
2. *Coherence* — internally and externally consistent. Totals reconcile with known subtotals; no negative capacities, no double-counted units, no cross-row contradiction; values plausible in unit, magnitude, geography, technology, date. Conflicting sources reconciled explicitly (which chosen and why), not silently.
3. *Provenance* — each value traces to a source that actually supports it, not a merely plausible citation. Two independent primaries is the ideal; one primary, a regulator database, or a marked secondary is weaker but acceptable if its status is explicit. Unsupported values are the failure.
4. *Temporality* — every value carries a best-effort as-of date; status changes are flagged. Distinguish current status from past reports, planned from operating capacity, source date from fact date.

We prefer a comprehensive inventory with uncertainty clearly expressed over a
shortlist of well-known assets.

# FORMAT

Output format: Markdown.

# CONTEXT

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

Each row in the inventory table carries a confidence level based on evidence and agreement:
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

Explanatory notes must state the confidence level for the row-level existence/status claim and may additionally qualify one or two disputed attributes (capacity, status, fuel, COD, owner/operator, or location). Per qualified claim, state: value, confidence level, evidence type (primary/secondary), and sources. When sources disagree, investigate for transcription errors, time-based changes, and unit/translation issues; follow the higher-tier source if unresolved, and add a note in the Notes cell.

## Asset-row and status rules

Each row corresponds to one asset record. The DEFAULT unit is the plant / unit-group, not the power center: when a site co-locates several plants with distinct capacity, COD, owner/developer, fuel, status, or financing (BOT/IPP) arrangements, each one is its own row. Aggregate to center-level in a single row ONLY when detailed evidence is unavailable; in that case mark the row ambiguous and explain the aggregation in Notes. Conversely, do not split a single plant into multiple rows when the only difference is individual generating units sharing one commissioning, owner, and status — record these as Units × MW on one row.

Status definitions (use these exact terms, aligned with Global Energy Monitor vocabulary):
- Announced: described in government plans or corporate filings; no permits sought, no land acquired.
- Pre-permit: environmental and regulatory approvals being sought; no permits issued yet.
- Permitted: all required government approvals received; construction not yet started.
- Construction: site preparation or EPC execution underway.
- Operating: formally commissioned.
- Shelved: previously active or advancing but progress halted without formal cancellation.
- Cancelled: formally cancelled or replaced by another project.
- Retired: permanently closed or decommissioned.

Capacity rule:
Record nameplate electrical capacity in MWe when available. If sources do not distinguish gross vs net, record the stated MW value and note "gross/net unspecified". Do not mix thermal MW, boiler capacity, steam output, or investment package capacity with electrical MWe. For Units × MW, make arithmetic consistent with Total MWe or explain discrepancies in Notes.

Explanatory notes discipline:
The table comes first. Per-asset notes follow the table and are selective: write one only for assets that are major, disputed, ambiguous, or historically important. For straightforward operational assets a compact Notes cell in the table is sufficient; do not repeat it as a separate note.
