-- Sample Asset Population Script for Fuel Depot Digital Twin Demo
-- All data is fictional and for demonstration purposes only
-- Updated to match depot layout from utils/depot_layout.py and blender_depot_generator.py

-- Clear existing data
DELETE FROM alerts;
DELETE FROM operation_logs;
DELETE FROM strapping_data;
DELETE FROM assets;

-- Storage Tanks (Fictional IDs and capacities)
-- Zone A - Northwest cluster (AGO and PMS)
INSERT INTO assets (asset_id, asset_type, area, product_service, usage_type, capacity_litres, description, density_at_20c_kg_m3) VALUES
('TK-A01', 'StorageTank', 'A', 'Gasoil (AGO)', 'Operational', 15000000, 'Zone A Storage Tank 01 - AGO', 835.0),
('TK-A02', 'StorageTank', 'A', 'Gasoil (AGO)', 'Operational', 15000000, 'Zone A Storage Tank 02 - AGO', 835.0),
('TK-A03', 'StorageTank', 'A', 'Gasoline (PMS)', 'Operational', 18000000, 'Zone A Storage Tank 03 - PMS', 745.0),
('TK-A04', 'StorageTank', 'A', 'Gasoline (PMS)', 'Operational', 18000000, 'Zone A Storage Tank 04 - PMS', 745.0),
-- Zone B - Northeast cluster (Transit Storage)
('TK-B01', 'StorageTank', 'B', 'Gasoil (AGO)', 'Transit Storage', 3000000, 'Zone B Transit Tank 01 - AGO', 835.0),
('TK-B02', 'StorageTank', 'B', 'Gasoil (AGO)', 'Transit Storage', 8000000, 'Zone B Transit Tank 02 - AGO', 835.0),
('TK-B03', 'StorageTank', 'B', 'Gasoil (AGO)', 'Transit Storage', 10000000, 'Zone B Transit Tank 03 - AGO', 835.0),
-- Zone C - Central-East cluster (Operational)
('TK-C01', 'StorageTank', 'C', 'Gasoil (AGO)', 'Operational', 12000000, 'Zone C Storage Tank 01 - AGO', 835.0),
('TK-C02', 'StorageTank', 'C', 'Gasoil (AGO)', 'Operational', 12000000, 'Zone C Storage Tank 02 - AGO', 835.0),
('TK-C03', 'StorageTank', 'C', 'Gasoline (PMS)', 'Operational', 12000000, 'Zone C Storage Tank 03 - PMS', 745.0),
('TK-C04', 'StorageTank', 'C', 'Gasoline (PMS)', 'Operational', 12000000, 'Zone C Storage Tank 04 - PMS', 745.0),
-- Zone D - South cluster (Third Party Rental)
('TK-D01', 'StorageTank', 'D', 'Gasoil (AGO)', 'ThirdPartyRental', 20000000, 'Zone D Rental Tank 01 - AGO', 835.0),
('TK-D02', 'StorageTank', 'D', 'Gasoil (AGO)', 'ThirdPartyRental', 20000000, 'Zone D Rental Tank 02 - AGO', 835.0),
('TK-D03', 'StorageTank', 'D', 'Gasoil (AGO)', 'ThirdPartyRental', 20000000, 'Zone D Rental Tank 03 - AGO', 835.0),
('TK-D04', 'StorageTank', 'D', 'Gasoil (AGO)', 'ThirdPartyRental', 10000000, 'Zone D Rental Tank 04 - AGO', 835.0);

-- Pump Houses (Updated to match depot layout)
INSERT INTO assets (asset_id, asset_type, area, product_service, description) VALUES 
('PH-A01', 'PumpHouse', 'A', 'PMS/AGO', 'Zone A Main Pump House'),
('PH-B01', 'PumpHouse', 'B', 'Gasoil (AGO)', 'Zone B Transfer Pump House'),
('PH-C01', 'PumpHouse', 'C', 'PMS/AGO', 'Zone C Main Pump House');

-- Pumps (Updated to match pump house configuration)
-- Added flow_rate_lpm column for tank transfer simulation
ALTER TABLE assets ADD COLUMN IF NOT EXISTS flow_rate_lpm NUMERIC;

