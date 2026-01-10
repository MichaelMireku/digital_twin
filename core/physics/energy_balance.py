# File: fuel_depot_digital_twin/core/physics/energy_balance.py
"""
Energy Balance Calculator for Petroleum Storage Tanks

Implements thermal energy calculations for tank operations:
- Heat content calculation (thermal energy stored in product)
- Ambient heat transfer (heating/cooling from environment)
- Temperature prediction over time
- Pump energy consumption

References:
- API MPMS Chapter 11 (Temperature and Pressure Effects)
- Engineering thermodynamics principles
"""

import logging
import math
from dataclasses import dataclass
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


# --- Physical Constants ---
GRAVITY_M_S2 = 9.81  # Gravitational acceleration
WATER_DENSITY_KG_M3 = 1000.0  # Reference density


@dataclass
class HeatContent:
    """Result of heat content calculation."""
    energy_kj: float
    energy_kwh: float
    mass_kg: float
    temperature_c: float
    specific_heat_kj_kg_c: float
    reference_temp_c: float
    
    def to_dict(self) -> dict:
        return {
            "energy_kj": round(self.energy_kj, 2),
            "energy_kwh": round(self.energy_kwh, 4),
            "energy_mj": round(self.energy_kj / 1000, 2),
            "mass_kg": round(self.mass_kg, 2),
            "temperature_c": round(self.temperature_c, 2),
            "specific_heat_kj_kg_c": round(self.specific_heat_kj_kg_c, 3),
            "reference_temp_c": round(self.reference_temp_c, 2),
        }


@dataclass
class HeatTransferRate:
    """Result of heat transfer rate calculation."""
    heat_rate_kw: float
    heat_rate_kj_hr: float
    temperature_difference_c: float
    heat_transfer_coeff_w_m2_k: float
    surface_area_m2: float
    
    def to_dict(self) -> dict:
        return {
            "heat_rate_kw": round(self.heat_rate_kw, 4),
            "heat_rate_kj_hr": round(self.heat_rate_kj_hr, 2),
            "temperature_difference_c": round(self.temperature_difference_c, 2),
            "heat_transfer_coeff_w_m2_k": round(self.heat_transfer_coeff_w_m2_k, 2),
            "surface_area_m2": round(self.surface_area_m2, 2),
        }


@dataclass
class TemperaturePrediction:
    """Result of temperature change prediction."""
    initial_temp_c: float
    predicted_temp_c: float
    delta_temp_c: float
    ambient_temp_c: float
    duration_hours: float
    heat_transferred_kj: float
    
    def to_dict(self) -> dict:
        return {
            "initial_temp_c": round(self.initial_temp_c, 2),
            "predicted_temp_c": round(self.predicted_temp_c, 2),
            "delta_temp_c": round(self.delta_temp_c, 2),
            "ambient_temp_c": round(self.ambient_temp_c, 2),
            "duration_hours": round(self.duration_hours, 2),
            "heat_transferred_kj": round(self.heat_transferred_kj, 2),
        }


@dataclass
class PumpEnergy:
    """Result of pump energy consumption calculation."""
    energy_kwh: float
    power_kw: float
    duration_hours: float
    flow_rate_m3_hr: float
    head_m: float
    efficiency: float
    
    def to_dict(self) -> dict:
        return {
            "energy_kwh": round(self.energy_kwh, 4),
            "power_kw": round(self.power_kw, 4),
            "duration_hours": round(self.duration_hours, 2),
            "flow_rate_m3_hr": round(self.flow_rate_m3_hr, 2),
            "head_m": round(self.head_m, 2),
            "efficiency_percent": round(self.efficiency * 100, 1),
        }


