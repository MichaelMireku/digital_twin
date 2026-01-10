# File: fuel_depot_digital_twin/core/models/meter.py
import datetime
import logging
from typing import Optional, Dict, Any
from .base import Asset, DataPoint # Correct import

logger = logging.getLogger(__name__)

class Meter(Asset):
    def __init__(self,
                 asset_id: str,
                 asset_type: str = "Meter",
                 # Add other meter-specific static attributes from your assets table if any
                 # e.g., gantry_rack_id, product_service
                 **kwargs): # To catch all attributes from assets table

        super().__init__(asset_id=asset_id, asset_type=asset_type, **kwargs)

        # Dynamic DataPoints for Meter
        self.flow_rate_lpm = DataPoint(name="Flow Rate", unit="LPM")
        self.total_volume_litres = DataPoint(name="Total Volume", unit="Liters") # Or cumulative
        # Add other relevant DataPoints like temperature, pressure if metered

        self.update_last_modified()
        logger.debug(f"Meter instance created: {self.asset_id}")

    def update_flow_rate(self, value: float, timestamp_utc: datetime.datetime, status: str = "OK"):
        self.flow_rate_lpm.update(value, timestamp_utc, status)
        self.update_last_modified(timestamp_utc)

    def update_total_volume(self, value: float, timestamp_utc: datetime.datetime, status: str = "OK"):
        self.total_volume_litres.update(value, timestamp_utc, status)
        self.update_last_modified(timestamp_utc)

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "flow_rate_lpm_details": self.flow_rate_lpm.to_dict(),
            "total_volume_litres_details": self.total_volume_litres.to_dict(),
            # Add other DataPoints to dict
        })
        return data