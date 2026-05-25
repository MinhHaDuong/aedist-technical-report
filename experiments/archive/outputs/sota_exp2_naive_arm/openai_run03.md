# Vietnam thermal generation assets (>30 MWe) — primary-sourced reference inventory, working edition

**As-of date used for current status:** 23 May 2026, unless a row’s status-as-of date is earlier and explicitly stated.  
**Important caveat:** A truly exhaustive, auditable Vietnam thermal-asset register requires line-by-line extraction from Vietnamese planning appendices, EVN/PVN/TKV annual reports, provincial investment approvals, ERAV generation licences, BOT handover notices and EPC/COD decisions. Within one response, I provide a **complete best-effort inventory** of known large coal, domestic-gas and imported-LNG thermal assets and projects, with **confidence labels**. Where I could not verify an exact primary URL in this session, I mark the row **LOW/MEDIUM** and explain.

---

## 1. Sector overview

Vietnam’s power system is now dominated by coal, hydropower, gas and fast-growing renewables. EVN’s 2025 annual report gives **2024 system installed capacity of 82,387 MW**, including **26,757 MW coal**, **8,653 MW gas + oil**, **23,664 MW hydropower**, **21,447 MW renewables**, **644 MW other** and **1,222 MW imports**. EVN also reports 2024 power production/purchases of **308,732 million kWh**, of which **coal-fired generation was 152,775 million kWh**, **gas-fired 21,827 million kWh**, hydropower 88,723 million kWh and renewables 39,641 million kWh. ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/2026/4/AnnualRepot2025_V23-20260408155435105.pdf?utm_source=openai))

