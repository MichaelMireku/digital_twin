# seed_sensor_data.py
# Seeds realistic sensor readings for all tanks - run once to populate dashboard
# Can be run periodically via external cron (e.g., cron-job.org) hitting an API endpoint

import os
import sys
import random
import datetime
import logging

project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config import settings
from data import database
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def seed_tank_readings():
    """Generate realistic sensor readings for all storage tanks."""
    
    with database.SessionLocal() as db:
        # Get all storage tanks
        result = db.execute(text("""
            SELECT asset_id, capacity_litres, product_service 
            FROM assets 
            WHERE asset_type = 'StorageTank'
        """))
        tanks = result.fetchall()
        
        if not tanks:
            logger.warning("No tanks found in database")
            return
        
        now = datetime.datetime.now(datetime.timezone.utc)
        readings_count = 0
        
        for tank in tanks:
            asset_id = tank[0]
            capacity = float(tank[1] or 10000000)
            product = tank[2] or ''
            
            # Generate realistic fill level (40-85%)
            fill_pct = random.uniform(40, 85)
            volume_litres = capacity * (fill_pct / 100)
            
            # Calculate level in mm (assuming ~12m max height for large tanks)
            max_height_mm = 12000
            level_mm = max_height_mm * (fill_pct / 100)
            
            # Temperature based on product (AGO slightly warmer)
            if 'AGO' in product.upper() or 'GASOIL' in product.upper():
                temp = random.uniform(28, 35)
            else:
                temp = random.uniform(22, 30)
            
            # Insert sensor readings
            db.execute(text("""
                INSERT INTO sensor_readings (time, asset_id, data_source_id, metric_name, value_numeric, unit, status)
                VALUES (:time, :asset_id, 'SEED_DATA', 'level_mm', :level, 'mm', 'OK')
            """), {"time": now, "asset_id": asset_id, "level": round(level_mm, 2)})
            
            db.execute(text("""
                INSERT INTO sensor_readings (time, asset_id, data_source_id, metric_name, value_numeric, unit, status)
                VALUES (:time, :asset_id, 'SEED_DATA', 'temperature', :temp, 'C', 'OK')
            """), {"time": now, "asset_id": asset_id, "temp": round(temp, 2)})
            
            db.execute(text("""
                INSERT INTO sensor_readings (time, asset_id, data_source_id, metric_name, value_numeric, unit, status)
                VALUES (:time, :asset_id, 'SEED_DATA', 'level_percentage', :pct, '%', 'OK')
            """), {"time": now, "asset_id": asset_id, "pct": round(fill_pct, 2)})
            
            # Insert calculated volumes
            db.execute(text("""
                INSERT INTO calculated_data (time, asset_id, metric_name, value, unit, calculation_status)
                VALUES (:time, :asset_id, 'volume_gov', :vol, 'litres', 'OK')
                ON CONFLICT (time, asset_id, metric_name) DO UPDATE SET value = :vol
            """), {"time": now, "asset_id": asset_id, "vol": round(volume_litres, 2)})
            
            db.execute(text("""
                INSERT INTO calculated_data (time, asset_id, metric_name, value, unit, calculation_status)
                VALUES (:time, :asset_id, 'volume_gsv', :vol, 'litres', 'OK')
                ON CONFLICT (time, asset_id, metric_name) DO UPDATE SET value = :vol
            """), {"time": now, "asset_id": asset_id, "vol": round(volume_litres * 0.98, 2)})
            
            readings_count += 1
            logger.info(f"Seeded {asset_id}: {fill_pct:.1f}% full, {temp:.1f}°C")
        
        db.commit()
        logger.info(f"Successfully seeded readings for {readings_count} tanks")

if __name__ == "__main__":
    logger.info("Starting sensor data seeding...")
    seed_tank_readings()
    logger.info("Done!")
