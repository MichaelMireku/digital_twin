import os
import sys
import datetime
import logging
from contextlib import contextmanager

# --- ROBUST PATH SETUP ---
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from config import settings
    from data import database
    from utils.helpers import parse_iso_datetime
    from simulation.simulator import TankTransferSimulator
    from simulation.fire_simulator import FireSimulator
    from api.auth import require_api_key
except ImportError as e:
    print(f"CRITICAL API ERROR: Could not import core modules: {e}")
    sys.exit(1)

from flask import Flask, jsonify, abort, request
from sqlalchemy.orm import Session
from pydantic import BaseModel, conint, ValidationError
from typing import Any, Optional, List, Literal, Dict
from waitress import serve

# --- Logging and App Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("depot_api")
app = Flask(__name__)

# --- Pydantic Models ---
class HistoryQueryArgs(BaseModel):
    start_time: Optional[datetime.datetime] = None
    end_time: Optional[datetime.datetime] = None
    limit: Optional[conint(gt=0)] = 5000
    source: Optional[Literal['all', 'sensor', 'calculated']] = 'all'

class OperationLogPayload(BaseModel):
    event_type: str
    description: str
    user_name: Optional[str] = "System"
    related_asset_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class TankTransferSimPayload(BaseModel):
    source_tank_id: str
    destination_tank_id: str
    pump_id: str

# --- Database Session ---
@contextmanager
def db_session_scope() -> Session:
    db = database.SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()

# --- Error Handlers ---
@app.errorhandler(400)
def bad_request(e): return jsonify({"error": "Bad Request", "details": getattr(e, 'description', str(e))}), 400
@app.errorhandler(401)
def unauthorized(e): return jsonify(error="Unauthorized"), 401
@app.errorhandler(404)
def resource_not_found(e): return jsonify(error=getattr(e, 'description', "Resource not found")), 404
@app.errorhandler(500)
def internal_server_error(e):
    logger.error(f"API Internal Server Error: {e}", exc_info=True)
    return jsonify(error="Internal server error occurred."), 500

# --- API Endpoints ---
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify(status="ok")

@app.route('/api/v1/assets', methods=['GET'])
@require_api_key
def get_all_assets():
    with db_session_scope() as db:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 500, type=int)
        include_state = request.args.get('include_state', 'true').lower() == 'true'
        
        assets, total = database.get_all_asset_metadata_paginated(db, page, per_page)
        
        # Include latest dynamic state for each asset (needed for dashboard)
        if include_state:
            for asset in assets:
                metrics_config = {}
                if asset.get('asset_type') == 'StorageTank':
                    metrics_config = {'level_percentage': 'sensor', 'temperature': 'sensor', 'volume_gov': 'calculated', 'volume_gsv': 'calculated'}
                elif asset.get('asset_type') == 'Pump':
                    metrics_config = {'flow_rate': 'sensor', 'pressure': 'sensor'}
                
                if metrics_config:
                    latest_state = database.get_latest_readings_for_asset(db, asset['asset_id'], metrics_config)
                    # Ensure None values are converted to empty dicts for safe access
                    asset['latest_dynamic_state'] = {k: (v if v is not None else {}) for k, v in latest_state.items()}
        
        return jsonify({"assets": assets, "total": total, "page": page, "per_page": per_page})

@app.route('/api/v1/assets/<string:asset_id>', methods=['GET'])
@require_api_key
def get_asset_details(asset_id):
    with db_session_scope() as db:
        metadata = database.get_asset_metadata(db, asset_id)
        if not metadata: abort(404, f"Asset '{asset_id}' not found.")
        metrics_config = {}
        if metadata.get('asset_type') == 'StorageTank':
            metrics_config = {'level_percentage': 'sensor', 'temperature': 'sensor', 'volume_gov': 'calculated', 'volume_gsv': 'calculated'}
        latest_state = database.get_latest_readings_for_asset(db, asset_id, metrics_config)
        # Ensure None values are converted to empty dicts for safe access
        safe_state = {k: (v if v is not None else {}) for k, v in latest_state.items()}
        return jsonify({**metadata, "latest_dynamic_state": safe_state})

