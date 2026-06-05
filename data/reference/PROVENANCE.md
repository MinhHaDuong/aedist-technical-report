# Reference dataset provenance — Vietnam thermal fleet

## Adopted release (v2, ticket 0413, 2026-06-05)

**The frozen reference is now `vietnam_thermal_plants_v2_classified.csv`**
(170 plants), pipe-regenerated from the master snapshot
`pipeline-2026-06-05.ods` by `extract_ods.py → aggregate_units.py →
add_classifications.py` (`make -C experiments -f acquire.mk
reference-pipeline`). Status distribution (v1-compat projection, see below):
operational 54, proposed 67, planned 21, constructing 10, cancelled 17,
retired 1. Provenance: extractor @ this commit applied to snapshot 2026-06-05.

The adoption ceremony (before/after gate, single-switch flip, official
re-score) is recorded in `data/reference/v1_v2_adoption_comparison.md`: every
v1→v2 delta in every reference-dependent report artifact traces to a "Known
defects of v1" entry (now fixed, below) or the documented master evolution
(extension-as-unit absorption, LNG splits, +9 new rows). The v2 release carries
the master's unified **ordinal status ladder** ("0 exploring" … "6 operating",
"9 cancelled", "10 retired"); consumers project it to the v1 four-bucket
vocabulary at load time via `evaluate.project_status` (≤2→proposed, 3–4→planned,
5→constructing, 6→operational, 9→cancelled, 10→retired). The 4 zero-capacity
placeholder rows (1 "0 exploring" `NĐ LNG miền Bắc`, carried from v1; 3 "9
cancelled" `NĐ Miền Bắc 1/2/3`, new) are **retained** in the scoring reference:
v1 already scored a zero-cap row, the LP matcher is name-dominant (capacity
weight 0.001, ADR-3), and excluding them would be undocumented hand-curation.
The 3 new cancelled placeholders are therefore guaranteed reference-only misses
(FN) for every model — intended.

**Re-score scope.** The v2 re-score covers Experiment 1 (the exp1_batch2
baseline, scored records + measurements rows carry
`reference=vietnam_thermal_plants_v2_classified.csv`) and Experiments 2–3 (the
`exp2_mart.jsonl` / `sota_cross_eval.csv` arms, scored against v2). The earlier
**model-census** rows (`direct`/`rag`/`multiturn`/`ablation`, `prompt_version`
absent / `census`) remain v1-era record (no `reference` field): their raw
replies live in `experiments/archive/outputs/`, there is no live DAG edge to
re-score them, and they are not displayed in the manuscript's Exp1–3 figures.
The `\input`'d census macros (`macros_census`, `macros_p1_base`, `tab_census`)
and the orphan `scaling_curve`/`regimes_scatter` figures therefore still reflect
v1-era scoring; their v2 re-score is deferred (ticket 0444).

## v1 (retired) — scope and version lock

163 thermal generation assets >30 MWe in Vietnam (coal, gas, gas/oil),
covering all lifecycle statuses. Status distribution:
operational 57, proposed 62, planned 21, constructing 10, cancelled 11,
retired 2.

v1 was frozen at commit `85a0e6c7c9690fa327f6a8b5d4ba024110653945`
as of 2026-05-20 and scored Experiments 1–3 until the 0413 v2 adoption. It is
retained in-tree (`vietnam_thermal_v1.csv`) as the pre-adoption record.

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

## Known defects of v1 (2026-06-04, ticket 0394) — FIXED IN v2 (0413)

**Status: closed.** All three defects below are corrected in the v2 release
adopted by ticket 0413 (2026-06-05): defects 1–2 were fixed in the master
(DH2 romanization removed 2026-06-03, Quảng Trị 1 duplicate Unit renamed
2026-06-04) and defect 3 is structurally impossible under the three-column
address contract (the aggregator groups by the data-carried `Plant`/`Complex`
cell, never by a name string, and hard-fails on a duplicate plant key). The
before/after gate confirmed every v1→v2 difference maps to these defects or the
documented master evolution; see `v1_v2_adoption_comparison.md`. The section is
retained below as the historical record and the expected-delta checklist used
at adoption.

The frozen v1 files kept scoring Exp1–3 **as-is** until adoption. The defects
below were documented, their scoring impact measured (nil for FP), and their
correction deliberately delegated to the master + regeneration pipeline
(tickets 0420 → 0416 → 0419; adoption in 0413 after the Cergy archive 0412). An
interim patched copy ("fix1", PR #699 first versions) was built, measured, and
then dropped: it duplicated upstream truth downstream and nothing consumed it.

Adjudicated by the author on 2026-06-03/04:

1. `Duyen Hai 2` (ASCII, 600 MW, Unit 1) duplicates `Duyên Hải 2`
   (1200 MW, Units 1+2) under a second romanization — at plant and unit
   level. Already fixed in the master (pipeline.ods, 2026-06-03).
2. `Quảng Trị 1` transcription error: `units_included` lists Unit 2
   twice ("Unit 2, Unit 2"), and the unit file carries two identical
   `Quảng Trị 1 Unit 2` rows — the plant is 1320 MW = 2 x 660, Units 1+2
   (sibling plants all have Units 1+2). Present in the unit-level master
   itself (a duplicated "Unit 2" row, no Unit 1); fixed there by the
   author on 2026-06-04.
3. `Dong Nai Formosa` ×2 and `Ha Tinh Formosa Plastics Steel Complex`
   ×2: two rows sharing one name (operational base vs proposed
   expansion, disjoint units). The plant name is the key and must be
   unique in v2; resolution happens in the master with source-attested
   designations — names are never invented.

Origin: defects 1–2 sat in the unit-level master itself and have been
fixed there by the author (DH2 on 2026-06-03, Quảng Trị 1 on
2026-06-04); the aggregation step passed them through silently — no
input guards — and manufactures defect 3 on its own
(`HDM_aggregate.py` groups by name+status — ticket 0416). A spreadsheet
round-trip during adjudication also coerced `ires_code` 0121 to 121 —
which is why the v2 pipeline reads everything as text (ticket 0420).

Measured impact (all 80 Exp2 runs re-reconciled against a corrected
variant via `fp_audit_exp2.py --reference`): FP unchanged, 399 -> 399;
FN 7617 -> 7537, the delta being phantom misses carried by the
duplicate row. The 14 `clean_name` collisions among *distinct* plants
(gas/LNG successors merged by the cleaner's prefix drops) cause neither
FP nor FN — documented non-finding, the cleaner stays untouched.

These defects double as the **expected-delta checklist** when validating
v2 against v1 at adoption time (0413): any v1→v2 difference beyond them
and the master's own evolution must be explained.

## Pipeline v2 (ticket 0420) — snapshot → release

**Snapshot ≠ release.** A snapshot's identity is *when it was captured*
(datestamp); a release's identity is *what the project adopted* (v1, v2 — a
deliberate act with a diff audit). The v2 reference **release** is produced by a
single reproducible extraction step that replaces the lost manual-export chain
(`pipeline.ods` → hand export → `HDM.csv` → `HDM_aggregate.py` with hard-coded
paths → manual curation). Every arrow in that chain was manual and uncommitted —
the seam through which the `ires_code` 0121→121 coercion entered.

**Snapshot source (ticket 0430).** The master spreadsheet lives in the author's
"Market report on Gas to Power" project. A read-only datestamped snapshot is
imported to `data/reference/raw/pipeline-YYYY-MM-DD.ods` by
`data/reference/raw/import.sh` (the master is absent from CI and the
workstation, so the script is documentation-grade and never runs in CI). Once
committed, a snapshot is immutable. Files under `raw/` are never hand-edited;
corrections go into the master, then re-import to produce a new datestamped
snapshot (see `data/reference/raw/README.md`). Config pins
(`config.VN_THERMAL_MASTER_SNAPSHOT_ODS`) point at a specific snapshot.

**Extraction.** `data/reference/extract_ods.py` reads sheet `"Power plants"`
with `header=4` (row 0 = title, rows 1–3 = metadata/sub-headers, row 4 = column
names; 254 data rows as of the 2026-06-05 snapshot) using
`pandas.read_excel(engine="odf", dtype=str)`. Every value stays a string — no
numeric coercion, so leading zeros survive by construction. It projects to
`name`, `complex`, `plant`, `unit`, `province`, `asset_type`, `capacity_mwe`,
`status`, `level`; `name` (the attested designation: Plant + Unit concatenated,
or the bare grain) and `level` (the finest non-empty address column, ticket
0401) are derived, never stored. Run via
`make -C experiments -f acquire.mk extract-reference-ods` (the Makefile consults
`config.VN_THERMAL_MASTER_SNAPSHOT_ODS` for the pinned snapshot path).

**Input validation (hard stop, no tolerance).** `validate_input` runs before
any transformation:
- `validate_address_shape` — fails on a Unit without a Plant (an unfinished
  split: parentage would be a name inference again) or a row with all three
  address columns empty.
- `validate_no_duplicate_names` — fails if any derived designation repeats
  *modulo diacritics and case* (NFKD fold + drop combining marks + casefold),
  listing the original surface forms.
A failure writes no CSV. Deeper conventions — grain exclusivity, controlled
status vocabulary, Plant→Complex consistency — are the 0416 contrat v2 layer.

## Master migration to the three-column address (ticket 0439, 2026-06-05)

**Motif.** The root defect class of v1 was identity carried by name strings
("X Unit 2" duplicated by hand — defects 1–3 above). The master now carries a
three-column address `Complex | Plant | Unit` (one denormalized table,
dimension-path pattern): parentage is data, never an inference. Design
ratified in the 2026-06-05 Imagine dialogue (alternatives — Parent column,
3NF tables, surrogate IDs, sidecar — documented in session); conventions live
in the master's own `Conventions` sheet (grain exclusivity, empty-cell
semantics, no Block column, controlled status vocabulary, human attestation).

**The pass.** One editing surgery on the author's working copy: defect fixes
1–2 re-done (ASCII `Duyen Hai 2` row removed, `Quảng Trị 1` duplicate Unit 2
renamed Unit 1), 250→254 rows (LNG complex-grain additions), 176 designations
split mechanically via a reviewed proposal CSV (author adjudicated: `GT` stays
in the plant name, extensions become units), project stages renumbered into a
single ladder (0 exploring … 6 operating, 9 cancelled, 10 retired; the
`4 Construction`/`4 construction` case split unified). Captured as
`pipeline-2026-06-05.ods` and pinned. Extraction is green on this snapshot —
the first snapshot accepted since the validator hard-stop landed (0420).

**Same-day recapture (Err:510 fix).** The first 2026-06-05 capture carried a
leaked spreadsheet formula error (`Err:510`) in the capacity of Vung Ang 2
Unit 1/2, caught by the 0416 aggregator's capacity guard (PR #760; extraction
had green-lit it — closed by the 0442 extraction validator). The author fixed
the formula in the master and the snapshot was recaptured the same day,
replacing the defective blob. Legitimate exception to snapshot immutability:
no release or artifact ever derived from the defective capture (the pipe
refused it), and git history preserves the original blob.

