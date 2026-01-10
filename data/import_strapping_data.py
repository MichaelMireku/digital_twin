# fuel_depot_digital_twin/data/import_strapping_data.py
import os
import sys
import pandas as pd
import logging
from sqlalchemy.orm import Session

# Add project root to path to allow module imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from data.database import SessionLocal, get_db
from data.db_models import StrappingData, Asset

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIGURATION ---
# IMPORTANT: Update this path to the correct location of your strapping table files
STRAPPING_TABLES_DIR = os.path.join(project_root, 'data', 'strapping_tables')

def clear_existing_strapping_data(db: Session, asset_id: str):
    """Deletes old strapping data for a specific asset before import."""
    try:
        num_deleted = db.query(StrappingData).filter(StrappingData.asset_id == asset_id).delete()
        db.commit()
        if num_deleted > 0:
            logging.info(f"Cleared {num_deleted} existing strapping records for asset '{asset_id}'.")
    except Exception as e:
        db.rollback()
        logging.error(f"Failed to clear existing data for '{asset_id}': {e}")
        raise

def import_strapping_table(db: Session, asset_id: str, file_path: str):
    """Imports a single strapping table CSV into the database."""
    if not os.path.exists(file_path):
        logging.warning(f"File not found: {file_path}. Skipping import for asset '{asset_id}'.")
        return

    try:
        # Check if the asset exists in the assets table
        asset = db.query(Asset).filter(Asset.asset_id == asset_id).first()
        if not asset:
            logging.warning(f"Asset ID '{asset_id}' not found in the 'assets' table. Skipping strapping data import.")
            return

        logging.info(f"Processing strapping table for asset '{asset_id}' from file '{os.path.basename(file_path)}'...")

        # Clear old data first
        clear_existing_strapping_data(db, asset_id)

        # Read the CSV
        df = pd.read_csv(file_path)
        # Standardize column names (assuming they might be 'Level (mm)' or 'Volume (L)')
        df.columns = [c.lower().strip().replace(' ', '_').replace('(','').replace(')','') for c in df.columns]
        
        if 'level_mm' not in df.columns or 'volume_litres' not in df.columns:
            logging.error(f"CSV file '{os.path.basename(file_path)}' must contain 'level_mm' and 'volume_litres' columns. Skipping.")
            return

        # Prepare data for bulk insert
        records_to_insert = [
            StrappingData(asset_id=asset_id, level_mm=row['level_mm'], volume_litres=row['volume_litres'])
            for index, row in df.iterrows()
        ]

        if not records_to_insert:
            logging.warning(f"No data to insert for asset '{asset_id}'.")
            return

        # Bulk insert
        db.bulk_save_objects(records_to_insert)
        db.commit()
        logging.info(f"Successfully imported {len(records_to_insert)} strapping records for asset '{asset_id}'.")

    except Exception as e:
        db.rollback()
        logging.error(f"An error occurred during import for asset '{asset_id}': {e}", exc_info=True)

def main():
    """Main function to iterate through CSVs and import them."""
    if not os.path.isdir(STRAPPING_TABLES_DIR):
        logging.critical(f"Strapping tables directory not found at: '{STRAPPING_TABLES_DIR}'")
        sys.exit(1)

    with get_db() as db:
        if not db:
            logging.critical("Could not establish a database session. Exiting.")
            sys.exit(1)
            
        # The script assumes the filename IS the asset_id (e.g., "T01.csv")
        for filename in os.listdir(STRAPPING_TABLES_DIR):
            if filename.lower().endswith('.csv'):
                asset_id = os.path.splitext(filename)[0]
                file_path = os.path.join(STRAPPING_TABLES_DIR, filename)
                import_strapping_table(db, asset_id, file_path)
    
    logging.info("Strapping data import process finished.")

if __name__ == "__main__":
    main()