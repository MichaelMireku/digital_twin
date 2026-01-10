# File: fuel_depot_digital_twin/core/models/pipeline.py
import datetime
import logging
from typing import Optional, List, Dict, Any
from .base import Asset, DataPoint # Ensure this import is correct

logger = logging.getLogger(__name__)

class Pipeline(Asset):
    def __init__(self,
                 asset_id: str, # Explicitly accept asset_id
                 asset_type: str = "Pipeline", # Default or allow it to be passed
                 # Define other pipeline-specific static attributes from your assets table
                 pipeline_source: Optional[str] = None,
                 pipeline_destination: Optional[str] = None,
                 pipeline_size_inches: Optional[float] = None,
                 pipeline_length_km: Optional[float] = None,
                 # allowed_products, capacity_litres (linefill), density_at_15c_kg_m3
                 # are common attributes handled by Asset base class if passed in kwargs
                 **kwargs): # To catch all other attributes like description, area, etc.

        super().__init__(
            asset_id=asset_id,
            asset_type=asset_type, # Pass asset_type
            pipeline_source=pipeline_source, # Pass specific attributes to Asset constructor
            pipeline_destination=pipeline_destination,
            pipeline_size_inches=pipeline_size_inches,
            pipeline_length_km=pipeline_length_km,
            # other common Asset params like description, area, product_service,
            # capacity_litres, density_at_15c_kg_m3, allowed_products are expected
            # to be in kwargs if they are not explicit params of Asset.__init__
            # or if they are explicit, Asset.__init__ needs to accept them.
            # The Asset class __init__ I provided earlier tries to set any kwarg as an attribute.
            **kwargs # Pass through all other parameters
        )
        # Dynamic DataPoints for Pipeline
        self.current_flow_rate = DataPoint(name="Flow Rate", unit="m³/hr")
        self.current_pressure = DataPoint(name="Pressure", unit="bar")
        self.current_temperature = DataPoint(name="Temperature", unit="°C")
        self.current_product_in_line = DataPoint(name="Current Product", unit="product_code")
        self.operational_status = DataPoint(name="Operational Status", unit="status")
        self.leak_detection_status = DataPoint(name="Leak Detection", unit="status")

        self.update_last_modified()
        logger.debug(f"Pipeline instance created: {self.asset_id}")

    # ... (add update methods and to_dict() as shown in my previous "full code" response for Pipeline) ...
    def update_flow(self, flow_rate: float, timestamp_utc: datetime.datetime, status: str = "OK"):
        self.current_flow_rate.update(flow_rate, timestamp_utc, status)
        self.update_last_modified(timestamp_utc)

    def update_pressure(self, pressure: float, timestamp_utc: datetime.datetime, status: str = "OK"):
        self.current_pressure.update(pressure, timestamp_utc, status)
        self.update_last_modified(timestamp_utc)

    def update_temperature(self, temperature: float, timestamp_utc: datetime.datetime, status: str = "OK"):
        self.current_temperature.update(temperature, timestamp_utc, status)
        self.update_last_modified(timestamp_utc)

    def update_product_in_line(self, product_code: str, timestamp_utc: datetime.datetime, status: str = "OK"):
        self.current_product_in_line.update(product_code, timestamp_utc, status)
        self.update_last_modified(timestamp_utc)

    def update_operational_state(self,
                                 op_status: str, 
                                 timestamp_utc: datetime.datetime,
                                 leak_status: Optional[str] = None, 
                                 status_detail: str = "OK"):
        self.operational_status.update(op_status, timestamp_utc, status_detail)
        if leak_status is not None:
            self.leak_detection_status.update(leak_status, timestamp_utc, status_detail)
        self.update_last_modified(timestamp_utc)

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "current_flow_rate_details": self.current_flow_rate.to_dict(),
            "current_pressure_details": self.current_pressure.to_dict(),
            "current_temperature_details": self.current_temperature.to_dict(),
            "current_product_in_line_details": self.current_product_in_line.to_dict(),
            "operational_status_details": self.operational_status.to_dict(),
            "leak_detection_status_details": self.leak_detection_status.to_dict()
        })
        return data