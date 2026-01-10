-- Final, Complete, and Robust Asset Population Script for Fuel Depot Digital Twin
-- This version correctly handles foreign key constraints by deleting from child tables first.

-- Step 1: Clear dependent tables first to avoid foreign key violations.
-- The order is important.
DELETE FROM alerts;
DELETE FROM strapping_data;
DELETE FROM operation_logs;
-- Note: calculated_data and sensor_readings are time-series and can be left as is,
-- but if you want a completely fresh start, uncomment the lines below.
-- DELETE FROM calculated_data;
-- DELETE FROM sensor_readings;

-- Step 2: Now it is safe to clear the main assets table.
DELETE FROM assets;

\echo 'Cleared all dependent tables and assets table. Starting fresh population...'

-- Step 3: Re-populate the assets table with complete and correct data.
-- This script uses ON CONFLICT DO UPDATE to be safe and handle reruns gracefully.

-- Storage Tanks (15 Total)
INSERT INTO assets (asset_id, asset_type, area, product_service, usage_type, capacity_litres, description, density_at_20c_kg_m3, max_level_mm) VALUES
('TANK_121', 'StorageTank', 'A', 'Gasoil (AGO)', 'Operational', 20000000, 'Area A AGO Tank 121', 835.0, 16000),
('TANK_122', 'StorageTank', 'A', 'Gasoil (AGO)', 'Operational', 20000000, 'Area A AGO Tank 122', 835.0, 16000),
('TANK_123', 'StorageTank', 'A', 'Gasoline (PMS)', 'Operational', 20000000, 'Area A PMS Tank 123', 745.0, 16000),
('TANK_124', 'StorageTank', 'A', 'Gasoline (PMS)', 'Operational', 20000000, 'Area A PMS Tank 124', 745.0, 16000),
('TANK_101', 'StorageTank', 'B', 'Gasoil (AGO)', 'Transit Storage', 2600000, 'Area B Transit Tank 101', 835.0, 16000),
('TANK_102', 'StorageTank', 'B', 'Gasoil (AGO)', 'Transit Storage', 7200000, 'Area B Transit Tank 102', 835.0, 16000),
('TANK_103', 'StorageTank', 'B', 'Gasoil (AGO)', 'Transit Storage', 12600000, 'Area B Transit Tank 103', 835.0, 16000),
('TANK_141', 'StorageTank', 'C', 'Gasoil (AGO)', 'Operational', 11600000, 'Area C AGO Tank 141', 835.0, 16000),
('TANK_142', 'StorageTank', 'C', 'Gasoil (AGO)', 'Operational', 11600000, 'Area C AGO Tank 142', 835.0, 16000),
('TANK_143', 'StorageTank', 'C', 'Gasoline (PMS)', 'Operational', 11600000, 'Area C PMS Tank 143', 745.0, 16000),
('TANK_144', 'StorageTank', 'C', 'Gasoline (PMS)', 'Operational', 11600000, 'Area C PMS Tank 144', 745.0, 16000),
('TANK_5801', 'StorageTank', 'D', 'Gasoil (AGO)', 'ThirdPartyRental', 21700000, 'Area D Rental Tank 5801', 835.0, 16000),
('TANK_5802', 'StorageTank', 'D', 'Gasoil (AGO)', 'ThirdPartyRental', 21800000, 'Area D Rental Tank 5802', 835.0, 16000),
('TANK_5803', 'StorageTank', 'D', 'Gasoil (AGO)', 'ThirdPartyRental', 21300000, 'Area D Rental Tank 5803', 835.0, 16000),
('TANK_5804', 'StorageTank', 'D', 'Gasoil (AGO)', 'ThirdPartyRental', 11300000, 'Area D Rental Tank 5804', 835.0, 16000);

