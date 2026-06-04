# Exp2 false-positive audit

Sweep of every false positive (FP) across the four Exp2 arms, deduplicated and
classified, with concrete proposals to repair the matcher and extend the
reference list.

Reproduce: `uv run python experiments/scripts/fp_audit_exp2.py`
Artefacts: `experiments/derived/exp2_fp_{occurrences,dedup,classified}.csv`

## What counts as an FP

An FP is a `SYSTEM_ONLY` reconciliation entry: a plant a model reported that the
global LP matcher (`reconcile()` → `metrics.py`) could not pair with any row of
the frozen 163-row reference `data/reference/vietnam_thermal_v1.csv`. It is the
`hallucinated_plant` term in the error taxonomy. The audit reconciles all 160
runs (4 arms × 4 agents × up to 5 reps) and collects, for each FP occurrence,
the reported **name, fuel, status, capacity, province**, plus the **arm** and
**model**.

## Headline

**640 FP occurrences → 291 distinct plants. Roughly two thirds are matcher
artefacts, not model hallucination.**

| Category | distinct | occurrences | share |
|---|---:|---:|---:|
| `matcher_fail_lp_veto` | 112 | 276 | 43% |
| `matcher_fail_normalization` | 57 | 152 | 24% |
| `statistical_borderline` | 66 | 98 | 15% |
| `reference_hole` | 48 | 95 | 15% |
| `other` (out of scope) | 5 | 13 | 2% |
| `likely_hallucination` | 3 | 6 | 1% |
| **Total** | **291** | **640** | |

**Matcher failures account for ≈67 % of FP occurrences; genuine hallucination is
≈1 %.** The precision penalty the models pay in Exp2 is overwhelmingly a
reconciliation problem, not an extraction problem. This is a take-home-message
caveat: the Exp2 FP/precision bars overstate model error.

### Distribution

By arm (FP occurrences): arm1 (naive) 126 · arm2 (optimised) 112 ·
arm3 (naive+EP) 243 · arm4 (multiturn+EP) 159. Evidence-pack arms produce more
FPs, consistent with longer inventories.

By model (FP occurrences): GPT-5.5 283 (162 in arm1/3 as `gpt-5.5` + 121 in
arm2/4 as `gpt-5.5-2026-04-23`) · Mistral-Large-2512 152 · Qwen3.7-Max 111 ·
Claude-Opus-4-6 94. Claude is the most conservative; GPT-5.5 the most prolific.

## Classification, with evidence

The two scores in `exp2_fp_classified.csv` drive the split:
`cur_score` = best rapidfuzz partial-ratio against the reference under the
**current** cleaner; `new_score` = the same under the **proposed** normalisation
(§Matcher repair). A high `new_score` with a low `cur_score` means "the matcher
*could* have caught it".

### `matcher_fail_normalization` — 57 distinct / 152 occ

The model name carries a Vietnamese facility-type prefix the cleaner does not
strip, or uses `mở rộng` where the reference uses `extension`/`MR`. All recover
to a real reference row once normalised.

| n | plant | → reference | cur→new |
|--:|---|---|---|
| 18 | Nhiệt điện Bà Rịa | Bà Rịa GT | 85.7 → 100 |
| 11 | Nhiệt điện Cẩm Phả | Cam Pha 3 | 87.5 → 100 |
| 10 | NĐ đồng phát Hải Hà 1 | Hai Ha CHP Phase 1 | 77.8 → 93.3 |
| 9 | Nhiệt điện Na Dương | Na Dương 1 | 88.9 → 100 |
| 5 | NĐ đồng phát Đức Giang | Duc Giang – Lao Cai Chemical | 85.7 → 100 |

Root cause: `cleaner/config.json:name_drops` strips `tbkhh`, `lng`, `nd`,
`thermal`, parentheticals — but **not** the single most common prefix
`nhiệt điện` (→ `nhiet dien`), nor `nhà máy` (`nha may`), `đồng phát`
(`dong phat`), or bare `tbk`; and `mở rộng`/`MR` is not unified with
`extension`.

