# File: fuel_depot_digital_twin/core/physics/mass_balance.py
"""
Mass Balance Calculator for Petroleum Storage Tanks

Implements mass conservation principles for accurate product tracking:
- Volume-to-mass conversion with temperature-corrected density
- Mass reconciliation for tank transfers
- Loss/gain detection

References:
- API MPMS Chapter 11.1 (Volume Correction)
- ASTM D1250 (Petroleum Measurement Tables)
"""

import logging
import math
from dataclasses import dataclass
from typing import Optional
from decimal import Decimal, getcontext

# Set precision for calculations
getcontext().prec = 28

logger = logging.getLogger(__name__)


# --- Product Properties Database ---
# Thermal expansion coefficients (β) per °C at 20°C reference
# These are approximate values for common petroleum products
PRODUCT_PROPERTIES = {
    "PMS": {  # Premium Motor Spirit (Gasoline)
        "thermal_expansion_coeff": 0.00120,  # per °C
        "specific_heat_kj_kg_c": 2.22,
        "vapor_pressure_kpa_25c": 55.0,
        "typical_density_20c": 740.0,  # kg/m³
    },
    "AGO": {  # Automotive Gas Oil (Diesel)
        "thermal_expansion_coeff": 0.00083,
        "specific_heat_kj_kg_c": 2.05,
        "vapor_pressure_kpa_25c": 0.5,
        "typical_density_20c": 850.0,
    },
    "DPK": {  # Dual Purpose Kerosene
        "thermal_expansion_coeff": 0.00090,
        "specific_heat_kj_kg_c": 2.10,
        "vapor_pressure_kpa_25c": 1.5,
        "typical_density_20c": 800.0,
    },
    "LPG": {  # Liquefied Petroleum Gas
        "thermal_expansion_coeff": 0.00300,
        "specific_heat_kj_kg_c": 2.50,
        "vapor_pressure_kpa_25c": 1200.0,
        "typical_density_20c": 540.0,
    },
    "RFO": {  # Residual Fuel Oil
        "thermal_expansion_coeff": 0.00065,
        "specific_heat_kj_kg_c": 1.80,
        "vapor_pressure_kpa_25c": 0.01,
        "typical_density_20c": 980.0,
    },
    "DEFAULT": {  # Generic petroleum product
        "thermal_expansion_coeff": 0.00095,
        "specific_heat_kj_kg_c": 2.00,
        "vapor_pressure_kpa_25c": 10.0,
        "typical_density_20c": 820.0,
    },
}


@dataclass
class MassResult:
    """Result of mass calculation for a tank."""
    mass_kg: float
    volume_litres: float
    density_at_temp_kg_m3: float
    temperature_c: float
    density_at_20c_kg_m3: float
    product_type: Optional[str] = None
    timestamp_utc: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "mass_kg": round(self.mass_kg, 2),
            "volume_litres": round(self.volume_litres, 2),
            "density_at_temp_kg_m3": round(self.density_at_temp_kg_m3, 3),
            "temperature_c": round(self.temperature_c, 2),
            "density_at_20c_kg_m3": round(self.density_at_20c_kg_m3, 3),
            "product_type": self.product_type,
            "timestamp_utc": self.timestamp_utc,
        }


@dataclass
class MassChange:
    """Represents a change in mass over time."""
    initial_mass_kg: float
    final_mass_kg: float
    delta_mass_kg: float
    delta_volume_litres: float
    duration_hours: Optional[float] = None
    rate_kg_per_hour: Optional[float] = None
    
    def to_dict(self) -> dict:
        return {
            "initial_mass_kg": round(self.initial_mass_kg, 2),
            "final_mass_kg": round(self.final_mass_kg, 2),
            "delta_mass_kg": round(self.delta_mass_kg, 2),
            "delta_volume_litres": round(self.delta_volume_litres, 2),
            "duration_hours": round(self.duration_hours, 2) if self.duration_hours else None,
            "rate_kg_per_hour": round(self.rate_kg_per_hour, 2) if self.rate_kg_per_hour else None,
        }


@dataclass
class ReconciliationResult:
    """Result of mass balance reconciliation for a transfer operation."""
    source_mass_change_kg: float
    destination_mass_change_kg: float
    metered_mass_kg: float
    discrepancy_kg: float
    discrepancy_percent: float
    status: str  # "BALANCED", "GAIN", "LOSS", "ERROR"
    details: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "source_mass_change_kg": round(self.source_mass_change_kg, 2),
            "destination_mass_change_kg": round(self.destination_mass_change_kg, 2),
            "metered_mass_kg": round(self.metered_mass_kg, 2),
            "discrepancy_kg": round(self.discrepancy_kg, 2),
            "discrepancy_percent": round(self.discrepancy_percent, 4),
            "status": self.status,
            "details": self.details,
        }


