# File: fuel_depot_digital_twin/core/models/base.py
import datetime
import logging
from typing import Any, Optional, Dict, List

logger = logging.getLogger(__name__)

class DataPoint:
    """Represents a single data point with metadata, like a sensor reading or calculated value."""
    def __init__(self, name: str, unit: Optional[str] = None, data_source_id: Optional[str] = None):
        self.name: str = name
        self.value: Any = None
        self.unit: Optional[str] = unit
        self.timestamp_utc: Optional[datetime.datetime] = None
        self.data_source_id: Optional[str] = data_source_id
        self.status: str = "NoData"

    def update(self, value: Any, timestamp_utc: datetime.datetime, status: str = "OK", unit: Optional[str] = None, data_source_id: Optional[str] = None):
        self.value = value
        if timestamp_utc.tzinfo is None:
            timestamp_utc = timestamp_utc.replace(tzinfo=datetime.timezone.utc)
        self.timestamp_utc = timestamp_utc
        self.status = status
        if unit is not None: self.unit = unit
        if data_source_id is not None: self.data_source_id = data_source_id

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "timestamp_utc": self.timestamp_utc.isoformat(timespec='seconds') if self.timestamp_utc else None,
            "data_source_id": self.data_source_id,
            "status": self.status
        }

    def __str__(self) -> str:
        ts_str = self.timestamp_utc.strftime('%Y-%m-%d %H:%M:%S %Z') if self.timestamp_utc else "N/A"
        unit_str = f" {self.unit}" if self.unit else ""
        return f"{self.name}: {self.value}{unit_str} (Status: {self.status} @ {ts_str}, Source: {self.data_source_id or 'N/A'})"

class Asset:
    """Base class for all physical or logical assets in the digital twin."""
    def __init__(self,
                 asset_id: str,
                 asset_type: str,
                 depot_id: str,
                 description: Optional[str] = None,
                 area: Optional[str] = None,
                 product_service: Optional[str] = None,
                 allowed_products: Optional[List[str]] = None,
                 capacity_litres: Optional[float] = None,
                 density_at_20c_kg_m3: Optional[float] = None,
                 is_active: bool = True,
                 notes: Optional[str] = None,
                 maintenance_notes: Optional[str] = None,
                 **kwargs):
        self.asset_id: str = asset_id
        self.asset_type: str = asset_type
        self.depot_id: str = depot_id
        self.description: Optional[str] = description
        self.area: Optional[str] = area
        self.product_service: Optional[str] = product_service
        self.allowed_products: Optional[List[str]] = allowed_products if allowed_products is not None else []
        self.capacity_litres: Optional[float] = capacity_litres
        self.density_at_20c_kg_m3: Optional[float] = density_at_20c_kg_m3
        self.is_active: bool = is_active
        self.notes: Optional[str] = notes
        self.maintenance_notes: Optional[str] = maintenance_notes
        
        self.last_updated: Optional[datetime.datetime] = None

        self._additional_properties: Dict[str, Any] = kwargs
        for key, value in kwargs.items():
            if not hasattr(self, key):
                setattr(self, key, value)
            else:
                logger.debug(f"Skipping kwarg '{key}' for asset '{asset_id}': attribute already exists.")
        
        # Call update_last_modified upon initialization
        self.update_last_modified()


    def update_last_modified(self, timestamp: Optional[datetime.datetime] = None):
        if timestamp:
            if timestamp.tzinfo is None or timestamp.tzinfo.utcoffset(timestamp) is None:
                self.last_updated = timestamp.replace(tzinfo=datetime.timezone.utc)
            else:
                self.last_updated = timestamp.astimezone(datetime.timezone.utc)
        else:
            self.last_updated = datetime.datetime.now(datetime.timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the static and potentially some core dynamic state of the asset to a dictionary."""
        data = {
            "asset_id": self.asset_id,
            "asset_type": self.asset_type,
            "depot_id": self.depot_id,
            "description": self.description,
            "area": self.area,
            "product_service": self.product_service,
            "allowed_products": self.allowed_products,
            "capacity_litres": self.capacity_litres,
            "density_at_20c_kg_m3": self.density_at_20c_kg_m3,
            "is_active": self.is_active,
            "notes": self.notes,
            "maintenance_notes": self.maintenance_notes,
            "last_updated": self.last_updated.isoformat(timespec='seconds') if self.last_updated else None
        }
        data.update(self._additional_properties)
        
        return data

    def __str__(self) -> str:
        return f"{self.asset_type} - {self.asset_id} ({self.description or 'No description'})"