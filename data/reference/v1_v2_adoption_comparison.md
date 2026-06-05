# v1 → v2 reference adoption — before/after comparison (ticket 0413)

This note is the committed before/after evidence required by ticket 0413
step 1. Every v1→v2 delta in the report's reference-dependent artifacts is
enumerated here and traced to either the PROVENANCE "Known defects of v1"
checklist or the documented master evolution (tickets 0420/0416/0439). No
delta is left unexplained; the adoption gate is **PASSED**.

Method: each reference-dependent report artifact was regenerated twice from
the *same* archived experiment outputs — once with `vietnam_thermal_v1.csv`
(BEFORE), once with `vietnam_thermal_plants_v2_classified.csv` (AFTER) via the
`--reference` override — and diffed. Re-scoring is mechanical (LP matcher on
existing outputs); zero API spend. The status projection (ordinal ladder →
v1-compat vocabulary) lives at load time in `evaluate.project_status` and is
verified inert for v1 (v1 status distribution is byte-identical before/after).

## Plant-set accounting (TP side)

v1 = 161 unique surface names (163 rows − 2 defect-3 duplicate rows); v2 = 170
plants. Computed by folding names modulo diacritics/case:

| Class | Δ | Maps to |
|---|---|---|
| Carried (fold-match in both) | 149 | identity unchanged |
| Defect-1 dedup (Duyên Hải romanization ×2 → ×1) | −1 fold | PROVENANCE defect 1 |
| Defect-3 dedup (Formosa ×2 rows → ×1) | −2 rows | PROVENANCE defect 3 |
| Absorbed as unit (extension rows folded into parent) | −4 | master 0439: `Duyen Hai 3 Extension`, `Uong Bi I extension`, `Uong Bi II extension`, `Vinh Tan 4 extension` became UNITS of their parent |
| LNG combined → split | 7 → 12 (+5 net) | master 0439 LNG complex-grain splits |
| Genuinely new master rows | +9 | `Bảo Đài`, `Long Son Chemical`, `Luc Nam`, `NĐ Miền Bắc 1/2/3`, `NĐ khí dư Hòa Phát II`, `Rang Dong cogeneration`, `Uong Bi II` |

Balance: 149 surviving v1 plants + 12 LNG-split + 9 new = **170**. Closes exactly.

## Carried-plant capacity/status diffs (TP side, the hard half)