The `ires_code`, `ires_label`, `isic_code`, and `pypsa_carrier` columns are NOT
in the ODS; they are added downstream (ticket 0416 aggregator, or manually), not
by this extraction step.

Each release entry should cite: "extractor @ commit X applied to snapshot
YYYY-MM-DD" (per ticket 0430 traceability discipline).

## Aggregation + classification (ticket 0416) — units → plants

`aggregate_units.py` rolls the unit-grain CSV up to plant grain, replacing the
lost `HDM_aggregate.py` (whose `normalize_plant_name` parsed "X Unit N" off the
name to find the parent — a forbidden name synthesis). Under the three-column
address contract parentage is DATA: grouping is a pure `groupby(Plant)` (or
`Complex` for the 19 complex-grain LNG rows). The output plant name is the
`Plant`/`Complex` cell verbatim — never invented.

**Hard guards (no tolerance, master-fix doctrine).**
- INPUT: a duplicated unit designation aborts (the "Quảng Trị 1 Unit 2" x2 →
  1320 defect can never be summed).
- INPUT: a non-numeric, non-empty capacity aborts (`validate_capacity_numeric`).
  An empty cell is legitimately-unknown capacity (summed as 0, v1-consistent —
  `NĐ LNG miền Bắc` = 0.0); a spreadsheet error value is corruption.
