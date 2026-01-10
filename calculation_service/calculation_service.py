import os
import sys
import time
import logging
from typing import Dict, Any, Optional


try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from config import settings
    from data import database
    from utils.volume_calculator import VolumeCalculator
    # Physics Engine imports
    from core.physics import MassBalanceCalculator, EnergyBalanceCalculator
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import core modules: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CalculationService")

class CalculationService:
    def __init__(self, interval_seconds: int = 30):
        self.interval = interval_seconds
        self.volume_calculator = VolumeCalculator()
        # Initialize physics calculators
        self.mass_calculator = MassBalanceCalculator(reference_temp_c=20.0)
        self.energy_calculator = EnergyBalanceCalculator(reference_temp_c=0.0)
        logger.info(f"Calculation Service initialized with Physics Engine. Run interval: {self.interval} seconds.")

    def run_cycle(self):
        logger.info("--- Starting new calculation cycle ---")
        with database.get_db() as db:
            if not db:
                logger.error("Could not get DB session. Skipping cycle.")
                return

            all_assets, _ = database.get_all_asset_metadata_paginated(db, per_page=1000)
            tanks = [asset for asset in all_assets if asset.get('asset_type') == 'StorageTank']
            logger.info(f"Found {len(tanks)} storage tanks to process.")

            for tank_meta in tanks:
                asset_id = tank_meta['asset_id']
                try:
                    self.process_tank(db, asset_id, tank_meta)
                except Exception as e:
                    logger.error(f"[FATAL] Failed to process tank {asset_id}: {e}", exc_info=True)
        logger.info("--- Calculation cycle finished ---")

    def process_tank(self, db, asset_id: str, tank_meta: Dict[str, Any]):
        latest_level = database.get_latest_sensor_reading(db, asset_id, 'level_mm')
        if not latest_level:
            logger.debug(f"No level reading for tank {asset_id}. Skipping.")
            return

        last_calc_time = database.get_latest_calculated_data(db, asset_id, 'level_percentage')
        if last_calc_time and last_calc_time['time'] >= latest_level['time']:
            logger.debug(f"Calculations for {asset_id} are already up-to-date.")
            return
        
        level_mm = latest_level.get('value')
        capacity_litres = float(tank_meta.get('capacity_litres', 0))
        
        # 1. Calculate Level Percentage
   
        max_level_mm = 16000.0 
        level_pct = (level_mm / max_level_mm) * 100 if max_level_mm > 0 else 0
        database.save_calculated_data(db, time=latest_level['time'], asset_id=asset_id, metric_name='level_percentage', value=level_pct, unit='%', calculation_status='OK')
        logger.info(f"Calculated level_percentage for {asset_id}: {level_pct:.2f}%")

        # 2. Calculate GOV
        strapping_data = database.get_strapping_data_from_db(db, asset_id)
        if not strapping_data:
            logger.warning(f"No strapping data for tank {asset_id}. Cannot calculate volumes.")
            return
        
        gov_litres = self.volume_calculator.calculate_gov_from_strapping(level_mm, strapping_data)
        if gov_litres is not None:
            database.save_calculated_data(db, time=latest_level['time'], asset_id=asset_id, metric_name='volume_gov', value=gov_litres, unit='Litres', calculation_status='OK')
            logger.info(f"Calculated volume_gov for {asset_id}: {gov_litres:,.2f} L.")

            # 3. Calculate GSV
            latest_temp = database.get_latest_sensor_reading(db, asset_id, 'temperature')
            if latest_temp:
                density_at_20c = tank_meta.get('density_at_20c_kg_m3')
                if density_at_20c:
                    gsv_litres = self.volume_calculator.calculate_gsv(gov_litres=gov_litres, observed_temp_c=latest_temp.get('value'), density_at_20c=float(density_at_20c))
                    if gsv_litres is not None:
                        database.save_calculated_data(db, time=latest_level['time'], asset_id=asset_id, metric_name='volume_gsv', value=gsv_litres, unit='Litres', calculation_status='OK')
                        logger.info(f"Calculated volume_gsv for {asset_id}: {gsv_litres:,.2f} L.")

                    # 4. Calculate Mass Balance (NEW - Physics Engine)
                    product_type = tank_meta.get('product_service', 'DEFAULT')
                    temperature_c = latest_temp.get('value')
                    
                    mass_result = self.mass_calculator.calculate_mass_in_tank(
                        gov_litres=gov_litres,
                        temperature_c=temperature_c,
                        density_at_20c=float(density_at_20c),
                        product_type=product_type
                    )
                    
                    if mass_result.mass_kg > 0:
                        database.save_calculated_data(
                            db, time=latest_level['time'], asset_id=asset_id,
                            metric_name='mass_kg', value=mass_result.mass_kg,
                            unit='kg', calculation_status='OK'
                        )
                        logger.info(f"Calculated mass_kg for {asset_id}: {mass_result.mass_kg:,.2f} kg")
                        
                        # Also save temperature-corrected density
                        database.save_calculated_data(
                            db, time=latest_level['time'], asset_id=asset_id,
                            metric_name='density_at_temp', value=mass_result.density_at_temp_kg_m3,
                            unit='kg/m³', calculation_status='OK'
                        )

                    # 5. Calculate Heat Content (NEW - Energy Balance)
                    heat_result = self.energy_calculator.calculate_tank_heat_content(
                        mass_kg=mass_result.mass_kg,
                        temperature_c=temperature_c,
                        product_type=product_type
                    )
                    
                    if heat_result.energy_kj > 0:
                        database.save_calculated_data(
                            db, time=latest_level['time'], asset_id=asset_id,
                            metric_name='heat_content_kj', value=heat_result.energy_kj,
                            unit='kJ', calculation_status='OK'
                        )
                        logger.info(f"Calculated heat_content for {asset_id}: {heat_result.energy_kj:,.0f} kJ")

    def start(self):
        logger.info("Calculation Service is starting...")
        while True:
            try:
                self.run_cycle()
            except Exception as e:
                logger.critical(f"Unhandled exception in main service loop: {e}", exc_info=True)
            logger.info(f"Sleeping for {self.interval} seconds...")
            time.sleep(self.interval)

def main():
    service = CalculationService()
    service.start()

if __name__ == "__main__":
    main()
