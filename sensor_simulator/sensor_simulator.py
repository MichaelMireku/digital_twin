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
        
        # Initialize tank states
        self.asset_states = {
            asset['asset_id']: {
                'level_mm': random.uniform(1000, 15000),
                'temperature': random.uniform(25.0, 35.0),
                'level_direction': random.choice([1, -1])
            }
            for asset in self.assets if asset.get('asset_type') == 'StorageTank'
        }
        
        # Initialize pump states (simulates realistic on/off patterns)
        for asset in self.assets:
            if asset.get('asset_type') == 'Pump':
                motor_power_kw = asset.get('motor_power_kw') or 55  # Default 55kW
                self.asset_states[asset['asset_id']] = {
                    'is_running': random.choice([True, False]),
                    'motor_power_kw': motor_power_kw,
                    'run_probability': 0.3,  # 30% chance to toggle state each cycle
                    'min_run_cycles': random.randint(3, 10),  # Min cycles before state change
                    'cycles_in_state': 0
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

    def simulate_pump_data(self, asset_id: str):
        """Generates and publishes data for a single pump (status and current draw)."""
        state = self.asset_states[asset_id]
        state['cycles_in_state'] += 1
        
        # Simulate realistic pump on/off patterns
        if state['cycles_in_state'] >= state['min_run_cycles']:
            if random.random() < state['run_probability']:
                state['is_running'] = not state['is_running']
                state['cycles_in_state'] = 0
                state['min_run_cycles'] = random.randint(3, 10)
        
        is_running = state['is_running']
        motor_power_kw = state['motor_power_kw']
        
        # Publish pump status (1 = running, 0 = stopped)
        status_payload = {
            "value": 1 if is_running else 0,
            "unit": "status",
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        status_topic = f"{settings.MQTT_BASE_TOPIC}/sensor/{asset_id}/pump_status/data"
        self.publish(status_topic, status_payload)
        
        # Publish motor current (amps) - calculated from power assuming 415V 3-phase
        # I = P / (√3 × V × PF × η) where PF≈0.85, η≈0.85
        if is_running:
            # Add some realistic variation (±5%)
            base_current = (motor_power_kw * 1000) / (1.732 * 415 * 0.85 * 0.85)
            current_amps = base_current * random.uniform(0.95, 1.05)
        else:
            current_amps = 0.0
        
        current_payload = {
            "value": round(current_amps, 2),
            "unit": "A",
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        current_topic = f"{settings.MQTT_BASE_TOPIC}/sensor/{asset_id}/motor_current/data"
        self.publish(current_topic, current_payload)

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
                asset_type = asset.get('asset_type')
                
                if asset_type == 'StorageTank':
                    self.simulate_tank_data(asset_id)
                elif asset_type == 'Pump':
                    self.simulate_pump_data(asset_id)
            
            time.sleep(settings.SIMULATION_INTERVAL_SECONDS)

def main():
    """Entry point for the sensor simulator with robust cross-platform connection handling."""
    logger.info("Starting Sensor Simulator service...")
    logger.info("Attempting to connect to cross-platform database (Railway -> Render)...")
    
    max_retries = 10
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Database connection attempt {attempt + 1}/{max_retries}...")
            
            with database.get_db() as db:
                if not db:
                    raise Exception("Could not get a database session")
                
                # Fetch assets from the database to simulate
                logger.info("Fetching assets from database...")
                assets_to_simulate, total = database.get_all_asset_metadata_paginated(db, per_page=1000)
            
            if not assets_to_simulate:
                logger.warning("No assets found in the database. Simulator will not run.")
                logger.info("Please ensure assets are populated in the database.")
                return

            logger.info(f"Successfully loaded {len(assets_to_simulate)} assets from database")
            logger.info("Starting simulation loop...")
            
            simulator = SensorSimulator(assets_to_simulate)
            simulator.run()
            break  # Success, exit retry loop
            
        except Exception as e:
            attempt_num = attempt + 1
            if attempt_num < max_retries:
                wait_time = min(retry_delay * (2 ** attempt), 120)  # Exponential backoff, max 2 minutes
                logger.warning(f"Database connection failed (attempt {attempt_num}/{max_retries}): {str(e)[:100]}")
                logger.info(f"Retrying in {wait_time}s... (This is normal for cross-platform connections)")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to connect to database after {max_retries} attempts")
                logger.error(f"Last error: {e}")
                logger.info("Possible causes:")
                logger.info("  1. Network connectivity issues between Railway and Render")
                logger.info("  2. Database connection limit reached")
                logger.info("  3. Database server temporarily unavailable")
                logger.info("  4. SSL/TLS handshake failures")
                logger.info("Simulator will exit. It will retry on next deployment.")
                return

if __name__ == "__main__":
    main()