@app.route('/api/v1/assets/<string:asset_id>/metrics/<string:metric_name>/history', methods=['GET'])
@require_api_key
def get_asset_metric_history(asset_id, metric_name):
    with db_session_scope() as db:
        try:
            args = HistoryQueryArgs(**request.args.to_dict())
            history = database.get_metric_history(db, asset_id, metric_name, args.source, args.start_time, args.end_time, args.limit)
            return jsonify(history)
        except ValidationError as e:
            abort(400, description=e.errors())

@app.route('/api/v1/simulations/fire-consequence', methods=['POST'])
@require_api_key
def run_fire_consequence_simulation():
    if not request.is_json or 'asset_id' not in request.get_json(): abort(400, "Request must be JSON with an 'asset_id'.")
    asset_id = request.get_json()['asset_id']
    try:
        with db_session_scope() as db:
            tank_meta = database.get_asset_metadata(db, asset_id)
            if not tank_meta or tank_meta.get('asset_type') != 'StorageTank': abort(404, f"Asset '{asset_id}' is not a valid storage tank.")
            simulator = FireSimulator(tank_data=tank_meta)
            results = simulator.run()
            return jsonify({"source_asset_id": asset_id, "simulation_type": "fire_consequence", "impact_radii_meters": results})
    except Exception as e:
        logger.error(f"Fire simulation error for {asset_id}: {e}", exc_info=True)
        abort(500, "Error running fire simulation.")

def normalize_product(product_service: str) -> str:
    """Normalize product names for comparison (AGO/PMS)."""
    if not product_service:
        return ""
    product = product_service.upper()
    if "AGO" in product or "GASOIL" in product or "DIESEL" in product:
        return "AGO"
    if "PMS" in product or "GASOLINE" in product or "PETROL" in product:
        return "PMS"
    return product

@app.route('/api/v1/simulations/tank-transfer', methods=['POST'])
@require_api_key
def run_tank_transfer_simulation():
    if not request.is_json: abort(400, description="Request content type must be application/json.")
    try:
        payload = TankTransferSimPayload(**request.get_json())
    except ValidationError as e:
        abort(400, description=e.errors())

    try:
        with db_session_scope() as db:
            source_tank_meta = database.get_asset_metadata(db, payload.source_tank_id)
            dest_tank_meta = database.get_asset_metadata(db, payload.destination_tank_id)
            pump_meta = database.get_asset_metadata(db, payload.pump_id)

            if not all([source_tank_meta, dest_tank_meta, pump_meta]):
                abort(404, description="One or more assets for simulation not found.")

            # Validate asset types
            if source_tank_meta.get('asset_type') != 'StorageTank':
                abort(400, description=f"Source '{payload.source_tank_id}' is not a storage tank.")
            if dest_tank_meta.get('asset_type') != 'StorageTank':
                abort(400, description=f"Destination '{payload.destination_tank_id}' is not a storage tank.")
            if pump_meta.get('asset_type') != 'Pump':
                abort(400, description=f"'{payload.pump_id}' is not a pump.")

            # Validate product compatibility
            source_product = normalize_product(source_tank_meta.get('product_service', ''))
            dest_product = normalize_product(dest_tank_meta.get('product_service', ''))
            pump_product = normalize_product(pump_meta.get('product_service', ''))

            if source_product != dest_product:
                abort(400, description=f"Product mismatch: source tank contains {source_product}, destination contains {dest_product}. Cannot transfer between different products.")

            if pump_product and pump_product != source_product:
                abort(400, description=f"Pump '{payload.pump_id}' is configured for {pump_product} but tanks contain {source_product}. Use a compatible pump.")

            source_tank_latest = database.get_latest_readings_for_asset(db, payload.source_tank_id, {'volume_gsv': 'calculated'})
            dest_tank_latest = database.get_latest_readings_for_asset(db, payload.destination_tank_id, {'volume_gsv': 'calculated'})

            source_tank_data = {
                "asset_id": source_tank_meta['asset_id'],
                "capacity_litres": source_tank_meta.get('capacity_litres', 0),
                "current_volume_litres": source_tank_latest.get('volume_gsv', {}).get('value', 0)
            }
            dest_tank_data = {
                "asset_id": dest_tank_meta['asset_id'],
                "capacity_litres": dest_tank_meta.get('capacity_litres', 0),
                "current_volume_litres": dest_tank_latest.get('volume_gsv', {}).get('value', 0)
            }

            simulator = TankTransferSimulator(source_tank_data, dest_tank_data, pump_meta)
            results = simulator.run()
            return jsonify(results)
    except Exception as e:
        logger.error(f"Error during tank transfer simulation: {e}", exc_info=True)
        abort(500, description="An internal error occurred while running the simulation.")

