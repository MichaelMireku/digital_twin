# fuel_depot_digital_twin/utils/volume_calculator.py

import os
import sys
import logging
from typing import Dict, Optional
import numpy as np

# --- ROBUST PATH SETUP ---
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from config import settings
except ImportError as e:
    # This fallback is for when settings are not strictly needed but good practice
    print(f"Warning: Could not import settings module: {e}")
    settings = None

logger = logging.getLogger(__name__)

class VolumeCalculator:
    """
    Handles advanced volume calculations for storage tanks, including
    Gross Observed Volume (GOV) and Gross Standard Volume (GSV).
    """

    def __init__(self):
        # The standard reference temperature, typically 15°C or 20°C.
        # Defaulting to 20.0 as per our settings file.
        self.std_temp_c = 20.0
        if settings and hasattr(settings, 'STANDARD_REFERENCE_TEMPERATURE_CELSIUS'):
            self.std_temp_c = settings.STANDARD_REFERENCE_TEMPERATURE_CELSIUS
        logger.info(f"VolumeCalculator initialized with standard reference temperature: {self.std_temp_c}°C")

    def calculate_gov_from_strapping(self, level_mm: float, strapping_data: Dict[int, float]) -> Optional[float]:
        """
        Calculates the Gross Observed Volume (GOV) by interpolating from strapping data.

        Args:
            level_mm: The measured level in millimeters.
            strapping_data: A dictionary mapping level (mm) to volume (litres).

        Returns:
            The interpolated volume in litres, or None if calculation fails.
        """
        if not strapping_data or level_mm is None:
            logger.warning("Strapping data is empty or level is not provided. Cannot calculate GOV.")
            return None

        try:
            # Extract levels and volumes into sorted numpy arrays for efficient interpolation
            levels = np.array(sorted(strapping_data.keys()))
            volumes = np.array([strapping_data[lvl] for lvl in levels])

            # Use numpy's interpolation function. It's fast and handles edge cases.
            # np.interp will correctly handle cases where level_mm is outside the range
            # by returning the min or max volume.
            gov = np.interp(level_mm, levels, volumes)
            return float(gov)

        except Exception as e:
            logger.error(f"Error during GOV interpolation for level {level_mm}: {e}", exc_info=True)
            return None


    def get_vcf(self, density_at_20c: float, observed_temp_c: float) -> Optional[float]:
        """
        Calculates the Volume Correction Factor (VCF) based on API tables.
        This is a simplified model. Real-world applications use complex tables (e.g., ASTM D1250).

        Args:
            density_at_20c: The density of the product at 20°C in kg/m³.
            observed_temp_c: The observed temperature of the product in °C.

        Returns:
            The calculated Volume Correction Factor (VCF).
        """
        if density_at_20c is None or observed_temp_c is None:
            return None

        try:
            # Simplified thermal expansion coefficient (alpha) calculation.
            # This is a placeholder for real API table lookups.
            # Different product types (crude, gasoline, diesel) have different coefficients.
            # A typical value for gasoline is around 0.00095 per degree Celsius.
            alpha = 0.00095

            delta_t = observed_temp_c - self.std_temp_c

            # VCF formula: VCF = 1 - (alpha * delta_t)
            vcf = 1 - (alpha * delta_t)
            return vcf

        except Exception as e:
            logger.error(f"Failed to calculate VCF: {e}", exc_info=True)
            return None

    def calculate_gsv(self, gov_litres: float, observed_temp_c: float, density_at_20c: float) -> Optional[float]:
        """
        Calculates the Gross Standard Volume (GSV) by applying the VCF to the GOV.
        GSV is the volume the product would occupy at the standard reference temperature.

        Args:
            gov_litres: The Gross Observed Volume in litres.
            observed_temp_c: The observed temperature of the product in °C.
            density_at_20c: The density of the product at 20°C in kg/m³.

        Returns:
            The calculated Gross Standard Volume in litres.
        """
        if gov_litres is None:
            return None

        vcf = self.get_vcf(density_at_20c, observed_temp_c)

        if vcf is None:
            logger.warning("Could not calculate VCF. GSV calculation aborted.")
            return None

        gsv_litres = gov_litres * vcf
        return gsv_litres