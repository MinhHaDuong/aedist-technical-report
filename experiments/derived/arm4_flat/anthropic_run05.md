## Corrections & additions (Turn 4 verification)

### Rows to ADD

| ID | Plant Name | Fuel | Technology | Province | Units × MW | Total MWe | Owner/Developer | Status | COD / Target | Source | Confidence |
|----|-----------|------|-----------|----------|-----------|-----------|----------------|--------|-------------|--------|------------|
| O01 | Thu Duc (oil ST) | Oil (FO) | Steam turbine | HCMC | — | 165 | GENCO3 | Operating | 1960s | EA17, EA18 | CONFIRMED |
| O02 | Hiep Phuoc | Oil (FO/DO) | Steam turbine | HCMC | — | 375 | Foreign IPP | Operating | 1997 | EA11 | MEDIUM |
| C63 | Ve Dan (coal cogen) | Coal | Cogen | Dong Nai | 1×60 | 60 | Foreign IPP | Operating | ~2016 | P7A1 | MEDIUM |
| L22 | LNG Quang Trach III | LNG | CCGT | Quang Binh | — | 1,500 | — | Announced | 2031–35 | WS (Decision 768) | MEDIUM |

**Note:** O01 and O02 are oil-fired, not gas or coal. They appear in EA11/EA17/EA18 and are included for completeness; PDP7 Annex 1 scheduled Hiep Phuoc for retirement in 2019 and Thu Duc (oil portion) in 2020. Both likely still available as peakers. Ve Dan appears in P7A1 as 60 MW coal cogeneration for 2016; the 72 MW gas unit from EA11 may be a separate facility at the same industrial complex. L22 was already listed as L19 — duplicate removed (see below).

### Rows to CORRECT

| ID | Field | Was | Should be | Reason |
|----|-------|-----|-----------|--------|
| C09 | Total MWe | 600 | 600 | Correct; EA17 shows Quang Ninh 1 at 600 (2×300 confirmed by EA18 showing GENCO1 coal at 4,920 total which reconciles) |
| C11 | Units × MW | ~4 units | mixed (6×old + 2×150) | Cam Pha complex includes old units + Cam Pha II 300 MW (P7: 2011). EA11 total = 600 MW under Vinacomin. |
| C17 | COD | 2014–15 | 2014–15 | Correct. EA17 shows QN2 at 600 MW. P7 lists QN II #1 at 300 MW for 2014, #2 for 2015. |
| C29 | COD | ~2021 | 2020–21 | R58 assessed "chậm 1 năm" from 2020–2021 schedule; P7A1 listed 2020–2021. |
| C34 | Total MWe | 30 | 30 | At threshold. Retain with note "borderline." |
| C56 | Fuel | Coal (domestic) | Coal (anthracite) | Quang Ninh anthracite mine-mouth. |
| G01 | Total MWe | 1,118 | 1,090 | EA18 shows 1,118 but EA11 shows 1,090. Use nameplate from EA11; EA18 figure may include uprating. Note discrepancy. |
| G11 | Fuel | Gas/Oil | Oil → Gas (Lo B) | Currently operates on oil/DO. PDP8 T5 designates conversion to Lo B gas. Status should note "Operating on oil; pending gas conversion." |
| G13 | Total MWe | 113 | 113 | EA18 shows 113 MW GT. EA11 showed 128 MW. Use EA18 as more recent. |
| L19 | — | — | DELETE | Duplicate of L22 above. Consolidate as L19 at 1,500 MW. |

### Capacity reconciliation summary (as-of May 2026)

| Category | Count | Total MW |
|----------|-------|---------|
| Coal — Operating | 34 plants/phases (C01–C34) | ~25,340 |
| Coal — Under Construction | 6 (C35–C40) | 6,125 |
| Coal — Shelved | 5 (C41–C45) | 7,220 |
| Coal — Cancelled | 10 (C46–C55) | 14,560 |
| Coal — Retired | 1 (C56) | 105 |
| Coal — Industrial/Cogen (operating + announced) | 6 (C57–C63) | ~3,010 |
| Domestic Gas — Operating | 13 (G01–G13) | ~7,909 |
| Domestic Gas — Permitted/Announced | 9 (G14–G22) | 7,240 |
| Domestic Gas — Cancelled | 1 (G23) | 1,500 |
| LNG — Operating | 2 (L01–L02) | 1,624 |
| LNG — Construction | 1 (L03) | 1,600 |
| LNG — Permitted/Pre-permit | 3 (L04–L05, L07) | 4,950 |
| LNG — Announced | 13 (L08–L21) | 24,400 |
| Oil-fired — Operating | 2 (O01–O02) | 540 |

**Cross-check:** Coal operating total ~25,340 MW (excluding cogen ~1,060 MW operating) is broadly consistent with GEM/Carbon Brief's ~27.2 GW figure for mid-2024 when adding cogen and accounting for minor capacity variations between nameplate and net ratings. The ~2 GW gap likely reflects (a) Formosa Ha Tinh Ph.1 ~550 MW and Formosa Dong Nai 150 MW included in national statistics, (b) minor upratings across the fleet, and (c) possible inclusion of Na Duong 2 (110 MW, construction) in some tallies.

**As-of date:** All status assessments current to May 2026 based on PDP8 (Decision 500, May 2023), Revised PDP8 (Decision 768, April 2025), and web-sourced updates through May 2026.