class MassBalanceCalculator:
    """
    Calculator for mass balance operations in petroleum storage tanks.
    
    Implements the fundamental principle of mass conservation:
    - Mass = Volume × Density
    - Density varies with temperature: ρ(T) = ρ₂₀ × [1 - β(T - 20)]
    
    Usage:
        calc = MassBalanceCalculator()
        result = calc.calculate_mass_in_tank(
            gov_litres=500000,
            temperature_c=28.5,
            density_at_20c=850.0
        )
    """
    
    # Acceptable discrepancy threshold for reconciliation (0.5%)
    ACCEPTABLE_DISCREPANCY_PERCENT = 0.5
    
    def __init__(self, reference_temp_c: float = 20.0):
        """
        Initialize the mass balance calculator.
        
        Args:
            reference_temp_c: Reference temperature for density (default 20°C)
        """
        self.reference_temp_c = reference_temp_c
        logger.info(f"MassBalanceCalculator initialized with reference temp: {reference_temp_c}°C")
    
    def get_product_properties(self, product_type: Optional[str] = None) -> dict:
        """Get properties for a specific product type."""
        if product_type and product_type.upper() in PRODUCT_PROPERTIES:
            return PRODUCT_PROPERTIES[product_type.upper()]
        return PRODUCT_PROPERTIES["DEFAULT"]
    
    def calculate_density_at_temperature(
        self,
        density_at_20c: float,
        temperature_c: float,
        product_type: Optional[str] = None,
        thermal_expansion_coeff: Optional[float] = None
    ) -> float:
        """
        Calculate density at a given temperature using thermal expansion.
        
        Formula: ρ(T) = ρ₂₀ × [1 - β × (T - 20)]
        
        Args:
            density_at_20c: Density at 20°C in kg/m³
            temperature_c: Observed temperature in °C
            product_type: Product type for coefficient lookup
            thermal_expansion_coeff: Override coefficient (per °C)
            
        Returns:
            Density at observed temperature in kg/m³
        """
        if thermal_expansion_coeff is None:
            props = self.get_product_properties(product_type)
            thermal_expansion_coeff = props["thermal_expansion_coeff"]
        
        delta_t = temperature_c - self.reference_temp_c
        
        # Linear thermal expansion model
        # For more accuracy, could use the full ASTM D1250 table
        density_at_temp = density_at_20c * (1 - thermal_expansion_coeff * delta_t)
        
        logger.debug(
            f"Density correction: {density_at_20c:.2f} kg/m³ @ 20°C → "
            f"{density_at_temp:.2f} kg/m³ @ {temperature_c:.1f}°C "
            f"(β={thermal_expansion_coeff}, ΔT={delta_t:.1f}°C)"
        )
        
        return density_at_temp
    
    def calculate_mass_from_volume(
        self,
        volume_litres: float,
        density_kg_m3: float
    ) -> float:
        """
        Convert volume to mass using density.
        
        Formula: Mass (kg) = Volume (L) × Density (kg/m³) / 1000
        
        Args:
            volume_litres: Volume in litres
            density_kg_m3: Density in kg/m³
            
        Returns:
            Mass in kilograms
        """
        # 1 m³ = 1000 litres, so:
        # mass (kg) = volume (L) × density (kg/m³) / 1000
        mass_kg = volume_litres * density_kg_m3 / 1000.0
        return mass_kg
    
    def calculate_volume_from_mass(
        self,
        mass_kg: float,
        density_kg_m3: float
    ) -> float:
        """
        Convert mass to volume using density.
        
        Formula: Volume (L) = Mass (kg) × 1000 / Density (kg/m³)
        
        Args:
            mass_kg: Mass in kilograms
            density_kg_m3: Density in kg/m³
            
        Returns:
            Volume in litres
        """
        volume_litres = mass_kg * 1000.0 / density_kg_m3
        return volume_litres
    
    def calculate_mass_in_tank(
        self,
        gov_litres: float,
        temperature_c: float,
        density_at_20c: float,
        product_type: Optional[str] = None,
        timestamp_utc: Optional[str] = None
    ) -> MassResult:
        """
        Calculate the mass of product in a tank at observed conditions.
        
        This is the primary method for mass calculation, accounting for
        temperature effects on density.
        
        Args:
            gov_litres: Gross Observed Volume in litres
            temperature_c: Observed product temperature in °C
            density_at_20c: Density at 20°C in kg/m³
            product_type: Product type (PMS, AGO, DPK, etc.)
            timestamp_utc: Optional timestamp for the reading
            
        Returns:
            MassResult with calculated mass and supporting data
        """
        if gov_litres is None or temperature_c is None or density_at_20c is None:
            logger.warning("Cannot calculate mass: missing required parameters")
            return MassResult(
                mass_kg=0.0,
                volume_litres=gov_litres or 0.0,
                density_at_temp_kg_m3=0.0,
                temperature_c=temperature_c or 0.0,
                density_at_20c_kg_m3=density_at_20c or 0.0,
                product_type=product_type,
                timestamp_utc=timestamp_utc
            )
        
        # Calculate density at observed temperature
        density_at_temp = self.calculate_density_at_temperature(
            density_at_20c=density_at_20c,
            temperature_c=temperature_c,
            product_type=product_type
        )
        
        # Calculate mass
        mass_kg = self.calculate_mass_from_volume(gov_litres, density_at_temp)
        
        logger.info(
            f"Mass calculation: {gov_litres:,.0f} L × {density_at_temp:.2f} kg/m³ "
            f"= {mass_kg:,.2f} kg @ {temperature_c:.1f}°C"
        )
        
        return MassResult(
            mass_kg=mass_kg,
            volume_litres=gov_litres,
            density_at_temp_kg_m3=density_at_temp,
            temperature_c=temperature_c,
            density_at_20c_kg_m3=density_at_20c,
            product_type=product_type,
            timestamp_utc=timestamp_utc
        )
    
    def calculate_mass_change(
        self,
        before: MassResult,
        after: MassResult,
        duration_hours: Optional[float] = None
    ) -> MassChange:
        """
        Calculate the change in mass between two measurements.
        
        Args:
            before: Mass result at start time
            after: Mass result at end time
            duration_hours: Time between measurements
            
        Returns:
            MassChange with delta values
        """
        delta_mass = after.mass_kg - before.mass_kg
        delta_volume = after.volume_litres - before.volume_litres
        
        rate = None
        if duration_hours and duration_hours > 0:
            rate = delta_mass / duration_hours
        
        return MassChange(
            initial_mass_kg=before.mass_kg,
            final_mass_kg=after.mass_kg,
            delta_mass_kg=delta_mass,
            delta_volume_litres=delta_volume,
            duration_hours=duration_hours,
            rate_kg_per_hour=rate
        )
    
    def reconcile_transfer(
        self,
        source_before: MassResult,
        source_after: MassResult,
        dest_before: MassResult,
        dest_after: MassResult,
        metered_volume_litres: Optional[float] = None,
        metered_density_kg_m3: Optional[float] = None
    ) -> ReconciliationResult:
        """
        Perform mass balance reconciliation for a tank-to-tank transfer.
        
        The fundamental equation is:
            Source Loss + Destination Gain + Losses = 0
        
        Args:
            source_before: Source tank mass before transfer
            source_after: Source tank mass after transfer
            dest_before: Destination tank mass before transfer
            dest_after: Destination tank mass after transfer
            metered_volume_litres: Volume measured by flow meter (optional)
            metered_density_kg_m3: Density at meter (optional)
            
        Returns:
            ReconciliationResult with discrepancy analysis
        """
        # Calculate mass changes
        source_change = source_before.mass_kg - source_after.mass_kg  # Positive = loss
        dest_change = dest_after.mass_kg - dest_before.mass_kg  # Positive = gain
        
        # Calculate metered mass if available
        metered_mass = 0.0
        if metered_volume_litres and metered_density_kg_m3:
            metered_mass = self.calculate_mass_from_volume(
                metered_volume_litres, metered_density_kg_m3
            )
        elif metered_volume_litres:
            # Use average density from tanks
            avg_density = (source_before.density_at_temp_kg_m3 + 
                          dest_after.density_at_temp_kg_m3) / 2
            metered_mass = self.calculate_mass_from_volume(
                metered_volume_litres, avg_density
            )
        else:
            # No meter data, use source loss as reference
            metered_mass = source_change
        
        # Calculate discrepancy
        # Ideally: source_loss = dest_gain = metered
        # Discrepancy = dest_gain - source_loss (should be near zero)
        discrepancy = dest_change - source_change
        
        # Calculate percentage discrepancy relative to transferred mass
        reference_mass = max(source_change, dest_change, metered_mass, 1.0)
        discrepancy_percent = (abs(discrepancy) / reference_mass) * 100
        
        # Determine status
        if discrepancy_percent <= self.ACCEPTABLE_DISCREPANCY_PERCENT:
            status = "BALANCED"
            details = f"Transfer reconciled within {self.ACCEPTABLE_DISCREPANCY_PERCENT}% tolerance"
        elif discrepancy > 0:
            status = "GAIN"
            details = f"Destination gained more than source lost by {discrepancy:,.2f} kg"
        else:
            status = "LOSS"
            details = f"Source lost more than destination gained by {abs(discrepancy):,.2f} kg"
        
        logger.info(
            f"Transfer reconciliation: Source lost {source_change:,.2f} kg, "
            f"Dest gained {dest_change:,.2f} kg. "
            f"Discrepancy: {discrepancy:,.2f} kg ({discrepancy_percent:.3f}%) - {status}"
        )
        
        return ReconciliationResult(
            source_mass_change_kg=-source_change,  # Negative = decrease
            destination_mass_change_kg=dest_change,
            metered_mass_kg=metered_mass,
            discrepancy_kg=discrepancy,
            discrepancy_percent=discrepancy_percent,
            status=status,
            details=details
        )
    
    def estimate_mass_at_standard_conditions(
        self,
        gsv_litres: float,
        density_at_20c: float
    ) -> float:
        """
        Calculate mass from GSV (already temperature-corrected volume).
        
        Since GSV is already at standard conditions, we use density@20C directly.
        
        Args:
            gsv_litres: Gross Standard Volume at 20°C
            density_at_20c: Density at 20°C in kg/m³
            
        Returns:
            Mass in kilograms
        """
        return self.calculate_mass_from_volume(gsv_litres, density_at_20c)