INSERT INTO assets (asset_id, asset_type, pump_house_id, product_service, pump_service_description, description, flow_rate_lpm) VALUES 
-- Zone A Pumps (PH-A01) - High capacity loading/transfer pumps
('PP-A01', 'Pump', 'PH-A01', 'Gasoline (PMS)', 'Loading/Transfer', 'Zone A PMS Pump 01', 3000),
('PP-A02', 'Pump', 'PH-A01', 'Gasoline (PMS)', 'Loading/Transfer', 'Zone A PMS Pump 02', 3000),
('PP-A03', 'Pump', 'PH-A01', 'Gasoline (PMS)', 'Loading/Transfer', 'Zone A PMS Pump 03', 3000),
('PP-A04', 'Pump', 'PH-A01', 'Gasoil (AGO)', 'Loading/Transfer', 'Zone A AGO Pump 01', 2500),
('PP-A05', 'Pump', 'PH-A01', 'Gasoil (AGO)', 'Loading/Transfer', 'Zone A AGO Pump 02', 2500),
('PP-A06', 'Pump', 'PH-A01', 'Gasoil (AGO)', 'Loading/Transfer', 'Zone A AGO Pump 03', 2500),
-- Zone B Pumps (PH-B01) - Transfer pumps
('PP-B01', 'Pump', 'PH-B01', 'Gasoil (AGO)', 'Transfer', 'Zone B AGO Transfer Pump 01', 2000),
('PP-B02', 'Pump', 'PH-B01', 'Gasoil (AGO)', 'Transfer', 'Zone B AGO Transfer Pump 02', 2000),
-- Zone C Pumps (PH-C01) - Gantry feed pumps
('PP-C01', 'Pump', 'PH-C01', 'Gasoil (AGO)', 'Gantry Feed', 'Zone C AGO Pump 01', 1500),
('PP-C02', 'Pump', 'PH-C01', 'Gasoil (AGO)', 'Gantry Feed', 'Zone C AGO Pump 02', 1500),
('PP-C03', 'Pump', 'PH-C01', 'Gasoil (AGO)', 'Gantry Feed/Transfer', 'Zone C AGO Pump 03', 2000),
('PP-C04', 'Pump', 'PH-C01', 'Gasoline (PMS)', 'Gantry Feed', 'Zone C PMS Pump 01', 1800),
('PP-C05', 'Pump', 'PH-C01', 'Gasoline (PMS)', 'Gantry Feed', 'Zone C PMS Pump 02', 1800),
('PP-C06', 'Pump', 'PH-C01', 'Gasoline (PMS)', 'Gantry Feed/Transfer', 'Zone C PMS Pump 03', 2200);

-- Loading Gantries (6 lanes as per blender generator)
INSERT INTO assets (asset_id, asset_type, area, description) VALUES
('GT-01', 'GantryRack', 'Gantry', 'Loading Gantry 01'),
('GT-02', 'GantryRack', 'Gantry', 'Loading Gantry 02'),
('GT-03', 'GantryRack', 'Gantry', 'Loading Gantry 03'),
('GT-04', 'GantryRack', 'Gantry', 'Loading Gantry 04'),
('GT-05', 'GantryRack', 'Gantry', 'Loading Gantry 05'),
('GT-06', 'GantryRack', 'Gantry', 'Loading Gantry 06');

