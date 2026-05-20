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

**Off-corpus sources.** MOIT (Ministry of Industry and Trade) decisions
(numbers and dates of approval, cancellation, or reclassification of
specific projects) were consulted by the author at compilation time but
are not snapshotted in `data/rag_corpus/`. They are therefore not
available to the RAG pipeline in Experiments 2–3.

**AUTHOR-TODO:** list the specific MOIT decision IDs that were consulted
(e.g., "Decision 1208/QĐ-TTg", "Decision 428/QĐ-TTg", "Decision
500/QĐ-TTg", and any project-specific approvals), with date and the
fields they back.

## Conflict-resolution rules

**AUTHOR-TODO:** state the explicit priority rule used during
compilation. Default proposal (please confirm or override):

- **Forward-looking fields** (status="proposed" / "planned", expected
  COD): PDP8 > PDP7A > PDP7 — the most recent master plan governs.
- **Operational capacities** (status="operational", actual COD):
  EVN annual report > any PDP — the operator's own report is closer
  to the asset than the planning document.
- **Unit-level capacities** (multi-unit complexes where total ≠ sum
  of nameplate units): Report_58 / Study_E542 > PDP tables —
  fine-grained sources resolve the unit breakdown.
- **MOIT decisions** override the most recent PDP for status changes
  enacted after the PDP was published (e.g., a project cancelled by
  decision after PDP8 listed it as proposed).

When two sources of equal priority disagree, the row carries the
most-recent value and the alternative is recorded in a per-row note.

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
