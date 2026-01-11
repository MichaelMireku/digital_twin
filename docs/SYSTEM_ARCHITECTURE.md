# Fuel Depot Digital Twin - System Architecture Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Diagrams](#architecture-diagrams)
3. [Data Flow](#data-flow)
4. [Power Consumption & Tariff Calculations](#power-consumption--tariff-calculations)
5. [Physics Engine](#physics-engine)
6. [Database Schema](#database-schema)
7. [API Reference](#api-reference)
8. [Alerting System](#alerting-system)

---

## System Overview

The Fuel Depot Digital Twin is a comprehensive monitoring and simulation platform for petroleum storage facilities. It provides real-time monitoring, physics-based calculations, cost tracking, and alerting for fuel depot operations in Ghana.

### Key Features
- Real-time sensor data collection via MQTT
- Physics-based volume, mass, and energy calculations
- Ghana ECG electricity tariff integration for cost tracking
- Fire consequence simulation
- Tank transfer simulation
- Interactive dashboard with HMI visualization
- Configurable alerting system

---

## Architecture Diagrams

### High-Level System Architecture

```mermaid
flowchart TB
    subgraph External["External Systems"]
        MQTT[("MQTT Broker<br/>HiveMQ Cloud")]
        Weather["OpenWeather API"]
    end
    
    subgraph Sensors["Sensor Layer"]
        SIM["Sensor Simulator<br/>(sensor_simulator.py)"]
        PHYS["Physical Sensors<br/>(Future)"]
    end
    
    subgraph Core["Core Services"]
        API["Flask REST API<br/>(api/app.py)"]
        CALC["Calculation Service<br/>(calculation_service.py)"]
        ALERT["Alerting Service<br/>(alerting_service.py)"]
    end
    
    subgraph Physics["Physics Engine"]
        MASS["Mass Balance<br/>Calculator"]
        ENERGY["Energy Balance<br/>Calculator"]
        VOL["Volume Calculator<br/>(GOV/GSV)"]
    end
    
    subgraph Storage["Data Layer"]
        DB[("PostgreSQL<br/>TimescaleDB")]
    end
    
    subgraph Presentation["Presentation Layer"]
        DASH["Dash Dashboard<br/>(dashboard.py)"]
        HMI["3D HMI View<br/>(3dview.html)"]
    end
    
    SIM -->|Publish| MQTT
    PHYS -.->|Publish| MQTT
    MQTT -->|Subscribe| CALC
    
    CALC --> MASS
    CALC --> ENERGY
    CALC --> VOL
    
    CALC -->|Store| DB
    ALERT -->|Read/Write| DB
    API -->|Read/Write| DB
    
    DASH -->|REST Calls| API
    HMI -->|REST Calls| API
    Weather -->|Weather Data| DASH
    
    DB -->|Query| ALERT
    DB -->|Query| API
```

### Service Communication Flow

```mermaid
sequenceDiagram
    participant SIM as Sensor Simulator
    participant MQTT as MQTT Broker
    participant CALC as Calculation Service
    participant DB as PostgreSQL
    participant ALERT as Alerting Service
    participant API as REST API
    participant DASH as Dashboard
    
    loop Every 10 seconds
        SIM->>MQTT: Publish sensor data
        Note over SIM,MQTT: level_mm, temperature,<br/>pump_status
    end
    
    loop Every 30 seconds
        CALC->>DB: Get latest sensor readings
        DB-->>CALC: Raw sensor data
        CALC->>CALC: Calculate GOV, GSV, Mass
        CALC->>CALC: Calculate Energy & Costs
        CALC->>DB: Store calculated_data
    end
    
    loop Every 20 seconds
        ALERT->>DB: Load alert rules
        ALERT->>DB: Get asset states
        ALERT->>ALERT: Evaluate conditions
        ALERT->>DB: Create/Resolve alerts
    end
    
    loop Every 5 seconds
        DASH->>API: GET /api/v1/assets
        API->>DB: Query assets + state
        DB-->>API: Asset data
        API-->>DASH: JSON response
        DASH->>DASH: Update visualizations
    end
```

---

## Data Flow

### Sensor Data Pipeline

```mermaid
flowchart LR
    subgraph Input["Data Sources"]
        TANK_SENS["Tank Sensors"]
        PUMP_SENS["Pump Sensors"]
    end
    
    subgraph Processing["Processing Pipeline"]
        RAW["Raw Readings<br/>(sensor_readings)"]
        CALC["Calculations"]
        DERIVED["Derived Metrics<br/>(calculated_data)"]
    end
    
    subgraph Output["Outputs"]
        DASH["Dashboard"]
        ALERTS["Alerts"]
        REPORTS["Reports"]
    end
    
    TANK_SENS -->|level_mm<br/>temperature| RAW
    PUMP_SENS -->|pump_status<br/>motor_current| RAW
    
    RAW -->|Every 30s| CALC
    
    CALC -->|level_percentage<br/>volume_gov<br/>volume_gsv<br/>mass_kg<br/>heat_content_kj| DERIVED
    
    CALC -->|power_kw<br/>energy_kwh<br/>operating_cost| DERIVED
    
    DERIVED --> DASH
    DERIVED --> ALERTS
    DERIVED --> REPORTS
```

### Tank Metrics Calculation Flow

```mermaid
flowchart TD
    subgraph Inputs["Sensor Inputs"]
        LVL["level_mm"]
        TEMP["temperature (°C)"]
    end
    
    subgraph Static["Static Data"]
        STRAP["Strapping Table"]
        DENS["density_at_20c"]
        CAP["capacity_litres"]
    end
    
    subgraph Calculations["Calculation Steps"]
        PCT["Level %<br/>= level_mm / max_level × 100"]
        GOV["GOV (Litres)<br/>= interpolate(strapping, level_mm)"]
        VCF["VCF<br/>= 1 - α × (T - 20)"]
        GSV["GSV (Litres)<br/>= GOV × VCF"]
        MASS["Mass (kg)<br/>= GSV × ρ(T) / 1000"]
        HEAT["Heat Content (kJ)<br/>= mass × Cp × (T - 0)"]
    end
    
    LVL --> PCT
    LVL --> GOV
    STRAP --> GOV
    
    TEMP --> VCF
    DENS --> VCF
    
    GOV --> GSV
    VCF --> GSV
    
    GSV --> MASS
    TEMP --> MASS
    DENS --> MASS
    
    MASS --> HEAT
    TEMP --> HEAT
```

---

## Power Consumption & Tariff Calculations

### Ghana ECG Tariff Structure

The system implements Ghana's Electricity Company of Ghana (ECG) Non-Residential tariff structure for industrial consumers in the 1000+ kWh/month consumption band.

```mermaid
flowchart TD
    subgraph Tariff["Ghana ECG Non-Residential Tariff (May 2025)"]
        EC["Energy Charge<br/>1.59 GHS/kWh"]
        SC["Service Charge<br/>0.05 GHS/kWh"]
        NHI["NHIL + GETFund<br/>0.1243 GHS/kWh"]
        VAT["VAT<br/>15%"]
    end
    
    subgraph Calculation["Cost Calculation"]
        BASE["Base Rate<br/>= EC + SC + NHI<br/>= 1.7643 GHS/kWh"]
        TOTAL["Total Rate<br/>= Base × (1 + VAT)<br/>≈ 2.03 GHS/kWh"]
        SIMPLE["Simplified Rate<br/>2.21 GHS/kWh"]
    end
    
    EC --> BASE
    SC --> BASE
    NHI --> BASE
    BASE --> TOTAL
    VAT --> TOTAL
    TOTAL -.->|Rounded| SIMPLE
```

### Pump Power Consumption Calculation

```mermaid
flowchart TD
    subgraph Inputs["Pump Parameters"]
        MOTOR["Motor Power<br/>(motor_power_kw)<br/>Default: 55 kW"]
        EFF["Motor Efficiency<br/>(motor_efficiency)<br/>Default: 0.85"]
        STATUS["Pump Status<br/>1 = Running<br/>0 = Stopped"]
        INT["Calculation Interval<br/>30 seconds"]
    end
    
    subgraph Power["Power Calculation"]
        ACTUAL["Actual Power Draw<br/>P = motor_power_kw / efficiency<br/>= 55 / 0.85 = 64.7 kW"]
        COND["If pump_status = 1<br/>power_kw = P<br/>Else power_kw = 0"]
    end
    
    subgraph Energy["Energy Calculation"]
        HOURS["Interval Hours<br/>= 30 / 3600<br/>= 0.00833 hr"]
        KWH["Energy (kWh)<br/>= power_kw × interval_hours<br/>= 64.7 × 0.00833<br/>= 0.539 kWh"]
    end
    
    subgraph Cost["Cost Calculation"]
        RATE["Tariff Rate<br/>2.21 GHS/kWh"]
        COST["Operating Cost<br/>= energy_kwh × rate<br/>= 0.539 × 2.21<br/>= 1.19 GHS"]
    end
    
    MOTOR --> ACTUAL
    EFF --> ACTUAL
    STATUS --> COND
    ACTUAL --> COND
    
    INT --> HOURS
    COND --> KWH
    HOURS --> KWH
    
    KWH --> COST
    RATE --> COST
```

### Detailed Power Calculation Formula

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PUMP POWER CONSUMPTION CALCULATION                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. ACTUAL POWER DRAW (accounting for motor efficiency losses):             │
│                                                                              │
│     P_actual = P_rated / η                                                  │
│                                                                              │
│     Where:                                                                   │
│       P_rated = Motor nameplate power (kW)                                  │
│       η = Motor efficiency (0.85 = 85%)                                     │
│                                                                              │
│     Example: P_actual = 55 kW / 0.85 = 64.7 kW                             │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  2. ENERGY CONSUMPTION per interval:                                        │
│                                                                              │
│     E = P_actual × t                                                        │
│                                                                              │
│     Where:                                                                   │
│       t = interval in hours (30s = 0.00833 hr)                             │
│                                                                              │
│     Example: E = 64.7 kW × 0.00833 hr = 0.539 kWh                          │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  3. OPERATING COST per interval:                                            │
│                                                                              │
│     Cost = E × Tariff_Rate                                                  │
│                                                                              │
│     Where:                                                                   │
│       Tariff_Rate = 2.21 GHS/kWh (Ghana ECG Non-Residential)               │
│                                                                              │
│     Example: Cost = 0.539 kWh × 2.21 GHS/kWh = 1.19 GHS                    │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  4. DAILY COST ESTIMATION (8 hours operation):                              │
│                                                                              │
│     Daily_Cost = P_actual × 8 hr × Tariff_Rate                             │
│                = 64.7 kW × 8 hr × 2.21 GHS/kWh                             │
│                = 1,143.90 GHS/day per pump                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Tariff Configuration (Environment Variables)

```python
# Ghana ECG Non-Residential Tariffs (Effective 1st May 2025)
ENERGY_CHARGE_PER_KWH = 1.59    # GHS/kWh - Base energy charge
SERVICE_CHARGE_PER_KWH = 0.05   # GHS/kWh - Street light levy
NHIL_GETFUND_PER_KWH = 0.1243   # GHS/kWh - National Health Insurance + GETFund
VAT_RATE = 0.15                  # 15% Value Added Tax

# Simplified total rate (pre-calculated)
ELECTRICITY_RATE_PER_KWH = 2.21  # GHS/kWh - All-inclusive rate
```

---

## Physics Engine

### Mass Balance Calculator

```mermaid
flowchart TD
    subgraph Inputs["Inputs"]
        GOV["GOV (Litres)"]
        TEMP["Temperature (°C)"]
        D20["Density @ 20°C<br/>(kg/m³)"]
        PROD["Product Type"]
    end
    
    subgraph Properties["Product Properties"]
        BETA["Thermal Expansion<br/>Coefficient (β)"]
        CP["Specific Heat<br/>(Cp)"]
    end
    
    subgraph Density["Density Correction"]
        DT["ρ(T) = ρ₂₀ × [1 - β × (T - 20)]"]
    end
    
    subgraph Mass["Mass Calculation"]
        M["Mass (kg) = GOV × ρ(T) / 1000"]
    end
    
    GOV --> M
    TEMP --> DT
    D20 --> DT
    PROD --> BETA
    BETA --> DT
    DT --> M
```

### Product Properties Database

| Product | Code | Thermal Expansion (β) | Specific Heat (Cp) | Typical Density @ 20°C |
|---------|------|----------------------|-------------------|----------------------|
| Gasoline | PMS | 0.00120 /°C | 2.22 kJ/kg·°C | 740 kg/m³ |
| Diesel | AGO | 0.00083 /°C | 2.05 kJ/kg·°C | 850 kg/m³ |
| Kerosene | DPK | 0.00090 /°C | 2.10 kJ/kg·°C | 800 kg/m³ |
| LPG | LPG | 0.00300 /°C | 2.50 kJ/kg·°C | 540 kg/m³ |
| Residual Fuel | RFO | 0.00065 /°C | 1.80 kJ/kg·°C | 980 kg/m³ |

### Energy Balance Calculator

```mermaid
flowchart TD
    subgraph Heat["Heat Content Calculation"]
        Q["Q = m × Cp × (T - T_ref)"]
        KWH["Energy (kWh) = Q / 3600"]
    end
    
    subgraph Transfer["Heat Transfer Rate"]
        QDOT["Q̇ = U × A × ΔT"]
    end
    
    subgraph Prediction["Temperature Prediction"]
        NEWTON["T(t) = T_amb + (T₀ - T_amb) × e^(-t/τ)"]
        TAU["τ = m × Cp / (U × A)"]
    end
    
    subgraph Pump["Pump Energy"]
        PHYD["P_hydraulic = ρ × g × Q × H"]
        PELEC["P_electrical = P_hydraulic / η"]
    end
```

### Heat Transfer Coefficients

| Condition | U (W/m²·K) | Description |
|-----------|-----------|-------------|
| Still Air | 5.0 | Tank wall to calm ambient air |
| Windy | 15.0 | Tank wall with wind exposure |
| Roof (Still) | 8.0 | Tank roof to still air |
| Roof (Windy) | 20.0 | Tank roof with wind |
| Insulated | 0.5 | Insulated tank wall |
| Ground | 2.0 | Tank bottom to ground |

---

## Database Schema

### Entity Relationship Diagram

```mermaid
erDiagram
    ASSETS ||--o{ SENSOR_READINGS : generates
    ASSETS ||--o{ CALCULATED_DATA : produces
    ASSETS ||--o{ ALERTS : triggers
    ASSETS ||--o{ STRAPPING_DATA : has
    ASSETS ||--o{ OPERATION_LOGS : references
    ALERT_CONFIGURATIONS ||--o{ ALERTS : defines
    
    ASSETS {
        varchar asset_id PK
        varchar asset_type
        varchar depot_id
        varchar description
        varchar product_service
        numeric capacity_litres
        numeric density_at_20c_kg_m3
        numeric motor_power_kw
        numeric motor_efficiency
        numeric flow_rate_lpm
        boolean is_active
        timestamp created_at
    }
    
    SENSOR_READINGS {
        timestamp time PK
        varchar asset_id FK
        varchar data_source_id
        varchar metric_name
        double value_numeric
        varchar unit
        varchar status
    }
    
    CALCULATED_DATA {
        timestamp time PK
        varchar asset_id PK
        varchar metric_name PK
        double value
        varchar unit
        varchar calculation_status
    }
    
    ALERTS {
        serial alert_id PK
        varchar asset_id FK
        varchar alert_name
        text message
        varchar severity
        varchar status
        timestamp triggered_at
        timestamp resolved_at
        jsonb details
    }
    
    ALERT_CONFIGURATIONS {
        serial rule_id PK
        varchar asset_type
        varchar metric_name
        varchar condition_type
        numeric threshold_value
        varchar alert_name UK
        varchar severity
        boolean is_enabled
    }
    
    STRAPPING_DATA {
        serial id PK
        varchar asset_id FK
        numeric level_mm
        numeric volume_litres
    }
    
    OPERATION_LOGS {
        serial log_id PK
        timestamp timestamp
        varchar user_name
        varchar event_type
        text description
        varchar related_asset_id FK
        jsonb details
    }
```

### Key Metrics Stored

#### Sensor Readings (sensor_readings)
| Metric | Unit | Source | Description |
|--------|------|--------|-------------|
| level_mm | mm | Tank sensor | Tank liquid level |
| temperature | °C | Tank sensor | Product temperature |
| pump_status | - | Pump sensor | 1=Running, 0=Stopped |
| motor_current | A | Pump sensor | Motor current draw |

#### Calculated Data (calculated_data)
| Metric | Unit | Description |
|--------|------|-------------|
| level_percentage | % | Tank fill percentage |
| volume_gov | Litres | Gross Observed Volume |
| volume_gsv | Litres | Gross Standard Volume @ 20°C |
| mass_kg | kg | Product mass |
| density_at_temp | kg/m³ | Temperature-corrected density |
| heat_content_kj | kJ | Thermal energy content |
| power_kw | kW | Instantaneous pump power |
| energy_kwh | kWh | Energy consumed per interval |
| operating_cost | GHS | Cost per interval |

---

## API Reference

### Endpoints Overview

```mermaid
flowchart LR
    subgraph Public["Public"]
        HEALTH["/health"]
    end
    
    subgraph Assets["Asset Management"]
        A1["GET /api/v1/assets"]
        A2["GET /api/v1/assets/{id}"]
        A3["GET /api/v1/assets/{id}/metrics/{metric}/history"]
    end
    
    subgraph Simulations["Simulations"]
        S1["POST /api/v1/simulations/tank-transfer"]
        S2["POST /api/v1/simulations/fire-consequence"]
        S3["POST /api/v1/simulate/refresh"]
    end
    
    subgraph Monitoring["Monitoring"]
        M1["GET /api/v1/alerts/active"]
        M2["GET /api/v1/logs"]
        M3["POST /api/v1/logs"]
        M4["GET /api/v1/pumps/costs"]
    end
```

### Authentication
All endpoints (except `/health`) require API key authentication via the `x-api-key` header.

```bash
curl -H "x-api-key: YOUR_API_KEY" http://localhost:5000/api/v1/assets
```

### Endpoint Details

#### GET /api/v1/pumps/costs
Returns pump operating costs with tariff breakdown.

**Query Parameters:**
- `start_time` (optional): ISO datetime, defaults to 24 hours ago
- `end_time` (optional): ISO datetime, defaults to now
- `pump_id` (optional): Filter by specific pump

**Response:**
```json
{
  "time_range": {
    "start": "2025-01-10T00:00:00+00:00",
    "end": "2025-01-11T00:00:00+00:00"
  },
  "tariff": {
    "rate_per_kwh": 2.21,
    "currency": "GHS",
    "description": "Ghana ECG Non-Residential (1000+ kWh band, incl. VAT)"
  },
  "summary": {
    "total_energy_kwh": 1547.32,
    "total_cost_ghs": 3419.58,
    "pump_count": 12
  },
  "pumps": [
    {
      "asset_id": "PUMP-001",
      "description": "Main Transfer Pump 1",
      "motor_power_kw": 55.0,
      "pump_house_id": "PH-01",
      "total_energy_kwh": 258.45,
      "total_cost_ghs": 571.17,
      "runtime_percentage": 45.2
    }
  ]
}
```

---

## Alerting System

### Alert Flow

```mermaid
stateDiagram-v2
    [*] --> Monitoring: Service Start
    Monitoring --> Evaluating: Every 20s
    Evaluating --> CheckCondition: For each asset
    
    CheckCondition --> CreateAlert: Condition Met
    CheckCondition --> ResolveAlert: Condition Cleared
    CheckCondition --> NoAction: No Change
    
    CreateAlert --> Active: New Alert
    ResolveAlert --> Resolved: Alert Cleared
    NoAction --> Monitoring
    
    Active --> Acknowledged: User Acknowledges
    Active --> Resolved: Auto-resolve
    Acknowledged --> Resolved: Condition Clears
    Resolved --> [*]
```

### Alert Configuration

```mermaid
flowchart TD
    subgraph Config["Alert Configuration"]
        RULE["Alert Rule"]
        TYPE["asset_type: StorageTank"]
        METRIC["metric_name: level_percentage"]
        COND["condition_type: >"]
        THRESH["threshold_value: 90"]
        SEV["severity: Critical"]
    end
    
    subgraph Evaluation["Runtime Evaluation"]
        READ["Read Current Value"]
        COMPARE["Compare: value > threshold"]
        TRIGGER["Trigger Alert"]
    end
    
    RULE --> TYPE
    RULE --> METRIC
    RULE --> COND
    RULE --> THRESH
    RULE --> SEV
    
    TYPE --> READ
    METRIC --> READ
    READ --> COMPARE
    COND --> COMPARE
    THRESH --> COMPARE
    COMPARE -->|True| TRIGGER
    SEV --> TRIGGER
```

### Example Alert Rules

| Rule | Asset Type | Metric | Condition | Threshold | Severity |
|------|-----------|--------|-----------|-----------|----------|
| High Level | StorageTank | level_percentage | > | 90% | Critical |
| Low Level | StorageTank | level_percentage | < | 10% | Critical |
| High Temp | StorageTank | temperature | > | 45°C | Warning |
| Pump Overload | Pump | power_kw | > | 70 kW | Warning |

---

## Deployment Architecture

```mermaid
flowchart TB
    subgraph Cloud["Cloud Infrastructure"]
        subgraph Railway["Railway.app"]
            API_SVC["API Service"]
            CALC_SVC["Calculation Service"]
            ALERT_SVC["Alerting Service"]
            DASH_SVC["Dashboard"]
        end
        
        subgraph Render["Render.com"]
            PG[("PostgreSQL")]
        end
        
        subgraph HiveMQ["HiveMQ Cloud"]
            MQTT[("MQTT Broker")]
        end
    end
    
    subgraph External["External APIs"]
        OW["OpenWeather API"]
    end
    
    API_SVC <--> PG
    CALC_SVC <--> PG
    ALERT_SVC <--> PG
    DASH_SVC --> API_SVC
    DASH_SVC --> OW
    
    CALC_SVC <--> MQTT
```

---

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEY` | - | API authentication key |
| `DATABASE_URL` | - | PostgreSQL connection string |
| `MQTT_BROKER_ADDRESS` | localhost | MQTT broker hostname |
| `MQTT_BROKER_PORT` | 1883 | MQTT broker port |
| `MQTT_USE_TLS` | false | Enable TLS for MQTT |
| `ELECTRICITY_RATE_PER_KWH` | 2.21 | Ghana ECG tariff rate |
| `ENERGY_CHARGE_PER_KWH` | 1.59 | Base energy charge |
| `SERVICE_CHARGE_PER_KWH` | 0.05 | Service charge |
| `NHIL_GETFUND_PER_KWH` | 0.1243 | NHIL + GETFund levy |
| `VAT_RATE` | 0.15 | VAT rate (15%) |
| `SIMULATION_INTERVAL_SECONDS` | 10 | Sensor simulation interval |
| `STANDARD_REFERENCE_TEMPERATURE_CELSIUS` | 20.0 | Reference temp for GSV |

---

*Documentation generated for Fuel Depot Digital Twin v1.0*
*Last updated: January 2026*
