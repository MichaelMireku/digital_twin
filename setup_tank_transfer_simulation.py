#!/usr/bin/env python
"""
Tank Transfer Simulation Setup Script

This script sets up everything needed to run the tank transfer simulation:
1. Verifies database connection
2. Creates/updates database schema
3. Populates assets with pump flow rates
4. Seeds initial tank volume data for simulation

Usage:
    python setup_tank_transfer_simulation.py
"""

import os
import sys
import logging
import datetime
import random

# Add project root to path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_env_config():
    """Verify .env configuration is set up."""
    logger.info("Checking environment configuration...")
    
    env_file = os.path.join(project_root, '.env')
    if not os.path.exists(env_file):
        logger.error(".env file not found! Copy .env.example to .env and configure it.")
        return False
    
    # Check required variables
    from dotenv import load_dotenv
    load_dotenv(env_file)
    
    required_vars = ['DB_PASSWORD', 'API_KEY', 'DB_HOST', 'DB_NAME']
    missing = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value or value in ['your_password_here', 'your_api_key_here']:
            missing.append(var)
    
    if missing:
        logger.warning(f"Please configure these variables in .env: {', '.join(missing)}")
        return False
    
    logger.info("Environment configuration looks good.")
    return True


def setup_database():
    """Create database tables and populate assets."""
    logger.info("Setting up database...")
    
    try:
        from config import settings
        from data.database import engine, SessionLocal
        from data.db_models import Base
        from sqlalchemy import text
        
        if not engine:
            logger.error("Database engine not configured. Check your .env file.")
            return False
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified.")
        
        # Populate assets
        sql_file = os.path.join(project_root, 'populate_assets.sql')
        with open(sql_file, 'r') as f:
            sql_content = f.read()
        
        with SessionLocal() as session:
            # Clean and execute SQL
            lines = []
            for line in sql_content.split('\n'):
                if '--' in line:
                    line = line[:line.index('--')]
                lines.append(line)
            
            clean_sql = '\n'.join(lines)
            statements = [s.strip() for s in clean_sql.split(';') if s.strip()]
            
            for statement in statements:
                if statement:
                    try:
                        session.execute(text(statement))
                    except Exception as e:
                        # Ignore "column already exists" errors
                        if 'already exists' not in str(e).lower():
                            logger.warning(f"SQL warning: {e}")
            
            session.commit()
            logger.info("Assets populated successfully.")
            
            # Show summary
            result = session.execute(text(
                "SELECT asset_type, COUNT(*) FROM assets GROUP BY asset_type ORDER BY asset_type"
            ))
            logger.info("\nAsset Summary:")
            logger.info("-" * 40)
            for row in result:
                logger.info(f"  {row[0]}: {row[1]}")
        
        return True
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}", exc_info=True)
        return False


def seed_tank_volumes():
    """Seed initial calculated volume data for tanks."""
    logger.info("\nSeeding initial tank volume data...")
    
    try:
        from data.database import SessionLocal, save_calculated_data
        from sqlalchemy import text
        
        with SessionLocal() as session:
            # Get all storage tanks
            result = session.execute(text(
                "SELECT asset_id, capacity_litres FROM assets WHERE asset_type = 'StorageTank'"
            ))
            tanks = result.fetchall()
            
            now = datetime.datetime.now(datetime.timezone.utc)
            
            for tank_id, capacity in tanks:
                if capacity:
                    # Random fill level between 30% and 80%
                    fill_pct = random.uniform(0.30, 0.80)
                    volume = float(capacity) * fill_pct
                    
                    # Save as calculated GSV (Gross Standard Volume)
                    save_calculated_data(
                        session, now, tank_id, 'volume_gsv',
                        volume, 'litres', 'OK'
                    )
                    logger.info(f"  {tank_id}: {volume:,.0f} L ({fill_pct*100:.1f}% full)")
            
            logger.info("Tank volumes seeded.")
            return True
            
    except Exception as e:
        logger.error(f"Failed to seed tank volumes: {e}", exc_info=True)
        return False


def print_usage_instructions():
    """Print instructions for running the simulation."""
    print("\n" + "=" * 60)
    print("TANK TRANSFER SIMULATION SETUP COMPLETE")
    print("=" * 60)
    print("""
To run a tank transfer simulation, use the API endpoint:

  POST /api/v1/simulations/tank-transfer
  
  Headers:
    X-API-Key: <your_api_key>
    Content-Type: application/json
  
  Body:
    {
      "source_tank_id": "TK-A01",
      "destination_tank_id": "TK-A02", 
      "pump_id": "PP-A04"
    }

Example with curl:
  curl -X POST http://localhost:5000/api/v1/simulations/tank-transfer \\
    -H "X-API-Key: your_api_key_here" \\
    -H "Content-Type: application/json" \\
    -d '{"source_tank_id":"TK-A01","destination_tank_id":"TK-A02","pump_id":"PP-A04"}'

Available Tanks:
  Zone A: TK-A01, TK-A02 (AGO), TK-A03, TK-A04 (PMS)
  Zone B: TK-B01, TK-B02, TK-B03 (AGO Transit)
  Zone C: TK-C01, TK-C02 (AGO), TK-C03, TK-C04 (PMS)
  Zone D: TK-D01, TK-D02, TK-D03, TK-D04 (AGO Rental)

Available Pumps:
  Zone A: PP-A01 to PP-A06 (PMS: 3000 LPM, AGO: 2500 LPM)
  Zone B: PP-B01, PP-B02 (AGO: 2000 LPM)
  Zone C: PP-C01 to PP-C06 (1500-2200 LPM)

To start the API server:
  python api/app.py

To run the sensor simulator (requires MQTT broker):
  python sensor_simulator/sensor_simulator.py
""")


def main():
    """Main setup function."""
    print("=" * 60)
    print("TANK TRANSFER SIMULATION SETUP")
    print("=" * 60)
    print()
    
    # Step 1: Check environment
    if not check_env_config():
        logger.warning("Continuing with default/incomplete config...")
    
    # Step 2: Setup database
    if not setup_database():
        logger.error("Setup failed at database step.")
        return False
    
    # Step 3: Seed tank volumes
    if not seed_tank_volumes():
        logger.error("Setup failed at seeding step.")
        return False
    
    # Print usage instructions
    print_usage_instructions()
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
