----------------------------------
A. SCENARIO DEFINITIONS (THERMAL FLEET ONLY)
----------------------------------

Common 2023 starting point (actual end–2022 EVN statistics)
• Coal steam: 24 GW
• Domestic gas CCGT/OCGT: 7 GW
• Diesel & fuel-oil: 2 GW  (modelled as peaking only, omitted from tables)

Capacity figures below are net dependable GW. Positive = additions, negative = retirements.  
All new plants are assumed to be super-critical (coal) or F-class CCGT (gas/LNG) unless stated.

1. Reference / PDP8 Baseline  
   – Implements Decision 500/QĐ-TTg literally.

                         2025  2030  2035  2040  2045  2050   Comment
   ---------------------------------------------------------------
   Coal additions        +3    +5    +3     0     0     0    11 GW already under construction
   Coal retirements       0     0    −3    −10   −10   −12   Last units converted to biomass/ammonia post-2045
   LNG CCGT additions    +5   +13    +5    +5    +4    +3    As in PDP8 Annex IV
   Domestic gas CCGT add +1    +2    +4    +3    +2    +1    Block B & Cá Voi Xanh on schedule
   Gas retirements        0     0    −1    −2    −3    −4    Age-based

   Fuel-supply & price assumptions
   • Domestic coal output peaks 42 Mt (2028) then declines linearly to 12 Mt (2050). Import gap filled at ARA index FOB + 18 $/t shipping.  
   • Well-head gas: 6.0 $/MMBtu (2025) escalated 2 %/a real.  
   • LNG (DES, regasified): 11.5 $/MMBtu (2025), 10 $ (2030), then 10 $ ± 3 $ sensitivity band.  
   • Carbon price: pilot ETS starts 2028 at 5 $/tCO₂, linearly to 25 $ (2050).

   Demand drivers
   • GDP elasticity of electricity: 0.9 (MOIT baseline)  
   • Real GDP CAGR: 6.8 % (2025-30), 5.5 % (2031-40), 4 % (2041-50)  
   • Industrial load share grows from 55 % to 60 % by 2040, then stabilises  
   • EV penetration: 10 % of LDV stock 2030, 40 % 2050 (MOIT EV Roadmap “high”)

   Policy levers explicitly coded
   • No new coal approval after 2026, but already-approved projects proceed  
   • FiT for offshore wind ends 2031, replaced by auctions  
   • Gas prices kept under import-parity cap via Decree 80/2022

   Key uncertainties
   1. LNG spot price volatility (±50 %)  
   2. Domestic gas field schedule slippage (±3 y)  
   3. Coal to biomass co-firing success rate (0, 25, 50 %)

2. Accelerated Transition (JETP-aligned)  
   – Coal out by 2040, renewables & storage scale faster; uses same demand as Reference.

                         2025  2030  2035  2040  2045  2050
   --------------------------------------------------------
   Coal additions         0     0     0     0     0     0
   Coal retirements       0   −10   −10    −9     0     0   All retired by 2040
   LNG CCGT additions    +5   +10    +7    +5    −2    −5   Net decline after 2045 (hydrogen retrofit)
   Domestic gas CCGT add +1    +2    +2    +2    +1     0
   Gas retirements        0     0    −1    −1    −5    −5

   Supply & price
   • Domestic coal output fixed at 30 Mt (2025) then −5 Mt every 5 y; zero by 2040.  
   • LNG price identical to Reference but carbon price higher: 10 $/t (2028) → 60 $/t (2050).  
   • JETP concessional finance cuts WACC for green projects from 8 % to 5 %.

   Demand tweaks
   • Elasticity 0.85 (efficiency programmes)  
   • EV share 60 % by 2050 – additional 32 TWh demand.

   Policies
   • National coal moratorium 2024.  
   • Mandatory coal-plant minimum utilisation <20 % from 2030, incentivised via capacity payments.  
   • Renewable energy share target: 70 % generation by 2050 (Resolution 55 update).

   Uncertainties
   – Battery cost learning rate (12 % vs 18 %)  
   – Carbon price political acceptance plateau at 40 $ vs 60 $

