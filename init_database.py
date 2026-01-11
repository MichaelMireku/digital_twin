# init_database.py
# Script to initialize the database with schema and populate assets

import os
import sys
import logging

# Add project root to path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Initialize database: create tables and populate assets."""
    
    # Step 1: Create tables
    logger.info("=" * 60)
    logger.info("STEP 1: Creating database tables...")
    logger.info("=" * 60)
    
    try:
        from data.database import engine
        from data.db_models import Base
        
        if not engine:
            logger.critical("Database engine not configured. Check your .env file.")
            return False
            
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully.")
    except Exception as e:
        logger.error(f"Failed to create tables: {e}", exc_info=True)
        return False
    
    # Step 2: Populate assets from SQL file
    logger.info("")
    logger.info("=" * 60)
    logger.info("STEP 2: Populating assets...")
    logger.info("=" * 60)
    
    try:
        from sqlalchemy import text
        from data.database import SessionLocal
        
        # Read the SQL file
        sql_file = os.path.join(project_root, 'populate_assets.sql')
        with open(sql_file, 'r') as f:
            sql_content = f.read()
        
        # Execute SQL statements
        with SessionLocal() as session:
            # Remove SQL comments and split by semicolon
            lines = []
            for line in sql_content.split('\n'):
                # Remove single-line comments
                if '--' in line:
                    line = line[:line.index('--')]
                lines.append(line)
            
            clean_sql = '\n'.join(lines)
            statements = [s.strip() for s in clean_sql.split(';') if s.strip()]
            
            for statement in statements:
                if statement:
                    session.execute(text(statement))
            
            session.commit()
            logger.info("Assets populated successfully.")
            
            # Count assets
            result = session.execute(text("SELECT asset_type, COUNT(*) FROM assets GROUP BY asset_type ORDER BY asset_type"))
            logger.info("")
            logger.info("Asset Summary:")
            logger.info("-" * 40)
            total = 0
            for row in result:
                logger.info(f"  {row[0]}: {row[1]}")
                total += row[1]
            logger.info("-" * 40)
            logger.info(f"  Total: {total} assets")
            
    except Exception as e:
        logger.error(f"Failed to populate assets: {e}", exc_info=True)
        return False
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("Database initialization complete!")
    logger.info("=" * 60)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
