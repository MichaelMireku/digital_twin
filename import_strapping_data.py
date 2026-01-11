import os
import sys
import pandas as pd
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

# --- ROBUST PATH SETUP ---
try:
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from data.database import SessionLocal, get_db
    from data.db_models import StrappingData, Asset
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import core modules: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
STRAPPING_TABLES_DIR = os.path.join(project_root, 'data', 'strapping')

def import_strapping_table(db: Session, asset_id: str, file_path: str):
    """Imports a single strapping table CSV into the database."""
    if not os.path.exists(file_path):
        logging.warning(f"File not found: {file_path}. Skipping.")
        return

    try:
        asset = db.query(Asset).filter(Asset.asset_id == asset_id).first()
        if not asset:
            logging.warning(f"Asset ID '{asset_id}' not found in the 'assets' table. Skipping strapping data import.")
            return

        logging.info(f"Processing strapping table for asset '{asset_id}'...")
        # Clear existing data for this tank to ensure a clean import
        db.query(StrappingData).filter(StrappingData.asset_id == asset_id).delete()
        db.commit()

        # Read the CSV using the first row as the header
        df = pd.read_csv(file_path, header=0)
        
        # Ensure required columns exist
        if 'level_mm' not in df.columns or 'volume_litres' not in df.columns:
            logging.error(f"CSV for '{asset_id}' is missing required headers 'level_mm' or 'volume_litres'. Skipping.")
            return

        # Prepare records for bulk insertion
        records_to_insert = [
            StrappingData(
                asset_id=asset_id, 
                level_mm=float(row['level_mm']), 
                volume_litres=float(row['volume_litres'])
            )
            for _, row in df.iterrows()
        ]

        if not records_to_insert:
            logging.warning(f"No data to insert for asset '{asset_id}'.")
            return

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
            logging.critical("Could not establish a database session.")
            sys.exit(1)
            
        for filename in os.listdir(STRAPPING_TABLES_DIR):
            if filename.lower().endswith('.csv'):
                asset_id = os.path.splitext(filename)[0].upper()
                file_path = os.path.join(STRAPPING_TABLES_DIR, filename)
                import_strapping_table(db, asset_id, file_path)
    
    logging.info("Strapping data import process finished.")

if __name__ == "__main__":
    main()
