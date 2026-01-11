# File: fuel_depot_digital_twin/processing_service.py
import paho.mqtt.client as mqtt
import ssl
import json
import datetime
import time
import signal
import logging
from typing import Dict, Any, Optional, List
from contextlib import contextmanager

# Pydantic for MQTT payload validation
from pydantic import BaseModel, field_validator, ValidationError

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from config import settings
from core.models import (
    Asset, StorageTank, Meter, LoadingArm, Pump, Pipeline, PumpHouse, GantryRack
)
from data import database
from config.asset_loader import load_assets_from_db
from data.strapping_loader import preload_all_strapping_tables
from utils.helpers import setup_main_logging, parse_iso_datetime
from core.calculations import calculate_precise_gsv

# --- Setup Logging ---
setup_main_logging()
logger = logging.getLogger(__name__)

# --- Global State ---
digital_twin_state: Dict[str, Any] = {}
mqtt_client: Optional[mqtt.Client] = None
shutdown_flag = False
ALERT_RULES: Dict[str, List[Dict[str, Any]]] = {} # Populated from DB at startup
potential_alerts_tracker: Dict[str, Dict[str, Any]] = {}

# --- Pydantic Model for MQTT Payloads ---
class BaseMqttPayload(BaseModel):
    value: Any
    timestamp_utc: datetime.datetime
    unit: Optional[str] = None
    status: Optional[str] = "OK"

    @field_validator('timestamp_utc', mode='before')
    @classmethod
    def validate_timestamp_str_to_datetime(cls, v_value):
        if isinstance(v_value, str):
            dt = parse_iso_datetime(v_value)
            if dt is None:
                raise ValueError("Invalid timestamp_utc string format. Expected ISO 8601.")
            return dt
        if isinstance(v_value, datetime.datetime):
            if v_value.tzinfo is None:
                return v_value.replace(tzinfo=datetime.timezone.utc)
            return v_value.astimezone(datetime.timezone.utc)
        if v_value is None:
            raise ValueError("timestamp_utc cannot be null in MQTT payload.")
        raise TypeError("timestamp_utc must be a string or datetime object.")

@contextmanager
def db_session_scope() -> Session:
    session = None
    if not database.SessionLocal:
        logger.critical("Database SessionLocal is not initialized! Cannot create session.")
        raise RuntimeError("Database session factory (SessionLocal) is not initialized.")
    
    session = database.SessionLocal()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as e:
        logger.error(f"Database transaction (SQLAlchemyError) failed: {e}", exc_info=True)
        if session: session.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error during database session: {e}", exc_info=True)
        if session: session.rollback()
        raise
    finally:
        if session:
            session.close()

def signal_handler(signum, frame):
    global shutdown_flag
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_flag = True

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("MQTT: Connected successfully to broker!")
        client.subscribe(f"{settings.MQTT_BASE_TOPIC}/#", qos=1)
    else:
        logger.error(f"MQTT: Connection failed with code {rc}.")

def on_disconnect(client, userdata, rc):
    logger.warning(f"MQTT: Disconnected (rc: {rc}). Will attempt to reconnect.")

def get_asset_metric_value(asset_obj: Any, metric_name: str) -> Optional[Any]:
    try:
        if hasattr(asset_obj, metric_name):
            attr = getattr(asset_obj, metric_name)
            if hasattr(attr, 'value'):
                return attr.value
        dp_attr_name = None
        if isinstance(asset_obj, StorageTank):
            if metric_name == "level_percentage": dp_attr_name = "current_level_percentage"
            elif metric_name == "temperature": dp_attr_name = "current_temperature"
        elif isinstance(asset_obj, Pump):
            if metric_name == "power": dp_attr_name = "current_power"
            elif metric_name == "vibration": dp_attr_name = "current_vibration"
            elif metric_name == "state": dp_attr_name = "status"
        elif isinstance(asset_obj, Meter):
            if metric_name == "flow_rate": dp_attr_name = "flow_rate_lpm"
        
        if dp_attr_name and hasattr(asset_obj, dp_attr_name):
            attr = getattr(asset_obj, dp_attr_name)
            if hasattr(attr, 'value'):
                return attr.value
        logger.debug(f"Metric '{metric_name}' structure not directly found on {asset_obj.asset_id}")
    except Exception as e:
        logger.error(f"Error getting metric '{metric_name}' for {asset_obj.asset_id}: {e}", exc_info=True)
    return None

