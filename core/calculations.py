# File: fuel_depot_digital_twin/core/calculations.py
import logging
import math
from typing import Optional
from decimal import Decimal, getcontext # Import Decimal and getcontext for precision control
from config import settings

logger = logging.getLogger(__name__)

# Set global precision for Decimal operations to ensure consistency
getcontext().prec = 28 # A common precision for financial/scientific calculations

def calculate_alpha_for_table54b(density_at_15c: Decimal) -> Decimal: # Change type hint
    """
    Calculates the coefficient of thermal expansion (ALPHA) at 15°C
    based on density at 15°C. This formula is standard and requires a 15C input.
    """
    if density_at_15c <= Decimal('0'): # Compare with Decimal
        raise ValueError("Density must be positive for ALPHA calculation.")
    den15_sq = density_at_15c * density_at_15c
    if density_at_15c <= Decimal('770.0'): # Compare with Decimal
        k0, k1 = Decimal('346.42278'), Decimal('0.43884')
        alpha = (k0 + k1 * density_at_15c) / den15_sq
    elif density_at_15c < Decimal('778.0'): # Compare with Decimal
        k0, k1 = Decimal('594.5418'), Decimal('0.0')
        alpha = k0 / den15_sq
        logger.warning(f"Density {density_at_15c} in transition zone (770-778). ALPHA calculation is an approximation.")
    elif density_at_15c < Decimal('839.0'): # Compare with Decimal
        k0, k1 = Decimal('594.5418'), Decimal('0.0')
        alpha = k0 / den15_sq
    else:
        k0, k1 = Decimal('186.9696'), Decimal('0.48618')
        alpha = (k0 + k1 * density_at_15c) / den15_sq
    return alpha

def calculate_precise_vcf_c_table54b(observed_temperature_c: Decimal, density_at_15c: Decimal) -> Optional[Decimal]: # Change type hint
    """
    Calculates the Volume Correction Factor (VCF or CTL) to the reference temperature.
    """
    try:
        alpha_at_15c = calculate_alpha_for_table54b(density_at_15c)
    except ValueError as e:
        logger.error(f"Error calculating ALPHA for VCF: {e}")
        return None
    
    delta_t = observed_temperature_c - Decimal(str(settings.STANDARD_REFERENCE_TEMPERATURE_CELSIUS)) # Convert setting to Decimal

    # Math.exp does not support Decimal. Convert to float for exp, then back to Decimal.
    # This is a practical compromise for functions where Decimal's own math methods are not available
    # and extreme precision for transcendental functions is not paramount, but overall Decimal consistency is.
    exponent = -float(alpha_at_15c) * float(delta_t) * (1 + 0.8 * float(alpha_at_15c) * float(delta_t))
    vcf_float_result = math.exp(exponent)
    
    return Decimal(str(round(vcf_float_result, 5))) # Convert back to Decimal and round

def convert_density_20c_to_15c(density_at_20c: Decimal) -> Decimal: # Change type hint
    """
    Iteratively calculates the equivalent density at 15°C from a known density at 20°C.
    This is necessary because the formula for ALPHA requires density @ 15C.
    Formula: Density_15 = Density_20 / (1 - ALPHA_15 * (20 - 15))
    """
    density_15_guess = density_at_20c * Decimal('1.005') # Use Decimal
    for _ in range(5):
        alpha = calculate_alpha_for_table54b(density_15_guess)
        density_15_calculated = density_at_20c / (Decimal('1') - alpha * Decimal('5')) # Use Decimal constants
        if abs(density_15_calculated - density_15_guess) < Decimal('0.001'): # Compare with Decimal
            break
        density_15_guess = density_15_calculated
    logger.debug(f"Converted density @ 20C of {density_at_20c:.2f} to equivalent density @ 15C of {density_15_guess:.2f}")
    return density_15_guess

def calculate_precise_gsv(
    observed_volume: Decimal, # Accept Decimal
    observed_temperature_c: Decimal, # Accept Decimal
    density_at_20c: Decimal # Accept Decimal
) -> Optional[Decimal]: # Return Decimal
    """
    Calculates GSV at the configured reference temperature (20C).
    Accepts density at 20°C and internally converts it to 15°C for the ASTM formula.
    """
    if observed_volume is None or observed_temperature_c is None or density_at_20c is None:
        logger.warning("Cannot calculate GSV: observed volume, temperature, or density_at_20c is None.")
        return None
    
    try:
        density_at_15c_for_calc = convert_density_20c_to_15c(density_at_20c)
        vcf = calculate_precise_vcf_c_table54b(observed_temperature_c, density_at_15c_for_calc)
        
        if vcf is None:
            return None
            
        gsv = observed_volume * vcf
        gsv_rounded = gsv.quantize(Decimal('0.01')) # Round to 2 decimal places using Decimal
        logger.info(f"Calculated Precise GSV: {gsv_rounded} from GOV: {observed_volume} @ {observed_temperature_c}°C (Density@20C: {density_at_20c}, VCF: {vcf})")
        return gsv_rounded
    except Exception as e:
        logger.error(f"Error during GSV calculation: {e}", exc_info=True)
        return None