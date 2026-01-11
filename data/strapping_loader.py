# File: fuel_depot_digital_twin/data/strapping_loader.py
import csv
import os
import logging
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

# --- Global Cache for Strapping Tables ---
# Cache to store loaded strapping tables in memory to avoid repeated file I/O
# Key: asset_id (e.g., 'TK-A01'), Value: Dict[int, float] (level_mm -> volume_litres)
_strapping_tables_cache: Dict[str, Dict[int, float]] = {}

# --- Configuration for Strapping Data ---
# Assumes strapping CSVs are in a subdirectory named 'strapping' within this 'data' directory.
# e.g., data/strapping/TK-A01.csv
STRAPPING_DATA_BASE_PATH = os.path.join(os.path.dirname(__file__), 'strapping')
DEFAULT_STRAPPING_FILENAME_TEMPLATE = "{asset_id}.csv" # e.g., TK-A01.csv

def _load_single_strapping_table_from_csv(file_path: str) -> Optional[Dict[int, float]]:
    """
    Loads a single strapping table from a CSV file.
    CSV format: level_mm,volume_litres (or similar, ensure headers match or are skipped)
    """
    strapping_data: Dict[int, float] = {}
    try:
        if not os.path.exists(file_path):
            logger.warning(f"Strapping table file not found: {file_path}")
            return None

        with open(file_path, mode='r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader, None) # Read and skip header row

            # Validate header if necessary, e.g.:
            # if not header or header[0].lower() != 'level_mm' or header[1].lower() != 'volume_litres':
            #     logger.error(f"Invalid CSV header in {file_path}: Expected 'level_mm,volume_litres', got {header}")
            #     return None

            for i, row in enumerate(reader):
                if len(row) >= 2:
                    try:
                        level_mm = int(float(row[0])) # Allow float in CSV, convert to int
                        volume_litres = float(row[1])
                        strapping_data[level_mm] = volume_litres
                    except ValueError:
                        logger.warning(f"Skipping invalid row in {file_path} at line {i+2}: {row}. Could not convert to number.")
                else:
                    logger.warning(f"Skipping malformed row in {file_path} at line {i+2}: {row}. Expected at least 2 columns.")
        
        if not strapping_data:
            logger.warning(f"No valid data loaded from strapping table: {file_path}")
            return None
            
        logger.info(f"Successfully loaded strapping table from: {file_path} with {len(strapping_data)} entries.")
        return strapping_data

    except FileNotFoundError:
        logger.error(f"Strapping table file not found: {file_path}")
    except Exception as e:
        logger.error(f"Error loading strapping table from {file_path}: {e}", exc_info=True)
    return None


def get_strapping_table_litres(asset_id: str, filename_template: str = DEFAULT_STRAPPING_FILENAME_TEMPLATE) -> Optional[Dict[int, float]]:
    """
    Retrieves the strapping table (level_mm -> volume_litres) for a given asset_id.
    Loads from CSV if not already in cache.
    The filename is constructed using the template and asset_id.
    """
    if asset_id in _strapping_tables_cache:
        logger.debug(f"Strapping table for {asset_id} found in cache.")
        return _strapping_tables_cache[asset_id]

    filename = filename_template.format(asset_id=asset_id)
    file_path = os.path.join(STRAPPING_DATA_BASE_PATH, filename)

    logger.info(f"Attempting to load strapping table for {asset_id} from file: {file_path}")
    strapping_data = _load_single_strapping_table_from_csv(file_path)

    if strapping_data:
        _strapping_tables_cache[asset_id] = strapping_data
        logger.info(f"Strapping table for {asset_id} loaded and cached.")
    else:
        logger.warning(f"Failed to load strapping table for {asset_id}. It will not be cached.")
        # Optionally cache None or an empty dict to prevent repeated load attempts for missing files
        # _strapping_tables_cache[asset_id] = None # or {} 
    
    return strapping_data

def preload_all_strapping_tables(asset_ids: List[str], filename_template: str = DEFAULT_STRAPPING_FILENAME_TEMPLATE) -> None:
    """
    Preloads strapping tables for a list of asset IDs into the cache.
    Typically called at application startup.
    """
    logger.info(f"Preloading strapping tables for {len(asset_ids)} assets...")
    loaded_count = 0
    for asset_id in asset_ids:
        if asset_id not in _strapping_tables_cache: # Only load if not already cached
            if get_strapping_table_litres(asset_id, filename_template): # This will load and cache
                loaded_count +=1
    logger.info(f"Finished preloading. Successfully loaded and cached {loaded_count} new strapping tables.")

def clear_strapping_cache():
    """Clears the in-memory strapping table cache."""
    global _strapping_tables_cache
    _strapping_tables_cache.clear()
    logger.info("Strapping table cache cleared.")

# Example of how to ensure this runs if this script is executed directly for testing
# if __name__ == '__main__':
#     logging.basicConfig(level=logging.INFO)
#     print(f"Looking for strapping tables in: {STRAPPING_DATA_BASE_PATH}")
    
#     # Example: Test loading for a specific tank
#     test_tank_id = 'TK-A01'
#     table = get_strapping_table_litres(test_tank_id)
#     if table:
#         print(f"\nStrapping table for {test_tank_id} (first 5 entries):")
#         for i, (level, volume) in enumerate(table.items()):
#             if i < 5:
#                 print(f"Level: {level} mm -> Volume: {volume} L")
#             else:
#                 break
#         print(f"Total entries for {test_tank_id}: {len(table)}")
#     else:
#         print(f"\nCould not load strapping table for {test_tank_id}.")

#     # Example: Preload multiple tanks
#     # preload_all_strapping_tables(['TK-A01', 'TK-A02', 'TK-B01'])