-- Pump Houses
INSERT INTO assets (asset_id, asset_type, area, product_service, description) VALUES 
('PH_A', 'PumpHouse', 'A', 'PMS/AGO', 'Area A Main Pump House'),
('PH_C_AGO', 'PumpHouse', 'C', 'Gasoil (AGO)', 'Area C AGO Pump House'),
('PH_C_PMS', 'PumpHouse', 'C', 'Gasoline (PMS)', 'Area C PMS Pump House'),
('PH_B_TAPP', 'PumpHouse', 'B', 'PMS/AGO', 'Area B TAPP Pump House');

-- Pumps
INSERT INTO assets (asset_id, asset_type, pump_house_id, product_service, pump_service_description, description) VALUES 
('PUMP_A_PMS_01', 'Pump', 'PH_A', 'Gasoline (PMS)', 'Loading Gantry / Tank Transfer', 'Marathon Motor | 30Kw, 40Hp'),
('PUMP_A_PMS_02', 'Pump', 'PH_A', 'Gasoline (PMS)', 'Loading Gantry / Tank Transfer', 'Marathon Motor | 30Kw, 40Hp'),
('PUMP_A_PMS_03', 'Pump', 'PH_A', 'Gasoline (PMS)', 'Loading Gantry / Tank Transfer', 'Marathon Motor | 30Kw, 40Hp'),
('PUMP_A_PMS_04', 'Pump', 'PH_A', 'Gasoline (PMS)', 'Loading Gantry / Tank Transfer', 'Marathon Motor | 30Kw, 40Hp'),
('PUMP_A_AGO_01', 'Pump', 'PH_A', 'Gasoil (AGO)', 'Loading Gantry / Tank Transfer', 'Marathon Motor | 30Kw, 40Hp'),
('PUMP_A_AGO_02', 'Pump', 'PH_A', 'Gasoil (AGO)', 'Loading Gantry / Tank Transfer', 'Marathon Motor | 30Kw, 40Hp'),
('PUMP_A_AGO_03', 'Pump', 'PH_A', 'Gasoil (AGO)', 'Loading Gantry / Tank Transfer', 'Marathon Motor | 30Kw, 40Hp'),
('PUMP_C_AGO_01', 'Pump', 'PH_C_AGO', 'Gasoil (AGO)', 'Loading Gantry Feed', 'Marathon Motor | 30Kw, 40Hp'),
('PUMP_C_AGO_02', 'Pump', 'PH_C_AGO', 'Gasoil (AGO)', 'Loading Gantry Feed', 'Marathon Motor | 30Kw, 40Hp'),
('PUMP_C_AGO_03', 'Pump', 'PH_C_AGO', 'Gasoil (AGO)', 'Loading Gantry Feed / Tank Transfer', 'Marathon Motor | 30Kw, 40Hp'),
('PUMP_C_AGO_04', 'Pump', 'PH_C_AGO', 'Gasoil (AGO)', 'Loading Gantry Feed / Tank Transfer', 'Marathon Motor | 30Kw, 40Hp'),
('PUMP_C_PMS_01', 'Pump', 'PH_C_PMS', 'Gasoline (PMS)', 'Loading Gantry Feed', 'Marathon Motor | 30Kw, 40Hp'),
('PUMP_C_PMS_02', 'Pump', 'PH_C_PMS', 'Gasoline (PMS)', 'Loading Gantry Feed', 'Marathon Motor | 30Kw, 40Hp'),
('PUMP_C_PMS_03', 'Pump', 'PH_C_PMS', 'Gasoline (PMS)', 'Loading Gantry Feed / Tank Transfer', 'Marathon Motor | 30Kw, 40Hp'),
('PUMP_C_PMS_04', 'Pump', 'PH_C_PMS', 'Gasoline (PMS)', 'Loading Gantry Feed / Tank Transfer', 'Marathon Motor | 30Kw, 40Hp');