### `matcher_fail_lp_veto` — 112 distinct / 276 occ

Name already matches a reference row at ≥90, but the global one-to-one LP left it
unmatched. Three sub-mechanisms:

| n | plant | → reference | mechanism |
|--:|---|---|---|
| 17 | Nhiệt điện Duyên Hải 3 mở rộng | Duyen Hai 3 (+ "Duyen Hai 3 Extension") | base/extension contention |
| 17 | Nhơn Trạch 3 & 4 | LNG Nhơn Trạch 3 / 4 | combined `X & Y` row; unit-number veto |
| 16 | Nhiệt điện Vĩnh Tân 4 mở rộng | Vinh Tan 4 (+ "Vinh Tan 4 extension") | base/extension contention |
| 6 | Cẩm Phả I & II | Cẩm Phả 1 / 2 | combined-units + roman numerals |

The unit-number veto in `matching/lp.py` makes a `3 & 4` row cheaper to leave
unmatched than to pair with either `3` or `4`. Where a model lists both a base
and its extension, the cleaned names collide or the capacity weight misassigns
the LP, dropping one as an FP.

**Caveat:** a slice of this bucket (`Sông Hậu 3`/`Sông Hậu III` 17 occ,
`Nam Định II` 7 occ) fuzzy-matches a *sibling* unit (Sông Hậu 1/2; Nam Dinh 1)
at ≥90 but the named unit number is genuinely **not** in the reference — those
are really reference-holes/borderline, so 276 is an upper bound on LP-veto
failures.

### `reference_hole` — 48 distinct / 95 occ

Real Vietnamese plants absent from the reference under any spelling. Recur across
models, so unlikely to be hallucination.

| n (sum) | plant family | note |
|--:|---|---|
| 23 | Kiên Lương 1/2/3 | large cancelled Kiên Giang coal complex; distinct from "TBKHH Kiên Giang" |
| 13 | Hòa Phát II (khí dư) | Hòa Phát Dung Quất captive BFG/coal |
| 6 | Rạng Đông | Nam Định coal proposal |
| 5 | Kim Sơn | Ninh Bình LNG/coal proposal |
| 4 | Yên Hưng | Quảng Ninh LNG (in PDP8) |

### `statistical_borderline` — 66 distinct / 98 occ

