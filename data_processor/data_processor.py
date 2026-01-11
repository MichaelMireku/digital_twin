import os
import sys
import json
import time
import logging
import datetime
from typing import Dict, Any, Optional

# --- ROBUST PATH SETUP ---
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from config import settings
    from data import database
    from utils.helpers import parse_iso_datetime
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import core modules: {e}")
    sys.exit(1)

import paho.mqtt.client as mqtt
from pydantic import BaseModel, field_validator, ValidationError

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DataProcessor")

# --- Pydantic Model for MQTT Payload Validation ---
class SensorPayload(BaseModel):
    value: Any
    unit: Optional[str] = None
    status: str = "OK"
    timestamp_utc: datetime.datetime

    @field_validator('timestamp_utc', mode='before')
    @classmethod
    def validate_timestamp(cls, v):
        if isinstance(v, datetime.datetime):
            return v.astimezone(datetime.timezone.utc) if v.tzinfo else v.replace(tzinfo=datetime.timezone.utc)
        if isinstance(v, str):
            dt = parse_iso_datetime(v)
            if dt is None: raise ValueError("Invalid ISO 8601 timestamp format")
            return dt
        raise TypeError("Timestamp must be a valid ISO 8601 string or datetime object")

# --- MQTT Client Logic ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info(f"Successfully connected to MQTT Broker at {settings.MQTT_BROKER_ADDRESS}")
        topic = f"{settings.MQTT_BASE_TOPIC}/sensor/+/+/data"
        client.subscribe(topic)
        logger.info(f"Subscribed to topic: {topic}")
    else:
        logger.error(f"Failed to connect to MQTT Broker, return code {rc}")

def on_disconnect(client, userdata, rc):
    logger.warning(f"Disconnected from MQTT Broker. The client will attempt to reconnect automatically.")

def on_message(client, userdata, msg):
    """Callback for when a message is received from the broker."""
    topic = msg.topic
    payload_str = msg.payload.decode('utf-8')
    logger.debug(f"Received message on topic '{topic}': {payload_str}")

    try:
        # --- CORRECTED LOGIC ---
        # The topic format is: demo/depot/dev/sensor/{asset_id}/{metric_name}/data
        # This has exactly 7 parts.
        topic_parts = topic.split('/')
        if len(topic_parts) == 7 and topic_parts[3] == 'sensor':
            asset_id = topic_parts[4]
            metric_name = topic_parts[5]
            # We can create a unique data source ID for this sensor feed
            data_source_id = f"sensor_{asset_id}_{metric_name}"
        else:
            logger.warning(f"Topic structure is incorrect, cannot parse asset details: {topic}")
            return # Stop processing this message

        payload_json = json.loads(payload_str)
        sensor_data = SensorPayload(**payload_json)

        with database.get_db() as db_session:
            if not db_session:
                logger.error("Could not get a database session. Data not saved.")
                return

            success = database.save_sensor_reading(
                db=db_session,
                time=sensor_data.timestamp_utc,
                asset_id=asset_id,
                data_source_id=data_source_id,
                metric_name=metric_name,
                value=sensor_data.value,
                unit=sensor_data.unit,
                status=sensor_data.status
            )
            if success:
                logger.info(f"Successfully saved reading for {asset_id}/{metric_name}")
            else:
                logger.error(f"Failed to save reading for {asset_id}/{metric_name}")

    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON from payload: {payload_str}")
    except ValidationError as e:
        logger.error(f"Payload validation failed for topic {topic}: {e.errors()}")
    except Exception as e:
        logger.error(f"An unexpected error occurred in on_message: {e}", exc_info=True)


def main():
    """Main function to start the MQTT client and run indefinitely."""
    logger.info("Starting Data Processor service...")
    if not all([settings.MQTT_BROKER_ADDRESS, settings.MQTT_BROKER_PORT]):
        logger.critical("MQTT Broker configuration is missing. Exiting.")
        sys.exit(1)

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    while True:
        try:
            logger.info(f"Attempting to connect to MQTT broker at {settings.MQTT_BROKER_ADDRESS}:{settings.MQTT_BROKER_PORT}...")
            client.connect(settings.MQTT_BROKER_ADDRESS, settings.MQTT_BROKER_PORT, 60)
            client.loop_forever()
        except Exception as e:
            logger.critical(f"Unhandled exception in connection loop: {e}. Retrying in 15 seconds...", exc_info=True)
            time.sleep(15)

if __name__ == "__main__":
    main()