class EnergyBalanceCalculator:
    """
    Calculator for energy balance operations in petroleum storage.
    
    Provides calculations for:
    - Thermal energy content in tanks (Q = m × Cp × ΔT)
    - Heat transfer rates between tank and environment
    - Temperature change predictions
    - Pump energy consumption
    
    Usage:
        calc = EnergyBalanceCalculator()
        heat = calc.calculate_tank_heat_content(
            mass_kg=421250,
            temperature_c=28.5,
            specific_heat_kj_kg_c=2.0
        )
    """
    
    # Default specific heat values for petroleum products (kJ/kg·°C)
    SPECIFIC_HEAT_DEFAULTS = {
        "PMS": 2.22,    # Gasoline
        "AGO": 2.05,    # Diesel
        "DPK": 2.10,    # Kerosene
        "LPG": 2.50,    # LPG
        "RFO": 1.80,    # Residual Fuel Oil
        "DEFAULT": 2.00,
    }
    
    # Typical heat transfer coefficients (W/m²·K)
    HEAT_TRANSFER_COEFFICIENTS = {
        "tank_wall_still_air": 5.0,      # Tank wall to still ambient air
        "tank_wall_wind": 15.0,          # Tank wall with wind
        "tank_roof_still_air": 8.0,      # Tank roof to still air
        "tank_roof_wind": 20.0,          # Tank roof with wind
        "insulated_tank": 0.5,           # Insulated tank wall
        "ground_contact": 2.0,           # Tank bottom to ground
    }
    
    def __init__(self, reference_temp_c: float = 0.0):
        """
        Initialize the energy balance calculator.
        
        Args:
            reference_temp_c: Reference temperature for heat content calculations (default 0°C)
        """
        self.reference_temp_c = reference_temp_c
        logger.info(f"EnergyBalanceCalculator initialized with reference temp: {reference_temp_c}°C")
    
    def get_specific_heat(self, product_type: Optional[str] = None) -> float:
        """Get specific heat for a product type."""
        if product_type and product_type.upper() in self.SPECIFIC_HEAT_DEFAULTS:
            return self.SPECIFIC_HEAT_DEFAULTS[product_type.upper()]
        return self.SPECIFIC_HEAT_DEFAULTS["DEFAULT"]
    
    def calculate_tank_heat_content(
        self,
        mass_kg: float,
        temperature_c: float,
        specific_heat_kj_kg_c: Optional[float] = None,
        product_type: Optional[str] = None
    ) -> HeatContent:
        """
        Calculate the thermal energy content of product in a tank.
        
        Formula: Q = m × Cp × (T - T_ref)
        
        Args:
            mass_kg: Mass of product in kilograms
            temperature_c: Current product temperature in °C
            specific_heat_kj_kg_c: Specific heat capacity (optional)
            product_type: Product type for automatic specific heat lookup
            
        Returns:
            HeatContent with energy values
        """
        if specific_heat_kj_kg_c is None:
            specific_heat_kj_kg_c = self.get_specific_heat(product_type)
        
        # Q = m × Cp × ΔT
        delta_t = temperature_c - self.reference_temp_c
        energy_kj = mass_kg * specific_heat_kj_kg_c * delta_t
        
        # Convert to kWh (1 kWh = 3600 kJ)
        energy_kwh = energy_kj / 3600
        
        logger.info(
            f"Heat content: {mass_kg:,.0f} kg × {specific_heat_kj_kg_c} kJ/kg·°C × "
            f"{delta_t:.1f}°C = {energy_kj:,.0f} kJ ({energy_kwh:,.2f} kWh)"
        )
        
        return HeatContent(
            energy_kj=energy_kj,
            energy_kwh=energy_kwh,
            mass_kg=mass_kg,
            temperature_c=temperature_c,
            specific_heat_kj_kg_c=specific_heat_kj_kg_c,
            reference_temp_c=self.reference_temp_c
        )
    
    def estimate_tank_surface_area(
        self,
        diameter_m: Optional[float] = None,
        height_m: Optional[float] = None,
        capacity_litres: Optional[float] = None
    ) -> float:
        """
        Estimate tank surface area for heat transfer calculations.
        
        If dimensions not provided, estimates from capacity assuming
        height:diameter ratio of 1.5:1.
        
        Args:
            diameter_m: Tank diameter in meters
            height_m: Tank height in meters
            capacity_litres: Tank capacity in litres
            
        Returns:
            Estimated surface area in m²
        """
        if diameter_m and height_m:
            radius = diameter_m / 2
            # Cylinder: 2πrh (wall) + 2πr² (top + bottom)
            wall_area = 2 * math.pi * radius * height_m
            ends_area = 2 * math.pi * radius ** 2
            return wall_area + ends_area
        
        if capacity_litres:
            # Estimate dimensions from capacity
            # V = πr²h, assuming h = 1.5 × d = 3r
            # V = π × r² × 3r = 3πr³
            # r = (V / 3π)^(1/3)
            volume_m3 = capacity_litres / 1000
            radius = (volume_m3 / (3 * math.pi)) ** (1/3)
            height = 3 * radius
            diameter = 2 * radius
            
            wall_area = 2 * math.pi * radius * height
            ends_area = 2 * math.pi * radius ** 2
            
            logger.debug(
                f"Estimated tank dimensions: D={diameter:.1f}m, H={height:.1f}m, "
                f"Surface area={wall_area + ends_area:.1f}m²"
            )
            return wall_area + ends_area
        
        logger.warning("Cannot estimate tank surface area: no dimensions provided")
        return 0.0
    
    def calculate_heat_transfer_rate(
        self,
        tank_temp_c: float,
        ambient_temp_c: float,
        surface_area_m2: float,
        heat_transfer_coeff: Optional[float] = None,
        is_windy: bool = False,
        is_insulated: bool = False
    ) -> HeatTransferRate:
        """
        Calculate the rate of heat transfer between tank and environment.
        
        Formula: Q̇ = U × A × ΔT (simplified convection model)
        
        Args:
            tank_temp_c: Product temperature in tank (°C)
            ambient_temp_c: Ambient air temperature (°C)
            surface_area_m2: Tank surface area (m²)
            heat_transfer_coeff: Override coefficient (W/m²·K)
            is_windy: Whether there is significant wind
            is_insulated: Whether the tank is insulated
            
        Returns:
            HeatTransferRate with rate values
        """
        # Select heat transfer coefficient
        if heat_transfer_coeff is None:
            if is_insulated:
                heat_transfer_coeff = self.HEAT_TRANSFER_COEFFICIENTS["insulated_tank"]
            elif is_windy:
                heat_transfer_coeff = self.HEAT_TRANSFER_COEFFICIENTS["tank_wall_wind"]
            else:
                heat_transfer_coeff = self.HEAT_TRANSFER_COEFFICIENTS["tank_wall_still_air"]
        
        # Temperature difference
        delta_t = tank_temp_c - ambient_temp_c
        
        # Heat transfer rate: Q̇ = U × A × ΔT (W)
        # Positive = heat loss (tank warmer than ambient)
        # Negative = heat gain (tank cooler than ambient)
        heat_rate_w = heat_transfer_coeff * surface_area_m2 * delta_t
        heat_rate_kw = heat_rate_w / 1000
        heat_rate_kj_hr = heat_rate_kw * 3600
        
        logger.debug(
            f"Heat transfer: U={heat_transfer_coeff} W/m²·K × {surface_area_m2:.1f}m² × "
            f"{delta_t:.1f}°C = {heat_rate_kw:.2f} kW"
        )
        
        return HeatTransferRate(
            heat_rate_kw=heat_rate_kw,
            heat_rate_kj_hr=heat_rate_kj_hr,
            temperature_difference_c=delta_t,
            heat_transfer_coeff_w_m2_k=heat_transfer_coeff,
            surface_area_m2=surface_area_m2
        )
    
    def predict_temperature_change(
        self,
        mass_kg: float,
        initial_temp_c: float,
        ambient_temp_c: float,
        duration_hours: float,
        surface_area_m2: float,
        specific_heat_kj_kg_c: Optional[float] = None,
        product_type: Optional[str] = None,
        heat_transfer_coeff: Optional[float] = None
    ) -> TemperaturePrediction:
        """
        Predict the temperature change of tank contents over time.
        
        Uses Newton's law of cooling/heating for approximation.
        
        Formula: T(t) = T_ambient + (T_initial - T_ambient) × e^(-t/τ)
        where τ = m × Cp / (U × A)
        
        Args:
            mass_kg: Mass of product in tank
            initial_temp_c: Initial product temperature
            ambient_temp_c: Ambient temperature
            duration_hours: Time period for prediction
            surface_area_m2: Tank surface area
            specific_heat_kj_kg_c: Specific heat (optional)
            product_type: Product type for lookups
            heat_transfer_coeff: Heat transfer coefficient (W/m²·K)
            
        Returns:
            TemperaturePrediction with predicted values
        """
        if specific_heat_kj_kg_c is None:
            specific_heat_kj_kg_c = self.get_specific_heat(product_type)
        
        if heat_transfer_coeff is None:
            heat_transfer_coeff = self.HEAT_TRANSFER_COEFFICIENTS["tank_wall_still_air"]
        
        # Time constant τ = m × Cp / (U × A)
        # Cp in kJ/kg·K, U in W/m²·K = kJ/s/m²·K
        # τ in seconds = (kg × kJ/kg·K) / (kJ/s/m²·K × m²) = kg·K·s·m²·K / (m²·kJ) = s
        # Need to convert Cp from kJ to J (×1000) for consistent units
        
        thermal_mass = mass_kg * specific_heat_kj_kg_c * 1000  # J/K
        heat_transfer_ua = heat_transfer_coeff * surface_area_m2  # W/K = J/s·K
        
        if heat_transfer_ua <= 0:
            logger.warning("Heat transfer coefficient or area is zero, no temperature change predicted")
            return TemperaturePrediction(
                initial_temp_c=initial_temp_c,
                predicted_temp_c=initial_temp_c,
                delta_temp_c=0.0,
                ambient_temp_c=ambient_temp_c,
                duration_hours=duration_hours,
                heat_transferred_kj=0.0
            )
        
        time_constant_s = thermal_mass / heat_transfer_ua  # seconds
        time_constant_hr = time_constant_s / 3600
        
        # Newton's law: T(t) = T_amb + (T_0 - T_amb) × e^(-t/τ)
        delta_t_initial = initial_temp_c - ambient_temp_c
        t_seconds = duration_hours * 3600
        
        decay_factor = math.exp(-t_seconds / time_constant_s)
        predicted_temp = ambient_temp_c + delta_t_initial * decay_factor
        
        delta_temp = predicted_temp - initial_temp_c
        
        # Heat transferred: Q = m × Cp × ΔT
        heat_transferred_kj = mass_kg * specific_heat_kj_kg_c * abs(delta_temp)
        
        logger.info(
            f"Temperature prediction: {initial_temp_c:.1f}°C → {predicted_temp:.1f}°C "
            f"over {duration_hours:.1f}hr (τ={time_constant_hr:.1f}hr, "
            f"Q={heat_transferred_kj:,.0f} kJ)"
        )
        
        return TemperaturePrediction(
            initial_temp_c=initial_temp_c,
            predicted_temp_c=predicted_temp,
            delta_temp_c=delta_temp,
            ambient_temp_c=ambient_temp_c,
            duration_hours=duration_hours,
            heat_transferred_kj=heat_transferred_kj
        )
    
    def calculate_pump_energy(
        self,
        flow_rate_lpm: float,
        head_m: float,
        duration_hours: float,
        efficiency: float = 0.75,
        density_kg_m3: float = 850.0
    ) -> PumpEnergy:
        """
        Calculate the energy consumption of a pump.
        
        Formula: P = (ρ × g × Q × H) / η
        
        Where:
            P = Power (W)
            ρ = Fluid density (kg/m³)
            g = Gravitational acceleration (9.81 m/s²)
            Q = Flow rate (m³/s)
            H = Total head (m)
            η = Pump efficiency (0-1)
        
        Args:
            flow_rate_lpm: Flow rate in litres per minute
            head_m: Total dynamic head in meters
            duration_hours: Operating duration in hours
            efficiency: Pump efficiency (default 0.75 = 75%)
            density_kg_m3: Fluid density (default 850 kg/m³ for diesel)
            
        Returns:
            PumpEnergy with consumption values
        """
        # Convert flow rate: LPM → m³/s
        flow_rate_m3_s = flow_rate_lpm / (1000 * 60)
        flow_rate_m3_hr = flow_rate_lpm * 60 / 1000
        
        # Hydraulic power: P_hydraulic = ρ × g × Q × H
        hydraulic_power_w = density_kg_m3 * GRAVITY_M_S2 * flow_rate_m3_s * head_m
        
        # Electrical power: P_electrical = P_hydraulic / η
        electrical_power_w = hydraulic_power_w / efficiency
        electrical_power_kw = electrical_power_w / 1000
        
        # Energy: E = P × t
        energy_kwh = electrical_power_kw * duration_hours
        
        logger.info(
            f"Pump energy: {flow_rate_lpm:.0f} LPM × {head_m:.1f}m head × "
            f"{duration_hours:.1f}hr @ {efficiency*100:.0f}% eff = "
            f"{electrical_power_kw:.2f}kW, {energy_kwh:.2f}kWh"
        )
        
        return PumpEnergy(
            energy_kwh=energy_kwh,
            power_kw=electrical_power_kw,
            duration_hours=duration_hours,
            flow_rate_m3_hr=flow_rate_m3_hr,
            head_m=head_m,
            efficiency=efficiency
        )
    
    def estimate_daily_electricity_cost(
        self,
        pumps_energy_kwh: float,
        electricity_rate_per_kwh: float = 0.15,
        demand_charge_per_kw: float = 0.0,
        peak_power_kw: float = 0.0
    ) -> Dict[str, float]:
        """
        Estimate daily electricity cost for pump operations.
        
        Args:
            pumps_energy_kwh: Total daily energy consumption
            electricity_rate_per_kwh: Cost per kWh
            demand_charge_per_kw: Monthly demand charge (allocated daily)
            peak_power_kw: Peak power demand
            
        Returns:
            Dictionary with cost breakdown
        """
        energy_cost = pumps_energy_kwh * electricity_rate_per_kwh
        demand_cost = (demand_charge_per_kw * peak_power_kw) / 30  # Daily allocation
        total_cost = energy_cost + demand_cost
        
        return {
            "energy_kwh": round(pumps_energy_kwh, 2),
            "energy_cost": round(energy_cost, 2),
            "demand_cost": round(demand_cost, 2),
            "total_daily_cost": round(total_cost, 2),
            "currency": "USD"  # US Dollars
        }
