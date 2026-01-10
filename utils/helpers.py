# File: utils/helpers.py
import logging
import datetime
import json # Added for CustomJsonEncoder
from typing import Optional
from decimal import Decimal # Added for CustomJsonEncoder to handle Decimal types

def setup_main_logging():
    """Sets up basic root logging configuration."""
    logging.basicConfig(
        level=logging.INFO, # You can change this to logging.DEBUG for more verbose output
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    # Example of adding a file handler (optional)
    # file_handler = logging.FileHandler('digital_twin_service.log')
    # file_handler.setLevel(logging.DEBUG)
    # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # file_handler.setFormatter(formatter)
    # logging.getLogger('').addHandler(file_handler) # Add to root logger to catch all
    # logger = logging.getLogger(__name__) # Get a logger for this module if needed for specific messages
    # logger.info("Root logging configured by helpers.setup_main_logging.")


def parse_iso_datetime(timestamp_str: str) -> Optional[datetime.datetime]:
    """Parses an ISO 8601 timestamp string to a timezone-aware datetime object (UTC)."""
    if not timestamp_str:
        return None
    try:
        # Handle Z for UTC timezone offset more robustly
        if timestamp_str.endswith('Z'):
            timestamp_str = timestamp_str[:-1] + '+00:00'
        dt = datetime.datetime.fromisoformat(timestamp_str)
        # Ensure timezone-aware (assume UTC if naive, or convert)
        if dt.tzinfo is None:
             dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(datetime.timezone.utc) # Standardize to UTC
    except (ValueError, TypeError) as e:
        # Use logging if available, otherwise print for simple helpers
        # logging.warning(f"Could not parse timestamp string: {timestamp_str}. Error: {e}")
        print(f"WARNING: Could not parse timestamp string: {timestamp_str}. Error: {e}") # Fallback if logger not set up when this is called
        return None

class CustomJsonEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to handle types not serializable by default,
    specifically datetime objects and Decimal objects.
    """
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            # Format datetime objects to ISO 8601 string with Z for UTC
            return obj.isoformat(timespec='milliseconds') + 'Z' if obj.tzinfo else obj.isoformat(timespec='milliseconds')
        if isinstance(obj, Decimal):
            # Convert Decimal objects to float for JSON serialization
            # Note: This might lose precision, but floats are standard in JSON.
            # For strict precision, consider keeping as string or a custom format.
            return float(obj)
        # Let the base class default method raise the TypeError for other types
        return json.JSONEncoder.default(self, obj)