def check_and_process_asset_alerts(db_session: Session, asset_id: str, asset_obj: Any):
    asset_type = type(asset_obj).__name__
    if asset_type not in ALERT_RULES:
        return

    logger.debug(f"Checking alerts for asset {asset_id} (type: {asset_type})")
    now_utc = datetime.datetime.now(datetime.timezone.utc)

    for rule in ALERT_RULES.get(asset_type, []):
        rule_metric = rule.get("metric")
        alert_name = rule["alert_name"]
        alert_key = f"{asset_id}_{alert_name}"
        current_value = None

        if rule_metric:
            current_value = get_asset_metric_value(asset_obj, rule_metric)

        if rule_metric and current_value is None:
            if alert_key in potential_alerts_tracker:
                if potential_alerts_tracker[alert_key].get('notified_active'):
                    database.resolve_alerts_for_condition(db_session, asset_id, alert_name)
                del potential_alerts_tracker[alert_key]
            else:
                database.resolve_alerts_for_condition(db_session, asset_id, alert_name)
            continue

        is_primary_trigger_condition_met = False
        if rule_metric and current_value is not None:
            try:
                threshold = rule["threshold"]
                condition = rule["condition"]
                val_for_comparison = float(current_value) if isinstance(current_value, (int, float, str)) else current_value
                
                if isinstance(val_for_comparison, float):
                    if condition == "gt" and val_for_comparison > threshold: is_primary_trigger_condition_met = True
                    elif condition == "lt" and val_for_comparison < threshold: is_primary_trigger_condition_met = True
                    elif condition == "gte" and val_for_comparison >= threshold: is_primary_trigger_condition_met = True
                    elif condition == "lte" and val_for_comparison <= threshold: is_primary_trigger_condition_met = True
                if condition == "eq" and str(val_for_comparison) == str(threshold): is_primary_trigger_condition_met = True
                elif condition == "ne" and str(val_for_comparison) != str(threshold): is_primary_trigger_condition_met = True
            except (TypeError, ValueError, KeyError) as e_cmp:
                logger.warning(f"Comparison error for rule '{alert_name}' on {asset_id}: {e_cmp}")
                is_primary_trigger_condition_met = False

        duration_seconds = rule.get("duration_seconds")
        clear_threshold = rule.get("clear_threshold")

        if is_primary_trigger_condition_met:
            if duration_seconds is not None:
                if alert_key not in potential_alerts_tracker:
                    potential_alerts_tracker[alert_key] = {'first_seen_utc': now_utc, 'notified_active': False, 'last_value': current_value}
                elif not potential_alerts_tracker[alert_key]['notified_active']:
                    elapsed_time = now_utc - potential_alerts_tracker[alert_key]['first_seen_utc']
                    if elapsed_time.total_seconds() >= duration_seconds:
                        database.save_alert(db_session, asset_id, alert_name, rule["message_template"].format(asset_id=asset_id, value=current_value, threshold=rule.get("threshold")), rule.get("severity", "Warning"), details={"metric": rule_metric, "value": current_value})
                        potential_alerts_tracker[alert_key]['notified_active'] = True
            else:
                database.save_alert(db_session, asset_id, alert_name, rule["message_template"].format(asset_id=asset_id, value=current_value, threshold=rule.get("threshold")), rule.get("severity", "Warning"), details={"metric": rule_metric, "value": current_value})
        else:
            should_resolve = False
            if clear_threshold is not None and isinstance(current_value, (int, float)):
                original_condition = rule["condition"]
                if original_condition in ["gt", "gte"] and current_value < clear_threshold: should_resolve = True
                elif original_condition in ["lt", "lte"] and current_value > clear_threshold: should_resolve = True
            else:
                should_resolve = True

            if should_resolve:
                if alert_key in potential_alerts_tracker:
                    if potential_alerts_tracker[alert_key]['notified_active']:
                        database.resolve_alerts_for_condition(db_session, asset_id, alert_name)
                    del potential_alerts_tracker[alert_key]
                else:
                    database.resolve_alerts_for_condition(db_session, asset_id, alert_name)

