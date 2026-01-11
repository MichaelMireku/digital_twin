# sensor_simulator/sensor_simulator.py

import os
import sys
import json
import time
import random
import logging
import datetime
from typing import List, Dict, Any

# --- ROBUST PATH SETUP ---
try:
    # Get the absolute path of the directory containing this script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to the project root
    project_root = os.path.dirname(current_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from config import settings
    from data import database
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import core modules: {e}")
    sys.exit(1)

import paho.mqtt.client as mqtt
import ssl

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SensorSimulator")

class SensorSimulator:
    """
    Simulates sensor data for various assets and publishes it to an MQTT broker.
    """
    def __init__(self, assets: List[Dict[str, Any]]):
        self.client = mqtt.Client()
        
        # Configure TLS if enabled
        if settings.MQTT_USE_TLS:
            self.client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS)
            logger.info("MQTT TLS enabled")
        
        # Configure authentication if credentials provided
        if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
            self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
            logger.info("MQTT authentication configured")
        
        self.assets = assets
        self.asset_states = {
            asset['asset_id']: {
                'level_mm': random.uniform(1000, 15000),  # Initial random level
                'temperature': random.uniform(25.0, 35.0), # Initial random temp
                'level_direction': random.choice([1, -1])
            }
            for asset in self.assets if asset.get('asset_type') == 'StorageTank'
        }
        logger.info(f"Simulator initialized with {len(self.assets)} assets.")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Successfully connected to MQTT Broker at {settings.MQTT_BROKER_ADDRESS}")
        else:
            logger.error(f"Failed to connect to MQTT Broker, return code {rc}")

    def connect(self):
        """Connects to the MQTT broker."""
        self.client.on_connect = self.on_connect
        self.client.connect(settings.MQTT_BROKER_ADDRESS, settings.MQTT_BROKER_PORT, 60)
        self.client.loop_start()

    def simulate_tank_data(self, asset_id: str):
        """Generates and publishes data for a single storage tank."""
        state = self.asset_states[asset_id]

        # Simulate level change
        state['level_mm'] += state['level_direction'] * random.uniform(10, 50)
        if state['level_mm'] > 18000:
            state['level_mm'] = 18000
            state['level_direction'] = -1
        elif state['level_mm'] < 1000:
            state['level_mm'] = 1000
            state['level_direction'] = 1

        # Simulate temperature fluctuation
        state['temperature'] += random.uniform(-0.1, 0.1)
        if state['temperature'] > 40.0: state['temperature'] = 40.0
        if state['temperature'] < 20.0: state['temperature'] = 20.0

        # Publish Level Data
        level_payload = {
            "value": round(state['level_mm'], 2),
            "unit": "mm",
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        level_topic = f"{settings.MQTT_BASE_TOPIC}/sensor/{asset_id}/level_mm/data"
        self.publish(level_topic, level_payload)

        # Publish Temperature Data
        temp_payload = {
            "value": round(state['temperature'], 2),
            "unit": "C",
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        temp_topic = f"{settings.MQTT_BASE_TOPIC}/sensor/{asset_id}/temperature/data"
        self.publish(temp_topic, temp_payload)

    def publish(self, topic: str, payload: Dict[str, Any]):
        """Publishes a JSON payload to a specific MQTT topic."""
        try:
            self.client.publish(topic, json.dumps(payload))
            logger.info(f"Published to {topic}: {payload}")
        except Exception as e:
            logger.error(f"Failed to publish to topic {topic}: {e}")

    def run(self):
        """Runs the main simulation loop."""
        self.connect()
        while True:
            for asset in self.assets:
                asset_id = asset['asset_id']
                if asset.get('asset_type') == 'StorageTank':
                    self.simulate_tank_data(asset_id)
            
            time.sleep(settings.SIMULATION_INTERVAL_SECONDS)

def main():
    """Entry point for the sensor simulator."""
    logger.info("Starting Sensor Simulator service...")
    
    with database.get_db() as db:
        if not db:
            logger.critical("Could not get a database session. Exiting.")
            return
        
        # Fetch assets from the database to simulate
        assets_to_simulate, _ = database.get_all_asset_metadata_paginated(db, per_page=1000)

    if not assets_to_simulate:
        logger.warning("No assets found in the database. Simulator will not run.")
        return

    simulator = SensorSimulator(assets_to_simulate)
    simulator.run()

if __name__ == "__main__":
    main()