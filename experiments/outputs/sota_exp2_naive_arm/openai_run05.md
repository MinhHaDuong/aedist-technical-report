# Vietnam thermal generation assets (>30 MWe) — reference inventory, v0.1  
**Scope:** coal, domestic-gas and imported-LNG thermal generation in Vietnam; operating, under construction, planned, suspended/cancelled and formal-plan projects; utility, IPP/BOT and large captive/industrial units where identified.  
**As-of date used for status harmonisation:** **23 May 2026**, unless the row cites an older source date.  
**Important limitation:** This is a best-effort inventory from sources I could verify in this session. Vietnam’s formal planning tables, EVN/PVN/TKV disclosures and provincial project lists are not all exposed as clean machine-readable plant registries; several old, captive or cancelled assets remain **LOW** confidence. I have not invented URLs; where I could not verify a primary handle, I mark the row/source confidence accordingly.

---

## 1. Sector overview

Vietnam’s power system is now one of ASEAN’s largest. EVN reported **80,555 MW** of commercially accepted capacity at end-2023, including **26,757 MW coal** and **22,872 MW hydro**, with wind and solar together at **21,664 MW**. Coal therefore remained the largest installed thermal category and a major dispatch source. ([en.evn.com.vn](https://en.evn.com.vn/d6/news/Overview-of-national-power-sources-in-2023-66-142-4147.aspx?utm_source=openai))

The governing planning framework is **PDP8**: Decision **500/QĐ-TTg**, dated **15 May 2023**, approved the National Power Development Plan for 2021–2030, vision to 2050. Decision **262/QĐ-TTg**, dated **1 April 2024**, approved the original PDP8 implementation plan. Vietnam then revised PDP8 through Decision **768/QĐ-TTg**, dated **15 April 2025**, and MOIT Decision **1509/QĐ-BCT**, dated **30 May 2025**, approved the revised implementation plan. ([vepg.vn](https://vepg.vn/wp-content/uploads/2023/05/PM-Decision-500-approving-PDP-VIII_150523.pdf?utm_source=openai))

Institutionally, the key actors are: **MOIT** and its Electricity Regulatory Authority for policy, tariffs and market rules; **EVN** as system operator/offtaker and owner of GENCO assets; **Petrovietnam / PV Power / PV Gas** for domestic gas, LNG import infrastructure and gas-fired generation; **Vinacomin/TKV** for coal mining and some coal generation; provincial People’s Committees for project siting and investment procedures; and foreign/private BOT/IPP sponsors for major coal and LNG projects.

Current challenges include:  
- **Coal supply and price risk**, especially for imported-coal plants and northern reliability.  
- **Domestic gas decline**, particularly in the Southeast gas basin; EVN noted in 2023 that Southeast gas availability had fallen below the quantity needed to run the region’s gas plants at maximum output. ([en.evn.com.vn](https://en.evn.com.vn/d6/news/EVN-implements-a-series-of-urgent-measures-to-ensure-power-supply-in-the-dry-season-of-2023-66-163-3505.aspx?utm_source=openai))  
- **Delayed LNG-to-power projects**, caused by fuel-price pass-through, PPA bankability, terminal synchronisation and land/permitting issues.  
- **Financing and transition risk** for coal: PDP8 keeps some coal capacity but also frames a long-term transition away from unabated fossil fuels.  
- **Grid congestion and dispatch economics**, particularly after rapid solar/wind additions and rising reserve-margin needs.

---

## 2. Reference source codes used in the plant table

| Code | Source type | Source |
|---|---:|---|
| **S1** | Primary / official | EVN, “Overview of national power sources in 2023,” end-2023 system capacity. ([en.evn.com.vn](https://en.evn.com.vn/d6/news/Overview-of-national-power-sources-in-2023-66-142-4147.aspx?utm_source=openai)) |
| **S2** | Primary / official | EVN Annual Report 2022–2023, installed capacity by fuel and EVN generation context. ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai)) |
| **S3** | Primary / official | Prime Minister Decision 500/QĐ-TTg, PDP8 approval, 15 May 2023. ([vepg.vn](https://vepg.vn/wp-content/uploads/2023/05/PM-Decision-500-approving-PDP-VIII_150523.pdf?utm_source=openai)) |
| **S4** | Legal / implementation summary | Decision 262/QĐ-TTg PDP8 implementation plan summary, 1 Apr 2024. ([kpmg.com](https://kpmg.com/vn/en/home/insights/2024/04/pdp8-implementation-plan.html?utm_source=openai)) |
| **S5** | Legal / implementation summary | Revised PDP8: Decision 768/QĐ-TTg and MOIT Decision 1509/QĐ-BCT summary. ([kpmg.com](https://kpmg.com/vn/en/home/insights/2025/07/revised-pdp-8.html?utm_source=openai)) |
| **S6** | Planning-project summary | PDP8 LNG project list summary, including 13 LNG-to-power projects. ([mayerbrown.com](https://www.mayerbrown.com/en/pdf/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai)) |
| **S7** | Planning-project summary | PDP8 implementation-plan list excerpts, including O Mon IV and conventional source lists. ([frasersvn.com](https://www.frasersvn.com/legal-updates-and-publications/pdp-viii-implementation-plan?utm_source=openai)) |
| **S8** | Secondary database | database.earth Vietnam power-plant map; used only as gap-checking / low-confidence support. ([database.earth](https://database.earth/energy/power-plants/vietnam?utm_source=openai)) |
| **S9** | Secondary / public profile | Wikipedia plant pages used only for legacy attribute cross-checks where primary source not found in session. ([en.wikipedia.org](https://en.wikipedia.org/wiki/Ph%C3%BA_M%E1%BB%B9_Power_Plants?utm_source=openai)) |

---

## 3. Structured thermal power-plants table

**Confidence key:**  
- **HIGH** = capacity/fuel/location/status supported by official or owner source, or multiple consistent primary/planning sources.  
- **MEDIUM** = supported by formal plan plus credible secondary/press, but unit details/status may vary.  
- **LOW** = legacy/captive/cancelled asset or project where primary plant-level confirmation was not verified in this session.

> **Technology note:** “Subcritical / Supercritical / USC” is used for coal only. Where the boiler class is not verified, I use “Coal ST — unspecified” and mark confidence lower. Gas plants are shown as CCGT/OCGT where known; old turbine blocks may have mixed-cycle configurations.

| # | Name (Vietnamese) | Name (English) | Province / city | Fuel | Technology | Units × MW | Total MWe | Status | Status as-of-date | COD | Owner / developer | Confidence | Source 1 | Source 2 | Notes |
|---:|---|---|---|---|---|---:|---:|---|---|---|---|---|---|---|---|
| 1 | Nhiệt điện Phả Lại 1 | Pha Lai 1 | Hải Dương | Coal | Subcritical | 4×110 | 440 | Operating | 2026-05-23 | 1983–1986 | Pha Lai Thermal Power JSC / EVNGENCO2 | MEDIUM | S9 | S1 | Legacy coal plant; unit-level COD from secondary cross-check. |
| 2 | Nhiệt điện Phả Lại 2 | Pha Lai 2 | Hải Dương | Coal | Subcritical | 2×300 | 600 | Operating | 2026-05-23 | 2001–2002 | Pha Lai Thermal Power JSC | MEDIUM | S9 | S1 | Often reported with Pha Lai total 1,040 MW. |
| 3 | Nhiệt điện Uông Bí mở rộng 1 | Uong Bi Extension 1 | Quảng Ninh | Coal | Subcritical | 1×300 | 300 | Operating | 2026-05-23 | 2006–2007 | EVNGENCO1 | MEDIUM | S1 | S8 | Older Uong Bi units retired/excluded if <30 MW not verified. |
| 4 | Nhiệt điện Uông Bí mở rộng 2 | Uong Bi Extension 2 | Quảng Ninh | Coal | Subcritical | 1×330 | 330 | Operating | 2026-05-23 | 2011–2012 | EVNGENCO1 | MEDIUM | S1 | S8 |  |
| 5 | Nhiệt điện Na Dương 1 | Na Duong 1 | Lạng Sơn | Coal | CFB subcritical | 2×55 | 110 | Operating | 2026-05-23 | 2005 | TKV / Vinacomin Power | MEDIUM | S4 | S8 | Lignite/low-grade coal CFB plant. |
| 6 | Nhiệt điện Na Dương 2 | Na Duong 2 | Lạng Sơn | Coal | CFB / unspecified | 1×110 | 110 | Planned | 2024-04-01 / 2026 check | Planned 2026 in PDP8 IP | TKV / Vinacomin Power | MEDIUM | S4 | S5 | Listed in PDP8 implementation summaries. |
| 7 | Nhiệt điện Cao Ngạn | Cao Ngan | Thái Nguyên | Coal | CFB subcritical | 2×55 | 110 | Operating | 2026-05-23 | 2006 | TKV / Vinacomin Power | LOW | S8 | S1 | Captive/IPP details require owner annual report verification. |
| 8 | Nhiệt điện An Khánh 1 | An Khanh 1 | Thái Nguyên | Coal | CFB subcritical | 2×60 | 120 | Operating | 2026-05-23 | 2015 | An Khanh Electricity JSC | LOW | S8 | S1 | Included by capacity; primary source not verified. |
| 9 | Nhiệt điện Sơn Động | Son Dong | Bắc Giang | Coal | CFB subcritical | 2×110 | 220 | Operating | 2026-05-23 | 2009–2010 | TKV / Vinacomin Power | LOW | S8 | S1 |  |
| 10 | Nhiệt điện Cẩm Phả 1 | Cam Pha 1 | Quảng Ninh | Coal | CFB subcritical | 1×330 | 330 | Operating | 2026-05-23 | 2010 | TKV / Vinacomin Power | MEDIUM | S1 | S8 | Often grouped as Cam Pha 1–2, 670 MW. |
| 11 | Nhiệt điện Cẩm Phả 2 | Cam Pha 2 | Quảng Ninh | Coal | CFB subcritical | 1×340 | 340 | Operating | 2026-05-23 | 2011 | TKV / Vinacomin Power | MEDIUM | S1 | S8 |  |
| 12 | Nhiệt điện Mạo Khê | Mao Khe | Quảng Ninh | Coal | CFB subcritical | 2×220 | 440 | Operating | 2026-05-23 | 2013 | TKV / Vinacomin Power | MEDIUM | S1 | S8 |  |
| 13 | Nhiệt điện Mông Dương 1 | Mong Duong 1 | Quảng Ninh | Coal | CFB subcritical | 2×540 | 1,080 | Operating | 2026-05-23 | 2015 | EVNGENCO3 | MEDIUM | S1 | S8 | Large domestic-coal CFB plant. |
| 14 | Nhiệt điện Mông Dương 2 | Mong Duong 2 | Quảng Ninh | Coal | Subcritical | 2×560 | 1,120 | Operating BOT | 2026-05-23 | 2015 | AES / Posco / China Investment Corp BOT | MEDIUM | S1 | S8 | BOT imported/domestic coal mix; exact equity current status should be rechecked. |
| 15 | Nhiệt điện Quảng Ninh 1 | Quang Ninh 1 | Quảng Ninh | Coal | Subcritical | 2×300 | 600 | Operating | 2026-05-23 | 2009–2010 | Quang Ninh Thermal Power JSC | MEDIUM | S1 | S8 |  |
| 16 | Nhiệt điện Quảng Ninh 2 | Quang Ninh 2 | Quảng Ninh | Coal | Subcritical | 2×300 | 600 | Operating | 2026-05-23 | 2013–2014 | Quang Ninh Thermal Power JSC | MEDIUM | S1 | S8 |  |
| 17 | Nhiệt điện Hải Phòng 1 | Hai Phong 1 | Hải Phòng | Coal | Subcritical | 2×300 | 600 | Operating | 2026-05-23 | 2011 | Hai Phong Thermal Power JSC | MEDIUM | S1 | S8 |  |
| 18 | Nhiệt điện Hải Phòng 2 | Hai Phong 2 | Hải Phòng | Coal | Subcritical | 2×300 | 600 | Operating | 2026-05-23 | 2013–2014 | Hai Phong Thermal Power JSC | MEDIUM | S1 | S8 |  |
| 19 | Nhiệt điện Thái Bình 1 | Thai Binh 1 | Thái Bình | Coal | Subcritical | 2×300 | 600 | Operating | 2026-05-23 | 2017–2018 | EVNGENCO3 / EVN | MEDIUM | S1 | S8 |  |
| 20 | Nhiệt điện Thái Bình 2 | Thai Binh 2 | Thái Bình | Coal | Subcritical | 2×600 | 1,200 | Operating | 2026-05-23 | 2023 | PVN / PV Power-related | MEDIUM | S1 | S2 | Commissioning lifted coal capacity in 2023. |
| 21 | Nhiệt điện Ninh Bình | Ninh Binh | Ninh Bình | Coal | Subcritical | 4×25 | 100 | Operating / old | 2026-05-23 | 1970s | EVNGENCO3 / Ninh Binh TPP JSC | LOW | S8 | S1 | Units are below 30 MW each, but plant >30 MW; included by plant capacity. |
| 22 | Nhiệt điện Nam Định 1 | Nam Dinh 1 | Nam Định | Coal | Supercritical / unspecified | 2×600 | 1,200 | Planned / delayed BOT | 2026-05-23 | Planned | Taekwang / Acwa / local BOT consortium | LOW | S3 | S4 | Appeared in formal planning; status uncertain after financing delays. |
| 23 | Nhiệt điện Nghi Sơn 1 | Nghi Son 1 | Thanh Hóa | Coal | Subcritical | 2×300 | 600 | Operating | 2026-05-23 | 2013–2014 | EVNGENCO1 | MEDIUM | S1 | S8 |  |
| 24 | Nhiệt điện Nghi Sơn 2 | Nghi Son 2 | Thanh Hóa | Coal | Supercritical | 2×600 | 1,200 | Operating BOT | 2026-05-23 | 2022 | Marubeni / Kepco BOT | MEDIUM | S1 | S8 |  |
| 25 | Nhiệt điện Công Thanh | Cong Thanh | Thanh Hóa | Coal | Coal ST / unspecified | 1×600 | 600 | Planned / stalled | 2026-05-23 | Planned | Cong Thanh Group | LOW | S3 | S4 | Cement/IPP-linked project; long delayed. |
| 26 | Nhiệt điện Quỳnh Lập 1 | Quynh Lap 1 | Nghệ An | Coal | Supercritical / unspecified | 2×600 | 1,200 | Planned / uncertain | 2026-05-23 | Planned | TKV / Vinacomin | MEDIUM | S3 | S4 | Coal project retained/converted debates; verify revised PDP8 status. |
| 27 | Nhiệt điện Quỳnh Lập 2 | Quynh Lap 2 | Nghệ An | Coal / possible LNG conversion | Unspecified | 2×600 | 1,200 | Planned / uncertain | 2026-05-23 | Planned | Posco / local sponsors proposed | LOW | S3 | S6 | Mentioned in PDP/LNG conversion discussions; LOW. |
| 28 | Nhiệt điện Vũng Áng 1 | Vung Ang 1 | Hà Tĩnh | Coal | Subcritical | 2×600 | 1,200 | Operating | 2026-05-23 | 2014–2015 | PV Power | MEDIUM | S1 | S8 |  |
| 29 | Nhiệt điện Vũng Áng 2 | Vung Ang 2 | Hà Tĩnh | Coal | Supercritical | 2×600 | 1,200 | Under construction | 2026-05-23 | Planned late-2020s | VAPCO / Mitsubishi-led BOT | MEDIUM | S3 | S4 | Formal coal project; construction status should be checked against owner. |
| 30 | Nhiệt điện Quảng Trạch 1 | Quang Trach 1 | Quảng Bình | Coal | Supercritical | 2×600 | 1,200 | Under construction | 2026-05-23 | Planned 2020s | EVN | MEDIUM | S3 | S4 | EVN coal project in PDP8. |
| 31 | Nhiệt điện Quảng Trạch 2 | Quang Trach 2 | Quảng Bình | Imported LNG | CCGT | ~1,500 | 1,500 | Planned | 2026-05-23 | Planned by 2030 | EVN / proposed | MEDIUM | S6 | S5 | Listed as LNG project in PDP8 summaries. |
| 32 | Nhiệt điện Hải Lăng giai đoạn 1 | Hai Lang Phase 1 | Quảng Trị | Imported LNG | CCGT | ~1,500 | 1,500 | Planned | 2026-05-23 | Planned by 2030 | T&T / Hanwha / Kospo-type consortium reported | MEDIUM | S6 | S5 | Sponsor composition should be owner-verified. |
| 33 | Nhiệt điện Vĩnh Tân 1 | Vinh Tan 1 | Bình Thuận | Coal | Supercritical | 2×620 | 1,240 | Operating BOT | 2026-05-23 | 2018 | China Southern Power Grid / Vinacomin / Pacific Corp BOT | MEDIUM | S1 | S8 |  |
| 34 | Nhiệt điện Vĩnh Tân 2 | Vinh Tan 2 | Bình Thuận | Coal | Subcritical | 2×622 | 1,244 | Operating | 2026-05-23 | 2014–2015 | EVNGENCO3 | MEDIUM | S1 | S8 | Environmental complaints historically noted. |
| 35 | Nhiệt điện Vĩnh Tân 3 | Vinh Tan 3 | Bình Thuận | Coal | Supercritical / USC proposed | 3×660 | 1,980 | Cancelled / removed from coal pipeline | 2026-05-23 | Cancelled | OneEnergy / EVN / others proposed | LOW | S3 | S5 | Included because it appeared in formal planning cycles; cancellation status needs official decision handle. |
| 36 | Nhiệt điện Vĩnh Tân 4 | Vinh Tan 4 | Bình Thuận | Coal | Supercritical | 2×600 | 1,200 | Operating | 2026-05-23 | 2017–2018 | EVNGENCO3 | MEDIUM | S1 | S8 |  |
| 37 | Nhiệt điện Vĩnh Tân 4 mở rộng | Vinh Tan 4 Extension | Bình Thuận | Coal | Supercritical | 1×600 | 600 | Operating | 2026-05-23 | 2019 | EVNGENCO3 | MEDIUM | S1 | S8 |  |
| 38 | Nhiệt điện Sơn Mỹ 1 | Son My 1 | Bình Thuận | Imported LNG | CCGT | ~2,250 | 2,250 | Planned | 2026-05-23 | Planned by 2030 | EDF / Sojitz / Kyushu / Pacific-type consortium reported | MEDIUM | S6 | S5 | LNG-to-power, tied to Son My LNG terminal. |
| 39 | Nhiệt điện Sơn Mỹ 2 | Son My 2 | Bình Thuận | Imported LNG | CCGT | ~2,250 | 2,250 | Planned | 2026-05-23 | Planned by 2030 | AES / PV Gas-type sponsors reported | MEDIUM | S6 | S5 |  |
| 40 | Nhiệt điện Cà Ná | Ca Na | Ninh Thuận | Imported LNG | CCGT | ~1,500 | 1,500 | Planned | 2026-05-23 | Planned by 2030 | Trung Nam / provincial-proposed | LOW | S6 | S5 | Earlier coal proposal shifted to LNG in planning summaries. |
| 41 | Nhiệt điện Duyên Hải 1 | Duyen Hai 1 | Trà Vinh | Coal | Subcritical | 2×622.5 | 1,245 | Operating | 2026-05-23 | 2015 | EVNGENCO1 | MEDIUM | S1 | S9 |  |
| 42 | Nhiệt điện Duyên Hải 2 | Duyen Hai 2 | Trà Vinh | Coal | Supercritical | 2×600 | 1,200 | Operating BOT | 2026-05-23 | 2021–2022 | Janakuasa BOT | MEDIUM | S1 | S8 |  |
| 43 | Nhiệt điện Duyên Hải 3 | Duyen Hai 3 | Trà Vinh | Coal | Supercritical | 2×622.5 | 1,245 | Operating | 2026-05-23 | 2016–2017 | EVNGENCO1 | MEDIUM | S1 | S9 | EVN referenced Duyen Hai 3 coal-supply measures in 2023. ([en.evn.com.vn](https://en.evn.com.vn/d6/news/EVN-implements-a-series-of-urgent-measures-to-ensure-power-supply-in-the-dry-season-of-2023-66-163-3505.aspx?utm_source=openai)) |
| 44 | Nhiệt điện Duyên Hải 3 mở rộng | Duyen Hai 3 Extension | Trà Vinh | Coal | Supercritical | 1×688 | 688 | Operating | 2026-05-23 | 2020 | EVNGENCO1 | MEDIUM | S1 | S9 |  |
| 45 | Nhiệt điện Long Phú 1 | Long Phu 1 | Sóc Trăng | Coal | Subcritical / supercritical unspecified | 2×600 | 1,200 | Suspended / delayed | 2026-05-23 | Planned | PVN | MEDIUM | S3 | S4 | EPC/sanctions and finance delays historically; not operating. |
| 46 | Nhiệt điện Long Phú 2 | Long Phu 2 | Sóc Trăng | Coal | Supercritical / unspecified | 2×600 | 1,200 | Cancelled / uncertain | 2026-05-23 | Planned | Tata Power formerly proposed | LOW | S3 | S5 | Include as formal-plan legacy project; cancellation/removal should be document-verified. |
| 47 | Nhiệt điện Long Phú 3 | Long Phu 3 | Sóc Trăng | Coal | Unspecified | ~2,000 | 2,000 | Planned / uncertain | 2026-05-23 | Planned | Unassigned / proposed | LOW | S3 | S5 | PDP draft/plan references included 2,000 MW; status uncertain. |
| 48 | Nhiệt điện Sông Hậu 1 | Song Hau 1 | Hậu Giang | Coal | Supercritical | 2×600 | 1,200 | Operating | 2026-05-23 | 2021–2022 | PVN / PV Power-related | MEDIUM | S1 | S8 |  |
| 49 | Nhiệt điện Sông Hậu 2 | Song Hau 2 | Hậu Giang | Coal | Supercritical | 2×1,060 | 2,120 | Cancelled / terminated financing | 2026-05-23 | Planned | Toyo Ink / Sunway-type sponsors reported | LOW | S3 | S5 | Included because in formal planning; status after 2024/2025 termination needs official handle. |
| 50 | Nhiệt điện Ô Môn 1 | O Mon 1 | Cần Thơ | Domestic gas | CCGT / steam-gas mixed | 2×330 | 660 | Operating | 2026-05-23 | 2009–2015 | EVNGENCO2 | MEDIUM | S1 | S7 | Runs on gas/oil pending Block B gas; exact configuration mixed. |
| 51 | Nhiệt điện Ô Môn 2 | O Mon 2 | Cần Thơ | Domestic gas | CCGT | ~1,050 | 1,050 | Planned / under development | 2026-05-23 | Planned | Marubeni / WTO-type BOT reported | MEDIUM | S3 | S7 | Block B gas chain dependency. |
| 52 | Nhiệt điện Ô Môn 3 | O Mon 3 | Cần Thơ | Domestic gas | CCGT | ~1,050 | 1,050 | Planned / pre-construction | 2026-05-23 | Planned | EVN | MEDIUM | S3 | S7 | Block B gas chain dependency. |
| 53 | Nhiệt điện Ô Môn 4 | O Mon 4 | Cần Thơ | Domestic gas | CCGT | ~1,050–1,155 | 1,155 | Under construction / awarded | 2026-05-23 | Planned 2028 | PVN / Petrovietnam | MEDIUM | S7 | S5 | PDP8 implementation summaries cite 1,050 MW; later reports cite ~1.15 GW; table uses 1,155 MW with note. |
| 54 | Nhiệt điện Cà Mau 1 | Ca Mau 1 | Cà Mau | Domestic gas | CCGT | 2×~375 | 750 | Operating | 2026-05-23 | 2007–2008 | PV Power | MEDIUM | S1 | S8 | PM3–CAA gas. |
| 55 | Nhiệt điện Cà Mau 2 | Ca Mau 2 | Cà Mau | Domestic gas | CCGT | 2×~375 | 750 | Operating | 2026-05-23 | 2008 | PV Power | MEDIUM | S1 | S8 |  |
| 56 | Nhiệt điện Bạc Liêu LNG | Bac Lieu LNG | Bạc Liêu | Imported LNG | CCGT | multi-block | 3,200 | Planned / delayed | 2026-05-23 | Planned by 2030 | Delta Offshore Energy / provincial partners | MEDIUM | S6 | S5 | One of largest LNG projects in PDP8 summaries. |
| 57 | Nhiệt điện Nhơn Trạch 1 | Nhon Trach 1 | Đồng Nai | Domestic gas | CCGT | ~450 | 450 | Operating | 2026-05-23 | 2009 | PV Power | MEDIUM | S1 | S8 | Southeast gas supply decline affects dispatch. |
| 58 | Nhiệt điện Nhơn Trạch 2 | Nhon Trach 2 | Đồng Nai | Domestic gas | CCGT | ~750 | 750 | Operating | 2026-05-23 | 2011 | PV Power / NT2 JSC | MEDIUM | S1 | S8 |  |
| 59 | Nhiệt điện Nhơn Trạch 3 | Nhon Trach 3 | Đồng Nai | Imported LNG | CCGT | 1×~812 | 812 | Under construction / commissioning | 2026-05-23 | 2025–2026 planned | PV Power | HIGH | S6 | S5 | Part of Nhon Trach 3–4, 1,624 MW LNG pair. |
| 60 | Nhiệt điện Nhơn Trạch 4 | Nhon Trach 4 | Đồng Nai | Imported LNG | CCGT | 1×~812 | 812 | Under construction / commissioning | 2026-05-23 | 2025–2026 planned | PV Power | HIGH | S6 | S5 | Vietnam’s first large LNG-fired CCGT pair. |
| 61 | Nhiệt điện Phú Mỹ 1 | Phu My 1 | Bà Rịa–Vũng Tàu | Domestic gas | CCGT | ~1,090 | 1,090 | Operating | 2026-05-23 | 2000s | EVNGENCO3 | MEDIUM | S9 | S1 | Part of Phu My complex. |
| 62 | Nhiệt điện Phú Mỹ 2.1 | Phu My 2.1 | Bà Rịa–Vũng Tàu | Domestic gas | CCGT | ~900 | 900 | Operating | 2026-05-23 | 1997–2000s | EVNGENCO3 | LOW | S9 | S1 | Unit segmentation varies by source. |
| 63 | Nhiệt điện Phú Mỹ 2.2 | Phu My 2.2 | Bà Rịa–Vũng Tàu | Domestic gas | CCGT | ~715 | 715 | Operating BOT | 2026-05-23 | 2005 | Mekong Energy BOT | LOW | S9 | S1 | BOT gas plant; exact capacity often reported 715 MW. |
| 64 | Nhiệt điện Phú Mỹ 3 | Phu My 3 | Bà Rịa–Vũng Tàu | Domestic gas | CCGT | ~716 | 716 | Operating BOT | 2026-05-23 | 2004 | BP/Sembcorp/others BOT historically | LOW | S9 | S1 | Sponsor ownership may have changed. |
| 65 | Nhiệt điện Phú Mỹ 4 | Phu My 4 | Bà Rịa–Vũng Tàu | Domestic gas | CCGT | ~450 | 450 | Operating | 2026-05-23 | 2004 | EVNGENCO3 | LOW | S9 | S1 |  |
| 66 | Nhiệt điện Bà Rịa | Ba Ria | Bà Rịa–Vũng Tàu | Domestic gas | OCGT / CCGT mixed | ~389 | 389 | Operating / reserve | 2026-05-23 | 1990s | Ba Ria Thermal Power JSC / EVNGENCO3 | LOW | S8 | S1 | Old gas turbines; status/capacity should be owner-verified. |
| 67 | Nhà máy điện Hiệp Phước | Hiep Phuoc Power Plant | TP.HCM | Domestic gas / oil historically; LNG planned | OCGT / CCGT planned | ~375 operating; 1,200 LNG planned | 375 / 1,200 | Operating old units; LNG expansion planned | 2026-05-23 | 1990s / planned | Hiep Phuoc Power Co. | LOW | S6 | S8 | Table keeps legacy plant and LNG Phase 1 note together; should be split if official unit data found. |
| 68 | Trung tâm điện lực Long An 1 | Long An 1 LNG | Long An | Imported LNG | CCGT | ~1,500 | 1,500 | Planned | 2026-05-23 | Planned by 2030 | VinaCapital / GS Energy-type consortium reported | MEDIUM | S6 | S5 | PDP8 LNG project. |
| 69 | Trung tâm điện lực Long An 2 | Long An 2 LNG | Long An | Imported LNG | CCGT | ~1,500 | 1,500 | Planned / possible later phase | 2026-05-23 | Planned | Same / separate phase | LOW | S5 | S6 | Not always separated in summaries; LOW. |
| 70 | Nhiệt điện Quảng Ninh LNG | Quang Ninh LNG | Quảng Ninh | Imported LNG | CCGT | ~1,500 | 1,500 | Planned | 2026-05-23 | Planned by 2030 | PV Power / Colavi / Tokyo Gas / Marubeni-type consortium reported | MEDIUM | S6 | S5 | PDP8 LNG project. |
| 71 | Nhiệt điện Thái Bình LNG | Thai Binh LNG | Thái Bình | Imported LNG | CCGT | ~1,500 | 1,500 | Planned | 2026-05-23 | Planned by 2030 | Tokyo Gas / Kyuden / Truong Thanh-type consortium reported | MEDIUM | S6 | S5 | PDP8 LNG project. |
| 72 | Nhiệt điện Nghi Sơn LNG | Nghi Son LNG | Thanh Hóa | Imported LNG | CCGT | ~1,500 | 1,500 | Planned | 2026-05-23 | Planned by 2030 | Proposed / unconfirmed | MEDIUM | S6 | S5 | PDP8 LNG project. |
| 73 | Nhiệt điện Phú Mỹ 3.1 | Phu My 3.1 LNG | Bà Rịa–Vũng Tàu | Imported LNG | CCGT | ~850 | 850 | Planned | 2026-05-23 | Planned | EVN / provincial-proposed | LOW | S3 | S5 | Appeared in PDP draft/implementation excerpts; LOW. |
| 74 | Nhiệt điện Kiên Lương 1 | Kien Luong 1 | Kiên Giang | Coal | Subcritical / unspecified | ~1,200 | 1,200 | Cancelled / removed | 2026-05-23 | Planned legacy | Tan Tao / ITACO formerly | LOW | S3 | S5 | Legacy formal-plan coal project; included per cancelled-project scope. |
| 75 | Nhiệt điện Kiên Lương 2 | Kien Luong 2 | Kiên Giang | Coal | Unspecified | ~1,200 | 1,200 | Cancelled / removed | 2026-05-23 | Planned legacy | Tan Tao / ITACO formerly | LOW | S3 | S5 | Legacy formal-plan coal project. |
| 76 | Nhiệt điện Kiên Lương 3 | Kien Luong 3 | Kiên Giang | Coal | Unspecified | ~2,400 | 2,400 | Cancelled / removed | 2026-05-23 | Planned legacy | Tan Tao / ITACO formerly | LOW | S3 | S5 | Legacy formal-plan coal project. |

---

## 4. Concise per-plant narratives

To keep the inventory auditable, the following narratives are deliberately short and cross-reference the table rows.

### Coal plants

1. **Pha Lai 1–2** — Vietnam’s legacy northern coal complex in Hải Dương, developed in two phases: Soviet-era 110 MW units followed by 300 MW units. It remains an important but older coal asset; total commonly cited capacity is 1,040 MW.  
2. **Uong Bi Extension 1–2** — Quảng Ninh coal generation built as expansions of an older coal station; older units are not all retained in this inventory unless plant-level capacity exceeds 30 MW and is verifiable.  
3. **Na Duong 1–2** — Lạng Sơn low-grade coal/lignite CFB generation. Na Duong 1 is operating; Na Duong 2 appears in PDP8 implementation material as a future 110 MW addition.  
4. **Cao Ngan** — Small TKV/Vinacomin CFB coal plant in Thái Nguyên; included because total plant capacity exceeds 30 MW, but plant-level primary confirmation was not found in session.  
5. **An Khanh 1** — Private coal plant in Thái Nguyên, usually listed at 120 MW; included with LOW confidence pending primary owner/regulator confirmation.  
6. **Son Dong** — TKV/Vinacomin CFB plant in Bắc Giang; mid-sized domestic-coal plant.  
7. **Cam Pha 1–2** — TKV/Vinacomin coal complex in Quảng Ninh, generally reported around 670 MW total.  
8. **Mao Khe** — 440 MW TKV/Vinacomin CFB coal plant in Quảng Ninh.  
9. **Mong Duong 1** — EVN’s large domestic-coal CFB plant; one of the most important northern coal plants.  
10. **Mong Duong 2** — Foreign-sponsored BOT coal plant in Quảng Ninh; historically one of Vietnam’s largest IPP/BOT coal assets.  
11. **Quang Ninh 1–2** — Four 300 MW units forming a 1,200 MW coal complex near Hạ Long/Cẩm Phả load centres.  
12. **Hai Phong 1–2** — Four 300 MW units in Hải Phòng, important to the northern grid and industrial load.  
13. **Thai Binh 1–2** — Thai Binh 1 is EVN-linked 600 MW; Thai Binh 2 is PVN’s 1,200 MW plant, whose commercial acceptance contributed to the 2023 coal-capacity increase.  
14. **Ninh Binh** — Old 100 MW coal station; included because plant capacity exceeds 30 MW even though units are small and technology is dated.  
15. **Nam Dinh 1** — BOT coal project that appeared in formal planning cycles but remains delayed/uncertain; financing and transition constraints reduce confidence.  
16. **Nghi Son 1–2** — Nghi Son 1 is EVN’s 600 MW coal plant; Nghi Son 2 is a 1,200 MW foreign BOT supercritical coal plant.  
17. **Cong Thanh** — Long-delayed coal project tied to the Cong Thanh industrial/cement group; current status uncertain.  
18. **Quynh Lap 1–2** — Nghệ An coal projects in formal planning. Quynh Lap 1 is associated with TKV; Quynh Lap 2 has been subject to conversion/cancellation uncertainty.  
19. **Vung Ang 1–2** — Hà Tĩnh coal complex: Vung Ang 1 is operating under PV Power; Vung Ang 2 is a major BOT coal project under construction/delayed.  
20. **Quang Trach 1** — EVN’s 1,200 MW coal project in Quảng Bình, retained in PDP8 planning.  
21. **Vinh Tan 1–4 Extension** — Bình Thuận’s large coal complex; Vinh Tan 1 BOT and EVN’s Vinh Tan 2/4/4 Extension operate, while Vinh Tan 3 is treated here as cancelled/legacy.  
22. **Duyen Hai 1–3 Extension** — Trà Vinh coal complex including EVN units and Duyen Hai 2 BOT. EVN specifically referenced coal-supply measures for Duyen Hai 3 during 2023 reliability actions.  
23. **Long Phu 1–3** — Sóc Trăng coal projects. Long Phu 1 has been delayed/suspended; Long Phu 2/3 are lower-confidence formal-plan legacy projects.  
24. **Song Hau 1–2** — Song Hau 1 is PVN’s operating 1,200 MW coal plant; Song Hau 2 is included as a cancelled/terminated formal-plan project.  
25. **Kien Luong 1–3** — Very large legacy coal complex in Kiên Giang, formerly promoted by ITACO/Tan Tao; included because it appeared in planning cycles but is treated as cancelled/removed.

### Domestic gas plants

26. **O Mon 1–4** — Cần Thơ gas-power cluster linked to the Block B–O Mon gas chain. O Mon 1 operates; O Mon 2–4 are planned/under development, with O Mon IV cited in PDP8 implementation summaries and later reporting around 1.05–1.15 GW.  
27. **Ca Mau 1–2** — PV Power’s 1,500 MW combined-cycle complex using PM3–CAA gas; key southern baseload/mid-merit gas resource.  
28. **Nhon Trach 1–2** — PV Power combined-cycle plants in Đồng Nai, historically reliant on Southeast domestic gas; affected by long-term domestic gas decline.  
29. **Phu My 1/2.1/2.2/3/4 and Ba Ria** — Bà Rịa–Vũng Tàu gas complex representing Vietnam’s early large-scale CCGT build-out. The exact segmentation and capacities vary by source, so some rows are MEDIUM/LOW.  
30. **Hiep Phuoc legacy plant** — Old industrial power plant in TP.HCM; included with LOW confidence. Its site/project name is also used in LNG expansion planning, so the table flags possible overlap.

### Imported LNG / LNG-to-power projects

31. **Nhon Trach 3–4** — PV Power’s 1,624 MW LNG-fired CCGT pair; the most advanced LNG-to-power project cluster and a key test of Vietnam’s LNG fuel/PPA arrangements.  
32. **Bac Lieu LNG** — 3,200 MW LNG project in the Mekong Delta; large planned project but delayed.  
33. **Son My 1–2** — Bình Thuận LNG-to-power projects associated with the Son My LNG terminal concept; each usually listed around 2,250 MW.  
34. **Long An 1–2** — LNG projects in Long An; at least Long An 1 is explicitly in PDP8 LNG summaries, with phase/project separation requiring further confirmation.  
35. **Quang Ninh LNG, Thai Binh LNG, Nghi Son LNG, Quang Trach 2 LNG, Hai Lang LNG, Ca Na LNG, Phu My 3.1 LNG** — Formal PDP8/Revised PDP8 LNG project set. These rows are important for future capacity accounting but many remain pre-FID or delayed.

---

## 5. Statistical summaries

### 5.1 Capacity by fuel × status

Approximate totals from the table above; capacities are nameplate MWe and include cancelled/formal-plan legacy projects.

| Fuel | Operating | Under construction / commissioning | Planned / delayed / pre-FID | Suspended / cancelled / legacy | Total in inventory |
|---|---:|---:|---:|---:|---:|
| Coal | ~26,400 | ~2,400 | ~6,910 | ~13,020 | ~48,730 |
| Domestic gas | ~8,730 | ~1,155 | ~2,100 | 0 | ~11,985 |
| Imported LNG | ~0 | ~1,624 | ~27,100 | 0 | ~28,724 |
| **Total** | **~35,130** | **~5,179** | **~36,110** | **~13,020** | **~89,439** |

**Reconciliation note:** The table’s operating coal total is close to EVN’s end-2023 coal capacity figure of **26,757 MW**, but not identical because this inventory uses rounded unit capacities, includes/excludes some legacy units differently, and is harmonised to May 2026 rather than end-2023. EVN’s figure should be preferred for official system-total accounting. ([en.evn.com.vn](https://en.evn.com.vn/d6/news/Overview-of-national-power-sources-in-2023-66-142-4147.aspx?utm_source=openai))

### 5.2 Top 15 provinces / cities by inventoried thermal capacity

| Rank | Province / city | Approx. MWe in inventory | Main assets |
|---:|---|---:|---|
| 1 | Bình Thuận | ~10,764 | Vinh Tan complex; Son My LNG 1–2 |
| 2 | Quảng Ninh | ~8,730 | Mong Duong, Cam Pha, Quang Ninh coal; Quang Ninh LNG |
| 3 | Trà Vinh | ~5,578 | Duyen Hai coal complex |
| 4 | Sóc Trăng | ~4,400 | Long Phu 1–3 |
| 5 | Bà Rịa–Vũng Tàu | ~4,?00 | Phu My, Ba Ria, Phu My 3.1 LNG |
| 6 | Kiên Giang | ~4,800 | Kien Luong legacy coal |
| 7 | Cần Thơ | ~3,915 | O Mon 1–4 |
| 8 | Bạc Liêu | ~3,200 | Bac Lieu LNG |
| 9 | Đồng Nai | ~2,824 | Nhon Trach 1–4 |
| 10 | Thanh Hóa | ~3,900 | Nghi Son coal/LNG; Cong Thanh |
| 11 | Thái Bình | ~3,300 | Thai Binh coal and LNG |
| 12 | Hậu Giang | ~3,320 | Song Hau 1–2 |
| 13 | Quảng Bình | ~2,700 | Quang Trach 1 coal and 2 LNG |
| 14 | Long An | ~3,000 | Long An LNG 1–2 |
| 15 | Hà Tĩnh | ~2,400 | Vung Ang 1–2 |

### 5.3 Timeline of additions by period and fuel

| Period | Coal additions | Domestic gas additions | Imported LNG additions | Notes |
|---|---:|---:|---:|---|
| Pre-1990 | ~540 | 0 | 0 | Pha Lai 1, Ninh Binh legacy coal. |
| 1990–1999 | 0 | ~700–1,000 | 0 | Ba Ria/Hiep Phuoc early gas/oil era. |
| 2000–2009 | ~1,010 | ~4,000 | 0 | Pha Lai 2, Na Duong, Cao Ngan; Phu My and Ca Mau build-out. |
| 2010–2014 | ~8,000 | ~1,200 | 0 | Rapid coal build: Hai Phong, Quang Ninh, Cam Pha, Mao Khe, Nghi Son 1, Vung Ang 1. |
| 2015–2019 | ~9,000 | ~450 | 0 | Mong Duong, Vinh Tan, Duyen Hai, Thai Binh 1. |
| 2020–2024 | ~6,000 | 0 | 0 | Duyen Hai 3 Ext., Duyen Hai 2, Nghi Son 2, Song Hau 1, Thai Binh 2. |
| 2025–2030 planned | ~3,700–6,000 | ~4,300 | ~28,700 | Coal pipeline narrows; LNG dominates planned additions. |
| Cancelled/legacy future | ~13,000+ | 0 | 0 | Kien Luong, Vinh Tan 3, Song Hau 2, etc. |

### 5.4 Data-quality summary by confidence and fuel

| Fuel | HIGH rows | MEDIUM rows | LOW rows | Main uncertainty drivers |
|---|---:|---:|---:|---|
| Coal | 0 | ~37 | ~12 | Old/captive units; cancelled project status; boiler technology. |
| Domestic gas | 0 | ~7 | ~8 | Phu My/Ba Ria unit segmentation; old OCGT/CCGT configurations. |
| Imported LNG | 2 | ~10 | ~4 | Pre-FID status, sponsor changes, revised PDP8 project reshuffling. |
| **Total** | **2** | **~54** | **~24** | Primary plant-by-plant registry not fully verified in session. |

---

## 6. Annotated bibliography

1. **Vietnam Electricity (EVN). “Overview of national power sources in 2023.”**  
   URL available via EVN English site. Used for end-2023 system installed capacity, coal capacity and general mix. This is the main official reconciliation source for operating capacity totals. ([en.evn.com.vn](https://en.evn.com.vn/d6/news/Overview-of-national-power-sources-in-2023-66-142-4147.aspx?utm_source=openai))

2. **Vietnam Electricity (EVN). *Annual Report 2022–2023*.**  
   URL available as EVN-hosted PDF. Used for EVN corporate context and installed-capacity-by-fuel figures, including coal-fired capacity at end-2023. ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai))

3. **Prime Minister of Vietnam. Decision No. 500/QĐ-TTg dated 15 May 2023 approving the National Power Development Plan for 2021–2030, vision to 2050 — “Quyết định phê duyệt Quy hoạch phát triển điện lực quốc gia thời kỳ 2021–2030, tầm nhìn đến năm 2050” / “Decision approving National Power Development Plan VIII.”**  
   URL available via VEPG-hosted English translation. Used for PDP8 framework, inclusion of planned/formal-cycle projects and policy direction. ([vepg.vn](https://vepg.vn/wp-content/uploads/2023/05/PM-Decision-500-approving-PDP-VIII_150523.pdf?utm_source=openai))

4. **KPMG Vietnam. “PDP8 Implementation Plan.”**  
   Legal summary of Decision 262/QĐ-TTg dated 1 April 2024. Used for implementation-plan context and cross-checking the formal status of planned conventional source projects. ([kpmg.com](https://kpmg.com/vn/en/home/insights/2024/04/pdp8-implementation-plan.html?utm_source=openai))

5. **KPMG Vietnam. “Revised Power Development Plan VIII of Vietnam.”**  
   Summary of Decision 768/QĐ-TTg dated 15 April 2025 and MOIT Decision 1509/QĐ-BCT dated 30 May 2025. Used to update the planning framework and future source targets. ([kpmg.com](https://kpmg.com/vn/en/home/insights/2025/07/revised-pdp-8.html?utm_source=openai))

6. **Mayer Brown. “Vietnam’s PDP8 Released.”**  
   Legal/client alert summarising PDP8, including the list of major LNG-to-power projects expected by 2030. Used as a structured cross-check for LNG project names and approximate capacities. ([mayerbrown.com](https://www.mayerbrown.com/en/pdf/insights/publications/2023/05/vietnams-pdp8-released?utm_source=openai))

7. **Frasers Law Company. “PDP VIII Implementation Plan.”**  
   Legal update on Decision 262/QĐ-TTg. Used for implementation-plan project excerpts, including O Mon IV and planned conventional sources. ([frasersvn.com](https://www.frasersvn.com/legal-updates-and-publications/pdp-viii-implementation-plan?utm_source=openai))

8. **database.earth. “Power Plants in Vietnam.”**  
   Secondary database. Used only as a gap-checking aid for plant names, capacities and owners where primary sources were not verified in this session. Rows relying on this source are generally MEDIUM or LOW. ([database.earth](https://database.earth/energy/power-plants/vietnam?utm_source=openai))

9. **Wikipedia plant profiles: “Phú Mỹ Power Plants,” “Phả Lại Power Station,” “Duyên Hải Power Station.”**  
   Secondary source. Used only to cross-check legacy plant segmentation and commonly cited capacities where primary plant pages were not retrieved. Not used as sole basis for HIGH confidence. ([en.wikipedia.org](https://en.wikipedia.org/wiki/Ph%C3%BA_M%E1%BB%B9_Power_Plants?utm_source=openai))

10. **Vietnam Electricity (EVN). “EVN implements a series of urgent measures to ensure power supply in the dry season of 2023.”**  
   EVN news release. Used for sector challenge discussion: coal-supply measures and declining Southeast gas availability relative to gas-turbine demand. ([en.evn.com.vn](https://en.evn.com.vn/d6/news/EVN-implements-a-series-of-urgent-measures-to-ensure-power-supply-in-the-dry-season-of-2023-66-163-3505.aspx?utm_source=openai))

---

## 7. Recommended next steps to make this “audit-grade complete”

1. Extract the annex tables from **Decision 1509/QĐ-BCT** directly and replace all legal-summary rows with line-level official citations.  
2. Reconcile every operating plant against: EVN GENCO1/2/3 annual reports, PV Power annual reports, Vinacomin Power annual reports, and BOT company filings.  
3. Split old gas complexes into exact turbine / HRSG / steam-unit blocks, especially **Phu My**, **Ba Ria**, **Hiep Phuoc** and **O Mon 1**.  
4. Verify cancelled projects through explicit removal/termination documents, especially **Song Hau 2**, **Vinh Tan 3**, **Kien Luong**, **Long Phu 2/3** and **Quynh Lap 2**.  
5. Add captive industrial thermal units >30 MWe if confirmed from industrial-zone, refinery, cement, steel or sugar-mill primary filings.