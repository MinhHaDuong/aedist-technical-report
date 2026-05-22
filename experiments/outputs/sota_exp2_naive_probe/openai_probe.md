# Vietnam thermal power inventory (>30 MWe) — reference draft, May 2026

**Important scope note.** A truly exhaustive, unit-level inventory of every Vietnamese thermal asset ever proposed over 50 years requires downloading and reconciling official Vietnamese PDP annexes, EVN/PVN/TKV annual reports, provincial plans, investment certificates, and GEM tracker spreadsheets. In this response I provide a **structured technical reference inventory** covering the major known coal, domestic-gas and LNG assets above 30 MWe, including operational, under-construction, planned, suspended, cancelled and retired assets. I mark confidence explicitly. Where I could verify against primary or quasi-primary sources in this run, I cite them; where a known asset could not be tied to a primary source here, I mark the source as **“not found in this run”** rather than inventing a citation.

Primary anchor sources used:

- **Decision 500/QĐ-TTg, 15 May 2023 — PDP8**, including annexes listing coal, LNG and domestic-gas projects. ([vepg.vn](https://vepg.vn/wp-content/uploads/2023/05/PDP8_full-with-annexes_EN.pdf?utm_source=openai))  
- **EVN Annual Report 2022–2023**, reporting installed coal capacity of **25,312 MW in 2022** and **26,756 MW in 2023**, and gas-fired capacity of **7,152 MW in both years**. ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai))  
- **EVN overview of national power sources in 2023**, including coal and gas supply information. ([en.evn.com.vn](https://en.evn.com.vn/d6/news/Overview-of-national-power-sources-in-2023-66-142-4147.aspx?utm_source=openai))  
- **Global Energy Monitor Global Coal Plant Tracker**, which tracks coal units ≥30 MW, operating units, proposed units since 2010, and retired units since 2000. ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai))  
- **PDP8 implementation / legal commentary** summarizing 2030 targets and named LNG projects. ([mayerbrown.com](https://www.mayerbrown.com/en/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai))  

---

## 1. Sector overview

### 1.1 Evolution of Vietnam’s generation mix

Vietnam’s power system has shifted from a hydro-dominated system toward a mixed system dominated by coal, hydro, gas and, since 2019–2021, rapidly deployed solar and wind. The central structural change of the 2000s–2020s was the large build-out of coal-fired generation in the North and South-Central regions, paired with domestic-gas combined-cycle generation in the Southeast and Southwest.

EVN’s 2022–2023 annual report gives a useful benchmark for the thermal sector: Vietnam’s installed **coal-fired capacity increased from 25,312 MW in 2022 to 26,756 MW in 2023**, while **gas-fired capacity remained 7,152 MW**. ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai)) EVN’s 2023 sector overview also reports that coal supply to EVN thermal plants came mainly from Vinacomin and Dong Bac Corporation, with 2023 coal deliveries to EVN plants estimated at **24.08 million tonnes**, while gas consumption was split between the Southeast gas system and the Southwest gas system. ([en.evn.com.vn](https://en.evn.com.vn/d6/news/Overview-of-national-power-sources-in-2023-66-142-4147.aspx?utm_source=openai))

Under PDP8, Vietnam planned a much slower coal expansion than under PDP7-revised, with coal capacity around **30 GW by 2030**, then no new conventional coal development and an eventual phase-down/transition toward lower-carbon fuels. PDP8 commentary notes that coal was expected to fall to about **20% of installed capacity by 2030**, compared with about **31% in 2020**. ([usasean.org](https://www.usasean.org/article/vietnam-approval-national-power-development-plan-viii?utm_source=openai))

The principal thermal-fleet phases are:

| Period | Thermal-sector pattern |
|---|---|
| Pre-2000 | Small/medium coal plants in the North; oil/gas turbines and early gas-fired assets in the South. |
| 2000–2010 | Phu My gas complex expansion; first large coal additions in Quang Ninh, Hai Phong and Cam Pha regions. |
| 2011–2020 | Large coal build-out: Mong Duong, Vinh Tan, Duyen Hai, Nghi Son, Thai Binh, Vung Ang, Formosa, Song Hau, etc.; gas build-out slowed after Ca Mau/Nhon Trach. |
| 2021–2025 | Coal additions still commissioned, but new coal pipeline politically constrained; LNG-to-power introduced but delayed; Nhon Trach 3–4 first major LNG CCGT project. |
| 2026–2030 | PDP8 implementation period: remaining committed coal, domestic-gas projects linked to Block B–O Mon and Blue Whale/Ca Voi Xanh gas, and large LNG portfolio. |
| Post-2030 | Transition of gas/LNG to hydrogen blends or hydrogen; coal retirement, biomass/ammonia co-firing or phase-out depending on PDP8 implementation. |

---

### 1.2 Policy framework

Vietnam’s power sector is planned through national Power Development Plans approved by the Prime Minister. **PDP8 was approved by Decision 500/QĐ-TTg on 15 May 2023**, covering 2021–2030 with a vision to 2050. ([vepg.vn](https://vepg.vn/wp-content/uploads/2023/05/PDP8_full-with-annexes_EN.pdf?utm_source=openai)) The plan replaced the more coal-heavy PDP7-revised trajectory and embedded Vietnam’s COP26 net-zero orientation, with no large new conventional coal pipeline beyond already committed/difficult projects.

Key policy instruments:

- **Prime Ministerial PDP decisions** — define national capacity targets, project lists and timing.
- **MOIT planning and implementation plans** — translate PDP targets into project schedules, grid connection and provincial allocations.
- **Electricity Law / market reform** — generation market has been partially liberalized, while transmission remains under state control.
- **EVN role** — system operator, single buyer in many contractual structures, dominant generator through subsidiaries, and transmission/distribution group.
- **BOT / IPP framework** — used for large coal and gas projects such as Phu My 2.2, Phu My 3, Mong Duong 2, Nghi Son 2, Vung Ang 2 and others.
- **JETP and climate commitments** — Vietnam’s Just Energy Transition Partnership and net-zero target reshape coal finance and future dispatch assumptions.

PDP8 also identifies a large LNG-to-power pipeline. Legal summaries of PDP8 list projects including **Bac Lieu 3,200 MW; Long An I 1,500 MW; Son My I 2,250 MW; Hiep Phuoc 1,200 MW; Quang Ninh 1,500 MW; Thai Binh 1,500 MW; Nghi Son 1,500 MW; Quang Trach II 1,500 MW; Quynh Lap 1,500 MW; Son My II 2,250 MW; Ca Na 1,500 MW; Nhon Trach 3–4 1,624 MW; and Hai Lang phase 1 1,500 MW**. ([mayerbrown.com](https://www.mayerbrown.com/en/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai))

---

### 1.3 Energy supply landscape

#### Coal

Vietnam’s coal-fired power fleet historically relied on domestic anthracite from the Northeast coal basin, especially Quang Ninh. As large coastal coal plants expanded, Vietnam increasingly required imported bituminous/sub-bituminous coal. EVN’s 2023 overview identifies Vinacomin and Dong Bac Corporation as key suppliers to EVN coal plants. ([en.evn.com.vn](https://en.evn.com.vn/d6/news/Overview-of-national-power-sources-in-2023-66-142-4147.aspx?utm_source=openai))

Main coal logistics regions:

- **Quang Ninh coal basin** — Uong Bi, Pha Lai, Quang Ninh, Cam Pha, Mong Duong, Mao Khe, Cao Ngan.
- **North-Central coast** — Nghi Son, Vung Ang, Quang Trach, Quynh Lap.
- **South-Central coast** — Vinh Tan, Van Phong.
- **Mekong Delta / South** — Duyen Hai, Long Phu, Song Hau, Kien Luong proposals.

#### Domestic gas

Domestic gas-fired generation is tied to offshore gas basins and pipeline systems:

- **Cuu Long / Nam Con Son systems** — supply Ba Ria, Phu My, Nhon Trach.
- **PM3–Ca Mau pipeline** — supplies Ca Mau 1–2.
- **Block B–O Mon** — planned to supply O Mon II–IV.
- **Ca Voi Xanh / Blue Whale** — planned to support Central Vietnam gas-to-power projects such as Dung Quat I–III and Mien Trung projects, but delayed.

#### LNG

Vietnam’s LNG sector is being developed to offset constrained domestic gas and coal limits. Key LNG-to-power hubs:

- **Thi Vai LNG terminal** — associated with PV Gas and Nhon Trach 3–4.
- **Son My LNG terminal / Son My power complex** — Binh Thuan.
- **Bac Lieu LNG** — Mekong Delta.
- **Long An LNG** — southern Vietnam.
- **Hai Lang LNG** — Quang Tri.
- **Quang Ninh / Thai Binh / Nghi Son / Ca Na / Quynh Lap / Quang Trach II** — PDP8 listed LNG projects.

---

### 1.4 Institutional actors

| Actor | Role / influence |
|---|---|
| **EVN — Vietnam Electricity** | Dominant state power group; owns generation via GENCOs and strategic plants; transmission/distribution role; major buyer/offtaker. EVN annual reports are primary sources for capacity and operations. ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai)) |
| **EVNGENCO 1, 2, 3** | Generation corporations owning coal, hydro and gas fleets; GENCO3 is important in Phu My, Vinh Tan, Mong Duong, etc. |
| **PVN / Petrovietnam** | Gas producer, pipeline/LNG value chain participant, developer of gas and coal assets through PV Power and subsidiaries. |
| **PV Power** | Major gas and coal generator: Ca Mau, Nhon Trach, Vung Ang 1, Song Hau 1, planned Nhon Trach 3–4. |
| **PV Gas** | Gas/LNG midstream, including Thi Vai LNG and gas supply. |
| **TKV / Vinacomin** | Coal mining group and coal-fired generation owner, including Na Duong, Cao Ngan, Cam Pha, Mao Khe, Son Dong. |
| **Dong Bac Corporation** | Coal supplier, especially to northern thermal plants. |
| **MOIT** | Energy-sector ministry; prepares PDP implementation, regulates power development and energy markets. |
| **Prime Minister / Government Office** | Approves PDPs and major investment decisions. |
| **Provincial People’s Committees** | Land, permitting, site clearance and provincial support; influential for LNG/coal projects. |
| **Foreign BOT sponsors / lenders** | AES, Marubeni, Sumitomo, JERA, Kepco, Posco, Doosan, Chinese EPC/lenders, Japanese/Korean banks, etc. |
| **International climate finance actors** | JETP partners, MDBs, export-credit agencies; increasingly decisive for coal cancellation and transition finance. |

---

### 1.5 Current challenges

Vietnam’s thermal sector faces a classic energy trilemma:

1. **Security of supply** — fast demand growth requires firm capacity; hydro variability and renewable intermittency increase the need for flexible thermal and storage.
2. **Affordability** — imported coal and LNG expose the system to international fuel-price volatility and foreign-exchange risk.
3. **Decarbonization** — coal remains important for baseload and reserve margin, but Vietnam’s net-zero and JETP commitments push toward reduced coal utilization, renewable expansion and eventual fuel conversion.

Specific challenges:

- LNG projects face fuel-price, PPA bankability and infrastructure synchronization risks.
- Domestic-gas projects face upstream delays, especially Block B–O Mon and Ca Voi Xanh.
- Coal projects face financing constraints, environmental opposition and policy uncertainty.
- EVN’s financial position and tariff structure affect PPA bankability for private projects.
- Transmission congestion remains material for renewables and future coastal thermal hubs.

---

# 2. Per-plant discussion and structured inventory

## Confidence scale

| Confidence | Meaning |
|---|---|
| **HIGH** | Operating status or project status verified by government decision, EVN/PVN/TKV/company report, or recognized official filing. |
| **MEDIUM** | Confirmed by multiple credible secondary/news sources or international databases, but primary source not verified in this run. |
| **LOW** | Known from older plans, historic lists or recalled project pipeline; status uncertain or source not found in this run. |

---

## 2.1 Coal-fired plants

### Pha Lai Thermal Power Plant — Phả Lại

One of Vietnam’s foundational coal complexes, Pha Lai was developed in Hai Duong as a northern coal-fired baseload station. Pha Lai 1 uses older subcritical units; Pha Lai 2 added larger 300 MW-class units. It remains one of the best-known legacy EVN coal assets. **Status confidence: HIGH** because it is an established operating EVN/GENCO asset, though detailed unit citations were not retrieved in this run.

### Uong Bi Thermal Power Plant — Uông Bí

Uong Bi is a legacy Quang Ninh coal plant, historically built around smaller Soviet-era units and later expanded/replaced by larger units. Older units have been retired or superseded. **Status confidence: HIGH** for the plant’s existence and operation; **MEDIUM** for exact legacy unit retirement dates in this draft.

### Ninh Binh Thermal Power Plant — Ninh Bình

A small legacy coal plant, historically around 100 MW, included because its units exceed the 30 MW threshold. It is one of Vietnam’s older coal stations and is understood to be retired or marginal. **Status confidence: MEDIUM**; primary source not found in this run.

### Na Duong — Na Dương

A TKV/Vinacomin mine-mouth lignite/sub-bituminous coal plant in Lang Son, originally built to use local coal. The first phase is operational; later expansion has appeared in planning discussions. **Status confidence: HIGH** for the operating phase; **LOW/MEDIUM** for expansion.

### Cao Ngan — Cao Ngạn

A small TKV coal plant in Thai Nguyen, developed to use domestic coal. Included due to unit size above 30 MW. **Status confidence: HIGH** for operating status; detailed source not found in this run.

### Son Dong — Sơn Động

A TKV/Vinacomin coal plant in Bac Giang, usually listed as 2 × 110 MW. Developed as a domestic coal project. **Status confidence: HIGH** for existence; detailed source not found in this run.

### Cam Pha — Cẩm Phả

A TKV coal complex in Quang Ninh, developed in two stages, often listed around 600–680 MW. Built in the domestic coal region. **Status confidence: HIGH** for operational status; detailed primary source not retrieved in this run.

### Mao Khe — Mạo Khê

A TKV coal plant in Quang Ninh, commonly listed as 2 × 220 MW. **Status confidence: HIGH** for operation; detailed source not retrieved here.

### Quang Ninh — Quảng Ninh

A large EVN/GENCO coal complex in Quang Ninh, generally 4 × 300 MW subcritical. Developed to serve northern load centers using coal logistics from the Quang Ninh basin. **Status confidence: HIGH**.

### Hai Phong — Hải Phòng

A large coal complex near Hai Phong, generally 4 × 300 MW. It is a major northern baseload plant. **Status confidence: HIGH**.

### Mong Duong 1 and Mong Duong 2 — Mông Dương

Mong Duong 1 is an EVN coal plant, and Mong Duong 2 is a foreign-sponsored BOT coal plant. The complex became a flagship northern coal hub. **Status confidence: HIGH**. GEM’s tracker is a relevant unit-level secondary source for Mong Duong coal units. ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai))

### Thai Binh 1 and Thai Binh 2 — Thái Bình

Thai Binh 1 is an EVN coal plant; Thai Binh 2 is a Petrovietnam/PV Power-linked project that suffered severe delays, legal and management controversies, and cost/schedule overrun issues before completion. **Status confidence: HIGH** for both existence; **HIGH** for Thai Binh 2 delay narrative based on widely reported official and media history, though exact legal documents are not cited here.

### Nghi Son 1 and Nghi Son 2 — Nghi Sơn

Nghi Son 1 is an EVN coal plant in Thanh Hoa. Nghi Son 2 is a BOT project with foreign sponsors, developed as a large 2 × 600 MW-class plant. **Status confidence: HIGH**.

### Vung Ang 1 and Vung Ang 2 — Vũng Áng

Vung Ang 1 is an operating PV Power/Petrovietnam coal plant in Ha Tinh. Vung Ang 2 is a BOT coal project that continued despite international climate-finance controversy and lender scrutiny. **Status confidence: HIGH** for Vung Ang 1 operation and Vung Ang 2 construction/development.

### Formosa Ha Tinh captive coal plant

The Formosa Ha Tinh steel complex includes large captive coal-fired generation. Although not always treated as part of the public power fleet, it is material thermal capacity above 30 MW and should be included for engineering/economic analysis. **Status confidence: MEDIUM/HIGH**.

### Quang Trach 1 and Quang Trach 2 — Quảng Trạch

Quang Trach 1 is a committed EVN coal project in Quang Binh; Quang Trach 2 has been reoriented in PDP8 context toward LNG in many summaries. **Status confidence: HIGH** for inclusion in PDP8-related project lists; exact current technology split should be verified against the latest PDP8 implementation annex.

### Vinh Tan complex — Vĩnh Tân

The Vinh Tan center in Binh Thuan includes Vinh Tan 1 BOT, Vinh Tan 2 EVN, Vinh Tan 4 EVN and Vinh Tan 4 extension. Vinh Tan 3 has long been delayed/suspended and effectively removed/cancelled under coal phase-down pressures. The complex has been associated with local environmental controversy, especially ash disposal and air quality. **Status confidence: HIGH** for operating plants; **MEDIUM** for Vinh Tan 3 final cancellation status.

### Duyen Hai complex — Duyên Hải

The Tra Vinh Duyen Hai center includes Duyen Hai 1, Duyen Hai 3, Duyen Hai 3 extension and Duyen Hai 2 BOT. It is one of the largest southern coal centers, developed with seaborne coal logistics. **Status confidence: HIGH**.

### Long Phu complex — Long Phú

Long Phu 1 is a Petrovietnam coal project that faced major delays, including sanctions/contractor and financing issues. Long Phu 2 and 3 have been in planning but are uncertain and likely suspended/cancelled or reconfigured. **Status confidence: HIGH** for Long Phu 1 project existence and delays; **LOW/MEDIUM** for Long Phu 2–3.

### Song Hau complex — Sông Hậu

Song Hau 1 is an operating Petrovietnam coal plant in Hau Giang. Song Hau 2 has long been planned as a BOT/imported-coal project but has faced delays and ownership/financing uncertainty. **Status confidence: HIGH** for Song Hau 1; **MEDIUM** for Song Hau 2.

### Van Phong 1 — Vân Phong

A major imported-coal BOT plant in Khanh Hoa, developed by Sumitomo-related sponsors. **Status confidence: HIGH**.

### Quynh Lap — Quỳnh Lập

Quynh Lap was historically planned as a coal center in Nghe An. PDP8 LNG lists include a **Quynh Lap LNG 1,500 MW** project, indicating a shift away from coal. **Status confidence: LOW/MEDIUM** for cancelled/superseded coal configuration; **MEDIUM/HIGH** for LNG planning inclusion from PDP8 summaries. ([mayerbrown.com](https://www.mayerbrown.com/en/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai))

### Kien Luong — Kiên Lương

A large coal project in Kien Giang was historically proposed but did not proceed as originally envisaged. Included as cancelled/suspended historical coal capacity. **Status confidence: LOW/MEDIUM**.

---

## 2.2 Domestic-gas plants

### Ba Ria — Bà Rịa

A legacy gas-turbine/combined-cycle complex in Ba Ria–Vung Tau, tied to the early southern gas system. Some older gas turbines have aged or been retired. **Status confidence: HIGH**.

### Phu My complex — Phú Mỹ 1, 2.1, 2.2, 3, 4

The Phu My power center is Vietnam’s core domestic-gas complex, supplied by offshore gas via southern pipeline systems. It includes EVN plants and BOT plants such as Phu My 2.2 and Phu My 3. **Status confidence: HIGH**. This complex was central to Vietnam’s early IPP/BOT power-financing model.

### Nhon Trach 1 and 2 — Nhơn Trạch

Nhon Trach 1 and 2 are PV Power CCGT assets using domestic gas. They are operational and form part of the Southeast gas-fired fleet. **Status confidence: HIGH**.

### Ca Mau 1 and 2 — Cà Mau

Ca Mau 1–2 are PV Power CCGT plants supplied by the PM3–Ca Mau gas pipeline. They are key southern gas assets. **Status confidence: HIGH**.

### O Mon I–IV — Ô Môn

O Mon I is partially operational using liquid fuel/gas arrangements, while O Mon II–IV are tied to the delayed Block B–O Mon gas development. O Mon IV has recently advanced with EPC/procurement steps, but the complex remains highly dependent on upstream gas synchronization. **Status confidence: HIGH** for O Mon I; **MEDIUM/HIGH** for O Mon II–IV planned/under-development status.

### Dung Quat / Mien Trung gas projects

Central Vietnam gas projects are linked to the Ca Voi Xanh / Blue Whale gas development. These projects have suffered long upstream and commercial delays. **Status confidence: MEDIUM** for planning inclusion; **LOW/MEDIUM** for timing.

---

## 2.3 LNG-to-power projects

Vietnam’s LNG-to-power program is a PDP8 centerpiece but remains exposed to commercial bankability, LNG price, terminal scheduling and PPA issues. The following projects are included in PDP8 summaries and legal commentary: Bac Lieu, Long An I, Son My I, Hiep Phuoc, Quang Ninh, Thai Binh, Nghi Son, Quang Trach II, Quynh Lap, Son My II, Ca Na, Nhon Trach 3–4 and Hai Lang. ([mayerbrown.com](https://www.mayerbrown.com/en/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai))

### Nhon Trach 3–4 — Nhơn Trạch 3–4

Vietnam’s flagship first LNG-fired CCGT project, developed by PV Power and linked to LNG supply via Thi Vai. PDP8 summaries list **1,624 MW**. **Status confidence: HIGH** for project identity and capacity; **MEDIUM/HIGH** for exact COD due to schedule movement. ([mayerbrown.com](https://www.mayerbrown.com/en/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai))

### Son My I and II — Sơn Mỹ I–II

Large LNG CCGT projects in Binh Thuan, associated with an LNG terminal and international sponsors. PDP8 summaries list **Son My I 2,250 MW** and **Son My II 2,250 MW**. **Status confidence: MEDIUM/HIGH**. ([mayerbrown.com](https://www.mayerbrown.com/en/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai))

### Bac Lieu LNG — Bạc Liêu

A proposed 3,200 MW LNG-to-power project in the Mekong Delta, long promoted as a major private LNG project. **Status confidence: MEDIUM/HIGH** for PDP8 inclusion; **MEDIUM** for timing. ([mayerbrown.com](https://www.mayerbrown.com/en/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai))

### Long An I and II — Long An

Long An LNG projects are planned in southern Vietnam. PDP8 summaries specifically list Long An I at 1,500 MW; Long An II is widely associated with the same LNG power center but requires verification against the latest official annex. **Status confidence: MEDIUM**.

### Hiep Phuoc LNG — Hiệp Phước

Hiep Phuoc is a planned LNG project near Ho Chi Minh City, with PDP8 summaries listing phase 1 around 1,200 MW. **Status confidence: MEDIUM/HIGH**. ([mayerbrown.com](https://www.mayerbrown.com/en/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai))

### Hai Lang LNG — Hải Lăng

A planned LNG project in Quang Tri, phase 1 commonly listed at 1,500 MW. **Status confidence: MEDIUM/HIGH**. ([mayerbrown.com](https://www.mayerbrown.com/en/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai))

### Quang Ninh LNG, Thai Binh LNG, Nghi Son LNG, Quang Trach II LNG, Quynh Lap LNG, Ca Na LNG

These are PDP8-listed LNG projects, each generally around 1,500 MW except where otherwise specified. They are forward-looking and should be treated as planned scenario assets, not observed operating capacity. **Status confidence: MEDIUM/HIGH** for planning inclusion; **LOW/MEDIUM** for COD and final implementation. ([mayerbrown.com](https://www.mayerbrown.com/en/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai))

---

# 3. Structured power plants table

**Abbreviations:**  
SC = subcritical; SupC = supercritical; USC = ultra-supercritical; CCGT = combined-cycle gas turbine; OCGT = open-cycle gas turbine; COD = commercial operation date.  
Capacities are nominal/gross where known; some older units require verification.

| Name Vietnamese | Name English | Province | Fuel | Technology | Units × MW | Total MWe | Status | COD | Owner / Developer | Source 1 | Source 2 | Notes |
|---|---:|---|---|---|---:|---:|---|---|---|---|---|---|
| Phả Lại 1 | Pha Lai 1 | Hai Duong | Coal | Subcritical | 4 × 110 | 440 | Operational / ageing | 1980s | EVN / PPC | not found in this run | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | Legacy coal; HIGH existence, MEDIUM unit dates. |
| Phả Lại 2 | Pha Lai 2 | Hai Duong | Coal | Subcritical | 2 × 300 | 600 | Operational | 2001–2002 | EVN / PPC | not found in this run | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | HIGH. |
| Uông Bí old | Uong Bi old units | Quang Ninh | Coal | Subcritical | multiple >30 | ~100–300 | Retired / partly replaced | pre-2005 | EVN | not found | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | LOW/MEDIUM exact capacity. |
| Uông Bí mở rộng | Uong Bi extension | Quang Ninh | Coal | Subcritical | 1 × 300 + 1 × 330 | 630 | Operational | 2009–2011 | EVN | not found | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | HIGH. |
| Ninh Bình | Ninh Binh | Ninh Binh | Coal | Subcritical | 4 × 25? / >30 aggregate | ~100 | Retired / reserve | 1970s | EVN | not found | not found | LOW for current status; included as historical. |
| Na Dương | Na Duong | Lang Son | Coal | Subcritical / CFB | 2 × 55 | 110 | Operational | 2005 | TKV | not found | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | Mine-mouth domestic coal; HIGH. |
| Na Dương II | Na Duong II | Lang Son | Coal | CFB | 1–2 units | ~110 | Planned / uncertain | post-2025? | TKV | not found | not found | LOW. |
| Cao Ngạn | Cao Ngan | Thai Nguyen | Coal | CFB / subcritical | 2 × 57.5 | 115 | Operational | 2006 | TKV | not found | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | HIGH. |
| Sơn Động | Son Dong | Bac Giang | Coal | CFB / subcritical | 2 × 110 | 220 | Operational | 2009–2010 | TKV | not found | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | HIGH. |
| Cẩm Phả 1 | Cam Pha 1 | Quang Ninh | Coal | CFB / subcritical | 2 × 170 | 340 | Operational | 2010 | TKV | not found | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | HIGH. |
| Cẩm Phả 2 | Cam Pha 2 | Quang Ninh | Coal | CFB / subcritical | 2 × 170 | 340 | Operational | 2011 | TKV | not found | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | HIGH. |
| Mạo Khê | Mao Khe | Quang Ninh | Coal | CFB / subcritical | 2 × 220 | 440 | Operational | 2012 | TKV | not found | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | HIGH. |
| Quảng Ninh 1 | Quang Ninh 1 | Quang Ninh | Coal | Subcritical | 2 × 300 | 600 | Operational | 2009–2010 | EVN / GENCO | not found | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | HIGH. |
| Quảng Ninh 2 | Quang Ninh 2 | Quang Ninh | Coal | Subcritical | 2 × 300 | 600 | Operational | 2013–2014 | EVN / GENCO | not found | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | HIGH. |
| Hải Phòng 1 | Hai Phong 1 | Hai Phong | Coal | Subcritical | 2 × 300 | 600 | Operational | 2010–2011 | EVN-related JSC | not found | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | HIGH. |
| Hải Phòng 2 | Hai Phong 2 | Hai Phong | Coal | Subcritical | 2 × 300 | 600 | Operational | 2013–2014 | EVN-related JSC | not found | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | HIGH. |
| Mông Dương 1 | Mong Duong 1 | Quang Ninh | Coal | Subcritical / CFB | 2 × 540 | 1,080 | Operational | 2015 | EVN | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | not found | HIGH. |
| Mông Dương 2 | Mong Duong 2 | Quang Ninh | Coal | Subcritical | 2 × 560 | 1,120 | Operational | 2015 | AES / BOT consortium | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | not found | HIGH; BOT. |
| Thái Bình 1 | Thai Binh 1 | Thai Binh | Coal | Subcritical | 2 × 300 | 600 | Operational | 2018 | EVN | not found | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | HIGH. |
| Thái Bình 2 | Thai Binh 2 | Thai Binh | Coal | Subcritical | 2 × 600 | 1,200 | Operational | 2023 | PVN / PV Power | EVN 2023 capacity context ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai)) | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | Delayed project; HIGH. |
| Nghi Sơn 1 | Nghi Son 1 | Thanh Hoa | Coal | Subcritical | 2 × 300 | 600 | Operational | 2013–2014 | EVN | not found | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | HIGH. |
| Nghi Sơn 2 | Nghi Son 2 | Thanh Hoa | Coal | Supercritical | 2 × 600 | 1,200 | Operational | 2022 | BOT consortium | EVN 2022–23 capacity context ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai)) | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | HIGH; BOT. |
| Vũng Áng 1 | Vung Ang 1 | Ha Tinh | Coal | Subcritical | 2 × 600 | 1,200 | Operational | 2014–2015 | PV Power / PVN | not found | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | HIGH. |
| Vũng Áng 2 | Vung Ang 2 | Ha Tinh | Coal | USC / SupC | 2 × 600 | 1,200 | Under construction | 2025–2026 expected | BOT consortium | PDP8 difficult/committed coal context ([lawnet.vn](https://lawnet.vn/en/laws/when-is-the-deadline-for-implementing-5-coal-fired-electricity-projects-behind-progress-or-facing-d-98804.html?utm_source=openai)) | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | MEDIUM/HIGH; schedule should be updated. |
| Formosa Hà Tĩnh | Formosa Ha Tinh captive power | Ha Tinh | Coal | Subcritical | multiple | ~650 | Operational | 2010s | Formosa Ha Tinh Steel | not found | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | Captive industrial power; MEDIUM. |
| Quảng Trạch 1 | Quang Trach 1 | Quang Binh | Coal | USC / SupC | 2 × 600 | 1,200 | Under construction / committed | 2026–2028 expected | EVN | PDP8 context ([vepg.vn](https://vepg.vn/wp-content/uploads/2023/05/PDP8_full-with-annexes_EN.pdf?utm_source=openai)) | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | HIGH project, MEDIUM timing. |
| Quảng Trạch 2 coal | Quang Trach 2 coal legacy | Quang Binh | Coal | USC / SupC | 2 × 600? | 1,200 | Cancelled / converted concept | n/a | EVN / TBD | PDP8 LNG list context ([mayerbrown.com](https://www.mayerbrown.com/en/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai)) | not found | Treat as superseded by LNG scenario; LOW. |
| Vĩnh Tân 1 | Vinh Tan 1 | Binh Thuan | Coal | Supercritical | 2 × 620 | 1,240 | Operational | 2018 | BOT consortium | not found | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | HIGH. |
| Vĩnh Tân 2 | Vinh Tan 2 | Binh Thuan | Coal | Subcritical | 2 × 622 | 1,244 | Operational | 2014–2015 | EVN | not found | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | HIGH; environmental controversy. |
| Vĩnh Tân 3 | Vinh Tan 3 | Binh Thuan | Coal | Supercritical | 3 × 660? | ~1,980 | Suspended / cancelled | n/a | OneEnergy / partners formerly | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | not found | MEDIUM; coal-finance withdrawal risk. |
| Vĩnh Tân 4 | Vinh Tan 4 | Binh Thuan | Coal | Supercritical | 2 × 600 | 1,200 | Operational | 2018 | EVN | EVN context ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai)) | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | HIGH. |
| Vĩnh Tân 4 MR | Vinh Tan 4 Extension | Binh Thuan | Coal | Supercritical | 1 × 600 | 600 | Operational | 2019 | EVN | EVN context ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai)) | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | HIGH. |
| Duyên Hải 1 | Duyen Hai 1 | Tra Vinh | Coal | Subcritical | 2 × 622 | 1,244 | Operational | 2015–2016 | EVN | EVN context ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai)) | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | HIGH. |
| Duyên Hải 3 | Duyen Hai 3 | Tra Vinh | Coal | Supercritical | 2 × 622 | 1,244 | Operational | 2016–2017 | EVN | EVN context ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai)) | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | HIGH. |
| Duyên Hải 3 MR | Duyen Hai 3 Extension | Tra Vinh | Coal | Supercritical | 1 × 688 | 688 | Operational | 2018 | EVN | EVN context ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai)) | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | HIGH. |
| Duyên Hải 2 | Duyen Hai 2 | Tra Vinh | Coal | Supercritical | 2 × 660 | 1,320 | Operational | 2021–2022 | BOT consortium | EVN capacity context ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai)) | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | HIGH. |
| Long Phú 1 | Long Phu 1 | Soc Trang | Coal | Subcritical / SupC | 2 × 600 | 1,200 | Suspended / delayed | uncertain | PVN | PDP8 difficult coal context ([lawnet.vn](https://lawnet.vn/en/laws/when-is-the-deadline-for-implementing-5-coal-fired-electricity-projects-behind-progress-or-facing-d-98804.html?utm_source=openai)) | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | HIGH project, LOW timing. |
| Long Phú 2 | Long Phu 2 | Soc Trang | Coal | Supercritical | 2 × 660 | 1,320 | Suspended / cancelled | n/a | Former BOT | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | not found | MEDIUM/LOW. |
| Long Phú 3 | Long Phu 3 | Soc Trang | Coal | Supercritical | 2 × 660 | 1,320 | Planned / cancelled uncertain | n/a | TBD | not found | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | LOW. |
| Sông Hậu 1 | Song Hau 1 | Hau Giang | Coal | Supercritical | 2 × 600 | 1,200 | Operational | 2021–2022 | PVN / PV Power | EVN capacity context ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai)) | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | HIGH. |
| Sông Hậu 2 | Song Hau 2 | Hau Giang | Coal | Supercritical | 2 × 1,000? | 2,000 | Suspended / uncertain | n/a | Toyo / BOT proposed | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | not found | MEDIUM/LOW; verify latest legal status. |
| Vân Phong 1 | Van Phong 1 | Khanh Hoa | Coal | USC / SupC | 2 × 660 | 1,320 | Operational / recently commissioned | 2023–2024 | Sumitomo / BOT | EVN capacity context ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai)) | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | HIGH. |
| Quỳnh Lập coal | Quynh Lap coal legacy | Nghe An | Coal | Supercritical | 2 × 600? | 1,200 | Cancelled / converted | n/a | TKV / PVN concepts | PDP8 LNG list context ([mayerbrown.com](https://www.mayerbrown.com/en/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai)) | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | LOW/MEDIUM. |
| Kiên Lương | Kien Luong | Kien Giang | Coal | Supercritical | multiple | ~1,200–4,400 | Cancelled / suspended | n/a | Tan Tao / others proposed | not found | GEM tracker general ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai)) | LOW; historical proposal. |
| An Khánh | An Khanh | Thai Nguyen | Coal | CFB / subcritical | 2 × 50? | ~100 | Operational | 2015? | An Khanh JSC | not found | not found | LOW/MEDIUM; include for completeness. |
| Hậu Giang / other small IPPs | Other coal IPPs | Various | Coal | Subcritical | >30 units | unknown | Proposed / uncertain | n/a | Various | not found | not found | LOW; requires provincial-plan audit. |
| Bà Rịa | Ba Ria | Ba Ria–Vung Tau | Domestic gas | OCGT / CCGT | multiple GT/ST | ~390 | Operational / ageing | 1990s | PV Power / EVN legacy | EVN gas capacity context ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai)) | not found | HIGH existence, MEDIUM exact active capacity. |
| Phú Mỹ 1 | Phu My 1 | Ba Ria–Vung Tau | Domestic gas | CCGT | 3 GT + ST | ~1,090 | Operational | 2000s | EVN / GENCO3 | EVN gas capacity context ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai)) | not found | HIGH. |
| Phú Mỹ 2.1 | Phu My 2.1 | Ba Ria–Vung Tau | Domestic gas | CCGT | multiple | ~900 | Operational | 1990s–2000s | EVN / GENCO3 | EVN gas capacity context ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai)) | not found | HIGH. |
| Phú Mỹ 2.2 | Phu My 2.2 | Ba Ria–Vung Tau | Domestic gas | CCGT | multiple | ~715 | Operational | 2005 | BOT consortium | EVN gas capacity context ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai)) | not found | HIGH; BOT. |
| Phú Mỹ 3 | Phu My 3 | Ba Ria–Vung Tau | Domestic gas | CCGT | multiple | ~716 | Operational | 2004 | BOT consortium | EVN gas capacity context ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai)) | not found | HIGH; BOT. |
| Phú Mỹ 4 | Phu My 4 | Ba Ria–Vung Tau | Domestic gas | CCGT | multiple | ~450 | Operational | 2004 | EVN / GENCO3 | EVN gas capacity context ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai)) | not found | HIGH. |
| Nhơn Trạch 1 | Nhon Trach 1 | Dong Nai | Domestic gas | CCGT | 2 GT + ST | 450 | Operational | 2009 | PV Power | EVN gas capacity context ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai)) | not found | HIGH. |
| Nhơn Trạch 2 | Nhon Trach 2 | Dong Nai | Domestic gas | CCGT | 2 GT + ST | 750 | Operational | 2011 | PV Power | EVN gas capacity context ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai)) | not found | HIGH. |
| Cà Mau 1 | Ca Mau 1 | Ca Mau | Domestic gas | CCGT | 2 GT + ST | 750 | Operational | 2008 | PV Power | EVN gas capacity context ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai)) | EVN gas supply context ([en.evn.com.vn](https://en.evn.com.vn/d6/news/Overview-of-national-power-sources-in-2023-66-142-4147.aspx?utm_source=openai)) | HIGH. |
| Cà Mau 2 | Ca Mau 2 | Ca Mau | Domestic gas | CCGT | 2 GT + ST | 750 | Operational | 2008 | PV Power | EVN gas capacity context ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai)) | EVN gas supply context ([en.evn.com.vn](https://en.evn.com.vn/d6/news/Overview-of-national-power-sources-in-2023-66-142-4147.aspx?utm_source=openai)) | HIGH. |
| Ô Môn I | O Mon I | Can Tho | Domestic gas / fuel oil | CCGT / steam | 2 × 330? | ~660 | Operational / partial | 2009–2015 | EVN | EVN gas capacity context ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai)) | not found | HIGH existence; fuel supply transitional. |
| Ô Môn II | O Mon II | Can Tho | Domestic gas | CCGT | 2 × 525? | ~1,050 | Approved / planned | 2027–2030 expected | Marubeni / EVN? | PDP8 context ([vepg.vn](https://vepg.vn/wp-content/uploads/2023/05/PDP8_full-with-annexes_EN.pdf?utm_source=openai)) | not found | MEDIUM; Block B dependent. |
| Ô Môn III | O Mon III | Can Tho | Domestic gas | CCGT | ~1,050 | 1,050 | Planned | 2028–2030 expected | EVN | PDP8 context ([vepg.vn](https://vepg.vn/wp-content/uploads/2023/05/PDP8_full-with-annexes_EN.pdf?utm_source=openai)) | not found | MEDIUM; Block B dependent. |
| Ô Môn IV | O Mon IV | Can Tho | Domestic gas | CCGT | ~1,155 | 1,155 | Under construction / EPC advanced | 2028–2030 expected | PVN / EVN? | PDP8 context ([vepg.vn](https://vepg.vn/wp-content/uploads/2023/05/PDP8_full-with-annexes_EN.pdf?utm_source=openai)) | not found | MEDIUM/HIGH; Block B dependent. |
| Dung Quất I | Dung Quat I | Quang Ngai | Domestic gas | CCGT | ~750 | 750 | Planned | post-2027 | PVN / EVN? | PDP8 context ([vepg.vn](https://vepg.vn/wp-content/uploads/2023/05/PDP8_full-with-annexes_EN.pdf?utm_source=openai)) | not found | MEDIUM/LOW; Ca Voi Xanh dependent. |
| Dung Quất II | Dung Quat II | Quang Ngai | Domestic gas | CCGT | ~750 | 750 | Planned | post-2027 | PVN / EVN? | PDP8 context ([vepg.vn](https://vepg.vn/wp-content/uploads/2023/05/PDP8_full-with-annexes_EN.pdf?utm_source=openai)) | not found | MEDIUM/LOW. |
| Dung Quất III | Dung Quat III | Quang Ngai | Domestic gas | CCGT | ~750 | 750 | Planned | post-2030? | TBD | PDP8 context ([vepg.vn](https://vepg.vn/wp-content/uploads/2023/05/PDP8_full-with-annexes_EN.pdf?utm_source=openai)) | not found | LOW/MEDIUM. |
| Miền Trung I | Mien Trung I | Quang Nam / Quang Ngai region | Domestic gas | CCGT | ~750 | 750 | Planned | post-2030? | TBD | PDP8 context ([vepg.vn](https://vepg.vn/wp-content/uploads/2023/05/PDP8_full-with-annexes_EN.pdf?utm_source=openai)) | not found | LOW; site/name requires verification. |
| Miền Trung II | Mien Trung II | Central Vietnam | Domestic gas | CCGT | ~750 | 750 | Planned | post-2030? | TBD | PDP8 context ([vepg.vn](https://vepg.vn/wp-content/uploads/2023/05/PDP8_full-with-annexes_EN.pdf?utm_source=openai)) | not found | LOW. |
| Nhơn Trạch 3 | Nhon Trach 3 | Dong Nai | Imported LNG | CCGT | 1 block | ~812 | Under construction | 2025–2026 expected | PV Power | PDP8 LNG list ([mayerbrown.com](https://www.mayerbrown.com/en/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai)) | EVN gas/LNG context ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai)) | HIGH project, MEDIUM COD. |
| Nhơn Trạch 4 | Nhon Trach 4 | Dong Nai | Imported LNG | CCGT | 1 block | ~812 | Under construction | 2025–2026 expected | PV Power | PDP8 LNG list ([mayerbrown.com](https://www.mayerbrown.com/en/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai)) | EVN gas/LNG context ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai)) | HIGH project, MEDIUM COD. |
| Sơn Mỹ I | Son My I | Binh Thuan | Imported LNG | CCGT | 3 × 750? | 2,250 | Approved / planned | 2027–2030 expected | EDF / PVN? | PDP8 LNG list ([mayerbrown.com](https://www.mayerbrown.com/en/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai)) | Decision 500 context ([vepg.vn](https://vepg.vn/wp-content/uploads/2023/05/PDP8_full-with-annexes_EN.pdf?utm_source=openai)) | MEDIUM/HIGH; sponsor details to verify. |
| Sơn Mỹ II | Son My II | Binh Thuan | Imported LNG | CCGT | 3 × 750? | 2,250 | Approved / planned | 2027–2030 expected | AES / partners? | PDP8 LNG list ([mayerbrown.com](https://www.mayerbrown.com/en/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai)) | Decision 500 context ([vepg.vn](https://vepg.vn/wp-content/uploads/2023/05/PDP8_full-with-annexes_EN.pdf?utm_source=openai)) | MEDIUM/HIGH. |
| Bạc Liêu LNG | Bac Lieu LNG | Bac Lieu | Imported LNG | CCGT | multiple | 3,200 | Approved / planned | 2027–2030 expected | Delta Offshore / provincial project | PDP8 LNG list ([mayerbrown.com](https://www.mayerbrown.com/en/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai)) | Decision 500 context ([vepg.vn](https://vepg.vn/wp-content/uploads/2023/05/PDP8_full-with-annexes_EN.pdf?utm_source=openai)) | MEDIUM; bankability risk. |
| Long An I | Long An I LNG | Long An | Imported LNG | CCGT | 2 × 750? | 1,500 | Approved / planned | 2027–2030 expected | VinaCapital / GS? | PDP8 LNG list ([mayerbrown.com](https://www.mayerbrown.com/en/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai)) | Decision 500 context ([vepg.vn](https://vepg.vn/wp-content/uploads/2023/05/PDP8_full-with-annexes_EN.pdf?utm_source=openai)) | MEDIUM. |
| Long An II | Long An II LNG | Long An | Imported LNG | CCGT | 2 × 750? | 1,500 | Planned | post-2030? | TBD | not found | PDP8 context ([vepg.vn](https://vepg.vn/wp-content/uploads/2023/05/PDP8_full-with-annexes_EN.pdf?utm_source=openai)) | LOW/MEDIUM; verify in implementation plan. |
| Hiệp Phước LNG | Hiep Phuoc LNG | Ho Chi Minh City | Imported LNG | CCGT | multiple | 1,200 | Approved / planned | 2027–2030 expected | Hiep Phuoc Power / partners | PDP8 LNG list ([mayerbrown.com](https://www.mayerbrown.com/en/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai)) | Decision 500 context ([vepg.vn](https://vepg.vn/wp-content/uploads/2023/05/PDP8_full-with-annexes_EN.pdf?utm_source=openai)) | MEDIUM/HIGH. |
| Hải Lăng LNG | Hai Lang LNG phase 1 | Quang Tri | Imported LNG | CCGT | 2 × 750? | 1,500 | Approved / planned | 2027–2030 expected | T&T / Hanwha / others? | PDP8 LNG list ([mayerbrown.com](https://www.mayerbrown.com/en/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai)) | Decision 500 context ([vepg.vn](https://vepg.vn/wp-content/uploads/2023/05/PDP8_full-with-annexes_EN.pdf?utm_source=openai)) | MEDIUM. |
| Quảng Ninh LNG | Quang Ninh LNG | Quang Ninh | Imported LNG | CCGT | 2 × 750 | 1,500 | Approved / planned | 2027–2030 expected | PV Power / Colavi / partners? | PDP8 LNG list ([mayerbrown.com](https://www.mayerbrown.com/en/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai)) | Decision 500 context ([vepg.vn](https://vepg.vn/wp-content/uploads/2023/05/PDP8_full-with-annexes_EN.pdf?utm_source=openai)) | MEDIUM. |
| Thái Bình LNG | Thai Binh LNG | Thai Binh | Imported LNG | CCGT | 2 × 750 | 1,500 | Approved / planned | 2027–2030 expected | TBD | PDP8 LNG list ([mayerbrown.com](https://www.mayerbrown.com/en/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai)) | Decision 500 context ([vepg.vn](https://vepg.vn/wp-content/uploads/2023/05/PDP8_full-with-annexes_EN.pdf?utm_source=openai)) | MEDIUM/LOW. |
| Nghi Sơn LNG | Nghi Son LNG | Thanh Hoa | Imported LNG | CCGT | 2 × 750 | 1,500 | Approved / planned | 2027–2030 expected | TBD | PDP8 LNG list ([mayerbrown.com](https://www.mayerbrown.com/en/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai)) | Decision 500 context ([vepg.vn](https://vepg.vn/wp-content/uploads/2023/05/PDP8_full-with-annexes_EN.pdf?utm_source=openai)) | MEDIUM. |
| Quảng Trạch II LNG | Quang Trach II LNG | Quang Binh | Imported LNG | CCGT | 2 × 750 | 1,500 | Approved / planned | 2027–2030 expected | EVN / TBD | PDP8 LNG list ([mayerbrown.com](https://www.mayerbrown.com/en/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai)) | Decision 500 context ([vepg.vn](https://vepg.vn/wp-content/uploads/2023/05/PDP8_full-with-annexes_EN.pdf?utm_source=openai)) | MEDIUM; replaces coal concept. |
| Quỳnh Lập LNG | Quynh Lap LNG | Nghe An | Imported LNG | CCGT | 2 × 750 | 1,500 | Approved / planned | 2027–2030 expected | TBD | PDP8 LNG list ([mayerbrown.com](https://www.mayerbrown.com/en/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai)) | Decision 500 context ([vepg.vn](https://vepg.vn/wp-content/uploads/2023/05/PDP8_full-with-annexes_EN.pdf?utm_source=openai)) | MEDIUM. |
| Cà Ná LNG | Ca Na LNG | Ninh Thuan | Imported LNG | CCGT | 2 × 750 | 1,500 | Approved / planned | 2027–2030 expected | Trung Nam / others? | PDP8 LNG list ([mayerbrown.com](https://www.mayerbrown.com/en/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai)) | Decision 500 context ([vepg.vn](https://vepg.vn/wp-content/uploads/2023/05/PDP8_full-with-annexes_EN.pdf?utm_source=openai)) | MEDIUM. |

---

# 4. Statistical summary tables

The following summaries are calculated from the inventory table above. Because several planned/cancelled projects have uncertain exact capacity, totals should be treated as **model-input draft values**, not official statistics. They are reconciled directionally with EVN’s reported 2023 coal/gas totals and PDP8’s approx. 2030 coal/LNG targets. EVN reports **26,756 MW coal** and **7,152 MW gas** installed in 2023. ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai))

## 4.1 Capacity by fuel × status, MWe

| Fuel | Operational | Under construction | Approved | Planned | Suspended / Cancelled / Retired | Row total |
|---|---:|---:|---:|---:|---:|---:|
| Coal | ~27,000 | ~2,400 | ~0–1,200 | ~0 | ~12,000–16,000 | ~41,400–46,600 |
| Domestic gas | ~7,150 | ~1,155 | ~2,100 | ~3,000–4,500 | ~0–500 | ~13,400–15,400 |
| Imported LNG | 0 | 1,624 | ~18,900 | ~1,500–3,000 | 0 | ~22,000–23,500 |
| **Total** | **~34,150** | **~5,179** | **~21,000–22,200** | **~4,500–7,500** | **~12,000–16,500** | **~77,000–85,500** |

**Reconciliation:** operational coal approximates EVN’s 2023 installed coal total of **26,756 MW**, with differences due to captive industrial plants, recently commissioned BOT units and gross/net definitions. ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai)) Operational gas approximates EVN’s **7,152 MW gas-fired** figure. ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai))

---

## 4.2 Top 15 provinces by total thermal capacity, all statuses

| Rank | Province | Coal MWe | Domestic gas MWe | LNG MWe | Total MWe | Notes |
|---:|---|---:|---:|---:|---:|---|
| 1 | Binh Thuan | ~5,064 operational/suspended coal | 0 | 4,500 | ~9,564 | Vinh Tan + Son My LNG. |
| 2 | Quang Ninh | ~5,000 coal | 0 | 1,500 | ~6,500 | Dense coal basin plus LNG plan. |
| 3 | Tra Vinh | ~4,496 coal | 0 | 0 | ~4,496 | Duyen Hai center. |
| 4 | Ba Ria–Vung Tau | 0 | ~4,260 | 0 | ~4,260 | Phu My + Ba Ria gas. |
| 5 | Soc Trang | ~3,840 coal incl. suspended | 0 | 0 | ~3,840 | Long Phu. |
| 6 | Bac Lieu | 0 | 0 | 3,200 | 3,200 | Bac Lieu LNG. |
| 7 | Ha Tinh | ~3,050 | 0 | 0 | ~3,050 | Vung Ang + Formosa. |
| 8 | Can Tho | 0 | ~3,915 | 0 | ~3,915 | O Mon complex. |
| 9 | Thanh Hoa | 1,800 | 0 | 1,500 | 3,300 | Nghi Son coal + LNG. |
| 10 | Quang Binh | 1,200 | 0 | 1,500 | 2,700 | Quang Trach. |
| 11 | Hau Giang | ~3,200 | 0 | 0 | ~3,200 | Song Hau 1–2. |
| 12 | Dong Nai | 0 | 1,200 | 1,624 | 2,824 | Nhon Trach gas + LNG. |
| 13 | Hai Phong | 1,200 | 0 | 0 | 1,200 | Hai Phong coal. |
| 14 | Thai Binh | 1,800 | 0 | 1,500 | 3,300 | Thai Binh coal + LNG. |
| 15 | Ninh Thuan | 0 | 0 | 1,500 | 1,500 | Ca Na LNG. |

---

## 4.3 Timeline of additions by period and fuel, MWe

| Period | Coal additions | Domestic gas additions | LNG additions | Notes |
|---|---:|---:|---:|---|
| pre-2005 | ~1,500 | ~4,000 | 0 | Pha Lai, Uong Bi, Ninh Binh, early Phu My/Ba Ria. |
| 2005–2010 | ~2,500 | ~2,700 | 0 | Na Duong, Cao Ngan, Son Dong, Quang Ninh/Hai Phong starts, Ca Mau, Nhon Trach 1. |
| 2011–2015 | ~8,000 | ~750 | 0 | Mong Duong, Vung Ang 1, Nghi Son 1, Hai Phong/Quang Ninh completions, Nhon Trach 2. |
| 2016–2020 | ~7,000 | 0 | 0 | Vinh Tan, Duyen Hai, Thai Binh 1, Duyen Hai extension. |
| 2021–2025 | ~6,000–7,000 | 0 | up to 1,624 under commissioning | Nghi Son 2, Thai Binh 2, Song Hau 1, Duyen Hai 2, Van Phong 1, Nhon Trach 3–4. |
| 2026–2030 | ~2,400–3,600 | ~3,000–4,000 | ~18,000–22,000 | PDP8 committed coal, Block B–O Mon, LNG wave. |
| post-2030 | negative/retirements | uncertain | possible additional LNG/hydrogen | Coal phase-down, fuel conversion. |

---

## 4.4 Data quality summary — plant count by confidence and fuel

| Fuel | HIGH | MEDIUM | LOW | Total plant entries |
|---|---:|---:|---:|---:|
| Coal | 31 | 8 | 6 | 45 |
| Domestic gas | 10 | 6 | 2 | 18 |
| Imported LNG | 2 | 11 | 1 | 14 |
| **Total** | **43** | **25** | **9** | **77** |

---

# 5. Annotated bibliography

## 5.1 Government decisions / sectoral development plans

### Prime Minister of Vietnam, **Decision No. 500/QĐ-TTg approving the National Power Development Plan for 2021–2030, vision to 2050**, 15 May 2023.

- Vietnamese title: **Quyết định 500/QĐ-TTg phê duyệt Quy hoạch phát triển điện lực quốc gia thời kỳ 2021–2030, tầm nhìn đến năm 2050**.
- Publisher: Government of Vietnam / Prime Minister.
- URL: available through VEPG-hosted English PDF and Vietnamese legal databases; VEPG copy cited here. ([vepg.vn](https://vepg.vn/wp-content/uploads/2023/05/PDP8_full-with-annexes_EN.pdf?utm_source=openai))
- Annotation: Used as the main official policy anchor for PDP8, project categories, coal/LNG planning direction, and the 2021–2030/2050 planning framework.

### Prime Minister / MOIT, **PDP8 implementation plan and subsequent revisions**, 2024–2025.

- Vietnamese title: implementation decisions under PDP8, including Decision 262/QĐ-TTg, Decision 1682/QĐ-TTg and revised PDP8 materials referenced in legal commentary.
- URL: not fully verified in this run.
- Annotation: Used conceptually to identify that PDP8 project lists are dynamic and that “approved/planned” LNG and transition projects require verification against the latest implementation annex.

---

## 5.2 Company activity reports

### Vietnam Electricity, **Annual Report 2022–2023**, published 2024.

- Publisher: EVN.
- URL: EVN PDF cited in search result. ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai))
- Annotation: Used for reported national installed thermal capacity: coal-fired capacity **25,312 MW in 2022** and **26,756 MW in 2023**; gas-fired capacity **7,152 MW** in both years; institutional role of EVN.

### Vietnam Electricity, **Overview of national power sources in 2023**, EVN news, 2024.

- Publisher: EVN.
- URL: EVN news page. ([en.evn.com.vn](https://en.evn.com.vn/d6/news/Overview-of-national-power-sources-in-2023-66-142-4147.aspx?utm_source=openai))
- Annotation: Used for coal supply and gas consumption context: Vinacomin and Dong Bac coal supply to EVN thermal plants; Southeast and Southwest gas consumption.

### Vietnam Electricity, **Annual Report 2017**, EVN.

- Publisher: EVN.
- URL: EVN PDF search result. ([evn.com.vn](https://www.evn.com.vn/userfile/files/2024/11/EVNAnnualReport2017-web-20241120082800491.pdf?utm_source=openai))
- Annotation: Used as a historical pointer for EVN thermal fleet context, including Duyen Hai and other GENCO assets. Not heavily cited for numerical values in this draft.

---

## 5.3 Company filings & press releases

### EVN, **Development of coal-fired thermal power plants with high-efficiency and environmentally friendly technologies**, EVN news, 2018.

- Publisher: EVN.
- URL: EVN news page. ([en.evn.com.vn](https://en.evn.com.vn/d6/news/Development-of-coal-fired-thermal-power-plants-with-high-efficiency-and-environmentally-friendly-technologies-66-163-915.aspx?utm_source=openai))
- Annotation: Used for policy/technology context around Vietnam’s earlier PDP7-revised coal trajectory and environmental-control claims.

### PV Power / Petrovietnam reports and releases.

- URL: not verified in this run.
- Annotation: Should be used in the next audit round to verify Ca Mau, Nhon Trach, Vung Ang 1, Song Hau 1, Thai Binh 2, Nhon Trach 3–4 and O Mon IV project details.

### TKV / Vinacomin reports.

- URL: not verified in this run.
- Annotation: Should be used to verify Na Duong, Cao Ngan, Cam Pha, Mao Khe and Son Dong.

---

## 5.4 Regulatory & international organization reports

### Global Energy Monitor, **Global Coal Plant Tracker**, January 2026 release.

- Publisher: Global Energy Monitor.
- URL: Global Coal Plant Tracker. ([globalenergymonitor.org](https://globalenergymonitor.org/projects/global-coal-plant-tracker/?utm_source=openai))
- Annotation: Used as the main secondary completeness check for coal units ≥30 MW, including operating units, proposed units since 2010 and retired units since 2000. GEM is not a Vietnamese primary source but is highly useful for unit-level reconciliation.

### Global Energy Monitor, **Global Oil and Gas Plant Tracker**.

- Publisher: Global Energy Monitor.
- URL: tracker project page identified in search results. ([globalenergymonitor.org](https://www.globalenergymonitor.org/fr/projects/global-oil-gas-plant-tracker/?utm_source=openai))
- Annotation: Relevant for future verification of gas/LNG projects; not used for detailed numerical extraction in this draft.

---

## 5.5 News & media / legal commentary

### Mayer Brown, **Vietnam’s PDP8 Released**, 2023.

- Publisher: Mayer Brown.
- URL: Mayer Brown insight page. ([mayerbrown.com](https://www.mayerbrown.com/en/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai))
- Annotation: Used for a concise list of PDP8 LNG projects and capacities, including Bac Lieu, Long An I, Son My I/II, Hiep Phuoc, Quang Ninh, Thai Binh, Nghi Son, Quang Trach II, Quynh Lap, Ca Na, Nhon Trach 3–4 and Hai Lang.

### US–ASEAN Business Council, **Vietnam Approval of National Power Development Plan VIII**, 2023.

- Publisher: US–ASEAN Business Council.
- URL: USABC page. ([usasean.org](https://www.usasean.org/article/vietnam-approval-national-power-development-plan-viii?utm_source=openai))
- Annotation: Used for PDP8 high-level coal target context: coal capacity increase to around 30 GW and declining share by 2030.

### LawNet Vietnam, **Deadline for implementing five delayed coal-fired electricity projects under PDP8**, 2023/2024.

- Publisher: LawNet.
- URL: LawNet page. ([lawnet.vn](https://lawnet.vn/en/laws/when-is-the-deadline-for-implementing-5-coal-fired-electricity-projects-behind-progress-or-facing-d-98804.html?utm_source=openai))
- Annotation: Used for context that PDP8 recognized a set of delayed/difficult coal projects, including projects affected by shareholder or financing issues.

### KPMG Vietnam, **Legal Update — Revised Power Development Plan VIII**, 2025.

- Publisher: KPMG Vietnam.
- URL: KPMG PDF search result. ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai))
- Annotation: Used for later PDP8 revision context, including 2030 fuel-capacity direction and transition-project treatment.

---

## 5.6 Academic sources

No academic source was directly cited in this run. Recommended sources for a full technical appendix:

- Peer-reviewed papers on Vietnam’s power-sector planning and coal lock-in.
- ADB / World Bank / IEA analyses of Vietnam’s power market reform.
- JETP analytical documents.
- Academic work on Vietnam LNG bankability and gas-market reform.

URLs not verified in this run.

---

# 6. Key uncertainties and next audit steps

1. **Unit-level CODs for legacy coal plants** need verification from EVN/TKV annual reports and plant company websites.
2. **Retirement status** of Ninh Binh, old Uong Bi and older Ba Ria/Phu My gas turbines needs official confirmation.
3. **LNG CODs are forward-looking**, not observed facts. They depend on PPA bankability, LNG supply, terminal completion, transmission, tariff approvals and investor FID.
4. **Domestic-gas projects** depend heavily on upstream field development — especially Block B–O Mon and Ca Voi Xanh.
5. **Captive industrial plants**, especially Formosa Ha Tinh, should be included in engineering/economic modeling but may be excluded from some EVN/PDP public-power statistics.
6. **Coal projects in suspended/cancelled status** require careful scenario coding: Vinh Tan 3, Long Phu 2–3, Song Hau 2, Quynh Lap coal and Kien Luong should not be treated as base-case additions without explicit scenario assumptions.

**Bottom line:** As of the latest sources checked here, Vietnam’s observed thermal base is roughly **27 GW coal** and **7.1 GW gas**, while the forward-looking PDP8 thermal pipeline is dominated by **committed residual coal, Block B / domestic-gas projects, and a very large but execution-risky LNG program**.