The key policy framework is **Power Development Plan VIII — PDP8**, approved by **Decision 500/QĐ-TTg dated 15 May 2023**, and later revised by **Decision 768/QĐ-TTg dated 15 April 2025**, with implementation guidance under **Decision 1509/QĐ-BCT dated 30 May 2025**. The original PDP8 targeted roughly **30,127 MW coal**, **22.4 GW LNG** and domestic gas additions by 2030; the 2025 revision increased/adjusted planning targets, with reported 2030 targets of about **31,055 MW coal**, **10,861–14,930 MW domestic gas** and **22,524 MW LNG**. ([blogs.duanemorris.com](https://blogs.duanemorris.com/vietnam/wp-content/uploads/sites/19/2023/05/Decision-No.500_QD-TTg_E.pdf?utm_source=openai))

Institutionally, the sector is led by the **Ministry of Industry and Trade — MOIT/Bộ Công Thương**, the **Electricity Regulatory Authority of Vietnam — ERAV**, **Vietnam Electricity — EVN**, EVN generation corporations **GENCO1/2/3**, **Petrovietnam/PVN and PV Power**, **Vinacomin/TKV and Vinacomin Power**, provincial people’s committees, and BOT/IPP developers such as AES, Marubeni, JERA, Sumitomo, Toyo, Posco, Samsung C&T, Sembcorp and local private groups. EVN remains central as single buyer/system operator for most legacy assets, while PVN/PV Power dominate domestic-gas generation and TKV owns several mine-mouth coal plants.

Current challenges include: coal-fuel security and import dependence; gas-field decline in the Southeast and Southwest basins; delays to Block B–Ô Môn, Cá Voi Xanh and LNG-to-power chains; tariff/PPA bankability for LNG; grid congestion in high-renewables regions; emissions and Just Energy Transition Partnership commitments; and the practical need for dispatchable capacity after several years of fast but intermittent solar/wind growth. EVN’s 2023 and 2024 disclosures specifically highlight coal-supply coordination with Vinacomin and Đông Bắc Corporation and lower-than-plan gas consumption in some regions. ([en.evn.com.vn](https://en.evn.com.vn/d6/news/Overview-of-national-power-sources-in-2023-66-142-4147.aspx?utm_source=openai))

---

## 2. Source-code legend used in plant table

| Code | Source |
|---|---|
| **EVN-2025AR** | EVN Annual Report 2025 / 2024 data, installed capacity and generation mix. ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/2026/4/AnnualRepot2025_V23-20260408155435105.pdf?utm_source=openai)) |
| **EVN-2023SRC** | EVN overview of national power sources in 2023. ([en.evn.com.vn](https://en.evn.com.vn/d6/news/Overview-of-national-power-sources-in-2023-66-142-4147.aspx?utm_source=openai)) |
| **PDP8-500** | Prime Minister Decision 500/QĐ-TTg, PDP8, 15 May 2023. ([blogs.duanemorris.com](https://blogs.duanemorris.com/vietnam/wp-content/uploads/sites/19/2023/05/Decision-No.500_QD-TTg_E.pdf?utm_source=openai)) |
| **PDP8-IP** | PDP8 implementation plan summary/list. ([vietnamenergy.vn](https://vietnamenergy.vn/promulgating-the-plan-forimplementing-power-development-planning-viii-32400.html?utm_source=openai)) |
| **PDP8-REV** | Revised PDP8, Decision 768/QĐ-TTg / implementation guidance summary. ([kpmg.com](https://kpmg.com/vn/en/home/insights/2025/07/revised-pdp-8.html?utm_source=openai)) |
| **GENCO3-AR** | EVNGENCO3 annual/prospectus disclosures for Phú Mỹ, Mông Dương 1, Vĩnh Tân 2. ([genco3.com](https://www.genco3.com/baocaothuongnien_EN/tong-quan-ve-evngenco3.html?utm_source=openai)) |
| **GENCO1-DH** | EVN/GENCO1 disclosures for Duyên Hải 1, 3 and 3 extension. ([en.evn.com.vn](https://en.evn.com.vn/d6/news/Boiler-1-Duyen-Hai-3-Thermal-Power-plant-heated-for-the-first-time-66-142-365.aspx?utm_source=openai)) |
| **EVN-COAL** | EVN articles on coal-fired development/operation/fuel supply. ([en.evn.com.vn](https://en.evn.com.vn/d6/news/Overview-of-coal-fired-thermal-power-development-in-Vietnam-66-163-1573.aspx?utm_source=openai)) |
| **WIKI-LIST** | Wikipedia plant list, used only as secondary cross-check where primary source not verified. ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) |
| **PT-PHUMY** | Power Technology profile of Phú Mỹ complex, secondary cross-check. ([power-technology.com](https://www.power-technology.com/projects/phu-my-power-plants/?utm_source=openai)) |
| **VNENERGY-PDP8** | Vietnam Energy article summarizing PDP8 implementation plan, secondary but based on official plan. ([vietnamenergy.vn](https://vietnamenergy.vn/promulgating-the-plan-forimplementing-power-development-planning-viii-32400.html?utm_source=openai)) |

---

## 3. Structured thermal power-plants table

**Status vocabulary:** Operating; Under construction; Planned / pre-FID; Delayed / uncertain; Cancelled / removed; Retired / standby; Converted / superseded.  
**Confidence:** HIGH = primary source supports key attributes; MEDIUM = strong secondary or partial primary; LOW = known/likely asset but key attributes or status not independently verified here.

### 3.1 Coal-fired plants and projects

| Name (Vietnamese) | Name (English) | Province | Fuel | Technology | Units × MW | Total MWe | Status | Status as-of-date | COD | Owner / Developer | Confidence | Source 1 | Source 2 | Notes |
|---|---:|---|---|---|---:|---:|---|---|---|---|---|---|---|---|
| Nhiệt điện Ninh Bình | Ninh Bình TPP | Ninh Bình | Coal | Subcritical | 4×25 | 100 | Operating / old | 2024 | 1970s | EVN / GENCO3? | MEDIUM | WIKI-LIST | EVN-COAL | Legacy small coal plant >30 MWe; exact current operating regime uncertain. |
| Nhiệt điện Phả Lại 1 | Phả Lại 1 TPP | Hải Dương | Coal | Subcritical | 4×110 | 440 | Operating / aging | 2024 | 1983–1986 | PPC / EVN-affiliated | MEDIUM | WIKI-LIST | EVN-COAL | Old Soviet-era units; environmental/efficiency constraints. |
| Nhiệt điện Phả Lại 2 | Phả Lại 2 TPP | Hải Dương | Coal | Subcritical | 2×300 | 600 | Operating | 2024 | 2001–2002 | PPC / EVN-affiliated | MEDIUM | WIKI-LIST | EVN-COAL | Often grouped with Phả Lại total 1,040 MW. |
| Nhiệt điện Uông Bí mở rộng | Uông Bí Extension | Quảng Ninh | Coal | Subcritical | 1×300 + 1×330 | 630 | Operating | 2024 | 2006–2011 | EVN / GENCO1 | MEDIUM | WIKI-LIST | EVN-COAL | Older Uông Bí units partly retired; table records modern extension capacity. |
| Nhiệt điện Cao Ngạn | Cao Ngạn TPP | Thái Nguyên | Coal | Subcritical / CFB | 2×57.5 | 115 | Operating | 2024 | 2006 | Vinacomin Power / TKV | MEDIUM | WIKI-LIST | EVN-COAL | Mine-mouth anthracite/low-grade coal plant. |
| Nhiệt điện Na Dương | Na Dương TPP | Lạng Sơn | Coal | Subcritical / CFB | 2×55 | 110 | Operating | 2024 | 2005 | Vinacomin Power / TKV | MEDIUM | WIKI-LIST | EVN-COAL | Phase 2 has appeared in planning but not operating. |
| Nhiệt điện Cẩm Phả 1 | Cẩm Phả 1 TPP | Quảng Ninh | Coal | Subcritical / CFB | 1×330 | 330 | Operating | 2024 | 2010 | Vinacomin Power / TKV | MEDIUM | WIKI-LIST | EVN-COAL | Sometimes reported as part of Cẩm Phả 1–2 complex. |
| Nhiệt điện Cẩm Phả 2 | Cẩm Phả 2 TPP | Quảng Ninh | Coal | Subcritical / CFB | 1×330 | 330 | Operating | 2024 | 2011 | Vinacomin Power / TKV | MEDIUM | WIKI-LIST | EVN-COAL | See above. |
| Nhiệt điện Sơn Động | Sơn Động TPP | Bắc Giang | Coal | Subcritical / CFB | 2×110 | 220 | Operating | 2024 | 2009–2010 | Vinacomin Power / TKV | MEDIUM | WIKI-LIST | EVN-COAL | Burns local coal; ash/disposal issues reported historically. |
| Nhiệt điện Mạo Khê | Mạo Khê TPP | Quảng Ninh | Coal | Subcritical / CFB | 2×220 | 440 | Operating | 2024 | 2012 | Vinacomin Power / TKV | MEDIUM | WIKI-LIST | EVN-COAL | TKV mine-mouth plant. |
| Nhiệt điện An Khánh | An Khánh TPP | Thái Nguyên | Coal | Subcritical / CFB | 2×50 | 100 | Operating | 2024 | 2015 | An Khánh Thermal Power JSC | LOW | WIKI-LIST | URL not verified | Captive/IPP plant; primary URL not verified here. |
| Nhiệt điện Nông Sơn | Nông Sơn TPP | Quảng Nam | Coal | Subcritical / CFB | 1×30 | 30 | Borderline / operating | 2024 | 2015? | TKV / local | LOW | WIKI-LIST | URL not verified | Inclusion depends on strict “>30 MWe”: if exactly 30 MW net, exclude; retained for review. |
| Nhiệt điện Hải Phòng 1 | Hải Phòng 1 TPP | Hải Phòng | Coal | Subcritical | 2×300 | 600 | Operating | 2024 | 2011–2012 | Hải Phòng Thermal Power JSC / EVN | MEDIUM | WIKI-LIST | EVN-COAL | Part of Hải Phòng 1–2 complex. |
| Nhiệt điện Hải Phòng 2 | Hải Phòng 2 TPP | Hải Phòng | Coal | Subcritical | 2×300 | 600 | Operating | 2024 | 2013–2014 | Hải Phòng Thermal Power JSC / EVN | MEDIUM | WIKI-LIST | EVN-COAL | Total complex about 1,200 MW. |
| Nhiệt điện Quảng Ninh 1 | Quảng Ninh 1 TPP | Quảng Ninh | Coal | Subcritical | 2×300 | 600 | Operating | 2024 | 2009–2010 | Quảng Ninh Thermal Power JSC / EVN | MEDIUM | WIKI-LIST | EVN-COAL | — |
| Nhiệt điện Quảng Ninh 2 | Quảng Ninh 2 TPP | Quảng Ninh | Coal | Subcritical | 2×300 | 600 | Operating | 2024 | 2013–2014 | Quảng Ninh Thermal Power JSC / EVN | MEDIUM | WIKI-LIST | EVN-COAL | Total complex about 1,200 MW. |
| Nhiệt điện Mông Dương 1 | Mông Dương 1 TPP | Quảng Ninh | Coal | Subcritical / CFB | 2×540 | 1,080 | Operating | 2024 | 2015 | EVNGENCO3 | HIGH | GENCO3-AR | WIKI-LIST | GENCO3 identifies Mông Dương 1 as 1,080 MW. |
| Nhiệt điện Mông Dương 2 | Mông Dương 2 TPP | Quảng Ninh | Coal | Subcritical | 2×560 | 1,120 | Operating | 2024 | 2015 | AES-led BOT / later ownership changes | MEDIUM | WIKI-LIST | EVN-COAL | BOT coal plant; owner changes require current corporate verification. |
| Nhiệt điện Thái Bình 1 | Thái Bình 1 TPP | Thái Bình | Coal | Subcritical | 2×300 | 600 | Operating | 2024 | 2018 | EVN / GENCO3? | MEDIUM | WIKI-LIST | EVN-COAL | — |
| Nhiệt điện Thái Bình 2 | Thái Bình 2 TPP | Thái Bình | Coal | Subcritical | 2×600 | 1,200 | Operating | 2024 | 2023 | PVN / PV Power? | MEDIUM | EVN-2023SRC | WIKI-LIST | Long-delayed PVN project; commercial operation achieved before 2024 system totals. |
| Nhiệt điện Nghi Sơn 1 | Nghi Sơn 1 TPP | Thanh Hóa | Coal | Subcritical | 2×300 | 600 | Operating | 2024 | 2013–2014 | EVN / GENCO1 | MEDIUM | WIKI-LIST | EVN-COAL | — |
| Nhiệt điện Nghi Sơn 2 | Nghi Sơn 2 TPP | Thanh Hóa | Coal | Supercritical | 2×600 | 1,200 | Operating | 2024 | 2022 | Marubeni / KEPCO BOT | MEDIUM | WIKI-LIST | EVN-2023SRC | BOT project; exact unit COD needs primary COD decision. |
| Nhiệt điện Vũng Áng 1 | Vũng Áng 1 TPP | Hà Tĩnh | Coal | Subcritical | 2×600 | 1,200 | Operating | 2024 | 2014–2015 | PVN / PV Power | MEDIUM | WIKI-LIST | EVN-COAL | — |
| Nhiệt điện Formosa Hà Tĩnh | Formosa Hà Tĩnh Captive TPP | Hà Tĩnh | Coal | Subcritical | multiple | ~1,500 | Operating / captive CHP | 2024 | 2010s | Formosa Hà Tĩnh Steel | LOW | WIKI-LIST | URL not verified | Industrial captive plant; capacity often reported around 1.5 GW; needs primary corporate/environmental filing. |
| Nhiệt điện Vĩnh Tân 1 | Vĩnh Tân 1 TPP | Bình Thuận | Coal | Supercritical | 2×620 | 1,240 | Operating | 2024 | 2018 | China Southern Power Grid / Vinacomin / EVN BOT | MEDIUM | WIKI-LIST | EVN-COAL | Imported coal coastal plant. |
| Nhiệt điện Vĩnh Tân 2 | Vĩnh Tân 2 TPP | Bình Thuận | Coal | Subcritical | 2×622 | 1,244 | Operating | 2024 | 2014 | EVNGENCO3 | HIGH | GENCO3-AR | EVN-2025AR | GENCO3 identifies Vĩnh Tân 2 as 1,244 MW. |
| Nhiệt điện Vĩnh Tân 4 | Vĩnh Tân 4 TPP | Bình Thuận | Coal | Supercritical | 2×600 | 1,200 | Operating | 2024 | 2017–2018 | EVN | MEDIUM | WIKI-LIST | EVN-COAL | Imported coal; EVN has O&M/operation references. |
| Nhiệt điện Vĩnh Tân 4 mở rộng | Vĩnh Tân 4 Extension | Bình Thuận | Coal | Supercritical | 1×600 | 600 | Operating | 2024 | 2019 | EVN | MEDIUM | WIKI-LIST | EVN-COAL | Often grouped with Vĩnh Tân 4 total 1,800 MW. |
| Nhiệt điện Duyên Hải 1 | Duyên Hải 1 TPP | Trà Vinh | Coal | Subcritical | 2×622.5 | 1,245 | Operating | 2024 | 2015–2016 | EVNGENCO1 | HIGH | GENCO1-DH | WIKI-LIST | GENCO1/EVN says Duyên Hải 1 + Duyên Hải 3 total design capacity 2,490 MW. |
| Nhiệt điện Duyên Hải 3 | Duyên Hải 3 TPP | Trà Vinh | Coal | Subcritical | 2×622.5 | 1,245 | Operating | 2024 | 2016–2017 | EVNGENCO1 | HIGH | GENCO1-DH | WIKI-LIST | EVN notes imported coal and subcritical steam parameters. |
| Nhiệt điện Duyên Hải 3 mở rộng | Duyên Hải 3 Extension | Trà Vinh | Coal | Subcritical / supercritical? | 1×688 | 688 | Operating | 2024 | 2020 | EVNGENCO1 | MEDIUM | EVN-COAL | WIKI-LIST | Technology needs primary technical confirmation. |
| Nhiệt điện Duyên Hải 2 | Duyên Hải 2 TPP | Trà Vinh | Coal | Supercritical | 2×660 | 1,320 | Operating | 2024 | 2021–2022 | Janakuasa BOT | MEDIUM | WIKI-LIST | EVN-2023SRC | BOT imported-coal plant. |
| Nhiệt điện Sông Hậu 1 | Sông Hậu 1 TPP | Hậu Giang | Coal | Supercritical? | 2×600 | 1,200 | Operating | 2024 | 2022 | PVN | MEDIUM | WIKI-LIST | EVN-2023SRC | Technology frequently reported as supercritical; confirm from EPC spec. |
| Nhiệt điện Long Phú 1 | Long Phú 1 TPP | Sóc Trăng | Coal | Supercritical? | 2×600 | 1,200 | Delayed / under construction | 2025 | Not COD | PVN | MEDIUM | PDP8-IP | WIKI-LIST | Long-delayed by contractor/sanctions issues; appears in planning. |
| Nhiệt điện Long Phú 2 | Long Phú 2 TPP | Sóc Trăng | Coal | Supercritical? | 2×660 | 1,320 | Cancelled / removed from 2030 coal list | 2023–2025 | Not COD | Formerly TATA / other | LOW | PDP8-IP | WIKI-LIST | Reported excluded from PDP8-era coal additions. |
| Nhiệt điện Long Phú 3 | Long Phú 3 TPP | Sóc Trăng | Coal | Supercritical? | ~2×600 | ~1,200 | Cancelled / uncertain | 2023–2025 | Not COD | Planned IPP | LOW | PDP8-IP | URL not verified | Retained because appeared in earlier planning cycles. |
| Nhiệt điện Quỳnh Lập 1 | Quỳnh Lập 1 TPP | Nghệ An | Coal | Supercritical? | 2×600 | 1,200 | Cancelled / removed | 2023–2025 | Not COD | PVN / TKV? | LOW | PDP8-IP | WIKI-LIST | Reported excluded from near-term PDP8 coal plan. |
| Nhiệt điện Quỳnh Lập 2 | Quỳnh Lập 2 TPP | Nghệ An | Coal | Supercritical? | 2×600 | 1,200 | Cancelled / removed | 2023–2025 | Not COD | Planned IPP | LOW | PDP8-IP | WIKI-LIST | Same as above. |
| Nhiệt điện Vũng Áng 2 | Vũng Áng 2 TPP | Hà Tĩnh | Coal | USC / supercritical | 2×600 | 1,200 | Under construction | 2025 | Future | VAPCO / Mitsubishi-JERA-KEPCO? | MEDIUM | PDP8-IP | WIKI-LIST | Under construction despite transition-policy controversy. |
| Nhiệt điện Vũng Áng 3 | Vũng Áng 3 TPP | Hà Tĩnh | Coal | Supercritical? | 2×600 | 1,200 | Cancelled / removed | 2023–2025 | Not COD | Planned | LOW | PDP8-IP | WIKI-LIST | Reported excluded from new PDP8 coal list. |
| Nhiệt điện Nam Định 1 | Nam Định 1 TPP | Nam Định | Coal | Supercritical | 2×600 | 1,200 | Planned / delayed | 2025 | Future | Taekwang / Acwa Power? | LOW | PDP8-IP | WIKI-LIST | BOT coal project; status uncertain amid financing constraints. |
| Nhiệt điện Công Thanh | Công Thanh TPP | Thanh Hóa | Coal | Subcritical? | 2×300 | 600 | Delayed / uncertain | 2025 | Not COD | Công Thanh Group | LOW | WIKI-LIST | URL not verified | Appeared in prior plans; current viability unclear. |
| Nhiệt điện Hải Dương | Hải Dương BOT TPP | Hải Dương | Coal | Subcritical | 2×600 | 1,200 | Operating | 2024 | 2020 | JAKS / China Power? BOT | MEDIUM | WIKI-LIST | EVN-2023SRC | BOT plant; owner/corporate structure should be verified. |
| Nhiệt điện Kiên Lương 1 | Kiên Lương 1 TPP | Kiên Giang | Coal | Supercritical? | 2×600 | 1,200 | Cancelled / superseded | 2023–2025 | Not COD | ITACO / planned | LOW | WIKI-LIST | URL not verified | Earlier coal-power-centre plan largely superseded; retained due formal planning history. |
| Nhiệt điện Kiên Lương 2 | Kiên Lương 2 TPP | Kiên Giang | Coal | Supercritical? | 2×600 | 1,200 | Cancelled / superseded | 2023–2025 | Not COD | Planned | LOW | WIKI-LIST | URL not verified | Same. |
| Nhiệt điện Kiên Lương 3 | Kiên Lương 3 TPP | Kiên Giang | Coal | Supercritical? | ~2×600 | ~1,200 | Cancelled / superseded | 2023–2025 | Not COD | Planned | LOW | WIKI-LIST | URL not verified | Same. |

### 3.2 Domestic-gas / oil-gas plants

| Name (Vietnamese) | Name (English) | Province | Fuel | Technology | Units × MW | Total MWe | Status | Status as-of-date | COD | Owner / Developer | Confidence | Source 1 | Source 2 | Notes |
|---|---:|---|---|---|---:|---:|---|---|---|---|---|---|---|---|
| Tuabin khí Bà Rịa | Bà Rịa Gas Turbines | Bà Rịa–Vũng Tàu | Domestic gas | OCGT / some CCGT? | multiple | ~389 | Operating / aging | 2024 | 1990s | Bà Rịa Thermal Power JSC / EVN | LOW | WIKI-LIST | PT-PHUMY | Exact net capacity and current dispatch uncertain. |
| Nhiệt điện Phú Mỹ 1 | Phú Mỹ 1 CCGT | Bà Rịa–Vũng Tàu | Domestic gas | CCGT | 3 GT + 1 ST | ~1,090 | Operating | 2024 | 2002 | EVNGENCO3 | HIGH | GENCO3-AR | PT-PHUMY | GENCO3 identifies Phú Mỹ thermal power as a major operating complex. |
| Nhiệt điện Phú Mỹ 2.1 | Phú Mỹ 2.1 CCGT | Bà Rịa–Vũng Tàu | Domestic gas | CCGT | multiple | ~900 | Operating | 2024 | 1997–2005 | EVNGENCO3 | MEDIUM | GENCO3-AR | PT-PHUMY | Often split into 2.1 and 2.1 extension; exact unit allocation varies. |
| Nhiệt điện Phú Mỹ 2.2 | Phú Mỹ 2.2 CCGT | Bà Rịa–Vũng Tàu | Domestic gas | CCGT | 2+1 | ~715 | Operating / BOT handover | 2024–2025 | 2005 | Former Mekong Energy BOT; EVN/GENCO3 O&M | MEDIUM | GENCO3-AR | PT-PHUMY | BOT handover/operation details require current EVN notice. |
| Nhiệt điện Phú Mỹ 3 | Phú Mỹ 3 CCGT | Bà Rịa–Vũng Tàu | Domestic gas | CCGT | 2+1 | ~716 | Operating / BOT handover | 2024–2025 | 2004 | Former BP/Sembcorp/Kyuden BOT; EVN/GENCO3 O&M | MEDIUM | GENCO3-AR | PT-PHUMY | GENCO3 2024/2025 disclosures mention O&M contracts for Phú Mỹ 3. |
| Nhiệt điện Phú Mỹ 4 | Phú Mỹ 4 CCGT | Bà Rịa–Vũng Tàu | Domestic gas | CCGT | multiple | ~450 | Operating | 2024 | 2004 | EVNGENCO3 | MEDIUM | GENCO3-AR | PT-PHUMY | Part of Phú Mỹ complex. |
| Nhiệt điện Nhơn Trạch 1 | Nhơn Trạch 1 CCGT | Đồng Nai | Domestic gas | CCGT | 2 GT + 1 ST | 450 | Operating | 2024 | 2009 | PV Power | MEDIUM | WIKI-LIST | EVN-2023SRC | Uses Nam Côn Sơn / Southeast gas. |
| Nhiệt điện Nhơn Trạch 2 | Nhơn Trạch 2 CCGT | Đồng Nai | Domestic gas | CCGT | 2 GT + 1 ST | 750 | Operating | 2024 | 2011 | PV Power NT2 | MEDIUM | WIKI-LIST | EVN-2023SRC | Listed gas capacity in national totals. |
| Nhiệt điện Cà Mau 1 | Cà Mau 1 CCGT | Cà Mau | Domestic gas | CCGT | 2 GT + 1 ST | 750 | Operating | 2024 | 2007–2008 | PV Power | MEDIUM | WIKI-LIST | EVN-2023SRC | Part of Cà Mau gas-power-fertilizer complex. |
| Nhiệt điện Cà Mau 2 | Cà Mau 2 CCGT | Cà Mau | Domestic gas | CCGT | 2 GT + 1 ST | 750 | Operating | 2024 | 2008 | PV Power | MEDIUM | WIKI-LIST | EVN-2023SRC | Same complex; supplied by PM3–Cà Mau pipeline. |
| Nhiệt điện Ô Môn 1 | Ô Môn 1 CCGT / oil-gas | Cần Thơ | Domestic gas / oil backup | CCGT / steam? | 2×330 | 660 | Operating, awaiting Block B gas | 2024 | 2009/2015 | EVNGENCO2 | LOW | WIKI-LIST | PDP8-IP | Often oil-fired pending gas; technology classification needs primary plant spec. |
| Nhiệt điện Ô Môn 2 | Ô Môn 2 CCGT | Cần Thơ | Domestic gas | CCGT | ~1×1,050 | 1,050 | Planned / pre-FID | 2025 | Future | Marubeni / WTO? | MEDIUM | PDP8-IP | PDP8-REV | Part of Block B–Ô Môn chain. |
| Nhiệt điện Ô Môn 3 | Ô Môn 3 CCGT | Cần Thơ | Domestic gas | CCGT | ~1,050 | 1,050 | Planned / financing | 2025 | Future | EVN | MEDIUM | PDP8-IP | PDP8-REV | Depends on Block B gas and financing. |
| Nhiệt điện Ô Môn 4 | Ô Môn 4 CCGT | Cần Thơ | Domestic gas | CCGT | ~1,050 | 1,050 | Planned | 2025 | Future | EVN / PVN? | MEDIUM | PDP8-IP | PDP8-REV | Included in domestic gas plan. |
| Trung tâm điện lực Dung Quất 1 | Dung Quất 1 CCGT | Quảng Ngãi | Domestic gas | CCGT | ~750 | 750 | Planned / uncertain | 2025 | Future | PVN / PV Power | LOW | PDP8-IP | URL not verified | Linked to Cá Voi Xanh gas; project status uncertain. |
| Trung tâm điện lực Dung Quất 2 | Dung Quất 2 CCGT | Quảng Ngãi | Domestic gas | CCGT | ~750 | 750 | Planned / uncertain | 2025 | Future | PVN / PV Power | LOW | PDP8-IP | URL not verified | Same. |
| Trung tâm điện lực Dung Quất 3 | Dung Quất 3 CCGT | Quảng Ngãi | Domestic gas | CCGT | ~750 | 750 | Planned / uncertain | 2025 | Future | EVN / PVN? | LOW | PDP8-IP | URL not verified | Same. |
| Miền Trung 1 | Central Vietnam Gas Power 1 | Quảng Nam / Quảng Ngãi? | Domestic gas | CCGT | ~750 | 750 | Planned / uncertain | 2025 | Future | Planned | LOW | PDP8-IP | URL not verified | Appeared in Cá Voi Xanh-related planning; exact siting/name uncertain. |
| Miền Trung 2 | Central Vietnam Gas Power 2 | Quảng Nam / Quảng Ngãi? | Domestic gas | CCGT | ~750 | 750 | Planned / uncertain | 2025 | Future | Planned | LOW | PDP8-IP | URL not verified | Same. |
| Hiệp Phước | Hiệp Phước Power Plant | TP. Hồ Chí Minh | Domestic gas / fuel oil | OCGT / steam | ~375 | 375 | Operating / captive-grid legacy | 2024 | 1990s | Hiệp Phước Power Co. | LOW | WIKI-LIST | URL not verified | Included because >30 MWe and thermal; current operation/fuel mix uncertain. |
| Vedan cogeneration | Vedan Việt Nam CHP | Đồng Nai | Domestic gas / biomass? | CHP | >30 | unknown | Operating / captive | 2024 | unknown | Vedan Việt Nam | LOW | URL not verified | URL not verified | Known industrial CHP candidate; insufficient verified data. |
| Nhơn Trạch 3 | Nhơn Trạch 3 LNG CCGT | Đồng Nai | Imported LNG | CCGT | ~1×812 | 812 | Under construction / commissioning | 2025–2026 | Future | PV Power | MEDIUM | PDP8-IP | EVN-2025AR | Technically imported-LNG; grouped with LNG below in summaries. |
| Nhơn Trạch 4 | Nhơn Trạch 4 LNG CCGT | Đồng Nai | Imported LNG | CCGT | ~1×812 | 812 | Under construction / commissioning | 2025–2026 | Future | PV Power | MEDIUM | PDP8-IP | EVN-2025AR | Uses Thị Vải LNG supply chain. |

### 3.3 Imported-LNG plants and projects

| Name (Vietnamese) | Name (English) | Province | Fuel | Technology | Units × MW | Total MWe | Status | Status as-of-date | COD | Owner / Developer | Confidence | Source 1 | Source 2 | Notes |
|---|---:|---|---|---|---:|---:|---|---|---|---|---|---|---|---|
| LNG Nhơn Trạch 3 | Nhơn Trạch 3 LNG Power Plant | Đồng Nai | Imported LNG | CCGT | ~812 | 812 | Under construction / commissioning | 2025–2026 | Future | PV Power | MEDIUM | PDP8-IP | PDP8-REV | Duplicate of gas table item; counted once in statistics. |
| LNG Nhơn Trạch 4 | Nhơn Trạch 4 LNG Power Plant | Đồng Nai | Imported LNG | CCGT | ~812 | 812 | Under construction / commissioning | 2025–2026 | Future | PV Power | MEDIUM | PDP8-IP | PDP8-REV | Duplicate of gas table item; counted once. |
| LNG Sơn Mỹ 1 | Sơn Mỹ 1 LNG Power Plant | Bình Thuận | Imported LNG | CCGT | ~2×1,125 | 2,250 | Planned / pre-FID | 2025 | Future | EDF / Sojitz / Kyushu / Pacific? | MEDIUM | PDP8-IP | PDP8-REV | Part of Sơn Mỹ LNG-to-power centre; ownership needs current verification. |
| LNG Sơn Mỹ 2 | Sơn Mỹ 2 LNG Power Plant | Bình Thuận | Imported LNG | CCGT | ~2,250 | 2,250 | Planned / pre-FID | 2025 | Future | AES / PV Gas? | MEDIUM | PDP8-IP | PDP8-REV | Linked to Sơn Mỹ LNG terminal; PPA/tariff constraints. |
| LNG Bạc Liêu | Bạc Liêu LNG Power Plant | Bạc Liêu | Imported LNG | CCGT | 3,200 | 3,200 | Planned / delayed | 2025 | Future | Delta Offshore Energy / provincial partners | MEDIUM | PDP8-IP | PDP8-REV | High-profile 3.2 GW project; bankability and schedule uncertain. |
| LNG Long An 1 | Long An 1 LNG Power Plant | Long An | Imported LNG | CCGT | ~1,500 | 1,500 | Planned / pre-FID | 2025 | Future | VinaCapital / GS Energy? | MEDIUM | PDP8-IP | PDP8-REV | One of Long An LNG projects in PDP8. |
| LNG Long An 2 | Long An 2 LNG Power Plant | Long An | Imported LNG | CCGT | ~1,500 | 1,500 | Planned / pre-FID | 2025 | Future | VinaCapital / GS Energy? | MEDIUM | PDP8-IP | PDP8-REV | Same site/cluster. |
| LNG Quảng Ninh | Quảng Ninh LNG Power Plant | Quảng Ninh | Imported LNG | CCGT | ~1,500 | 1,500 | Planned / investor selected | 2025 | Future | PV Power / Colavi / Tokyo Gas / Marubeni? | MEDIUM | PDP8-IP | PDP8-REV | Included in PDP8 LNG list. |
| LNG Hải Lăng giai đoạn 1 | Hải Lăng LNG Phase 1 | Quảng Trị | Imported LNG | CCGT | ~1,500 | 1,500 | Planned / pre-FID | 2025 | Future | T&T / Hanwha / KOSPO / KOGAS? | MEDIUM | PDP8-IP | PDP8-REV | Part of Hải Lăng LNG power centre. |
| LNG Nghi Sơn | Nghi Sơn LNG Power Plant | Thanh Hóa | Imported LNG | CCGT | ~1,500 | 1,500 | Planned / pre-FID | 2025 | Future | T&T / Korean or Japanese partners? | LOW | PDP8-IP | PDP8-REV | Developer/status needs primary update. |
| LNG Thái Bình | Thái Bình LNG Power Plant | Thái Bình | Imported LNG | CCGT | ~1,500 | 1,500 | Planned / pre-FID | 2025 | Future | Tokyo Gas / Kyuden / Truong Thanh? | LOW | PDP8-IP | PDP8-REV | Appears in PDP8 LNG planning; current investor status uncertain. |
| LNG Hải Phòng | Hải Phòng LNG Power Plant | Hải Phòng | Imported LNG | CCGT | ~1,600 | 1,600 | Planned / pre-FID | 2025 | Future | Vingroup / V-Green? or other local consortia | LOW | PDP8-REV | URL not verified | Newer/project-specific details need direct provincial/MOIT source. |
| LNG Cà Ná | Cà Ná LNG Power Plant | Ninh Thuận | Imported LNG | CCGT | ~1,500 | 1,500 | Delayed / uncertain | 2025 | Future | Trung Nam / provincial? | LOW | PDP8-IP | URL not verified | Earlier LNG plan; may have shifted in revised plan. |
| LNG Chân Mây | Chân Mây LNG Power Plant | Thừa Thiên Huế | Imported LNG | CCGT | ~1,500 | 1,500 | Planned / uncertain | 2025 | Future | Chan May LNG JSC? | LOW | PDP8-IP | URL not verified | Needs confirmation against latest implementation appendix. |
| LNG Cái Mép Hạ / Long Sơn | Cái Mép Hạ / Long Sơn LNG Power Plant | Bà Rịa–Vũng Tàu | Imported LNG | CCGT | ~1,500 | 1,500 | Planned / uncertain | 2025 | Future | Proposed IPP | LOW | PDP8-IP | URL not verified | Retained as planning-cycle candidate; avoid double-counting with terminal-only projects. |

---

## 4. Concise per-plant narrative notes

### Coal

- **Ninh Bình, Phả Lại 1–2, Uông Bí:** Vietnam’s early coal fleet. These plants formed the backbone of the northern grid before larger 300–600 MW units arrived. Current role is increasingly constrained by age, efficiency and environmental performance.
- **TKV mine-mouth fleet — Cao Ngạn, Na Dương, Cẩm Phả, Sơn Động, Mạo Khê:** Developed to use domestic anthracite or low-grade coal near mining areas. They are mostly smaller CFB/subcritical plants and remain important for local system support.
- **Hải Phòng and Quảng Ninh complexes:** 1.2 GW-class northern coastal/near-coalfield subcritical plants built during the 2000s–2010s to meet fast load growth.
- **Mông Dương 1–2:** Mông Dương 1 is EVNGENCO3’s 1,080 MW coal plant; Mông Dương 2 is a 1,120 MW BOT project. Together they are among the largest northern coal complexes.
- **Thái Bình 1–2:** Thái Bình 1 is EVN-linked; Thái Bình 2 was a long-delayed PVN project that entered the operating fleet before 2024 system reporting.
- **Nghi Sơn 1–2:** Nghi Sơn 1 is EVN’s 600 MW plant; Nghi Sơn 2 is a 1.2 GW BOT plant using more efficient large-unit technology.
- **Vũng Áng 1–2 and Formosa Hà Tĩnh:** Hà Tĩnh is a major thermal hub. Vũng Áng 1 is operating; Vũng Áng 2 is one of the last large coal projects under construction; Formosa’s captive plant supplies the steel complex and should be treated separately from grid-only capacity.
- **Vĩnh Tân 1/2/4/4 extension:** Bình Thuận’s Vĩnh Tân centre is a major imported-coal complex. Vĩnh Tân 2 is EVNGENCO3’s 1,244 MW plant; Vĩnh Tân 1 is BOT; Vĩnh Tân 4 and extension are EVN plants.
- **Duyên Hải 1/2/3/3 extension:** Trà Vinh’s Duyên Hải power centre is the largest southern coal cluster. EVN/GENCO1 disclosures support Duyên Hải 1 and 3 as 2,490 MW combined; Duyên Hải 2 is BOT; Duyên Hải 3 extension adds about 688 MW.
- **Sông Hậu 1 and Long Phú 1:** Mekong Delta coal projects under PVN. Sông Hậu 1 is operating; Long Phú 1 remains delayed.
- **Cancelled/uncertain coal projects — Long Phú 2–3, Quỳnh Lập 1–2, Vũng Áng 3, Kiên Lương, Công Thanh, Nam Định 1:** These appeared in formal planning cycles, but PDP8-era policy reduced the forward coal pipeline. Some are removed/cancelled; others remain delayed or uncertain.

### Domestic gas

- **Bà Rịa and Phú Mỹ complex:** The Southeast gas-power system was Vietnam’s first large modern gas fleet, supplied mainly by offshore gas. Phú Mỹ is a multi-plant CCGT complex of roughly 3.9 GW; GENCO3 disclosures support EVNGENCO3’s central operating role.
- **Nhơn Trạch 1–2:** PV Power’s CCGT plants in Đồng Nai, operating on domestic gas, are important mid-merit/peaking and reliability assets.
- **Cà Mau 1–2:** PV Power’s 1.5 GW Cà Mau complex is integrated with the PM3–Cà Mau pipeline and fertilizer complex.
- **Ô Môn 1–4:** Ô Môn 1 exists but has historically relied on oil/limited gas pending Block B. Ô Môn 2–4 are future CCGT projects dependent on the Block B–Ô Môn upstream and pipeline chain.
- **Dung Quất / Central Vietnam gas projects:** Planned around Cá Voi Xanh gas. Because the upstream project has faced delays, these rows are LOW confidence for timing and final configuration.
- **Industrial/captive gas or CHP plants:** Hiệp Phước and possible industrial CHP units are in scope by the user’s definition, but exact current operating status and net export capacity require plant-level licences or corporate filings.

### Imported LNG

- **Nhơn Trạch 3–4:** Vietnam’s most advanced LNG-to-power projects, intended to use LNG supplied through the Thị Vải LNG chain. They are the bridge between domestic-gas CCGT experience and the PDP8 LNG buildout.
- **Sơn Mỹ 1–2:** Large planned LNG power centre in Bình Thuận, tied to Sơn Mỹ LNG terminal infrastructure.
- **Bạc Liêu LNG:** A 3.2 GW flagship southern LNG project, long discussed but delayed by PPA/tariff and bankability issues.
- **Long An 1–2, Quảng Ninh LNG, Hải Lăng LNG, Nghi Sơn LNG, Thái Bình LNG, Hải Phòng LNG, Cà Ná, Chân Mây, Cái Mép/Long Sơn:** These represent the broad PDP8 LNG pipeline. Most are pre-FID and should be treated as **planned capacity, not reliable operating capacity**, until PPAs, fuel-supply arrangements, financing and EPC notices are confirmed.

---

## 5. Statistical summary tables

### 5.1 Capacity by fuel × status  
Approximate; excludes rows with unknown capacity and avoids double-counting Nhơn Trạch 3–4.

| Fuel | Operating MWe | Under construction / commissioning MWe | Planned / pre-FID MWe | Delayed / uncertain MWe | Cancelled / removed MWe | Notes |
|---|---:|---:|---:|---:|---:|---|
| Coal | ~27,000–28,500 | ~1,200 | ~1,200 | ~2,400 | ~9,720 | Operating range depends on captive Formosa and small/borderline units. EVN reports 26,757 MW coal in 2024 system capacity, which excludes or treats some captive/off-grid assets differently. |
| Domestic gas / oil-gas | ~8,600–9,000 | 0 | ~6,900 | ~1,875 | 0 | EVN reports 8,653 MW gas + oil in 2024, consistent with grid-connected fleet. |
| Imported LNG | 0 | ~1,624 | ~20,600 | ~4,500 | 0 | PDP8/PDP8 revision targets about 22.4–22.5 GW LNG by 2030; most remains pre-FID. |
| **Total** | **~35,600–37,500** | **~2,824** | **~28,700** | **~8,775** | **~9,720** | Planning totals are not equivalent to bankable capacity. |

### 5.2 Top 15 provinces by identified thermal capacity, all statuses

| Rank | Province | Approx. identified MWe | Main assets |
|---:|---|---:|---|
| 1 | Bình Thuận | ~10,084 | Vĩnh Tân coal complex; Sơn Mỹ LNG |
| 2 | Quảng Ninh | ~6,720 | Uông Bí, Cẩm Phả, Quảng Ninh, Mông Dương, Quảng Ninh LNG |
| 3 | Bà Rịa–Vũng Tàu | ~5,960 | Bà Rịa, Phú Mỹ, possible LNG projects |
| 4 | Trà Vinh | ~4,498 | Duyên Hải coal centre |
| 5 | Hà Tĩnh | ~5,100 | Vũng Áng 1–3, Formosa |
| 6 | Cần Thơ | ~3,810 | Ô Môn 1–4 |
| 7 | Đồng Nai | ~3,636 | Nhơn Trạch 1–4, industrial CHP |
| 8 | Thanh Hóa | ~3,300 | Nghi Sơn 1–2, Công Thanh, Nghi Sơn LNG |
| 9 | Sóc Trăng | ~3,720 | Long Phú 1–3 |
| 10 | Bạc Liêu | ~3,200 | Bạc Liêu LNG |
| 11 | Long An | ~3,000 | Long An LNG 1–2 |
| 12 | Hải Dương | ~2,240 | Phả Lại, Hải Dương BOT |
| 13 | Thái Bình | ~3,300 | Thái Bình 1–2, Thái Bình LNG |
| 14 | Kiên Giang | ~3,600 | Kiên Lương legacy coal plans |
| 15 | Quảng Trị | ~1,500 | Hải Lăng LNG |

### 5.3 Timeline of additions by period and fuel  
Approximate COD grouping; planned future based on current planning, not committed construction.

| Period | Coal additions | Domestic gas additions | Imported LNG additions | Notes |
|---|---:|---:|---:|---|
| Pre-1990 | ~500–600 MW | 0 | 0 | Ninh Bình, early Phả Lại. |
| 1990–1999 | limited | ~1,000+ MW | 0 | Bà Rịa and early Phú Mỹ gas turbines. |
| 2000–2009 | ~2,000 MW | ~4,000 MW | 0 | Phú Mỹ CCGT buildout, Cà Mau, Ô Môn 1, Nhơn Trạch 1; first wave of modern coal. |
| 2010–2014 | ~6,000 MW | ~750 MW | 0 | Hải Phòng, Quảng Ninh, Vĩnh Tân 2, Nghi Sơn 1, Nhơn Trạch 2. |
| 2015–2019 | ~10,000 MW | limited | 0 | Mông Dương, Duyên Hải, Vĩnh Tân 1/4, Thái Bình 1. |
| 2020–2024 | ~6,000–7,000 MW | limited | 0 | Duyên Hải 2/3 ext., Sông Hậu 1, Thái Bình 2, Nghi Sơn 2, Hải Dương. |
| 2025–2030 planned | ~1,200–2,400 MW | ~7,000 MW | ~22,000 MW | Vũng Áng 2, Long Phú 1 if completed; Ô Môn/Block B; LNG pipeline. |
| Post-2030 / uncertain | declining coal | hydrogen-ready gas possible | LNG/hydrogen conversion | Revised PDP8 foresees fuel switching and lower coal share over time. |

### 5.4 Data-quality summary by confidence level and fuel

| Fuel | HIGH rows | MEDIUM rows | LOW rows | Main reason for LOW confidence |
|---|---:|---:|---:|---|
| Coal | 4 | ~25 | ~15 | Older/captive plants, cancelled projects, unverified current status. |
| Domestic gas | 1 | ~8 | ~9 | Unit configuration, fuel mode, Block B/Cá Voi Xanh timing, industrial CHP data gaps. |
| Imported LNG | 0 | ~9 | ~6 | Pre-FID status, shifting developers, revised PDP8 changes. |
| **Total** | **~5** | **~42** | **~30** | Vietnam planning names are stable, but project status and ownership require continuous verification. |

---

## 6. Annotated bibliography

1. **Vietnam Electricity — EVN. _Annual Report 2025 / data for 2024_.**  
   URL available via EVN PDF. Used for national 2024 installed-capacity totals, generation by fuel, ownership categories and system mix. This is the highest-level primary source for reconciling current grid-connected capacity. ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/2026/4/AnnualRepot2025_V23-20260408155435105.pdf?utm_source=openai))

2. **Vietnam Electricity — EVN. “Overview of national power sources in 2023.”**  
   Original title: English EVN article. Used for 2023 installed capacity, coal share, and EVN discussion of coal and gas supply/consumption. ([en.evn.com.vn](https://en.evn.com.vn/d6/news/Overview-of-national-power-sources-in-2023-66-142-4147.aspx?utm_source=openai))

3. **Prime Minister of Vietnam. Decision No. 500/QĐ-TTg dated 15 May 2023 approving the National Power Development Plan for 2021–2030, vision to 2050 — PDP8.**  
   Vietnamese title: _Quyết định phê duyệt Quy hoạch phát triển điện lực quốc gia thời kỳ 2021–2030, tầm nhìn đến năm 2050_ — “Decision approving the National Power Development Plan for 2021–2030, vision to 2050.” Used for planning framework and future thermal categories. English copy located via Duane Morris-hosted PDF; official Vietnamese legal gazette handle should be verified for production use. ([blogs.duanemorris.com](https://blogs.duanemorris.com/vietnam/wp-content/uploads/sites/19/2023/05/Decision-No.500_QD-TTg_E.pdf?utm_source=openai))

4. **Vietnam Energy. “Promulgating the Plan for Implementing Power Development Planning VIII.”**  
   Vietnamese planning-summary article, English translation. Used for PDP8 implementation-plan summary capacities: LNG, coal and project categories. Secondary but derived from official implementation plan. ([vietnamenergy.vn](https://vietnamenergy.vn/promulgating-the-plan-forimplementing-power-development-planning-viii-32400.html?utm_source=openai))

5. **KPMG Vietnam. “Revised Power Development Plan VIII of Vietnam.” 2025.**  
   Used for summary of Decision 768/QĐ-TTg dated 15 April 2025 and Decision 1509/QĐ-BCT dated 30 May 2025, including revised capacity ranges for coal, domestic gas and LNG. ([kpmg.com](https://kpmg.com/vn/en/home/insights/2025/07/revised-pdp-8.html?utm_source=openai))

6. **KPMG Vietnam. _Legal Update: Revised Power Development Plan VIII of Vietnam under Decision 768/QĐ-TTg and Decision 1509/QĐ-BCT_. July 2025.**  
   Used to corroborate revised PDP8 policy context and 2030/2050 capacity planning changes. ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai))

7. **EVNGENCO3. Annual report / overview disclosures, including EVNGENCO3 2022 and subsequent investor documents.**  
   Used for EVNGENCO3 portfolio references: Phú Mỹ thermal power complex, Mông Dương 1 at 1,080 MW, Vĩnh Tân 2 at 1,244 MW, and O&M references for BOT gas assets. ([genco3.com](https://www.genco3.com/baocaothuongnien_EN/tong-quan-ve-evngenco3.html?utm_source=openai))

8. **EVN. “Boiler 1 – Duyen Hai 3 Thermal Power Plant heated for the first time.”**  
   Used for Duyên Hải 3 attributes: investor EVN/GENCO1, imported coal, subcritical steam parameters and plant context. ([en.evn.com.vn](https://en.evn.com.vn/d6/news/Boiler-1-Duyen-Hai-3-Thermal-Power-plant-heated-for-the-first-time-66-142-365.aspx?utm_source=openai))

9. **EVN. “Duyen Hai Thermal Power Company reaches electricity output milestone of 100 billion kWh.”**  
   Used for Duyên Hải Thermal Power Company’s operation of Duyên Hải 1 and Duyên Hải 3 and their combined design capacity of 2,490 MW. ([en.evn.com.vn](https://en.evn.com.vn/d6/news/Duyen-Hai-Thermal-Power-Company-reaches-electricity-output-milestone-of-100-billion-kWh-66-163-3957.aspx?utm_source=openai))

10. **EVN. “Overview of coal-fired thermal power development in Vietnam.”**  
    Used for historical sector context on coal plant development and technology evolution. ([en.evn.com.vn](https://en.evn.com.vn/d6/news/Overview-of-coal-fired-thermal-power-development-in-Vietnam-66-163-1573.aspx?utm_source=openai))

11. **EVN. “Coal-fired thermal power and the challenge of operation for over 7,000 hours/year.”**  
    Used for coal-supply and operational-challenge context. ([en.evn.com.vn](https://en.evn.com.vn/d6/news/Coal-fired-thermal-power-and-the-challenge-of-operation-for-over-7000-hoursyear-66-163-1796.aspx?utm_source=openai))

12. **EVN. “Thermal power operation in 2024 and ‘3 no-tolerances’ goal.”**  
    Used for current coal-supply coordination and reliability context. ([en.evn.com.vn](https://en.evn.com.vn/d6/news/Thermal-power-operation-in-2024-and-3-no-tolerances-goal-66-163-3987.aspx?utm_source=openai))

13. **EVN. “Meeting to prepare for ensuring coal supply for power production in 2025.”**  
    Used for 2025 coal-supply coordination among EVN, Vinacomin and Đông Bắc Corporation and for references to imported-coal plants such as Vĩnh Tân 4 and Duyên Hải 3/3 extension. ([en.evn.com.vn](https://en.evn.com.vn/d6/news/Meeting-to-prepare-for-ensuring-coal-supply-for-power-production-in-2025-66-163-4370.aspx?utm_source=openai))

14. **Power Technology. “Phu My Power Plants, Vietnam.”**  
    Secondary source used to cross-check Phú Mỹ complex scale and configuration. Not treated as primary. ([power-technology.com](https://www.power-technology.com/projects/phu-my-power-plants/?utm_source=openai))

15. **Wikipedia. “List of power stations in Vietnam” and “List of coal-fired power stations in Vietnam.”**  
    Used only as a secondary completeness cross-check for older, captive, cancelled or difficult-to-source assets. Any row relying mainly on these lists is marked MEDIUM or LOW, never HIGH. ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai))

---

## 7. Reconciliation notes and next steps for a production-grade inventory

- **EVN’s 2024 coal capacity of 26,757 MW** is the best anchor for grid-connected coal capacity. My table’s operating coal total can exceed that if captive plants such as Formosa or borderline/small CHP plants are included.
- **Gas + oil capacity of 8,653 MW** from EVN is the best current grid-connected anchor; older oil/gas and captive assets need licence-level verification.
- **Future LNG capacity** is planning capacity, not bankable capacity. Most projects lack confirmed PPA, tariff, LNG supply, EPC and financing closure.
- For a final audited dataset, each row should be checked against: ERAV generation licence; MOIT PDP8 implementation appendix; EVN/PVN/TKV annual report; provincial investment-registration certificate; and COD acceptance notice.