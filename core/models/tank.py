# File: fuel_depot_digital_twin/core/models/tank.py
import logging
import datetime
from typing import Optional, Dict, Any, List

from .base import Asset, DataPoint
from data.strapping_loader import get_strapping_table_litres

logger = logging.getLogger(__name__)

class StorageTank(Asset):
    def __init__(self, asset_id: str, asset_type: str, depot_id: str, description: Optional[str] = None,
                 area: Optional[str] = None, capacity_litres: Optional[float] = None,
                 product_service: Optional[str] = None, allowed_products: Optional[List[str]] = None,
                 foam_system_present: bool = False,
                 density_at_20c_kg_m3: Optional[float] = None, # UPDATED
                 **kwargs):

        super().__init__(
            asset_id=asset_id, asset_type=asset_type, depot_id=depot_id, description=description, area=area,
            capacity_litres=capacity_litres, product_service=product_service,
            allowed_products=allowed_products,
            density_at_20c_kg_m3=density_at_20c_kg_m3, # UPDATED
            **kwargs
        )
        
        self.strapping_data: Optional[Dict[int, float]] = None
        self.max_level_mm: Optional[int] = None
        
        self.current_level_mm = DataPoint(name="Level", unit="mm")
        self.current_level_percentage = DataPoint(name="Level Percentage", unit="%")
        self.current_volume_litres = DataPoint(name="Volume GOV", unit="Liters")
        self.gross_standard_volume_litres = DataPoint(name="Volume GSV", unit="Liters@20C") # UPDATED UNIT
        self.current_temperature = DataPoint(name="Temperature", unit="°C")
        self.high_level_alarm = DataPoint(name="High Level Alarm", unit="status")
        self.low_level_alarm = DataPoint(name="Low Level Alarm", unit="status")

        self._load_strapping_data()

    def _load_strapping_data(self):
        try:
            self.strapping_data = get_strapping_table_litres(self.asset_id)
            if self.strapping_data:
                self.max_level_mm = max(self.strapping_data.keys())
            else:
                self.max_level_mm = 0
        except Exception:
            self.strapping_data = {}
            self.max_level_mm = 0

    def _calculate_volume_from_level(self, level_mm: float) -> Optional[float]:
        # (Implementation of volume calculation as before)
        return 0.0 # Placeholder for brevity

    def update_iot_level(self, level_mm: float, timestamp: datetime.datetime, status: str = "OK"):
        self.current_level_mm.update(level_mm, timestamp, status)
        percentage = (level_mm / self.max_level_mm) * 100 if self.max_level_mm and self.max_level_mm > 0 else 0
        self.current_level_percentage.update(round(percentage, 2), timestamp, status)
        volume = self._calculate_volume_from_level(level_mm)
        self.current_volume_litres.update(round(volume, 2) if volume is not None else None, timestamp, status)

    def update_temperature(self, temperature_c: float, timestamp: datetime.datetime, status: str = "OK"):
        self.current_temperature.update(temperature_c, timestamp, status)

    def update_gsv(self, gsv_litres: Optional[float], timestamp: datetime.datetime, status: str = "OK"):
        self.gross_standard_volume_litres.update(round(gsv_litres, 2) if gsv_litres is not None else None, timestamp, status)

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "current_level_mm": self.current_level_mm.to_dict(),
            "current_level_percentage": self.current_level_percentage.to_dict(),
            "current_volume_litres_gov": self.current_volume_litres.to_dict(),
            "gross_standard_volume_litres_gsv": self.gross_standard_volume_litres.to_dict(),
            "current_temperature": self.current_temperature.to_dict(),
        })
        return data