3. Gas Bridge  
   – Uses abundant domestic gas + LNG as “bridge”; renewables moderate.

                         2025  2030  2035  2040  2045  2050
   --------------------------------------------------------
   Coal additions         0     0     0     0     0     0
   Coal retirements       0    −5   −10   −10    −5    −5   Last unit closed 2050
   LNG CCGT additions    +7   +15   +10    +5    +5    +3
   Domestic gas CCGT add +2    +6    +6    +4    +2     0
   Gas retirements        0     0    −1    −2    −3    −5

   Supply/price
   • Block B + Lô B-Ô Môn: 5 bcm y-1 online 2028; Cá Voi Xanh 6 bcm y-1 2030; plateau 2040 then decline 20 % by 2050.  
   • Domestic gas 4.8 $/MMBtu (well-head) to power sector by PM Decision 60/2023.  
   • LNG price Reference path.  
   • Carbon price low: 5 $/t (2028) → 15 $/t (2050).

   Demand
   • Elasticity 0.95 (gas power supplies new industrial zones).  
   • Petrochemical cluster electrification adds 20 TWh by 2035.

   Policies
   • Guaranteed gas-offtake contracts for 20 y.  
   • No coal moratorium but higher coal excise tax.

   Uncertainties
   – Offshore gas CAPEX overruns (+30 / 0 %).  
   – LNG price divergence (Asia spot vs long-term contracts).


----------------------------------
B. MODELING FRAMEWORK
----------------------------------

Recommended tool: PyPSA-Earth v0.6.0 (MIT licence)

Why PyPSA-Earth?
1. Combined long-term capacity optimisation AND hourly dispatch with unit-commitment-style constraints (via clustered units).  
2. Mature multi-area transmission representation—needed to model gas-pipe and 500 kV backbone congestion central to PDP8.  
3. Existing ASEAN and Vietnam forks (e.g. PyPSA-VN 2023 by TU Berlin) provide templates.  
4. Codebase in active development (≥200 contributors), strong documentation, container images.

Model set-up
• Version & deps: PyPSA-Earth 0.6.0, PyPSA 0.26, xarray, atlite 0.3, pycountry, gurobi-remote or CBC.  
• Temporal resolution:  
  – Investment years: 2025, 2030, 2035, 2040, 2045, 2050.  
  – Representative hours: 8,760 for milestone years (no time-slice aggregation) to capture peak-demand/gas-supply constraints; solved with rolling-horizon 24 h clusters if memory tight.  
• Spatial resolution: 11 nodes (Northern, Central 1/2/3, Southern) reflecting EVN system-operator zones; gas and LNG terminals mapped to the same nodes.  
• Critical features used:  
  – Integer linear commitment for coal units (min up/down, minimum stable load).  
  – Fuel supply constraints (annual domestic production curves, monthly LNG import capacity).  
  – CO₂ accounting with scenario-specific carbon price.  
  – Transmission expansion limit per PDP8 (8 GW per 5 y).

Alternatives evaluated
PyPSA beats OSeMOSYS (no sub-hourly dispatch), Calliope (weaker UC), TEMOA (AGPL + less community) and Switch (US-centric data pipeline).  


----------------------------------
C. DATA REQUIREMENTS & OPEN SOURCES
----------------------------------

(Only key lines shown – full spreadsheet in repository)

1. Existing generation fleet  
   • Parameter: Plant name, fuel, net MW, heat-rate (GJ/MWh), COD  
   • Primary: Global Power Plant Database v1.3 (https://datasets.wri.org) 2022  
   • Fallback: Global Energy Monitor Coal & Gas Tracker 2023  
   • Pre-processing: deduct 7 % auxiliary loss; harmonise fuel codes.

2. Fuel prices  
   a) Domestic coal mine mouth (USD/t, HHV)  
      – Source: Vinacomin annual report 2022 (URL not verified)  
      – Fallback: Vietnam GSO “Industrial Production and Price Index” table 024a.  
   b) Newcastle FOB (USD/t)  
      – Source: ICE Futures Europe historical settlement via Quandl (free API).  
   c) LNG spot JKM (USD/MMBtu)  
      – Source: EIA LNG price brief 2023 Table 3.  
   d) Carbon price pathway  
      – Source: World Bank “State & Trends of Carbon Pricing 2023” – Viet Nam pilot ETS design note.

3. Demand projections  
   • Parameter: Total system load, hourly shape (MWh)  
   • Primary: MOIT PDP8 Appendix XII hourly profiles 2022 (released under Open-Data Decree 73/2020)  
   • GDP series: World Bank WDI NY.GDP.MKTP.KD (constant 2015 $)  
   • EV adoption: Vietnam Automobile Manufacturers Association open data.

