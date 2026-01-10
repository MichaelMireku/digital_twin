# File: fuel_depot_digital_twin/core/models/pump.py
import datetime
import logging
from typing import Optional, Dict, Any

# Corrected import:
from .base import Asset, DataPoint # Import Asset and DataPoint from base.py

logger = logging.getLogger(__name__)

class Pump(Asset):
    def __init__(self, asset_id: str, asset_type: str, # depot_id is inherited
                 pump_house_id: Optional[str] = None,
                 product_service: Optional[str] = None,
                 pump_service_description: Optional[str] = None,
                 # Add other pump-specific static attributes from your assets table if any
                 **kwargs): # To catch all other attributes from the assets table row

        super().__init__(asset_id, asset_type=asset_type, pump_house_id=pump_house_id,
                         product_service=product_service, pump_service_description=pump_service_description,
                         **kwargs) # Pass kwargs to parent

        # Dynamic DataPoints for Pump
        self.status = DataPoint(name="Pump Status", unit="state") # e.g., "Running", "Stopped", "Tripped"
        self.control_mode = DataPoint(name="Control Mode", unit="mode") # e.g., "Auto", "Manual", "Local"
        self.current_power = DataPoint(name="Power Consumption", unit="kW")
        self.current_vibration = DataPoint(name="Vibration Level", unit="mm/s")
        self.current_temperature = DataPoint(name="Motor Temperature", unit="°C")
        self.run_hours = DataPoint(name="Run Hours", unit="hours") # This would need accumulation logic

        self.update_last_modified() # Set initial last_updated

    def update_operational_status(self, status: Optional[str], timestamp_utc: datetime.datetime, 
                                  control_mode: Optional[str] = None, status_detail: str = "OK"):
        if status is not None:
            self.status.update(status, timestamp_utc, status_detail)
        if control_mode is not None:
            self.control_mode.update(control_mode, timestamp_utc, status_detail)
        self.update_last_modified(timestamp_utc)
        logger.debug(f"Pump {self.asset_id} status updated: {status}, mode: {control_mode}")

    def update_power(self, power_kw: float, timestamp_utc: datetime.datetime, status: str = "OK"):
        self.current_power.update(power_kw, timestamp_utc, status)
        self.update_last_modified(timestamp_utc)

    def update_vibration(self, vibration_mm_s: float, timestamp_utc: datetime.datetime, status: str = "OK"):
        self.current_vibration.update(vibration_mm_s, timestamp_utc, status)
        self.update_last_modified(timestamp_utc)

    def update_temperature(self, temperature_c: float, timestamp_utc: datetime.datetime, status: str = "OK"):
        self.current_temperature.update(temperature_c, timestamp_utc, status)
        self.update_last_modified(timestamp_utc)

    # Add update_run_hours method if needed

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "pump_house_id": self.pump_house_id, # Already in base if passed via kwargs, but can be explicit
            "pump_service_description": getattr(self, 'pump_service_description', None), # Get if exists
            "current_status_details": self.status.to_dict(),
            "control_mode_details": self.control_mode.to_dict(),
            "power_consumption_details": self.current_power.to_dict(),
            "vibration_level_details": self.current_vibration.to_dict(),
            "motor_temperature_details": self.current_temperature.to_dict(),
            "run_hours_details": self.run_hours.to_dict()
        })
        return data