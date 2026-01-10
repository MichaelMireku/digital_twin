# File: fuel_depot_digital_twin/core/models/__init__.py
import logging

logger = logging.getLogger(__name__)
logger.info("Initializing core.models package...")

# Initialize with placeholders for robustness
Asset = None
DataPoint = None
StorageTank = None
Pump = None
Meter = None
Pipeline = None
LoadingArm = None
GantryRack = None
PumpHouse = None

try:
    from .base import Asset, DataPoint
    logger.info("Successfully imported Asset and DataPoint from .base")
except ImportError as e:
    logger.critical(f"CRITICAL: Failed to import Asset or DataPoint from .base: {e}. Model definitions may fail.", exc_info=True)

try:
    from .tank import StorageTank
    logger.debug("Successfully imported StorageTank from .tank")
except ImportError as e:
    logger.error(f"Failed to import StorageTank from .tank: {e}", exc_info=True)

try:
    from .pump import Pump
    logger.debug("Successfully imported Pump from .pump")
except ImportError as e:
    logger.error(f"Failed to import Pump from .pump: {e}", exc_info=True)

try:
    from .meter import Meter # Assumes meter.py exists and defines Meter
    logger.debug("Successfully imported Meter from .meter")
except ImportError as e:
    logger.error(f"Failed to import Meter from .meter. Ensure meter.py exists and defines Meter class: {e}", exc_info=True)

try:
    from .pipeline import Pipeline
    logger.debug("Successfully imported Pipeline from .pipeline")
except ImportError as e:
    logger.error(f"Failed to import Pipeline from .pipeline: {e}", exc_info=True)

try:
    # Assuming gantry.py defines both LoadingArm and GantryRack
    from .gantry import LoadingArm, GantryRack
    logger.debug("Successfully imported LoadingArm and GantryRack from .gantry")
except ImportError as e:
    logger.error(f"Failed to import LoadingArm or GantryRack from .gantry. Ensure gantry.py exists and defines these classes: {e}", exc_info=True)

try:
    from .pump_house import PumpHouse # Assumes pump_house.py exists
    logger.debug("Successfully imported PumpHouse from .pump_house")
except ImportError as e:
    logger.error(f"Failed to import PumpHouse from .pump_house. Ensure pump_house.py exists and defines PumpHouse class: {e}", exc_info=True)


# Define what is available for import when `from core.models import *` is used,
# or what is typically imported like `from core.models import StorageTank`.
__all__ = [
    "Asset",
    "DataPoint",
    "StorageTank",
    "Pump",
    "Meter",
    "Pipeline",
    "LoadingArm",
    "GantryRack",
    "PumpHouse"
]

# Filter out None values from __all__ if any imports failed,
# to accurately reflect what's available.
# This also ensures that if a module is missing, its corresponding class name won't be in __all__.
_imported_successfully = []
for _name in __all__:
    if globals().get(_name) is not None:
        _imported_successfully.append(_name)
__all__ = _imported_successfully

logger.info(
    "core.models package initialization complete. Available models/classes in __all__: %s",
    ", ".join(__all__) if __all__ else "None (Check import errors for specific models)"
)

# Example: How to check if a model loaded successfully before using it elsewhere
if StorageTank is None: # Check against the actual variable in globals()
    logger.warning("StorageTank model failed to load. Tank-related functionality might be broken.")
if Meter is None:
    logger.warning("Meter model failed to load. Meter-related functionality might be broken.")
# Add similar checks for other critical models if desired.