def process_message_type(asset_id: str, metric: str, validated_payload: BaseMqttPayload, data_type_str: str, original_topic: str):
    if asset_id not in digital_twin_state:
        logger.warning(f"Received {data_type_str} for unknown asset: {asset_id} from topic {original_topic}")
        return

    asset = digital_twin_state[asset_id]
    value = validated_payload.value
    timestamp_utc = validated_payload.timestamp_utc
    unit = validated_payload.unit
    status_from_payload = validated_payload.status
    
    updated_in_memory = False
    
    try:
        if isinstance(asset, StorageTank):
            if metric == 'level':
                asset.update_iot_level(float(value), timestamp_utc, status_from_payload)
                updated_in_memory = True
            elif metric == 'temperature':
                asset.update_temperature(float(value), timestamp_utc, status_from_payload)
                updated_in_memory = True
            else: logger.warning(f"Unknown metric '{metric}' for StorageTank {asset_id}"); return
        
        # (Add elif for other asset types as needed)

        if updated_in_memory:
            logger.info(f"In-memory state updated: {asset_id}/{metric} -> {value}")
            with db_session_scope() as db:
                database.save_sensor_reading(db, timestamp_utc, asset_id, f"MQTT_{data_type_str}", metric, value, unit, status_from_payload)
                
                if isinstance(asset, StorageTank) and (metric == 'level' or metric == 'temperature'):
                    if (asset.current_volume_litres and asset.current_volume_litres.value is not None and
                        asset.current_temperature and asset.current_temperature.value is not None and
                        hasattr(asset, 'density_at_20c_kg_m3') and asset.density_at_20c_kg_m3 is not None):
                        
                        gov = asset.current_volume_litres.value
                        obs_temp = asset.current_temperature.value
                        density20c = asset.density_at_20c_kg_m3 # Use the 20C density attribute
                        
                        gsv = calculate_precise_gsv(
                            observed_volume=gov, 
                            observed_temperature_c=obs_temp, 
                            density_at_20c=density20c
                        )
                        if gsv is not None:
                            asset.update_gsv(gsv, timestamp_utc)
                            gsv_unit = f"Liters@{int(settings.STANDARD_REFERENCE_TEMPERATURE_CELSIUS)}C"
                            database.save_calculated_data(db, timestamp_utc, asset_id, "gsv_litres_precise", gsv, gsv_unit, "OK")
                            logger.info(f"Calculated and saved GSV for {asset_id}: {gsv:.2f} {gsv_unit}")

                check_and_process_asset_alerts(db, asset_id, asset)
    except Exception as e:
        logger.error(f"Error processing message for {asset_id}/{metric}: {e}", exc_info=True)

def on_message(client, userdata, msg):
    topic = msg.topic
    try:
        payload_str = msg.payload.decode('utf-8')
        payload_dict = json.loads(payload_str)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        logger.error(f"Error decoding payload from topic '{topic}': {e}")
        return

    try:
        validated_payload = BaseMqttPayload(**payload_dict)
    except ValidationError as e_val:
        logger.error(f"MQTT Payload Validation Error for topic '{topic}': {e_val.errors()}")
        return

    try:
        remaining_parts = topic.split(f"{settings.MQTT_BASE_TOPIC}/")[1].split('/')
        if len(remaining_parts) < 4:
            logger.warning(f"Topic structure insufficient: {topic}")
            return
        data_type, asset_id, metric = remaining_parts[0], remaining_parts[2], remaining_parts[3]
        
        process_message_type(asset_id, metric, validated_payload, data_type, topic)
    except Exception as e:
        logger.error(f"Error parsing topic or processing message for topic '{topic}': {e}", exc_info=True)


if __name__ == "__main__":
    logger.info("Starting Fuel Depot Digital Twin Processing Service...")
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # REMOVED: global ALERT_RULES - it is not needed here.
    
    try:
        with db_session_scope() as db:
            logger.info("Database session test successful.")
            
            logger.info("Loading asset configurations from database...")
            digital_twin_state = load_assets_from_db()
            if not digital_twin_state:
                logger.warning("Asset loading returned empty.")
            else:
                logger.info(f"Loaded {len(digital_twin_state)} assets.")

            if hasattr(database, 'load_alert_rules_from_db'):
                logger.info("Loading alert rules from database...")
                ALERT_RULES = database.load_alert_rules_from_db(db) # This directly modifies the global ALERT_RULES
                if not ALERT_RULES:
                    logger.warning("Alert rules loading returned empty.")
    except Exception as e_startup:
        logger.critical(f"FATAL: Startup database error: {e_startup}", exc_info=True)
        exit(1)

    if tank_ids := [aid for aid, asset in digital_twin_state.items() if isinstance(asset, StorageTank)]:
        logger.info(f"Preloading strapping tables for {len(tank_ids)} tanks...")
        preload_all_strapping_tables(tank_ids)
    
    mqtt_client = mqtt.Client(client_id=settings.MQTT_CLIENT_ID_PROCESSOR)
    
    # Configure TLS if enabled
    if settings.MQTT_USE_TLS:
        mqtt_client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS)
        logger.info("MQTT TLS enabled")
    
    # Configure authentication if credentials provided
    if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
        mqtt_client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
        logger.info("MQTT authentication configured")
    
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.on_disconnect = on_disconnect
    
    try:
        mqtt_client.connect(settings.MQTT_BROKER_ADDRESS, settings.MQTT_BROKER_PORT, 60)
        mqtt_client.loop_start()
    except Exception as e_mqtt:
        logger.critical(f"FATAL: MQTT Connection Error: {e_mqtt}", exc_info=True)
        exit(1)

    logger.info("Processing service running. Waiting for messages or shutdown signal...")
    try:
        while not shutdown_flag:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Shutting down...")
    finally:
        shutdown_flag = True
        logger.info("Shutdown sequence initiated...")
        if mqtt_client:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
        logger.info("Processing service has stopped.")