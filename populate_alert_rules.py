import sys
import os
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text

# --- ROBUST PATH SETUP ---
try:
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from data import database
    from data.db_models import AlertConfiguration
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import core modules: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def populate_rules(db: Session):
    """
    Inserts a standard set of alert rules into the database.
    This function is idempotent - it will not create duplicates.
    """
    rules = [
        # --- Storage Tank Rules ---
        {
            'asset_type': 'StorageTank', 'metric_name': 'level_percentage', 'condition_type': '>=',
            'threshold_value': 95.0, 'alert_name': 'TANK_LEVEL_HIGH_HIGH',
            'message_template': 'CRITICAL: Tank {asset_id} level is at {value}%, exceeding H/H threshold of {threshold}%.',
            'severity': 'Critical', 'is_enabled': True
        },
        {
            'asset_type': 'StorageTank', 'metric_name': 'level_percentage', 'condition_type': '>=',
            'threshold_value': 90.0, 'alert_name': 'TANK_LEVEL_HIGH',
            'message_template': 'WARNING: Tank {asset_id} level is at {value}%, exceeding high threshold of {threshold}%.',
            'severity': 'Warning', 'is_enabled': True
        },
        {
            'asset_type': 'StorageTank', 'metric_name': 'level_percentage', 'condition_type': '<=',
            'threshold_value': 10.0, 'alert_name': 'TANK_LEVEL_LOW',
            'message_template': 'WARNING: Tank {asset_id} level is at {value}%, below low threshold of {threshold}%.',
            'severity': 'Warning', 'is_enabled': True
        },
        {
            'asset_type': 'StorageTank', 'metric_name': 'level_percentage', 'condition_type': '<=',
            'threshold_value': 5.0, 'alert_name': 'TANK_LEVEL_LOW_LOW',
            'message_template': 'CRITICAL: Tank {asset_id} level is at {value}%, below L/L threshold of {threshold}%.',
            'severity': 'Critical', 'is_enabled': True
        },
    ]

    try:
        existing_names = {res[0] for res in db.execute(text("SELECT alert_name FROM alert_configurations")).fetchall()}
        
        new_rules_to_add = []
        for rule_data in rules:
            if rule_data['alert_name'] not in existing_names:
                new_rules_to_add.append(AlertConfiguration(**rule_data))

        if not new_rules_to_add:
            logging.warning("All standard alert rules already exist in the database. No new rules added.")
            return

        db.add_all(new_rules_to_add)
        db.commit()
        logging.info(f"✅ Successfully added {len(new_rules_to_add)} new alert rules to the database.")

    except Exception as e:
        logging.error(f"Failed to populate alert rules: {e}", exc_info=True)
        db.rollback()

def main():
    logging.info("Attempting to populate standard alert rules...")
    with database.get_db() as db:
        if db:
            populate_rules(db)
        else:
            logging.critical("Could not get a database session. Aborting.")

if __name__ == "__main__":
    main()