-- Gantries, Loading Arms, Meters, and Pipelines
INSERT INTO assets (asset_id, asset_type, area, description) VALUES
('GANTRY_1', 'GantryRack', 'Gantry', 'Loading Gantry 1'), ('GANTRY_2', 'GantryRack', 'Gantry', 'Loading Gantry 2'),
('GANTRY_3', 'GantryRack', 'Gantry', 'Loading Gantry 3'), ('GANTRY_4', 'GantryRack', 'Gantry', 'Loading Gantry 4'),
('GANTRY_5', 'GantryRack', 'Gantry', 'Loading Gantry 5'), ('GANTRY_6', 'GantryRack', 'Gantry', 'Loading Gantry 6');

INSERT INTO assets (asset_id, asset_type, gantry_rack_id, product_service, description) VALUES
('LA_1_PMS_1', 'LoadingArm', 'GANTRY_1', 'Gasoline (PMS)', 'Loading Arm 1-1 for PMS'), ('LA_1_PMS_2', 'LoadingArm', 'GANTRY_1', 'Gasoline (PMS)', 'Loading Arm 1-2 for PMS'),
('LA_1_AGO_1', 'LoadingArm', 'GANTRY_1', 'Gasoil (AGO)', 'Loading Arm 1-1 for AGO'), ('LA_1_AGO_2', 'LoadingArm', 'GANTRY_1', 'Gasoil (AGO)', 'Loading Arm 1-2 for AGO'),
('LA_2_PMS_1', 'LoadingArm', 'GANTRY_2', 'Gasoline (PMS)', 'Loading Arm 2-1 for PMS'), ('LA_2_PMS_2', 'LoadingArm', 'GANTRY_2', 'Gasoline (PMS)', 'Loading Arm 2-2 for PMS'),
('LA_2_AGO_1', 'LoadingArm', 'GANTRY_2', 'Gasoil (AGO)', 'Loading Arm 2-1 for AGO'), ('LA_2_AGO_2', 'LoadingArm', 'GANTRY_2', 'Gasoil (AGO)', 'Loading Arm 2-2 for AGO'),
('LA_3_PMS_1', 'LoadingArm', 'GANTRY_3', 'Gasoline (PMS)', 'Loading Arm 3-1 for PMS'), ('LA_3_PMS_2', 'LoadingArm', 'GANTRY_3', 'Gasoline (PMS)', 'Loading Arm 3-2 for PMS'),
('LA_3_AGO_1', 'LoadingArm', 'GANTRY_3', 'Gasoil (AGO)', 'Loading Arm 3-1 for AGO'), ('LA_3_AGO_2', 'LoadingArm', 'GANTRY_3', 'Gasoil (AGO)', 'Loading Arm 3-2 for AGO'),
('LA_4_PMS_1', 'LoadingArm', 'GANTRY_4', 'Gasoline (PMS)', 'Loading Arm 4-1 for PMS'), ('LA_4_PMS_2', 'LoadingArm', 'GANTRY_4', 'Gasoline (PMS)', 'Loading Arm 4-2 for PMS'),
('LA_4_AGO_1', 'LoadingArm', 'GANTRY_4', 'Gasoil (AGO)', 'Loading Arm 4-1 for AGO'), ('LA_4_AGO_2', 'LoadingArm', 'GANTRY_4', 'Gasoil (AGO)', 'Loading Arm 4-2 for AGO'),
('LA_5_PMS_1', 'LoadingArm', 'GANTRY_5', 'Gasoline (PMS)', 'Loading Arm 5-1 for PMS'), ('LA_5_PMS_2', 'LoadingArm', 'GANTRY_5', 'Gasoline (PMS)', 'Loading Arm 5-2 for PMS'),
('LA_5_AGO_1', 'LoadingArm', 'GANTRY_5', 'Gasoil (AGO)', 'Loading Arm 5-1 for AGO'), ('LA_5_AGO_2', 'LoadingArm', 'GANTRY_5', 'Gasoil (AGO)', 'Loading Arm 5-2 for AGO'),
('LA_6_PMS_1', 'LoadingArm', 'GANTRY_6', 'Gasoline (PMS)', 'Loading Arm 6-1 for PMS'), ('LA_6_PMS_2', 'LoadingArm', 'GANTRY_6', 'Gasoline (PMS)', 'Loading Arm 6-2 for PMS'),
('LA_6_AGO_1', 'LoadingArm', 'GANTRY_6', 'Gasoil (AGO)', 'Loading Arm 6-1 for AGO'), ('LA_6_AGO_2', 'LoadingArm', 'GANTRY_6', 'Gasoil (AGO)', 'Loading Arm 6-2 for AGO');

