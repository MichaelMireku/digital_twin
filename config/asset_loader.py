# fuel_depot_digital_twin/config/asset_loader.py

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from data import database
from core.models import (
    StorageTank, Pump, Meter, Pipeline, LoadingArm, GantryRack, PumpHouse, Asset
)

logger = logging.getLogger(__name__)

# A mapping from asset_type string in the DB to the actual Python class
ASSET_CLASS_MAP = {
    "StorageTank": StorageTank,
    "Pump": Pump,
    "Meter": Meter,
    "Pipeline": Pipeline,
    "LoadingArm": LoadingArm,
    "GantryRack": GantryRack,
    "PumpHouse": PumpHouse,
}

def create_asset_instance(asset_data: Dict[str, Any]) -> Optional[Asset]:
    """Factory function to create an instance of a specific asset class."""
    asset_type = asset_data.get("asset_type")
    asset_class = ASSET_CLASS_MAP.get(asset_type)

    if not asset_class:
        logger.warning(f"Unknown asset type '{asset_type}' encountered for asset_id '{asset_data.get('asset_id')}'. Skipping instance creation.")
        return None

    try:
        # Pydantic models are great for this, as they handle validation and type conversion
        return asset_class(**asset_data)
    except Exception as e:
        logger.error(f"Failed to instantiate asset {asset_data.get('asset_id')} of type {asset_type}: {e}", exc_info=True)
        return None

def load_assets_from_db() -> Dict[str, Asset]:
    """
    Loads all asset configurations from the database and creates Python object instances.
    """
    assets: Dict[str, Asset] = {}
    with database.get_db() as db:
        if not db:
            logger.error("Could not get a database session for loading assets.")
            return assets
        try:
            # CORRECTED: Use the new paginated function to get all assets
            all_assets_metadata, total_count = database.get_all_asset_metadata_paginated(db, per_page=1000) # Load up to 1000 assets
            logger.info(f"Loaded metadata for {len(all_assets_metadata)} of {total_count} assets from the database.")

            for asset_data in all_assets_metadata:
                asset_instance = create_asset_instance(asset_data)
                if asset_instance:
                    assets[asset_instance.asset_id] = asset_instance

        except Exception as e:
            logger.error(f"Error loading assets from database: {e}", exc_info=True)

    if not assets:
        logger.warning("Asset loading returned empty. This might be normal if the DB is empty, or it could indicate an issue.")

    return assets