-- Loading Arms
INSERT INTO assets (asset_id, asset_type, gantry_rack_id, product_service, description) VALUES
('LA-01-P1', 'LoadingArm', 'GT-01', 'Gasoline (PMS)', 'Gantry 01 PMS Arm 1'),
('LA-01-P2', 'LoadingArm', 'GT-01', 'Gasoline (PMS)', 'Gantry 01 PMS Arm 2'),
('LA-01-A1', 'LoadingArm', 'GT-01', 'Gasoil (AGO)', 'Gantry 01 AGO Arm 1'),
('LA-01-A2', 'LoadingArm', 'GT-01', 'Gasoil (AGO)', 'Gantry 01 AGO Arm 2'),
('LA-02-P1', 'LoadingArm', 'GT-02', 'Gasoline (PMS)', 'Gantry 02 PMS Arm 1'),
('LA-02-P2', 'LoadingArm', 'GT-02', 'Gasoline (PMS)', 'Gantry 02 PMS Arm 2'),
('LA-02-A1', 'LoadingArm', 'GT-02', 'Gasoil (AGO)', 'Gantry 02 AGO Arm 1'),
('LA-02-A2', 'LoadingArm', 'GT-02', 'Gasoil (AGO)', 'Gantry 02 AGO Arm 2'),
('LA-03-P1', 'LoadingArm', 'GT-03', 'Gasoline (PMS)', 'Gantry 03 PMS Arm 1'),
('LA-03-A1', 'LoadingArm', 'GT-03', 'Gasoil (AGO)', 'Gantry 03 AGO Arm 1'),
('LA-04-P1', 'LoadingArm', 'GT-04', 'Gasoline (PMS)', 'Gantry 04 PMS Arm 1'),
('LA-04-A1', 'LoadingArm', 'GT-04', 'Gasoil (AGO)', 'Gantry 04 AGO Arm 1'),
('LA-05-P1', 'LoadingArm', 'GT-05', 'Gasoline (PMS)', 'Gantry 05 PMS Arm 1'),
('LA-05-A1', 'LoadingArm', 'GT-05', 'Gasoil (AGO)', 'Gantry 05 AGO Arm 1'),
('LA-06-P1', 'LoadingArm', 'GT-06', 'Gasoline (PMS)', 'Gantry 06 PMS Arm 1'),
('LA-06-A1', 'LoadingArm', 'GT-06', 'Gasoil (AGO)', 'Gantry 06 AGO Arm 1');

-- Flow Meters
INSERT INTO assets (asset_id, asset_type, gantry_rack_id, product_service, description) VALUES
('FM-01-P', 'Meter', 'GT-01', 'Gasoline (PMS)', 'Gantry 01 PMS Meter'),
('FM-01-A', 'Meter', 'GT-01', 'Gasoil (AGO)', 'Gantry 01 AGO Meter'),
('FM-02-P', 'Meter', 'GT-02', 'Gasoline (PMS)', 'Gantry 02 PMS Meter'),
('FM-02-A', 'Meter', 'GT-02', 'Gasoil (AGO)', 'Gantry 02 AGO Meter'),
('FM-03-P', 'Meter', 'GT-03', 'Gasoline (PMS)', 'Gantry 03 PMS Meter'),
('FM-03-A', 'Meter', 'GT-03', 'Gasoil (AGO)', 'Gantry 03 AGO Meter'),
('FM-04-P', 'Meter', 'GT-04', 'Gasoline (PMS)', 'Gantry 04 PMS Meter'),
('FM-04-A', 'Meter', 'GT-04', 'Gasoil (AGO)', 'Gantry 04 AGO Meter'),
('FM-05-P', 'Meter', 'GT-05', 'Gasoline (PMS)', 'Gantry 05 PMS Meter'),
('FM-05-A', 'Meter', 'GT-05', 'Gasoil (AGO)', 'Gantry 05 AGO Meter'),
('FM-06-P', 'Meter', 'GT-06', 'Gasoline (PMS)', 'Gantry 06 PMS Meter'),
('FM-06-A', 'Meter', 'GT-06', 'Gasoil (AGO)', 'Gantry 06 AGO Meter');

-- Pipelines
INSERT INTO assets (asset_id, asset_type, product_service, pipeline_source, pipeline_destination, pipeline_size_inches) VALUES
('PL-01', 'Pipeline', 'Gasoil (AGO)', 'Marine Terminal', 'Zone C Manifold', 20),
('PL-02', 'Pipeline', 'Gasoline (PMS)', 'Marine Terminal', 'Zone C Manifold', 20),
('PL-03', 'Pipeline', 'Gasoil (AGO)', 'Zone A/B Manifold', 'Distribution Hub', 16);

-- Fire Water Tanks (matching blender generator)
INSERT INTO assets (asset_id, asset_type, area, product_service, capacity_litres, description) VALUES
('FW-01', 'FireWaterTank', 'Central', 'Fire Water', 500000, 'Fire Water Tank 1'),
('FW-02', 'FireWaterTank', 'Central', 'Fire Water', 500000, 'Fire Water Tank 2');
