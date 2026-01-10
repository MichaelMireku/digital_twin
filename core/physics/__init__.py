# File: fuel_depot_digital_twin/core/physics/__init__.py
"""
Physics Engine Module for Fuel Depot Digital Twin

This module provides physics-based calculations for petroleum depot operations:
- Mass Balance: Volume-to-mass conversion with temperature/density corrections
- Energy Balance: Heat content, transfer rates, and temperature prediction
- Evaporation Loss: Standing and working loss calculations (API MPMS Ch. 19)
"""

from .mass_balance import MassBalanceCalculator, MassResult, MassChange, ReconciliationResult
from .energy_balance import EnergyBalanceCalculator, HeatContent, TemperaturePrediction
from .evaporation import EvaporationCalculator, EvaporationLoss

__all__ = [
    # Mass Balance
    'MassBalanceCalculator',
    'MassResult',
    'MassChange',
    'ReconciliationResult',
    # Energy Balance
    'EnergyBalanceCalculator',
    'HeatContent',
    'TemperaturePrediction',
    # Evaporation
    'EvaporationCalculator',
    'EvaporationLoss',
]
