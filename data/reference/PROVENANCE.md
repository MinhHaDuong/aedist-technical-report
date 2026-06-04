# Reference dataset provenance — vietnam_thermal_v1.csv

## Scope and version lock

163 thermal generation assets >30 MWe in Vietnam (coal, gas, gas/oil),
covering all lifecycle statuses. Status distribution:
operational 57, proposed 62, planned 21, constructing 10, cancelled 11,
retired 2.

This file is frozen at commit `85a0e6c7c9690fa327f6a8b5d4ba024110653945`
as of 2026-05-20 for Experiments 1–3. Any later edit to the CSV requires
a new version tag and a corresponding entry in this file.

## Compilation method

Single-author manual compilation from primary sources, cross-referenced
against `data/rag_corpus/` snapshots and EVN annual reports. See
`docs/quality-grounding.md` for the broader quality framework that
motivates the reference design (notably §2.1 on empirical adequacy and
§5 gap G5 on the lack of an independent second reviewer).

## Source inventory

The 18 files currently snapshotted under `data/rag_corpus/` back the
inventory's plant identity, capacity, status, and COD fields:

| File | Backs |
|---|---|
| PDP7_annex1.md | Plant list and capacities under PDP7 |
| PDP7_annex2.md | Plant list and capacities under PDP7 |
| PDP7A_annex1_table1.md | PDP7A revisions (table 1) |
| PDP7A_annex1_table2.md | PDP7A revisions (table 2) |
| PDP7A_annex1_table3.md | PDP7A revisions (table 3) |
| PDP8_annex2_table1.md | PDP8 plant list (table 1) |
| PDP8_annex2_table2.md | PDP8 plant list (table 2) |
| PDP8_annex2_table3.md | PDP8 plant list (table 3) |
| PDP8_annex2_table4.md | PDP8 plant list (table 4) |
| PDP8_annex2_table5.md | PDP8 plant list (table 5) |
| EVN_Annual_Report_2010_2011_CapacitiesTable.md | EVN-owned operational capacities, 2010–2011 |
| EVN_Annual_Report_2017_CapacitiesTable.md | EVN-owned operational capacities, 2017 |
| EVN_Annual_Report_2018_CapacitiesTable.md | EVN-owned operational capacities, 2018 |
| Report_32_annex1.md | Project-specific status notes |
| Report_58_annex.md | Unit-level fine-grained capacities |
| Study_E542_table_9.1.md | Unit-level fine-grained capacities |
| Study_E542_table_9.2.md | Unit-level fine-grained capacities |
| Study_E542_table_9.5A.md | Unit-level fine-grained capacities |

**Off-corpus sources.** MOIT decisions (numbering and issue dates) were
consulted by the author through Vietnam government gazettes during
compilation but are not snapshotted in `data/rag_corpus/`. The reference
file's `status` column reflects the most recent applicable MOIT decision
known to the author at the freeze date.

## Conflict-resolution rules

Where sources disagreed during compilation, the following priority applied:

- **Forward-looking fields (`proposed`, `planned`, projected COD):** PDP8
  supersedes PDP7A which supersedes PDP7. PDP8 annexes 2-1 through 2-5
  are authoritative for the post-2021 pipeline.
- **Operational capacities (existing plants):** EVN annual reports take
  precedence over any PDP annex, as PDP figures are planning targets
  that may diverge from commissioned reality. The 2018 EVN report is
  the latest snapshot.
- **Unit-level capacities within a multi-unit plant:** Report_58_annex
  and Study_E542 tables provide the finest-grained breakdown when annex
  tables aggregate to plant level.
- **Status reclassifications between cycles:** the latest PDP wins
  (PDP8 > PDP7A > PDP7), even when EVN annual reports list an interim
  status that has since been superseded.

## Residual uncertainty (top-3 disputed cases)

The 62 "proposed" + 21 "planned" rows carry the highest status
volatility across PDP cycles. The three cases most likely to shift
status, capacity, or developer between the freeze date and any
downstream use:

- **LNG Cái Mép Hạ** (Bà Rịa-Vũng Tàu, 6000 MWe, status=proposed) —
  PDP8 multi-phase project; per-phase MWe contested across sources,
  and the developer consortium has not fully closed financing as of
  the freeze date.
- **LNG Hà Tĩnh** (6000 MWe, status=proposed) — siting and developer
  reshuffling between the PDP7A and PDP8 cycles; the project's
  province assignment and lead developer differ across vintages.
- **Dung Quat SEZ J-Power Phase I** (Quảng Ngãi, 2400 MWe coal,
  status=proposed) — foreign-developer coal entry kept in PDP8
  against the broader domestic coal contraction; future
  re-classification or cancellation likely.

## GEM cross-check

An independent 153-plant comparison with Global Energy Monitor data
(`data/reference/gem_thermal.csv`) is deferred. See
`docs/quality-grounding.md:65` and gap G5. The three-way reconciliation
(system vs. expert vs. GEM) would quantify reference disagreement rate
but is out of scope for the current article.

## Known limitations

Single observer; no independent second reviewer; per-row audit trail
(which source backs which cell) is incomplete. The 62 "proposed" + 21
"planned" rows carry the highest status volatility and should be
treated as upper-bound counts: the planning horizon has tightened
under PDP8, and any reader using these rows for capacity-expansion
analysis should re-validate against the most recent MOIT decisions.

To our knowledge, no public per-plant audit-trail dataset exists for
Vietnam's thermal generation fleet that would let an independent
reviewer reconstruct the compilation row by row. Closing that gap
is the motivation for the source-citation infrastructure in
Experiments 2–3.

## fix1 integrity patch (2026-06-04, ticket 0394)

`vietnam_thermal_v1_fix1.csv` (162 rows) and
`vietnam_thermal_units_v1_fix1.csv` (249 rows) are built from the frozen
v1 files by `experiments/scripts/build_reference_v1_fix1.py` — a pure
text transform that preserves every untouched field verbatim (a
spreadsheet round-trip during adjudication coerced `ires_code` 0121 to
121; the scripted rebuild is the countermeasure, and
`tests/test_reference_integrity.py` guards the invariants).

Four defects, adjudicated by the author on 2026-06-03/04. The `name`
column is the de-facto key (matcher, plant↔units linkage, diagnostics);
defects 1–3 are key collisions, defect 4 a data-entry typo:

1. `Duyen Hai 2` (ASCII, 600 MW, Unit 1) deleted at both levels —
   romanization duplicate subsumed by `Duyên Hải 2` (1200 MW, Units 1+2).
2. `Dong Nai Formosa` (proposed, Unit 3) renamed
   `Dong Nai Formosa extension` — two distinct assets (operational base
   vs proposed extension) shared one identical name string; renamed
   following the file's existing `extension` convention.
3. `Ha Tinh Formosa Plastics Steel Complex` (proposed, Units 6/7/10)
   renamed `... extension` — same pattern.
4. `Quảng Trị 1` typo: `units_included` listed Unit 2 twice; first
   occurrence corrected to Unit 1 at both levels (1320 MW = 2x660,
   sibling plants all have Units 1+2).

Effect, measured by re-reconciling all Exp2 outputs (80 runs): FP
unchanged (399 -> 399); FN 7617 -> 7537, the delta being phantom misses
carried by the deleted duplicate row. The 14 remaining `clean_name`
collisions (distinct gas/LNG plants merged by the cleaner's prefix
drops) cause neither FP nor FN and are left untouched — a documented
non-finding; see ticket 0394.

The frozen v1 files remain the scoring reference for Exp1–3. Adoption
of fix1 (figure-level before/after validation, then rewiring) is
tracked in a separate ticket.