Mid-similarity (75–88), few appearances, ambiguous. Examples: `NĐ Formosa Đồng
Nai` (10×, near "Formosa HT2" / "Dong Nai Formosa"), `Cẩm Thanh` (8×, plausibly
a misspelling of reference "Cong Thanh"), `NĐ Vedan/Vê Đan` (near "Vedan Vietnam
Cogeneration"). Triage per case.

### `likely_hallucination` — 3 distinct / 6 occ · `other` — 5 distinct / 13 occ

Genuine hallucination is rare: `Phú Yên` (4000 MW coal — no such plant),
`NĐ Than An Giang` (2000 MW coal in An Giang — implausible). `other` is
out-of-scope: nuclear (`Ninh Thuận 1/2`), and sub-30-MWe captive cogen
(`Đạm Phú Mỹ` 21 MW, `Bourbon` 24 MW) below the reference's >30 MWe threshold.

## Matcher repair (proposals)

Concrete, test-first. Each step is independently shippable.

1. **Extend `cleaner/config.json:name_drops`** with the missing facility-type
   prefixes (post-diacritic-fold forms): `nhiet dien`, `nha may`, `dong phat`,
   `^tbk\s`, `nmnd?`, `cum`, `trung tam dien luc`. Expected recovery: most of
   `matcher_fail_normalization` (≈150 occ). Guard against over-stripping a name
   down to empty.
2. **Unify the extension marker.** Add a substitution mapping
   `mo rong` / `mr` / `extension` to one canonical token so
   `Vĩnh Tân 4 mở rộng` ↔ `Vinh Tan 4 extension`. This must run *before* the
   unit-number veto so the digit comparison sees identical names.
3. **Romanise the reference once.** The reference mixes 54 ASCII-only names with
   109 diacritic names (`Duyen Hai 1` vs `Duyên Hải 2` — and `duyen hai 2`
   appears twice, once each way). Models emit diacritic Vietnamese, so the 54
   ASCII rows are systematically harder to match. Normalise the reference to a
   single representation (keep diacritics; add a romanised alias column) and the
   cleaner gains a stable target.
4. **Fix reference internal collisions before matching.** 17 cleaned-name
   collisions exist, of two kinds: (a) true duplicates to delete
   (`Dong Nai Formosa`×2, `Ha Tinh Formosa…`×2, `Duyên Hải 2`×2); (b) **distinct**
   plants the cleaner wrongly collapses (`Cà Mau I` vs `LNG Cà Mau 1`;
   `Quang Ninh 1` vs `LNG Quảng Ninh 1`; `NĐ Ô Môn I` vs `TBKHH Ô Môn I`). The
   roman→arabic substitution plus `^lng` drop is too aggressive here — gate the
   `lng` drop so a gas plant and its LNG successor stay distinct.
5. **Handle combined `X & Y` rows.** Either split a system row whose name matches
   `(.+?)\s*(\d+)\s*&\s*(\d+)` into two pre-reconciliation, or relax the
   unit-number veto when one side is an aggregate with no capacity conflict.
   Recovers the `Nhơn Trạch 3 & 4` / `Cẩm Phả I & II` family (≈40 occ).
6. **Re-audit, do not re-instrument blindly.** After steps 1–2 (the cheap,
   high-yield ones) re-run this script; the FP count is the regression oracle.

**Outcome for proposals 3–4 (ticket 0394, 2026-06-04).** Re-running this audit
with the reference swapped (`--reference`, `--label`) measured the collision
repair directly: FP 399 → 399, FN 7617 → 7537 — the delta is the phantom
misses of the deleted `Duyen Hai 2` duplicate. Adjudication with
`units_included` in hand showed only `Duyên Hải 2` was a true duplicate;
`Dong Nai Formosa` and `Ha Tinh Formosa` are base/extension pairs sharing one
name string, renamed `... extension` in
`data/reference/vietnam_thermal_v1_fix1.csv` (see `PROVENANCE.md` §fix1, plus
a `Quảng Trị 1` "Unit 2, Unit 2" typo found by the new integrity test). The 14
cleaner-collapsed pairs cause neither FP nor FN, so the `lng`-drop gate and
the romanised alias column (proposal 3) were dropped — documented non-finding.

## Reference extension (proposals)

Add the verified reference holes (status as noted; all > 30 MWe). Each needs a
`PROVENANCE.md` source line and a new version tag (the file is frozen at
`85a0e6c7`, so this is a `vietnam_thermal_v2.csv` change, not an in-place edit).

- **Kiên Lương 1 / 2 / 3** — Kiên Giang, coal, cancelled (~4400 MW complex).
- **Hòa Phát Dung Quất** captive power (BFG/coal), Quảng Ngãi, operating.
- **Kim Sơn** — Ninh Bình, LNG/coal, proposed.
- **Yên Hưng** — Quảng Ninh, LNG, planned (PDP8).
- **Rạng Đông** — Nam Định, coal, proposed/cancelled.
- Triage from `statistical_borderline`: `Cẩm Thanh` (vs Cong Thanh),
  `Bảo Đại`, `Cái Lân`, `Lục Nam`, `Vedan` cogeneration.

Out of scope, do **not** add: `Ninh Thuận 1/2` (nuclear), `Đạm Phú Mỹ`/`Bourbon`
(< 30 MWe).

## Caveats

- Categories are auto-assigned by rule (`classify()`); the head of every bucket
  was hand-verified but the long tail is heuristic. The
  `lp_veto`/`reference_hole` boundary for sibling units is the softest.
- Dedup is by the *current* cleaned name, so spelling variants of one real plant
  (e.g. `Uông Bí mở rộng 2` vs `Uông Bí MR 2`) count as distinct rows; the true
  number of distinct real plants behind the 291 is smaller.
