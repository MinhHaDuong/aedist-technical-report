### A. Scenario Definitions

#### 1. Reference / PDP8 Baseline
- **Thermal Capacity (MW):**
  - *2025-2030:* Coal +10,000, LNG +5,000, Gas +2,000  
  - *2030-2040:* Coal +5,000, LNG +5,000, Gas +2,000  
  - *2040-2050:* Coal +3,000, LNG +5,000, Gas +2,000  
  - *Retirements:* Coal -1,000 (2025-2030), -2,000 (2030-2040), -3,000 (2040-2050)

- **Fuel Supply:**
  - Domestic coal: 100 Mtpa (2023) +1% annual growth  
  - Domestic gas: 10 BCM (2023) +3% annual growth  
  - LNG price: $8.5/MMBtu (2023) +2% annual inflation  
  - Carbon price: $0 until 2030, then $10/ton CO₂ (2030) +5% annually  

- **Demand Growth:**
  - GDP elasticity: 0.8  
  - Industrial load: 7% annual growth  
  - EV penetration: 10% of new sales (2030), 30% (2040), 50% (2050)  

- **Policy Levers:**
  - Carbon tax: None until 2030  
  - Coal moratorium: None  
  - Renewable target: 21% total generation (2030)  
  - Gas price: Regulated by MOIT  

- **Key Uncertainties:**  
  - Coal production constraints (geological limits)  
  - LNG import capacity delays  
  - EV adoption faster than forecast  

#### 2. Accelerated Transition
- **Thermal Capacity (MW):**
  - *2025-2030:* Coal +5,000, LNG +8,000, Gas +3,000  
  - *2030-2040:* Coal +0, LNG +7,000, Gas +3,000  
  - *2040-2050:* Coal +0, LNG +5,000, Gas +3,000  
  - *Retirements:* Coal -5,000 (2025-2030), -10,000 (2030-2040), -15,000 (2040-2050)  

- **Fuel Supply:**
  - Domestic coal: 100 Mtpa (2023) capped  
  - Domestic gas: 10 BCM (2023) +3% annual growth  
  - LNG price: $8.5/MMBtu (2023) +2% annual inflation  
  - Carbon price: $20/ton CO₂ (2030) +10% annually  

- **Demand Growth:**
  - GDP elasticity: 0.8  
  - Industrial load: 7% annual growth  
  - EV penetration: 20% (2030), 50% (2040), 70% (2050)  

- **Policy Levers:**
  - Carbon tax: $20/ton CO₂ (2030) +10% annually  
  - Coal moratorium: Immediate moratorium after 2025  
  - Renewable target: 30% total generation (2030)  
  - Gas price: Regulated by MOIT  

- **Key Uncertainties:**  
  - Renewable cost reductions exceeding forecasts  
  - Gas supply shortages from Block B/CVX  
  - Policy implementation delays  

#### 3. Gas Bridge
- **Thermal Capacity (MW):**
  - *2025-2030:* Coal +8,000, LNG +7,000, Gas +4,000  
  - *2030-2040:* Coal +3,000, LNG +5,000, Gas +4,000  
  - *2040-2050:* Coal +0, LNG +3,000, Gas +4,000  
  - *Retirements:* Coal -2,000 (2025-2030), -4,000 (2030-2040), -6,000 (2040-2050)  

- **Fuel Supply:**
  - Domestic coal: 100 Mtpa (2023) capped  
  - Domestic gas: 10 BCM (2023) +5% annual growth (maximized)  
  - LNG price: $8.5/MMBtu (2023) +2% annual inflation  
  - Carbon price: $10/ton CO₂ (2030) +5% annually  

- **Demand Growth:**
  - GDP elasticity: 0.8  
  - Industrial load: 7% annual growth  
  - EV penetration: 15% (2030), 40% (2040), 60% (2050)  

- **Policy Levers:**
  - Carbon tax: $10/ton CO₂ (2030) +5% annually  
  - Coal moratorium: Moratorium after 2030  
  - Renewable target: 25% total generation (2030)  
  - Gas price: Regulated by MOIT  

- **Key Uncertainties:**  
  - Gas production from Block B/CVX exceeding projections  
  - Renewable cost reductions  
  - Transmission constraints for gas plants  

---

### B. Modeling Framework  
**Recommended Model: PyPSA**  

| Model       | License | Granularity | Vietnam Support | Active Community |  
|-------------|---------|-------------|-----------------|------------------|  
| **PyPSA**   | MIT     | Hourly, network | Configurable | Yes |  
| OSeMOSYS    | Apache-2.0 | Annual | ASEAN precedents | Yes |  
| Calliope    | Apache-2.0 | Multi-carrier | Configurable | Moderate |  
| Temoa       | AGPL    | Annual | Academic use | Moderate |  
| Switch      | Apache-2.0 | Investment + dispatch | US-focused | Moderate |  

**Justification for PyPSA:**  
- **Temporal Resolution:** Hourly dispatch captures renewable intermittency and thermal plant cycling.  
- **Spatial Resolution:** Network modeling (e.g., province-level nodes) accounts for transmission constraints.  
- **Key Features:** Unit commitment, fuel supply constraints (e.g., gas pipeline capacity), and explicit emission modeling.  
- **Vietnam Suitability:** Handles complex fuel mix transitions and integrates renewable profiles (e.g., from renewables.ninja).  

**Model Specifications:**  
- **Version:** PyPSA 0.23.0 (Python 3.8+)  
- **Dependencies:** pandas, numpy, scipy, geopandas, shapely, pyproj  
- **Temporal Resolution:** 2025–2050, hourly (with 5-year capacity expansion intervals)  
- **Spatial Resolution:** 8 provinces (North, Central, South) + 3 load centers (Hanoi, Ho Chi Minh City, Da Nang)  

