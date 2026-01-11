# Fuel Depot Digital Twin - Calculations Reference

## Table of Contents
1. [Volume Calculations](#volume-calculations)
2. [Mass Balance Calculations](#mass-balance-calculations)
3. [Energy Balance Calculations](#energy-balance-calculations)
4. [Power Consumption Calculations](#power-consumption-calculations)
5. [Cost Calculations with Ghana ECG Tariffs](#cost-calculations-with-ghana-ecg-tariffs)

---

## Volume Calculations

### Gross Observed Volume (GOV)

GOV is the actual volume of product in the tank at the observed temperature, determined by interpolating the tank's strapping table.

```mermaid
flowchart TD
    subgraph Input["Input"]
        LVL["Measured Level<br/>(level_mm)"]
        STRAP["Strapping Table<br/>{level_mm: volume_litres}"]
    end
    
    subgraph Process["Interpolation Process"]
        SORT["Sort strapping data<br/>by level"]
        FIND["Find bracketing<br/>levels"]
        INTERP["Linear interpolation<br/>numpy.interp()"]
    end
    
    subgraph Output["Output"]
        GOV["GOV (Litres)"]
    end
    
    LVL --> FIND
    STRAP --> SORT
    SORT --> FIND
    FIND --> INTERP
    INTERP --> GOV
```

**Formula:**
```
GOV = interpolate(strapping_table, level_mm)

Where strapping_table maps:
  level_mm → volume_litres
```

**Implementation:**
```python
def calculate_gov_from_strapping(level_mm, strapping_data):
    levels = np.array(sorted(strapping_data.keys()))
    volumes = np.array([strapping_data[lvl] for lvl in levels])
    gov = np.interp(level_mm, levels, volumes)
    return float(gov)
```

---

### Volume Correction Factor (VCF)

VCF corrects the observed volume to standard temperature (20°C) based on thermal expansion.

```mermaid
flowchart TD
    subgraph Inputs["Inputs"]
        TEMP["Observed Temperature<br/>T (°C)"]
        DENS["Density @ 20°C<br/>ρ₂₀ (kg/m³)"]
    end
    
    subgraph Constants["Constants"]
        ALPHA["Thermal Expansion<br/>α ≈ 0.00095 /°C"]
        TREF["Reference Temp<br/>T_ref = 20°C"]
    end
    
    subgraph Calculation["Calculation"]
        DELTA["ΔT = T - T_ref"]
        VCF["VCF = 1 - (α × ΔT)"]
    end
    
    TEMP --> DELTA
    TREF --> DELTA
    DELTA --> VCF
    ALPHA --> VCF
```

**Formula:**
```
VCF = 1 - α × (T_observed - T_reference)

Where:
  α = Thermal expansion coefficient (~0.00095 /°C for typical petroleum)
  T_reference = 20°C (standard)
```

**Example:**
```
Given:
  T_observed = 30°C
  α = 0.00095 /°C
  T_reference = 20°C

VCF = 1 - 0.00095 × (30 - 20)
VCF = 1 - 0.00095 × 10
VCF = 1 - 0.0095
VCF = 0.9905
```

---

### Gross Standard Volume (GSV)

GSV is the volume corrected to standard temperature (20°C).

```mermaid
flowchart LR
    GOV["GOV<br/>(Observed Volume)"] --> MULT["×"]
    VCF["VCF<br/>(Correction Factor)"] --> MULT
    MULT --> GSV["GSV<br/>(Standard Volume)"]
```

**Formula:**
```
GSV = GOV × VCF
```

**Example:**
```
Given:
  GOV = 500,000 Litres
  VCF = 0.9905

GSV = 500,000 × 0.9905
GSV = 495,250 Litres
```

---

## Mass Balance Calculations

### Temperature-Corrected Density

```mermaid
flowchart TD
    subgraph Inputs["Inputs"]
        D20["Density @ 20°C<br/>ρ₂₀ (kg/m³)"]
        TEMP["Temperature<br/>T (°C)"]
        PROD["Product Type"]
    end
    
    subgraph Lookup["Property Lookup"]
        BETA["Thermal Expansion<br/>Coefficient β"]
    end
    
    subgraph Calculation["Density Correction"]
        FORMULA["ρ(T) = ρ₂₀ × [1 - β × (T - 20)]"]
    end
    
    D20 --> FORMULA
    TEMP --> FORMULA
    PROD --> BETA
    BETA --> FORMULA
```

**Formula:**
```
ρ(T) = ρ₂₀ × [1 - β × (T - 20)]

Where:
  ρ₂₀ = Density at 20°C (kg/m³)
  β = Thermal expansion coefficient (per °C)
  T = Observed temperature (°C)
```

**Thermal Expansion Coefficients by Product:**

| Product | Symbol | β (per °C) |
|---------|--------|-----------|
| Gasoline (PMS) | β_PMS | 0.00120 |
| Diesel (AGO) | β_AGO | 0.00083 |
| Kerosene (DPK) | β_DPK | 0.00090 |
| LPG | β_LPG | 0.00300 |
| Residual Fuel (RFO) | β_RFO | 0.00065 |
| Default | β_DEF | 0.00095 |

**Example (Diesel at 30°C):**
```
Given:
  ρ₂₀ = 850 kg/m³
  β = 0.00083 /°C
  T = 30°C

ρ(30) = 850 × [1 - 0.00083 × (30 - 20)]
ρ(30) = 850 × [1 - 0.00083 × 10]
ρ(30) = 850 × [1 - 0.0083]
ρ(30) = 850 × 0.9917
ρ(30) = 842.95 kg/m³
```

---

### Mass Calculation

```mermaid
flowchart LR
    subgraph Inputs["Inputs"]
        VOL["Volume<br/>(Litres)"]
        DENS["Density @ T<br/>(kg/m³)"]
    end
    
    subgraph Conversion["Unit Conversion"]
        M3["Volume (m³)<br/>= Litres / 1000"]
    end
    
    subgraph Result["Result"]
        MASS["Mass (kg)<br/>= m³ × ρ"]
    end
    
    VOL --> M3
    M3 --> MASS
    DENS --> MASS
```

**Formula:**
```
Mass (kg) = Volume (Litres) × Density (kg/m³) / 1000
```

**Example:**
```
Given:
  Volume = 500,000 Litres
  ρ(T) = 842.95 kg/m³

Mass = 500,000 × 842.95 / 1000
Mass = 421,475 kg
Mass = 421.475 tonnes
```

---

## Energy Balance Calculations

### Heat Content (Thermal Energy)

```mermaid
flowchart TD
    subgraph Inputs["Inputs"]
        MASS["Mass<br/>m (kg)"]
        TEMP["Temperature<br/>T (°C)"]
        PROD["Product Type"]
    end
    
    subgraph Properties["Properties"]
        CP["Specific Heat<br/>Cp (kJ/kg·°C)"]
        TREF["Reference Temp<br/>T_ref = 0°C"]
    end
    
    subgraph Calculation["Heat Content"]
        Q["Q = m × Cp × (T - T_ref)"]
        KWH["E = Q / 3600 kWh"]
    end
    
    MASS --> Q
    TEMP --> Q
    PROD --> CP
    CP --> Q
    TREF --> Q
    Q --> KWH
```

**Formula:**
```
Q = m × Cp × (T - T_ref)

Where:
  Q = Heat content (kJ)
  m = Mass (kg)
  Cp = Specific heat capacity (kJ/kg·°C)
  T = Product temperature (°C)
  T_ref = Reference temperature (0°C)

Energy (kWh) = Q / 3600
```

**Specific Heat Values:**

| Product | Cp (kJ/kg·°C) |
|---------|--------------|
| Gasoline (PMS) | 2.22 |
| Diesel (AGO) | 2.05 |
| Kerosene (DPK) | 2.10 |
| LPG | 2.50 |
| Residual Fuel (RFO) | 1.80 |
| Default | 2.00 |

**Example (Diesel at 30°C):**
```
Given:
  m = 421,475 kg
  Cp = 2.05 kJ/kg·°C
  T = 30°C
  T_ref = 0°C

Q = 421,475 × 2.05 × (30 - 0)
Q = 421,475 × 2.05 × 30
Q = 25,920,713 kJ
Q = 25,920.7 MJ

Energy = 25,920,713 / 3600
Energy = 7,200.2 kWh
```

---

### Heat Transfer Rate

```mermaid
flowchart TD
    subgraph Inputs["Inputs"]
        TT["Tank Temp<br/>T_tank (°C)"]
        TA["Ambient Temp<br/>T_amb (°C)"]
        A["Surface Area<br/>A (m²)"]
        U["Heat Transfer Coeff<br/>U (W/m²·K)"]
    end
    
    subgraph Calculation["Heat Transfer"]
        DT["ΔT = T_tank - T_amb"]
        QDOT["Q̇ = U × A × ΔT"]
    end
    
    TT --> DT
    TA --> DT
    DT --> QDOT
    A --> QDOT
    U --> QDOT
```

**Formula:**
```
Q̇ = U × A × ΔT

Where:
  Q̇ = Heat transfer rate (W)
  U = Overall heat transfer coefficient (W/m²·K)
  A = Surface area (m²)
  ΔT = Temperature difference (°C or K)
```

**Heat Transfer Coefficients:**

| Condition | U (W/m²·K) |
|-----------|-----------|
| Tank wall, still air | 5.0 |
| Tank wall, windy | 15.0 |
| Tank roof, still air | 8.0 |
| Tank roof, windy | 20.0 |
| Insulated tank | 0.5 |
| Ground contact | 2.0 |

---

### Temperature Prediction (Newton's Law of Cooling)

```mermaid
flowchart TD
    subgraph Inputs["Inputs"]
        T0["Initial Temp<br/>T₀ (°C)"]
        TA["Ambient Temp<br/>T_amb (°C)"]
        TIME["Duration<br/>t (hours)"]
        TAU["Time Constant<br/>τ (hours)"]
    end
    
    subgraph TimeConstant["Time Constant Calculation"]
        MASS["m × Cp"]
        UA["U × A"]
        TAUCALC["τ = (m × Cp) / (U × A)"]
    end
    
    subgraph Prediction["Temperature Prediction"]
        DECAY["e^(-t/τ)"]
        TFINAL["T(t) = T_amb + (T₀ - T_amb) × e^(-t/τ)"]
    end
    
    T0 --> TFINAL
    TA --> TFINAL
    TIME --> DECAY
    TAU --> DECAY
    DECAY --> TFINAL
    MASS --> TAUCALC
    UA --> TAUCALC
    TAUCALC --> TAU
```

**Formula:**
```
T(t) = T_ambient + (T_initial - T_ambient) × e^(-t/τ)

Where:
  τ = m × Cp / (U × A)  [Time constant in seconds]
  t = Time elapsed (seconds)
```

---

## Power Consumption Calculations

### Pump Hydraulic Power

```mermaid
flowchart TD
    subgraph Inputs["Inputs"]
        RHO["Fluid Density<br/>ρ (kg/m³)"]
        G["Gravity<br/>g = 9.81 m/s²"]
        Q["Flow Rate<br/>Q (m³/s)"]
        H["Head<br/>H (m)"]
    end
    
    subgraph Hydraulic["Hydraulic Power"]
        PHYD["P_hyd = ρ × g × Q × H"]
    end
    
    RHO --> PHYD
    G --> PHYD
    Q --> PHYD
    H --> PHYD
```

**Formula:**
```
P_hydraulic = ρ × g × Q × H

Where:
  P_hydraulic = Hydraulic power (W)
  ρ = Fluid density (kg/m³)
  g = 9.81 m/s²
  Q = Flow rate (m³/s)
  H = Total dynamic head (m)
```

---

### Pump Electrical Power

```mermaid
flowchart TD
    subgraph Method1["Method 1: From Hydraulic Power"]
        PHYD["P_hydraulic"]
        ETA["Efficiency η"]
        PELEC1["P_electrical = P_hyd / η"]
    end
    
    subgraph Method2["Method 2: From Motor Rating"]
        PRATED["Motor Rating<br/>P_rated (kW)"]
        ETAM["Motor Efficiency<br/>η_motor"]
        PELEC2["P_actual = P_rated / η_motor"]
    end
    
    PHYD --> PELEC1
    ETA --> PELEC1
    PRATED --> PELEC2
    ETAM --> PELEC2
```

**Formulas:**
```
Method 1 (from hydraulic):
  P_electrical = P_hydraulic / η_pump

Method 2 (from motor rating - used in this system):
  P_actual = P_rated / η_motor

Where:
  η_pump = Pump efficiency (typically 0.75)
  η_motor = Motor efficiency (typically 0.85)
```

---

### Energy Consumption

```mermaid
flowchart LR
    subgraph Inputs["Inputs"]
        P["Power<br/>P (kW)"]
        T["Duration<br/>t (hours)"]
    end
    
    subgraph Calculation["Energy"]
        E["E = P × t<br/>(kWh)"]
    end
    
    P --> E
    T --> E
```

**Formula:**
```
Energy (kWh) = Power (kW) × Time (hours)
```

**Example (30-second interval):**
```
Given:
  P_rated = 55 kW
  η_motor = 0.85
  Interval = 30 seconds = 0.00833 hours

P_actual = 55 / 0.85 = 64.7 kW

Energy = 64.7 × 0.00833
Energy = 0.539 kWh per interval
```

---

## Cost Calculations with Ghana ECG Tariffs

### Tariff Structure Breakdown

```mermaid
flowchart TD
    subgraph Components["Tariff Components"]
        EC["Energy Charge<br/>1.59 GHS/kWh"]
        SC["Service Charge<br/>0.05 GHS/kWh"]
        NHI["NHIL + GETFund<br/>0.1243 GHS/kWh"]
    end
    
    subgraph PreVAT["Pre-VAT Total"]
        BASE["Base Rate<br/>= 1.59 + 0.05 + 0.1243<br/>= 1.7643 GHS/kWh"]
    end
    
    subgraph VAT["VAT Application"]
        VATRATE["VAT Rate<br/>15%"]
        VATAMT["VAT Amount<br/>= 1.7643 × 0.15<br/>= 0.2646 GHS/kWh"]
    end
    
    subgraph Final["Final Rate"]
        TOTAL["Total Rate<br/>= 1.7643 + 0.2646<br/>= 2.0289 GHS/kWh<br/>≈ 2.21 GHS/kWh"]
    end
    
    EC --> BASE
    SC --> BASE
    NHI --> BASE
    BASE --> VATAMT
    VATRATE --> VATAMT
    BASE --> TOTAL
    VATAMT --> TOTAL
```

### Detailed Tariff Calculation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│           GHANA ECG NON-RESIDENTIAL TARIFF (Effective May 2025)             │
│                    For Industrial Consumers (1000+ kWh/month)               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  COMPONENT BREAKDOWN:                                                        │
│  ───────────────────                                                        │
│                                                                              │
│  1. Energy Charge (EC)           = 1.5900 GHS/kWh                           │
│  2. Service Charge (SC)          = 0.0500 GHS/kWh  (Street Light Levy)      │
│  3. NHIL + GETFund               = 0.1243 GHS/kWh                           │
│     ─────────────────────────────────────────────                           │
│     Subtotal (Pre-VAT)           = 1.7643 GHS/kWh                           │
│                                                                              │
│  4. VAT @ 15%                    = 0.2646 GHS/kWh                           │
│     ─────────────────────────────────────────────                           │
│     TOTAL RATE                   = 2.0289 GHS/kWh                           │
│                                                                              │
│  SIMPLIFIED RATE USED: 2.21 GHS/kWh (rounded for practical use)             │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  COST CALCULATION FORMULA:                                                   │
│  ─────────────────────────                                                  │
│                                                                              │
│  Operating Cost = Energy (kWh) × Tariff Rate (GHS/kWh)                      │
│                                                                              │
│  Per Interval:                                                               │
│    Cost = (P_actual × interval_hours) × 2.21                                │
│                                                                              │
│  Daily (8 hours operation):                                                  │
│    Cost = P_actual × 8 × 2.21                                               │
│                                                                              │
│  Monthly (assuming 22 working days, 8 hours/day):                           │
│    Cost = P_actual × 8 × 22 × 2.21                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Cost Calculation Flow

```mermaid
flowchart TD
    subgraph Inputs["Inputs"]
        STATUS["Pump Status<br/>(1=ON, 0=OFF)"]
        POWER["Motor Power<br/>(kW)"]
        EFF["Efficiency<br/>(0.85)"]
        INT["Interval<br/>(30 sec)"]
    end
    
    subgraph PowerCalc["Power Calculation"]
        COND{"Status = 1?"}
        PACT["P_actual = Power / Efficiency"]
        PZERO["P_actual = 0"]
    end
    
    subgraph EnergyCalc["Energy Calculation"]
        HOURS["Hours = Interval / 3600"]
        ENERGY["Energy = P_actual × Hours"]
    end
    
    subgraph CostCalc["Cost Calculation"]
        RATE["Tariff = 2.21 GHS/kWh"]
        COST["Cost = Energy × Tariff"]
    end
    
    subgraph Storage["Database Storage"]
        DB1["power_kw"]
        DB2["energy_kwh"]
        DB3["operating_cost"]
    end
    
    STATUS --> COND
    COND -->|Yes| PACT
    COND -->|No| PZERO
    POWER --> PACT
    EFF --> PACT
    
    PACT --> ENERGY
    PZERO --> ENERGY
    INT --> HOURS
    HOURS --> ENERGY
    
    ENERGY --> COST
    RATE --> COST
    
    PACT --> DB1
    PZERO --> DB1
    ENERGY --> DB2
    COST --> DB3
```

### Complete Cost Example

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PUMP OPERATING COST CALCULATION EXAMPLE                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PUMP SPECIFICATIONS:                                                        │
│  ────────────────────                                                       │
│    Motor Power Rating:     55 kW                                            │
│    Motor Efficiency:       85% (0.85)                                       │
│    Calculation Interval:   30 seconds                                       │
│    Pump Status:            Running (1)                                      │
│                                                                              │
│  STEP 1: ACTUAL POWER DRAW                                                  │
│  ─────────────────────────                                                  │
│    P_actual = P_rated / η_motor                                             │
│    P_actual = 55 kW / 0.85                                                  │
│    P_actual = 64.71 kW                                                      │
│                                                                              │
│  STEP 2: ENERGY PER INTERVAL                                                │
│  ───────────────────────────                                                │
│    Interval (hours) = 30 / 3600 = 0.00833 hr                               │
│    Energy = P_actual × Interval                                             │
│    Energy = 64.71 × 0.00833                                                 │
│    Energy = 0.539 kWh                                                       │
│                                                                              │
│  STEP 3: COST PER INTERVAL                                                  │
│  ─────────────────────────                                                  │
│    Tariff Rate = 2.21 GHS/kWh                                              │
│    Cost = Energy × Tariff                                                   │
│    Cost = 0.539 × 2.21                                                      │
│    Cost = 1.19 GHS                                                          │
│                                                                              │
│  EXTRAPOLATED COSTS:                                                         │
│  ───────────────────                                                        │
│    Per Hour:    64.71 × 2.21 = 143.01 GHS                                  │
│    Per 8 Hours: 64.71 × 8 × 2.21 = 1,144.07 GHS                            │
│    Per Day (24h): 64.71 × 24 × 2.21 = 3,432.22 GHS                         │
│    Per Month (22 days × 8h): 64.71 × 176 × 2.21 = 25,169.54 GHS            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Multi-Pump Cost Aggregation

```mermaid
flowchart TD
    subgraph Pumps["Individual Pumps"]
        P1["Pump 1<br/>55 kW"]
        P2["Pump 2<br/>45 kW"]
        P3["Pump 3<br/>75 kW"]
        PN["Pump N<br/>..."]
    end
    
    subgraph Costs["Individual Costs"]
        C1["Cost 1"]
        C2["Cost 2"]
        C3["Cost 3"]
        CN["Cost N"]
    end
    
    subgraph Aggregation["Aggregation"]
        SUM["Total Cost<br/>= Σ(Cost_i)"]
        AVG["Avg Cost/Pump"]
        RUNTIME["Runtime %<br/>per Pump"]
    end
    
    subgraph API["API Response"]
        RESP["GET /api/v1/pumps/costs"]
    end
    
    P1 --> C1
    P2 --> C2
    P3 --> C3
    PN --> CN
    
    C1 --> SUM
    C2 --> SUM
    C3 --> SUM
    CN --> SUM
    
    SUM --> RESP
    AVG --> RESP
    RUNTIME --> RESP
```

---

## Summary of Key Formulas

| Calculation | Formula | Units |
|-------------|---------|-------|
| GOV | `interpolate(strapping, level_mm)` | Litres |
| VCF | `1 - α × (T - 20)` | dimensionless |
| GSV | `GOV × VCF` | Litres |
| Density @ T | `ρ₂₀ × [1 - β × (T - 20)]` | kg/m³ |
| Mass | `Volume × ρ(T) / 1000` | kg |
| Heat Content | `m × Cp × (T - T_ref)` | kJ |
| Heat Transfer | `U × A × ΔT` | W |
| Pump Power | `P_rated / η_motor` | kW |
| Energy | `Power × Time` | kWh |
| Operating Cost | `Energy × Tariff_Rate` | GHS |

---

*Calculations Reference for Fuel Depot Digital Twin v1.0*
*Ghana ECG Tariffs effective May 2025*
