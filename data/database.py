import datetime
import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
from decimal import Decimal

from sqlalchemy import create_engine, select, update, desc, text, func, union_all
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from config import settings
from data.db_models import Base, Asset, SensorReading, CalculatedData, AlertConfiguration, OperationLog, StrappingData, Alert
from utils.helpers import parse_iso_datetime

logger = logging.getLogger(__name__)

try:
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("Database engine created successfully and SessionLocal configured.")
except Exception as e:
    logger.critical(f"CRITICAL: Failed to create database engine or SessionLocal: {e}", exc_info=True)
    engine = None
    SessionLocal = None

@contextmanager
def get_db() -> Optional[Session]:
    """Provide a transactional scope around a series of operations."""
    if not SessionLocal:
        logger.error("Database SessionLocal is not initialized. Cannot provide DB session.")
        yield None
        return

    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        logger.error(f"Database Session Error during yield: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()

def save_sensor_reading(db: Session, time: datetime.datetime, asset_id: str, data_source_id: str,
                       metric_name: str, value: Any, unit: Optional[str], status: str) -> bool:
    if not db: return False
    try:
        value_numeric = float(value) if isinstance(value, (int, float)) else None
        value_text = str(value) if not isinstance(value, (int, float)) else None
        if isinstance(time, str):
            time = parse_iso_datetime(time)
        if time.tzinfo is None:
            time = time.replace(tzinfo=datetime.timezone.utc)

        reading = SensorReading(
            time=time, asset_id=asset_id, data_source_id=data_source_id,
            metric_name=metric_name, value_numeric=value_numeric,
            value_text=value_text, unit=unit, status=status
        )
        db.add(reading)
        db.commit()
        return True
    except SQLAlchemyError as e:
        logger.error(f"DB Error saving sensor reading for {data_source_id}, metric {metric_name}: {e}", exc_info=True)
        db.rollback()
        return False

def save_calculated_data(db: Session, time: datetime.datetime, asset_id: str, metric_name: str,
                         value: float, unit: Optional[str], calculation_status: str) -> bool:
    """Saves (or updates) a single calculated data point to the database."""
    if not db: return False
    try:
        if isinstance(time, str):
            parsed_time = parse_iso_datetime(time)
            if not parsed_time:
                logger.error(f"Could not parse timestamp string: {time}")
                return False
            time = parsed_time
        
        if time.tzinfo is None:
            time = time.replace(tzinfo=datetime.timezone.utc)
            
        calc_data = CalculatedData(
            time=time, asset_id=asset_id, metric_name=metric_name,
            value=value, unit=unit, calculation_status=calculation_status
        )
        db.merge(calc_data)
        db.commit()
        return True
    except SQLAlchemyError as e:
        logger.error(f"DB Error saving calculated data for {asset_id}, metric {metric_name}: {e}", exc_info=True)
        db.rollback()
        return False

def get_all_asset_metadata_paginated(db: Session, page: int = 1, per_page: int = 100) -> Tuple[List[Dict[str, Any]], int]:
    if not db: return [], 0
    try:
        offset = (page - 1) * per_page
        total = db.execute(select(func.count(Asset.asset_id))).scalar_one()
        query = select(Asset).order_by(Asset.asset_id).limit(per_page).offset(offset)
        results = db.execute(query).scalars().all()
        return [asset.to_dict() for asset in results], total
    except SQLAlchemyError as e:
        logger.error(f"DB Error getting all asset metadata: {e}", exc_info=True)
        return [], 0

def get_asset_metadata(db: Session, asset_id: str) -> Optional[Dict[str, Any]]:
    if not db: return None
    try:
        result = db.execute(select(Asset).where(Asset.asset_id == asset_id)).scalar_one_or_none()
        return result.to_dict() if result else None
    except SQLAlchemyError as e:
        logger.error(f"DB Error getting asset metadata for {asset_id}: {e}", exc_info=True)
        return None

def get_latest_sensor_reading(db: Session, asset_id: str, metric_name: str) -> Optional[Dict[str, Any]]:
    if not db: return None
    try:
        result = db.execute(select(SensorReading).where(SensorReading.asset_id == asset_id, SensorReading.metric_name == metric_name).order_by(SensorReading.time.desc()).limit(1)).scalar_one_or_none()
        return result.to_dict() if result else None
    except SQLAlchemyError as e:
        logger.error(f"DB Error getting latest sensor reading for {asset_id}/{metric_name}: {e}", exc_info=True)
        return None

def get_latest_calculated_data(db: Session, asset_id: str, metric_name: str) -> Optional[Dict[str, Any]]:
    if not db: return None
    try:
        result = db.execute(select(CalculatedData).where(CalculatedData.asset_id == asset_id, CalculatedData.metric_name == metric_name).order_by(CalculatedData.time.desc()).limit(1)).scalar_one_or_none()
        return result.to_dict() if result else None
    except SQLAlchemyError as e:
        logger.error(f"DB Error getting latest calculated data for {asset_id}/{metric_name}: {e}", exc_info=True)
        return None

def get_latest_readings_for_asset(db: Session, asset_id: str, metrics_config: Dict[str, str]) -> Dict[str, Any]:
    latest_data = {}
    if not db: return latest_data
    for metric, source_type in metrics_config.items():
        reading = None
        if source_type == 'sensor':
            reading = get_latest_sensor_reading(db, asset_id, metric)
        elif source_type == 'calculated':
            reading = get_latest_calculated_data(db, asset_id, metric)
        latest_data[metric] = reading
    return latest_data

def get_metric_history(db: Session, asset_id: str, metric_name: str, source_type: str = 'all',
                       start_time: Optional[datetime.datetime] = None,
                       end_time: Optional[datetime.datetime] = None,
                       limit: int = 1000) -> List[Dict[str, Any]]:
    if not db: return []
    all_results = []
    try:
        if source_type in ['all', 'sensor']:
            sensor_query = select(SensorReading).where(SensorReading.asset_id == asset_id, SensorReading.metric_name == metric_name)
            if start_time: sensor_query = sensor_query.where(SensorReading.time >= start_time)
            if end_time: sensor_query = sensor_query.where(SensorReading.time <= end_time)
            sensor_results = db.execute(sensor_query.order_by(desc(SensorReading.time)).limit(limit)).scalars().all()
            for res in sensor_results: all_results.append(res.to_dict())
        if source_type in ['all', 'calculated']:
            calc_query = select(CalculatedData).where(CalculatedData.asset_id == asset_id, CalculatedData.metric_name == metric_name)
            if start_time: calc_query = calc_query.where(CalculatedData.time >= start_time)
            if end_time: calc_query = calc_query.where(CalculatedData.time <= end_time)
            calc_results = db.execute(calc_query.order_by(desc(CalculatedData.time)).limit(limit)).scalars().all()
            for res in calc_results: all_results.append(res.to_dict())
        all_results.sort(key=lambda x: x['time'], reverse=True)
        return all_results[:limit]
    except SQLAlchemyError as e:
        logger.error(f"DB Error getting metric history for {asset_id}/{metric_name}: {e}", exc_info=True)
        return []

def save_operation_log(db: Session, event_type: str, description: str,
                       user_name: Optional[str] = None,
                       related_asset_id: Optional[str] = None,
                       details: Optional[Dict[str, Any]] = None) -> bool:
    if not db: return False
    try:
        log_entry = OperationLog(
            user_name=user_name, event_type=event_type, description=description,
            related_asset_id=related_asset_id, details=details
        )
        db.add(log_entry)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error saving operation log event: {e}", exc_info=True)
        db.rollback()
        return False

def get_operation_logs(db: Session, limit: int = 50) -> List[Dict[str, Any]]:
    if not db: return []
    try:
        logs = db.query(OperationLog).order_by(OperationLog.timestamp.desc()).limit(limit).all()
        return [log.to_dict() for log in logs]
    except Exception as e:
        logger.error(f"Error fetching operation logs: {e}", exc_info=True)
        return []

# --- NEW: Alerting Functions ---
def save_alert(db: Session, asset_id: str, alert_name: str, message: str,
               severity: str = "Warning", status: str = "Active", details: Optional[Dict[str, Any]] = None) -> Optional[int]:
    """Saves a new alert, preventing duplicates for the same active condition."""
    if not db:
        logger.error("No database session provided to save_alert.")
        return None
    try:
        # Check if an identical active alert already exists
        existing_alert = db.query(Alert).filter_by(asset_id=asset_id, alert_name=alert_name, status='Active').first()
        if existing_alert:
            logger.debug(f"Active alert '{alert_name}' for asset '{asset_id}' already exists.")
            return existing_alert.alert_id

        # If not, create a new one
        new_alert = Alert(
            asset_id=asset_id,
            alert_name=alert_name,
            message=message,
            severity=severity,
            status=status,
            details=details
        )
        db.add(new_alert)
        db.commit()
        logger.info(f"New alert '{alert_name}' for asset '{asset_id}' saved.")
        return new_alert.alert_id
    except Exception as e:
        logger.error(f"Error saving alert for asset {asset_id}, alert {alert_name}: {e}", exc_info=True)
        db.rollback()
        return None

def resolve_alerts_for_condition(db: Session, asset_id: str, alert_name: str) -> int:
    """Resolves all active alerts for a specific condition on a specific asset."""
    if not db: return 0
    try:
        updated_rows = db.query(Alert).filter_by(asset_id=asset_id, alert_name=alert_name, status='Active').update({
            'status': 'Resolved',
            'resolved_at': datetime.datetime.now(datetime.timezone.utc)
        })
        db.commit()
        if updated_rows > 0:
            logger.info(f"Resolved {updated_rows} active alert(s) for '{alert_name}' on asset '{asset_id}'.")
        return updated_rows
    except Exception as e:
        logger.error(f"Error resolving alerts for {asset_id}, alert {alert_name}: {e}", exc_info=True)
        db.rollback()
        return 0

def get_active_alerts(db: Session, limit: int = 100) -> List[Dict[str, Any]]:
    if not db: return []
    try:
        alerts = db.query(Alert).filter_by(status='Active').order_by(desc(Alert.triggered_at)).limit(limit).all()
        return [alert.to_dict() for alert in alerts]
    except Exception as e:
        logger.error(f"Error fetching active alerts: {e}", exc_info=True)
        return []
        
def load_alert_rules_from_db(db: Session) -> Dict[str, List[Dict[str, Any]]]:
    loaded_rules: Dict[str, List[Dict[str, Any]]] = {}
    if not db: return loaded_rules
    try:
        db_rules = db.query(AlertConfiguration).filter(AlertConfiguration.is_enabled == True).all()
        for db_rule in db_rules:
            rule_dict = db_rule.to_rule_dict()
            asset_type_key = db_rule.asset_type
            if asset_type_key not in loaded_rules:
                loaded_rules[asset_type_key] = []
            loaded_rules[asset_type_key].append(rule_dict)
        logger.info(f"Loaded {sum(len(v) for v in loaded_rules.values())} alert rules from DB.")
        return loaded_rules
    except Exception as e:
        logger.error(f"Error loading alert rules: {e}", exc_info=True)
        return {}

def get_strapping_data_from_db(db: Session, asset_id: str) -> Optional[Dict[int, float]]:
    if not db: return None
    try:
        results = db.query(StrappingData).filter(StrappingData.asset_id == asset_id).order_by(StrappingData.level_mm).all()
        if not results: return None
        return {int(row.level_mm): float(row.volume_litres) for row in results}
    except SQLAlchemyError as e:
        logger.error(f"DB Error getting strapping data for {asset_id}: {e}", exc_info=True)
        return None
