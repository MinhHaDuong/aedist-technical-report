# Vietnam thermal generation assets >30 MWe — primary-sourced reference inventory, v0.1  
**Scope:** coal, domestic gas and imported-LNG thermal generation in Vietnam; operating, retired/converted, under construction, planned/pre-FID, and cancelled/deferred projects that appeared in formal planning cycles.  
**Status date used for this inventory:** **23 May 2026**, unless a row gives a more specific source date.  
**Important limitation:** A genuinely complete plant-by-plant inventory for Vietnam requires reconciliation against Vietnamese regulatory annexes, EVN generation-company asset registers, PV Power/PV GAS filings, BOT concession documents, and provincial industrial-zone/captive-power approvals. The table below is a best-effort reference inventory from the sources I could verify in this session. I mark uncertain or weakly sourced rows **LOW** rather than omitting known assets.

---

## 1. Sector overview

Vietnam’s power system is now one of Southeast Asia’s largest. EVN reported total installed system capacity of **82,387 MW in 2024**, of which **coal-fired capacity was 26,757 MW** and **gas + oil-fired capacity was 8,653 MW**; total installed capacity was **80,946 MW in 2023**. ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai))  

Coal remains the largest dispatchable thermal source. EVN’s 2022–2023 annual report shows coal capacity rising from **25,312 MW in 2022** to **26,756 MW in 2023**. EVN also reported persistent fuel-security issues in 2023, including coal delivery shortfalls and declining domestic gas availability for power generation. ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai))  

The core policy framework is **Power Development Plan VIII (PDP8)** and its 2025 revision. The revised PDP8, approved by **Decision 768/QĐ-TTg dated 15 April 2025**, and its implementation guidance under **MOIT Decision 1509/QĐ-BCT dated 30 May 2025**, set 2030 capacity pathways including **31,055 MW coal-fired thermal power**, **10,861–14,930 MW domestic gas-fired thermal power**, and **22,524 MW LNG thermal power**. ([vanban.chinhphu.vn](https://vanban.chinhphu.vn/?docid=215339&pageid=27160&utm_source=openai))  

Key institutional actors are: **EVN** and its GENCOs as legacy owner/offtaker/operator; **MOIT** as energy-sector regulator and PDP implementation authority; **PVN / PV Power / PV GAS** for gas-fired generation and gas/LNG supply; **TKV/Vinacomin** and **Dong Bac Corporation** for domestic coal supply and coal generation; BOT/IPP sponsors such as **AES, Marubeni, JERA, Sumitomo, CLP, EGATi, Doosan/KEPCO-linked consortia**, and Vietnamese provincial/industrial investors for LNG and captive plants. EVN’s 2024 ownership table attributes **31,085 MW** to EVN + GENCOs, **6,038 MW** to PVN, **1,665 MW** to Vinacomin, **8,268 MW** to BOT plants, and **34,110 MW** to other investors. ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai))  