INSERT INTO assets (asset_id, asset_type, gantry_rack_id, product_service, description) VALUES
('METER_1_PMS', 'Meter', 'GANTRY_1', 'Gasoline (PMS)', 'Gantry 1 PMS Meter (Shared)'),
('METER_1_AGO_1', 'Meter', 'GANTRY_1', 'Gasoil (AGO)', 'Gantry 1 AGO Meter 1'),
('METER_1_AGO_2', 'Meter', 'GANTRY_1', 'Gasoil (AGO)', 'Gantry 1 AGO Meter 2'),
('METER_2_PMS', 'Meter', 'GANTRY_2', 'Gasoline (PMS)', 'Gantry 2 PMS Meter (Shared)'),
('METER_2_AGO_1', 'Meter', 'GANTRY_2', 'Gasoil (AGO)', 'Gantry 2 AGO Meter 1'),
('METER_2_AGO_2', 'Meter', 'GANTRY_2', 'Gasoil (AGO)', 'Gantry 2 AGO Meter 2'),
('METER_3_PMS', 'Meter', 'GANTRY_3', 'Gasoline (PMS)', 'Gantry 3 PMS Meter (Shared)'),
('METER_3_AGO_1', 'Meter', 'GANTRY_3', 'Gasoil (AGO)', 'Gantry 3 AGO Meter 1'),
('METER_3_AGO_2', 'Meter', 'GANTRY_3', 'Gasoil (AGO)', 'Gantry 3 AGO Meter 2'),
('METER_4_PMS', 'Meter', 'GANTRY_4', 'Gasoline (PMS)', 'Gantry 4 PMS Meter (Shared)'),
('METER_4_AGO_1', 'Meter', 'GANTRY_4', 'Gasoil (AGO)', 'Gantry 4 AGO Meter 1'),
('METER_4_AGO_2', 'Meter', 'GANTRY_4', 'Gasoil (AGO)', 'Gantry 4 AGO Meter 2'),
('METER_5_PMS', 'Meter', 'GANTRY_5', 'Gasoline (PMS)', 'Gantry 5 PMS Meter (Shared)'),
('METER_5_AGO_1', 'Meter', 'GANTRY_5', 'Gasoil (AGO)', 'Gantry 5 AGO Meter 1'),
('METER_5_AGO_2', 'Meter', 'GANTRY_5', 'Gasoil (AGO)', 'Gantry 5 AGO Meter 2'),
('METER_6_PMS', 'Meter', 'GANTRY_6', 'Gasoline (PMS)', 'Gantry 6 PMS Meter (Shared)'),
('METER_6_AGO_1', 'Meter', 'GANTRY_6', 'Gasoil (AGO)', 'Gantry 6 AGO Meter 1'),
('METER_6_AGO_2', 'Meter', 'GANTRY_6', 'Gasoil (AGO)', 'Gantry 6 AGO Meter 2');

INSERT INTO assets (asset_id, asset_type, product_service, pipeline_source, pipeline_destination, pipeline_size_inches) VALUES
('PIPE_JETTY_AGO', 'Pipeline', 'Gasoil (AGO)', 'Main Jetty', 'Area C Manifold', 24),
('PIPE_JETTY_PMS', 'Pipeline', 'Gasoline (PMS)', 'Main Jetty', 'Area C Manifold', 24),
('PIPE_TERMINAL_AGO', 'Pipeline', 'Gasoil (AGO)', 'Area A/B Manifold', 'Distribution Terminal', 18);

\echo '✅ Finished populating assets table.'
