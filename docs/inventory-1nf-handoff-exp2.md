# Handoff — non-atomicity (1NF) of Exp2 inventory rows

Findings on the sub-problem of non-1NF rows in Exp2 model outputs: rows that
merge ≥2 distinct numbered plants into one (`1&2`, `I+II`, `III & IV`, `1–3`,
`và`, `mở rộng`). Source: an investigation on branch
`inventory-normalization-exp2`. Persisted here as a durable note (the analysis
is too rich for copy-paste); a dedicated ticket is **deferred** until the
reference-free consolidation objective is prioritized (see §Two objectives).

## Two objectives — do not conflate

This note belongs to a **different objective** than the matcher tickets
(0392–0395), and confusing the two breaks one or the other.

- **Scoring against the reference (0392 done, 0393–0395).** The matcher holds
  the gold reference. Decomposing "Cẩm Phả I & II" to match the attested
  reference rows "Cẩm Phả 1" + "Cẩm Phả 2" fabricates nothing — the reference
  attests both. It is safe, and it is exactly the 0393 fix.
- **Reference-free consolidation (this note).** Fusing runs into a zero-FP
  inventory with **no** reference. Here, decomposing a merged row *fabricates*
  entities → an FP risk that cannot be guaranteed away without a reference. The
  asymmetric-consensus rule (§4) is the right answer instead.

**Therefore the "do not decompose" rule of §4 is correct for the reference-free
path and wrong for 0393.** A downstream instance that applies it to the matcher
would neutralize the 0393 fix. This distinction is logged on ticket 0393.

## 1. Measured extent

Rows merging ≥2 distinct numbered plants:

| Arm | Merged rows | % | Runs touched |
|---|---|---|---|
| arm1 | 27 / 1229 | 2.2 % | 15 / 20 |
| arm2 | 49 / 1049 | 4.7 % | 13 / 20 |
| arm3 | 22 / 1663 | 1.3 % | 16 / 20 |
| arm4 | 37 / 1283 | 2.9 % | 13 / 20 |
| **Total** | **130–135 / 5224** | **2.6 %** | **57 / 80 (71 %)** |

Rare per row, near-ubiquitous per run.

## 2. Three categories — do not over-count

- **Hard 1NF violation** ⇒ two plants joined in one row. **This is the subject.**
- **Soft symptom:** `Units×MW = "multiple"/"aggregate"/"unspecified"`. Ambiguous
  — also covers planned LNG of unknown configuration (missing data ≠ 1NF
  violation). ~5–9 %/arm.
- **False positive to EXCLUDE:** Phase I / Phase II as *separate* rows =
  decomposition (good), not a violation. Likewise `2 GT + 1 ST`, `1 CC` (3+1),
  `Coal + BFG` = atomic description of one CCGT. A naive filter counts 14 %;
  after tightening it is 2.6 %.

## 3. Decisive findings for the method

(a) **It is model behavior, not a parser bug.** The row
`NĐ Cẩm Phả (I+II) | multiple | 600` is written as-is by the model
(`experiments/derived/arm3_flat/anthropic_run01.md:197`). `extract.py` only
merges *fragmented tables* (repeated headers), never plants. → a legitimate
scientific signal, not to be cleaned away silently.

(b) **The corpus decomposes itself (reference-free).** 118/130 (91 %) of merged
rows have all their phases attested atomically in *other* runs. The 12
"orphans" are almost all artifacts of the investigator's key normalization
(`NMĐ`/`NMNĐ` prefixes not stripped, `và` mishandled on Nhơn Trạch — itself
atomically attested in 51 runs). True orphans ≈ 0. **The peer runs ARE the
decomposition authority; no gold is required.**

## 4. Central recommendation — asymmetric rule

Do **not** decompose (`I+II / 600 → 1/300 + 2/300` fabricates entities = FP
risk, not guaranteeable without a reference). Instead:

> A merged row may **reinforce** an entity already attested atomically, **never
> instantiate** a new one.

- FP from a merged row ⇒ impossible by construction.
- Orphans (components attested nowhere atomically) ⇒ drop = FN, not FP.
  Consistent with zero-FP.

The 1NF problem dissolves into an asymmetric consensus fusion. **It is not the
bottleneck.**

## 5. Alert for the downstream instance

The dominant FP risk is **not** merged rows (2.6 %, self-repairing) — it is
**entity resolution**: the threshold deciding `Nhiệt điện Cẩm Phả = NĐ Cẩm Phả ≠
Cẩm Phả 2`. A 3-token `base_key` already produces collisions. Two thresholds in
tension govern zero-FP: (1) name matching, (2) consensus (how many runs attest).
The 1NF asymmetry is a brick *downstream* of entity resolution — testable in
isolation only once resolution is in place. (This is why a 1NF ticket would be
`Blocked-by` an entity-resolution ticket that does not yet exist.)

## 6. Reproduction

Ad-hoc throwaway scripts (uncommitted, Imagine-phase). Key signals:

- **Merged rows:** name-join regex
  `\d\s*&\s*\d | [ivx]+\s*&\s*[ivx]+ | [ivx0-9]\+[ivx0-9] | \d\s*và\s*\d | \d[-–]\d`
- **Self-decomposition:** `phase_nums(name)` (arabic + roman ≤12) ⊆ union of the
  atomic phases of peer runs sharing the same `base_key`.
- **Source:** `experiments/derived/arm{1..4}_flat/*.md`; header located by the
  pipe line containing Province + Fuel + Name|Plant.

## Status

Deferred pending dev priorities. If the paper / benchmark stays front
(reference-based scoring), this is off the critical path — keep as a note. If
the production pipeline (reference-free PyPSA-ASEAN consolidation) is prioritized,
sprout a ticket from §4–§6, `Blocked-by` a new entity-resolution ticket.
