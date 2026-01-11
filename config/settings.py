# File: fuel_depot_digital_twin/config/settings.py
import os
import logging
import sys
from dotenv import load_dotenv

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper(),
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    dotenv_path = os.path.join(project_root, '.env')
    logger.info(f"Attempting to load .env file from: {dotenv_path}")

    if os.path.exists(dotenv_path):
        if load_dotenv(dotenv_path=dotenv_path, verbose=True):
            logger.info(f"Successfully loaded .env file from {dotenv_path}")
        else:
            logger.info(f".env file at {dotenv_path} processed but might be empty or set no new vars.")
    else:
        logger.info(f".env file not found at {dotenv_path}. Using system environment variables or defaults.")
except Exception as e:
    logger.error(f"Error loading .env file from {dotenv_path}: {e}", exc_info=True)


# --- API Configuration ---
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    logger.warning("API_KEY is not set. The API will not be accessible without it.")


# --- MQTT Configuration ---
MQTT_BROKER_ADDRESS = os.getenv("MQTT_BROKER_ADDRESS", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_CLIENT_ID_PROCESSOR = os.getenv("MQTT_CLIENT_ID_PROCESSOR", "digital_twin_processor")
MQTT_CLIENT_ID_SIMULATOR = os.getenv("MQTT_CLIENT_ID_SIMULATOR", "sensor_simulator")
MQTT_BASE_TOPIC = os.getenv("MQTT_BASE_TOPIC", "demo/depot/dev")
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
MQTT_USE_TLS = os.getenv("MQTT_USE_TLS", "false").lower() == "true"

logger.info(f"MQTT_BROKER_ADDRESS = {MQTT_BROKER_ADDRESS}")
logger.info(f"MQTT_BROKER_PORT = {MQTT_BROKER_PORT}")
logger.info(f"MQTT_BASE_TOPIC = {MQTT_BASE_TOPIC}")
logger.info(f"MQTT_USE_TLS = {MQTT_USE_TLS}")


# --- Database Configuration (For SQLAlchemy) ---
DB_NAME = os.getenv("DB_NAME", "depot_twin_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

if not DB_PASSWORD:
    logger.critical("DB_PASSWORD is not set. Please set a secure password via .env or environment variable.")
    sys.exit(1)

logger.info(f"DB_NAME = {DB_NAME}")
logger.info(f"DB_USER = {DB_USER}")
logger.info(f"DB_HOST = {DB_HOST}")
logger.info(f"DB_PORT = {DB_PORT}")


# SQLAlchemy Database URL Construction
DATABASE_URL = None
try:
    DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    masked_db_url = f"postgresql+psycopg2://{DB_USER}:***@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    logger.info(f"DATABASE_URL constructed: {masked_db_url}")
except Exception as e_url:
    logger.critical(f"Failed to construct DATABASE_URL string: {e_url}", exc_info=True)

if not DATABASE_URL:
     logger.critical("DATABASE_URL was not successfully constructed! Database connections will fail.")


# --- Simulation Settings ---
SIMULATION_INTERVAL_SECONDS = int(os.getenv("SIMULATION_INTERVAL_SECONDS", "10"))
logger.info(f"SIMULATION_INTERVAL_SECONDS = {SIMULATION_INTERVAL_SECONDS}")


# --- Volume Correction Settings ---
# UPDATED: Standard reference temperature in Celsius for petroleum products is now 20°C
STANDARD_REFERENCE_TEMPERATURE_CELSIUS = float(os.getenv("STANDARD_REFERENCE_TEMPERATURE_CELSIUS", "20.0"))
logger.info(f"STANDARD_REFERENCE_TEMPERATURE_CELSIUS = {STANDARD_REFERENCE_TEMPERATURE_CELSIUS}°C")


logger.info("Configuration settings loaded.")

# --- Weather API Configuration ---
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
if not OPENWEATHER_API_KEY:
    logger.warning("OPENWEATHER_API_KEY is not set. Weather features will be disabled.")