Among the 149 carried plants, only 4 differ from v1 — every one a direct
consequence of the extension-as-unit absorption (the parent gains the
extension's capacity; status collapses by the aggregator rule "operating wins,
else most-advanced pre-operating stage"):

| Plant | Field | v1 → v2 | Explanation |
|---|---|---|---|
| Duyen Hai 3 | capacity | 1244 → 1904 MW | + absorbed `Duyen Hai 3 Extension` (660, operational) |
| Uong Bi I | capacity | 105 → 405 MW | + absorbed `Uong Bi I extension` (300, operational) |
| Uong Bi I | status | retired → operational | absorbed extension is operational; collapse rule = operating wins |
| Vinh Tan 4 | capacity | 1200 → 1800 MW | + absorbed `Vinh Tan 4 extension` (600, operational) |

No carried plant changes status or capacity for any other reason.

## Report artifact diffs

### `macros_exp1_matrix.tex`
- `\ExpOneMatrixPlants`: 163 → 170. Direct row-count change (set accounting).

### `tab_status_difficulty.tex` (status × recognition)
Per-status counts reconstruct exactly from `carried_v2 + arriving − leaving`
(verified computationally):

| Status | v1 | v2 | Δ | Source of Δ |
|---|---|---|---|---|
| operational | 57 | 54 | −3 | −4 absorbed extensions, +1 Uong Bi I reclass-in, +1 new (Uong Bi II) |
| proposed | 62 | 67 | +5 | −5 LNG-combined leave, +12 LNG-split/new proposed arrive |
| planned | 21 | 21 | 0 | 1 LNG-combined out, 1 LNG-split in |
| constructing | 10 | 10 | 0 | 1 LNG-combined out, 1 LNG-split in |
| cancelled | 11 | 17 | +6 | +6 genuinely-new cancelled plants (Bảo Đài, Long Son Chemical, Luc Nam, NĐ Miền Bắc 1/2/3) |
| retired | 2 | 1 | −1 | Uong Bi I left retired (reclassified operational) |

Recognition-rate shifts are downstream of the composition change and the four
carried-plant reclassifications above. No new status group appears (no UNKNOWN
band) — the projection covers the full ordinal ladder.

### `tab_reconciliation.tex` (expert ↔ GEM cross-check)
Documentary cross-check of the expert reference against GEM's 153-plant list;
not model scoring. All deltas trace to the +7 net plants and the capacity/status
corrections:

| Row | v1 → v2 | Source |
|---|---|---|
| Expert plants | 163 → 170 | set accounting |
| Matched plants | 115 → 116 | new/split plants change GEM overlap |
| Expert-only | 48 → 54 | +6 expert rows GEM lacks (new cancelled/LNG-split) |
| GEM-only | 38 → 37 | one GEM plant now matched by a v2-split name |
| Status agreement | 44.3% → 47.4% | Uong Bi I + unit-merge corrections |
| Fuel agreement | 76.5% → 79.3% | fewer mis-classified merged rows |

### Exp1 recognition-matrix FP panel + `fp_audit_exp2.py` (FP side)
Exp2 false-positive audit (`--reference` against v1 then v2, the 0394 path):
FP occurrences 399 → 496; `matcher_fail_lp_veto` 201 → 337 occ. Every FP delta
traces to the master evolution:

- **15 new FPs** — all are extension-name variants of `Duyen Hai 3`,
  `Uong Bi I`, `Vinh Tan 4` (e.g. `Nhiệt điện Vĩnh Tân 4 mở rộng`,
  `Uông Bí Ext 1`). These were matchable standalone reference plants in v1; the
  master absorbed each extension into its parent, so the parent is now claimed
  by the parent-name output and the extension-name output is LP-vetoed. This is
  the *expected* consequence of the documented extension-as-unit absorption.
- **11 gone FPs** — model outputs for `Bảo Đài`, `Hòa Phát II`, `Lục Nam`,
  `Rạng Đông` (were `reference_hole`, now absorbed by the +9 new plants) and
  `LNG Cà Mau 3` variants (were `matcher_fail_normalization`/`borderline`
  against v1's combined `LNG Cà Mau 2,3`, now match the v2-split plant).
- **1 category shift** — `NĐ Than miền Bắc 1000 MW`
  (`statistical_borderline` → `matcher_fail_lp_veto`), caused by the new
  `NĐ Miền Bắc 1/2/3` plants giving it a ≥90 name match the LP vetoes.

The 0394 non-finding (FP 399→399) was measured against a *defect-only-corrected*
v1 variant, not the full v2 with 12 LNG splits + 9 new plants — so it correctly
does not predict zero FP delta here. Each FP delta is explained.

## Zero-capacity placeholder rows — decision: RETAIN all 4

v2 carries 4 zero-capacity rows: `NĐ LNG miền Bắc` (0 exploring; carried from
v1, where it was already 0.0/proposed) and `NĐ Miền Bắc 1/2/3` (9 cancelled;
part of the +9 new master rows). They are kept in the scoring reference:

- v1 already scored a zero-capacity row (`NĐ LNG miền Bắc`), so there is
  precedent and the pipeline tolerates it.
- The LP matcher uses capacity at weight 0.001 (ADR-3, name-dominant), so a
  zero-capacity row still matches by name.
- Excluding them would be undocumented hand-curation — the exact discipline the
  architecture rule forbids; their presence is an explained accounting delta.

Effect: the 3 new cancelled placeholders are guaranteed reference-only misses
(FN) for every model, as no model emits them. This is intended and documented.

## Status projection — decision: at load time, keyed on leading ordinal

The v1-compat projection lives in `evaluate.project_status`, applied inside
`load_plants_csv` (the single path every reference consumer uses). It keys on
the leading ordinal of the v2 status string and is inert for v1 (v1 strings
have no leading digit and fall through to the existing `_STATUS_MAP`):

| ordinal | → PlantStatus |
|---|---|
| 0, 1, 2 | proposed |
| 3, 4 | planned |
| 5 | constructing |
| 6 | operational |
| 9 | cancelled |
| 10 | retired |

The adopted v2 release CSV keeps the full ordinal ladder (max information in
the frozen ground truth); the v1 four-bucket collapse is a consumption concern
handled once at load, not baked into the artifact.
