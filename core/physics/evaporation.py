# File: fuel_depot_digital_twin/core/physics/evaporation.py
"""
Evaporation Loss Calculator for Petroleum Storage Tanks

Implements evaporation loss estimation based on API MPMS Chapter 19:
- Standing losses: Evaporation during storage (breathing losses)
- Working losses: Evaporation during filling/emptying operations

These calculations help with:
- Inventory reconciliation
- Environmental compliance
- Loss prevention planning

References:
- API MPMS Chapter 19.1 (Evaporative Loss from Fixed-Roof Tanks)
- API MPMS Chapter 19.2 (Evaporative Loss from Floating-Roof Tanks)
- EPA AP-42 Chapter 7 (Storage of Organic Liquids)
"""

import logging
import math
from dataclasses import dataclass
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


# --- Vapor Pressure Data (Reid Vapor Pressure at 37.8°C / 100°F in kPa) ---
# True Vapor Pressure (TVP) varies with temperature
VAPOR_PRESSURE_DATA = {
    "PMS": {  # Gasoline
        "rvp_kpa": 62.0,  # Reid VP at 37.8°C
        "tvp_coeff_a": 6.5,  # Antoine equation coefficient
        "tvp_coeff_b": 1200.0,
        "molecular_weight": 92.0,  # Average
    },
    "AGO": {  # Diesel
        "rvp_kpa": 0.5,
        "tvp_coeff_a": 6.0,
        "tvp_coeff_b": 1400.0,
        "molecular_weight": 200.0,
    },
    "DPK": {  # Kerosene
        "rvp_kpa": 1.5,
        "tvp_coeff_a": 6.2,
        "tvp_coeff_b": 1350.0,
        "molecular_weight": 170.0,
    },
    "LPG": {  # LPG - stored under pressure, minimal losses
        "rvp_kpa": 1200.0,
        "tvp_coeff_a": 5.5,
        "tvp_coeff_b": 800.0,
        "molecular_weight": 50.0,
    },
    "RFO": {  # Residual Fuel Oil - very low volatility
        "rvp_kpa": 0.01,
        "tvp_coeff_a": 7.0,
        "tvp_coeff_b": 1800.0,
        "molecular_weight": 400.0,
    },
    "DEFAULT": {
        "rvp_kpa": 10.0,
        "tvp_coeff_a": 6.3,
        "tvp_coeff_b": 1300.0,
        "molecular_weight": 150.0,
    },
}

# Tank paint solar absorptance (α) values
PAINT_ABSORPTANCE = {
    "white": 0.17,
    "aluminum": 0.39,
    "light_gray": 0.54,
    "medium_gray": 0.68,
    "dark_gray": 0.89,
    "black": 0.97,
    "DEFAULT": 0.54,  # Light gray (common)
}


@dataclass
class EvaporationLoss:
    """Result of evaporation loss calculation."""
    loss_kg: float
    loss_litres: float
    loss_type: str  # "standing", "working", "total"
    period_description: str
    product_type: Optional[str] = None
    tank_id: Optional[str] = None
    temperature_avg_c: Optional[float] = None
    details: Optional[Dict] = None
    
    def to_dict(self) -> dict:
        return {
            "loss_kg": round(self.loss_kg, 2),
            "loss_litres": round(self.loss_litres, 2),
            "loss_type": self.loss_type,
            "period_description": self.period_description,
            "product_type": self.product_type,
            "tank_id": self.tank_id,
            "temperature_avg_c": round(self.temperature_avg_c, 1) if self.temperature_avg_c else None,
            "details": self.details,
        }


@dataclass 
class AnnualLossReport:
    """Annual evaporation loss summary."""
    total_loss_kg: float
    total_loss_litres: float
    standing_loss_kg: float
    working_loss_kg: float
    monthly_breakdown: List[Dict]
    economic_loss_value: Optional[float] = None
    currency: str = "GHS"
    
    def to_dict(self) -> dict:
        return {
            "total_loss_kg": round(self.total_loss_kg, 0),
            "total_loss_litres": round(self.total_loss_litres, 0),
            "total_loss_tonnes": round(self.total_loss_kg / 1000, 2),
            "standing_loss_kg": round(self.standing_loss_kg, 0),
            "working_loss_kg": round(self.working_loss_kg, 0),
            "standing_loss_percent": round(self.standing_loss_kg / max(self.total_loss_kg, 1) * 100, 1),
            "working_loss_percent": round(self.working_loss_kg / max(self.total_loss_kg, 1) * 100, 1),
            "economic_loss_value": round(self.economic_loss_value, 2) if self.economic_loss_value else None,
            "currency": self.currency,
            "monthly_breakdown": self.monthly_breakdown,
        }


