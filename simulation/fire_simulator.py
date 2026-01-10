# simulation/fire_simulator.py

import math
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

class FireSimulator:
    """
    Simulates the thermal radiation effects of a full-surface tank fire.
    Uses a simplified Point Source model based on industry standards.
    """

    # --- Model Constants ---
    # These values are typical for gasoline/petrol fires.
    HEAT_OF_COMBUSTION_KW_M2 = 4500  # Heat generated per square meter of burning fuel (kW/m^2)
    FRACTION_OF_HEAT_RADIATED = 0.3  # A typical value for large hydrocarbon pool fires
    
    # Heat radiation levels and their effects (in kW/m^2)
    # These are standard industry thresholds.
    RADIATION_THRESHOLDS_KW_M2 = {
        "equipment_damage": 37.5, # Significant damage to process equipment
        "second_degree_burns": 5.0, # Causes 2nd-degree burns in ~1 minute
        "pain_threshold": 1.6, # Causes pain after ~1 minute, safe for brief exposure
    }

    def __init__(self, tank_data: Dict[str, Any]):
        """
        Initializes the simulator with the tank that is on fire.

        Args:
            tank_data (Dict): Dictionary with tank details, must include 'capacity_litres'.
        """
        self.tank_id = tank_data.get('asset_id', 'UnknownTank')
        self.capacity_litres = float(tank_data.get('capacity_litres', 0))
        
        # Estimate the tank diameter from its capacity (assuming a standard height-to-diameter ratio)
        # V = pi * r^2 * h. If h = 1.5*d = 3*r, then V = 3 * pi * r^3.
        # So, r = (V / (3*pi))^(1/3). d = 2*r.
        # This is a simplification; a real model would use exact dimensions from asset data.
        volume_m3 = self.capacity_litres / 1000
        radius_m = (volume_m3 / (3 * math.pi)) ** (1/3)
        self.tank_diameter_m = radius_m * 2
        
        logger.info(f"FireSimulator initialized for {self.tank_id} with estimated diameter {self.tank_diameter_m:.2f} m")

    def calculate_radiation_distance(self, heat_intensity_kw_m2: float) -> float:
        """
        Calculates the distance at which a given heat intensity is felt.
        Based on the inverse square law for radiation from a point source.
        """
        # 1. Calculate the total heat radiated by the fire (Q) in kW
        fire_area_m2 = math.pi * ((self.tank_diameter_m / 2) ** 2)
        total_heat_output_kw = self.HEAT_OF_COMBUSTION_KW_M2 * fire_area_m2
        radiated_heat_kw = total_heat_output_kw * self.FRACTION_OF_HEAT_RADIATED
        
        # 2. Calculate distance (r) using the inverse square law: I = Q / (4 * pi * r^2)
        # Rearranging for r: r = sqrt(Q / (4 * pi * I))
        if heat_intensity_kw_m2 <= 0:
            return 0.0

        distance_m = math.sqrt(radiated_heat_kw / (4 * math.pi * heat_intensity_kw_m2))
        return distance_m

    def run(self) -> Dict[str, float]:
        """
        Runs the simulation to calculate the radii for each safety threshold.

        Returns:
            Dict[str, float]: A dictionary mapping effect names to their impact radius in meters.
        """
        results = {}
        for effect, intensity in self.RADIATION_THRESHOLDS_KW_M2.items():
            radius = self.calculate_radiation_distance(intensity)
            results[effect] = round(radius, 2)
            logger.info(f"Calculated radius for '{effect}' ({intensity} kW/m^2): {radius:.2f} m")
            
        return results