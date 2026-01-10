import os
import csv
import logging

# --- Logging Configuration ---
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Tank Configurations ---
# This dictionary holds the master data for tank capacities.
TANK_CONFIGS = {
    'TANK_121': 20000000, 'TANK_122': 20000000, 'TANK_123': 20000000, 'TANK_124': 20000000,
    'TANK_101': 2600000,  'TANK_102': 7200000,  'TANK_103': 12600000,
    'TANK_141': 11600000, 'TANK_142': 11600000, 'TANK_143': 11600000, 'TANK_144': 11600000,
    'TANK_5801': 21700000, 'TANK_5802': 21800000, 'TANK_5803': 21300000, 'TANK_5804': 11300000,
}

# --- Constants ---
MAX_PLACEHOLDER_LEVEL_MM = 16000.0  # Standard 16-meter height for all tanks
OUTPUT_DIR = os.path.join("data", "strapping")
HEADER = ['level_mm', 'volume_litres']  # Standardized lowercase headers

def generate_strapping_data(max_capacity_litres: float, max_level_mm: float, num_points: int = 40) -> list:
    """Generates a list of (level, volume) tuples with a slight curve for realism."""
    data = []
    for i in range(num_points + 1):
        level_fraction = i / num_points
        # Using a slight power curve (x^1.05) simulates a more realistic tank shape than a perfect cylinder.
        volume_fraction = level_fraction ** 1.05 
        
        level = round(level_fraction * max_level_mm, 2)
        volume = round(volume_fraction * max_capacity_litres, 0)
        
        data.append((level, volume))
        
    return data

def main():
    """Main function to create the strapping CSV files."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        logger.info(f"Created directory: {OUTPUT_DIR}")
        
    for tank_id, capacity_l in TANK_CONFIGS.items():
        filepath = os.path.join(OUTPUT_DIR, f"{tank_id}.csv")
        strapping_data = generate_strapping_data(capacity_l, MAX_PLACEHOLDER_LEVEL_MM)
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(HEADER)
                writer.writerows(strapping_data)
            logger.info(f"✅ Generated placeholder strapping file: {filepath}")
        except IOError as e:
            logger.error(f"Could not write to file {filepath}: {e}")

if __name__ == "__main__":
    main()