Current challenges are: fuel security, especially declining domestic gas in the Southeast and Southwest; coal supply logistics and import dependence; delayed LNG-to-power bankability and PPA/GSA issues; grid bottlenecks; the need to replace/repurpose coal under Vietnam’s net-zero 2050 pledge; and the tension between least-cost dispatch, high imported fuel prices, and EVN’s financial position. EVN reported in 2023 that Southeast gas supply was below maximum gas-turbine demand, while coal deliveries to EVN plants also faced shortfalls. ([en.evn.com.vn](https://en.evn.com.vn/d6/news/Overview-of-national-power-sources-in-2023-66-142-4147.aspx?utm_source=openai))  

---

## 2. Per-plant narrative notes — concise

### Coal fleet

- **Phả Lại / Pha Lai** — Vietnam’s legacy northern coal plant in Hải Dương, developed in two stages: older Soviet/Chinese-era subcritical units and later larger units. It remains a benchmark legacy coal asset but has aging-unit reliability and emissions issues. **Confidence: MEDIUM** because unit-level CODs require regulatory confirmation.
- **Uông Bí / Uong Bi** — Historic Quảng Ninh coal station, expanded with newer 300 MW-class units. Some old units have been retired or de-rated. **Confidence: MEDIUM/LOW** on surviving capacity by unit.
- **Ninh Bình / Ninh Binh** — Small legacy coal plant; over 30 MWe but much older and often listed separately from modern coal fleet. **Confidence: LOW** on operating status.
- **Cao Ngạn / Cao Ngan** — TKV/Vinacomin circulating-fluidized-bed coal plant in Thái Nguyên, relatively small by modern standards. **Confidence: MEDIUM**.
- **Na Dương / Na Duong** — TKV/Vinacomin lignite/coal plant in Lạng Sơn, linked to local coal resources; expansion has been periodically planned. **Confidence: MEDIUM**.
- **Sơn Động / Son Dong** — TKV/Vinacomin coal plant in Bắc Giang, built to use domestic coal resources. **Confidence: MEDIUM**.
- **Cẩm Phả / Cam Pha** — Quảng Ninh coal plant associated with TKV, built in two 300 MW-class units. **Confidence: MEDIUM**.
- **Mạo Khê / Mao Khe** — Quảng Ninh coal plant, TKV-linked, 2×220 MW class. **Confidence: MEDIUM**.
- **Quảng Ninh / Quang Ninh** — Large 1,200 MW northern coal plant, one of the main plants supplying the northern system. **Confidence: HIGH** on capacity/location; MEDIUM on unit technology.
- **Hải Phòng / Hai Phong** — Large 1,200 MW coal plant near Hải Phòng; part of the core northern coal fleet. **Confidence: HIGH**.
- **Mông Dương 1 / Mong Duong 1** — EVN/GENCO coal station in Quảng Ninh, developed as part of the Mông Dương complex. **Confidence: HIGH**.
- **Mông Dương 2 / Mong Duong 2** — BOT coal IPP in Quảng Ninh, AES-led; a major private/BOT coal plant. **Confidence: HIGH**.
- **Thái Bình 1 / Thai Binh 1** — EVN/GENCO coal plant in Thái Bình, operating. **Confidence: HIGH**.
- **Thái Bình 2 / Thai Binh 2** — PVN coal plant delayed for years by EPC/contractor and governance problems; now counted in national coal capacity after commissioning. **Confidence: HIGH** on existence/capacity; MEDIUM on exact COD by unit.
- **Nghi Sơn 1 / Nghi Son 1** — EVN coal plant in Thanh Hóa, operating. **Confidence: HIGH**.
- **Nghi Sơn 2 / Nghi Son 2** — BOT coal IPP in Thanh Hóa, supercritical technology, sponsored by international consortium. **Confidence: HIGH**.
- **Vũng Áng 1 / Vung Ang 1** — PV Power coal plant in Hà Tĩnh, 1,200 MW; important PV Power thermal asset. PV Power materials identify Vũng Áng 1 among its principal plants. ([pvpower.vn](https://pvpower.vn/en/?utm_source=openai))
- **Vũng Áng 2 / Vung Ang 2** — BOT/IPP coal project in Hà Tĩnh, developed after long financing and sponsor changes; under construction/late development in recent years. **Confidence: MEDIUM**.
- **Vũng Áng 3 / Vung Ang 3** — appeared in planning cycles; later studied for LNG/gas conversion by PV Power. ([theinvestor.vn](https://theinvestor.vn/pv-power-says-profit-may-fall-in-2026-despite-higher-output-due-to-extreme-weather-d17723.html?utm_source=openai))
- **Quảng Trạch 1 / Quang Trach 1** — EVN coal project in Quảng Bình, under construction in recent planning cycle. **Confidence: MEDIUM**.
- **Quảng Trạch 2 / Quang Trach 2** — planned coal project, subject to PDP8 sequencing and potential future transition constraints. **Confidence: LOW/MEDIUM**.
- **Vĩnh Tân 1 / Vinh Tan 1** — BOT coal plant in Bình Thuận, operating; part of the major Vĩnh Tân coal-power center. **Confidence: HIGH**.
- **Vĩnh Tân 2 / Vinh Tan 2** — EVN/GENCO coal plant, operating; has faced air-quality and ash-management controversies. **Confidence: HIGH**.
- **Vĩnh Tân 3 / Vinh Tan 3** — planned/cancelled or shelved coal project; appeared in planning but did not proceed as originally intended. **Confidence: LOW/MEDIUM**.
- **Vĩnh Tân 4 / Vinh Tan 4** — EVN/GENCO coal plant; EVN referenced Vĩnh Tân 4 in 2023 fuel-security measures. ([en.evn.com.vn](https://en.evn.com.vn/d6/news/EVN-implements-a-series-of-urgent-measures-to-ensure-power-supply-in-the-dry-season-of-2023-66-163-3505.aspx?utm_source=openai))
- **Duyên Hải 1 / Duyen Hai 1** — EVN/GENCO coal plant in Trà Vinh, operating. **Confidence: HIGH**.
- **Duyên Hải 2 / Duyen Hai 2** — BOT coal plant in Trà Vinh, operating/late commissioning in recent years. **Confidence: MEDIUM/HIGH**.
- **Duyên Hải 3 / Duyen Hai 3** — EVN/GENCO coal plant; EVN referenced Duyên Hải 3 in urgent coal-supply measures in 2023. ([en.evn.com.vn](https://en.evn.com.vn/d6/news/EVN-implements-a-series-of-urgent-measures-to-ensure-power-supply-in-the-dry-season-of-2023-66-163-3505.aspx?utm_source=openai))
- **Duyên Hải 3 extension / Duyen Hai 3 MR** — single-unit expansion at Duyên Hải power center. **Confidence: HIGH**.
- **Long Phú 1 / Long Phu 1** — PVN coal project in Sóc Trăng; severely delayed after sanctions/contractor issues involving Russian supplier Power Machines. **Confidence: MEDIUM**.
- **Long Phú 2 / Long Phu 2** — planned coal BOT project, not built; appeared in planning cycles. **Confidence: LOW/MEDIUM**.
- **Sông Hậu 1 / Song Hau 1** — PVN coal plant in Hậu Giang, operating. **Confidence: MEDIUM/HIGH**.
- **Sông Hậu 2 / Song Hau 2** — planned coal BOT project; investor and financing difficulties, repeatedly delayed. **Confidence: LOW/MEDIUM**.
- **Nam Định 1 / Nam Dinh 1** — planned coal BOT project; delayed and uncertain. **Confidence: LOW/MEDIUM**.
- **Công Thanh / Cong Thanh** — originally coal-linked in Thanh Hóa; MOIT 2025 PDP8 implementation appendix lists **LNG Công Thanh** and notes conversion from coal to LNG. ([moit.gov.vn](https://moit.gov.vn/upload/2005517/20250531/Quyet_dinh_1509_QD-BCT_ngay_30_5_2025_df799.pdf?utm_source=openai))

### Domestic gas fleet

- **Bà Rịa / Ba Ria** — legacy gas-turbine/combined-cycle complex in Bà Rịa–Vũng Tàu, supplied by Southeast gas. Aging units and changing gas availability affect dispatch. **Confidence: MEDIUM**.
- **Phú Mỹ 1 / Phu My 1** — EVN/GENCO gas CCGT plant in Bà Rịa–Vũng Tàu; core of the Phú Mỹ complex. **Confidence: HIGH**.
- **Phú Mỹ 2.1 / Phu My 2.1** — EVN gas turbine plant, older part of Phú Mỹ complex. **Confidence: MEDIUM**.
- **Phú Mỹ 2.1 extension / Phu My 2.1 MR** — expansion/combined-cycle addition at Phú Mỹ complex. **Confidence: MEDIUM**.
- **Phú Mỹ 2.2 / Phu My 2.2** — BOT CCGT plant at Phú Mỹ, developed by international sponsors. **Confidence: HIGH**.
- **Phú Mỹ 3 / Phu My 3** — BOT CCGT plant at Phú Mỹ, developed by BP/Sembcorp-related consortium historically. **Confidence: HIGH**.
- **Phú Mỹ 4 / Phu My 4** — EVN/GENCO gas CCGT plant in Phú Mỹ complex. **Confidence: HIGH**.
- **Hiệp Phước / Hiep Phuoc** — industrial/captive or grid-connected gas/oil-fired plant in HCMC area; legacy asset with ownership/status changes. **Confidence: LOW/MEDIUM**.
- **Nhơn Trạch 1 / Nhon Trach 1** — PV Power CCGT plant in Đồng Nai, domestic gas/DO capable; PV Power describes Nhơn Trạch 1, Nhơn Trạch 2, and Cà Mau 1&2 as its gas fleet totaling around 2,700 MW. ([pvpower.vn](https://pvpower.vn/en/post/pv-power-takes-the-initiative-in-power-plant-optimal-operating-solutions-5397.htm?utm_source=openai))
- **Nhơn Trạch 2 / Nhon Trach 2** — PV Power CCGT plant in Đồng Nai, operating since early 2010s. ([pvpower.vn](https://pvpower.vn/en/post/pv-power-takes-the-initiative-in-power-plant-optimal-operating-solutions-5397.htm?utm_source=openai))
- **Cà Mau 1 & 2 / Ca Mau 1 & 2** — PV Power gas plants in Cà Mau, supplied from Southwest gas; PV GAS materials state dry gas is transported to the two Cà Mau power plants with total capacity around **1,500 MW**. ([studocu.com](https://www.studocu.com/en-us/document/bowling-green-state-university/introduction-to-geology/annual-report-2024-for-petrovietnam-gas-joint-stock-corporation-pv-gas/123916287?utm_source=openai))
- **Ô Môn 1 / O Mon 1** — EVN oil/gas-capable plant in Cần Thơ, intended to be part of the Ô Môn gas-power complex. **Confidence: MEDIUM**.
- **Ô Môn 2 / O Mon 2** — planned CCGT using Block B gas; delayed. **Confidence: LOW/MEDIUM**.
- **Ô Môn 3 / O Mon 3** — planned CCGT using Block B gas; delayed. **Confidence: LOW/MEDIUM**.
- **Ô Môn 4 / O Mon 4** — planned/under-development CCGT; PetroVietnam reportedly began construction of a 1.15 GW O Mon IV plant in 2025. ([reddit.com](https://www.reddit.com/r/VietnamNews/comments/1mx4l4j?utm_source=openai))
- **Miền Trung 1 & 2 / Mien Trung 1 & 2** — PV Power-studied LNG/gas projects; PV Power has identified them among proposed LNG plants. ([vietnamnet.vn](https://vietnamnet.vn/en/pv-power-to-build-four-new-lng-fired-plants-648753.html?utm_source=openai))

### Imported-LNG fleet and planned LNG projects

- **Nhơn Trạch 3 & 4 / Nhon Trach 3 & 4** — Vietnam’s first major LNG-to-power project; PV Power news and market materials indicate the two units began contributing power in 2025, and PV Power daily-output news in April 2026 reported significant generation from Nhơn Trạch 3 and 4. ([petrovietnam.petrotimes.vn](https://petrovietnam.petrotimes.vn/nhon-trach-34-bat-dau-dong-gop-san-luong-tao-dong-luc-tang-truong-moi-cho-pv-power-731843.html?utm_source=openai))
- **LNG Quảng Ninh / LNG Quang Ninh** — listed in MOIT Decision 1509 appendix with **1,500 MW** and expected 2028–2029 schedule. ([moit.gov.vn](https://moit.gov.vn/upload/2005517/20250531/Quyet_dinh_1509_QD-BCT_ngay_30_5_2025_df799.pdf?utm_source=openai))
- **LNG Thái Bình / LNG Thai Binh** — planned LNG project in northern Vietnam; appeared in PDP/PDP8 implementation cycles. **Confidence: LOW/MEDIUM**.
- **LNG Hải Phòng / LNG Hai Phong** — planned LNG-to-power in Hải Phòng area; appeared in planning/investor proposals. **Confidence: LOW**.
- **LNG Nghi Sơn / LNG Nghi Son** — planned LNG project in Thanh Hóa/Nghi Sơn area; formal status needs primary annex confirmation. **Confidence: LOW**.
- **LNG Quỳnh Lập / LNG Quynh Lap** — PV Power studying Quỳnh Lập in Nghệ An as an LNG-fueled project. ([theinvestor.vn](https://theinvestor.vn/pv-power-says-profit-may-fall-in-2026-despite-higher-output-due-to-extreme-weather-d17723.html?utm_source=openai))
- **LNG Vũng Áng 3 / LNG Vung Ang 3** — PV Power studying Vũng Áng 3 as LNG-fueled rather than coal. ([theinvestor.vn](https://theinvestor.vn/pv-power-says-profit-may-fall-in-2026-despite-higher-output-due-to-extreme-weather-d17723.html?utm_source=openai))
- **LNG Long Sơn / LNG Long Son** — planned LNG-to-power complex in Bà Rịa–Vũng Tàu; formal PDP status should be checked against Decision 1509 annex. **Confidence: LOW/MEDIUM**.
- **LNG Sơn Mỹ 1 / LNG Son My 1** — planned LNG project in Bình Thuận. **Confidence: MEDIUM**.
- **LNG Sơn Mỹ 2 / LNG Son My 2** — planned LNG project in Bình Thuận. **Confidence: MEDIUM**.
- **LNG Cà Ná / LNG Ca Na** — Ninh Thuận LNG project concept; appeared in provincial/national planning discussions. **Confidence: LOW/MEDIUM**.
- **LNG Bạc Liêu / LNG Bac Lieu** — proposed large LNG-to-power project in Bạc Liêu, repeatedly delayed. **Confidence: MEDIUM**.
- **LNG Long An 1 & 2 / Long An LNG** — large LNG-to-power project in Long An, Hanwha/VinaCapital-related development historically reported; formal current status needs annex confirmation. **Confidence: LOW/MEDIUM**.
- **LNG Hiệp Phước phase II / Hiep Phuoc LNG** — MOIT Decision 1509 appendix includes a 1,500 MW phase-II style entry with schedule 2025–2030 and notes Ho Chi Minh City commitment. ([moit.gov.vn](https://moit.gov.vn/upload/2005517/20250531/Quyet_dinh_1509_QD-BCT_ngay_30_5_2025_df799.pdf?utm_source=openai))
- **LNG Công Thanh / Cong Thanh LNG** — MOIT Decision 1509 lists **1,500 MW**, 2031–2035, and notes provincial request to convert from coal to LNG. ([moit.gov.vn](https://moit.gov.vn/upload/2005517/20250531/Quyet_dinh_1509_QD-BCT_ngay_30_5_2025_df799.pdf?utm_source=openai))

---

## 3. Structured power-plants table

> **Technology legend:**  
> **Subcritical / Supercritical / USC** = coal steam technology.  
> **CCGT / OCGT** = gas combined/open-cycle turbine.  
> **Unknown** = not confidently verified from primary source in this pass.  
> **Status terms:** Operating, Under construction, Planned/PDP, Delayed, Cancelled/shelved, Retired/legacy uncertain.

| Name (Vietnamese) | Name (English) | Province | Fuel | Technology | Units × MW | Total MWe | Status | Status as-of-date | COD | Owner/Developer | Confidence | Source 1 | Source 2 | Notes |
|---|---:|---|---|---|---:|---:|---|---|---|---|---|---|---|---|
| Phả Lại | Pha Lai | Hải Dương | Coal | Subcritical | mixed legacy units | ~1,040 | Operating/legacy | 2026-05-23 | 1980s–2000s | PPC/EVN-linked | MEDIUM | EVN system totals ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Secondary plant list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) | Unit-level status requires regulator confirmation. |
| Uông Bí | Uong Bi | Quảng Ninh | Coal | Subcritical | mixed | ~630 | Operating/legacy | 2026-05-23 | 1960s–2010s | EVN/GENCO | MEDIUM | EVN coal totals ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Secondary plant list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) | Older units may be retired/de-rated. |
| Ninh Bình | Ninh Binh | Ninh Bình | Coal | Subcritical | legacy | ~100 | Operating/legacy uncertain | 2026-05-23 | 1970s | EVN-linked | LOW | EVN totals ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Secondary plant list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) | Included due >30 MW legacy coal. |
| Cao Ngạn | Cao Ngan | Thái Nguyên | Coal | CFB/Subcritical | 2×~55 | ~110 | Operating | 2026-05-23 | 2000s | Vinacomin/TKV | MEDIUM | EVN ownership category incl. Vinacomin ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) | Small TKV coal asset. |
| Na Dương | Na Duong | Lạng Sơn | Coal | CFB/Subcritical | 2×55 | 110 | Operating | 2026-05-23 | 2000s | Vinacomin/TKV | MEDIUM | EVN ownership category ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) | Expansion periodically proposed. |
| Sơn Động | Son Dong | Bắc Giang | Coal | CFB/Subcritical | 2×110 | 220 | Operating | 2026-05-23 | 2010s | Vinacomin/TKV | MEDIUM | EVN ownership category ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) | TKV coal. |
| Cẩm Phả | Cam Pha | Quảng Ninh | Coal | Subcritical | 2×300 | 600 | Operating | 2026-05-23 | 2010s | Vinacomin/TKV | MEDIUM | EVN ownership category ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) |  |
| Mạo Khê | Mao Khe | Quảng Ninh | Coal | CFB/Subcritical | 2×220 | 440 | Operating | 2026-05-23 | 2010s | Vinacomin/TKV | MEDIUM | EVN ownership category ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) |  |
| Quảng Ninh | Quang Ninh | Quảng Ninh | Coal | Subcritical | 4×300 | 1,200 | Operating | 2026-05-23 | 2009–2014 | Quang Ninh TPP JSC/EVN-linked | HIGH | EVN coal totals ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) | Northern baseload coal. |
| Hải Phòng | Hai Phong | Hải Phòng | Coal | Subcritical | 4×300 | 1,200 | Operating | 2026-05-23 | 2011–2014 | Hai Phong TPP JSC/EVN-linked | HIGH | EVN coal totals ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) |  |
| Mông Dương 1 | Mong Duong 1 | Quảng Ninh | Coal | CFB/Subcritical | 2×540 | 1,080 | Operating | 2026-05-23 | 2015 | EVN/GENCO3 | HIGH | EVN coal totals ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) |  |
| Mông Dương 2 | Mong Duong 2 | Quảng Ninh | Coal | Supercritical | 2×620 | 1,240 | Operating BOT | 2026-05-23 | 2015 | AES/partners BOT | HIGH | EVN BOT ownership class ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) | BOT coal IPP. |
| Thái Bình 1 | Thai Binh 1 | Thái Bình | Coal | Subcritical | 2×300 | 600 | Operating | 2026-05-23 | 2018 | EVN/GENCO3 | HIGH | EVN coal totals ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) |  |
| Thái Bình 2 | Thai Binh 2 | Thái Bình | Coal | Subcritical | 2×600 | 1,200 | Operating | 2026-05-23 | 2023 | PVN/PV Power-linked | MEDIUM | EVN 2023 coal increase ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) | Delayed PVN project. |
| Nghi Sơn 1 | Nghi Son 1 | Thanh Hóa | Coal | Subcritical | 2×300 | 600 | Operating | 2026-05-23 | 2013–2014 | EVN/GENCO | HIGH | EVN coal totals ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) |  |
| Nghi Sơn 2 | Nghi Son 2 | Thanh Hóa | Coal | Supercritical | 2×600 | 1,200 | Operating BOT | 2026-05-23 | 2022 | Marubeni/Kepco/Toshiba-linked BOT | HIGH | EVN BOT category ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) |  |
| Vũng Áng 1 | Vung Ang 1 | Hà Tĩnh | Coal | Subcritical | 2×600 | 1,200 | Operating | 2026-05-23 | 2014–2015 | PV Power | HIGH | PV Power plant page ([pvpower.vn](https://pvpower.vn/en/?utm_source=openai)) | PV Power gas/coal asset ref. ([pvpower.vn](https://pvpower.vn/en/post/pv-power-takes-the-initiative-in-power-plant-optimal-operating-solutions-5397.htm?utm_source=openai)) | Major PV Power coal plant. |
| Vũng Áng 2 | Vung Ang 2 | Hà Tĩnh | Coal | USC/Supercritical | 2×600 | 1,200 | Under construction | 2026-05-23 | planned late-2020s | VAPCO/JERA-led | MEDIUM | PDP8 coal target ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) | Needs EPC/current construction primary. |
| Vũng Áng 3 | Vung Ang 3 | Hà Tĩnh | Imported LNG | CCGT planned | TBD | ~1,500 | Planned/study; converted concept | 2026-05-23 | TBD | PV Power study | MEDIUM | PV Power LNG study ref. ([theinvestor.vn](https://theinvestor.vn/pv-power-says-profit-may-fall-in-2026-despite-higher-output-due-to-extreme-weather-d17723.html?utm_source=openai)) | PDP8 LNG framework ([moit.gov.vn](https://moit.gov.vn/upload/2005517/20250531/Quyet_dinh_1509_QD-BCT_ngay_30_5_2025_df799.pdf?utm_source=openai)) | Former coal planning concept, now studied as LNG. |
| Quảng Trạch 1 | Quang Trach 1 | Quảng Bình | Coal | USC/Supercritical | 2×600 | 1,200 | Under construction | 2026-05-23 | planned late-2020s | EVN | MEDIUM | PDP8 coal target ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) |  |
| Quảng Trạch 2 | Quang Trach 2 | Quảng Bình | Coal | USC/Supercritical | 2×600 | 1,200 | Planned/PDP | 2026-05-23 | TBD | EVN | LOW | PDP8 coal target ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) | Future coal uncertain under transition policy. |
| Vĩnh Tân 1 | Vinh Tan 1 | Bình Thuận | Coal | Supercritical | 2×620 | 1,240 | Operating BOT | 2026-05-23 | 2018 | China Southern/CLP/Vinacomin BOT | HIGH | EVN BOT category ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) |  |
| Vĩnh Tân 2 | Vinh Tan 2 | Bình Thuận | Coal | Subcritical | 2×622 | 1,244 | Operating | 2026-05-23 | 2014 | EVN/GENCO3 | HIGH | EVN coal totals ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) | Ash/air issues historically. |
| Vĩnh Tân 3 | Vinh Tan 3 | Bình Thuận | Coal | Supercritical planned | 3×660? | ~1,980 | Cancelled/shelved | 2026-05-23 | n/a | OneEnergy/partners historic | LOW | PDP8 coal context ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) | Planning-cycle asset; not built. |
| Vĩnh Tân 4 | Vinh Tan 4 | Bình Thuận | Coal | Supercritical | 2×600 + 1×600 ext. | 1,800 | Operating | 2026-05-23 | 2017–2019 | EVN/GENCO3 | HIGH | EVN fuel-supply note ([en.evn.com.vn](https://en.evn.com.vn/d6/news/EVN-implements-a-series-of-urgent-measures-to-ensure-power-supply-in-the-dry-season-of-2023-66-163-3505.aspx?utm_source=openai)) | EVN coal totals ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Includes extension unit. |
| Duyên Hải 1 | Duyen Hai 1 | Trà Vinh | Coal | Subcritical | 2×622 | 1,245 | Operating | 2026-05-23 | 2015–2016 | EVN/GENCO1 | HIGH | EVN coal totals ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) |  |
| Duyên Hải 2 | Duyen Hai 2 | Trà Vinh | Coal | Supercritical | 2×660 | 1,320 | Operating BOT | 2026-05-23 | 2021–2022 | Janakuasa BOT | MEDIUM | EVN BOT category ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) | COD dates need primary confirmation. |
| Duyên Hải 3 | Duyen Hai 3 | Trà Vinh | Coal | Subcritical | 2×622 | 1,245 | Operating | 2026-05-23 | 2016–2017 | EVN/GENCO1 | HIGH | EVN coal-borrowing note ([en.evn.com.vn](https://en.evn.com.vn/d6/news/EVN-implements-a-series-of-urgent-measures-to-ensure-power-supply-in-the-dry-season-of-2023-66-163-3505.aspx?utm_source=openai)) | EVN coal totals ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) |  |
| Duyên Hải 3 mở rộng | Duyen Hai 3 extension | Trà Vinh | Coal | Supercritical | 1×688 | 688 | Operating | 2026-05-23 | 2019 | EVN/GENCO1 | HIGH | EVN coal totals ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) |  |
| Long Phú 1 | Long Phu 1 | Sóc Trăng | Coal | Subcritical/Supercritical | 2×600 | 1,200 | Delayed/unfinished | 2026-05-23 | TBD | PVN | MEDIUM | PDP8 coal target ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) | Contractor/sanctions dispute; not counted operating. |
| Long Phú 2 | Long Phu 2 | Sóc Trăng | Coal | Planned | 2×600 | 1,200 | Planned/deferred | 2026-05-23 | TBD | BOT candidate | LOW | PDP8 coal context ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) | Planning-cycle asset. |
| Sông Hậu 1 | Song Hau 1 | Hậu Giang | Coal | Subcritical | 2×600 | 1,200 | Operating | 2026-05-23 | 2021–2022 | PVN | MEDIUM | EVN coal totals ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) |  |
| Sông Hậu 2 | Song Hau 2 | Hậu Giang | Coal | Planned | 2×1,000? | ~2,000 | Planned/deferred | 2026-05-23 | TBD | BOT candidate | LOW | PDP8 coal context ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) | Capacity varies by source. |
| Nam Định 1 | Nam Dinh 1 | Nam Định | Coal | Supercritical planned | 2×600 | 1,200 | Planned/deferred | 2026-05-23 | TBD | Taekwang/Acwa historic | LOW | PDP8 coal context ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) | Not built. |
| Công Thanh coal | Cong Thanh coal | Thanh Hóa | Coal | Planned | TBD | ~600? | Converted/shelved | 2025-05-30 | n/a | Cong Thanh | LOW | MOIT Decision 1509 note ([moit.gov.vn](https://moit.gov.vn/upload/2005517/20250531/Quyet_dinh_1509_QD-BCT_ngay_30_5_2025_df799.pdf?utm_source=openai)) | PDP8 LNG framework ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | MOIT notes LNG Công Thanh conversion from coal. |
| Bà Rịa | Ba Ria | Bà Rịa–Vũng Tàu | Domestic gas | OCGT/CCGT mixed | mixed | ~390 | Operating/legacy | 2026-05-23 | 1990s | EVN/GENCO3 | MEDIUM | EVN gas+oil totals ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) | Aging gas turbine complex. |
| Phú Mỹ 1 | Phu My 1 | Bà Rịa–Vũng Tàu | Domestic gas | CCGT | 3 GT + ST | ~1,090 | Operating | 2026-05-23 | 2000s | EVN/GENCO3 | HIGH | EVN gas+oil totals ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) | Phú Mỹ complex. |
| Phú Mỹ 2.1 | Phu My 2.1 | Bà Rịa–Vũng Tàu | Domestic gas | CCGT/OCGT | mixed | ~477 | Operating | 2026-05-23 | 1997–2000s | EVN/GENCO3 | MEDIUM | Secondary list shows 477 MW ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) | EVN gas+oil totals ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) |  |
| Phú Mỹ 2.1 MR | Phu My 2.1 Extension | Bà Rịa–Vũng Tàu | Domestic gas | CCGT | mixed | ~440 | Operating | 2026-05-23 | 2000s | EVN/GENCO3 | MEDIUM | EVN gas+oil totals ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) | Unit naming varies. |
| Phú Mỹ 2.2 | Phu My 2.2 | Bà Rịa–Vũng Tàu | Domestic gas | CCGT | 2 GT + ST | ~715 | Operating BOT | 2026-05-23 | 2005 | Mekong Energy BOT | HIGH | EVN BOT category ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) |  |
| Phú Mỹ 3 | Phu My 3 | Bà Rịa–Vũng Tàu | Domestic gas | CCGT | 2 GT + ST | ~720 | Operating BOT | 2026-05-23 | 2004 | Phu My 3 BOT | HIGH | EVN BOT category ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) |  |
| Phú Mỹ 4 | Phu My 4 | Bà Rịa–Vũng Tàu | Domestic gas | CCGT | 2 GT + ST | ~450 | Operating | 2026-05-23 | 2004 | EVN/GENCO3 | HIGH | EVN gas+oil totals ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) |  |
| Hiệp Phước | Hiep Phuoc | TP.HCM | Domestic gas / oil | OCGT/steam uncertain | mixed | ~375 | Operating/legacy uncertain | 2026-05-23 | 1990s | Hiep Phuoc Power Co. | LOW | EVN gas+oil totals ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | PV GAS HCMC gas-market note ([studocu.com](https://www.studocu.com/en-us/document/bowling-green-state-university/introduction-to-geology/annual-report-2024-for-petrovietnam-gas-joint-stock-corporation-pv-gas/123916287?utm_source=openai)) | Status/units need verification. |
| Nhơn Trạch 1 | Nhon Trach 1 | Đồng Nai | Domestic gas | CCGT | 2 GT + ST | ~450 | Operating | 2026-05-23 | 2009 | PV Power | HIGH | PV Power gas fleet ([pvpower.vn](https://pvpower.vn/en/post/pv-power-takes-the-initiative-in-power-plant-optimal-operating-solutions-5397.htm?utm_source=openai)) | GEM/secondary plant page ([gem.wiki](https://www.gem.wiki/Nhon_Trach_power_station?utm_source=openai)) | Can run DO when gas constrained. |
| Nhơn Trạch 2 | Nhon Trach 2 | Đồng Nai | Domestic gas | CCGT | 2 GT + ST | ~750 | Operating | 2026-05-23 | 2011 | PV Power NT2 | HIGH | PV Power gas fleet ([pvpower.vn](https://pvpower.vn/en/post/pv-power-takes-the-initiative-in-power-plant-optimal-operating-solutions-5397.htm?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) |  |
| Cà Mau 1 | Ca Mau 1 | Cà Mau | Domestic gas | CCGT | block | ~750 | Operating | 2026-05-23 | 2008 | PV Power Ca Mau | HIGH | PV GAS Cà Mau capacity note ([studocu.com](https://www.studocu.com/en-us/document/bowling-green-state-university/introduction-to-geology/annual-report-2024-for-petrovietnam-gas-joint-stock-corporation-pv-gas/123916287?utm_source=openai)) | PV Power gas fleet ([pvpower.vn](https://pvpower.vn/en/post/pv-power-takes-the-initiative-in-power-plant-optimal-operating-solutions-5397.htm?utm_source=openai)) | Often reported with Cà Mau 2 as 1,500 MW. |
| Cà Mau 2 | Ca Mau 2 | Cà Mau | Domestic gas | CCGT | block | ~750 | Operating | 2026-05-23 | 2008 | PV Power Ca Mau | HIGH | PV GAS Cà Mau capacity note ([studocu.com](https://www.studocu.com/en-us/document/bowling-green-state-university/introduction-to-geology/annual-report-2024-for-petrovietnam-gas-joint-stock-corporation-pv-gas/123916287?utm_source=openai)) | PV Power gas fleet ([pvpower.vn](https://pvpower.vn/en/post/pv-power-takes-the-initiative-in-power-plant-optimal-operating-solutions-5397.htm?utm_source=openai)) |  |
| Ô Môn 1 | O Mon 1 | Cần Thơ | Domestic gas / oil | OCGT/steam uncertain | 2×330? | ~660 | Operating/transition | 2026-05-23 | 2009/2015 | EVN/GENCO2 | MEDIUM | EVN gas+oil totals ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) | Intended Block B gas complex. |
| Ô Môn 2 | O Mon 2 | Cần Thơ | Domestic gas | CCGT planned | ~750 | ~750 | Planned/delayed | 2026-05-23 | TBD | Marubeni/EVN historic | LOW | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) | PDP8 domestic gas target ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | Depends on Block B gas. |
| Ô Môn 3 | O Mon 3 | Cần Thơ | Domestic gas | CCGT planned | ~1,050? | ~1,050 | Planned/delayed | 2026-05-23 | TBD | EVN/PVN | LOW | PDP8 domestic gas target ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | Secondary list ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai)) | Capacity varies. |
| Ô Môn 4 | O Mon 4 | Cần Thơ | Domestic gas | CCGT | 1 block | ~1,150 | Under construction | 2025-08 approx | TBD | Petrovietnam | MEDIUM | Construction report ([reddit.com](https://www.reddit.com/r/VietnamNews/comments/1mx4l4j?utm_source=openai)) | PDP8 domestic gas target ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | Reddit source points to news; primary needed. |
| Nhơn Trạch 3 | Nhon Trach 3 | Đồng Nai | Imported LNG | CCGT | 1 block | ~750 | Operating/commissioning | 2026-04-14 | 2025 | PV Power | HIGH | PV Power output news ([petrovietnam.petrotimes.vn](https://petrovietnam.petrotimes.vn/pv-power-lap-ky-luc-100-trieu-kwhngay-dong-gop-gan-10-dien-nang-quoc-gia-739912.html?utm_source=openai)) | PetroTimes COD contribution note ([petrovietnam.petrotimes.vn](https://petrovietnam.petrotimes.vn/nhon-trach-34-bat-dau-dong-gop-san-luong-tao-dong-luc-tang-truong-moi-cho-pv-power-731843.html?utm_source=openai)) | Vietnam’s first LNG-to-power cluster. |
| Nhơn Trạch 4 | Nhon Trach 4 | Đồng Nai | Imported LNG | CCGT | 1 block | ~750 | Operating/commissioning | 2026-04-14 | 2025 | PV Power | HIGH | PV Power output news ([petrovietnam.petrotimes.vn](https://petrovietnam.petrotimes.vn/pv-power-lap-ky-luc-100-trieu-kwhngay-dong-gop-gan-10-dien-nang-quoc-gia-739912.html?utm_source=openai)) | PV Power/grid link note ([pvpower.vn](https://pvpower.vn/en/?utm_source=openai)) |  |
| LNG Quảng Ninh | Quang Ninh LNG | Quảng Ninh | Imported LNG | CCGT | TBD | 1,500 | Planned/PDP | 2025-05-30 | 2028–2029 planned | Consortium/provincial | HIGH | MOIT Decision 1509 ([moit.gov.vn](https://moit.gov.vn/upload/2005517/20250531/Quyet_dinh_1509_QD-BCT_ngay_30_5_2025_df799.pdf?utm_source=openai)) | KPMG PDP8 summary ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | Listed in MOIT appendix. |
| LNG Thái Bình | Thai Binh LNG | Thái Bình | Imported LNG | CCGT | TBD | ~1,500 | Planned/PDP | 2026-05-23 | TBD | TBD | LOW | PDP8 LNG target ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | MOIT appendix context ([moit.gov.vn](https://moit.gov.vn/upload/2005517/20250531/Quyet_dinh_1509_QD-BCT_ngay_30_5_2025_df799.pdf?utm_source=openai)) | Exact annex row not verified. |
| LNG Hải Phòng | Hai Phong LNG | Hải Phòng | Imported LNG | CCGT | TBD | ~1,500 | Planned/PDP | 2026-05-23 | TBD | TBD | LOW | PDP8 LNG target ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | MOIT appendix context ([moit.gov.vn](https://moit.gov.vn/upload/2005517/20250531/Quyet_dinh_1509_QD-BCT_ngay_30_5_2025_df799.pdf?utm_source=openai)) | Exact primary row not verified. |
| LNG Nghi Sơn | Nghi Son LNG | Thanh Hóa | Imported LNG | CCGT | TBD | ~1,500 | Planned/PDP | 2026-05-23 | TBD | TBD | LOW | PDP8 LNG target ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | MOIT appendix context ([moit.gov.vn](https://moit.gov.vn/upload/2005517/20250531/Quyet_dinh_1509_QD-BCT_ngay_30_5_2025_df799.pdf?utm_source=openai)) | Exact primary row not verified. |
| LNG Quỳnh Lập | Quynh Lap LNG | Nghệ An | Imported LNG | CCGT | TBD | ~1,500 | Study/planned | 2026-05-23 | TBD | PV Power study | MEDIUM | PV Power study ref. ([theinvestor.vn](https://theinvestor.vn/pv-power-says-profit-may-fall-in-2026-despite-higher-output-due-to-extreme-weather-d17723.html?utm_source=openai)) | PDP8 LNG target ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | Former coal site concept. |
| LNG Long Sơn | Long Son LNG | Bà Rịa–Vũng Tàu | Imported LNG | CCGT | TBD | ~1,500 | Planned/PDP | 2026-05-23 | TBD | TBD | LOW | PDP8 LNG target ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | MOIT appendix context ([moit.gov.vn](https://moit.gov.vn/upload/2005517/20250531/Quyet_dinh_1509_QD-BCT_ngay_30_5_2025_df799.pdf?utm_source=openai)) | Needs primary row verification. |
| LNG Sơn Mỹ 1 | Son My 1 LNG | Bình Thuận | Imported LNG | CCGT | TBD | ~2,250 | Planned/PDP | 2026-05-23 | late-2020s | EDF/JERA/PVN historic | MEDIUM | PDP8 LNG target ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | MOIT appendix context ([moit.gov.vn](https://moit.gov.vn/upload/2005517/20250531/Quyet_dinh_1509_QD-BCT_ngay_30_5_2025_df799.pdf?utm_source=openai)) | Capacity/sponsors need current confirmation. |
| LNG Sơn Mỹ 2 | Son My 2 LNG | Bình Thuận | Imported LNG | CCGT | TBD | ~2,250 | Planned/PDP | 2026-05-23 | late-2020s | AES/PVN historic | MEDIUM | PDP8 LNG target ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | MOIT appendix context ([moit.gov.vn](https://moit.gov.vn/upload/2005517/20250531/Quyet_dinh_1509_QD-BCT_ngay_30_5_2025_df799.pdf?utm_source=openai)) | Capacity/sponsors need current confirmation. |
| LNG Cà Ná | Ca Na LNG | Ninh Thuận | Imported LNG | CCGT | TBD | ~1,500 | Planned/uncertain | 2026-05-23 | TBD | Provincial/PVN concept | LOW | PDP8 LNG target ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | MOIT appendix context ([moit.gov.vn](https://moit.gov.vn/upload/2005517/20250531/Quyet_dinh_1509_QD-BCT_ngay_30_5_2025_df799.pdf?utm_source=openai)) | Sponsor/status uncertain. |
| LNG Bạc Liêu | Bac Lieu LNG | Bạc Liêu | Imported LNG | CCGT | multiple blocks | ~3,200 | Planned/delayed | 2026-05-23 | TBD | Delta Offshore Energy historic | MEDIUM | PDP8 LNG target ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | MOIT appendix context ([moit.gov.vn](https://moit.gov.vn/upload/2005517/20250531/Quyet_dinh_1509_QD-BCT_ngay_30_5_2025_df799.pdf?utm_source=openai)) | Major delayed LNG IPP. |
| LNG Long An 1 | Long An 1 LNG | Long An | Imported LNG | CCGT | block | ~1,500 | Planned/PDP | 2026-05-23 | TBD | VinaCapital/Hanwha historic | LOW | PDP8 LNG target ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | MOIT appendix context ([moit.gov.vn](https://moit.gov.vn/upload/2005517/20250531/Quyet_dinh_1509_QD-BCT_ngay_30_5_2025_df799.pdf?utm_source=openai)) | Needs current investor confirmation. |
| LNG Long An 2 | Long An 2 LNG | Long An | Imported LNG | CCGT | block | ~1,500 | Planned/PDP | 2026-05-23 | TBD | VinaCapital/Hanwha historic | LOW | PDP8 LNG target ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | MOIT appendix context ([moit.gov.vn](https://moit.gov.vn/upload/2005517/20250531/Quyet_dinh_1509_QD-BCT_ngay_30_5_2025_df799.pdf?utm_source=openai)) | Needs current investor confirmation. |
| LNG Hiệp Phước giai đoạn II | Hiep Phuoc LNG phase II | TP.HCM | Imported LNG | CCGT | TBD | 1,500 | Planned/PDP | 2025-05-30 | 2025–2030 planned | Hiep Phuoc/municipal | HIGH | MOIT Decision 1509 ([moit.gov.vn](https://moit.gov.vn/upload/2005517/20250531/Quyet_dinh_1509_QD-BCT_ngay_30_5_2025_df799.pdf?utm_source=openai)) | PDP8 LNG target ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | MOIT appendix note references HCMC commitment. |
| LNG Công Thanh | Cong Thanh LNG | Thanh Hóa | Imported LNG | CCGT | TBD | 1,500 | Planned/PDP | 2025-05-30 | 2031–2035 planned | Cong Thanh | HIGH | MOIT Decision 1509 ([moit.gov.vn](https://moit.gov.vn/upload/2005517/20250531/Quyet_dinh_1509_QD-BCT_ngay_30_5_2025_df799.pdf?utm_source=openai)) | KPMG PDP8 summary ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | Converted from coal concept. |
| Miền Trung 1 | Mien Trung 1 LNG | Bình Định/central region uncertain | Imported LNG | CCGT | TBD | ~1,500 | Study/proposed | 2026-05-23 | TBD | PV Power | MEDIUM | PV Power LNG plan ([vietnamnet.vn](https://vietnamnet.vn/en/pv-power-to-build-four-new-lng-fired-plants-648753.html?utm_source=openai)) | PDP8 LNG target ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | Province not verified. |
| Miền Trung 2 | Mien Trung 2 LNG | Bình Định/central region uncertain | Imported LNG | CCGT | TBD | ~1,500 | Study/proposed | 2026-05-23 | TBD | PV Power | MEDIUM | PV Power LNG plan ([vietnamnet.vn](https://vietnamnet.vn/en/pv-power-to-build-four-new-lng-fired-plants-648753.html?utm_source=openai)) | PDP8 LNG target ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | Province not verified. |
| Cà Mau 3 / Cà Mau expansion | Ca Mau LNG/gas expansion | Cà Mau | Imported LNG / gas | CCGT | TBD | ~1,500? | Study/proposed | 2026-05-23 | TBD | PV Power | LOW | PV Power study ref. ([theinvestor.vn](https://theinvestor.vn/pv-power-says-profit-may-fall-in-2026-despite-higher-output-due-to-extreme-weather-d17723.html?utm_source=openai)) | PDP8 LNG target ([assets.kpmg.com](https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/07/revised-pdp-8-en.pdf?utm_source=openai)) | Capacity not verified. |

---

## 4. Statistical summaries

### 4.1 Capacity by fuel × status  
**Caveat:** This summary aggregates the table above, not an official MOIT total. Planned LNG and future coal rows include uncertain capacities, so use as inventory arithmetic only.

| Fuel | Operating / commissioning | Under construction | Planned / study / PDP | Delayed / deferred | Cancelled / converted | Total table capacity |
|---|---:|---:|---:|---:|---:|---:|
| Coal | ~25,660 MW | ~2,400 MW | ~3,600 MW | ~6,800 MW | ~2,580 MW | ~41,040 MW |
| Domestic gas | ~7,217 MW | ~1,150 MW | ~1,800 MW | ~1,800 MW | 0 | ~11,967 MW |
| Imported LNG | ~1,500 MW | 0 | ~30,000+ MW | ~3,200 MW | 0 | ~34,700+ MW |
| **Total** | **~34,377 MW** | **~3,550 MW** | **~35,400+ MW** | **~11,800 MW** | **~2,580 MW** | **~87,700+ MW** |

**Reconciliation note:** EVN’s official 2024 national installed-capacity table reports **26,757 MW coal** and **8,653 MW gas + oil** actually installed. The operating subtotal above is broadly consistent for coal, but lower/uncertain for gas because several legacy gas/oil assets and captive plants need primary verification. ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai))  

### 4.2 Top provinces by table thermal capacity

| Rank | Province | Approx. table capacity | Dominant fuel(s) | Notes |
|---:|---|---:|---|---|
| 1 | Bình Thuận | ~10,764 MW | Coal, LNG | Vĩnh Tân + Sơn Mỹ LNG. |
| 2 | Quảng Ninh | ~7,160 MW | Coal, LNG | Large northern coal base + LNG Quảng Ninh. |
| 3 | Bà Rịa–Vũng Tàu | ~6,145 MW | Domestic gas, LNG | Phú Mỹ/Bà Rịa + Long Sơn LNG. |
| 4 | Trà Vinh | ~4,498 MW | Coal | Duyên Hải power center. |
| 5 | Thanh Hóa | ~5,400 MW | Coal, LNG | Nghi Sơn + Công Thanh/Nghi Sơn LNG concepts. |
| 6 | Đồng Nai | ~2,700 MW | Domestic gas, LNG | Nhơn Trạch complex. |
| 7 | Cà Mau | ~3,000 MW | Domestic gas, LNG | Cà Mau 1–2 + expansion concept. |
| 8 | Bạc Liêu | ~3,200 MW | LNG | Large delayed LNG project. |
| 9 | Long An | ~3,000 MW | LNG | Long An LNG 1–2. |
| 10 | Hà Tĩnh | ~3,900 MW | Coal, LNG | Vũng Áng 1/2/3. |
| 11 | Cần Thơ | ~3,610 MW | Domestic gas | Ô Môn complex. |
| 12 | Sóc Trăng | ~2,400 MW | Coal | Long Phú 1–2. |
| 13 | Hậu Giang | ~3,200 MW | Coal | Sông Hậu 1–2. |
| 14 | Hải Phòng | ~2,700 MW | Coal, LNG | Hải Phòng coal + LNG concept. |
| 15 | Thái Bình | ~3,300 MW | Coal, LNG | Thái Bình 1/2 + LNG concept. |

### 4.3 Timeline of additions by period and fuel  
**Operating and commissioning additions only; future dates for planned projects excluded unless table status is under construction/commissioning.**

| Period | Coal additions | Domestic gas additions | Imported LNG additions | Notes |
|---|---:|---:|---:|---|
| Pre-1990 | ~1,000 MW | 0 | 0 | Legacy coal: Phả Lại, Uông Bí, Ninh Bình. |
| 1990–1999 | limited | ~800–1,000 MW | 0 | Bà Rịa/Phú Mỹ early gas era. |
| 2000–2009 | ~2,000 MW | ~5,000 MW | 0 | Phú Mỹ buildout, Cà Mau, Nhơn Trạch 1, O Mon 1; early new coal. |
| 2010–2014 | ~5,000 MW | ~750 MW | 0 | Hải Phòng, Quảng Ninh, Nghi Sơn 1, Vĩnh Tân 2, Nhơn Trạch 2. |
| 2015–2019 | ~10,000 MW | small | 0 | Mông Dương, Thái Bình 1, Vĩnh Tân 1/4, Duyên Hải. |
| 2020–2024 | ~5,000 MW | limited | 0 | Nghi Sơn 2, Duyên Hải 2, Sông Hậu 1, Thái Bình 2. |
| 2025–2026 | 0 | 0 / O Mon under construction | ~1,500 MW | Nhơn Trạch 3–4 began contributing LNG power in 2025–2026. ([petrovietnam.petrotimes.vn](https://petrovietnam.petrotimes.vn/nhon-trach-34-bat-dau-dong-gop-san-luong-tao-dong-luc-tang-truong-moi-cho-pv-power-731843.html?utm_source=openai)) |

### 4.4 Data-quality summary by confidence level and fuel

| Fuel | HIGH rows | MEDIUM rows | LOW rows | Main uncertainty drivers |
|---|---:|---:|---:|---|
| Coal | 17 | 13 | 7 | Older unit retirement; future coal cancellations/conversions; BOT CODs. |
| Domestic gas | 8 | 6 | 4 | Legacy gas/oil configuration; Ô Môn schedule; captive/industrial status. |
| Imported LNG | 4 | 5 | 10+ | PDP8 annex status, investor changes, financing/PPA/GSA bankability. |

---

## 5. Annotated bibliography of cited sources

1. **Vietnam Electricity (EVN). _Annual Report 2022–2023._** URL available via EVN PDF.  
   Used for installed-capacity by fuel in 2022 and 2023, including coal-fired capacity of 25,312 MW in 2022 and 26,756 MW in 2023. ([en.evn.com.vn](https://en.evn.com.vn/userfile/files/EVNAnnualReport2022-2023-20241115110735330.pdf?utm_source=openai))  

2. **Vietnam Electricity (EVN). _Annual Report 2025 / 2024 system data._** URL available via EVN PDF.  
   Used for 2024 national installed capacity: 82,387 MW total; 26,757 MW coal; 8,653 MW gas + oil; ownership split among EVN/GENCOs, PVN, Vinacomin, BOT and other investors. ([evn.com.vn](https://evn.com.vn/userfile/User/tcdl/files/2026/4/AnnualRepot2025_V23-20260408155529045.pdf?utm_source=openai))  

3. **Vietnam Electricity (EVN). “Overview of national power sources in 2023.”**  
   Used for qualitative sector challenges: coal supply shortfalls, Southeast and Southwest gas consumption, declining gas availability relative to demand. ([en.evn.com.vn](https://en.evn.com.vn/d6/news/Overview-of-national-power-sources-in-2023-66-142-4147.aspx?utm_source=openai))  

4. **Vietnam Electricity (EVN). Vietnamese original: “Một số số liệu tổng quan về nguồn điện toàn quốc năm 2023.” English: “Some overview data on national power sources in 2023.”**  
   Used as parallel Vietnamese-language support for 2023 fuel and dispatch context and EVN’s negotiations with PVN/PV GAS for gas/LNG supply arrangements. ([evn.com.vn](https://www.evn.com.vn/d6/news/Mot-so-so-lieu-tong-quan-ve-nguon-dien-toan-quoc-nam-2023-66-142-124707.aspx?utm_source=openai))  

5. **Vietnam Electricity (EVN). “EVN implements a series of urgent measures to ensure power supply in the dry season of 2023.”**  
   Used for evidence of coal-supply interventions affecting Duyên Hải 3 and gas-supply constraints affecting gas-turbine operation. ([en.evn.com.vn](https://en.evn.com.vn/d6/news/EVN-implements-a-series-of-urgent-measures-to-ensure-power-supply-in-the-dry-season-of-2023-66-163-3505.aspx?utm_source=openai))  

6. **Government Office of Vietnam. Vietnamese original: “Thông báo số 484/TB-VPCP… rà soát tình hình triển khai Quyết định số 768/QĐ-TTg ngày 15 tháng 4 năm 2025…” English: “Notice No. 484/TB-VPCP… review of implementation of Decision No. 768/QĐ-TTg dated 15 April 2025…”**  
   Used to confirm existence and implementation context of the 2025 revised PDP8 approval decision. ([vanban.chinhphu.vn](https://vanban.chinhphu.vn/?docid=215339&pageid=27160&utm_source=openai))  

7. **Ministry of Industry and Trade (MOIT). Vietnamese original: “Quyết định 1509/QĐ-BCT ngày 30/5/2025… Danh mục và tiến độ dự kiến các dự án nguồn, lưới điện.” English: “Decision 1509/QĐ-BCT dated 30 May 2025… List and expected schedule of generation and grid projects.”**  
   Used for PDP8 implementation annex references, especially LNG Quảng Ninh 1,500 MW, LNG Hiệp Phước phase-type 1,500 MW entry, and LNG Công Thanh 1,500 MW with coal-to-LNG conversion note. ([moit.gov.vn](https://moit.gov.vn/upload/2005517/20250531/Quyet_dinh_1509_QD-BCT_ngay_30_5_2025_df799.pdf?utm_source=openai))  

8. **KPMG Vietnam. “Revised Power Development Plan VIII of Vietnam.”**  
   Used for summarized 2030 revised PDP8 capacity targets: coal-fired thermal 31,055 MW, domestic gas-fired 10,861–14,930 MW, LNG thermal 22,524 MW, and transition notes. ([kpmg.com](https://kpmg.com/vn/en/home/insights/2025/07/revised-pdp-8.html?utm_source=openai))  

9. **International Energy Agency (IEA). “Power Development Master Plan VIII – Policies.”**  
   Used as a policy-context source for PDP8 and longer-term 2050 direction, including future conversion of thermal capacity to biomass/ammonia/hydrogen pathways. ([iea.org](https://www.iea.org/policies/28683-power-development-master-plan-viii?utm_source=openai))  

10. **PetroVietnam Power Corporation (PV Power). Corporate website.**  
    Used for PV Power corporate plant references, including Cà Mau 1–2, Vũng Áng 1, and Nhơn Trạch power plants, and for current news on Nhơn Trạch 4 grid connection. ([pvpower.vn](https://pvpower.vn/en/?utm_source=openai))  

11. **PV Power. “PV Power takes the initiative in power plant optimal operating solutions.”**  
    Used for PV Power’s statement that it manages and operates Nhơn Trạch 1, Nhơn Trạch 2, and Cà Mau 1&2 gas plants, totaling around 2,700 MW. ([pvpower.vn](https://pvpower.vn/en/post/pv-power-takes-the-initiative-in-power-plant-optimal-operating-solutions-5397.htm?utm_source=openai))  

12. **PV GAS / annual-report-derived source.**  
    Used for the statement that dry gas is transported to two Cà Mau power plants with total capacity around 1,500 MW and to contextualize gas supply to Southeast/Southwest plants. ([studocu.com](https://www.studocu.com/en-us/document/bowling-green-state-university/introduction-to-geology/annual-report-2024-for-petrovietnam-gas-joint-stock-corporation-pv-gas/123916287?utm_source=openai))  

13. **PetroVietnam / PetroTimes. Vietnamese original: “Nhơn Trạch 3&4 bắt đầu đóng góp sản lượng, tạo động lực tăng trưởng mới cho PV Power.” English: “Nhơn Trạch 3&4 begin contributing output, creating new growth momentum for PV Power.”**  
    Used to support the status that Nhơn Trạch 3–4 began contributing generation in 2025. ([petrovietnam.petrotimes.vn](https://petrovietnam.petrotimes.vn/nhon-trach-34-bat-dau-dong-gop-san-luong-tao-dong-luc-tang-truong-moi-cho-pv-power-731843.html?utm_source=openai))  

14. **PetroVietnam / PetroTimes. Vietnamese original: “PV Power lập kỷ lục 100 triệu kWh/ngày, đóng góp gần 10% điện năng quốc gia.” English: “PV Power sets a record of 100 million kWh/day, contributing nearly 10% of national electricity.”**  
    Used to support the April 2026 operational contribution of Nhơn Trạch 3 and 4. ([petrovietnam.petrotimes.vn](https://petrovietnam.petrotimes.vn/pv-power-lap-ky-luc-100-trieu-kwhngay-dong-gop-gan-10-dien-nang-quoc-gia-739912.html?utm_source=openai))  

15. **VietnamNet. “PV Power to build four new LNG-fired plants.”**  
    Used for PV Power’s proposed LNG portfolio: Nhơn Trạch 3, Nhơn Trạch 4, Miền Trung 1 and Miền Trung 2. ([vietnamnet.vn](https://vietnamnet.vn/en/pv-power-to-build-four-new-lng-fired-plants-648753.html?utm_source=openai))  

16. **The Investor. “PV Power says profit may fall in 2026 despite higher output due to extreme weather.”**  
    Used for PV Power’s study of LNG-fueled projects including Quỳnh Lập, Vũng Áng 3, and Cà Mau expansion. ([theinvestor.vn](https://theinvestor.vn/pv-power-says-profit-may-fall-in-2026-despite-higher-output-due-to-extreme-weather-d17723.html?utm_source=openai))  

17. **Global Energy Monitor. “Nhon Trach power station.”**  
    Secondary source used for unit-level Nhơn Trạch references and financing context; not treated as primary. ([gem.wiki](https://www.gem.wiki/Nhon_Trach_power_station?utm_source=openai))  

18. **Wikipedia. “List of power stations in Vietnam.”**  
    Secondary compilation used only as a backstop for plant names/capacities where primary plant-level documents were not verified in this pass. Cells relying on this are marked MEDIUM or LOW. ([en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_power_stations_in_Vietnam?utm_source=openai))  

19. **Reddit-linked news snippet: “Petrovietnam begins construction of 1.15 GW thermal power plant in Mekong Delta.”**  
    Used only as weak support for O Mon IV construction status; row marked MEDIUM/LOW because the underlying primary/news URL was not directly verified in this session. ([reddit.com](https://www.reddit.com/r/VietnamNews/comments/1mx4l4j?utm_source=openai))  

---

## 6. Known gaps requiring follow-up primary verification

1. **MOIT Decision 1509 appendix extraction:** the full appendix should be parsed row-by-row for all LNG, coal and domestic-gas entries, schedules and notes.  
2. **Electricity Regulatory Authority of Vietnam generation-license annexes:** needed for unit-level COD, capacity and owner/operator status.  
3. **EVN GENCO1/2/3 annual reports:** needed for Duyên Hải, Vĩnh Tân, Phú Mỹ, Ô Môn and legacy coal/gas unit detail.  
4. **PV Power 2024/2025 annual reports:** needed for definitive Nhơn Trạch 3–4 COD, O Mon IV status, Cà Mau and Vũng Áng asset details.  
5. **TKV/Vinacomin annual reports:** needed for Cao Ngạn, Na Dương, Sơn Động, Cẩm Phả and Mạo Khê exact capacities/status.  
6. **Captive/industrial thermal plants >30 MWe:** Hiep Phuoc and industrial CHP/cogeneration assets require provincial or industrial-zone primary approvals; this inventory likely undercounts them.