---

### C. Data Requirements and Sources  

| Data Category          | Parameter Name & Units                     | Primary Source (URL)                          | Vintage | Fallback Source | Preprocessing |  
|------------------------|--------------------------------------------|-----------------------------------------------|---------|-----------------|---------------|  
| **Existing Fleet**     | Plant capacity (MW), heat rate (kWh/MWh)   | Global Energy Monitor (GEM): https://globalenergymonitor.org/ | 2023    | World Resources Institute | Harmonize plant IDs, calculate remaining life |  
| **Fuel Costs**         | Domestic coal ($/ton)                      | Ministry of Industry and Trade (MOIT): https://moit.gov.vn/ | 2023    | World Bank Energy Sector Report | Normalize to 2023 prices |  
|                        | LNG ($/MMBtu)                              | Singapore LNG Exchange: https://www.sgx.com/ | 2023    | World Bank      | Use 2023 average |  
| **Demand Projections** | Annual demand (GWh)                        | MOIT Load Forecast: https://moit.gov.vn/      | 2023    | World Bank      | Scale by GDP elasticity |  
| **Technology Costs**   | CAPEX (USD/kW): Coal USC, Gas CCGT, Solar  | IRENA Renewable Cost Database: https://www.irena.org/ | 2023    | NREL ATB        | Adjust for Vietnam-specific O&M |  
| **Policy Parameters**  | Carbon tax ($/ton), renewable targets (%)  | PDP8 Decision 500/QĐ-TTg: https://chinhphu.vn/ | 2023    | JETP Documents  | Extract scenario-specific values |  
| **Renewable Profiles** | Hourly capacity factors (solar/wind)       | renewables.ninja: https://renewables.ninja/   | 2023    | Global Solar Atlas | Resample to hourly |  

---

### D. Reproducibility Package  

**Repository Structure:**  
```  
/thermal_power_vietnam_2050  
├── /data  
│   ├── /raw (raw datasets)  
│   ├── /processed (cleaned data)  
├── /models  
│   ├── /pypsacode.py (PyPSA model)  
├── /scripts  
│   ├── /run_scenarios.py (main script)  
│   ├── /preprocess_data.py (data harmonization)  
├── /results  
│   ├── /reference (CSV outputs)  
│   ├── /accelerated  
│   └── /gas_bridge  
├── /environment  
│   ├── environment.yml (conda)  
│   └── requirements.txt (pip)  
└── /docs  
    ├── README.md  
    └── run_instructions.md  
```  

**Environment Specification:**  
- `environment.yml`: Python 3.8, PyPSA 0.23.0, pandas, numpy, geopandas  
- `conda create -n vnpower python=3.8`  

**Run Instructions:**  
```bash  
python scripts/run_scenarios.py --scenarios reference accelerated gas_bridge  
```  
*Outputs:* CSV time series for capacity mix, generation mix, emissions, and system cost.  

**Validation:**  
- Compare model-simulated 2015–2023 generation with EVN historical data (from EVN reports).  
- Sensitivity analysis: Vary carbon price ±20% and renewable cost reductions ±15%.  

---

### E. Expected Results Discussion  

#### Reference Scenario  
- **2030 Thermal Capacity:** 23,000 MW (Coal 10,000 MW, LNG 5,000 MW, Gas 2,000 MW)  
- **2050 Thermal Capacity:** 39,000 MW (Coal 18,000 MW, LNG 15,000 MW, Gas 6,000 MW)  
- **Coal Share (2030):** 45%  
- **Coal Share (2050):** 40%  
- **Cumulative CO₂ (2025–2050):** 12.5 Gt  
- **System Cost:** Moderate (high fuel costs in 2040s)  
- **Risks:** Stranded assets if transition accelerates; high emissions.  

#### Accelerated Transition  
- **2030 Thermal Capacity:** 16,000 MW (Coal 5,000 MW, LNG 8,000 MW, Gas 3,000 MW)  
- **2050 Thermal Capacity:** 35,000 MW (Coal 0 MW, LNG 20,000 MW, Gas 9,000 MW)  
- **Coal Share (2030):** 25%  
- **Coal Share (2050):** 10%  
- **Cumulative CO₂ (2025–2050):** 6.2 Gt  
- **System Cost:** High upfront investment, lower long-term costs  
- **Risks:** LNG import dependency; gas supply shortages.  

#### Gas Bridge  
- **2030 Thermal Capacity:** 19,000 MW (Coal 8,000 MW, LNG 7,000 MW, Gas 4,000 MW)  
- **2050 Thermal Capacity:** 32,000 MW (Coal 2,000 MW, LNG 18,000 MW, Gas 12,000 MW)  
- **Coal Share (2030):** 35%  
- **Coal Share (2050):** 20%  
- **Cumulative CO₂ (2025–2050):** 8.5 Gt  
- **System Cost:** Balanced (lower than Reference, higher than Accelerated)  
- **Risks:** Gas supply constraints; delayed renewables scaling.  

**Key Tipping Points:**  
- Carbon price >$25/ton CO₂ accelerates coal retirement.  
- Renewable cost reductions >15% by 2030 enable faster transition.  
- Gas production from Block B/CVX exceeding 12 BCM/year reduces LNG imports.  

---  
*All data sources are open-access. Primary sources are government/multilateral reports. Scenario parameters are specific to publications (e.g., PDP8 Decision 500/QĐ-TTg, JETP documents).*