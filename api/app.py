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
        assets, total = database.get_all_asset_metadata_paginated(db, page, per_page)
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
        return jsonify({**metadata, "latest_dynamic_state": latest_state})

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

# --- Main Execution Block ---
if __name__ == '__main__':
    port = int(os.environ.get("FLASK_PORT", 5000))
    logger.info(f"Starting API server with Waitress on http://0.0.0.0:{port}")
    serve(app, host='0.0.0.0', port=port, threads=8)
