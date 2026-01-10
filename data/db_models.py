import datetime
import json
from sqlalchemy import (
    Column, String, Float, Boolean, Text, ARRAY, Numeric, Index, func, Integer, JSON, ForeignKey, TIMESTAMP
)
from sqlalchemy.orm import declarative_base
from typing import Dict, Any

# Base class for all ORM models
Base = declarative_base()

class Asset(Base):
    __tablename__ = 'assets'
    asset_id = Column(String(50), primary_key=True)
    asset_type = Column(String(50), nullable=False, index=True)
    depot_id = Column(String(20), default='DEMO_DEPOT_01')
    description = Column(String(255))
    area = Column(String(10), index=True)
    pump_house_id = Column(String(50), index=True)
    gantry_rack_id = Column(String(50), index=True)
    side = Column(String(50))
    product_service = Column(String(50), index=True)
    allowed_products = Column(ARRAY(Text))
    usage_type = Column(String(50))
    capacity_litres = Column(Numeric)
    density_at_20c_kg_m3 = Column(Numeric)
    source_system = Column(String(50))
    rented_to = Column(String(100))
    connected_meter_id = Column(String(50))
    pump_service_description = Column(String(255))
    pipeline_source = Column(String(100))
    pipeline_destination = Column(String(100))
    pipeline_size_inches = Column(Numeric)
    pipeline_length_km = Column(Numeric)
    is_active = Column(Boolean, default=True)
    maintenance_notes = Column(Text)
    notes = Column(Text)
    foam_system_present = Column(Boolean, default=False)
    high_level_threshold_m = Column(Numeric)
    low_level_threshold_m = Column(Numeric)
    high_high_level_threshold_m = Column(Numeric)
    low_low_level_threshold_m = Column(Numeric)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    last_updated = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class SensorReading(Base):
    __tablename__ = 'sensor_readings'
    time = Column(TIMESTAMP(timezone=True), primary_key=True, nullable=False, server_default=func.now())
    asset_id = Column(String(50), primary_key=True, nullable=False, index=True)
    data_source_id = Column(String(100), primary_key=True, nullable=False, index=True)
    metric_name = Column(String(50), primary_key=True, nullable=False, index=True)
    value_numeric = Column(Float)
    value_text = Column(Text)
    unit = Column(String(20))
    status = Column(String(50), default='OK')

    def to_dict(self):
         return {
             "time": self.time.isoformat() if self.time else None, "asset_id": self.asset_id,
             "data_source_id": self.data_source_id, "metric_name": self.metric_name,
             "value": self.value_numeric if self.value_numeric is not None else self.value_text,
             "unit": self.unit, "status": self.status
         }

class CalculatedData(Base):
    __tablename__ = 'calculated_data'
    time = Column(TIMESTAMP(timezone=True), primary_key=True, nullable=False)
    asset_id = Column(String(50), primary_key=True, nullable=False, index=True)
    metric_name = Column(String(50), primary_key=True, nullable=False, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String(20))
    calculation_status = Column(String(50), default='OK')

    def to_dict(self):
        return {
            "time": self.time.isoformat() if self.time else None, "asset_id": self.asset_id,
            "metric_name": self.metric_name, "value": self.value, "unit": self.unit,
            "calculation_status": self.calculation_status
        }

class AlertConfiguration(Base):
    __tablename__ = 'alert_configurations'
    rule_id = Column(Integer, primary_key=True, autoincrement=True)
    asset_type = Column(String(50), nullable=False, index=True)
    metric_name = Column(String(50), nullable=False)
    condition_type = Column(String(10), nullable=False)
    threshold_value = Column(Numeric, nullable=False)
    clear_threshold_value = Column(Numeric, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    alert_name = Column(String(100), nullable=False, unique=True)
    message_template = Column(Text, nullable=False)
    severity = Column(String(20), default='Warning')
    is_enabled = Column(Boolean, default=True, index=True)
    description = Column(Text, nullable=True)

    def to_rule_dict(self) -> Dict[str, Any]:
        rule_data = {
            "metric": self.metric_name, "condition": self.condition_type,
            "threshold": float(self.threshold_value) if self.threshold_value is not None else None,
            "alert_name": self.alert_name, "message_template": self.message_template, "severity": self.severity
        }
        if self.clear_threshold_value is not None:
            rule_data["clear_threshold"] = float(self.clear_threshold_value)
        if self.duration_seconds is not None:
            rule_data["duration_seconds"] = self.duration_seconds
        return rule_data

class OperationLog(Base):
    __tablename__ = 'operation_logs'
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now())
    user_name = Column(String(100), nullable=True)
    event_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    related_asset_id = Column(String(50), nullable=True)
    details = Column(JSON, nullable=True)

    def to_dict(self):
        return {
            "log_id": self.log_id, "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user_name": self.user_name, "event_type": self.event_type, "description": self.description,
            "related_asset_id": self.related_asset_id, "details": self.details
        }

class StrappingData(Base):
    __tablename__ = 'strapping_data'
    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(String(50), ForeignKey('assets.asset_id'), nullable=False, index=True)
    level_mm = Column(Numeric, nullable=False)
    volume_litres = Column(Numeric, nullable=False)

# --- NEW: Alert Model ---
class Alert(Base):
    __tablename__ = 'alerts'
    alert_id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(String(50), ForeignKey('assets.asset_id'), nullable=False, index=True)
    alert_name = Column(String(100), nullable=False, index=True)
    message = Column(Text, nullable=False)
    severity = Column(String(20), default='Warning', index=True)
    status = Column(String(20), default='Active', index=True)
    details = Column(JSON, nullable=True)
    triggered_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    resolved_at = Column(TIMESTAMP(timezone=True), nullable=True)

    def to_dict(self):
        return {
            "alert_id": self.alert_id, "asset_id": self.asset_id, "alert_name": self.alert_name,
            "message": self.message, "severity": self.severity, "status": self.status,
            "details": self.details,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None
        }
