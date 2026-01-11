# generate_placeholder_strapping.py
# Generates placeholder strapping table CSV files for demo tanks

import os
import csv

# Tank configurations with fictional IDs and capacities
TANK_CONFIGS = {
    'TK-A01': 15000000, 'TK-A02': 15000000, 'TK-A03': 18000000, 'TK-A04': 18000000,
    'TK-B01': 3000000,  'TK-B02': 8000000,  'TK-B03': 10000000,
    'TK-C01': 12000000, 'TK-C02': 12000000, 'TK-C03': 12000000, 'TK-C04': 12000000,
    'TK-D01': 20000000, 'TK-D02': 20000000, 'TK-D03': 20000000, 'TK-D04': 10000000,
}

# Assumed max level in mm for all tanks
MAX_LEVEL_MM = 16000
LEVEL_INCREMENT_MM = 100

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'data', 'strapping')

def generate_strapping_csv(tank_id: str, capacity_litres: int):
    """Generates a linear strapping table CSV for a given tank."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    file_path = os.path.join(OUTPUT_DIR, f"{tank_id}.csv")
    
    with open(file_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['level_mm', 'volume_litres'])
        
        for level in range(0, MAX_LEVEL_MM + LEVEL_INCREMENT_MM, LEVEL_INCREMENT_MM):
            volume = (level / MAX_LEVEL_MM) * capacity_litres
            writer.writerow([level, round(volume, 2)])
    
    print(f"Generated: {file_path}")

if __name__ == '__main__':
    print(f"Generating strapping tables in: {OUTPUT_DIR}")
    for tank_id, capacity in TANK_CONFIGS.items():
        generate_strapping_csv(tank_id, capacity)
    print("Done!")