- Per-plant invariants: all units of a plant must agree on `province` and
  `asset_type` (a disagreement is a master error). **Status is NOT asserted
  constant** — units commission and retire in phases (Dong Nai Formosa
  operating+announced, Uong Bi I operating+retired), so status is collapsed
  (operating wins; else the most-advanced pre-operating stage).
- OUTPUT: plant name unique, no unit repeated within one plant's `Units
  Included`, no unit in two groups.

Fuel is derived from `asset_type` (pipe-owned, contrat v2): Coal/Coal cogen →
coal, Gas → gas, Gas/Oil → gas/oil. `add_classifications.py` (rewritten to an
input→output transform, ticket 0416) then adds the IRES/ISIC/PyPSA columns. The
whole chain is `make -C experiments -f acquire.mk reference-pipeline`.

**Known defect of the 2026-06-05 snapshot — BLOCKS criterion 5.** The `Vung Ang
2` Unit 1 and Unit 2 capacity cells carry `Err:510` (a leaked spreadsheet
formula error; v1 records 665 + 665 = 1330 MW). The aggregator correctly
refuses the snapshot with an actionable message. The v1→v2 oracle (criterion 5)
cannot run on a clean full extract until the author fixes the formula in the
master and re-imports a clean snapshot. raw/ snapshots are immutable — the fix
is upstream, not in this repo.

**v1 → v2 plant-set accounting (oracle, computed with Vung Ang 2 patched to its
v1 value for the count only).** Every delta is explained by a documented class;
the balance closes exactly. v1 = 161 unique plant names (163 rows − 2 defect-3
duplicates: Dong Nai Formosa, Ha Tinh Formosa, each two same-name rows in v1,
one plant in v2); v2 = 170 plants.

| Class | Δ | Detail |
|---|---|---|
| Common (unchanged identity) | 150 v1 names → 149 v2 plants | name present as a plant in both (one fold-collision, next row) |
| Defect-1 dedup (Duyên Hải romanization ×2 → ×1) | −1 | `Duyên Hải 2` and ASCII `Duyen Hai 2` are two v1 names that fold to one v2 plant; the ASCII duplicate was merged in the master (PROVENANCE defect 1) |
| Defect-3 dedup (Formosa ×2 → ×1) | −2 rows in v1 | `Dong Nai Formosa`, `Ha Tinh Formosa` each two same-name multi-status rows in v1, one plant in v2 (PROVENANCE defect 3) |
| Absorbed as unit (master split) | −4 from v1 | `Duyen Hai 3 Extension / Uong Bi I extension / Uong Bi II extension / Vinh Tan 4 extension` were standalone v1 plant rows; the master made each a UNIT of its parent plant |
| LNG combined → split | 7 v1 → 12 v2 | `LNG Cà Mau 2,3 → 2 + 3`, `LNG Cà Ná II+III → II + III`, `LNG Hải Lăng / (2 and 3) → (1)/2/3`, `LNG Long Sơn / II+III → (I)/II/III`, `LNG Mũi Kê Gà 2,3 → 2 + 3` |
| Genuinely new master rows | +9 | `Bảo Đài`, `Long Son Chemical`, `Luc Nam`, `NĐ Miền Bắc 1/2/3`, `NĐ khí dư Hòa Phát II`, `Rang Dong cogeneration`, `Uong Bi II` |

Balance (closes exactly): v1 = 161 unique names (163 rows − 2 defect-3
duplicates). Of those 161: 150 are still present as a plant name in v2 (but two
of them — defect 1, the Duyên Hải romanization pair — fold to a single v2 plant,
so 149 distinct surviving plants), 4 became units of their parent, 7 were LNG
combined designations. v2 = **149 surviving v1 plants + 12 LNG-split + 9
genuinely new = 170**. No unexplained delta in the plant SET; every difference
maps to a PROVENANCE "Known defects of v1" entry (defects 1 and 3) or the
master's own evolution (extension-as-unit splits, LNG splits, new rows).
Per-plant capacity/status diffs are deferred to the 0413 adoption ceremony and
require the clean (Err-free) snapshot.
