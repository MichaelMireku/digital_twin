# fuel_depot_digital_twin/alerting_service/alerting_service.py

import os
import sys
import time
import logging
from typing import Dict, Any, List

# --- ROBUST PATH SETUP ---
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from config import settings
    from data import database
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import core modules: {e}")
    sys.exit(1)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AlertingService")

class AlertingService:
    """
    Monitors asset data against configured rules and generates or resolves alerts.
    """
    def __init__(self, interval_seconds: int = 20):
        self.interval = interval_seconds
        self.alert_rules: Dict[str, List[Dict[str, Any]]] = {}
        logger.info(f"Alerting Service initialized. Run interval: {self.interval} seconds.")

    def load_rules(self, db_session):
        """Loads all enabled alert rules from the database."""
        self.alert_rules = database.load_alert_rules_from_db(db_session)
        logger.info(f"Successfully loaded {sum(len(v) for v in self.alert_rules.values())} alert rules.")

    def run_cycle(self):
        """Executes one full cycle of checking alerts."""
        logger.info("--- Starting new alerting cycle ---")
        with database.get_db() as db:
            if not db:
                logger.error("Could not get DB session. Skipping cycle.")
                return

            # Load the latest rules at the start of each cycle
            self.load_rules(db)
            if not self.alert_rules:
                logger.warning("No alert rules loaded. Nothing to check.")
                return

            # Get all assets with their latest state
            all_assets, _ = database.get_all_asset_metadata_paginated(db, per_page=1000)
            
            # Pre-fetch latest readings for all assets to minimize DB calls
            for asset in all_assets:
                metrics_config = self.get_metrics_for_asset_type(asset.get('asset_type'))
                asset['latest_dynamic_state'] = database.get_latest_readings_for_asset(db, asset['asset_id'], metrics_config)
            
            # Now process each asset against the rules
            for asset in all_assets:
                self.check_asset_against_rules(db, asset)

        logger.info("--- Alerting cycle finished ---")

    def get_metrics_for_asset_type(self, asset_type: str) -> Dict[str, str]:
        """Gets all the metrics that need to be checked for a given asset type."""
        metrics = {}
        rules_for_type = self.alert_rules.get(asset_type, [])
        for rule in rules_for_type:
            # Assuming all alertable metrics are from calculated data for simplicity
            metrics[rule['metric']] = 'calculated'
        return metrics

    def check_asset_against_rules(self, db, asset: Dict[str, Any]):
        """Checks a single asset against all applicable rules."""
        asset_id = asset['asset_id']
        asset_type = asset['asset_type']
        rules_for_type = self.alert_rules.get(asset_type, [])

        if not rules_for_type:
            return

        logger.debug(f"Checking asset {asset_id} (type: {asset_type}) against {len(rules_for_type)} rules.")

        for rule in rules_for_type:
            metric_name = rule['metric']
            latest_reading = asset.get('latest_dynamic_state', {}).get(metric_name)

            if not latest_reading:
                continue # Can't check a rule if there's no data

            current_value = latest_reading.get('value')
            if current_value is None:
                continue

            threshold = rule['threshold']
            condition = rule['condition'].lower()
            alert_name = rule['alert_name']
            is_triggered = False

            # Check if the alert condition is met
            if condition == '>' and current_value > threshold:
                is_triggered = True
            elif condition == '<' and current_value < threshold:
                is_triggered = True
            elif condition == '>=' and current_value >= threshold:
                is_triggered = True
            elif condition == '<=' and current_value <= threshold:
                is_triggered = True

            # Take action
            if is_triggered:
                message = rule['message_template'].format(
                    asset_id=asset_id,
                    value=f"{current_value:.2f}",
                    threshold=threshold
                )
                database.save_alert(
                    db,
                    asset_id=asset_id,
                    alert_name=alert_name,
                    message=message,
                    severity=rule['severity'],
                    details={'value': current_value, 'threshold': threshold}
                )
            else:
                # If the condition is no longer met, resolve any active alerts of this type
                database.resolve_alerts_for_condition(db, asset_id, alert_name)

    def start(self):
        """Starts the service's main loop."""
        logger.info("Alerting Service is starting...")
        while True:
            try:
                self.run_cycle()
            except Exception as e:
                logger.critical(f"Unhandled exception in main service loop: {e}", exc_info=True)
            
            logger.info(f"Sleeping for {self.interval} seconds...")
            time.sleep(self.interval)

def main():
    service = AlertingService()
    service.start()

if __name__ == "__main__":
    main()