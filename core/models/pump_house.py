# File: fuel_depot_digital_twin/core/models/pump_house.py
import logging
import datetime
from typing import Optional, List, Dict, Any
from .base import Asset, DataPoint # Correct import

logger = logging.getLogger(__name__)

class PumpHouse(Asset):
    def __init__(self,
                 asset_id: str,
                 asset_type: str = "PumpHouse",
                 # Add other pump_house-specific static attributes if any
                 # e.g., area, product_service from your populate_assets.sql
                 **kwargs): # To catch all attributes

        super().__init__(asset_id=asset_id, asset_type=asset_type, **kwargs)

        # Example DataPoint if a pump house has overall status or readings
        self.operational_status = DataPoint(name="Operational Status", unit="status")
        # self.contained_pumps: List[str] = [] # Could list pump_ids if loaded separately

        self.update_last_modified()
        logger.debug(f"PumpHouse instance created: {self.asset_id}")

    def update_status(self, status_value: str, timestamp_utc: datetime.datetime, status_detail: str = "OK"):
        self.operational_status.update(status_value, timestamp_utc, status_detail)
        self.update_last_modified(timestamp_utc)

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "operational_status_details": self.operational_status.to_dict(),
            # "contained_pumps": self.contained_pumps
        })
        return data