class EvaporationCalculator:
    """
    Calculator for evaporation losses from petroleum storage tanks.
    
    Implements simplified API MPMS Chapter 19 methods for:
    - Fixed-roof tanks (breathing and working losses)
    - Floating-roof tanks (rim seal and withdrawal losses)
    
    Usage:
        calc = EvaporationCalculator()
        standing = calc.estimate_standing_losses(
            tank_diameter_m=20.0,
            tank_height_m=15.0,
            product_type="PMS",
            average_temp_c=30.0,
            temp_range_c=15.0
        )
    """
    
    # Atmospheric pressure (kPa)
    ATMOSPHERIC_PRESSURE_KPA = 101.325
    
    # Ideal gas constant (kPa·L / mol·K)
    R_CONSTANT = 8.314
    
    def __init__(self):
        logger.info("EvaporationCalculator initialized")
    
    def get_vapor_properties(self, product_type: Optional[str] = None) -> dict:
        """Get vapor pressure properties for a product type."""
        if product_type and product_type.upper() in VAPOR_PRESSURE_DATA:
            return VAPOR_PRESSURE_DATA[product_type.upper()]
        return VAPOR_PRESSURE_DATA["DEFAULT"]
    
    def estimate_true_vapor_pressure(
        self,
        temperature_c: float,
        product_type: Optional[str] = None,
        rvp_kpa: Optional[float] = None
    ) -> float:
        """
        Estimate true vapor pressure at a given temperature.
        
        Uses a simplified Antoine-like equation based on RVP.
        
        Args:
            temperature_c: Temperature in °C
            product_type: Product type for vapor data lookup
            rvp_kpa: Override Reid Vapor Pressure
            
        Returns:
            True vapor pressure in kPa
        """
        props = self.get_vapor_properties(product_type)
        
        if rvp_kpa is None:
            rvp_kpa = props["rvp_kpa"]
        
        # Simplified temperature correction
        # TVP increases with temperature approximately exponentially
        # TVP ≈ RVP × exp(0.02 × (T - 37.8))
        temp_factor = math.exp(0.02 * (temperature_c - 37.8))
        tvp = rvp_kpa * temp_factor
        
        logger.debug(f"True vapor pressure at {temperature_c}°C: {tvp:.3f} kPa (RVP={rvp_kpa})")
        return tvp
    
    def estimate_standing_losses(
        self,
        tank_diameter_m: float,
        tank_height_m: Optional[float] = None,
        product_type: Optional[str] = None,
        average_temp_c: float = 25.0,
        temp_range_c: float = 10.0,
        days: int = 1,
        paint_color: str = "light_gray",
        solar_insulation_factor: float = 1.0,
        liquid_height_m: Optional[float] = None,
        capacity_litres: Optional[float] = None
    ) -> EvaporationLoss:
        """
        Estimate standing (breathing) losses from a fixed-roof tank.
        
        Standing losses occur due to:
        - Daily temperature cycling (breathing)
        - Vapor space saturation changes
        
        Simplified API 19.1 method:
        Ls = 365 × Vv × Wv × Ke × Ks × Kn × Kp
        
        Args:
            tank_diameter_m: Tank diameter in meters
            tank_height_m: Tank height in meters
            product_type: Product type (PMS, AGO, etc.)
            average_temp_c: Average ambient temperature
            temp_range_c: Daily temperature range (max - min)
            days: Number of days
            paint_color: Tank paint color
            solar_insulation_factor: Factor for solar heating (0-1)
            liquid_height_m: Current liquid height
            capacity_litres: Tank capacity (alternative to height)
            
        Returns:
            EvaporationLoss with standing loss values
        """
        props = self.get_vapor_properties(product_type)
        
        # Estimate tank height if not provided
        if tank_height_m is None:
            if capacity_litres:
                # V = π × r² × h → h = V / (π × r²)
                radius = tank_diameter_m / 2
                tank_height_m = (capacity_litres / 1000) / (math.pi * radius ** 2)
            else:
                # Assume typical height:diameter ratio of 0.75
                tank_height_m = tank_diameter_m * 0.75
        
        # Estimate liquid height if not provided (assume 50% full)
        if liquid_height_m is None:
            liquid_height_m = tank_height_m * 0.5
        
        # Vapor space height
        vapor_height_m = max(tank_height_m - liquid_height_m, 0.1)
        
        # Tank diameter in feet (API formula uses imperial units internally)
        diameter_ft = tank_diameter_m * 3.281
        vapor_height_ft = vapor_height_m * 3.281
        
        # Vapor space volume (cubic feet)
        vapor_volume_ft3 = math.pi * (diameter_ft / 2) ** 2 * vapor_height_ft
        
        # True vapor pressure at average temperature
        tvp = self.estimate_true_vapor_pressure(average_temp_c, product_type)
        
        # Vapor pressure function (Kp)
        # Kp = P / (P_atm - P)^0.5 where P is vapor pressure
        p_ratio = tvp / self.ATMOSPHERIC_PRESSURE_KPA
        if p_ratio >= 0.95:
            kp = 1.0  # Limit for very high vapor pressures
        else:
            kp = p_ratio / math.sqrt(1 - p_ratio)
        
        # Temperature range factor (Ke)
        # Higher daily temperature swings cause more breathing
        ke = 0.06 + 0.02 * temp_range_c
        
        # Solar absorptance factor (Ks)
        absorptance = PAINT_ABSORPTANCE.get(paint_color.lower(), PAINT_ABSORPTANCE["DEFAULT"])
        ks = absorptance * solar_insulation_factor
        
        # Simplified standing loss formula (lb/day)
        # Based on AP-42 / API 19.1 simplified method
        stock_vapor_density = props["molecular_weight"] * tvp / (self.R_CONSTANT * (average_temp_c + 273.15))
        
        # Breathing loss (kg/day)
        # L = Vv × ρv × Ke × Ks × Kp
        loss_kg_per_day = (vapor_volume_ft3 * 0.0283) * stock_vapor_density * ke * ks * kp
        
        # Scale by number of days
        total_loss_kg = loss_kg_per_day * days
        
        # Convert to litres using liquid density
        density_kg_m3 = props.get("molecular_weight", 100) * 5  # Approximate liquid density
        if product_type and product_type.upper() in ["PMS"]:
            density_kg_m3 = 740
        elif product_type and product_type.upper() in ["AGO"]:
            density_kg_m3 = 850
        
        loss_litres = (total_loss_kg / density_kg_m3) * 1000
        
        logger.info(
            f"Standing loss for {tank_diameter_m}m tank: {total_loss_kg:.2f} kg "
            f"({loss_litres:.2f} L) over {days} days"
        )
        
        return EvaporationLoss(
            loss_kg=total_loss_kg,
            loss_litres=loss_litres,
            loss_type="standing",
            period_description=f"{days} day(s)",
            product_type=product_type,
            temperature_avg_c=average_temp_c,
            details={
                "vapor_volume_m3": round(vapor_volume_ft3 * 0.0283, 2),
                "true_vapor_pressure_kpa": round(tvp, 3),
                "temperature_range_c": temp_range_c,
                "paint_absorptance": absorptance,
                "loss_rate_kg_day": round(loss_kg_per_day, 3),
            }
        )
    
    def estimate_working_losses(
        self,
        volume_throughput_litres: float,
        product_type: Optional[str] = None,
        average_temp_c: float = 25.0,
        turnover_factor: float = 1.0
    ) -> EvaporationLoss:
        """
        Estimate working losses during tank filling operations.
        
        Working losses occur when:
        - Filling displaces vapor-saturated air
        - Product enters the tank and releases dissolved vapors
        
        Simplified formula:
        Lw = throughput × working loss factor × saturation factor
        
        Args:
            volume_throughput_litres: Volume filled into tank
            product_type: Product type
            average_temp_c: Average temperature during filling
            turnover_factor: Number of complete tank turnovers
            
        Returns:
            EvaporationLoss with working loss values
        """
        props = self.get_vapor_properties(product_type)
        
        # True vapor pressure
        tvp = self.estimate_true_vapor_pressure(average_temp_c, product_type)
        
        # Working loss factor (approximate)
        # Higher vapor pressure = higher working losses
        # Typical range: 0.0001 to 0.01 (0.01% to 1%)
        vapor_pressure_ratio = tvp / self.ATMOSPHERIC_PRESSURE_KPA
        working_loss_factor = vapor_pressure_ratio * 0.01  # 1% at atmospheric VP
        
        # Saturation factor (1.0 = fully saturated vapor space)
        saturation_factor = 0.5 + 0.5 * min(turnover_factor, 1.0)
        
        # Working loss (litres of liquid equivalent)
        loss_litres = volume_throughput_litres * working_loss_factor * saturation_factor
        
        # Convert to mass
        if product_type and product_type.upper() == "PMS":
            density_kg_m3 = 740
        elif product_type and product_type.upper() == "AGO":
            density_kg_m3 = 850
        else:
            density_kg_m3 = 820
        
        loss_kg = (loss_litres / 1000) * density_kg_m3
        
        logger.info(
            f"Working loss for {volume_throughput_litres:,.0f}L throughput: "
            f"{loss_kg:.2f} kg ({loss_litres:.2f} L)"
        )
        
        return EvaporationLoss(
            loss_kg=loss_kg,
            loss_litres=loss_litres,
            loss_type="working",
            period_description=f"Throughput of {volume_throughput_litres:,.0f} litres",
            product_type=product_type,
            temperature_avg_c=average_temp_c,
            details={
                "throughput_litres": round(volume_throughput_litres, 0),
                "working_loss_factor": round(working_loss_factor, 6),
                "saturation_factor": round(saturation_factor, 3),
                "true_vapor_pressure_kpa": round(tvp, 3),
            }
        )
    
    def calculate_annual_loss(
        self,
        tank_diameter_m: float,
        tank_height_m: float,
        product_type: str,
        annual_throughput_litres: float,
        monthly_avg_temps: Optional[List[float]] = None,
        monthly_temp_ranges: Optional[List[float]] = None,
        avg_liquid_level_percent: float = 50.0,
        paint_color: str = "light_gray",
        product_price_per_litre: float = 8.0
    ) -> AnnualLossReport:
        """
        Calculate comprehensive annual evaporation loss for a tank.
        
        Args:
            tank_diameter_m: Tank diameter
            tank_height_m: Tank height
            product_type: Product type
            annual_throughput_litres: Total annual throughput
            monthly_avg_temps: List of 12 monthly average temperatures
            monthly_temp_ranges: List of 12 monthly temperature ranges
            avg_liquid_level_percent: Average fill level
            paint_color: Tank exterior paint color
            product_price_per_litre: Product value per litre
            
        Returns:
            AnnualLossReport with comprehensive breakdown
        """
        # Default tropical climate temperatures if not provided
        if monthly_avg_temps is None:
            monthly_avg_temps = [27, 28, 29, 29, 28, 26, 25, 24, 25, 26, 27, 27]
        
        if monthly_temp_ranges is None:
            monthly_temp_ranges = [12, 12, 11, 10, 9, 8, 7, 7, 8, 9, 10, 11]
        
        # Days per month
        days_per_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        
        monthly_breakdown = []
        total_standing = 0.0
        total_working = 0.0
        
        avg_liquid_height = tank_height_m * (avg_liquid_level_percent / 100)
        monthly_throughput = annual_throughput_litres / 12
        
        for month_idx in range(12):
            month_name = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                         "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][month_idx]
            
            # Calculate standing loss for month
            standing = self.estimate_standing_losses(
                tank_diameter_m=tank_diameter_m,
                tank_height_m=tank_height_m,
                product_type=product_type,
                average_temp_c=monthly_avg_temps[month_idx],
                temp_range_c=monthly_temp_ranges[month_idx],
                days=days_per_month[month_idx],
                paint_color=paint_color,
                liquid_height_m=avg_liquid_height
            )
            
            # Calculate working loss for month
            working = self.estimate_working_losses(
                volume_throughput_litres=monthly_throughput,
                product_type=product_type,
                average_temp_c=monthly_avg_temps[month_idx]
            )
            
            monthly_total = standing.loss_kg + working.loss_kg
            total_standing += standing.loss_kg
            total_working += working.loss_kg
            
            monthly_breakdown.append({
                "month": month_name,
                "standing_loss_kg": round(standing.loss_kg, 2),
                "working_loss_kg": round(working.loss_kg, 2),
                "total_loss_kg": round(monthly_total, 2),
                "avg_temp_c": monthly_avg_temps[month_idx],
            })
        
        total_loss_kg = total_standing + total_working
        
        # Estimate litres (use approximate density)
        if product_type.upper() == "PMS":
            density = 740
        elif product_type.upper() == "AGO":
            density = 850
        else:
            density = 820
        
        total_loss_litres = (total_loss_kg / density) * 1000
        economic_loss = total_loss_litres * product_price_per_litre
        
        logger.info(
            f"Annual evaporation loss for {tank_diameter_m}m {product_type} tank: "
            f"{total_loss_kg:,.0f} kg ({total_loss_litres:,.0f} L), "
            f"Economic value: {economic_loss:,.0f} GHS"
        )
        
        return AnnualLossReport(
            total_loss_kg=total_loss_kg,
            total_loss_litres=total_loss_litres,
            standing_loss_kg=total_standing,
            working_loss_kg=total_working,
            monthly_breakdown=monthly_breakdown,
            economic_loss_value=economic_loss,
            currency="GHS"
        )
