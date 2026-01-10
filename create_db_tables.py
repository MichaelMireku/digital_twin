# create_db_tables.py

import os
import sys
import logging

# Add project root to path to allow module imports
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from data.database import engine
from data.db_models import Base  # This imports the Base that all your models are declarative from

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """
    Connects to the database and creates all tables defined by the SQLAlchemy models.
    """
    if not engine:
        logging.critical("Database engine is not configured. Cannot create tables. Check your .env and config settings.")
        return

    try:
        logging.info("Connecting to the database to create tables...")
        # The magic happens here: SQLAlchemy inspects the Base object, finds all
        # classes that inherit from it, and creates the corresponding tables.
        # This is safe to run multiple times; it will not recreate existing tables.
        Base.metadata.create_all(bind=engine)
        logging.info("✅ All tables created successfully (or already exist).")
        logging.info("Your database schema is now up-to-date.")

    except Exception as e:
        logging.critical(f"An error occurred while creating database tables: {e}", exc_info=True)

if __name__ == "__main__":
    main()