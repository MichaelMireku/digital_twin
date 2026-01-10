# File: fuel_depot_digital_twin/core/models/gantry.py
import datetime
import logging
from typing import Optional, List, Dict, Any # Added List
from .base import Asset, DataPoint # Correct import

logger = logging.getLogger(__name__)

class GantryRack(Asset): # << NEW CLASS DEFINITION
    def __init__(self,
                 asset_id: str,
                 asset_type: str = "GantryRack",
                 description: Optional[str] = None,
                 # Add any other gantry-rack specific static attributes
                 **kwargs):
        super().__init__(asset_id=asset_id, asset_type=asset_type, description=description, **kwargs)
        
        self.loading_arms: List[str] = [] # Example: list of LoadingArm asset_ids associated
        self.status = DataPoint(name="Gantry Rack Status", unit="state") # e.g. "Available", "InUse", "OutOfService"

        self.update_last_modified()
        logger.debug(f"GantryRack instance created: {self.asset_id}")

    def add_loading_arm(self, arm_id: str):
        if arm_id not in self.loading_arms:
            self.loading_arms.append(arm_id)

    def update_gantry_status(self, status_value: str, timestamp_utc: datetime.datetime, status_detail: str = "OK"):
        self.status.update(status_value, timestamp_utc, status_detail)
        self.update_last_modified(timestamp_utc)

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "loading_arms_associated": self.loading_arms,
            "gantry_rack_status_details": self.status.to_dict()
        })
        return data


class LoadingArm(Asset):
    def __init__(self,
                 asset_id: str, # <<<< Make sure asset_id is accepted
                 asset_type: str = "LoadingArm", # Default type
                 gantry_rack_id: Optional[str] = None,
                 side: Optional[str] = None,
                 product_service: Optional[str] = None,
                 connected_meter_id: Optional[str] = None,
                 # Add other loading-arm specific static attributes
                 **kwargs): # To catch all attributes from assets table

        # Call super().__init__ with all common Asset parameters
        super().__init__(
            asset_id=asset_id, # <<<< Pass asset_id to super
            asset_type=asset_type,
            gantry_rack_id=gantry_rack_id,
            side=side,
            product_service=product_service,
            connected_meter_id=connected_meter_id,
            **kwargs # Pass remaining common_params and other kwargs
        )
        # self.gantry_rack_id = gantry_rack_id # Already handled by super if passed via kwargs
        # self.side = side
        # self.product_service = product_service # Also handled by super
        # self.connected_meter_id = connected_meter_id

        # Dynamic DataPoints for LoadingArm
        self.valve_position = DataPoint(name="Valve Position", unit="%") # e.g., 0-100
        self.grounding_check = DataPoint(name="Grounding Check", unit="status") # e.g., "OK", "Fail", True/False
        self.overfill_status = DataPoint(name="Overfill Status", unit="status") # e.g., "OK", "Alarm"
        self.operational_status = DataPoint(name="Operational Status", unit="state") # e.g. "Available", "InUse", "Faulted"

        self.update_last_modified()
        logger.debug(f"LoadingArm instance created: {self.asset_id}")

    def update_valve_position(self, value: float, timestamp_utc: datetime.datetime, status: str = "OK"):
        self.valve_position.update(value, timestamp_utc, status)
        self.update_last_modified(timestamp_utc)

    def update_grounding_check(self, value: bool, timestamp_utc: datetime.datetime, status: str = "OK"): # Assuming boolean
        self.grounding_check.update(value, timestamp_utc, status)
        self.update_last_modified(timestamp_utc)

    def update_overfill_status(self, value: str, timestamp_utc: datetime.datetime, status: str = "OK"):
        self.overfill_status.update(value, timestamp_utc, status)
        self.update_last_modified(timestamp_utc)
        
    def update_arm_status(self, value: str, timestamp_utc: datetime.datetime, status: str = "OK"):
        self.operational_status.update(value, timestamp_utc, status)
        self.update_last_modified(timestamp_utc)

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            # gantry_rack_id, side, product_service, connected_meter_id should be in super().to_dict()
            "valve_position_details": self.valve_position.to_dict(),
            "grounding_check_details": self.grounding_check.to_dict(),
            "overfill_status_details": self.overfill_status.to_dict(),
            "operational_status_details": self.operational_status.to_dict()
        })
        return data