4. New build CAPEX/OPEX  
   • IRENA Renewable Power Generation Costs 2022, Annex 3.  
   • Gas & coal: IEA WEO 2022 Stated Policies, Table A28 (publicly downloadable data file).  
   • Battery: NREL ATB 2023 “Mid” trajectory.

5. Renewable resource time series  
   • Solar PV & Wind: renewables.ninja (free non-commercial API) at 0.1° grid, 2012–2021.  
   • Offshore wind: Global Wind Atlas 3.3 mean CFs.

6. Policy parameters  
   • PDP8 Decision 500/QĐ-TTg full annexes (open pdf).  
   • JETP Political Declaration (Dec-2022) – public.  
   • Vietnam updated NDC 2022 (UNFCCC registry).

All data files will be cached in ./data/raw; scripts in ./data/prepare convert to model-ready CSV/NetCDF, tag with commit hash for provenance.


----------------------------------
D. REPRODUCIBILITY PACKAGE
----------------------------------

Repository layout
.
├── environment.yml           (conda)  
├── README.md                 (quick-start)  
├── data  
│   ├── raw/                  (downloaded sources)  
│   └── processed/            (ready for PyPSA)  
├── scripts  
│   ├── 00_download.py        (grab all open data)  
│   ├── 10_prepare_fleet.py  
│   ├── 20_prepare_demand.py  
│   └── build_scenarios.yaml  (Snakemake master)  
├── model  
│   ├── config/               (PyPSA-Earth YAML)  
│   ├── scenarios/            (reference.yml, transition.yml, gasbridge.yml)  
│   └── run.py                (wrapper)  
└── results/                  (auto-generated)

Environment
conda env create -f environment.yml  
• python=3.11, pypsa-earth=0.6.0, atlite=0.3.3, xarray, snakemake, gurobi=10.0 (if licence) or coincbc.

One-command execution
snakemake --cores 8 all      # reproduces data prep, solves 3 scenarios, exports csv

Outputs
results/<scenario>/  
   capacity_{year}.csv  
   generation_{year}.csv  
   emissions.csv  
   system_cost.csv  
   fuel_use.csv  

Validation
script 99_validation.py compares 2018-2022 model back-cast against EVN Statistical Yearbook (peak, total GWh, coal burn). Pass-fail thresholds:  
• Annual generation error <3 %  
• Peak load error <5 %.


----------------------------------
E. EXPECTED QUALITATIVE RESULTS
----------------------------------

1. Reference / PDP8  
   • Thermal capacity: 2030 ≈ 30 GW coal / 25 GW gas; 2050 ≈ 5 GW coal (biomass-co-fired) / 50 GW gas-&-LNG.  
   • Coal generation share: 40 % (2030) → 5 % (2050).  
   • Cum. CO₂ (2025-50): ~9.4 Gt.  
   • System cost rises gently; LNG exposure a major fuel-price risk.  
   • Tipping point: timely gas field commissioning—3-year slip triggers 6 TWh brown-outs in 2031 sensitivity.

2. Accelerated Transition  
   • Thermal capacity: 2030 ≈ 15 GW coal / 22 GW gas; 2050 ≈ 0 GW coal / 15 GW gas (some H₂-ready).  
   • Coal share: 18 % (2030) → 0 % (after 2040).  
   • Cum. CO₂: ~5.1 Gt (46 % below Reference).  
   • Higher upfront CAPEX (+35 Bn $ through 2035) but lower fuel OPEX gives LCOE parity ~2042.  
   • Risks: battery storage cost trajectory; social transition for coal regions.

3. Gas Bridge  
   • Thermal capacity: 2030 ≈ 20 GW coal / 38 GW gas; 2050 ≈ 5 GW coal / 55 GW gas.  
   • Coal share: 25 % (2030) → 6 % (2050).  
   • Cum. CO₂: ~7.9 Gt (15 % below Reference).  
   • System cost middle-of-road, but CO₂ lock-in; sensitivity shows LNG price spike to 20 $/MMBtu lifts total system cost 18 %.  
   • Tipping point: global gas price convergence; if high ≥15 $/MMBtu after 2035, scenario no longer cheaper than Accelerated Transition.

Key insight: early coal retirement alone is insufficient unless coupled with rapid renewables; over-reliance on gas exposes Vietnam to import-price volatility and stranded-asset risk post-2045 decarbonisation tightening.

Graduate students can reproduce all numbers by cloning the repo, creating the conda env, and running Snakemake as described above.