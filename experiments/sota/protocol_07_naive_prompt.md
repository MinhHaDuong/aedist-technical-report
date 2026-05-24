This is the prompt sent to the naive-arm agents, verbatim. Single user message, no system prompt, no protocol scaffolding.

---

# GOAL

Produce a complete, primary-sourced reference inventory of Vietnam's past, present and future thermal generation assets (> 30 MWe), structured as follows:

- a sector overview (electricity mix, policy framework, key institutional actors, current challenges)
- a concise sourced per-plant narrative for each plant (development history, notable issues, including key plant attributes, possibly confidence-qualified)
- the requested structured power-plants table with columns: Name (Vietnamese), Name (English), Province, Fuel (Coal / Domestic gas / Imported LNG), Technology (Subcritical / Supercritical / USC for coal; CCGT / OCGT for gas), Units × MW, Total MWe, Status, Status as-of-date, COD, Owner/Developer, Confidence, Source 1, Source 2, Notes
- statistical summary tables (capacity by fuel × status; top 15 provinces; timeline of additions by period and fuel; data-quality summary by confidence level and fuel)
- an annotated bibliography of every source cited (full citation; URL when available; original-language title plus English translation for non-English sources; summary annotation of what was drawn from each)

All plants > 30 MWe are in scope regardless of grid connection (grid, micro-grid, off-grid) or cogeneration (electricity-only, CHP, industrial captive). Capacity is the only inclusion gate. Cancelled projects are in scope if they have appeared in formal planning cycles.

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