@app.route('/api/v1/alerts/active', methods=['GET'])
@require_api_key
def get_active_alerts():
    with db_session_scope() as db:
        active_alerts = database.get_active_alerts(db, limit=100)
        return jsonify(active_alerts)

@app.route('/api/v1/logs', methods=['GET'])
@require_api_key
def get_operation_logs():
    limit = request.args.get('limit', default=50, type=int)
    with db_session_scope() as db:
        logs = database.get_operation_logs(db, limit=limit)
        return jsonify(logs)

@app.route('/api/v1/logs', methods=['POST'])
@require_api_key
def create_operation_log():
    if not request.is_json:
        abort(400, description="Request content type must be application/json.")
    try:
        payload = OperationLogPayload(**request.get_json())
    except ValidationError as e:
        abort(400, description=e.errors())

    with db_session_scope() as db:
        success = database.save_operation_log(
            db, event_type=payload.event_type, description=payload.description,
            user_name=payload.user_name, related_asset_id=payload.related_asset_id,
            details=payload.details
        )
        if success:
            return jsonify({"message": "Log entry created successfully."}), 201
        else:
            abort(500, description="Failed to save log entry.")

@app.route('/api/v1/simulate/refresh', methods=['POST'])
@require_api_key
def refresh_sensor_data():
    """Generate fresh simulated sensor readings for all tanks."""
    import random
    from sqlalchemy import text
    
    try:
        with db_session_scope() as db:
            # Get all storage tanks
            result = db.execute(text("""
                SELECT asset_id, capacity_litres, product_service 
                FROM assets 
                WHERE asset_type = 'StorageTank'
            """))
            tanks = result.fetchall()
            
            if not tanks:
                return jsonify({"message": "No tanks found", "count": 0})
            
            now = datetime.datetime.now(datetime.timezone.utc)
            
            for tank in tanks:
                asset_id = tank[0]
                capacity = float(tank[1] or 10000000)
                product = tank[2] or ''
                
                # Generate realistic fill level (40-85%)
                fill_pct = random.uniform(40, 85)
                volume_litres = capacity * (fill_pct / 100)
                max_height_mm = 12000
                level_mm = max_height_mm * (fill_pct / 100)
                
                # Temperature based on product
                if 'AGO' in product.upper() or 'GASOIL' in product.upper():
                    temp = random.uniform(28, 35)
                else:
                    temp = random.uniform(22, 30)
                
                # Insert sensor readings
                db.execute(text("""
                    INSERT INTO sensor_readings (time, asset_id, data_source_id, metric_name, value_numeric, unit, status)
                    VALUES (:time, :asset_id, 'API_REFRESH', 'level_mm', :level, 'mm', 'OK')
                """), {"time": now, "asset_id": asset_id, "level": round(level_mm, 2)})
                
                db.execute(text("""
                    INSERT INTO sensor_readings (time, asset_id, data_source_id, metric_name, value_numeric, unit, status)
                    VALUES (:time, :asset_id, 'API_REFRESH', 'temperature', :temp, 'C', 'OK')
                """), {"time": now, "asset_id": asset_id, "temp": round(temp, 2)})
                
                db.execute(text("""
                    INSERT INTO sensor_readings (time, asset_id, data_source_id, metric_name, value_numeric, unit, status)
                    VALUES (:time, :asset_id, 'API_REFRESH', 'level_percentage', :pct, '%', 'OK')
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
            
            logger.info(f"Refreshed sensor data for {len(tanks)} tanks")
            return jsonify({"message": "Sensor data refreshed", "count": len(tanks), "timestamp": now.isoformat()})
    except Exception as e:
        logger.error(f"Error refreshing sensor data: {e}", exc_info=True)
        abort(500, description="Failed to refresh sensor data")


@app.route('/api/v1/pumps/costs', methods=['GET'])
@require_api_key
def get_pump_operating_costs():
    """
    Get pump operating costs summary.
    Query params:
      - start_time: ISO datetime (optional, defaults to last 24 hours)
      - end_time: ISO datetime (optional, defaults to now)
      - pump_id: specific pump ID (optional, returns all pumps if not specified)
    """
    from sqlalchemy import text
    
    try:
        with db_session_scope() as db:
            # Parse time range
            end_time = request.args.get('end_time')
            start_time = request.args.get('start_time')
            pump_id = request.args.get('pump_id')
            
            if end_time:
                end_time = parse_iso_datetime(end_time)
            else:
                end_time = datetime.datetime.now(datetime.timezone.utc)
            
            if start_time:
                start_time = parse_iso_datetime(start_time)
            else:
                start_time = end_time - datetime.timedelta(hours=24)
            
            # Build query for aggregated pump costs
            query = """
                SELECT 
                    cd.asset_id,
                    a.description,
                    a.motor_power_kw,
                    a.pump_house_id,
                    SUM(CASE WHEN cd.metric_name = 'energy_kwh' THEN cd.value ELSE 0 END) as total_energy_kwh,
                    SUM(CASE WHEN cd.metric_name = 'operating_cost' THEN cd.value ELSE 0 END) as total_cost,
                    COUNT(CASE WHEN cd.metric_name = 'power_kw' AND cd.value > 0 THEN 1 END) as running_intervals,
                    COUNT(CASE WHEN cd.metric_name = 'power_kw' THEN 1 END) as total_intervals
                FROM calculated_data cd
                JOIN assets a ON cd.asset_id = a.asset_id
                WHERE a.asset_type = 'Pump'
                  AND cd.time >= :start_time
                  AND cd.time <= :end_time
                  AND cd.metric_name IN ('energy_kwh', 'operating_cost', 'power_kw')
            """
            
            params = {"start_time": start_time, "end_time": end_time}
            
            if pump_id:
                query += " AND cd.asset_id = :pump_id"
                params["pump_id"] = pump_id
            
            query += " GROUP BY cd.asset_id, a.description, a.motor_power_kw, a.pump_house_id ORDER BY total_cost DESC"
            
            result = db.execute(text(query), params)
            rows = result.fetchall()
            
            pumps_data = []
            total_energy = 0
            total_cost = 0
            
            for row in rows:
                running_pct = (row[6] / row[7] * 100) if row[7] > 0 else 0
                pump_data = {
                    "asset_id": row[0],
                    "description": row[1],
                    "motor_power_kw": float(row[2]) if row[2] else None,
                    "pump_house_id": row[3],
                    "total_energy_kwh": round(float(row[4]), 2),
                    "total_cost_ghs": round(float(row[5]), 2),
                    "runtime_percentage": round(running_pct, 1)
                }
                pumps_data.append(pump_data)
                total_energy += float(row[4])
                total_cost += float(row[5])
            
            return jsonify({
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "tariff": {
                    "rate_per_kwh": 1.6135,
                    "currency": "GHS",
                    "description": "Ghana ECG Non-Residential (1000+ kWh band, incl. VAT)"
                },
                "summary": {
                    "total_energy_kwh": round(total_energy, 2),
                    "total_cost_ghs": round(total_cost, 2),
                    "pump_count": len(pumps_data)
                },
                "pumps": pumps_data
            })
    except Exception as e:
        logger.error(f"Error getting pump costs: {e}", exc_info=True)
        abort(500, description="Failed to retrieve pump operating costs")

# --- Main Execution Block ---
if __name__ == '__main__':
    port = int(os.environ.get("FLASK_PORT", 5000))
    logger.info(f"Starting API server with Waitress on http://0.0.0.0:{port}")
    serve(app, host='0.0.0.0', port=port, threads=8)
