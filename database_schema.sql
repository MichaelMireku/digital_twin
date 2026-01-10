-- File: fuel_depot_digital_twin/database_schema.sql

-- Note: TimescaleDB extension is optional. Uncomment if you have it installed.
-- CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Table for storing static asset metadata
CREATE TABLE IF NOT EXISTS assets (
    asset_id VARCHAR(50) PRIMARY KEY,
    asset_type VARCHAR(50) NOT NULL,
    depot_id VARCHAR(20) DEFAULT 'DEMO_DEPOT_01',
    description VARCHAR(255),
    area VARCHAR(10),
    pump_house_id VARCHAR(50),
    gantry_rack_id VARCHAR(50),
    side VARCHAR(50),
    product_service VARCHAR(50),
    allowed_products TEXT[],
    usage_type VARCHAR(50),
    capacity_litres NUMERIC,
    density_at_20c_kg_m3 NUMERIC,   -- UPDATED: Density in kg/m³ at 20°C
    source_system VARCHAR(50),
    rented_to VARCHAR(100),
    connected_meter_id VARCHAR(50),
    pump_service_description VARCHAR(255),
    pipeline_source VARCHAR(100),
    pipeline_destination VARCHAR(100),
    pipeline_size_inches NUMERIC,
    pipeline_length_km NUMERIC,
    is_active BOOLEAN DEFAULT TRUE,
    maintenance_notes TEXT,
    notes TEXT,
    foam_system_present BOOLEAN DEFAULT FALSE,
    high_level_threshold_m NUMERIC,
    low_level_threshold_m NUMERIC,
    high_high_level_threshold_m NUMERIC,
    low_low_level_threshold_m NUMERIC,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for assets table
CREATE INDEX idx_assets_asset_type ON assets (asset_type);
CREATE INDEX idx_assets_area ON assets (area);
CREATE INDEX idx_assets_product_service ON assets (product_service);
CREATE INDEX idx_assets_pump_house_id ON assets (pump_house_id);
CREATE INDEX idx_assets_gantry_rack_id ON assets (gantry_rack_id);


-- Time-Series Table for Sensor/Manual Readings
CREATE TABLE IF NOT EXISTS sensor_readings (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    asset_id VARCHAR(50) NOT NULL,
    data_source_id VARCHAR(100) NOT NULL,
    metric_name VARCHAR(50) NOT NULL,
    value_numeric DOUBLE PRECISION,
    value_text TEXT,
    unit VARCHAR(20),
    status VARCHAR(50) DEFAULT 'OK'
);

-- Uncomment if using TimescaleDB:
-- SELECT create_hypertable('sensor_readings', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_sensor_readings_asset_time ON sensor_readings (asset_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_sensor_readings_source_time ON sensor_readings (data_source_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_sensor_readings_metric_time ON sensor_readings (metric_name, time DESC);


-- Time-Series Table for Calculated Data
CREATE TABLE IF NOT EXISTS calculated_data (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    asset_id VARCHAR(50) NOT NULL,
    metric_name VARCHAR(50) NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit VARCHAR(20),
    calculation_status VARCHAR(50) DEFAULT 'OK',
    PRIMARY KEY (time, asset_id, metric_name)
);

-- Uncomment if using TimescaleDB:
-- SELECT create_hypertable('calculated_data', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_calculated_data_asset_time ON calculated_data (asset_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_calculated_data_metric_name ON calculated_data (metric_name);

-- Table for storing alerts
CREATE TABLE IF NOT EXISTS alerts (
    alert_id SERIAL PRIMARY KEY,
    asset_id VARCHAR(50) NOT NULL REFERENCES assets(asset_id),
    alert_name VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    severity VARCHAR(20) DEFAULT 'Warning',
    status VARCHAR(20) DEFAULT 'Active',
    triggered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE NULL,
    acknowledged_at TIMESTAMP WITH TIME ZONE NULL,
    acknowledged_by VARCHAR(100) NULL,
    details JSONB NULL
);

CREATE INDEX IF NOT EXISTS idx_alerts_asset_id_status ON alerts (asset_id, status);
CREATE INDEX IF NOT EXISTS idx_alerts_status_triggered_at ON alerts (status, triggered_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_alert_name ON alerts (alert_name);

-- NEW TABLE for storing user/system operational events
CREATE TABLE IF NOT EXISTS operation_logs (
    log_id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    user_name VARCHAR(100), -- Who performed the action (can be 'system' or NULL)
    event_type VARCHAR(50) NOT NULL, -- e.g., 'MANUAL_ENTRY', 'ALERT_ACK', 'CONFIG_CHANGE'
    description TEXT NOT NULL, -- Human-readable description of the event
    related_asset_id VARCHAR(50) REFERENCES assets(asset_id), -- Optional foreign key to assets table
    details JSONB NULL -- For extra structured data about the event
);

CREATE INDEX IF NOT EXISTS idx_operation_logs_timestamp ON operation_logs (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_operation_logs_event_type ON operation_logs (event_type);
CREATE INDEX IF NOT EXISTS idx_operation_logs_related_asset_id ON operation_logs (related_asset_id);

-- Strapping data table
CREATE TABLE IF NOT EXISTS strapping_data (
    id SERIAL PRIMARY KEY,
    asset_id VARCHAR(50) REFERENCES assets(asset_id),
    level_mm NUMERIC NOT NULL,
    volume_litres NUMERIC NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_strapping_data_asset_id ON strapping_data (asset_id);

-- Alert configurations table
CREATE TABLE IF NOT EXISTS alert_configurations (
    rule_id SERIAL PRIMARY KEY,
    asset_type VARCHAR(50) NOT NULL,
    metric_name VARCHAR(50) NOT NULL,
    condition_type VARCHAR(10) NOT NULL,
    threshold_value NUMERIC NOT NULL,
    clear_threshold_value NUMERIC,
    duration_seconds INTEGER,
    alert_name VARCHAR(100) NOT NULL UNIQUE,
    message_template TEXT NOT NULL,
    severity VARCHAR(20) DEFAULT 'Warning',
    is_enabled BOOLEAN DEFAULT TRUE,
    description TEXT
);

CREATE INDEX IF NOT EXISTS idx_alert_configurations_asset_type ON alert_configurations (asset_type);
CREATE INDEX IF NOT EXISTS idx_alert_configurations_is_enabled ON alert_configurations (is_enabled);
